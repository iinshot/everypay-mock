from uuid import UUID
from django.shortcuts import get_object_or_404
from .models import Account, StatementRequest

class AccountService:
    @staticmethod
    def get_accounts(company):
        return Account.objects.filter(company=company).select_related("bank")

    @staticmethod
    def get_account(account_id: UUID, company) -> Account:
        return get_object_or_404(Account, account_id=account_id, company=company)

class StatementService:
    @staticmethod
    def create(account: Account, from_dt: str, to_dt: str) -> StatementRequest:
        return StatementRequest.objects.create(
            account=account,
            from_booking_date_time=from_dt,
            to_booking_date_time=to_dt,
        )

    @staticmethod
    def get(statement_id: UUID, account: Account) -> StatementRequest:
        return get_object_or_404(
            StatementRequest,
            statement_id=statement_id,
            account=account,
        )