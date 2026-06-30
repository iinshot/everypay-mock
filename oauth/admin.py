from django.contrib import admin

from .models import (
    AccessToken,
    OAuthClient,
    PKCEAuthorizationCode,
    RefreshToken,
    ThirdPartyCode,
)


@admin.register(OAuthClient)
class OAuthClientAdmin(admin.ModelAdmin):
    list_display = ("name", "client_id", "company", "is_active", "created_at")
    search_fields = ("name", "client_id", "company__name")
    readonly_fields = ("created_at",)


@admin.register(AccessToken)
class AccessTokenAdmin(admin.ModelAdmin):
    list_display = (
        "client",
        "company",
        "third_party",
        "created_at",
        "expires_at",
        "is_revoked",
    )
    list_filter = ("is_revoked",)
    readonly_fields = ("token", "created_at")


@admin.register(RefreshToken)
class RefreshTokenAdmin(admin.ModelAdmin):
    list_display = ("access_token", "created_at", "expires_at", "is_used")
    readonly_fields = ("token", "created_at")


@admin.register(ThirdPartyCode)
class ThirdPartyCodeAdmin(admin.ModelAdmin):
    list_display = ("client", "user_id", "created_at", "expires_at", "is_used")
    readonly_fields = ("code", "created_at")


@admin.register(PKCEAuthorizationCode)
class PKCEAuthorizationCodeAdmin(admin.ModelAdmin):
    list_display = ("client", "company", "created_at", "expires_at", "is_used")
    readonly_fields = ("code", "created_at")
