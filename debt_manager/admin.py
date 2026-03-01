from django.contrib import admin
from .models import DebtAccount, Income, DebtPaymentPlan


@admin.register(DebtAccount)
class DebtAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'debt_type', 'balance', 'interest_rate', 'minimum_payment', 'due_date', 'user')
    list_filter = ('debt_type',)
    search_fields = ('name',)


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ('source', 'amount', 'frequency', 'user')
    list_filter = ('frequency',)


@admin.register(DebtPaymentPlan)
class DebtPaymentPlanAdmin(admin.ModelAdmin):
    list_display = ('debt_account', 'strategy', 'target_payment', 'estimated_payoff_date', 'user')
    list_filter = ('strategy',)
