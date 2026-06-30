from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MetaInfo(BaseModel):
    totalPages: int = 1


class LinksInfo(BaseModel):
    self: str


class AccountOut(BaseModel):
    accountId: UUID
    currency: str
    accountType: str
    accountSubType: str
    status: str
    bban: Optional[str] = None


class AccountData(BaseModel):
    Account: List[AccountOut]


class AccountResponse(BaseModel):
    Data: AccountData
    Risk: Dict = Field(default_factory=dict)
    Links: LinksInfo
    Meta: MetaInfo = Field(default_factory=MetaInfo)


class StatementCreateBody(BaseModel):
    fromBookingDateTime: str
    toBookingDateTime: str


class StatementBodyWrapper(BaseModel):
    Statement: StatementCreateBody


class StatementRequestBody(BaseModel):
    Data: StatementBodyWrapper


class StatementInitOut(BaseModel):
    statementId: UUID
    accountId: UUID
    status: str


class StatementInitData(BaseModel):
    Statement: List[StatementInitOut]


class StatementInitResponse(BaseModel):
    Data: StatementInitData
    Risk: Dict = Field(default_factory=dict)
    Links: LinksInfo
    Meta: MetaInfo = Field(default_factory=MetaInfo)


class ThirdPartyOut(BaseModel):
    type: str
    code: str
    name: str
    description: str


class ThirdPartyData(BaseModel):
    ThirdParty: List[ThirdPartyOut]


class ThirdPartyResponse(BaseModel):
    Data: ThirdPartyData
    Risk: Dict = Field(default_factory=dict)
    Links: LinksInfo
    Meta: MetaInfo = Field(default_factory=MetaInfo)


class TransactionOut(BaseModel):
    transactionId: UUID
    creditDebitIndicator: str
    status: str
    bookingDateTime: str
    amount: str
    currency: str
    description: Optional[str] = None
    debtorName: Optional[str] = None
    debtorAccount: Optional[str] = None
    creditorName: Optional[str] = None
    creditorAccount: Optional[str] = None


class StatementDetailOut(BaseModel):
    statementId: UUID
    accountId: UUID
    status: str
    fromBookingDateTime: str
    toBookingDateTime: str
    Transaction: Optional[List[TransactionOut]] = None


class StatementDetailData(BaseModel):
    Statement: List[StatementDetailOut]


class StatementDetailResponse(BaseModel):
    Data: StatementDetailData
    Risk: Dict = Field(default_factory=dict)
    Links: LinksInfo
    Meta: MetaInfo = Field(default_factory=MetaInfo)
