"""CSV export utilities for batch validation findings and data-quality results.

Converts a ``PipelineRunResult`` into a downloadable CSV report suitable for
AICTE statutory review and institution audit workflows.

Design decisions
----------------
* **No new dependencies** – uses only Python stdlib ``csv`` and ``io``.
* **Formula-injection protection** – any cell value whose first character is one
  of ``= + - @ | %`` (common spreadsheet formula prefixes) is prefixed with a
  single-quote so that spreadsheet applications treat it as plain text.
* **Stable column order** – columns are declared explicitly so downstream
  tooling that parses by position remains compatible across releases.
* **No validation logic duplication** – all findings are taken verbatim from the
  already-evaluated ``PipelineRunResult``; this module only formats them.
"""

from __future__ import annotations

import csv
import io
from typing import List

from .schemas import (
    CrossDocConsistencyResult,
    DuplicateDetectionResult,
    PipelineRunResult,
    RegulatoryCheckResult,
)

# Characters that, when at the start of a CSV cell, trigger formula execution
# in Microsoft Excel, LibreOffice Calc, and Google Sheets.
_INJECTION_PREFIXES: str = "=+-@|%"

# Stable column definitions for the export
REGULATORY_COLUMNS: List[str] = [
    "finding_type",
    "rule_id",
    "rule_name",
    "rule_category",
    "status",
    "severity",
    "statutory_standard",
    "is_authoritatively_verified",
    "observed_value",
    "difference",
    "deficiency_reason",
    "source_documents",
    "correction_guidance",
]

CONSISTENCY_COLUMNS: List[str] = [
    "finding_type",
    "check_name",
    "field_compared",
    "is_consistent",
    "severity",
    "discrepancy_details",
    "documents_involved",
    "correction_guidance",
]

DUPLICATE_COLUMNS: List[str] = [
    "finding_type",
    "duplicate_type",
    "documents",
    "match_detail",
    "correction_guidance",
]

# Full merged column set (superset of all section columns)
ALL_COLUMNS: List[str] = [
    "application_id",
    "finding_type",
    "rule_id",
    "rule_name",
    "rule_category",
    "check_name",
    "field_compared",
    "status",
    "severity",
    "is_consistent",
    "is_authoritatively_verified",
    "statutory_standard",
    "observed_value",
    "difference",
    "deficiency_reason",
    "discrepancy_details",
    "duplicate_type",
    "documents_involved",
    "match_detail",
    "source_documents",
    "correction_guidance",
]


def _sanitize(value: object) -> str:
    """Convert *value* to a string and neutralize CSV formula-injection prefixes.

    Values whose string representation starts with a recognised formula prefix
    character are prepended with a single-quote (``'``).  This is the widely
    recommended defence-in-depth mitigation for CSV injection (OWASP A1).
    """
    text = str(value) if value is not None else ""
    if text and text[0] in _INJECTION_PREFIXES:
        text = "'" + text
    return text


def _regulatory_row(application_id: str, r: RegulatoryCheckResult) -> dict:
    """Map a single :class:`~verireg.schemas.RegulatoryCheckResult` to a CSV row dict."""
    return {
        "application_id": _sanitize(application_id),
        "finding_type": "REGULATORY_RULE",
        "rule_id": _sanitize(r.rule_id),
        "rule_name": _sanitize(r.rule_name),
        "rule_category": _sanitize(r.rule_category),
        "check_name": "",
        "field_compared": "",
        "status": _sanitize(r.status),
        "severity": _sanitize(r.severity.value if hasattr(r.severity, "value") else r.severity),
        "is_consistent": "",
        "is_authoritatively_verified": _sanitize(r.is_authoritatively_verified),
        "statutory_standard": _sanitize(r.statutory_standard),
        "observed_value": _sanitize(r.observed_value),
        "difference": _sanitize(r.difference or ""),
        "deficiency_reason": _sanitize(r.deficiency_reason or ""),
        "discrepancy_details": "",
        "duplicate_type": "",
        "documents_involved": "",
        "match_detail": "",
        "source_documents": _sanitize(
            "; ".join(
                e.source_document for e in (r.evidence or []) if e.source_document
            )
        ),
        "correction_guidance": _sanitize(r.deficiency_reason or ""),
    }


def _consistency_row(application_id: str, c: CrossDocConsistencyResult) -> dict:
    """Map a :class:`~verireg.schemas.CrossDocConsistencyResult` to a CSV row dict."""
    return {
        "application_id": _sanitize(application_id),
        "finding_type": "CONSISTENCY_CHECK",
        "rule_id": "",
        "rule_name": "",
        "rule_category": "",
        "check_name": _sanitize(c.check_name),
        "field_compared": _sanitize(c.field_compared),
        "status": "INCONSISTENT" if not c.is_consistent else "CONSISTENT",
        "severity": _sanitize(c.severity.value if hasattr(c.severity, "value") else c.severity),
        "is_consistent": _sanitize(c.is_consistent),
        "is_authoritatively_verified": "",
        "statutory_standard": "",
        "observed_value": "",
        "difference": "",
        "deficiency_reason": "",
        "discrepancy_details": _sanitize(c.discrepancy_details or ""),
        "duplicate_type": "",
        "documents_involved": _sanitize("; ".join(c.documents_involved or [])),
        "match_detail": "",
        "source_documents": _sanitize("; ".join(c.documents_involved or [])),
        "correction_guidance": _sanitize(
            c.discrepancy_details or "Reconcile the discrepancy across all listed documents."
        ),
    }


def _duplicate_rows(application_id: str, dup: DuplicateDetectionResult) -> List[dict]:
    """Map :class:`~verireg.schemas.DuplicateDetectionResult` findings to CSV row dicts."""
    rows: List[dict] = []

    def _base() -> dict:
        return {
            "application_id": _sanitize(application_id),
            "finding_type": "DUPLICATE_DETECTION",
            "rule_id": "",
            "rule_name": "",
            "rule_category": "",
            "check_name": "",
            "field_compared": "",
            "status": "FAIL",
            "severity": "CRITICAL",
            "is_consistent": "",
            "is_authoritatively_verified": "",
            "statutory_standard": "",
            "observed_value": "",
            "difference": "",
            "deficiency_reason": "",
            "discrepancy_details": "",
            "source_documents": "",
            "correction_guidance": "Remove or reconcile duplicate documents before resubmission.",
        }

    for entry in dup.exact_duplicates or []:
        row = _base()
        row["duplicate_type"] = "EXACT_SHA256"
        docs = entry.get("documents", [])
        row["documents_involved"] = _sanitize("; ".join(docs) if isinstance(docs, list) else str(docs))
        row["match_detail"] = _sanitize(entry.get("sha256_hash", ""))
        rows.append(row)

    for entry in dup.perceptual_image_duplicates or []:
        row = _base()
        row["duplicate_type"] = "PERCEPTUAL_IMAGE"
        docs = entry.get("documents", [])
        row["documents_involved"] = _sanitize("; ".join(docs) if isinstance(docs, list) else str(docs))
        row["match_detail"] = _sanitize(f"Hamming distance: {entry.get('hamming_distance', 'N/A')}")
        rows.append(row)

    return rows


def build_findings_csv(result: PipelineRunResult) -> str:
    """Serialise all findings in *result* to a UTF-8 CSV string.

    Sections included (in order):
    1. Regulatory rule evaluations (all statuses – PASS, FAIL, INDETERMINATE).
    2. Cross-document consistency checks.
    3. Duplicate detection findings (exact SHA-256 + perceptual image matches).

    Returns an **empty** CSV (header row only) when *result* contains no findings
    at all, rather than raising an error.

    Parameters
    ----------
    result:
        The :class:`~verireg.schemas.PipelineRunResult` produced by
        :meth:`~verireg.pipeline.DocumentIntelligencePipeline.process_application`.

    Returns
    -------
    str
        A UTF-8 CSV string ready for writing to a ``StreamingResponse`` or file.
    """
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=ALL_COLUMNS, extrasaction="ignore", lineterminator="\r\n")
    writer.writeheader()

    app_id = result.application_id or ""

    # Section 1: Regulatory rule evaluations
    for rule_result in result.rule_evaluations or []:
        writer.writerow(_regulatory_row(app_id, rule_result))

    # Section 2: Cross-document consistency checks
    for consistency_result in result.consistency_evaluations or []:
        writer.writerow(_consistency_row(app_id, consistency_result))

    # Section 3: Duplicate detection findings
    if result.duplicate_evaluations and result.duplicate_evaluations.has_duplicate_findings:
        for dup_row in _duplicate_rows(app_id, result.duplicate_evaluations):
            writer.writerow(dup_row)

    return buf.getvalue()
