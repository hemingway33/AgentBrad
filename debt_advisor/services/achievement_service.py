from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from ..models import Achievement, UserAchievement, UserProgress, ConversationSession
from debt_manager.models import DebtAccount, DebtPaymentPlan
from budget_tracker.models import Expense, Category
from goals.models import FinancialGoal


class AchievementService:
    def __init__(self, user):
        self.user = user
        self.progress = UserProgress.objects.get_or_create(user=user)[0]

    def check_achievements(self):
        """Check all possible achievements"""
        achievements = []

        achievements.extend(self._check_debt_reduction())
        achievements.extend(self._check_savings())
        achievements.extend(self._check_budgeting())
        achievements.extend(self._check_engagement())

        return achievements

    def _check_debt_reduction(self):
        """Check debt-related achievements"""
        achievements = []
        total_debt = DebtAccount.objects.filter(user=self.user).aggregate(
            total=Sum('balance'))['total'] or Decimal('0')

        if self._has_made_payment():
            achievements.append(self._award_achievement('FIRST_PAYMENT'))

        debt_reduction = self._calculate_debt_reduction()
        if debt_reduction >= 1000:
            achievements.append(self._award_achievement('REDUCE_1000'))
        if debt_reduction >= 5000:
            achievements.append(self._award_achievement('REDUCE_5000'))

        if total_debt == 0 and self._had_previous_debt():
            achievements.append(self._award_achievement('DEBT_FREE'))

        return [a for a in achievements if a]

    def _check_savings(self):
        """Check savings-related achievements"""
        achievements = []
        savings = self._calculate_savings()

        if savings >= 1000:
            achievements.append(self._award_achievement('EMERGENCY_FUND_1000'))
        if savings >= 5000:
            achievements.append(self._award_achievement('EMERGENCY_FUND_5000'))

        return [a for a in achievements if a]

    def _check_budgeting(self):
        """Check budgeting-related achievements"""
        achievements = []

        if Category.objects.filter(user=self.user).exists():
            achievements.append(self._award_achievement('FIRST_BUDGET'))

        if self._stayed_under_budget():
            achievements.append(self._award_achievement('UNDER_BUDGET_MONTH'))

        return [a for a in achievements if a]

    def _check_engagement(self):
        """Check engagement-related achievements"""
        achievements = []

        session_count = ConversationSession.objects.filter(user=self.user).count()
        if session_count >= 1:
            achievements.append(self._award_achievement('FIRST_SESSION'))
        if session_count >= 10:
            achievements.append(self._award_achievement('TEN_SESSIONS'))

        return [a for a in achievements if a]

    def _has_made_payment(self):
        """Check if user has any payment plans (indicates they've started paying)"""
        return DebtPaymentPlan.objects.filter(user=self.user).exists()

    def _calculate_debt_reduction(self):
        """Calculate total debt reduced based on payment plans vs current balance"""
        plans = DebtPaymentPlan.objects.filter(user=self.user).select_related('debt_account')
        total_reduction = Decimal('0')
        for plan in plans:
            paid = plan.target_payment - plan.debt_account.minimum_payment
            if paid > 0:
                total_reduction += paid
        return total_reduction

    def _had_previous_debt(self):
        """Check if user ever had debt accounts"""
        return DebtAccount.objects.filter(user=self.user).exists()

    def _calculate_savings(self):
        """Calculate total savings from financial goals"""
        savings_goals = FinancialGoal.objects.filter(
            user=self.user,
            category__in=['EMERGENCY_FUND', 'SAVINGS']
        )
        return sum(goal.current_amount for goal in savings_goals)

    def _stayed_under_budget(self):
        """Check if user stayed under budget for all categories last month"""
        categories = Category.objects.filter(user=self.user)
        if not categories.exists():
            return False

        last_month = timezone.now() - timedelta(days=30)
        for category in categories:
            spent = Expense.objects.filter(
                user=self.user,
                category=category,
                date__gte=last_month
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

            if spent > category.budget_limit:
                return False
        return True

    def _award_achievement(self, achievement_code):
        """Award an achievement if not already earned"""
        try:
            achievement = Achievement.objects.get(name=achievement_code)
        except Achievement.DoesNotExist:
            return None

        user_achievement, created = UserAchievement.objects.get_or_create(
            user=self.user,
            achievement=achievement
        )
        if created:
            return achievement
        return None
