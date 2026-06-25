import pytest
import json
from banking.models import ThirdParty, Company, Account
from oauth.models import AccessToken, OAuthClient
from django.utils import timezone
from datetime import timedelta

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
        name="Test",
        client_id="test-client",
        client_secret="secret",
        redirect_uris="http://localhost/callback",
        company=company,
    )


@pytest.fixture
def access_token(company, bank, oauth_client):
    return AccessToken.objects.create(
        token="test-token",
        client=oauth_client,
        company=company,
        third_party=bank,
        scope="iapi/accounts",
        expires_at=timezone.now() + timedelta(hours=1),
    )


@pytest.fixture
def auth_headers(access_token):
    return {"HTTP_AUTHORIZATION": f"Bearer {access_token.token}"}


def test_get_accounts(client, account, auth_headers):
    response = client.get("/api/accounts/", **auth_headers)
    data = response.json()

    assert response.status_code == 200
    assert len(data["Data"]["Account"]) == 1
    assert data["Data"]["Account"][0]["accountId"] == str(account.account_id)


def test_get_account_detail(client, account, auth_headers):
    response = client.get(f"/api/accounts/{account.account_id}/", **auth_headers)
    data = response.json()

    assert response.status_code == 200
    assert data["Data"]["Account"][0]["accountId"] == str(account.account_id)


def test_accounts_requires_token(client):
    response = client.get("/api/accounts/")

    assert response.status_code == 401


def test_get_third_parties(client, bank, auth_headers):
    response = client.get("/api/third-parties/", **auth_headers)
    data = response.json()

    assert response.status_code == 200
    assert len(data["Data"]["ThirdParty"]) == 1
    assert data["Data"]["ThirdParty"][0]["code"] == "tbank"


def test_create_statement(client, account, auth_headers):
    payload = {
        "Data": {
            "Statement": {
                "fromBookingDateTime": "2026-01-01T00:00:00Z",
                "toBookingDateTime": "2026-12-31T00:00:00Z",
            }
        }
    }
    response = client.post(
        f"/api/statements/{account.account_id}/",
        data=json.dumps(payload),
        content_type="application/json",
        **auth_headers,
    )
    data = response.json()

    assert response.status_code == 201
    assert data["Data"]["Statement"][0]["accountId"] == str(account.account_id)
