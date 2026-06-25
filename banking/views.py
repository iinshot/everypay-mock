from dmr import Body, Controller
from dmr.plugins.pydantic import PydanticSerializer
from oauth.auth import BearerTokenAuth
from banking.models import ThirdParty
from banking.serializers import (
    AccountOut,
    AccountData,
    AccountResponse,
    LinksInfo,
    StatementInitOut,
    StatementInitData,
    StatementInitResponse,
    StatementRequestBody,
    StatementDetailOut,
    StatementDetailData,
    StatementDetailResponse,
    ThirdPartyOut,
    ThirdPartyData,
    ThirdPartyResponse,
    TransactionOut,
)
from banking.services import AccountService, StatementService


def _links(request) -> LinksInfo:
    return LinksInfo(self=request.build_absolute_uri())


class PartiesController(Controller[PydanticSerializer]):
    auth = (BearerTokenAuth(),)

    def get(self) -> ThirdPartyResponse:
        request = self.request
        parties = ThirdParty.objects.all()
        return ThirdPartyResponse(
            Data=ThirdPartyData(
                ThirdParty=[
                    ThirdPartyOut(
                        type=p.type,
                        code=p.code,
                        name=p.name,
                        description=p.description,
                    )
                    for p in parties
                ]
            ),
            Links=_links(request),
        )


class AccountsController(Controller[PydanticSerializer]):
    auth = (BearerTokenAuth(),)

    def get(self) -> AccountResponse:
        request = self.request
        token = request.access_token
        accounts = AccountService.get_accounts(token.company)
        return AccountResponse(
            Data=AccountData(
                Account=[
                    AccountOut(
                        accountId=acc.account_id,
                        currency=acc.currency,
                        accountType=acc.account_type,
                        accountSubType=acc.account_sub_type,
                        status=acc.status,
                        bban=acc.bban or None,
                    )
                    for acc in accounts
                ]
            ),
            Links=_links(request),
        )


class AccountDetailController(Controller[PydanticSerializer]):
    auth = (BearerTokenAuth(),)

    def get(self) -> AccountResponse:
        request = self.request
        account_id = self.kwargs["account_id"]
        token = request.access_token
        acc = AccountService.get_account(account_id, token.company)
        return AccountResponse(
            Data=AccountData(
                Account=[
                    AccountOut(
                        accountId=acc.account_id,
                        currency=acc.currency,
                        accountType=acc.account_type,
                        accountSubType=acc.account_sub_type,
                        status=acc.status,
                        bban=acc.bban or None,
                    )
                ]
            ),
            Links=_links(request),
        )


class StatementsController(Controller[PydanticSerializer]):
    auth = (BearerTokenAuth(),)

    def post(self, parsed_body: Body[StatementRequestBody]) -> StatementInitResponse:
        request = self.request
        account_id = self.kwargs["account_id"]
        token = request.access_token
        acc = AccountService.get_account(account_id, token.company)
        stmt_data = parsed_body.Data.Statement
        stmt = StatementService.create(
            acc,
            stmt_data.fromBookingDateTime,
            stmt_data.toBookingDateTime,
        )
        return StatementInitResponse(
            Data=StatementInitData(
                Statement=[
                    StatementInitOut(
                        statementId=stmt.statement_id,
                        accountId=acc.account_id,
                        status=stmt.status,
                    )
                ]
            ),
            Links=_links(request),
        )


class StatementDetailController(Controller[PydanticSerializer]):
    auth = (BearerTokenAuth(),)

    def get(self) -> StatementDetailResponse:
        request = self.request
        account_id = self.kwargs["account_id"]
        statement_id = self.kwargs["statement_id"]
        token = request.access_token
        acc = AccountService.get_account(account_id, token.company)
        stmt = StatementService.get(statement_id, acc)
        transactions = [
            TransactionOut(
                transactionId=t.transaction_id,
                creditDebitIndicator=t.credit_debit_indicator,
                status=t.status,
                bookingDateTime=t.booking_date_time.isoformat(),
                amount=str(t.amount),
                currency=t.currency,
                description=t.description or None,
                debtorName=t.debtor_name or None,
                debtorAccount=t.debtor_account or None,
                creditorName=t.creditor_name or None,
                creditorAccount=t.creditor_account or None,
            )
            for t in stmt.get_transactions()
        ]

        return StatementDetailResponse(
            Data=StatementDetailData(
                Statement=[
                    StatementDetailOut(
                        statementId=stmt.statement_id,
                        accountId=acc.account_id,
                        status=stmt.status,
                        fromBookingDateTime=stmt.from_booking_date_time.isoformat(),
                        toBookingDateTime=stmt.to_booking_date_time.isoformat(),
                        Transaction=transactions,
                    )
                ]
            ),
            Links=_links(request),
        )
