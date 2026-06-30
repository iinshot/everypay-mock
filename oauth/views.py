import base64
import json
from django.http import HttpResponseRedirect, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from .services import AuthorizeService, OAuthError, ThirdPartyCodeService, TokenService


def _parse_basic_auth(request):
    auth = request.META.get("HTTP_AUTHORIZATION", "")
    try:
        decoded = base64.b64decode(auth[6:]).decode("utf-8")
        client_id, client_secret = decoded.split(":", 1)
        return client_id, client_secret
    except Exception:
        return None, None


def _error(message: str, status: int) -> JsonResponse:
    return JsonResponse({"error": message}, status=status)


@method_decorator(csrf_exempt, name="dispatch")
class ThirdPartyCodeView(View):
    def post(self, request):
        client_id, client_secret = _parse_basic_auth(request)
        if not client_id:
            return _error("Authorization header missing or invalid", 401)

        try:
            body = json.loads(request.body)
        except Exception:
            return _error("Invalid JSON body", 400)

        user_id = body.get("userId")
        if not user_id:
            return _error("userId is required", 400)

        try:
            code = ThirdPartyCodeService.create(client_id, client_secret, user_id)
        except OAuthError as e:
            return _error(e.message, e.status)

        return JsonResponse({"code": code.code})


class AuthorizeView(View):
    def get(self, request):
        p = request.GET
        try:
            client, third_party, companies = AuthorizeService.validate_get_params(
                client_id=p.get("client_id"),
                redirect_uri=p.get("redirect_uri"),
                code=p.get("code"),
                third_party_code=p.get("third_party"),
            )
        except OAuthError as e:
            return _error(e.message, e.status)

        return render(
            request,
            "oauth/authorize.html",
            {
                "client": client,
                "third_party": third_party,
                "companies": companies,
                "params": p.dict(),
            },
        )

    def post(self, request):
        p = request.POST
        try:
            auth_code = AuthorizeService.confirm(
                client_id=p.get("client_id"),
                company_id=p.get("company_id"),
                third_party_code=p.get("third_party"),
                redirect_uri=p.get("redirect_uri"),
                code_challenge=p.get("code_challenge"),
                code_challenge_method=p.get("code_challenge_method", "S256"),
                scope=p.get("scope", "iapi/accounts"),
                state=p.get("state", ""),
                tp_code_value=p.get("code"),
            )
        except OAuthError as e:
            return _error(e.message, e.status)

        redirect_url = f"{auth_code.redirect_uri}?code={auth_code.code}"
        if auth_code.state:
            redirect_url += f"&state={auth_code.state}"

        return HttpResponseRedirect(redirect_url)


@method_decorator(csrf_exempt, name="dispatch")
class TokenView(View):
    def post(self, request):
        print("TOKEN VIEW HIT")
        print("BODY:", request.body)
        try:
            body = json.loads(request.body)
        except Exception:
            body = request.POST.dict()

        grant_type = body.get("grant_type")

        try:
            if grant_type == "third_party_authorization_code":
                access_token, refresh_token = TokenService.exchange_code(
                    client_id=body.get("client_id"),
                    code_value=body.get("code"),
                    code_verifier=body.get("code_verifier"),
                    redirect_uri=body.get("redirect_uri"),
                )
            elif grant_type == "refresh_token":
                access_token, refresh_token = TokenService.refresh(
                    client_id=body.get("client_id"),
                    refresh_token_value=body.get("refresh_token"),
                )
            else:
                return _error("Unsupported grant_type", 400)
        except OAuthError as e:
            return _error(e.message, e.status)

        return JsonResponse(
            {
                "access_token": access_token.token,
                "token_type": "Bearer",
                "expires_in": 3600,
                "refresh_token": refresh_token.token,
                "scope": access_token.scope,
            }
        )
