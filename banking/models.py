from uuid import uuid4
from django.db import models
from django.utils import timezone

class ThirdParty(models.Model):
    """
    Банки(Поставщики платежных услуг - ППУ) или
    Сервисы (Сервисные поставщики информационных услуг - СПИУ)
    """
    TYPE_CHOICES = [("bank", "Bank"), ("service", "Service")]
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=512)

    def __str__(self):
        return self.name

class Company(models.Model):
    """
    Компания, которой принадлежит счет
    """
    name = models.CharField(max_length=255)
    inn = models.CharField(max_length=12, unique=True)

    def __str__(self):
        return self.name

class Account(models.Model):
    """
    Банковский счет
    """
    account_id = models.CharField(max_length=255, unique=True, default=uuid4)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="accounts")
    bank = models.ForeignKey(ThirdParty, on_delete=models.PROTECT, related_name="accounts")
    currency = models.CharField(max_length=3, default="RUB")

    def __str__(self):
        return f"{self.bank.name} - {self.company.name} ({self.account_id})"

class Transaction(models.Model):
    """
    Операция по счету
    """
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="transactions")
    transaction_id = models.CharField(max_length=255, unique=True, default=uuid4)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    credit_debit_indicator = models.CharField(max_length=10, choices=[("Credit", "Приход"), ("Debit", "Расход")])
    booking_date_time = models.DateTimeField(default=timezone.now)
    description = models.TextField(max_length=512)

class StatementRequest(models.Model):
    """
    Запрос на выписку (для имитации задержки в 30 сек)
    """
    statement_id = models.CharField(max_length=255, unique=True, default=uuid4)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="statement_requests")
    created_at = models.DateTimeField(auto_now_add=True)
    from_booking_date_time = models.DateTimeField()
    to_booking_date_time = models.DateTimeField()

    @property
    def status(self):
        if (timezone.now() - self.created_at).total_seconds() > 30:
            return "Ready"
        return "Processing"
