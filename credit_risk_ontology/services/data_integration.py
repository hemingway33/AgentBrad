"""
Multi-Source Data Integration Service.

Implements the diagram's "多源数据合规采集、融合为一" concept:
- Collects data from 15 dimensions
- Normalizes and validates data
- Computes derived indicators
- Feeds data into the ontology graph
"""

from decimal import Decimal
from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone

from credit_risk_ontology.models.entities import Enterprise
from credit_risk_ontology.models.data_sources import (
    TaxFinancialReport, CreditReport, SettlementRecord,
    OutputInvoice, InputInvoice, ERPLogisticsRecord,
    LegalLitigation, AssetClue, MovablePropertyRegistration,
    BusinessChange, NewsSentiment, GoodsServiceTransaction,
    BillPayment, DefaultBlacklist, BiddingRecord,
)
from credit_risk_ontology.models.indicators import (
    IndicatorCategory, IndicatorDefinition, IndicatorValue,
)


class DataIntegrationService:
    """
    Integrates multi-source data into unified indicator values.
    15 dimensions, 48 categories, 1800+ indicators.
    """

    @staticmethod
    def collect_enterprise_data(enterprise_id: int) -> dict:
        """
        Collect all data source records for an enterprise
        and return a unified data dictionary.
        """
        enterprise = Enterprise.objects.get(id=enterprise_id)
        data = {
            'enterprise': {
                'id': enterprise.id,
                'name': enterprise.name,
                'type': enterprise.enterprise_type,
                'industry': enterprise.industry_name,
                'registered_capital': float(enterprise.registered_capital or 0),
            },
        }

        # Tax & Financial
        tax_reports = TaxFinancialReport.objects.filter(enterprise=enterprise)
        latest_tax = tax_reports.order_by('-filing_date').first()
        if latest_tax:
            data['tax_financial'] = {
                'revenue': float(latest_tax.revenue or 0),
                'net_profit': float(latest_tax.net_profit or 0),
                'total_assets': float(latest_tax.total_assets or 0),
                'total_liabilities': float(latest_tax.total_liabilities or 0),
                'tax_credit_rating': latest_tax.tax_credit_rating,
                'is_abnormal': latest_tax.is_abnormal,
                'report_count': tax_reports.count(),
            }

        # Credit Report
        credit_reports = CreditReport.objects.filter(enterprise=enterprise)
        latest_credit = credit_reports.order_by('-report_date').first()
        if latest_credit:
            data['credit_report'] = {
                'credit_amount': float(latest_credit.credit_amount),
                'loan_balance': float(latest_credit.loan_balance),
                'historical_overdue_count': latest_credit.historical_overdue_count,
                'historical_overdue_amount': float(latest_credit.historical_overdue_amount),
                'recent_inquiry_count': latest_credit.recent_inquiry_count,
                'recent_loan_count': latest_credit.recent_loan_count,
                'average_loan_rate': latest_credit.average_loan_rate,
                'debt_to_income_ratio': latest_credit.debt_to_income_ratio,
            }

        # Settlement flow
        settlements = SettlementRecord.objects.filter(enterprise=enterprise)
        if settlements.exists():
            inflows = settlements.filter(direction='INFLOW').aggregate(
                total=Sum('transaction_amount'), count=Count('id'),
            )
            outflows = settlements.filter(direction='OUTFLOW').aggregate(
                total=Sum('transaction_amount'), count=Count('id'),
            )
            data['settlement'] = {
                'operating_income': float(inflows['total'] or 0),
                'operating_expenses': float(outflows['total'] or 0),
                'inflow_count': inflows['count'],
                'outflow_count': outflows['count'],
            }

        # Invoices
        output_invoices = OutputInvoice.objects.filter(enterprise=enterprise)
        input_invoices = InputInvoice.objects.filter(enterprise=enterprise)
        if output_invoices.exists() or input_invoices.exists():
            out_total = output_invoices.aggregate(total=Sum('total_amount'))['total'] or 0
            in_total = input_invoices.aggregate(total=Sum('total_amount'))['total'] or 0
            data['invoices'] = {
                'output_total': float(out_total),
                'input_total': float(in_total),
                'output_count': output_invoices.count(),
                'input_count': input_invoices.count(),
            }

        # Legal
        legal_cases = LegalLitigation.objects.filter(enterprise=enterprise)
        if legal_cases.exists():
            enforcement = legal_cases.filter(case_type='ENFORCEMENT')
            data['legal'] = {
                'total_case_count': legal_cases.count(),
                'enforcement_case_count': enforcement.count(),
                'defendant_count': legal_cases.filter(enterprise_role='DEFENDANT').count(),
                'loan_litigation_amount': float(
                    legal_cases.filter(
                        case_type='CIVIL',
                        counterparty_name__icontains='银行',
                    ).aggregate(total=Sum('subject_amount'))['total'] or 0
                ),
                'total_subject_amount': float(
                    legal_cases.aggregate(total=Sum('subject_amount'))['total'] or 0
                ),
            }

        # Business changes
        changes = BusinessChange.objects.filter(enterprise=enterprise)
        if changes.exists():
            two_years_ago = timezone.now().date().replace(
                year=timezone.now().year - 2,
            )
            data['business_changes'] = {
                'total_changes': changes.count(),
                'anomaly_count': changes.filter(is_anomaly=True).count(),
                'legal_rep_changes_2y': changes.filter(
                    change_type='LEGAL_REP',
                    change_date__gte=two_years_ago,
                ).count(),
            }

        # News & Sentiment
        news = NewsSentiment.objects.filter(enterprise=enterprise)
        if news.exists():
            data['news'] = {
                'total_count': news.count(),
                'negative_count': news.filter(sentiment='NEGATIVE').count(),
                'critical_negative_count': news.filter(sentiment='CRITICAL').count(),
                'avg_sentiment_score': news.aggregate(
                    avg=Avg('sentiment_score'),
                )['avg'] or 0,
            }

        # Default blacklist
        defaults = DefaultBlacklist.objects.filter(enterprise=enterprise)
        if defaults.exists():
            data['blacklist'] = {
                'active_default_count': defaults.filter(is_resolved=False).count(),
                'total_default_count': defaults.count(),
                'default_types': list(
                    defaults.filter(is_resolved=False)
                    .values_list('default_type', flat=True)
                    .distinct()
                ),
                'lost_trust_count': defaults.filter(
                    default_type='TRUST_BREACH', is_resolved=False,
                ).count(),
            }

        # Bidding records
        bids = BiddingRecord.objects.filter(enterprise=enterprise)
        if bids.exists():
            data['bidding'] = {
                'total_bids': bids.count(),
                'won_count': bids.filter(result='WON').count(),
                'total_winning_amount': float(
                    bids.filter(result='WON').aggregate(
                        total=Sum('winning_amount'),
                    )['total'] or 0
                ),
            }

        return data

    @staticmethod
    def compute_derived_indicators(enterprise_id: int, data: dict) -> dict:
        """
        Compute derived indicators from collected raw data.
        Returns indicator code -> value mapping.
        """
        indicators = {}

        # Financial indicators
        tax = data.get('tax_financial', {})
        if tax:
            total_assets = tax.get('total_assets', 0)
            total_liabilities = tax.get('total_liabilities', 0)
            revenue = tax.get('revenue', 0)
            net_profit = tax.get('net_profit', 0)

            if total_assets > 0:
                indicators['debt_to_asset_ratio'] = total_liabilities / total_assets
                indicators['net_profit_margin'] = net_profit / revenue if revenue > 0 else 0
                indicators['asset_turnover'] = revenue / total_assets

            equity = total_assets - total_liabilities
            if equity > 0:
                indicators['debt_to_equity'] = total_liabilities / equity
                indicators['roe'] = net_profit / equity

        # Credit indicators
        credit = data.get('credit_report', {})
        if credit:
            loan_balance = credit.get('loan_balance', 0)
            credit_amount = credit.get('credit_amount', 0)
            if credit_amount > 0:
                indicators['credit_utilization'] = loan_balance / credit_amount

        # Settlement indicators
        settlement = data.get('settlement', {})
        if settlement:
            income = settlement.get('operating_income', 0)
            expenses = settlement.get('operating_expenses', 0)
            if income > 0:
                indicators['operating_cash_flow_ratio'] = (income - expenses) / income

        # Invoice indicators
        invoices = data.get('invoices', {})
        if invoices:
            out_total = invoices.get('output_total', 0)
            in_total = invoices.get('input_total', 0)
            if in_total > 0:
                indicators['invoice_output_input_ratio'] = out_total / in_total

        return indicators

    @staticmethod
    def save_indicator_values(enterprise_id: int, indicators: dict):
        """Persist computed indicator values to the database."""
        enterprise = Enterprise.objects.get(id=enterprise_id)
        for code, value in indicators.items():
            indicator_def = IndicatorDefinition.objects.filter(code=code).first()
            if indicator_def:
                IndicatorValue.objects.create(
                    enterprise=enterprise,
                    indicator=indicator_def,
                    numeric_value=value,
                    evaluated_at=timezone.now(),
                )
