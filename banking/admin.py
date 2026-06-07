from django.contrib import admin
from .models import ThirdParty, Company, Account, Balance, StatementRequest, Transaction

class StatementInline(admin.TabularInline):
    model = StatementRequest
    extra = 0
    fields = ("statement_id", "created_at", "from_booking_date_time", "to_booking_date_time")
    readonly_fields = ("statement_id", "created_at")
    show_change_link = True

class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 1
    fields = (
        "booking_date_time", "credit_debit_indicator",
        "amount", "currency", "status", "description",
    )
    show_change_link = True

class BalanceInline(admin.TabularInline):
    model = Balance
    extra = 1
    fields = ("amount", "currency", "credit_debit_indicator", "type", "datetime")

@admin.register(ThirdParty)
class ThirdPartyAdmin(admin.ModelAdmin):
    list_display = ("type", "code", "name", "description")
    search_fields = ("name", "code")

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "inn")
    search_fields = ("name", "inn")

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("company", "bank", "currency", "account_type", "account_sub_type", "status", "bban")
    list_filter = ("status", "account_type", "bank")
    search_fields = ("bban", "company__name")
    readonly_fields = ("account_id",)
    inlines = [BalanceInline, StatementInline]

@admin.register(StatementRequest)
class StatementRequestAdmin(admin.ModelAdmin):
    list_display = ("statement_id", "account", "created_at", "status_display")
    readonly_fields = ("statement_id", "created_at")
    inlines = [TransactionInline]

    def status_display(self, obj):
        return obj.status

    status_display.short_description = "Статус"

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "booking_date_time", "statement", "credit_debit_indicator",
        "amount", "currency", "status"
    )
    list_filter = ("credit_debit_indicator", "status")
    search_fields = ("debtor_name", "creditor_name")
    readonly_fields = ("transaction_id",)
    fieldsets = (
        ("Основное", {
            "fields": ("transaction_id", "statement", "credit_debit_indicator", "status"),
        }),
        ("Сумма и дата", {
            "fields": ("amount", "currency", "booking_date_time", "value_date_time", "document_number", "description"),
        }),
        ("Плательщик", {
            "fields": ("debtor_name", "debtor_account", "debtor_bic"),
            "classes": ("collapse",),
        }),
        ("Получатель", {
            "fields": ("creditor_name", "creditor_account", "creditor_bic"),
            "classes": ("collapse",),
        }),
        ("Налоговые реквизиты", {
            "fields": ("tax_uip", "tax_kbk", "tax_oktmo"),
            "classes": ("collapse",),
        }),
    )