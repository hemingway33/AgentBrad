from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

class Account(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=50, choices=[
        ('ASSET', 'Asset'),
        ('LIABILITY', 'Liability'),
        ('EQUITY', 'Equity'),
        ('REVENUE', 'Revenue'),
        ('EXPENSE', 'Expense'),
    ])
    account_number = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.account_number} - {self.name}"

class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    reference_number = models.CharField(max_length=50)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('POSTED', 'Posted'),
        ('RECONCILED', 'Reconciled'),
    ], default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=50, choices=[
        ('MANUAL', 'Manual Entry'),
        ('QUICKBOOKS', 'QuickBooks'),
        ('IMPORT', 'File Import'),
    ], default='MANUAL')
    
    def __str__(self):
        return f"{self.date} - {self.reference_number}"

class TransactionLine(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    description = models.CharField(max_length=200)
    debit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    credit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def __str__(self):
        return f"{self.account.name}: D{self.debit_amount} C{self.credit_amount}"

class QuickBooksIntegration(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    access_token = models.TextField()
    refresh_token = models.TextField()
    realm_id = models.CharField(max_length=50)
    last_sync = models.DateTimeField(null=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"QuickBooks Integration for {self.user.username}"

class FinancialStatement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    statement_type = models.CharField(max_length=50, choices=[
        ('BALANCE_SHEET', 'Balance Sheet'),
        ('INCOME_STATEMENT', 'Income Statement'),
        ('CASH_FLOW', 'Cash Flow Statement'),
    ])
    period_start = models.DateField()
    period_end = models.DateField()
    generated_at = models.DateTimeField(auto_now_add=True)
    data = models.JSONField()  # Stores the statement data in JSON format
    
    class Meta:
        ordering = ['-period_end']
    
    def __str__(self):
        return f"{self.statement_type} ({self.period_start} to {self.period_end})" 