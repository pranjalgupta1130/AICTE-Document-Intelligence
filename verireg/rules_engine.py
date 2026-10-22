"""Configurable regulatory rules engine grounded in the AICTE Approval Process Handbook (APH).
Provides explainable compliance checks for land, built-up area, fire safety NOC, FDR, and faculty ratio.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from .schemas import (
    DocumentAnalysisResult,
    EvidenceAnnotation,
    RegulatoryCheckResult,
    SeverityLevel,
)


class RegulatoryRulesEngine:
    """Evaluates institutional application filings against configurable statutory standards.
    
    IMPORTANT: Every regulatory standard is explicitly documented with its statutory verification
    status (is_authoritatively_verified). Benchmarks not explicitly quantified in the APH specification
    are marked unverified and remain fully user-configurable.
    """

    # Authoritative vs Unverified defaults:
    # 1. Fire Safety NOC: Mandated by AICTE Act / APH (Authoritative = True)
    # 2. Digital Signatures: Statutory authentication mandate (Authoritative = True)
    # 3. Land Area, Built-up Area, FDR, SFR: Institution/program/location dependent in APH;
    #    benchmarks provided as unverified configurable baseline defaults.
    DEFAULT_CONFIG = {
        "min_land_area_acres": 2.5,        # Unverified default: Depends on Mega/Metro/Urban/Rural classification in APH
        "min_built_up_area_sqm": 4000.0,   # Unverified default: Depends on program type and approved intake in APH
        "min_fdr_amount_inr": 1500000.0,   # Unverified default: Depends on institution category in APH
        "max_student_faculty_ratio": 20.0, # Authoritative: 1:20 SFR standard for Under Graduate Technical Engineering programs in APH
        "require_fire_noc": True,          # Authoritative: State Fire & Life Safety NOC is mandatory
        "require_digital_signatures": True,# Authoritative: Legal mandate for digital filings
    }

    # Metadata detailing authoritative provenance of rules
    RULE_METADATA = {
        "RULE-LAND-001": {
            "name": "Minimum Contiguous Land Requirement",
            "category": "Land",
            "is_authoritatively_verified": False,
            "verification_note": "Unverified default (2.5 acres); actual statutory land requirement varies by institution category (Mega/Metro/Urban/Rural) under AICTE APH.",
        },
        "RULE-ARCH-002": {
            "name": "Instructional & Administrative Built-Up Area Norm",
            "category": "Building",
            "is_authoritatively_verified": False,
            "verification_note": "Unverified default (4000 sqm); actual statutory carpet area depends on division count, courses, and student intake under AICTE APH.",
        },
        "RULE-FIN-003": {
            "name": "Statutory Joint FDR / Security Deposit",
            "category": "FDR",
            "is_authoritatively_verified": False,
            "verification_note": "Unverified default (INR 15 Lakhs); actual statutory security deposit varies by trust type and approved programs under AICTE APH.",
        },
        "RULE-FIRE-004": {
            "name": "Valid Fire & Life Safety Certificate",
            "category": "FireSafety",
            "is_authoritatively_verified": True,
            "verification_note": "Authoritative: Valid Fire & Life Safety clearance from competent state authority is codified under AICTE statutory compliance.",
        },
        "RULE-ACAD-005": {
            "name": "Cadre & Student-to-Faculty Ratio (SFR)",
            "category": "Faculty",
            "is_authoritatively_verified": True,
            "verification_note": "Authoritative: 1:20 SFR ratio for UG Engineering/Technology programs is mandated in AICTE Approval Process Handbook.",
        },
        "RULE-AUTH-006": {
            "name": "Cryptographic Document Authentication Mandate",
            "category": "Authentication",
            "is_authoritatively_verified": True,
            "verification_note": "Authoritative: Digital signatures required on online statutory submissions under IT Act and AICTE e-governance guidelines.",
        },
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = dict(self.DEFAULT_CONFIG)
        if config:
            self.config.update(config)

    def evaluate(
        self,
        documents: List[DocumentAnalysisResult],
        combined_fields: Dict[str, Any],
        evidences: Dict[str, List[EvidenceAnnotation]],
    ) -> List[RegulatoryCheckResult]:
        results: List[RegulatoryCheckResult] = []

        # 1. Land Area Check
        meta_land = self.RULE_METADATA["RULE-LAND-001"]
        min_land = self.config["min_land_area_acres"]
        land_field = combined_fields.get("land_area_acres")
        if land_field is not None and isinstance(land_field, (int, float)):
            pass_land = land_field >= min_land
            diff = f"{land_field - min_land:+.2f} acres"
            results.append(
                RegulatoryCheckResult(
                    rule_id="RULE-LAND-001",
                    rule_name=meta_land["name"],
                    rule_category=meta_land["category"],
                    status="PASS" if pass_land else "FAIL",
                    severity=SeverityLevel.INFO if pass_land else SeverityLevel.DEFICIENCY,
                    statutory_standard=f">= {min_land} acres (Configured default)",
                    is_authoritatively_verified=meta_land["is_authoritatively_verified"],
                    observed_value=f"{land_field} acres",
                    difference=diff,
                    deficiency_reason=None if pass_land else f"Observed land area ({land_field} acres) is below configured requirement ({min_land} acres). Note: {meta_land['verification_note']}",
                    evidence=evidences.get("land_area_acres", []),
                )
            )
        else:
            results.append(
                RegulatoryCheckResult(
                    rule_id="RULE-LAND-001",
                    rule_name=meta_land["name"],
                    rule_category=meta_land["category"],
                    status="INDETERMINATE",
                    severity=SeverityLevel.WARNING,
                    statutory_standard=f">= {min_land} acres (Configured default)",
                    is_authoritatively_verified=meta_land["is_authoritatively_verified"],
                    observed_value="Not Found in uploaded documents",
                    deficiency_reason=f"Land area documentation not identified or unreadable. Note: {meta_land['verification_note']}",
                )
            )

        # 2. Built-up / Instructional Carpet Area Check
        meta_bua = self.RULE_METADATA["RULE-ARCH-002"]
        min_bua = self.config["min_built_up_area_sqm"]
        bua_field = combined_fields.get("built_up_area_sqm")
        if bua_field is not None and isinstance(bua_field, (int, float)):
            pass_bua = bua_field >= min_bua
            diff = f"{bua_field - min_bua:+.1f} sqm"
            results.append(
                RegulatoryCheckResult(
                    rule_id="RULE-ARCH-002",
                    rule_name=meta_bua["name"],
                    rule_category=meta_bua["category"],
                    status="PASS" if pass_bua else "FAIL",
                    severity=SeverityLevel.INFO if pass_bua else SeverityLevel.DEFICIENCY,
                    statutory_standard=f">= {min_bua} sqm (Configured default)",
                    is_authoritatively_verified=meta_bua["is_authoritatively_verified"],
                    observed_value=f"{bua_field} sqm",
                    difference=diff,
                    deficiency_reason=None if pass_bua else f"Built-up area ({bua_field} sqm) fails configured requirement ({min_bua} sqm). Note: {meta_bua['verification_note']}",
                    evidence=evidences.get("built_up_area_sqm", []),
                )
            )
        else:
            results.append(
                RegulatoryCheckResult(
                    rule_id="RULE-ARCH-002",
                    rule_name=meta_bua["name"],
                    rule_category=meta_bua["category"],
                    status="INDETERMINATE",
                    severity=SeverityLevel.WARNING,
                    statutory_standard=f">= {min_bua} sqm (Configured default)",
                    is_authoritatively_verified=meta_bua["is_authoritatively_verified"],
                    observed_value="Not Found in uploaded documents",
                    deficiency_reason=f"Architectural blueprint carpet area not found. Note: {meta_bua['verification_note']}",
                )
            )

        # 3. Fixed Deposit / Security Lien Check
        meta_fdr = self.RULE_METADATA["RULE-FIN-003"]
        min_fdr = self.config["min_fdr_amount_inr"]
        fdr_field = combined_fields.get("fdr_amount_inr")
        if fdr_field is not None and isinstance(fdr_field, (int, float)):
            pass_fdr = fdr_field >= min_fdr
            diff = f"INR {fdr_field - min_fdr:+,.2f}"
            results.append(
                RegulatoryCheckResult(
                    rule_id="RULE-FIN-003",
                    rule_name=meta_fdr["name"],
                    rule_category=meta_fdr["category"],
                    status="PASS" if pass_fdr else "FAIL",
                    severity=SeverityLevel.INFO if pass_fdr else SeverityLevel.DEFICIENCY,
                    statutory_standard=f">= INR {min_fdr:,.2f} (Configured default)",
                    is_authoritatively_verified=meta_fdr["is_authoritatively_verified"],
                    observed_value=f"INR {fdr_field:,.2f}",
                    difference=diff,
                    deficiency_reason=None if pass_fdr else f"FDR amount (INR {fdr_field:,.2f}) does not meet configured requirement of INR {min_fdr:,.2f}. Note: {meta_fdr['verification_note']}",
                    evidence=evidences.get("fdr_amount_inr", []),
                )
            )
        else:
            results.append(
                RegulatoryCheckResult(
                    rule_id="RULE-FIN-003",
                    rule_name=meta_fdr["name"],
                    rule_category=meta_fdr["category"],
                    status="INDETERMINATE",
                    severity=SeverityLevel.WARNING,
                    statutory_standard=f">= INR {min_fdr:,.2f} (Configured default)",
                    is_authoritatively_verified=meta_fdr["is_authoritatively_verified"],
                    observed_value="Not Found in uploaded documents",
                    deficiency_reason=f"FDR receipt / lien endorsement not identified. Note: {meta_fdr['verification_note']}",
                )
            )

        # 4. Fire Safety NOC Status
        if self.config.get("require_fire_noc"):
            meta_fire = self.RULE_METADATA["RULE-FIRE-004"]
            fire_status = combined_fields.get("fire_safety_noc_status")
            if fire_status:
                valid_statuses = ["VALID", "ISSUED", "COMPLIANT", "APPROVED"]
                pass_fire = str(fire_status).upper() in valid_statuses
                results.append(
                    RegulatoryCheckResult(
                        rule_id="RULE-FIRE-004",
                        rule_name=meta_fire["name"],
                        rule_category=meta_fire["category"],
                        status="PASS" if pass_fire else "FAIL",
                        severity=SeverityLevel.INFO if pass_fire else SeverityLevel.CRITICAL,
                        statutory_standard="Active/Valid Fire NOC from State Fire Authority",
                        is_authoritatively_verified=meta_fire["is_authoritatively_verified"],
                        observed_value=str(fire_status),
                        deficiency_reason=None if pass_fire else f"Fire safety certificate status is '{fire_status}' (must be valid/active).",
                        evidence=evidences.get("fire_safety_noc_status", []),
                    )
                )
            else:
                results.append(
                    RegulatoryCheckResult(
                        rule_id="RULE-FIRE-004",
                        rule_name=meta_fire["name"],
                        rule_category=meta_fire["category"],
                        status="FAIL",
                        severity=SeverityLevel.CRITICAL,
                        statutory_standard="Active/Valid Fire NOC from State Fire Authority",
                        is_authoritatively_verified=meta_fire["is_authoritatively_verified"],
                        observed_value="Missing",
                        deficiency_reason="Mandatory Fire & Life Safety NOC was not detected in submitted documents.",
                    )
                )

        # 5. Student Faculty Ratio Check
        meta_sfr = self.RULE_METADATA["RULE-ACAD-005"]
        max_sfr = self.config["max_student_faculty_ratio"]
        sfr_field = combined_fields.get("student_faculty_ratio")
        if sfr_field is not None and isinstance(sfr_field, (int, float)):
            pass_sfr = sfr_field <= max_sfr
            results.append(
                RegulatoryCheckResult(
                    rule_id="RULE-ACAD-005",
                    rule_name=meta_sfr["name"],
                    rule_category=meta_sfr["category"],
                    status="PASS" if pass_sfr else "FAIL",
                    severity=SeverityLevel.INFO if pass_sfr else SeverityLevel.DEFICIENCY,
                    statutory_standard=f"<= {max_sfr}:1 (AICTE Handbook Mandate)",
                    is_authoritatively_verified=meta_sfr["is_authoritatively_verified"],
                    observed_value=f"{sfr_field}:1",
                    difference=f"{sfr_field - max_sfr:+.1f}",
                    deficiency_reason=None if pass_sfr else f"Student-to-Faculty ratio ({sfr_field}:1) exceeds upper permissible limit ({max_sfr}:1).",
                    evidence=evidences.get("student_faculty_ratio", []),
                )
            )

        # 6. Digital Signature Mandate Check
        if self.config.get("require_digital_signatures"):
            meta_sig = self.RULE_METADATA["RULE-AUTH-006"]
            signed_docs = [d for d in documents if d.signatures.has_signatures]
            has_valid_sigs = any(d.signatures.signatures_detected for d in signed_docs)
            if signed_docs:
                results.append(
                    RegulatoryCheckResult(
                        rule_id="RULE-AUTH-006",
                        rule_name=meta_sig["name"],
                        rule_category=meta_sig["category"],
                        status="PASS" if has_valid_sigs else "FAIL",
                        severity=SeverityLevel.INFO if has_valid_sigs else SeverityLevel.CRITICAL,
                        statutory_standard="Valid DSC/PKCS#7 signature on statutory filings",
                        is_authoritatively_verified=meta_sig["is_authoritatively_verified"],
                        observed_value=f"{len(signed_docs)} signed documents found",
                        deficiency_reason=None if has_valid_sigs else "Digital signature dictionaries contain validation anomalies or invalid structures.",
                    )
                )
            else:
                results.append(
                    RegulatoryCheckResult(
                        rule_id="RULE-AUTH-006",
                        rule_name=meta_sig["name"],
                        rule_category=meta_sig["category"],
                        status="INDETERMINATE",
                        severity=SeverityLevel.WARNING,
                        statutory_standard="Valid DSC/PKCS#7 signature on statutory filings",
                        is_authoritatively_verified=meta_sig["is_authoritatively_verified"],
                        observed_value="No digital signatures found (rasterized/scanned submission)",
                        deficiency_reason="Document submission lacks embedded CMS/PKCS#7 signature.",
                    )
                )

        return results

