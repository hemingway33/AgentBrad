from decimal import Decimal
from django.db.models import Sum, F, Q
from datetime import datetime, timedelta
from .models import Account, Transaction, TransactionLine

class BusinessMetrics:
    def __init__(self, user):
        self.user = user

    def quick_ratio(self):
        """Calculate Quick Ratio (Acid-Test Ratio)"""
        current_assets = self._get_account_balance('ASSET', ['cash', 'receivable'])
        inventory = self._get_account_balance('ASSET', ['inventory'])
        current_liabilities = self._get_account_balance('LIABILITY', ['current'])
        
        if current_liabilities == 0:
            return None
        return (current_assets - inventory) / current_liabilities

    def current_ratio(self):
        """Calculate Current Ratio"""
        current_assets = self._get_account_balance('ASSET', ['current'])
        current_liabilities = self._get_account_balance('LIABILITY', ['current'])
        
        if current_liabilities == 0:
            return None
        return current_assets / current_liabilities

    def operating_cash_flow_ratio(self):
        """Calculate Operating Cash Flow Ratio"""
        operating_cash_flow = self._calculate_operating_cash_flow()
        current_liabilities = self._get_account_balance('LIABILITY', ['current'])
        
        if current_liabilities == 0:
            return None
        return operating_cash_flow / current_liabilities

    def gross_profit_margin(self):
        """Calculate Gross Profit Margin"""
        revenue = self._get_account_balance('REVENUE')
        cogs = self._get_account_balance('EXPENSE', ['cogs'])
        
        if revenue == 0:
            return None
        return ((revenue - cogs) / revenue) * 100

    def debt_to_equity_ratio(self):
        """Calculate Debt to Equity Ratio"""
        total_liabilities = self._get_account_balance('LIABILITY')
        total_equity = self._get_account_balance('EQUITY')
        
        if total_equity == 0:
            return None
        return total_liabilities / total_equity

    def accounts_receivable_turnover(self):
        """Calculate Accounts Receivable Turnover"""
        net_credit_sales = self._get_credit_sales()
        avg_accounts_receivable = self._get_average_receivables()
        
        if avg_accounts_receivable == 0:
            return None
        return net_credit_sales / avg_accounts_receivable

    def _get_account_balance(self, account_type, tags=None):
        query = Account.objects.filter(
            user=self.user,
            account_type=account_type,
            is_active=True
        )
        if tags:
            query = query.filter(tags__name__in=tags)
        
        return query.aggregate(
            balance=Sum(
                F('transactionline__debit_amount') - F('transactionline__credit_amount')
            )
        )['balance'] or Decimal('0')

    def get_all_metrics(self):
        """Return all calculated metrics"""
        return {
            'quick_ratio': self.quick_ratio(),
            'current_ratio': self.current_ratio(),
            'operating_cash_flow_ratio': self.operating_cash_flow_ratio(),
            'gross_profit_margin': self.gross_profit_margin(),
            'debt_to_equity_ratio': self.debt_to_equity_ratio(),
            'accounts_receivable_turnover': self.accounts_receivable_turnover(),
        } 