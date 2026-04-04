"""
Logic-on-Ontology Reasoning Engine.

Implements Palantir's "Logic on Ontology" paradigm:
- Rules are defined as typed functions over ontology objects
- Rules compose through a forward-chaining inference engine
- Each rule produces typed outputs (risk scores, alerts, flags)
- Rules can reference other rules' outputs (dependency graph)

The engine evaluates rules in topological order based on dependencies.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional
import logging

logger = logging.getLogger(__name__)


class RuleStatus(Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    SKIPPED = 'skipped'


class AlertSeverity(Enum):
    INFO = 'info'
    WARNING = 'warning'
    HIGH = 'high'
    CRITICAL = 'critical'


@dataclass
class RuleResult:
    """Result produced by a single rule evaluation."""
    rule_name: str
    status: RuleStatus
    score: float = 0.0
    risk_level: str = ''
    alerts: list[dict] = field(default_factory=list)
    details: dict = field(default_factory=dict)
    error: str = ''


@dataclass
class RuleDefinition:
    """A rule in the reasoning engine."""
    name: str
    description: str
    category: str  # 'ANTI_FRAUD', 'KYB', 'RISK_RATING', 'CREDIT', 'POST_LOAN'
    weight: float = 1.0
    dependencies: list[str] = field(default_factory=list)
    evaluator: Optional[Callable] = None
    # Thresholds for auto-classification
    thresholds: dict = field(default_factory=lambda: {
        'low': 25, 'medium': 50, 'high': 75, 'critical': 90,
    })


@dataclass
class ReasoningContext:
    """
    Context object passed to each rule during evaluation.
    Contains the enterprise data, graph, and results from prior rules.
    """
    enterprise_id: int
    enterprise_data: dict = field(default_factory=dict)
    graph_data: dict = field(default_factory=dict)
    indicator_values: dict = field(default_factory=dict)
    data_sources: dict = field(default_factory=dict)
    prior_results: dict = field(default_factory=dict)  # rule_name -> RuleResult
    metadata: dict = field(default_factory=dict)


class ReasoningEngine:
    """
    Forward-chaining rule engine for credit risk assessment.

    Rules are registered with dependencies. The engine:
    1. Builds a dependency graph of rules
    2. Topologically sorts them
    3. Evaluates each rule in order, passing prior results as context
    4. Aggregates results into a comprehensive risk assessment
    """

    def __init__(self):
        self.rules: dict[str, RuleDefinition] = {}
        self._evaluation_order: list[str] = []

    def register_rule(self, rule: RuleDefinition):
        """Register a rule with the engine."""
        self.rules[rule.name] = rule
        self._evaluation_order = []  # Invalidate cached order

    def register_rules(self, rules: list[RuleDefinition]):
        for rule in rules:
            self.register_rule(rule)

    def _compute_evaluation_order(self) -> list[str]:
        """Topological sort of rules based on dependencies."""
        if self._evaluation_order:
            return self._evaluation_order

        in_degree = {name: 0 for name in self.rules}
        graph = {name: [] for name in self.rules}

        for name, rule in self.rules.items():
            for dep in rule.dependencies:
                if dep in self.rules:
                    graph[dep].append(name)
                    in_degree[name] += 1

        queue = [name for name, deg in in_degree.items() if deg == 0]
        order = []

        while queue:
            current = queue.pop(0)
            order.append(current)
            for neighbor in graph.get(current, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(self.rules):
            # Circular dependency - add remaining rules
            remaining = set(self.rules.keys()) - set(order)
            logger.warning(f"Circular dependencies detected in rules: {remaining}")
            order.extend(remaining)

        self._evaluation_order = order
        return order

    def evaluate(self, context: ReasoningContext) -> dict[str, RuleResult]:
        """
        Evaluate all registered rules for a given enterprise context.
        Returns a mapping of rule_name -> RuleResult.
        """
        order = self._compute_evaluation_order()
        results = {}

        for rule_name in order:
            rule = self.rules[rule_name]

            # Check dependencies are satisfied
            unmet_deps = [
                dep for dep in rule.dependencies
                if dep not in results or results[dep].status != RuleStatus.COMPLETED
            ]
            if unmet_deps:
                results[rule_name] = RuleResult(
                    rule_name=rule_name,
                    status=RuleStatus.SKIPPED,
                    error=f"Unmet dependencies: {unmet_deps}",
                )
                continue

            # Pass prior results to context
            context.prior_results = {k: v for k, v in results.items()}

            try:
                if rule.evaluator:
                    result = rule.evaluator(context, rule)
                else:
                    result = RuleResult(
                        rule_name=rule_name,
                        status=RuleStatus.SKIPPED,
                        error="No evaluator defined",
                    )

                # Auto-classify risk level from score if not set
                if result.score > 0 and not result.risk_level:
                    result.risk_level = self._classify_risk(result.score, rule.thresholds)

                results[rule_name] = result

            except Exception as e:
                logger.error(f"Rule {rule_name} failed: {e}")
                results[rule_name] = RuleResult(
                    rule_name=rule_name,
                    status=RuleStatus.FAILED,
                    error=str(e),
                )

        return results

    def aggregate_results(
        self, results: dict[str, RuleResult],
    ) -> dict:
        """
        Aggregate individual rule results into category-level
        and overall risk scores.
        """
        category_scores = {}
        category_weights = {}

        for rule_name, result in results.items():
            if result.status != RuleStatus.COMPLETED:
                continue
            rule = self.rules.get(rule_name)
            if not rule:
                continue

            cat = rule.category
            if cat not in category_scores:
                category_scores[cat] = 0.0
                category_weights[cat] = 0.0

            category_scores[cat] += result.score * rule.weight
            category_weights[cat] += rule.weight

        # Normalize category scores
        normalized = {}
        for cat, score in category_scores.items():
            weight = category_weights[cat]
            normalized[cat] = round(score / weight, 2) if weight > 0 else 0

        # Overall score (weighted average of categories)
        total_score = sum(normalized.values())
        total_categories = len(normalized)
        overall = round(total_score / total_categories, 2) if total_categories > 0 else 0

        # Collect all alerts
        all_alerts = []
        for result in results.values():
            all_alerts.extend(result.alerts)
        all_alerts.sort(key=lambda a: {'critical': 0, 'high': 1, 'warning': 2, 'info': 3}.get(
            a.get('severity', 'info'), 4,
        ))

        return {
            'overall_score': overall,
            'overall_risk_level': self._classify_risk(overall),
            'category_scores': normalized,
            'alerts': all_alerts,
            'rule_results': {
                name: {
                    'score': r.score,
                    'risk_level': r.risk_level,
                    'status': r.status.value,
                    'details': r.details,
                }
                for name, r in results.items()
            },
        }

    @staticmethod
    def _classify_risk(
        score: float,
        thresholds: Optional[dict] = None,
    ) -> str:
        thresholds = thresholds or {'low': 25, 'medium': 50, 'high': 75, 'critical': 90}
        if score >= thresholds.get('critical', 90):
            return 'CRITICAL'
        elif score >= thresholds.get('high', 75):
            return 'HIGH'
        elif score >= thresholds.get('medium', 50):
            return 'MEDIUM'
        return 'LOW'
