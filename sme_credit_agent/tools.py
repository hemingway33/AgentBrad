"""
Tool definitions for the SME credit analysis agent.

These tools correspond to the data flows shown in the diagram:
- fetch_internal_data       → 内部数据 (Internal Data)
- fetch_scenario_data       → 场景数据 (Scenario Data)
- run_quantitative_model    → 量化模型 (Quantitative Model)
- evaluate_risk_rules       → 风控规则 (Risk Control Rules)
- dispatch_due_diligence    → 分层尽调系统 (Layered Due Diligence System)
- get_due_diligence_result  → 尽调结果 (Due Diligence Result)
- record_credit_decision    → 审批结果 (Approval Result)
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from typing import Any

from .models import (
    CollateralType,
    CreditApplication,
    DueDiligenceMethod,
    DueDiligenceRequest,
    DueDiligenceResult,
    DueDiligenceStatus,
    InternalData,
    QuantitativeModelResult,
    RiskRuleEvaluation,
    ScenarioData,
)


# ---------------------------------------------------------------------------
# Tool schemas (passed to the Claude API)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "fetch_internal_data",
        "description": (
            "Retrieve the bank's internal data about a company: historical loans, "
            "repayment history, account activity, existing credit limits, and internal "
            "credit score. This is the 内部数据 (Internal Data) source in the decision engine."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {
                    "type": "string",
                    "description": "Full registered company name"
                },
                "include_transaction_history": {
                    "type": "boolean",
                    "description": "Whether to include detailed transaction patterns",
                    "default": True
                }
            },
            "required": ["company_name"]
        }
    },
    {
        "name": "fetch_scenario_data",
        "description": (
            "Retrieve industry and market scenario data for the company's sector: "
            "industry risk rating, supply chain position, market growth rate, peer "
            "default rates, and regulatory environment. This is the 场景数据 (Scenario Data) "
            "source in the decision engine."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "industry": {
                    "type": "string",
                    "description": "Industry or sector of the company"
                },
                "company_name": {
                    "type": "string",
                    "description": "Company name for supply-chain position lookup"
                }
            },
            "required": ["industry"]
        }
    },
    {
        "name": "run_quantitative_model",
        "description": (
            "Run the bank's quantitative credit scoring model (量化模型) on the application. "
            "Returns probability of default, loss given default, expected loss, and "
            "recommended maximum loan amount."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "application_id": {
                    "type": "string",
                    "description": "The credit application ID"
                },
                "loan_amount": {
                    "type": "number",
                    "description": "Requested loan amount in 万元 (CNY 10,000s)"
                },
                "collateral_type": {
                    "type": "string",
                    "enum": ["credit", "mortgage", "pledge", "guarantee"],
                    "description": "Type of collateral offered"
                },
                "internal_credit_score": {
                    "type": "number",
                    "description": "Internal credit score from fetch_internal_data (0-100)"
                },
                "industry_risk_rating": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Industry risk rating from fetch_scenario_data"
                }
            },
            "required": ["application_id", "loan_amount", "collateral_type"]
        }
    },
    {
        "name": "evaluate_risk_rules",
        "description": (
            "Apply the bank's risk control rule set (风控规则) to the application. "
            "Rules cover blacklists, concentration limits, single-borrower caps, "
            "industry restrictions, and regulatory compliance. Returns passed/failed/warning "
            "rules and whether credit enhancement is required."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "application_id": {
                    "type": "string",
                    "description": "The credit application ID"
                },
                "company_name": {
                    "type": "string",
                    "description": "Company name for blacklist and watchlist checks"
                },
                "loan_amount": {
                    "type": "number",
                    "description": "Requested loan amount in 万元"
                },
                "collateral_type": {
                    "type": "string",
                    "enum": ["credit", "mortgage", "pledge", "guarantee"]
                },
                "probability_of_default": {
                    "type": "number",
                    "description": "PD from quantitative model (0.0-1.0)",
                    "minimum": 0.0,
                    "maximum": 1.0
                }
            },
            "required": ["application_id", "company_name", "loan_amount", "collateral_type"]
        }
    },
    {
        "name": "dispatch_due_diligence",
        "description": (
            "Dispatch a due diligence work order to the 分层尽调系统 (Layered Due Diligence System). "
            "Choose the investigation method based on risk level: phone verification (电话核查) "
            "for low-risk cases, video due diligence (视频尽调) for medium-risk, "
            "and on-site investigation (下户调查) for high-risk or large loans. "
            "Returns a due diligence request ID for tracking."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "application_id": {
                    "type": "string",
                    "description": "The credit application ID"
                },
                "method": {
                    "type": "string",
                    "enum": ["phone", "video", "on_site"],
                    "description": "Investigation method: phone=电话核查, video=视频尽调, on_site=下户调查"
                },
                "focus_areas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific areas to investigate (e.g., 'operational continuity', 'actual controller background', 'accounts receivable authenticity')"
                },
                "priority": {
                    "type": "string",
                    "enum": ["urgent", "normal", "low"],
                    "default": "normal",
                    "description": "Investigation priority level"
                }
            },
            "required": ["application_id", "method", "focus_areas"]
        }
    },
    {
        "name": "get_due_diligence_result",
        "description": (
            "Retrieve the completed due diligence investigation result (尽调结果) "
            "for a given request. Returns structured findings, overall assessment, "
            "and any red flags discovered during investigation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "request_id": {
                    "type": "string",
                    "description": "The due diligence request ID returned by dispatch_due_diligence"
                }
            },
            "required": ["request_id"]
        }
    },
    {
        "name": "record_credit_decision",
        "description": (
            "Record the final credit decision (审批结果) to the system. "
            "This closes the 增信/增额决策 loop and feeds back to the customer operations models. "
            "Should be called after all analysis is complete."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "application_id": {
                    "type": "string",
                    "description": "The credit application ID"
                },
                "decision": {
                    "type": "string",
                    "enum": ["approve", "conditional", "reject", "pending_dd"],
                    "description": "Credit decision result"
                },
                "approved_amount": {
                    "type": "number",
                    "description": "Approved loan amount in 万元 (null if rejected)"
                },
                "approved_tenure_months": {
                    "type": "integer",
                    "description": "Approved loan tenure in months"
                },
                "interest_rate_bps": {
                    "type": "integer",
                    "description": "Interest rate premium in basis points above LPR"
                },
                "conditions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Conditions attached to the approval"
                },
                "requires_human_review": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether a human credit officer must review before final approval"
                }
            },
            "required": ["application_id", "decision"]
        }
    }
]


# ---------------------------------------------------------------------------
# Tool implementations (stubs — replace with real integrations)
# ---------------------------------------------------------------------------

_dd_requests: dict[str, DueDiligenceRequest] = {}
_dd_results: dict[str, DueDiligenceResult] = {}
_decisions: dict[str, dict] = {}


def fetch_internal_data(company_name: str, include_transaction_history: bool = True) -> dict:
    """Fetch internal bank data for the company."""
    # Stub: in production, query the bank's core banking system
    rng = random.Random(hash(company_name))
    credit_score = round(rng.uniform(45, 90), 1)
    on_time_rate = round(rng.uniform(0.75, 0.99), 3)

    result = {
        "company_name": company_name,
        "credit_score": credit_score,
        "relationship_years": rng.randint(1, 12),
        "historical_loans": [
            {
                "loan_id": f"LN{i:04d}",
                "amount": rng.randint(100, 2000),
                "purpose": rng.choice(["working_capital", "equipment", "raw_material"]),
                "status": rng.choice(["repaid", "repaid", "repaid", "active"]),
                "on_time": rng.random() < on_time_rate,
            }
            for i in range(rng.randint(2, 6))
        ],
        "repayment_history": {
            "on_time_rate": on_time_rate,
            "total_defaults": rng.randint(0, 1),
            "current_overdue_amount": round(rng.uniform(0, 50), 1) if rng.random() < 0.15 else 0,
        },
        "existing_credit_limit": rng.randint(0, 1000),
        "existing_utilized": rng.randint(0, 500),
        "tax_credit_rating": rng.choice(["A", "A", "B", "B", "C", "M"]),
    }
    if include_transaction_history:
        result["account_activity"] = {
            "avg_monthly_inflow": round(rng.uniform(200, 5000), 1),
            "avg_monthly_outflow": round(rng.uniform(180, 4800), 1),
            "transaction_regularity": rng.choice(["stable", "stable", "moderate", "volatile"]),
        }
    return result


def fetch_scenario_data(industry: str, company_name: str = "") -> dict:
    """Fetch industry and market scenario data."""
    # Stub: in production, query industry database and market intelligence platform
    rng = random.Random(hash(industry))
    risk_ratings = {
        "manufacturing": "medium",
        "construction": "high",
        "retail": "medium",
        "technology": "low",
        "agriculture": "medium",
        "logistics": "medium",
        "food": "low",
        "chemical": "high",
        "textile": "medium",
        "equipment": "medium",
    }
    industry_key = next((k for k in risk_ratings if k in industry.lower()), None)
    risk_rating = risk_ratings.get(industry_key, rng.choice(["low", "medium", "medium", "high"]))

    return {
        "industry": industry,
        "industry_risk_rating": risk_rating,
        "supply_chain_position": rng.choice(["upstream", "midstream", "downstream"]),
        "market_growth_rate": round(rng.uniform(-3, 18), 1),
        "peer_default_rate": round(rng.uniform(0.5, 8.0), 2),
        "macro_indicators": {
            "pmi": round(rng.uniform(48, 55), 1),
            "industry_capacity_utilization": round(rng.uniform(60, 90), 1),
        },
        "regulatory_environment": rng.choice(["favorable", "neutral", "neutral", "challenging"]),
        "policy_support": rng.choice(["strong", "moderate", "limited"]),
    }


def run_quantitative_model(
    application_id: str,
    loan_amount: float,
    collateral_type: str,
    internal_credit_score: float = 60.0,
    industry_risk_rating: str = "medium",
) -> dict:
    """Run the quantitative credit scoring model."""
    # Stub: in production, call the bank's ML model service
    rng = random.Random(hash(application_id))

    # Simulate PD based on key inputs
    base_pd = 0.05
    if internal_credit_score < 50:
        base_pd += 0.08
    elif internal_credit_score > 75:
        base_pd -= 0.02

    if industry_risk_rating == "high":
        base_pd += 0.04
    elif industry_risk_rating == "low":
        base_pd -= 0.02

    if collateral_type == "credit":
        base_pd += 0.02
    elif collateral_type in ("mortgage", "pledge"):
        base_pd -= 0.01

    pd = max(0.005, min(0.35, base_pd + rng.uniform(-0.02, 0.02)))
    lgd = 0.45 if collateral_type == "credit" else 0.30
    recommended_max = min(loan_amount * 1.1, loan_amount / max(pd * 10, 0.5)) * rng.uniform(0.85, 1.0)

    return {
        "application_id": application_id,
        "probability_of_default": round(pd, 4),
        "loss_given_default": round(lgd, 4),
        "expected_loss": round(loan_amount * pd * lgd, 2),
        "recommended_max_amount": round(recommended_max, 1),
        "model_confidence": round(rng.uniform(0.70, 0.95), 3),
        "model_version": "v2.3.1",
        "computed_at": datetime.utcnow().isoformat(),
    }


def evaluate_risk_rules(
    application_id: str,
    company_name: str,
    loan_amount: float,
    collateral_type: str,
    probability_of_default: float = 0.05,
) -> dict:
    """Apply the bank's risk control rule set."""
    # Stub: in production, query the rule engine service
    passed, failed, warnings = [], [], []

    # R001: Blacklist check
    passed.append("R001-blacklist-check")

    # R002: Single borrower concentration limit (假设上限 3000 万)
    if loan_amount > 3000:
        failed.append("R002-single-borrower-limit")
    else:
        passed.append("R002-single-borrower-limit")

    # R003: Credit-only collateral cap (信用贷上限 500 万)
    if collateral_type == "credit" and loan_amount > 500:
        failed.append("R003-credit-collateral-cap")
    else:
        passed.append("R003-credit-collateral-cap")

    # R004: PD threshold warning
    if probability_of_default > 0.10:
        failed.append("R004-pd-threshold")
    elif probability_of_default > 0.06:
        warnings.append("R004-pd-threshold")
    else:
        passed.append("R004-pd-threshold")

    # R005: Regulatory compliance
    passed.append("R005-regulatory-compliance")

    overall = "pass" if not failed else ("conditional" if len(failed) <= 1 else "block")
    needs_enhancement = collateral_type == "credit" and loan_amount > 200

    return {
        "application_id": application_id,
        "passed_rules": passed,
        "failed_rules": failed,
        "warning_rules": warnings,
        "overall_rule_result": overall,
        "credit_enhancement_required": needs_enhancement,
        "suggested_enhancements": (
            ["guarantor required", "pledge additional assets"] if needs_enhancement else []
        ),
    }


def dispatch_due_diligence(
    application_id: str,
    method: str,
    focus_areas: list[str],
    priority: str = "normal",
) -> dict:
    """Dispatch a due diligence work order."""
    method_enum = DueDiligenceMethod(method)
    req = DueDiligenceRequest(
        application_id=application_id,
        method=method_enum,
        focus_areas=focus_areas,
        priority=priority,
        deadline=datetime.utcnow() + timedelta(days={"urgent": 1, "normal": 3, "low": 7}[priority]),
    )
    _dd_requests[req.request_id] = req

    # Simulate async completion for demo purposes
    _simulate_dd_completion(req)

    return {
        "request_id": req.request_id,
        "application_id": application_id,
        "method": method,
        "focus_areas": focus_areas,
        "priority": priority,
        "status": "in_progress",
        "deadline": req.deadline.isoformat() if req.deadline else None,
        "message": f"Due diligence work order created. Method: {method}. Request ID: {req.request_id}",
    }


def get_due_diligence_result(request_id: str) -> dict:
    """Retrieve a completed due diligence result."""
    if request_id not in _dd_results:
        req = _dd_requests.get(request_id)
        if not req:
            return {"error": f"Request ID {request_id} not found"}
        return {"request_id": request_id, "status": "in_progress", "message": "Investigation still in progress"}

    result = _dd_results[request_id]
    return {
        "request_id": result.request_id,
        "application_id": result.application_id,
        "method": result.method.value,
        "overall_assessment": result.overall_assessment,
        "findings": result.findings,
        "red_flags": result.red_flags,
        "supporting_documents": result.supporting_documents,
        "completed_at": result.completed_at.isoformat(),
    }


def record_credit_decision(
    application_id: str,
    decision: str,
    approved_amount: float | None = None,
    approved_tenure_months: int | None = None,
    interest_rate_bps: int | None = None,
    conditions: list[str] | None = None,
    requires_human_review: bool = False,
) -> dict:
    """Record the final credit decision."""
    record = {
        "application_id": application_id,
        "decision": decision,
        "approved_amount": approved_amount,
        "approved_tenure_months": approved_tenure_months,
        "interest_rate_bps": interest_rate_bps,
        "conditions": conditions or [],
        "requires_human_review": requires_human_review,
        "recorded_at": datetime.utcnow().isoformat(),
    }
    _decisions[application_id] = record
    return {**record, "message": "Credit decision recorded successfully"}


# ---------------------------------------------------------------------------
# Tool dispatcher — maps tool names to implementations
# ---------------------------------------------------------------------------

def execute_tool(tool_name: str, tool_input: dict) -> Any:
    """Execute a tool by name and return its result as a JSON string."""
    handlers = {
        "fetch_internal_data": fetch_internal_data,
        "fetch_scenario_data": fetch_scenario_data,
        "run_quantitative_model": run_quantitative_model,
        "evaluate_risk_rules": evaluate_risk_rules,
        "dispatch_due_diligence": dispatch_due_diligence,
        "get_due_diligence_result": get_due_diligence_result,
        "record_credit_decision": record_credit_decision,
    }
    if tool_name not in handlers:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})
    result = handlers[tool_name](**tool_input)
    return json.dumps(result, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _simulate_dd_completion(req: DueDiligenceRequest) -> None:
    """Stub: simulate due diligence completion synchronously for demo."""
    rng = random.Random(hash(req.request_id))
    assessments = ["positive", "positive", "neutral", "mixed"]
    assessment = rng.choice(assessments)

    findings = {area: f"Investigation of '{area}' completed — {assessment} findings" for area in req.focus_areas}
    red_flags = []
    if assessment == "mixed":
        red_flags.append("Minor inconsistency found in accounts receivable documentation")

    result = DueDiligenceResult(
        request_id=req.request_id,
        application_id=req.application_id,
        method=req.method,
        findings=findings,
        overall_assessment=assessment,
        red_flags=red_flags,
        supporting_documents=[f"doc_{req.request_id}_{i}.pdf" for i in range(rng.randint(2, 5))],
        investigator=rng.choice(["Zhang Wei", "Li Hua", "Wang Fang", "Chen Ming"]),
    )
    _dd_results[req.request_id] = result
    req.status = DueDiligenceStatus.COMPLETED
