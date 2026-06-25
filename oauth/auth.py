from dmr.exceptions import NotAuthenticatedError
from dmr.security import SyncAuth
from dmr.openapi.objects import SecurityScheme
from oauth.models import AccessToken

class BearerTokenAuth(SyncAuth):
    """
    Кастомный Bearer auth для dmr.
    Проверяет AccessToken из oauth_models.
    После успешной проверки токен доступен через request_auth(request).token
    """

    def __call__(self, endpoint, controller):
        request = controller.request
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")

        if not auth_header.startswith("Bearer "):
            raise NotAuthenticatedError

        token_value = auth_header[7:]

        try:
            token = AccessToken.objects.select_related(
                "company",
                "third_party",
                "client",
            ).get(token=token_value)
        except AccessToken.DoesNotExist:
            raise NotAuthenticatedError

        if not token.is_valid:
            raise NotAuthenticatedError

        request.access_token = token

        return self

    @property
    def security_schemes(self):
        return {
            "bearer": SecurityScheme(
                type="http",
                scheme="bearer",
                description="EveryPay Bearer token",
            )
        }

    @property
    def security_requirement(self):
        return {"bearer": []}