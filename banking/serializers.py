from pydantic import BaseModel
from typing import List

class Meta(BaseModel):
    totalPages: int = 1

class Links(BaseModel):
    self: str

class AccountSchema(BaseModel):
    accountId: str
    currency: str
    accountType: str = "Business"
    accountSubType: str = "CurrentAccount"

class AccountData(BaseModel):
    Account: List[AccountSchema]

class AccountResponse(BaseModel):
    Data: AccountData
    Risk: dict = {}
    Links: Links
    Meta: Meta

class StatementInitData(BaseModel):
    accountId: str
    statementId: str
    status: str

class StatementInitResponse(BaseModel):
    Data: dict
    Risk: dict = {}
    Links: Links
    Meta: Meta