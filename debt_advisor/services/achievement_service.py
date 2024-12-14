from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Sum, F
from ..models import Achievement, UserAchievement, UserProgress
from debt_manager.models import DebtAccount, DebtPaymentPlan
from budget_tracker.models import Expense, Category

class AchievementService:
    def __init__(self, user):
        self.user = user
        self.progress = UserProgress.objects.get_or_create(user=user)[0]

    def check_achievements(self):
        """Check all possible achievements"""
        achievements = []
        
        # Debt Reduction Achievements
        achievements.extend(self._check_debt_reduction())
        
        # Saving Achievements
        achievements.extend(self._check_savings())
        
        # Budgeting Achievements
        achievements.extend(self._check_budgeting())
        
        # Engagement Achievements
        achievements.extend(self._check_engagement())
        
        return achievements

    def _check_debt_reduction(self):
        """Check debt-related achievements"""
        achievements = []
        total_debt = DebtAccount.objects.filter(user=self.user).aggregate(
            total=Sum('balance'))['total'] or Decimal('0')
        
        # First Debt Payment
        if self._has_made_payment():
            achievements.append(self._award_achievement('FIRST_PAYMENT'))
        
        # Debt Reduction Milestones
        debt_reduction = self._calculate_debt_reduction()
        if debt_reduction >= 1000:
            achievements.append(self._award_achievement('REDUCE_1000'))
        if debt_reduction >= 5000:
            achievements.append(self._award_achievement('REDUCE_5000'))
        
        # Debt-Free Achievement
        if total_debt == 0 and self._had_previous_debt():
            achievements.append(self._award_achievement('DEBT_FREE'))
        
        return [a for a in achievements if a]

    def _check_savings(self):
        """Check savings-related achievements"""
        achievements = []
        savings = self._calculate_savings()
        
        # Emergency Fund Achievements
        if savings >= 1000:
            achievements.append(self._award_achievement('EMERGENCY_FUND_1000'))
        if savings >= 5000:
            achievements.append(self._award_achievement('EMERGENCY_FUND_5000'))
        
        return [a for a in achievements if a]

    def _check_budgeting(self):
        """Check budgeting-related achievements"""
        achievements = []
        
        # Budget Creation
        if Category.objects.filter(user=self.user).exists():
            achievements.append(self._award_achievement('FIRST_BUDGET'))
        
        # Under Budget Achievement
        if self._stayed_under_budget():
            achievements.append(self._award_achievement('UNDER_BUDGET_MONTH'))
        
        return [a for a in achievements if a]

    def _award_achievement(self, achievement_code):
        """Award an achievement if not already earned"""
        achievement = Achievement.objects.get(name=achievement_code)
        user_achievement, created = UserAchievement.objects.get_or_create(
            user=self.user,
            achievement=achievement
        )
        if created:
            return achievement
        return None 