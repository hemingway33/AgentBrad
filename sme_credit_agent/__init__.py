"""
SME Credit Agent — 信贷流程体验优化

A Claude-powered SME credit analysis system implementing the three-panel
architecture:

Left panel  — SMECreditAgent: AI credit analysis assistant
Middle panel — RiskControlDecisionEngine: quantitative models + risk rules
Right panel  — DueDiligenceSystem: layered investigation (phone/video/on-site)

Quick start:
    from sme_credit_agent import SMECreditAgent, CreditApplication, CollateralType, LoanPurpose

    app = CreditApplication(
        company_name="江苏省XXX有限公司",
        registration_province="江苏省",
        loan_amount=2000,          # 万元
        collateral_type=CollateralType.CREDIT,
        loan_purpose=LoanPurpose.RAW_MATERIAL,
        loan_tenure_months=12,
        industry="制造业",
    )

    agent = SMECreditAgent()
    for chunk in agent.analyze_stream(app):
        print(chunk, end="", flush=True)
"""

from .agent import SMECreditAgent
from .decision_engine import RiskControlDecisionEngine
from .due_diligence import DueDiligenceSystem
from .models import (
    CollateralType,
    CreditAnalysisReport,
    CreditApplication,
    CreditDecisionResult,
    DueDiligenceMethod,
    LoanPurpose,
    RiskDecision,
)

__all__ = [
    # Agent
    "SMECreditAgent",
    # Engine
    "RiskControlDecisionEngine",
    # Due Diligence
    "DueDiligenceSystem",
    # Models
    "CreditApplication",
    "CollateralType",
    "LoanPurpose",
    "CreditAnalysisReport",
    "CreditDecisionResult",
    "DueDiligenceMethod",
    "RiskDecision",
]
