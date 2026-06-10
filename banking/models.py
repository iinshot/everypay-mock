from datetime import timedelta
from uuid import uuid4
from django.db import models
from django.utils import timezone

class ThirdParty(models.Model):
    """
    Внешний сервис
    (Банк - ППУ - поставщик платежных услуг) или
    (СПИУ - Сервисный поставщик информационных услуг)
    """
    TYPE_CHOICES = [("Bank", "Банк"), ("Service", "Сервис")]
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, verbose_name="Тип сервиса")
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Код сервиса",
        help_text="Например, sber, tbank"
    )
    name = models.CharField(max_length=50, verbose_name="Название сервиса")
    description = models.TextField(max_length=512)

    class Meta:
        verbose_name = "Внешний сервис"
        verbose_name_plural = "Внешние сервисы"

    def __str__(self):
        return f"{self.name}: ({self.code})"

class Company(models.Model):
    """
    Организации, которые пользуются сервисом EveryPay для получения банковских данных.
    Компания владеет счетами - если удалить компанию, удалятся все её счета.
    """
    name = models.CharField(max_length=255, verbose_name="Название компании")
    inn = models.CharField(
        max_length=12,
        unique=True,
        verbose_name="ИНН компании",
        help_text="Состоит из 12 цифр"
    )

    class Meta:
        verbose_name = "Компания"
        verbose_name_plural = "Компании"

    def __str__(self):
        return self.name

class Account(models.Model):
    """
    Счёт, открытый в конкретном банке для конкретной компании.
    Счет нельзя удалить, пока существует банк, к которому он привязан.
    """
    STATUS_CHOICES = [
        ("Enabled", "Активен"),
        ("Disabled", "Закрыт"),
        ("Deleted", "Удалён"),
    ]
    TYPE_CHOICES = [
        ("Business", "Юридическое лицо"),
        ("Personal", "Физическое лицо"),
    ]
    SUBTYPE_CHOICES = [
        ("CurrentAccount", "Расчётный"),
        ("Savings", "Сберегательный"),
        ("Loan", "Кредитный"),
    ]
    account_id = models.UUIDField(unique=True, default=uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="accounts")
    bank = models.ForeignKey(ThirdParty, on_delete=models.PROTECT, related_name="accounts")
    currency = models.CharField(
        max_length=3,
        default="RUB",
        verbose_name="Валюта",
        help_text="Код валюты по ISO 4217 (RUB, USD, EUR)"
    )
    account_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        verbose_name="Тип счета",
        help_text="Физ/Юр лица"
    )
    account_sub_type = models.CharField(max_length=30, choices=SUBTYPE_CHOICES, verbose_name="Подтип счета")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Enabled")
    bban = models.CharField(
        max_length=34,
        blank=True,
        verbose_name="Номер счёта (Basic Bank Account Number)",
        help_text="Расчетный счет, обычно 20 цифр"
    )
    status_update_datetime = models.DateTimeField(auto_now=True)
    registration_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Счёт"
        verbose_name_plural = "Счета"

    def __str__(self):
        return f"{self.bank.name} — {self.company.name}"

class StatementRequest(models.Model):
    """
    Создаётся, когда клиент запрашивает выписку по счёту за период.
    Статус: первые 30 секунд после создания отдаёт Processing,
    потом автоматически становится Ready.
    Создает имитацию асинхронной обработку.
    """
    statement_id = models.UUIDField(unique=True, default=uuid4, editable=False)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="statement_requests")
    created_at = models.DateTimeField(auto_now_add=True)
    from_booking_date_time = models.DateTimeField()
    to_booking_date_time = models.DateTimeField()

    class Meta:
        verbose_name = "Выписка"
        verbose_name_plural = "Выписки"

    @property
    def status(self):
        if timezone.now() - self.created_at >= timedelta(seconds=30):
            return "Ready"
        return "Processing"

class Transaction(models.Model):
    """
    Транзакция внутри выписки.
    Привязана не к счёту напрямую, а к выписке (StatementRequest).
    Если приход - заполняется плательщик, если расход - получатель.
    """
    INDICATOR_CHOICES = [
        ("Credit", "Приход"),
        ("Debit", "Расход")
    ]
    STATUS_CHOICES = [
        ("Booked", "Проведена"),
        ("Pending", "Ожидает")
    ]
    transaction_id = models.UUIDField(unique=True, default=uuid4, editable=False)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="transactions")
    credit_debit_indicator = models.CharField(
        max_length=6,
        choices=INDICATOR_CHOICES,
        verbose_name="Тип транзакции"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Booked")
    booking_date_time = models.DateTimeField(verbose_name="Дата транзакции")
    amount = models.DecimalField(max_digits=19, decimal_places=2, verbose_name="Сумма транзакции")
    value_date_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата, когда деньги становятся доступны"
    )
    description = models.CharField(max_length=300, blank=True, verbose_name="Назначение платежа")
    debtor_name = models.CharField(max_length=200, blank=True, verbose_name="Название плательщика")
    debtor_account = models.CharField(max_length=34, blank=True, verbose_name="Номер счета плательщика")
    creditor_name = models.CharField(max_length=200, blank=True, verbose_name="Название получателя")
    creditor_account = models.CharField(max_length=34, blank=True, verbose_name="Номер счета получателя")
    currency = models.CharField(
        max_length=3,
        default="RUB",
        verbose_name="Валюта",
        help_text="Код валюты по ISO 4217 (RUB, USD, EUR)"
    )
    document_number = models.CharField(
        max_length=6,
        blank=True,
        verbose_name="Номер платежного поручения",
        help_text="Обычно 6 цифр (может быть другой банковский документ)"
    )
    debtor_bic = models.CharField(
        max_length=11,
        blank=True,
        verbose_name="БИК плательщика",
        help_text="Обычно 11 цифр"
    )
    creditor_bic = models.CharField(
        max_length=11,
        blank=True,
        verbose_name="БИК получателя",
        help_text="Обычно 11 цифр"
    )
    tax_uip = models.CharField(
        max_length=25,
        blank=True,
        verbose_name="Уникальный идентификатор платежа",
        help_text="Уникален в пределах одного платежа. Обычно 22 символа. используется для платежей в бюджет"
    )
    tax_kbk = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Код бюджетной классификации",
        help_text="Обычно 20 цифр. Определяет вид налога"
    )
    tax_oktmo = models.CharField(
        max_length=11,
        blank=True,
        verbose_name="Код территории по ОКТМО",
        help_text="Муниципальное образование, куда идет платеж"
    )

    class Meta:
        verbose_name = "Транзакция"
        verbose_name_plural = "Транзакции"
        ordering = ["-booking_date_time"]

    def __str__(self):
        sign = "+" if self.credit_debit_indicator == "Credit" else "-"
        return f"{sign}{self.amount} / {self.description or '-'}"