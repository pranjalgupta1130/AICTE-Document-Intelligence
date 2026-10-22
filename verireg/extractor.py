"""PDF Text & Image extraction module with bounding boxes and perceptual image hashing.
Leverages PyMuPDF (fitz) and Pillow. Deterministic coordinate handling.
"""

from __future__ import annotations
import hashlib
import io
import os
from typing import Dict, List, Optional, Tuple
import fitz  # PyMuPDF
import numpy as np
from PIL import Image

from .schemas import (
    BoundingBox,
    DocumentMetadata,
    PageExtraction,
)


def compute_dhash(image: Image.Image, hash_size: int = 8) -> str:
    """Computes difference hash (dHash) for an image deterministically.
    
    Resizes image to (hash_size + 1, hash_size), converts to greyscale,
    and compares adjacent pixels.
    """
    resized = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = np.array(resized, dtype=np.float32)
    diff = pixels[:, 1:] > pixels[:, :-1]
    bitstring = "".join("1" if val else "0" for val in diff.flatten())
    # Format as hexadecimal string padded to 16 hex chars (for 64-bit dhash)
    hex_len = (hash_size * hash_size) // 4
    return f"{int(bitstring, 2):0{hex_len}x}"


def hamming_distance(hash1_hex: str, hash2_hex: str) -> int:
    """Computes bitwise Hamming distance between two hexadecimal perceptual hashes."""
    if len(hash1_hex) != len(hash2_hex):
        raise ValueError("Hash strings must have identical length")
    val1 = int(hash1_hex, 16)
    val2 = int(hash2_hex, 16)
    xor = val1 ^ val2
    return bin(xor).count("1")


class PDFExtractor:
    """Extracts text, metadata, bounding boxes, and embedded image hashes from PDF files."""

    def __init__(self, doc_path: str, tessdata_dir: Optional[str] = None):
        if not os.path.exists(doc_path):
            raise FileNotFoundError(f"Document file not found at: {doc_path}")
        self.doc_path = doc_path
        self.filename = os.path.basename(doc_path)
        self._doc: Optional[fitz.Document] = None
        self._ocr_pages: set = set()

        # Look for local or standard tessdata directory
        if tessdata_dir and os.path.isdir(tessdata_dir):
            self.tessdata_dir = tessdata_dir
        elif os.path.isdir(os.path.abspath("tessdata")):
            self.tessdata_dir = os.path.abspath("tessdata")
        elif os.environ.get("TESSDATA_PREFIX") and os.path.isdir(os.environ["TESSDATA_PREFIX"]):
            self.tessdata_dir = os.environ["TESSDATA_PREFIX"]
        else:
            self.tessdata_dir = None

    def __enter__(self):
        self._doc = fitz.open(self.doc_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._doc:
            self._doc.close()

    def get_metadata(self) -> DocumentMetadata:
        """Extracts file-level metadata and SHA-256 hash."""
        with open(self.doc_path, "rb") as f:
            content = f.read()
        sha256 = hashlib.sha256(content).hexdigest()
        file_size = len(content)

        doc = self._doc if self._doc else fitz.open(self.doc_path)
        try:
            total_pages = len(doc)
            meta = doc.metadata or {}
            creation_date = meta.get("creationDate")
            mod_date = meta.get("modDate")
        finally:
            if not self._doc:
                doc.close()

        return DocumentMetadata(
            filename=self.filename,
            sha256_hash=sha256,
            total_pages=total_pages,
            file_size_bytes=file_size,
            is_pdf=True,
            creation_date=creation_date,
            modification_date=mod_date,
        )

    def extract_pages(self) -> List[PageExtraction]:
        """Extracts text content and perceptual hashes of embedded images per page.
        
        Handles both native vector PDFs and scanned/rasterized documents.
        When a page contains raster images with zero text stream, automatically invokes
        PyMuPDF's integrated OCR engine to genuinely extract readable text.
        """
        doc = self._doc if self._doc else fitz.open(self.doc_path)
        pages_out: List[PageExtraction] = []

        try:
            for pno in range(len(doc)):
                page = doc[pno]
                text = page.get_text("text") or ""
                words = text.split()

                # Extract embedded images and compute dHash
                image_hashes: List[str] = []
                image_list = page.get_images(full=True)
                for img_info in image_list:
                    xref = img_info[0]
                    try:
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image.get("image")
                        if image_bytes:
                            pil_img = Image.open(io.BytesIO(image_bytes))
                            img_hash = compute_dhash(pil_img)
                            image_hashes.append(img_hash)
                    except Exception:
                        continue

                is_scanned = (len(words) == 0 and len(image_list) > 0)
                ocr_notice = None

                # If page is a raster scan with no embedded text, perform OCR
                if is_scanned:
                    try:
                        kwargs = {"dpi": 150}
                        if self.tessdata_dir:
                            kwargs["tessdata"] = self.tessdata_dir
                            kwargs["language"] = "eng"
                        tp = page.get_textpage_ocr(**kwargs)
                        ocr_text = page.get_text("text", textpage=tp)
                        if ocr_text and ocr_text.strip():
                            text = ocr_text
                            words = text.split()
                            self._ocr_pages.add(pno + 1)
                            ocr_notice = "OCR applied: successfully extracted text from scanned raster image."
                        else:
                            ocr_notice = "Raster scan page with no readable OCR text."
                    except Exception as e:
                        ocr_notice = f"Scanned image OCR engine unavailable: {str(e)}"

                pages_out.append(
                    PageExtraction(
                        page_number=pno + 1,
                        text=text,
                        word_count=len(words),
                        tables_found=0,
                        images_found=len(image_hashes),
                        is_scanned_image=is_scanned,
                        ocr_notice=ocr_notice,
                        image_perceptual_hashes=image_hashes,
                    )
                )
        finally:
            if not self._doc:
                doc.close()

        return pages_out

    def search_text_bounding_box(self, search_text: str, page_number: int) -> Optional[BoundingBox]:
        """Finds the bounding box of a verbatim text snippet on a specified 1-indexed page.
        
        Searches native vector text first; if page was scanned, invokes OCR textpage on the active page.
        """
        doc = self._doc if self._doc else fitz.open(self.doc_path)
        try:
            if page_number < 1 or page_number > len(doc):
                return None
            page = doc[page_number - 1]

            # 1. Native search
            rects = page.search_for(search_text)
            # 2. If not found and this page is known to be a scanned page, search via fresh OCR textpage
            if not rects and page_number in self._ocr_pages:
                try:
                    kwargs = {"dpi": 150}
                    if self.tessdata_dir:
                        kwargs["tessdata"] = self.tessdata_dir
                        kwargs["language"] = "eng"
                    tp = page.get_textpage_ocr(**kwargs)
                    rects = page.search_for(search_text, textpage=tp)
                except Exception:
                    pass

            if rects:
                r = rects[0]
                return BoundingBox(
                    x0=float(r.x0),
                    y0=float(r.y0),
                    x1=float(r.x1),
                    y1=float(r.y1),
                    page_number=page_number,
                )
            return None
        finally:
            if not self._doc:
                doc.close()
