"""Structured field extraction with deterministic page-level evidence and bounding boxes.
Extracts institutional details, land area, carpet area, FDR deposits, fire certificates, etc.
"""

from __future__ import annotations
import re
from typing import Dict, List, Optional, Tuple, Any
from .extractor import PDFExtractor
from .schemas import (
    BoundingBox,
    EvidenceAnnotation,
    ExtractedField,
    PageExtraction,
)


class FieldExtractor:
    """Extracts regulatory fields deterministically with regex patterns and grounds them with page-level evidence."""

    # Pre-compiled regulatory field patterns
    PATTERNS: Dict[str, List[Dict[str, Any]]] = {
        "institution_name": [
            {
                "regex": re.compile(r"(?:name\s+of\s+(?:the\s+)?institution|college\s+name|institute\s+name|institution(?:\s*name)?)\s*[:\-]\s*([^\n\r,]+)", re.IGNORECASE),
                "type": "string",
            },
            {
                "regex": re.compile(r"institution\s*[:\-]\s*([A-Za-z0-9\s.,&'-]+(?:Engineering|Technology|Institute|College|Polytechnic)[^\n\r,]*)", re.IGNORECASE),
                "type": "string",
            },
        ],
        "application_id": [
            {
                "regex": re.compile(r"(?:application\s*(?:id|no|number)|app\s*id)\s*[:\-]\s*([A-Z0-9\-_/]+)", re.IGNORECASE),
                "type": "string",
            },
        ],
        "aicte_permanent_id": [
            {
                "regex": re.compile(r"(?:permanent\s*(?:institute\s*)?id|pid|aicte\s*id)\s*[:\-]\s*([0-9\-]+)", re.IGNORECASE),
                "type": "string",
            },
        ],
        "land_area_acres": [
            {
                "regex": re.compile(r"(?:total\s*land\s*area|land\s*area|area\s*of\s*land)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:acres|acre)", re.IGNORECASE),
                "type": "float",
            },
            {
                "regex": re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*acres?\s*(?:of\s*contiguous\s*land|land)", re.IGNORECASE),
                "type": "float",
            },
        ],
        "built_up_area_sqm": [
            {
                "regex": re.compile(r"(?:total\s*built[\s\-]*up\s*area|instructional\s*area|carpet\s*area)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:sqm|sq\s*\.?\s*m|sq\s*meters|square\s*meters)", re.IGNORECASE),
                "type": "float",
            },
        ],
        "fdr_amount_inr": [
            {
                "regex": re.compile(r"(?:fdr|fixed\s*deposit|security\s*deposit|lien\s*amount)\s*[:\-]?\s*(?:inr|rs\.?|inr\s*rs\.?)?\s*([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)", re.IGNORECASE),
                "type": "currency",
            },
        ],
        "fire_safety_noc_status": [
            {
                "regex": re.compile(r"fire\s*(?:and\s*life\s*)?safety\s*(?:noc|certificate|clearance)\s*[:\-]?\s*(valid|issued|compliant|approved|expired|pending|deficiency)", re.IGNORECASE),
                "type": "status",
            },
            {
                "regex": re.compile(r"(?:fire\s*noc\s*is\s*)(valid|issued|expired|pending)", re.IGNORECASE),
                "type": "status",
            },
        ],
        "fire_safety_valid_till": [
            {
                "regex": re.compile(r"(?:fire\s*safety|fire\s*noc)\s*(?:valid\s*(?:till|up\s*to)|expiry\s*date)\s*[:\-]?\s*([0-9]{2}[\/\-][0-9]{2}[\/\-][0-9]{4}|[0-9]{4}[\/\-][0-9]{2}[\/\-][0-9]{2})", re.IGNORECASE),
                "type": "date",
            },
        ],
        "trust_society_name": [
            {
                "regex": re.compile(r"(?:name\s*of\s*(?:the\s*)?(?:trust|society|company)|(?:trust|society)(?:\s*[\/\-]\s*(?:society|trust))?\s*(?:name)?)\s*[:\-]\s*([^\n\r,]+)", re.IGNORECASE),
                "type": "string",
            },
            {
                "regex": re.compile(r"(?:trust|society)\s*[:\-]\s*([A-Za-z0-9\s.,&'-]+(?:Trust|Society|Foundation|Samiti|Mandal)[^\n\r,]*)", re.IGNORECASE),
                "type": "string",
            },
        ],
        "student_faculty_ratio": [
            {
                "regex": re.compile(r"(?:student[\s\-]*faculty\s*ratio|sfr)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*[:\-]\s*1", re.IGNORECASE),
                "type": "ratio",
            },
        ],
    }

    def __init__(self, extractor: PDFExtractor):
        self.extractor = extractor

    def extract_fields(self, pages: List[PageExtraction]) -> Dict[str, ExtractedField]:
        """Extracts known fields across all pages of the document."""
        results: Dict[str, ExtractedField] = {}

        for field_name, patterns in self.PATTERNS.items():
            for pno_idx, page in enumerate(pages):
                page_num = page.page_number
                text = page.text
                if not text:
                    continue

                for pattern_info in patterns:
                    regex: re.Pattern = pattern_info["regex"]
                    val_type: str = pattern_info["type"]
                    match = regex.search(text)
                    if match:
                        raw_matched_str = match.group(0).strip()
                        extracted_val_str = match.group(1).strip()
                        normalized = self._normalize_value(extracted_val_str, val_type)

                        # Bounding box lookup:
                        # Prioritize bounding box of the exact extracted value first,
                        # then fall back to full label snippet for complete evidence grounding.
                        bbox = self.extractor.search_text_bounding_box(extracted_val_str, page_num)
                        if not bbox:
                            bbox = self.extractor.search_text_bounding_box(raw_matched_str, page_num)

                        evidence = EvidenceAnnotation(
                            page_number=page_num,
                            bbox=bbox,
                            snippet=raw_matched_str,
                            source_document=self.extractor.filename,
                        )

                        # Confidence: deterministic score
                        confidence = 1.0 if bbox is not None else 0.85

                        results[field_name] = ExtractedField(
                            field_name=field_name,
                            value=extracted_val_str,
                            raw_text=raw_matched_str,
                            normalized_value=normalized,
                            confidence=confidence,
                            evidence=evidence,
                        )
                        break  # Found field, move to next field

                if field_name in results:
                    break

        return results

    def _normalize_value(self, val_str: str, val_type: str) -> Any:
        if val_type == "float":
            try:
                return float(val_str.replace(",", ""))
            except ValueError:
                return None
        elif val_type == "currency":
            try:
                cleaned = re.sub(r"[^\d.]", "", val_str)
                return float(cleaned)
            except ValueError:
                return None
        elif val_type == "status":
            return val_str.upper()
        elif val_type == "ratio":
            try:
                return float(val_str)
            except ValueError:
                return None
        return val_str.strip()
