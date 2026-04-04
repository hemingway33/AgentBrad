"""
Risk Assessment Service - Orchestrates the full credit risk assessment pipeline.

Brings together:
1. Data integration (multi-source data collection)
2. Graph construction (knowledge graph)
3. Reasoning engine (rule evaluation)
4. Result persistence (risk profiles)

This is the main entry point for assessing enterprise credit risk,
supporting: anti-fraud, KYB, risk rating, credit assessment, post-loan monitoring.
"""

from django.utils import timezone

from credit_risk_ontology.models.entities import Enterprise
from credit_risk_ontology.models.indicators import (
    RiskScore, ComprehensiveRiskProfile,
)
from credit_risk_ontology.graph.storage import GraphStorageManager
from credit_risk_ontology.graph.traversal import (
    RiskPropagationTraversal,
    CircularGuaranteeDetector,
    ShellCompanyDetector,
    ConcentrationRiskAnalyzer,
)
from credit_risk_ontology.graph.query import PatternMatcher
from credit_risk_ontology.reasoning.engine import ReasoningEngine, ReasoningContext
from credit_risk_ontology.reasoning.rules import get_standard_rules
from .data_integration import DataIntegrationService


class RiskAssessmentService:
    """
    End-to-end credit risk assessment for supply chain enterprises.
    """

    def __init__(self):
        self.engine = ReasoningEngine()
        self.engine.register_rules(get_standard_rules())

    def assess_enterprise(self, enterprise_id: int) -> dict:
        """
        Run full credit risk assessment for an enterprise.

        Pipeline:
        1. Collect multi-source data
        2. Build knowledge graph
        3. Run graph analysis (cycles, shells, concentration)
        4. Compute derived indicators
        5. Run reasoning engine rules
        6. Aggregate and persist results
        """
        # Step 1: Collect data
        raw_data = DataIntegrationService.collect_enterprise_data(enterprise_id)

        # Step 2: Build graph
        graph = GraphStorageManager.build_enterprise_subgraph(enterprise_id, max_depth=2)

        # Step 3: Graph analysis
        graph_analysis = self._run_graph_analysis(enterprise_id, graph)

        # Step 4: Compute indicators
        indicators = DataIntegrationService.compute_derived_indicators(
            enterprise_id, raw_data,
        )
        DataIntegrationService.save_indicator_values(enterprise_id, indicators)

        # Step 5: Build reasoning context and run rules
        context = ReasoningContext(
            enterprise_id=enterprise_id,
            enterprise_data=raw_data.get('enterprise', {}),
            graph_data=graph_analysis,
            indicator_values=indicators,
            data_sources=raw_data,
        )

        # Add extra enterprise data for credit assessment
        ent = Enterprise.objects.get(id=enterprise_id)
        context.enterprise_data.update({
            'total_assets': raw_data.get('tax_financial', {}).get('total_assets', 0),
            'registered_capital': float(ent.registered_capital or 0),
            'years_operating': self._compute_years_operating(ent),
        })

        # Check core enterprise profile
        if hasattr(ent, 'core_profile'):
            context.enterprise_data['is_core_supplier'] = True
            context.enterprise_data['whitelist_grade'] = ent.core_profile.whitelist_grade

        # Check shell company profile
        if hasattr(ent, 'shell_profile'):
            context.data_sources['shell_profile'] = {
                'has_real_office': ent.shell_profile.has_real_office,
                'has_real_employees': ent.shell_profile.has_real_employees,
                'has_real_business': ent.shell_profile.has_real_business,
                'tax_anomaly_score': ent.shell_profile.tax_anomaly_score,
            }

        rule_results = self.engine.evaluate(context)

        # Step 6: Aggregate and persist
        aggregated = self.engine.aggregate_results(rule_results)
        self._persist_results(enterprise_id, aggregated)

        return aggregated

    def _run_graph_analysis(self, enterprise_id: int, graph) -> dict:
        """Run all graph-based analyses."""
        analysis = {}

        # Circular guarantee detection
        detector = CircularGuaranteeDetector(graph)
        circles = detector.detect_all_circles()
        analysis['circular_guarantees'] = [
            {
                'cycle': c.cycle,
                'names': c.cycle_names,
                'amount': c.total_guarantee_amount,
                'severity': c.risk_severity,
            }
            for c in circles
        ]

        # Shell company detection
        shell_detector = ShellCompanyDetector(graph)
        suspicious = shell_detector.detect_suspicious_nodes()
        analysis['suspicious_shells'] = suspicious

        # Concentration risk
        concentration_analyzer = ConcentrationRiskAnalyzer(graph)
        concentration = concentration_analyzer.analyze_enterprise(enterprise_id)
        analysis['concentration'] = {
            'customer_hhi': next(
                (c.concentration_ratio for c in concentration
                 if c.concentration_type == 'CUSTOMER'), 0,
            ),
            'supplier_hhi': next(
                (c.concentration_ratio for c in concentration
                 if c.concentration_type == 'SUPPLIER'), 0,
            ),
        }

        # Transaction pattern matching
        matcher = PatternMatcher(graph)
        analysis['transaction_triangles'] = matcher.match_triangle('TRANSACTION')

        # Risk propagation
        propagation = RiskPropagationTraversal(graph)
        high_risk_nodes = [
            n for n in graph.nodes.values()
            if n.risk_score > 70
        ]
        analysis['risk_propagation'] = []
        for node in high_risk_nodes[:5]:  # Top 5 high-risk nodes
            results = propagation.propagate_from_node(node.id, max_depth=2)
            analysis['risk_propagation'].extend([
                {
                    'source': node.name,
                    'target': r.node_name,
                    'propagated_risk': r.propagated_risk,
                    'path': r.risk_path,
                }
                for r in results[:3]
            ])

        # Graph stats
        analysis['graph_stats'] = {
            'node_count': graph.node_count,
            'edge_count': graph.edge_count,
        }

        return analysis

    def _persist_results(self, enterprise_id: int, aggregated: dict):
        """Persist assessment results to the database."""
        enterprise = Enterprise.objects.get(id=enterprise_id)

        # Save per-category risk scores
        for category, score in aggregated.get('category_scores', {}).items():
            RiskScore.objects.create(
                enterprise=enterprise,
                score_type='DIMENSION',
                dimension=category,
                score=score,
                risk_level=self._score_to_level(score),
            )

        # Save comprehensive profile
        overall_level = aggregated.get('overall_risk_level', 'MEDIUM')
        overall_score = aggregated.get('overall_score', 50)

        profile = ComprehensiveRiskProfile.objects.create(
            enterprise=enterprise,
            overall_score=overall_score,
            overall_risk_level=overall_level,
            dimension_scores=aggregated.get('category_scores', {}),
            risk_alerts=aggregated.get('alerts', []),
            evaluated_at=timezone.now(),
        )

        # Update enterprise risk level
        enterprise.risk_level = overall_level
        enterprise.risk_score = overall_score
        enterprise.save(update_fields=['risk_level', 'risk_score'])

        return profile

    @staticmethod
    def _compute_years_operating(enterprise: Enterprise) -> float:
        if enterprise.establishment_date:
            delta = timezone.now().date() - enterprise.establishment_date
            return delta.days / 365.25
        return 0

    @staticmethod
    def _score_to_level(score: float) -> str:
        if score >= 90:
            return 'D'
        elif score >= 75:
            return 'CC'
        elif score >= 60:
            return 'B'
        elif score >= 45:
            return 'BB'
        elif score >= 30:
            return 'BBB'
        elif score >= 15:
            return 'A'
        return 'AAA'

    def batch_assess(self, enterprise_ids: list[int]) -> list[dict]:
        """Run assessment for multiple enterprises."""
        results = []
        for eid in enterprise_ids:
            try:
                result = self.assess_enterprise(eid)
                result['enterprise_id'] = eid
                results.append(result)
            except Exception as e:
                results.append({
                    'enterprise_id': eid,
                    'error': str(e),
                })
        return results
