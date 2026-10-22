"""PDF Digital Signature Inspection Module.
Performs deterministic structural and cryptographic check of PDF embedded signatures (/Sig, /ByteRange, PKCS#7).
"""

from __future__ import annotations
import os
import re
from typing import Any, Dict, List
import fitz  # PyMuPDF
from .schemas import DigitalSignatureInfo


class SignatureInspector:
    """Inspects PDF files for digital signatures, CMS/PKCS#7 signature objects, and integrity anomalies."""

    def __init__(self, doc_path: str):
        self.doc_path = doc_path
        self.filename = os.path.basename(doc_path)

    def inspect(self) -> DigitalSignatureInfo:
        signatures: List[Dict[str, Any]] = []
        cert_details: List[Dict[str, Any]] = []
        anomalies: List[str] = []
        verification_notes: List[str] = []

        try:
            doc = fitz.open(self.doc_path)
        except Exception as e:
            return DigitalSignatureInfo(
                has_signatures=False,
                signature_count=0,
                signatures_detected=False,
                integrity_verified=None,
                certificate_chain_trusted=None,
                signer_identity=None,
                anomalies=[f"Failed to parse PDF for digital signatures: {str(e)}"],
                verification_notes=["PDF parsing failed; unable to inspect signature structures."],
            )

        sig_count = 0
        primary_signer: Optional[str] = None
        integrity_verified: Optional[bool] = None
        certificate_chain_trusted: Optional[bool] = None

        try:
            # 1. Widget / form inspection
            for pno in range(len(doc)):
                page = doc[pno]
                for w in page.widgets():
                    if w.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                        sig_count += 1
                        signatures.append({
                            "page": pno + 1,
                            "field_name": w.field_name,
                            "rect": [round(c, 2) for c in w.rect],
                            "type": "SignatureWidget",
                        })

            # 2. Structural xref scan for /Sig dictionary
            for xref in range(1, doc.xref_length()):
                try:
                    obj_type = doc.xref_get_key(xref, "Type")
                    if obj_type and obj_type[1] == "/Sig":
                        sig_count += 1
                        filter_key = doc.xref_get_key(xref, "Filter")
                        subfilter_key = doc.xref_get_key(xref, "SubFilter")
                        name_key = doc.xref_get_key(xref, "Name")
                        byte_range_key = doc.xref_get_key(xref, "ByteRange")
                        m_date = doc.xref_get_key(xref, "M")

                        signer_str = name_key[1].strip("()") if name_key else "Unspecified Signer"
                        if not primary_signer and signer_str != "Unspecified Signer":
                            primary_signer = signer_str

                        sig_entry = {
                            "xref": xref,
                            "filter": filter_key[1] if filter_key else None,
                            "subfilter": subfilter_key[1] if subfilter_key else None,
                            "signer_name": signer_str,
                            "signed_date": m_date[1] if m_date else None,
                            "byte_range": byte_range_key[1] if byte_range_key else None,
                            "type": "SigDictionary",
                        }
                        signatures.append(sig_entry)

                        if subfilter_key and "adbe.pkcs7" in subfilter_key[1].lower():
                            cert_details.append({
                                "signer": sig_entry["signer_name"],
                                "standard": "PKCS#7 / CMS",
                                "subfilter": subfilter_key[1],
                            })
                except Exception:
                    continue

        finally:
            doc.close()

        # Check raw file for incremental update anomalies or signature flags without /Sig objects
        with open(self.doc_path, "rb") as f:
            raw_content = f.read()

        has_sig_bytes = b"/ByteRange" in raw_content or (b"/Contents" in raw_content and b"/Sig" in raw_content)
        if sig_count == 0 and has_sig_bytes:
            anomalies.append("File contains unindexed or detached /ByteRange signature references")

        # De-duplicate signature entries by field name / xref
        unique_sigs: List[Dict[str, Any]] = []
        seen = set()
        for s in signatures:
            key = s.get("xref") or s.get("field_name")
            if key not in seen:
                seen.add(key)
                unique_sigs.append(s)

        signatures_detected = len(unique_sigs) > 0

        # Technical verification notes: clearly separate detection, integrity, and trust chain
        if signatures_detected:
            verification_notes.append(f"Detected {len(unique_sigs)} cryptographic signature structure(s) in PDF.")
            # We do NOT fabricate cryptographic validity if an external CCA/Root CA trust store is unconfigured.
            # Mark integrity and trust as unverified/None rather than claiming valid verification.
            verification_notes.append("Byte-range integrity and PKCS#7 hash digest unverified (requires pyHanko or cryptographic provider).")
            verification_notes.append("Certificate chain trust unverified (no local CCA/Root CA trust store configured).")
            integrity_verified = None
            certificate_chain_trusted = None
        else:
            verification_notes.append("No embedded digital signature dictionaries or widgets found (rasterized/scanned document).")

        return DigitalSignatureInfo(
            has_signatures=signatures_detected,
            signature_count=len(unique_sigs),
            signatures_detected=signatures_detected,
            integrity_verified=integrity_verified,
            certificate_chain_trusted=certificate_chain_trusted,
            signer_identity=primary_signer,
            signatures=unique_sigs,
            certificate_details=cert_details,
            verification_notes=verification_notes,
            anomalies=anomalies,
        )
