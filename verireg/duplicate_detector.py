"""Exact file hash and perceptual image duplicate detector.
Identifies duplicate campus infrastructure, reused certificates, and re-uploaded files.
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Any
from .extractor import hamming_distance
from .schemas import (
    DocumentAnalysisResult,
    DuplicateDetectionResult,
)


class DuplicateDetector:
    """Detects both exact document matches (via SHA-256) and embedded image duplicates (via dHash)."""

    def __init__(self, hamming_threshold: int = 5):
        """Args:
            hamming_threshold: Maximum bit difference in 64-bit dhash to consider images duplicates.
                               5 bits difference out of 64 indicates identical/nearly-identical visual content.
        """
        self.hamming_threshold = hamming_threshold

    def evaluate_documents(
        self, documents: List[DocumentAnalysisResult]
    ) -> DuplicateDetectionResult:
        exact_duplicates: List[Dict[str, Any]] = []
        perceptual_duplicates: List[Dict[str, Any]] = []

        # 1. Exact document duplicate check
        hash_to_docs: Dict[str, List[str]] = {}
        for doc in documents:
            sha = doc.metadata.sha256_hash
            hash_to_docs.setdefault(sha, []).append(doc.metadata.filename)

        for sha, filenames in hash_to_docs.items():
            if len(filenames) > 1:
                exact_duplicates.append({
                    "sha256": sha,
                    "documents": filenames,
                    "details": f"Identical file content detected across {len(filenames)} files",
                })

        # 2. Embedded perceptual image duplicates check across pages and documents
        all_images: List[Dict[str, Any]] = []
        for doc in documents:
            for page in doc.pages:
                for idx, imghash in enumerate(page.image_perceptual_hashes):
                    all_images.append({
                        "document": doc.metadata.filename,
                        "page_number": page.page_number,
                        "image_index": idx + 1,
                        "hash": imghash,
                    })

        # Compare pairs
        for i in range(len(all_images)):
            for j in range(i + 1, len(all_images)):
                img1 = all_images[i]
                img2 = all_images[j]

                # If from same document and same page, skip self-comparison
                if img1["document"] == img2["document"] and img1["page_number"] == img2["page_number"]:
                    continue

                dist = hamming_distance(img1["hash"], img2["hash"])
                if dist <= self.hamming_threshold:
                    perceptual_duplicates.append({
                        "distance": dist,
                        "image_a": {
                            "document": img1["document"],
                            "page": img1["page_number"],
                            "index": img1["image_index"],
                            "hash": img1["hash"],
                        },
                        "image_b": {
                            "document": img2["document"],
                            "page": img2["page_number"],
                            "index": img2["image_index"],
                            "hash": img2["hash"],
                        },
                        "finding": "Identical or reused raster image asset detected across distinct pages/documents",
                    })

        has_findings = len(exact_duplicates) > 0 or len(perceptual_duplicates) > 0

        return DuplicateDetectionResult(
            exact_duplicates=exact_duplicates,
            perceptual_image_duplicates=perceptual_duplicates,
            has_duplicate_findings=has_findings,
        )
