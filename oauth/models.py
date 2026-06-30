import base64
import hashlib
from datetime import timedelta

from django.db import models
from django.utils import timezone


class OAuthClient(models.Model):
    """
    Зарегистрированное приложение-клиент.
    Создаётся в админке, client_id/secret выдаётся партнёру.
    """

    name = models.CharField(max_length=200, verbose_name="Название")
    client_id = models.CharField(max_length=100, unique=True, verbose_name="Client ID")
    client_secret = models.CharField(max_length=200, verbose_name="Client Secret")
    redirect_uris = models.TextField(
        verbose_name="Разрешённые uri",
        help_text="По одному на строку",
    )
    company = models.OneToOneField(
        "banking.Company",
        on_delete=models.CASCADE,
        related_name="oauth_client",
        verbose_name="Компания",
    )
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "OAuth клиент"
        verbose_name_plural = "OAuth клиенты"

    def __str__(self):
        return f"{self.name} ({self.client_id})"

    def check_secret(self, secret: str) -> bool:
        return self.client_secret == secret

    def has_redirect_uri(self, uri: str) -> bool:
        allowed = [u.strip() for u in self.redirect_uris.splitlines() if u.strip()]
        return uri in allowed


class ThirdPartyCode(models.Model):
    """
    Короткоживущий код привязанный к клиенту и user_id.
    Живёт 10 минут, одноразовый.
    """

    code = models.CharField(max_length=200, unique=True)
    client = models.ForeignKey(OAuthClient, on_delete=models.CASCADE)
    user_id = models.CharField(max_length=200, verbose_name="ID пользователя")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Third-party code"
        verbose_name_plural = "Third-party codes"

    def save(self, *args, **kwargs):
        if not self.pk and not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    @property
    def is_valid(self) -> bool:
        return not self.is_used and timezone.now() < self.expires_at


class PKCEAuthorizationCode(models.Model):
    """
    Код авторизации после подтверждения на странице authorize.
    Содержит code_challenge для проверки PKCE.
    Живёт 10 минут, одноразовый.
    """

    code = models.CharField(max_length=200, unique=True)
    client = models.ForeignKey(OAuthClient, on_delete=models.CASCADE)
    company = models.ForeignKey("banking.Company", on_delete=models.CASCADE)
    third_party = models.ForeignKey("banking.ThirdParty", on_delete=models.CASCADE)
    redirect_uri = models.CharField(max_length=500)
    scope = models.CharField(max_length=200)
    code_challenge = models.CharField(max_length=200)
    code_challenge_method = models.CharField(max_length=10)
    state = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Authorization code"
        verbose_name_plural = "Authorization codes"

    def save(self, *args, **kwargs):
        if not self.pk and not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    @property
    def is_valid(self) -> bool:
        return not self.is_used and timezone.now() < self.expires_at

    def verify_pkce(self, code_verifier: str) -> bool:
        if self.code_challenge_method == "plain":
            return self.code_challenge == code_verifier
        if self.code_challenge_method == "S256":
            digest = hashlib.sha256(code_verifier.encode()).digest()
            challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
            return self.code_challenge == challenge
        return False


class AccessToken(models.Model):
    """
    Bearer-токен для авторизации запросов к API.
    Живёт 1 час.
    """

    token = models.CharField(max_length=200, unique=True)
    client = models.ForeignKey(OAuthClient, on_delete=models.CASCADE)
    company = models.ForeignKey("banking.Company", on_delete=models.CASCADE)
    third_party = models.ForeignKey("banking.ThirdParty", on_delete=models.CASCADE)
    scope = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_revoked = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Access token"
        verbose_name_plural = "Access tokens"

    def __str__(self):
        return f"{self.client} → {self.company} [{self.token[:16]}…]"

    @property
    def is_valid(self) -> bool:
        return not self.is_revoked and timezone.now() < self.expires_at

    def revoke(self):
        self.is_revoked = True
        self.save(update_fields=["is_revoked"])


class RefreshToken(models.Model):
    """
    Refresh-токен для получения новой пары токенов.
    Живёт 24 часа, одноразовый.
    """

    token = models.CharField(max_length=200, unique=True)
    access_token = models.OneToOneField(
        AccessToken,
        on_delete=models.CASCADE,
        related_name="refresh_token",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Refresh token"
        verbose_name_plural = "Refresh tokens"

    @property
    def is_valid(self) -> bool:
        return not self.is_used and timezone.now() < self.expires_at
