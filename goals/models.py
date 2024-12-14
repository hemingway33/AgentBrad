from django.db import models
from django.contrib.auth.models import User

class FinancialGoal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    target_amount = models.DecimalField(max_digits=10, decimal_places=2)
    current_amount = models.DecimalField(max_digits=10, decimal_places=2)
    deadline = models.DateField()
    priority = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    category = models.CharField(max_length=50, choices=[
        ('DEBT_PAYOFF', 'Debt Payoff'),
        ('EMERGENCY_FUND', 'Emergency Fund'),
        ('SAVINGS', 'Savings'),
        ('INVESTMENT', 'Investment'),
    ])
    
    def progress_percentage(self):
        return (self.current_amount / self.target_amount) * 100 