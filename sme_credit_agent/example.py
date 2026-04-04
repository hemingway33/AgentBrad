"""
Example: Full SME credit analysis flow.

Mirrors the diagram scenario:
  江苏省XXX有限公司 applies for 2000万元 credit loan to purchase raw materials.
  The agent analyzes risk, dispatches due diligence, and produces a recommendation.

Run:
    ANTHROPIC_API_KEY=your-key python -m sme_credit_agent.example
"""

from __future__ import annotations

import os
import sys

from . import (
    CollateralType,
    CreditApplication,
    LoanPurpose,
    RiskControlDecisionEngine,
    SMECreditAgent,
)


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set.")
        sys.exit(1)

    # ── 1. Build the credit application (left panel input) ─────────────────
    application = CreditApplication(
        company_name="江苏省XXX有限公司",
        registration_province="江苏省",
        loan_amount=2000,                       # 2000万元
        collateral_type=CollateralType.CREDIT,  # 信用贷
        loan_purpose=LoanPurpose.RAW_MATERIAL,  # 采购原材料
        loan_tenure_months=12,
        industry="制造业",
        special_focus_areas=[
            "经营可持续性",
            "过往贷款履约情况",
            "产品竞争力",
            "产业链地位",
            "发展前景",
        ],
    )

    print("=" * 70)
    print("SME 信贷分析系统 — 信贷分析助理")
    print("=" * 70)
    print(f"申请编号  : {application.application_id}")
    print(f"申请企业  : {application.company_name}")
    print(f"申请金额  : {application.loan_amount:,.0f} 万元")
    print(f"担保方式  : {application.collateral_type.value}")
    print(f"贷款用途  : {application.loan_purpose.value}")
    print(f"申请期限  : {application.loan_tenure_months} 个月")
    print("=" * 70)
    print()

    # ── 2. Run the AI credit analysis agent (left panel) ──────────────────
    print("【信贷分析助理分析中...】")
    print("-" * 70)

    agent = SMECreditAgent()
    for chunk in agent.analyze_stream(application):
        print(chunk, end="", flush=True)

    print()
    print("-" * 70)

    # ── 3. Run the risk control decision engine (middle panel) ────────────
    print()
    print("【风控决策引擎评估中...】")
    print("-" * 70)

    engine = RiskControlDecisionEngine()
    decision = engine.evaluate(application)

    print(f"决策结果  : {decision.result.value}")
    print(f"批准金额  : {decision.approved_amount:,.1f} 万元" if decision.approved_amount else "批准金额  : 拒绝")
    print(f"批准期限  : {decision.approved_tenure_months} 个月" if decision.approved_tenure_months else "")
    print(f"利率溢价  : LPR + {decision.interest_rate_bps} BP" if decision.interest_rate_bps else "")
    print(f"人工复核  : {'需要' if decision.requires_human_review else '不需要'}")

    if decision.conditions:
        print("附加条件  :")
        for c in decision.conditions:
            print(f"  • {c}")

    if decision.required_enhancements:
        print("增信要求  :")
        for e in decision.required_enhancements:
            print(f"  • {e}")

    print()
    print("=" * 70)
    print("分析完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
