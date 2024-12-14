from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class DebtAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    balance = models.DecimalField(max_digits=10, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    minimum_payment = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    debt_type = models.CharField(max_length=50, choices=[
        ('CREDIT_CARD', 'Credit Card'),
        ('STUDENT_LOAN', 'Student Loan'),
        ('MORTGAGE', 'Mortgage'),
        ('PERSONAL_LOAN', 'Personal Loan'),
        ('OTHER', 'Other'),
    ])
    
    def __str__(self):
        return f"{self.name} - ${self.balance}"

class Income(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    source = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    frequency = models.CharField(max_length=20, choices=[
        ('WEEKLY', 'Weekly'),
        ('BIWEEKLY', 'Bi-weekly'),
        ('MONTHLY', 'Monthly'),
        ('ANNUAL', 'Annual'),
    ])
    
    def __str__(self):
        return f"{self.source}: ${self.amount} ({self.frequency})"

class DebtPaymentPlan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    debt_account = models.ForeignKey(DebtAccount, on_delete=models.CASCADE)
    target_payment = models.DecimalField(max_digits=10, decimal_places=2)
    strategy = models.CharField(max_length=20, choices=[
        ('AVALANCHE', 'Debt Avalanche'),
        ('SNOWBALL', 'Debt Snowball'),
    ])
    estimated_payoff_date = models.DateField() 