from django.contrib import admin
from .models import Account, Transaction, TransactionLine, QuickBooksIntegration, FinancialStatement


class TransactionLineInline(admin.TabularInline):
    model = TransactionLine
    extra = 2


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('account_number', 'name', 'account_type', 'is_active', 'user')
    list_filter = ('account_type', 'is_active')
    search_fields = ('name', 'account_number')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'date', 'status', 'source', 'user')
    list_filter = ('status', 'source', 'date')
    search_fields = ('reference_number', 'description')
    inlines = [TransactionLineInline]


@admin.register(QuickBooksIntegration)
class QuickBooksIntegrationAdmin(admin.ModelAdmin):
    list_display = ('user', 'realm_id', 'is_active', 'last_sync')


@admin.register(FinancialStatement)
class FinancialStatementAdmin(admin.ModelAdmin):
    list_display = ('statement_type', 'period_start', 'period_end', 'generated_at', 'user')
    list_filter = ('statement_type',)
