from decimal import Decimal
from django.db.models import Sum, F, Q
from datetime import datetime, timedelta
from .models import Account, Transaction, TransactionLine


class BusinessMetrics:
    def __init__(self, user):
        self.user = user

    def quick_ratio(self):
        """Calculate Quick Ratio (Acid-Test Ratio)"""
        current_assets = self._get_account_balance('ASSET', keywords=['cash', 'receivable'])
        inventory = self._get_account_balance('ASSET', keywords=['inventory'])
        current_liabilities = self._get_account_balance('LIABILITY')

        if current_liabilities == 0:
            return None
        return float((current_assets - inventory) / current_liabilities)

    def current_ratio(self):
        """Calculate Current Ratio"""
        current_assets = self._get_account_balance('ASSET')
        current_liabilities = self._get_account_balance('LIABILITY')

        if current_liabilities == 0:
            return None
        return float(current_assets / current_liabilities)

    def operating_cash_flow_ratio(self):
        """Calculate Operating Cash Flow Ratio"""
        operating_cash_flow = self._calculate_operating_cash_flow()
        current_liabilities = self._get_account_balance('LIABILITY')

        if current_liabilities == 0:
            return None
        return float(operating_cash_flow / current_liabilities)

    def gross_profit_margin(self):
        """Calculate Gross Profit Margin"""
        revenue = self._get_account_balance('REVENUE')
        cogs = self._get_account_balance('EXPENSE', keywords=['cogs', 'cost of goods'])

        if revenue == 0:
            return None
        return float(((revenue - cogs) / revenue) * 100)

    def debt_to_equity_ratio(self):
        """Calculate Debt to Equity Ratio"""
        total_liabilities = self._get_account_balance('LIABILITY')
        total_equity = self._get_account_balance('EQUITY')

        if total_equity == 0:
            return None
        return float(total_liabilities / total_equity)

    def accounts_receivable_turnover(self):
        """Calculate Accounts Receivable Turnover"""
        net_credit_sales = self._get_credit_sales()
        avg_accounts_receivable = self._get_average_receivables()

        if avg_accounts_receivable == 0:
            return None
        return float(net_credit_sales / avg_accounts_receivable)

    def _get_account_balance(self, account_type, keywords=None):
        """Get aggregate balance for accounts of a given type, optionally filtered by name keywords"""
        query = Account.objects.filter(
            user=self.user,
            account_type=account_type,
            is_active=True
        )
        if keywords:
            name_q = Q()
            for keyword in keywords:
                name_q |= Q(name__icontains=keyword)
            query = query.filter(name_q)

        return query.aggregate(
            balance=Sum(
                F('transactionline__debit_amount') - F('transactionline__credit_amount')
            )
        )['balance'] or Decimal('0')

    def _calculate_operating_cash_flow(self):
        """Calculate operating cash flow from cash-related revenue and expense accounts"""
        revenue = self._get_account_balance('REVENUE')
        operating_expenses = self._get_account_balance('EXPENSE')
        return revenue - operating_expenses

    def _get_credit_sales(self):
        """Calculate net credit sales from revenue transaction lines"""
        return TransactionLine.objects.filter(
            account__user=self.user,
            account__account_type='REVENUE',
            account__is_active=True,
        ).aggregate(
            total=Sum('credit_amount')
        )['total'] or Decimal('0')

    def _get_average_receivables(self):
        """Calculate average accounts receivable balance"""
        receivable_accounts = Account.objects.filter(
            user=self.user,
            account_type='ASSET',
            is_active=True,
            name__icontains='receivable'
        )
        balance = receivable_accounts.aggregate(
            total=Sum(
                F('transactionline__debit_amount') - F('transactionline__credit_amount')
            )
        )['total'] or Decimal('0')
        return balance

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
