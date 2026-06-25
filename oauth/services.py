import secrets
from datetime import timedelta
from django.utils import timezone
from banking.models import Company, ThirdParty
from .models import (
    AccessToken,
    OAuthClient,
    PKCEAuthorizationCode,
    RefreshToken,
    ThirdPartyCode,
)


class OAuthError(Exception):
    def __init__(self, message: str, status: int = 400):
        self.message = message
        self.status = status
        super().__init__(message)


class ThirdPartyCodeService:
    @staticmethod
    def create(client_id: str, client_secret: str, user_id: str) -> ThirdPartyCode:
        try:
            client = OAuthClient.objects.get(client_id=client_id, is_active=True)
        except OAuthClient.DoesNotExist:
            raise OAuthError("Invalid client_id", 401)

        if not client.check_secret(client_secret):
            raise OAuthError("Invalid client_secret", 401)

        return ThirdPartyCode.objects.create(
            code=secrets.token_urlsafe(32),
            client=client,
            user_id=user_id,
            expires_at=timezone.now() + timedelta(minutes=10),
        )


class AuthorizeService:
    @staticmethod
    def validate_get_params(
        client_id: str, redirect_uri: str, code: str, third_party_code: str
    ):
        try:
            client = OAuthClient.objects.select_related("company").get(
                client_id=client_id, is_active=True
            )
        except OAuthClient.DoesNotExist:
            raise OAuthError("Invalid client_id", 400)

        if not redirect_uri or not client.has_redirect_uri(redirect_uri):
            raise OAuthError("Invalid redirect_uri", 400)

        try:
            tp_code = ThirdPartyCode.objects.select_related("client").get(code=code)
        except ThirdPartyCode.DoesNotExist:
            raise OAuthError("Invalid code", 400)

        if not tp_code.is_valid:
            raise OAuthError("Code expired or already used", 400)

        if tp_code.client != client:
            raise OAuthError("Code does not belong to this client", 400)

        try:
            third_party = ThirdParty.objects.get(code=third_party_code)
        except ThirdParty.DoesNotExist:
            raise OAuthError("Invalid third_party", 400)

        companies = Company.objects.filter(accounts__bank=third_party).distinct()

        return client, third_party, companies

    @staticmethod
    def confirm(
        client_id: str,
        company_id: str,
        third_party_code: str,
        redirect_uri: str,
        code_challenge: str,
        code_challenge_method: str,
        scope: str,
        state: str,
        tp_code_value: str,
    ) -> PKCEAuthorizationCode:
        try:
            client = OAuthClient.objects.get(client_id=client_id, is_active=True)
        except OAuthClient.DoesNotExist:
            raise OAuthError("Invalid client_id", 400)

        try:
            tp_code = ThirdPartyCode.objects.get(code=tp_code_value)
        except ThirdPartyCode.DoesNotExist:
            raise OAuthError("Invalid code", 400)

        if not tp_code.is_valid:
            raise OAuthError("Code expired or already used", 400)

        tp_code.is_used = True
        tp_code.save(update_fields=["is_used"])

        try:
            company = Company.objects.get(id=company_id)
            third_party = ThirdParty.objects.get(code=third_party_code)
        except (Company.DoesNotExist, ThirdParty.DoesNotExist):
            raise OAuthError("Invalid company or third_party", 400)

        return PKCEAuthorizationCode.objects.create(
            code=secrets.token_urlsafe(32),
            client=client,
            company=company,
            third_party=third_party,
            redirect_uri=redirect_uri,
            scope=scope,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            state=state,
            expires_at=timezone.now() + timedelta(minutes=10),
        )


class TokenService:
    @staticmethod
    def exchange_code(
        client_id: str,
        code_value: str,
        code_verifier: str,
        redirect_uri: str,
    ) -> tuple[AccessToken, RefreshToken]:
        try:
            client = OAuthClient.objects.get(client_id=client_id, is_active=True)
        except OAuthClient.DoesNotExist:
            raise OAuthError("Invalid client_id", 401)

        try:
            auth_code = PKCEAuthorizationCode.objects.select_related(
                "company", "third_party"
            ).get(code=code_value, client=client)
        except PKCEAuthorizationCode.DoesNotExist:
            raise OAuthError("Invalid code", 400)

        if not auth_code.is_valid:
            raise OAuthError("Code expired or already used", 400)

        if auth_code.redirect_uri != redirect_uri:
            raise OAuthError("redirect_uri mismatch", 400)

        if not auth_code.verify_pkce(code_verifier):
            raise OAuthError("Invalid code_verifier", 400)

        auth_code.is_used = True
        auth_code.save(update_fields=["is_used"])

        return _create_token_pair(
            client=client,
            company=auth_code.company,
            third_party=auth_code.third_party,
            scope=auth_code.scope,
        )

    @staticmethod
    def refresh(
        client_id: str, refresh_token_value: str
    ) -> tuple[AccessToken, RefreshToken]:
        try:
            client = OAuthClient.objects.get(client_id=client_id, is_active=True)
        except OAuthClient.DoesNotExist:
            raise OAuthError("Invalid client_id", 401)

        try:
            old_refresh = RefreshToken.objects.select_related(
                "access_token__company",
                "access_token__third_party",
            ).get(token=refresh_token_value, access_token__client=client)
        except RefreshToken.DoesNotExist:
            raise OAuthError("Invalid refresh_token", 400)

        if not old_refresh.is_valid:
            raise OAuthError("Refresh token expired or already used", 400)

        old_refresh.is_used = True
        old_refresh.save(update_fields=["is_used"])
        old_refresh.access_token.revoke()

        return _create_token_pair(
            client=client,
            company=old_refresh.access_token.company,
            third_party=old_refresh.access_token.third_party,
            scope=old_refresh.access_token.scope,
        )


def _create_token_pair(
    client, company, third_party, scope
) -> tuple[AccessToken, RefreshToken]:
    access_token = AccessToken.objects.create(
        token=secrets.token_urlsafe(32),
        client=client,
        company=company,
        third_party=third_party,
        scope=scope,
        expires_at=timezone.now() + timedelta(hours=1),
    )
    refresh_token = RefreshToken.objects.create(
        token=secrets.token_urlsafe(32),
        access_token=access_token,
        expires_at=timezone.now() + timedelta(hours=24),
    )
    return access_token, refresh_token
