"""
Credit Risk Rules - Concrete rule implementations for the reasoning engine.

Implements rules across 5 assessment dimensions:
1. Anti-Fraud (反欺诈) - Shell company detection, transaction anomalies
2. KYB (Know Your Business) - Enterprise identity verification
3. Risk Rating (风险评级) - Multi-dimensional risk scoring
4. Credit Assessment (授信测额) - Credit limit recommendation
5. Post-Loan Monitoring (贷后监控) - Ongoing risk monitoring

Each rule is a function: (ReasoningContext, RuleDefinition) -> RuleResult
"""

from .engine import (
    RuleDefinition, RuleResult, RuleStatus, ReasoningContext, AlertSeverity,
)


# ============================================================
# Anti-Fraud Rules (反欺诈)
# ============================================================

def rule_shell_company_detection(ctx: ReasoningContext, rule: RuleDefinition) -> RuleResult:
    """
    Detect shell/packaging company indicators.
    Checks: real office, real employees, real business, tax anomalies.
    """
    shell_data = ctx.data_sources.get('shell_profile', {})
    score = 0.0
    alerts = []
    details = {}

    if not shell_data.get('has_real_office', True):
        score += 25
        alerts.append({
            'severity': 'high',
            'message': 'No verified physical office address',
            'rule': rule.name,
        })

    if not shell_data.get('has_real_employees', True):
        score += 25
        alerts.append({
            'severity': 'high',
            'message': 'No verified employee records (social insurance)',
            'rule': rule.name,
        })

    if not shell_data.get('has_real_business', True):
        score += 30
        alerts.append({
            'severity': 'critical',
            'message': 'No evidence of real business operations',
            'rule': rule.name,
        })

    tax_anomaly = shell_data.get('tax_anomaly_score', 0)
    if tax_anomaly > 0.7:
        score += 20
        alerts.append({
            'severity': 'high',
            'message': f'Tax anomaly score: {tax_anomaly:.2f}',
            'rule': rule.name,
        })

    details['shell_indicators'] = shell_data
    return RuleResult(
        rule_name=rule.name,
        status=RuleStatus.COMPLETED,
        score=min(score, 100),
        alerts=alerts,
        details=details,
    )


def rule_circular_transaction_detection(ctx: ReasoningContext, rule: RuleDefinition) -> RuleResult:
    """
    Detect circular transaction patterns (A->B->C->A).
    Indicates potential fictitious trade or money laundering.
    """
    graph_data = ctx.graph_data
    triangles = graph_data.get('transaction_triangles', [])
    round_trips = graph_data.get('round_trips', [])

    score = 0.0
    alerts = []

    if round_trips:
        score += min(len(round_trips) * 20, 60)
        alerts.append({
            'severity': 'critical',
            'message': f'Detected {len(round_trips)} round-trip transaction patterns',
            'rule': rule.name,
        })

    if triangles:
        score += min(len(triangles) * 10, 40)
        alerts.append({
            'severity': 'high',
            'message': f'Detected {len(triangles)} triangular transaction patterns',
            'rule': rule.name,
        })

    return RuleResult(
        rule_name=rule.name,
        status=RuleStatus.COMPLETED,
        score=min(score, 100),
        alerts=alerts,
        details={
            'round_trips': len(round_trips),
            'triangles': len(triangles),
        },
    )


def rule_invoice_anomaly_detection(ctx: ReasoningContext, rule: RuleDefinition) -> RuleResult:
    """
    Detect invoice anomalies - mismatches between invoices, orders, and logistics.
    Three-way matching: invoice <-> order <-> delivery.
    """
    invoices = ctx.data_sources.get('invoices', {})
    score = 0.0
    alerts = []

    mismatch_rate = invoices.get('three_way_mismatch_rate', 0)
    if mismatch_rate > 0.3:
        score += 40
        alerts.append({
            'severity': 'critical',
            'message': f'Invoice-order-delivery mismatch rate: {mismatch_rate:.1%}',
            'rule': rule.name,
        })
    elif mismatch_rate > 0.1:
        score += 20
        alerts.append({
            'severity': 'warning',
            'message': f'Elevated invoice mismatch rate: {mismatch_rate:.1%}',
            'rule': rule.name,
        })

    # Check for abnormally large invoices
    max_invoice_ratio = invoices.get('max_single_invoice_ratio', 0)
    if max_invoice_ratio > 0.5:
        score += 20
        alerts.append({
            'severity': 'high',
            'message': f'Single invoice exceeds 50% of total: {max_invoice_ratio:.1%}',
            'rule': rule.name,
        })

    # Check for concentration in invoice counterparties
    top_counterparty_share = invoices.get('top_counterparty_share', 0)
    if top_counterparty_share > 0.8:
        score += 15
        alerts.append({
            'severity': 'warning',
            'message': f'Top counterparty share: {top_counterparty_share:.1%}',
            'rule': rule.name,
        })

    return RuleResult(
        rule_name=rule.name,
        status=RuleStatus.COMPLETED,
        score=min(score, 100),
        alerts=alerts,
        details=invoices,
    )


# ============================================================
# KYB Rules (Know Your Business)
# ============================================================

def rule_business_legitimacy(ctx: ReasoningContext, rule: RuleDefinition) -> RuleResult:
    """
    Verify enterprise business legitimacy.
    Checks business registration, tax status, operating history.
    """
    ent = ctx.enterprise_data
    score = 0.0
    alerts = []

    # Check registration age
    years_operating = ent.get('years_operating', 0)
    if years_operating < 1:
        score += 30
        alerts.append({
            'severity': 'high',
            'message': f'Enterprise operating for less than 1 year ({years_operating} years)',
            'rule': rule.name,
        })
    elif years_operating < 3:
        score += 15
        alerts.append({
            'severity': 'warning',
            'message': f'Enterprise relatively new ({years_operating} years)',
            'rule': rule.name,
        })

    # Check business changes
    changes = ctx.data_sources.get('business_changes', {})
    anomaly_count = changes.get('anomaly_count', 0)
    if anomaly_count > 3:
        score += 25
        alerts.append({
            'severity': 'high',
            'message': f'{anomaly_count} business anomalies recorded',
            'rule': rule.name,
        })

    legal_rep_changes = changes.get('legal_rep_changes_2y', 0)
    if legal_rep_changes > 2:
        score += 20
        alerts.append({
            'severity': 'high',
            'message': f'Legal representative changed {legal_rep_changes} times in 2 years',
            'rule': rule.name,
        })

    return RuleResult(
        rule_name=rule.name,
        status=RuleStatus.COMPLETED,
        score=min(score, 100),
        alerts=alerts,
        details={'years_operating': years_operating, 'changes': changes},
    )


def rule_related_party_risk(ctx: ReasoningContext, rule: RuleDefinition) -> RuleResult:
    """
    Assess risk from related party relationships.
    Enterprise relationship graph analysis.
    """
    graph = ctx.graph_data
    score = 0.0
    alerts = []

    # Circular guarantees
    circular_guarantees = graph.get('circular_guarantees', [])
    if circular_guarantees:
        severity_map = {'CRITICAL': 40, 'HIGH': 25, 'MEDIUM': 15, 'LOW': 5}
        for cg in circular_guarantees:
            score += severity_map.get(cg.get('severity', 'LOW'), 5)
        alerts.append({
            'severity': 'critical',
            'message': f'Detected {len(circular_guarantees)} circular guarantee chains',
            'rule': rule.name,
        })

    # Related enterprise execution amount
    related_execution = graph.get('related_execution_amount', 0)
    if related_execution > 10_000_000:
        score += 20
        alerts.append({
            'severity': 'high',
            'message': f'Related enterprise execution amount: ¥{related_execution:,.0f}',
            'rule': rule.name,
        })

    # Related party transaction concentration
    related_txn_share = graph.get('related_party_transaction_share', 0)
    if related_txn_share > 0.5:
        score += 15
        alerts.append({
            'severity': 'warning',
            'message': f'Related party transaction share: {related_txn_share:.1%}',
            'rule': rule.name,
        })

    return RuleResult(
        rule_name=rule.name,
        status=RuleStatus.COMPLETED,
        score=min(score, 100),
        alerts=alerts,
        details=graph,
    )


# ============================================================
# Risk Rating Rules (风险评级)
# ============================================================

def rule_financial_health(ctx: ReasoningContext, rule: RuleDefinition) -> RuleResult:
    """
    Assess financial health from tax and financial reports.
    Key metrics: profitability, liquidity, leverage.
    """
    indicators = ctx.indicator_values
    score = 0.0
    alerts = []
    details = {}

    # Debt-to-asset ratio
    debt_ratio = indicators.get('debt_to_asset_ratio', 0)
    if debt_ratio > 0.8:
        score += 30
        alerts.append({
            'severity': 'high',
            'message': f'High leverage: debt-to-asset ratio {debt_ratio:.1%}',
            'rule': rule.name,
        })
    elif debt_ratio > 0.6:
        score += 15

    # Net profit margin
    npm = indicators.get('net_profit_margin', 0)
    if npm < -0.1:
        score += 25
        alerts.append({
            'severity': 'high',
            'message': f'Negative profitability: net margin {npm:.1%}',
            'rule': rule.name,
        })
    elif npm < 0:
        score += 10

    # Current ratio
    current_ratio = indicators.get('current_ratio', 2)
    if current_ratio < 1.0:
        score += 20
        alerts.append({
            'severity': 'warning',
            'message': f'Low liquidity: current ratio {current_ratio:.2f}',
            'rule': rule.name,
        })

    # Revenue growth
    revenue_growth = indicators.get('revenue_growth_yoy', 0)
    if revenue_growth < -0.3:
        score += 15
        alerts.append({
            'severity': 'warning',
            'message': f'Revenue declining: {revenue_growth:.1%} YoY',
            'rule': rule.name,
        })

    details['financial_indicators'] = {
        'debt_ratio': debt_ratio,
        'net_profit_margin': npm,
        'current_ratio': current_ratio,
        'revenue_growth': revenue_growth,
    }

    return RuleResult(
        rule_name=rule.name,
        status=RuleStatus.COMPLETED,
        score=min(score, 100),
        alerts=alerts,
        details=details,
    )


def rule_credit_history(ctx: ReasoningContext, rule: RuleDefinition) -> RuleResult:
    """
    Assess credit history from credit reports.
    Key metrics: overdue history, inquiry frequency, debt-to-income.
    """
    credit = ctx.data_sources.get('credit_report', {})
    score = 0.0
    alerts = []

    overdue_count = credit.get('historical_overdue_count', 0)
    if overdue_count > 5:
        score += 35
        alerts.append({
            'severity': 'critical',
            'message': f'Historical overdue count: {overdue_count}',
            'rule': rule.name,
        })
    elif overdue_count > 2:
        score += 20
        alerts.append({
            'severity': 'high',
            'message': f'Historical overdue count: {overdue_count}',
            'rule': rule.name,
        })
    elif overdue_count > 0:
        score += 10

    recent_inquiries = credit.get('recent_inquiry_count', 0)
    if recent_inquiries > 10:
        score += 20
        alerts.append({
            'severity': 'warning',
            'message': f'High credit inquiry frequency: {recent_inquiries} recent inquiries',
            'rule': rule.name,
        })

    dti = credit.get('debt_to_income_ratio', 0)
    if dti > 0.7:
        score += 25
        alerts.append({
            'severity': 'high',
            'message': f'High debt-to-income ratio: {dti:.1%}',
            'rule': rule.name,
        })

    return RuleResult(
        rule_name=rule.name,
        status=RuleStatus.COMPLETED,
        score=min(score, 100),
        alerts=alerts,
        details=credit,
    )


def rule_legal_risk(ctx: ReasoningContext, rule: RuleDefinition) -> RuleResult:
    """
    Assess legal risk from litigation records.
    Key: recent loan-related litigation, enforcement cases, dispute frequency.
    """
    legal = ctx.data_sources.get('legal', {})
    score = 0.0
    alerts = []

    enforcement_cases = legal.get('enforcement_case_count', 0)
    if enforcement_cases > 0:
        score += min(enforcement_cases * 15, 45)
        alerts.append({
            'severity': 'critical',
            'message': f'{enforcement_cases} enforcement case(s) found',
            'rule': rule.name,
        })

    loan_litigation_amount = legal.get('loan_litigation_amount', 0)
    if loan_litigation_amount > 5_000_000:
        score += 30
        alerts.append({
            'severity': 'high',
            'message': f'Loan litigation amount: ¥{loan_litigation_amount:,.0f}',
            'rule': rule.name,
        })

    total_cases = legal.get('total_case_count', 0)
    if total_cases > 10:
        score += 15

    return RuleResult(
        rule_name=rule.name,
        status=RuleStatus.COMPLETED,
        score=min(score, 100),
        alerts=alerts,
        details=legal,
    )


def rule_settlement_stability(ctx: ReasoningContext, rule: RuleDefinition) -> RuleResult:
    """
    Assess settlement/cash flow stability.
    Key: average daily balance, salary payment regularity, operating cash flow.
    """
    settlement = ctx.data_sources.get('settlement', {})
    score = 0.0
    alerts = []

    # Average daily balance trend
    balance_trend = settlement.get('avg_balance_trend', 'stable')
    if balance_trend == 'declining_fast':
        score += 25
        alerts.append({
            'severity': 'high',
            'message': 'Average daily balance declining rapidly',
            'rule': rule.name,
        })
    elif balance_trend == 'declining':
        score += 10

    # Salary payment stability
    salary_stability = settlement.get('salary_stability_score', 1.0)
    if salary_stability < 0.5:
        score += 20
        alerts.append({
            'severity': 'warning',
            'message': f'Irregular salary payments (stability: {salary_stability:.2f})',
            'rule': rule.name,
        })

    # Operating income vs expenses
    income = settlement.get('operating_income', 0)
    expenses = settlement.get('operating_expenses', 0)
    if income > 0 and expenses / income > 1.2:
        score += 20
        alerts.append({
            'severity': 'high',
            'message': f'Operating expenses exceed income by {(expenses / income - 1):.0%}',
            'rule': rule.name,
        })

    return RuleResult(
        rule_name=rule.name,
        status=RuleStatus.COMPLETED,
        score=min(score, 100),
        alerts=alerts,
        details=settlement,
    )


def rule_news_sentiment_risk(ctx: ReasoningContext, rule: RuleDefinition) -> RuleResult:
    """
    Assess risk from news and public sentiment.
    Key: negative news count, sentiment scores, major default news.
    """
    news = ctx.data_sources.get('news', {})
    score = 0.0
    alerts = []

    critical_news = news.get('critical_negative_count', 0)
    if critical_news > 0:
        score += min(critical_news * 25, 50)
        alerts.append({
            'severity': 'critical',
            'message': f'{critical_news} critically negative news article(s)',
            'rule': rule.name,
        })

    negative_news = news.get('negative_count', 0)
    if negative_news > 5:
        score += 20
        alerts.append({
            'severity': 'warning',
            'message': f'{negative_news} negative news articles in monitoring period',
            'rule': rule.name,
        })

    avg_sentiment = news.get('avg_sentiment_score', 0)
    if avg_sentiment < -0.5:
        score += 15

    return RuleResult(
        rule_name=rule.name,
        status=RuleStatus.COMPLETED,
        score=min(score, 100),
        alerts=alerts,
        details=news,
    )


# ============================================================
# Credit Assessment Rules (授信测额)
# ============================================================

def rule_credit_limit_assessment(ctx: ReasoningContext, rule: RuleDefinition) -> RuleResult:
    """
    Recommend credit limit based on multi-factor assessment.
    Depends on: financial_health, credit_history, supply_chain_position.
    """
    prior = ctx.prior_results
    ent = ctx.enterprise_data
    details = {}

    # Base credit from assets
    total_assets = ent.get('total_assets', 0)
    base_credit = total_assets * 0.3  # 30% of total assets as baseline

    # Adjust based on prior rule results
    financial_score = prior.get('financial_health', None)
    if financial_score and financial_score.status.value == 'completed':
        if financial_score.score < 25:
            base_credit *= 1.2  # Low risk = bonus
        elif financial_score.score > 75:
            base_credit *= 0.3  # High risk = reduction

    credit_score = prior.get('credit_history', None)
    if credit_score and credit_score.status.value == 'completed':
        if credit_score.score < 25:
            base_credit *= 1.1
        elif credit_score.score > 75:
            base_credit *= 0.4

    # Supply chain position bonus
    is_core_supplier = ent.get('is_core_supplier', False)
    whitelist_grade = ent.get('whitelist_grade', '')
    if is_core_supplier:
        base_credit *= 1.5
    if whitelist_grade == 'A':
        base_credit *= 1.3
    elif whitelist_grade == 'B':
        base_credit *= 1.1

    # Cap at registered capital * 5
    registered_capital = ent.get('registered_capital', 0)
    if registered_capital > 0:
        base_credit = min(base_credit, registered_capital * 5)

    details['recommended_credit_limit'] = round(base_credit, 2)
    details['calculation_basis'] = {
        'total_assets': total_assets,
        'registered_capital': registered_capital,
        'whitelist_grade': whitelist_grade,
    }

    # Score inversely: higher recommended credit = lower risk score
    score = max(0, 50 - (base_credit / max(total_assets, 1)) * 50) if total_assets > 0 else 50

    return RuleResult(
        rule_name=rule.name,
        status=RuleStatus.COMPLETED,
        score=min(score, 100),
        details=details,
    )


# ============================================================
# Post-Loan Monitoring Rules (贷后监控)
# ============================================================

def rule_default_blacklist_check(ctx: ReasoningContext, rule: RuleDefinition) -> RuleResult:
    """
    Check against default blacklist.
    Any active default record is a critical risk signal.
    """
    blacklist = ctx.data_sources.get('blacklist', {})
    score = 0.0
    alerts = []

    active_defaults = blacklist.get('active_default_count', 0)
    if active_defaults > 0:
        score = min(40 + active_defaults * 20, 100)
        for default_type in blacklist.get('default_types', []):
            alerts.append({
                'severity': 'critical',
                'message': f'Active default record: {default_type}',
                'rule': rule.name,
            })

    lost_trust = blacklist.get('lost_trust_count', 0)
    if lost_trust > 0:
        score = max(score, 80)
        alerts.append({
            'severity': 'critical',
            'message': f'Lost trust enforcement: {lost_trust} record(s)',
            'rule': rule.name,
        })

    return RuleResult(
        rule_name=rule.name,
        status=RuleStatus.COMPLETED,
        score=min(score, 100),
        alerts=alerts,
        details=blacklist,
    )


def rule_supply_chain_concentration(ctx: ReasoningContext, rule: RuleDefinition) -> RuleResult:
    """
    Monitor supply chain concentration risk.
    High dependency on single customer/supplier is risky.
    """
    concentration = ctx.graph_data.get('concentration', {})
    score = 0.0
    alerts = []

    customer_hhi = concentration.get('customer_hhi', 0)
    if customer_hhi > 2500:
        score += 30
        alerts.append({
            'severity': 'high',
            'message': f'High customer concentration (HHI: {customer_hhi})',
            'rule': rule.name,
        })
    elif customer_hhi > 1500:
        score += 15

    supplier_hhi = concentration.get('supplier_hhi', 0)
    if supplier_hhi > 2500:
        score += 30
        alerts.append({
            'severity': 'high',
            'message': f'High supplier concentration (HHI: {supplier_hhi})',
            'rule': rule.name,
        })
    elif supplier_hhi > 1500:
        score += 15

    return RuleResult(
        rule_name=rule.name,
        status=RuleStatus.COMPLETED,
        score=min(score, 100),
        alerts=alerts,
        details=concentration,
    )


# ============================================================
# Rule Registry - All standard rules
# ============================================================

def get_standard_rules() -> list[RuleDefinition]:
    """Return all standard credit risk assessment rules."""
    return [
        # Anti-Fraud
        RuleDefinition(
            name='shell_company_detection',
            description='Detect shell/packaging company indicators',
            category='ANTI_FRAUD',
            weight=2.0,
            evaluator=rule_shell_company_detection,
        ),
        RuleDefinition(
            name='circular_transaction_detection',
            description='Detect circular transaction patterns',
            category='ANTI_FRAUD',
            weight=2.0,
            evaluator=rule_circular_transaction_detection,
        ),
        RuleDefinition(
            name='invoice_anomaly_detection',
            description='Detect invoice-order-delivery mismatches',
            category='ANTI_FRAUD',
            weight=1.5,
            evaluator=rule_invoice_anomaly_detection,
        ),
        # KYB
        RuleDefinition(
            name='business_legitimacy',
            description='Verify enterprise business legitimacy',
            category='KYB',
            weight=1.5,
            evaluator=rule_business_legitimacy,
        ),
        RuleDefinition(
            name='related_party_risk',
            description='Assess related party relationship risk',
            category='KYB',
            weight=1.5,
            evaluator=rule_related_party_risk,
        ),
        # Risk Rating
        RuleDefinition(
            name='financial_health',
            description='Assess financial health from reports',
            category='RISK_RATING',
            weight=2.0,
            evaluator=rule_financial_health,
        ),
        RuleDefinition(
            name='credit_history',
            description='Assess credit history and overdue records',
            category='RISK_RATING',
            weight=2.0,
            evaluator=rule_credit_history,
        ),
        RuleDefinition(
            name='legal_risk',
            description='Assess legal litigation risk',
            category='RISK_RATING',
            weight=1.5,
            evaluator=rule_legal_risk,
        ),
        RuleDefinition(
            name='settlement_stability',
            description='Assess cash flow and settlement stability',
            category='RISK_RATING',
            weight=1.5,
            evaluator=rule_settlement_stability,
        ),
        RuleDefinition(
            name='news_sentiment_risk',
            description='Monitor news and public sentiment risk',
            category='RISK_RATING',
            weight=1.0,
            evaluator=rule_news_sentiment_risk,
        ),
        # Credit Assessment
        RuleDefinition(
            name='credit_limit_assessment',
            description='Recommend credit limit based on multi-factor assessment',
            category='CREDIT_ASSESSMENT',
            weight=2.0,
            dependencies=['financial_health', 'credit_history'],
            evaluator=rule_credit_limit_assessment,
        ),
        # Post-Loan Monitoring
        RuleDefinition(
            name='default_blacklist_check',
            description='Check against default blacklist records',
            category='POST_LOAN',
            weight=3.0,
            evaluator=rule_default_blacklist_check,
        ),
        RuleDefinition(
            name='supply_chain_concentration',
            description='Monitor supply chain concentration risk',
            category='POST_LOAN',
            weight=1.5,
            evaluator=rule_supply_chain_concentration,
        ),
    ]
