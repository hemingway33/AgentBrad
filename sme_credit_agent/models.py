"""
Data models for the SME credit agent system.

Mirrors the three-panel architecture:
- CreditApplication: input from the customer (left panel)
- RiskDecision: output from the decision engine (middle panel)
- DueDiligenceRequest/Result: layered investigation (right panel)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class CollateralType(str, Enum):
    CREDIT = "credit"           # 信用
    MORTGAGE = "mortgage"       # 抵押
    PLEDGE = "pledge"           # 质押
    GUARANTEE = "guarantee"     # 保证


class LoanPurpose(str, Enum):
    RAW_MATERIAL = "raw_material"       # 采购原材料
    EQUIPMENT = "equipment"             # 购置设备
    WORKING_CAPITAL = "working_capital" # 流动资金
    EXPANSION = "expansion"             # 扩大经营
    OTHER = "other"


class DueDiligenceMethod(str, Enum):
    PHONE = "phone"       # 电话核查
    VIDEO = "video"       # 视频尽调
    ON_SITE = "on_site"   # 下户调查


class DueDiligenceStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CreditDecisionResult(str, Enum):
    APPROVE = "approve"           # 批准
    CONDITIONAL = "conditional"   # 有条件批准
    REJECT = "reject"             # 拒绝
    PENDING_DD = "pending_dd"     # 待尽调结果


@dataclass
class CreditApplication:
    """
    Credit application submitted by an SME customer.
    Corresponds to the user message in the left panel of the diagram.
    """
    company_name: str
    registration_province: str
    loan_amount: float                    # in CNY 万元
    collateral_type: CollateralType
    loan_purpose: LoanPurpose
    loan_tenure_months: int

    # Optional enrichment fields
    industry: Optional[str] = None
    annual_revenue: Optional[float] = None  # 万元
    years_in_business: Optional[int] = None
    existing_loans: Optional[float] = None  # 万元
    tax_credit_rating: Optional[str] = None # A/B/C/D/M
    special_focus_areas: Optional[list[str]] = field(default_factory=list)

    application_id: str = field(default_factory=lambda: _generate_id("APP"))
    submitted_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class InternalData:
    """
    Internal bank data about the company (内部数据).
    Sourced from the bank's own systems.
    """
    company_name: str
    historical_loans: list[dict]          # past loan records
    repayment_history: dict               # on-time rate, defaults
    account_activity: dict                # transaction patterns
    existing_credit_limit: float          # existing approved limit
    credit_score: Optional[float] = None  # internal credit score
    relationship_years: int = 0           # years as bank customer


@dataclass
class ScenarioData:
    """
    Scenario / industry context data (场景数据).
    External market and industry intelligence.
    """
    industry: str
    industry_risk_rating: str             # low / medium / high
    supply_chain_position: str            # upstream / midstream / downstream
    market_growth_rate: float             # YoY %
    peer_default_rate: float              # industry peer default rate %
    macro_indicators: dict                # relevant macro signals
    regulatory_environment: str           # favorable / neutral / challenging


@dataclass
class QuantitativeModelResult:
    """
    Output from the quantitative model (量化模型).
    """
    probability_of_default: float         # 0.0 – 1.0
    loss_given_default: float             # 0.0 – 1.0
    expected_loss: float                  # CNY
    recommended_max_amount: float         # 万元
    model_confidence: float               # 0.0 – 1.0
    model_version: str = "v1.0"
    computed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RiskRuleEvaluation:
    """
    Result of applying risk control rules (风控规则).
    """
    passed_rules: list[str]
    failed_rules: list[str]
    warning_rules: list[str]
    overall_rule_result: str              # pass / conditional / block
    credit_enhancement_required: bool
    suggested_enhancements: list[str] = field(default_factory=list)


@dataclass
class DueDiligenceRequest:
    """
    Work order dispatched to the due diligence system (标准尽调工单).
    Triggered by the decision engine when deeper investigation is needed.
    """
    application_id: str
    method: DueDiligenceMethod
    focus_areas: list[str]                # what to investigate
    priority: str = "normal"             # urgent / normal / low
    assigned_to: Optional[str] = None
    deadline: Optional[datetime] = None

    request_id: str = field(default_factory=lambda: _generate_id("DD"))
    status: DueDiligenceStatus = DueDiligenceStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DueDiligenceResult:
    """
    Completed investigation result from the due diligence system (尽调结果).
    """
    request_id: str
    application_id: str
    method: DueDiligenceMethod
    findings: dict                        # structured findings by focus area
    overall_assessment: str              # positive / neutral / negative / mixed
    red_flags: list[str] = field(default_factory=list)
    supporting_documents: list[str] = field(default_factory=list)
    completed_at: datetime = field(default_factory=datetime.utcnow)
    investigator: Optional[str] = None


@dataclass
class RiskDecision:
    """
    Final output from the risk control decision engine (风控决策引擎).
    Human-AI collaborative risk control decision (人机协作风控决策).
    """
    application_id: str
    result: CreditDecisionResult
    approved_amount: Optional[float]      # 万元, None if rejected
    approved_tenure_months: Optional[int]
    interest_rate_bps: Optional[int]      # basis points above benchmark
    conditions: list[str] = field(default_factory=list)
    required_enhancements: list[str] = field(default_factory=list)
    due_diligence_requests: list[DueDiligenceRequest] = field(default_factory=list)
    decided_at: datetime = field(default_factory=datetime.utcnow)
    requires_human_review: bool = False


@dataclass
class CreditAnalysisReport:
    """
    Full analysis report produced by the credit analysis agent (left panel).
    Contains the agent's synthesis before the decision engine acts.
    """
    application_id: str
    company_name: str

    # Three business highlights (三大经营亮点)
    business_highlights: list[str]

    # Three risk concerns (三个风险关注点)
    risk_concerns: list[str]

    # Detailed analysis sections
    operational_sustainability_analysis: str
    repayment_history_analysis: str
    product_competitiveness_analysis: str
    supply_chain_position_analysis: str
    development_prospects_analysis: str

    # Credit recommendation
    credit_recommendation: str
    recommended_amount: float             # 万元
    confidence_level: str                 # high / medium / low

    # Due diligence suggestions (if any)
    suggested_dd_focus_areas: list[str] = field(default_factory=list)

    generated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PostLoanMonitoring:
    """
    In-loan customer operation model (贷中客户运营模型).
    Tracks behavior signals during loan tenure.
    """
    application_id: str
    company_name: str
    monitoring_signals: list[dict]        # real-time risk signals
    repayment_behavior: dict              # actual vs scheduled
    risk_level: str                       # green / yellow / red
    recommended_actions: list[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CollectionWorkOrder:
    """
    Post-loan collection operation model (贷后催收作业模型).
    Activated when repayment is overdue.
    """
    application_id: str
    company_name: str
    overdue_amount: float                 # 万元
    overdue_days: int
    collection_strategy: str             # reminder / negotiation / legal
    assigned_collector: Optional[str] = None
    contact_attempts: list[dict] = field(default_factory=list)
    resolution: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


def _generate_id(prefix: str) -> str:
    import uuid
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"
