from django.contrib import admin
from .models import FinancialGoal


@admin.register(FinancialGoal)
class FinancialGoalAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'target_amount', 'current_amount', 'deadline', 'priority', 'user')
    list_filter = ('category', 'priority')
    search_fields = ('title',)
