import base64
import json
from datetime import timedelta

import pytest
from django.utils import timezone

from banking.models import Account, Company, ThirdParty
from oauth.models import (
    AccessToken,
    OAuthClient,
    PKCEAuthorizationCode,
    RefreshToken,
    ThirdPartyCode,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def bank():
    return ThirdParty.objects.create(
        type="Bank",
        code="tbank",
        name="T-Bank",
        description="Test bank",
    )


@pytest.fixture
def company():
    return Company.objects.create(
        name="Test Company",
        inn="123456789012",
    )


@pytest.fixture
def account(company, bank):
    return Account.objects.create(
        company=company,
        bank=bank,
        currency="RUB",
        account_type="Business",
        account_sub_type="CurrentAccount",
        status="Enabled",
        bban="12345678912345678900",
    )


@pytest.fixture
def oauth_client(company):
    return OAuthClient.objects.create(
        name="Test App",
        client_id="test-client",
        client_secret="test-secret",
        redirect_uris="http://localhost/callback",
        company=company,
    )


@pytest.fixture
def basic_auth_headers(oauth_client):
    credentials = base64.b64encode(
        f"{oauth_client.client_id}:{oauth_client.client_secret}".encode(),
    ).decode()
    return {"HTTP_AUTHORIZATION": f"Basic {credentials}"}


@pytest.fixture
def third_party_code(oauth_client):
    return ThirdPartyCode.objects.create(
        code="test-tp-code",
        client=oauth_client,
        user_id="user123",
        expires_at=timezone.now() + timedelta(minutes=10),
    )


@pytest.fixture
def pkce_auth_code(oauth_client, company, bank):
    return PKCEAuthorizationCode.objects.create(
        code="test-auth-code",
        client=oauth_client,
        company=company,
        third_party=bank,
        redirect_uri="http://localhost/callback",
        scope="iapi/accounts",
        code_challenge="test-challenge",
        code_challenge_method="plain",
        state="test-state",
        expires_at=timezone.now() + timedelta(minutes=10),
    )


@pytest.fixture
def access_token(oauth_client, company, bank):
    return AccessToken.objects.create(
        token="test-access-token",
        client=oauth_client,
        company=company,
        third_party=bank,
        scope="iapi/accounts",
        expires_at=timezone.now() + timedelta(hours=1),
    )


@pytest.fixture
def refresh_token(access_token):
    return RefreshToken.objects.create(
        token="test-refresh-token",
        access_token=access_token,
        expires_at=timezone.now() + timedelta(hours=24),
    )


def test_third_party_code_success(client, oauth_client, basic_auth_headers):
    response = client.post(
        "/oauth/third-party-code",
        data=json.dumps({"userId": "user123"}),
        content_type="application/json",
        **basic_auth_headers,
    )
    assert response.status_code == 200
    assert "code" in response.json()


def test_third_party_code_missing_user_id(client, basic_auth_headers):
    response = client.post(
        "/oauth/third-party-code",
        data=json.dumps({}),
        content_type="application/json",
        **basic_auth_headers,
    )
    assert response.status_code == 400
    assert response.json()["error"] == "userId is required"


def test_third_party_code_invalid_credentials(client):
    credentials = base64.b64encode(b"wrong-client:wrong-secret").decode()
    response = client.post(
        "/oauth/third-party-code",
        data=json.dumps({"userId": "user123"}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Basic {credentials}",
    )
    assert response.status_code == 401


def test_third_party_code_no_auth(client):
    response = client.post(
        "/oauth/third-party-code",
        data=json.dumps({"userId": "user123"}),
        content_type="application/json",
    )
    assert response.status_code == 401


def test_third_party_code_wrong_secret(client, oauth_client):
    credentials = base64.b64encode(
        f"{oauth_client.client_id}:wrong-secret".encode(),
    ).decode()
    response = client.post(
        "/oauth/third-party-code",
        data=json.dumps({"userId": "user123"}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Basic {credentials}",
    )
    assert response.status_code == 401


def test_authorize_get_shows_form(
    client,
    oauth_client,
    third_party_code,
    bank,
    account,
):
    response = client.get(
        "/oauth/authorize",
        {
            "client_id": oauth_client.client_id,
            "redirect_uri": "http://localhost/callback",
            "response_type": "third_party_authorization_code",
            "scope": "iapi/accounts",
            "code_challenge": "test-challenge",
            "code_challenge_method": "S256",
            "state": "xyz",
            "third_party": bank.code,
            "code": third_party_code.code,
        },
    )
    assert response.status_code == 200
    assert b"Test App" in response.content
    assert b"T-Bank" in response.content


def test_authorize_get_invalid_client(client, third_party_code, bank):
    response = client.get(
        "/oauth/authorize",
        {
            "client_id": "nonexistent-client",
            "redirect_uri": "http://localhost/callback",
            "code": third_party_code.code,
            "third_party": bank.code,
        },
    )
    assert response.status_code == 400


def test_authorize_get_invalid_redirect_uri(
    client,
    oauth_client,
    third_party_code,
    bank,
):
    response = client.get(
        "/oauth/authorize",
        {
            "client_id": oauth_client.client_id,
            "redirect_uri": "http://evil.com/callback",
            "code": third_party_code.code,
            "third_party": bank.code,
        },
    )
    assert response.status_code == 400


def test_authorize_get_expired_code(client, oauth_client, bank, account):
    expired_code = ThirdPartyCode.objects.create(
        code="expired-code",
        client=oauth_client,
        user_id="user123",
        expires_at=timezone.now() - timedelta(minutes=1),
    )
    response = client.get(
        "/oauth/authorize",
        {
            "client_id": oauth_client.client_id,
            "redirect_uri": "http://localhost/callback",
            "code": expired_code.code,
            "third_party": bank.code,
        },
    )
    assert response.status_code == 400


def test_token_exchange_code_success(client, pkce_auth_code):
    response = client.post(
        "/oauth/token",
        data=json.dumps(
            {
                "grant_type": "third_party_authorization_code",
                "code": pkce_auth_code.code,
                "code_verifier": "test-challenge",  # plain method: verifier == challenge
                "client_id": pkce_auth_code.client.client_id,
                "redirect_uri": pkce_auth_code.redirect_uri,
            },
        ),
        content_type="application/json",
    )
    data = response.json()
    assert response.status_code == 200
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "Bearer"
    assert data["expires_in"] == 3600


def test_token_exchange_code_marks_as_used(client, pkce_auth_code):
    client.post(
        "/oauth/token",
        data=json.dumps(
            {
                "grant_type": "third_party_authorization_code",
                "code": pkce_auth_code.code,
                "code_verifier": "test-challenge",
                "client_id": pkce_auth_code.client.client_id,
                "redirect_uri": pkce_auth_code.redirect_uri,
            },
        ),
        content_type="application/json",
    )
    pkce_auth_code.refresh_from_db()
    assert pkce_auth_code.is_used is True


def test_token_exchange_code_cannot_reuse(client, pkce_auth_code):
    payload = json.dumps(
        {
            "grant_type": "third_party_authorization_code",
            "code": pkce_auth_code.code,
            "code_verifier": "test-challenge",
            "client_id": pkce_auth_code.client.client_id,
            "redirect_uri": pkce_auth_code.redirect_uri,
        },
    )
    client.post("/oauth/token", data=payload, content_type="application/json")
    response = client.post(
        "/oauth/token",
        data=payload,
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json()["error"] == "Code expired or already used"


def test_token_exchange_invalid_pkce(client, pkce_auth_code):
    response = client.post(
        "/oauth/token",
        data=json.dumps(
            {
                "grant_type": "third_party_authorization_code",
                "code": pkce_auth_code.code,
                "code_verifier": "wrong-verifier",
                "client_id": pkce_auth_code.client.client_id,
                "redirect_uri": pkce_auth_code.redirect_uri,
            },
        ),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json()["error"] == "Invalid code_verifier"


def test_token_exchange_redirect_uri_mismatch(client, pkce_auth_code):
    response = client.post(
        "/oauth/token",
        data=json.dumps(
            {
                "grant_type": "third_party_authorization_code",
                "code": pkce_auth_code.code,
                "code_verifier": "test-challenge",
                "client_id": pkce_auth_code.client.client_id,
                "redirect_uri": "http://wrong.com/callback",
            },
        ),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json()["error"] == "redirect_uri mismatch"


def test_token_refresh_success(client, refresh_token):
    response = client.post(
        "/oauth/token",
        data=json.dumps(
            {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token.token,
                "client_id": refresh_token.access_token.client.client_id,
            },
        ),
        content_type="application/json",
    )
    data = response.json()
    assert response.status_code == 200
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["access_token"] != refresh_token.access_token.token
    assert data["refresh_token"] != refresh_token.token


def test_token_refresh_revokes_old_access_token(client, refresh_token):
    old_access_token = refresh_token.access_token
    client.post(
        "/oauth/token",
        data=json.dumps(
            {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token.token,
                "client_id": old_access_token.client.client_id,
            },
        ),
        content_type="application/json",
    )
    old_access_token.refresh_from_db()
    assert old_access_token.is_revoked is True


def test_token_refresh_cannot_reuse(client, refresh_token):
    payload = json.dumps(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token.token,
            "client_id": refresh_token.access_token.client.client_id,
        },
    )
    client.post("/oauth/token", data=payload, content_type="application/json")
    response = client.post(
        "/oauth/token",
        data=payload,
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json()["error"] == "Refresh token expired or already used"


def test_token_refresh_expired(client, oauth_client, company, bank):
    old_token = AccessToken.objects.create(
        token="old-token",
        client=oauth_client,
        company=company,
        third_party=bank,
        scope="iapi/accounts",
        expires_at=timezone.now() + timedelta(hours=1),
    )
    expired_refresh = RefreshToken.objects.create(
        token="expired-refresh",
        access_token=old_token,
        expires_at=timezone.now() - timedelta(minutes=1),
    )
    response = client.post(
        "/oauth/token",
        data=json.dumps(
            {
                "grant_type": "refresh_token",
                "refresh_token": expired_refresh.token,
                "client_id": oauth_client.client_id,
            },
        ),
        content_type="application/json",
    )
    assert response.status_code == 400


def test_token_unsupported_grant_type(client):
    response = client.post(
        "/oauth/token",
        data=json.dumps({"grant_type": "password"}),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json()["error"] == "Unsupported grant_type"
