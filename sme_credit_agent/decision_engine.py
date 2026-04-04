"""
Risk Control Decision Engine (风控决策引擎 / 审批调度系统).

The middle panel of the diagram. Orchestrates:
1. Internal data + scenario data ingestion
2. Quantitative model scoring
3. Risk rule evaluation
4. Credit enhancement / amount increase decision (增信/增额决策)
5. Due diligence dispatch (分层尽调系统 integration)

The engine produces a RiskDecision and optionally triggers due diligence
work orders that feed back into the final decision via 人机协作风控决策.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from .models import (
    CollateralType,
    CreditApplication,
    CreditDecisionResult,
    DueDiligenceMethod,
    DueDiligenceRequest,
    RiskDecision,
)
from .tools import (
    dispatch_due_diligence,
    evaluate_risk_rules,
    fetch_internal_data,
    fetch_scenario_data,
    get_due_diligence_result,
    run_quantitative_model,
)

logger = logging.getLogger(__name__)


@dataclass
class EngineContext:
    """Assembled inputs for the decision engine."""
    application: CreditApplication
    internal_data: dict
    scenario_data: dict
    model_result: dict
    rule_evaluation: dict
    dd_results: list[dict]


class RiskControlDecisionEngine:
    """
    Implements the 风控决策引擎 (Risk Control Decision Engine).

    Architecture:
        场景数据 ─┐
                  ├─▶ 风控决策引擎 ──▶ 增信/增额决策 ──▶ RiskDecision
        内部数据 ─┘        │
                  量化模型 ─┘
                  风控规则 ─┘
                           │
                           ▼
                   分层尽调系统 ──▶ 尽调结果 (fed back)
    """

    # Thresholds for layered due diligence dispatch
    PHONE_DD_THRESHOLD_AMOUNT = 200       # 万元: require phone check above this
    VIDEO_DD_THRESHOLD_AMOUNT = 500       # 万元: require video due diligence above this
    ONSITE_DD_THRESHOLD_AMOUNT = 1000     # 万元: require on-site investigation above this
    HIGH_PD_THRESHOLD = 0.08              # PD threshold for mandatory DD

    def evaluate(self, application: CreditApplication) -> RiskDecision:
        """
        Run the full evaluation pipeline and produce a RiskDecision.

        Flow:
          1. Fetch data (internal + scenario)
          2. Run quantitative model
          3. Apply risk rules
          4. Determine DD requirements
          5. Collect DD results (synchronous in this stub)
          6. Make final credit decision
        """
        logger.info("Starting evaluation for application %s", application.application_id)

        # Step 1: Gather data
        internal = fetch_internal_data(application.company_name)
        industry = application.industry or "general"
        scenario = fetch_scenario_data(industry, application.company_name)

        # Step 2: Quantitative model
        model_result = run_quantitative_model(
            application_id=application.application_id,
            loan_amount=application.loan_amount,
            collateral_type=application.collateral_type.value,
            internal_credit_score=internal.get("credit_score", 60),
            industry_risk_rating=scenario.get("industry_risk_rating", "medium"),
        )

        # Step 3: Risk rules
        rule_eval = evaluate_risk_rules(
            application_id=application.application_id,
            company_name=application.company_name,
            loan_amount=application.loan_amount,
            collateral_type=application.collateral_type.value,
            probability_of_default=model_result.get("probability_of_default", 0.05),
        )

        # Step 4: Determine and dispatch due diligence
        dd_requests = self._dispatch_due_diligence(application, model_result, rule_eval)

        # Step 5: Collect DD results
        import json
        dd_results = []
        for req_dict in dd_requests:
            result_str = get_due_diligence_result(req_dict["request_id"])
            if isinstance(result_str, str):
                dd_results.append(json.loads(result_str))
            else:
                dd_results.append(result_str)

        # Step 6: Make decision
        ctx = EngineContext(
            application=application,
            internal_data=internal,
            scenario_data=scenario,
            model_result=model_result,
            rule_evaluation=rule_eval,
            dd_results=dd_results,
        )
        decision = self._make_decision(ctx)
        logger.info(
            "Decision for %s: %s (amount: %s 万元)",
            application.application_id,
            decision.result.value,
            decision.approved_amount,
        )
        return decision

    def _dispatch_due_diligence(
        self,
        application: CreditApplication,
        model_result: dict,
        rule_eval: dict,
    ) -> list[dict]:
        """
        Determine which due diligence method to use based on risk profile
        and dispatch work orders to the 分层尽调系统.

        Layering logic:
          - phone   (电话核查)  : 200–499 万元 or PD > 6%
          - video   (视频尽调)  : 500–999 万元 or failed soft rules
          - on_site (下户调查)  : ≥ 1000 万元 or hard rule failures
        """
        pd = model_result.get("probability_of_default", 0.05)
        amount = application.loan_amount
        failed_rules = rule_eval.get("failed_rules", [])
        dispatched = []

        # Determine method
        method: Optional[str] = None
        focus_areas: list[str] = []
        priority = "normal"

        if amount >= self.ONSITE_DD_THRESHOLD_AMOUNT or len(failed_rules) > 1:
            method = "on_site"
            priority = "urgent" if len(failed_rules) > 1 else "normal"
            focus_areas = [
                "actual controller background and ownership structure",
                "on-site production and operational status",
                "accounts receivable and inventory authenticity",
                "major customer and supplier verification",
            ]
        elif amount >= self.VIDEO_DD_THRESHOLD_AMOUNT or failed_rules:
            method = "video"
            focus_areas = [
                "business license and qualification verification",
                "management team interview",
                "financial statement consistency check",
            ]
        elif amount >= self.PHONE_DD_THRESHOLD_AMOUNT or pd > self.HIGH_PD_THRESHOLD:
            method = "phone"
            focus_areas = [
                "basic business operations confirmation",
                "loan purpose verification",
                "major repayment source confirmation",
            ]

        if method:
            result = dispatch_due_diligence(
                application_id=application.application_id,
                method=method,
                focus_areas=focus_areas,
                priority=priority,
            )
            dispatched.append(result if isinstance(result, dict) else {})

        return dispatched

    def _make_decision(self, ctx: EngineContext) -> RiskDecision:
        """
        Apply final decision logic combining all evaluation outputs.
        Implements the 增信/增额决策 (Credit Enhancement / Amount Decision).
        """
        app = ctx.application
        model = ctx.model_result
        rules = ctx.rule_evaluation
        dd = ctx.dd_results

        pd = model.get("probability_of_default", 0.05)
        recommended_max = model.get("recommended_max_amount", app.loan_amount * 0.8)
        rule_result = rules.get("overall_rule_result", "pass")
        failed_rules = rules.get("failed_rules", [])
        needs_enhancement = rules.get("credit_enhancement_required", False)

        # Check DD red flags
        all_red_flags = [flag for r in dd for flag in r.get("red_flags", [])]
        dd_negative = any(r.get("overall_assessment") == "negative" for r in dd)

        # Decision logic
        if rule_result == "block" or dd_negative:
            return RiskDecision(
                application_id=app.application_id,
                result=CreditDecisionResult.REJECT,
                approved_amount=None,
                approved_tenure_months=None,
                interest_rate_bps=None,
                conditions=[f"Rule violation: {r}" for r in failed_rules],
                requires_human_review=False,
            )

        # Approved amount is min of requested and model recommendation
        approved_amount = min(app.loan_amount, recommended_max)
        approved_amount = round(approved_amount, 1)

        # Interest rate premium based on risk
        if pd < 0.03:
            rate_bps = 50
        elif pd < 0.06:
            rate_bps = 100
        elif pd < 0.10:
            rate_bps = 150
        else:
            rate_bps = 200

        # Add red flag premium
        rate_bps += len(all_red_flags) * 25

        conditions = []
        required_enhancements = []
        result = CreditDecisionResult.APPROVE

        if needs_enhancement:
            result = CreditDecisionResult.CONDITIONAL
            required_enhancements = rules.get("suggested_enhancements", [])
            conditions.append("Credit enhancement required before drawdown")

        if all_red_flags:
            conditions.append(f"Due diligence flags: {'; '.join(all_red_flags)}")
            result = CreditDecisionResult.CONDITIONAL

        if rule_result == "conditional":
            result = CreditDecisionResult.CONDITIONAL
            conditions.extend([f"Conditional on resolving: {r}" for r in failed_rules])

        # Require human review for large or borderline cases
        requires_human = (
            app.loan_amount >= 1000
            or pd > 0.08
            or len(failed_rules) > 0
        )

        return RiskDecision(
            application_id=app.application_id,
            result=result,
            approved_amount=approved_amount,
            approved_tenure_months=app.loan_tenure_months,
            interest_rate_bps=rate_bps,
            conditions=conditions,
            required_enhancements=required_enhancements,
            requires_human_review=requires_human,
        )
