"""Findings & Risk Stratification Engine.
Calculates an aggregate anomaly score and routes applications to:
1. ACCELERATED (0-20 score): Clean, compliant application
2. CLARIFICATION (21-60 score): Minor clerical variances, non-critical deficiencies
3. ESCALATION (61-100 score): Critical red flags, signature anomalies, duplicate assets, severe statutory breach
"""

from __future__ import annotations
from typing import List, Tuple
from .schemas import (
    CrossDocConsistencyResult,
    DuplicateDetectionResult,
    RegulatoryCheckResult,
    RiskTier,
    SeverityLevel,
)


class RiskPrioritizationEngine:
    """Computes explainable anomaly risk scores and workflow routing recommendations.
    
    IMPORTANT: Risk scores and finding flags are triage priority metrics to focus human scrutiny.
    They NEVER constitute legal proof of fraud or forgery, nor automatic grounds for rejection.
    Every point added to the score is recorded in `findings_audit_trail` with transparent reasoning.
    """

    # Explicit penalty weights per finding type
    WEIGHT_CRITICAL_RULE = 45.0
    WEIGHT_DEFICIENCY_RULE = 20.0
    WEIGHT_WARNING_RULE = 5.0

    WEIGHT_CRITICAL_CONSISTENCY = 35.0
    WEIGHT_DEFICIENCY_CONSISTENCY = 15.0

    WEIGHT_EXACT_DUPLICATE = 50.0
    WEIGHT_PERCEPTUAL_DUPLICATE = 30.0

    def evaluate(
        self,
        rule_evaluations: List[RegulatoryCheckResult],
        consistency_evaluations: List[CrossDocConsistencyResult],
        duplicate_evaluations: DuplicateDetectionResult,
    ) -> Tuple[RiskTier, float, List[Dict[str, Any]], List[str], List[str], List[str]]:
        """Returns: (RiskTier, risk_score, findings_audit_trail, critical_deficiencies, clarification_notes, recommendations)"""
        raw_score = 0.0
        findings_audit_trail: List[Dict[str, Any]] = []
        critical_deficiencies: List[str] = []
        clarification_notes: List[str] = []
        recommendations: List[str] = []

        # 1. Evaluate Rule Deficiencies
        for rule in rule_evaluations:
            if rule.status == "FAIL":
                if rule.severity == SeverityLevel.CRITICAL:
                    points = self.WEIGHT_CRITICAL_RULE
                    raw_score += points
                    msg = f"Critical Failure [{rule.rule_id}]: {rule.deficiency_reason or rule.rule_name}"
                    critical_deficiencies.append(msg)
                    recommendations.append(f"Immediate rectification required: {rule.rule_name}")
                    findings_audit_trail.append({
                        "category": "Regulatory Rule",
                        "rule_id": rule.rule_id,
                        "finding": msg,
                        "severity": rule.severity.value,
                        "score_penalty": points,
                        "is_authoritatively_verified": rule.is_authoritatively_verified,
                    })
                elif rule.severity == SeverityLevel.DEFICIENCY:
                    points = self.WEIGHT_DEFICIENCY_RULE
                    raw_score += points
                    msg = f"Deficiency [{rule.rule_id}]: {rule.deficiency_reason or rule.rule_name}"
                    critical_deficiencies.append(msg)
                    recommendations.append(f"Address deficiency: {rule.rule_name} ({rule.observed_value} vs standard {rule.statutory_standard})")
                    findings_audit_trail.append({
                        "category": "Regulatory Rule",
                        "rule_id": rule.rule_id,
                        "finding": msg,
                        "severity": rule.severity.value,
                        "score_penalty": points,
                        "is_authoritatively_verified": rule.is_authoritatively_verified,
                    })
            elif rule.status == "INDETERMINATE":
                points = self.WEIGHT_WARNING_RULE
                raw_score += points
                msg = f"Indeterminate [{rule.rule_id}]: {rule.deficiency_reason or 'Field unverified'}"
                clarification_notes.append(msg)
                findings_audit_trail.append({
                    "category": "Regulatory Rule",
                    "rule_id": rule.rule_id,
                    "finding": msg,
                    "severity": rule.severity.value,
                    "score_penalty": points,
                    "is_authoritatively_verified": rule.is_authoritatively_verified,
                })

        # 2. Evaluate Cross-Doc Inconsistencies
        for c in consistency_evaluations:
            if not c.is_consistent:
                if c.severity == SeverityLevel.CRITICAL:
                    points = self.WEIGHT_CRITICAL_CONSISTENCY
                    raw_score += points
                    msg = f"Data Conflict [{c.check_name}]: {c.discrepancy_details}"
                    critical_deficiencies.append(msg)
                    recommendations.append(f"Resolve conflicting identifier data between: {', '.join(c.documents_involved)}")
                    findings_audit_trail.append({
                        "category": "Cross-Document Reconciliation",
                        "finding": msg,
                        "severity": c.severity.value,
                        "score_penalty": points,
                    })
                else:
                    points = self.WEIGHT_DEFICIENCY_CONSISTENCY
                    raw_score += points
                    msg = f"Reconciliation Note [{c.check_name}]: {c.discrepancy_details}"
                    clarification_notes.append(msg)
                    recommendations.append(f"Submit clarification or affidavit for: {c.check_name}")
                    findings_audit_trail.append({
                        "category": "Cross-Document Reconciliation",
                        "finding": msg,
                        "severity": c.severity.value,
                        "score_penalty": points,
                    })

        # 3. Evaluate Duplicate Findings
        if duplicate_evaluations.exact_duplicates:
            points = self.WEIGHT_EXACT_DUPLICATE
            raw_score += points
            msg = f"Exact Document Duplication detected: {len(duplicate_evaluations.exact_duplicates)} identical file pair(s) submitted."
            critical_deficiencies.append(msg)
            recommendations.append("Audit duplicate file uploads to ensure correct attachments are submitted.")
            findings_audit_trail.append({
                "category": "Duplicate Detection",
                "finding": msg,
                "severity": SeverityLevel.CRITICAL.value,
                "score_penalty": points,
            })

        if duplicate_evaluations.perceptual_image_duplicates:
            points = self.WEIGHT_PERCEPTUAL_DUPLICATE
            raw_score += points
            msg = f"Visual Asset Duplication detected: {len(duplicate_evaluations.perceptual_image_duplicates)} image asset(s) match across pages/files."
            critical_deficiencies.append(msg)
            recommendations.append("Scrutinize visual documentation for potential asset reuse via Expert Visit Committee (EVC).")
            findings_audit_trail.append({
                "category": "Duplicate Detection",
                "finding": msg,
                "severity": SeverityLevel.DEFICIENCY.value,
                "score_penalty": points,
            })

        # Cap score at 100.0
        final_score = min(100.0, round(raw_score, 1))

        # Determine Tier
        if final_score <= 20.0 and len(critical_deficiencies) == 0:
            tier = RiskTier.ACCELERATED
            if not recommendations:
                recommendations.append("Eligible for accelerated administrative approval track.")
        elif final_score <= 60.0 and len(critical_deficiencies) <= 1:
            tier = RiskTier.CLARIFICATION
            recommendations.append("Issue automated deficiency memo; allow institutional response within 14 calendar days.")
        else:
            tier = RiskTier.ESCALATION
            recommendations.append("Escalate file for Standing Hearing Committee (SHC) review and on-site Expert Visit Committee (EVC) scrutiny.")

        return tier, final_score, findings_audit_trail, critical_deficiencies, clarification_notes, recommendations
