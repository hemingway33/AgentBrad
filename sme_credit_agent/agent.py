"""
SME Credit Analysis Agent (信贷分析助理).

The left panel of the diagram. A Claude-powered agent that:
1. Accepts an SME credit application
2. Fetches internal data + scenario data (via tools)
3. Runs quantitative models and risk rule evaluation (via tools)
4. Synthesizes findings into a structured analysis report:
   - Three business highlights (三大经营亮点)
   - Three risk concerns (三个风险关注点)
   - Final credit recommendation
5. Optionally dispatches due diligence work orders (via tools)
6. Records the final decision (via tool)

Uses Claude Opus 4.6 with adaptive thinking for complex credit analysis.
Streams output for real-time display.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Iterator, Optional

import anthropic

from .models import CreditApplication, CreditAnalysisReport
from .tools import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger(__name__)

MODEL = "claude-opus-4-6"

SYSTEM_PROMPT = """你是专业的信贷分析助理，为银行提供中小企业（SME）信用风险评估服务。

你的核心职责：
1. **数据调取**：使用工具获取申请企业的内部数据（还款历史、账户活动）和场景数据（行业风险、产业链地位）
2. **模型评估**：运行量化信用评分模型，评估违约概率和预期损失
3. **规则核查**：执行风控规则集，识别合规风险和集中度风险
4. **综合分析**：从以下维度全面评估企业信用风险：
   - 经营可持续性（盈利能力、现金流稳定性）
   - 过往贷款履约情况（还款记录、违约历史）
   - 产品竞争力（市场份额、技术壁垒）
   - 产业链地位（上下游话语权、替代风险）
   - 发展前景（行业趋势、政策支持）
5. **尽调派发**：根据风险等级决定是否需要派发尽调工单（电话核查/视频尽调/下户调查）
6. **决策记录**：将最终授信建议录入系统

输出格式要求：
- **三大经营亮点**：列出企业最强的三个经营优势
- **三个风险关注点**：列出最重要的三个潜在风险
- **授信建议**：明确说明建议授信金额、期限、利率及附加条件

分析时保持客观专业，数据驱动，但也要结合定性判断。对于高风险案例，主动建议尽调方案。"""


class SMECreditAgent:
    """
    SME Credit Analysis Agent.

    Wraps a Claude-powered agentic loop with the bank's credit analysis tools.
    Produces a structured CreditAnalysisReport and records the decision.

    Usage:
        agent = SMECreditAgent()
        report = agent.analyze(application)
        # or for streaming:
        for chunk in agent.analyze_stream(application):
            print(chunk, end="", flush=True)
    """

    def __init__(self, api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )

    def analyze(self, application: CreditApplication) -> CreditAnalysisReport:
        """
        Run the full credit analysis for an SME application.
        Returns a structured CreditAnalysisReport.
        """
        full_text = ""
        for chunk in self.analyze_stream(application):
            full_text += chunk

        return self._parse_report(application, full_text)

    def analyze_stream(self, application: CreditApplication) -> Iterator[str]:
        """
        Stream the credit analysis in real-time.
        Yields text chunks as Claude produces them.
        """
        messages = [
            {"role": "user", "content": self._build_user_prompt(application)}
        ]

        logger.info("Starting credit analysis for application %s", application.application_id)

        # Agentic loop: keep going until Claude stops calling tools
        while True:
            with self.client.messages.stream(
                model=MODEL,
                max_tokens=8192,
                thinking={"type": "adaptive"},
                system=SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            ) as stream:
                # Stream text deltas in real-time
                for event in stream:
                    if (
                        event.type == "content_block_delta"
                        and event.delta.type == "text_delta"
                    ):
                        yield event.delta.text

                final = stream.get_final_message()

            # Append the assistant's response to history
            messages.append({"role": "assistant", "content": final.content})

            if final.stop_reason == "end_turn":
                break

            if final.stop_reason != "tool_use":
                logger.warning("Unexpected stop reason: %s", final.stop_reason)
                break

            # Execute all tool calls and collect results
            tool_results = []
            for block in final.content:
                if block.type == "tool_use":
                    logger.info("Executing tool: %s", block.name)
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "user", "content": tool_results})

    def _build_user_prompt(self, app: CreditApplication) -> str:
        """Build the initial user message from the credit application."""
        purpose_labels = {
            "raw_material": "采购原材料",
            "equipment": "购置设备",
            "working_capital": "补充流动资金",
            "expansion": "扩大经营",
            "other": "其他用途",
        }
        collateral_labels = {
            "credit": "信用",
            "mortgage": "抵押",
            "pledge": "质押",
            "guarantee": "第三方保证",
        }
        focus_areas = ""
        if app.special_focus_areas:
            focus_areas = f"\n特别关注：{', '.join(app.special_focus_areas)}"

        return f"""{app.registration_province} {app.company_name} 向我行申请授信，担保方式为{collateral_labels.get(app.collateral_type.value, app.collateral_type.value)}，\
客户资金需求{app.loan_amount:.0f}万元，贷款用于{purpose_labels.get(app.loan_purpose.value, app.loan_purpose.value)}，\
期限{app.loan_tenure_months}个月。{focus_areas}

请研究这家企业的信用风险情况，重点从经营可持续性、过往贷款履约情况、产品竞争力、产业链地位、发展前景等维度，\
梳理该客户三大经营亮点，以及三个风险关注点，给出最终授信建议。\
对于潜在风险点，可以派出尽调工单，列清尽调层次要求，会由尽调系统执行。我会将尽调结果反馈给你进一步决策。

申请编号：{app.application_id}
行业：{app.industry or '未填写'}
注册地：{app.registration_province}"""

    def _parse_report(
        self,
        application: CreditApplication,
        analysis_text: str,
    ) -> CreditAnalysisReport:
        """
        Parse the agent's text output into a structured CreditAnalysisReport.
        Uses a lightweight extraction pass — in production this would use
        structured output (output_config.format with JSON schema).
        """
        # Extract key sections using a quick Claude call for structured output
        extraction_prompt = f"""从以下信贷分析报告中提取结构化信息，以JSON格式返回：

分析报告：
{analysis_text}

请提取并返回以下JSON结构（所有字段必须填写，如信息不足则填写合理推断值）：
{{
  "business_highlights": ["亮点1", "亮点2", "亮点3"],
  "risk_concerns": ["风险1", "风险2", "风险3"],
  "operational_sustainability_analysis": "...",
  "repayment_history_analysis": "...",
  "product_competitiveness_analysis": "...",
  "supply_chain_position_analysis": "...",
  "development_prospects_analysis": "...",
  "credit_recommendation": "...",
  "recommended_amount": 数字（万元）,
  "confidence_level": "high|medium|low",
  "suggested_dd_focus_areas": ["尽调重点1", "尽调重点2"]
}}"""

        response = self.client.messages.create(
            model=MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": extraction_prompt}],
        )

        text = next(
            (b.text for b in response.content if b.type == "text"),
            "{}"
        )

        # Strip markdown code fences if present
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        try:
            data = json.loads(text.strip())
        except json.JSONDecodeError:
            logger.warning("Failed to parse structured output, using defaults")
            data = {}

        return CreditAnalysisReport(
            application_id=application.application_id,
            company_name=application.company_name,
            business_highlights=data.get("business_highlights", ["(解析失败)"]),
            risk_concerns=data.get("risk_concerns", ["(解析失败)"]),
            operational_sustainability_analysis=data.get("operational_sustainability_analysis", ""),
            repayment_history_analysis=data.get("repayment_history_analysis", ""),
            product_competitiveness_analysis=data.get("product_competitiveness_analysis", ""),
            supply_chain_position_analysis=data.get("supply_chain_position_analysis", ""),
            development_prospects_analysis=data.get("development_prospects_analysis", ""),
            credit_recommendation=data.get("credit_recommendation", analysis_text[-500:]),
            recommended_amount=float(data.get("recommended_amount", application.loan_amount * 0.8)),
            confidence_level=data.get("confidence_level", "medium"),
            suggested_dd_focus_areas=data.get("suggested_dd_focus_areas", []),
        )
