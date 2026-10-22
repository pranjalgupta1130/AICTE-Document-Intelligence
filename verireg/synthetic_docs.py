"""Generates synthetic PDF documents for rigorous automated testing of Member 1.
Covers:
- Compliant documents (valid areas, FDR, valid fire certificate)
- Deficient documents (sub-standard land, missing fire NOC, bad ratio)
- Duplicate documents (exact same file)
- Perceptual duplicate images (reused campus images)
- Inconsistent documents (mismatched trust / institution names across files)
"""

from __future__ import annotations
import io
import os
import fitz  # PyMuPDF
from PIL import Image, ImageDraw


def create_sample_pattern_image(color=(30, 100, 200), shape="circle") -> bytes:
    """Creates a sample raster image in PNG format."""
    im = Image.new("RGB", (120, 120), color=(255, 255, 255))
    draw = ImageDraw.Draw(im)
    if shape == "circle":
        draw.ellipse([20, 20, 100, 100], fill=color, outline=(0, 0, 0), width=2)
    elif shape == "rect":
        draw.rectangle([20, 20, 100, 100], fill=color, outline=(0, 0, 0), width=2)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def create_compliant_application_pdf(output_path: str, app_id: str = "APP-2026-001") -> str:
    """Creates a synthetic PDF representing a fully compliant institutional filing."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4 size

    lines = [
        "ALL INDIA COUNCIL FOR TECHNICAL EDUCATION",
        "INSTITUTIONAL EXTENSION OF APPROVAL APPLICATION",
        "--------------------------------------------------",
        f"Application ID: {app_id}",
        "Permanent Institute ID: 1-10492839",
        "Institution Name: Apex Institute of Technology and Science",
        "Trust / Society Name: Apex Educational and Charitable Trust",
        "Total Land Area: 5.50 Acres",
        "Total Built-up Area: 6500 Sqm",
        "Fixed Deposit: INR 2,000,000.00",
        "Fire Safety NOC: VALID",
        "Student-Faculty Ratio: 15.0:1",
        "--------------------------------------------------",
        "Certified that the spatial and financial standards conform to AICTE norms.",
    ]

    y = 50
    for line in lines:
        page.insert_text((50, y), line, fontsize=11)
        y += 24

    # Embed an image
    img_bytes = create_sample_pattern_image(color=(20, 120, 60), shape="rect")
    rect = fitz.Rect(50, 400, 180, 520)
    page.insert_image(rect, stream=img_bytes)

    doc.save(output_path)
    doc.close()
    return output_path


def create_deficient_application_pdf(output_path: str, app_id: str = "APP-2026-002") -> str:
    """Creates a synthetic PDF exhibiting clear statutory deficiencies (small land, expired fire NOC)."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    lines = [
        "ALL INDIA COUNCIL FOR TECHNICAL EDUCATION",
        "ANNUAL DEFICIENT APPLICATION FILING",
        "--------------------------------------------------",
        f"Application ID: {app_id}",
        "Permanent Institute ID: 1-99887766",
        "Institution Name: Horizon Technical Academy",
        "Trust / Society Name: Horizon Education Society",
        "Total Land Area: 1.20 Acres",          # Sub-standard (norm is >= 2.5)
        "Total Built-up Area: 2200 Sqm",       # Sub-standard (norm is >= 4000)
        "Fixed Deposit: INR 500,000.00",       # Sub-standard (norm is >= 15 Lakhs)
        "Fire Safety NOC: EXPIRED",            # Expired NOC
        "Student-Faculty Ratio: 28.5:1",       # Exceeds 20:1
        "--------------------------------------------------",
    ]

    y = 50
    for line in lines:
        page.insert_text((50, y), line, fontsize=11)
        y += 24

    doc.save(output_path)
    doc.close()
    return output_path


def create_inconsistent_secondary_pdf(output_path: str, app_id: str = "APP-2026-999") -> str:
    """Creates a second document with conflicting application ID & institution name."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    lines = [
        "ARCHITECTURAL CERTIFICATE & CARPET AREA AFFIDAVIT",
        "--------------------------------------------------",
        f"Application ID: {app_id}",  # Conflicting ID
        "Institution Name: Imperial Global Polytechnic",  # Conflicting name
        "Trust / Society Name: Apex Educational and Charitable Trust",
        "Total Built-up Area: 7500 Sqm",
        "--------------------------------------------------",
    ]

    y = 50
    for line in lines:
        page.insert_text((50, y), line, fontsize=11)
        y += 25

    # Embed same image as compliant doc to test perceptual duplication detection
    img_bytes = create_sample_pattern_image(color=(20, 120, 60), shape="rect")
    rect = fitz.Rect(50, 250, 180, 370)
    page.insert_image(rect, stream=img_bytes)

    doc.save(output_path)
    doc.close()
    return output_path


def create_scanned_image_pdf(output_path: str) -> str:
    """Creates a synthetic rasterized/scanned PDF where text exists inside a raster image without text stream."""
    im = Image.new("RGB", (800, 1100), color=(255, 255, 255))
    draw = ImageDraw.Draw(im)
    draw.text((40, 50), "SCANNED LAND TITLE DEED (SUB-REGISTRAR COPY)", fill=(0, 0, 0))
    draw.text((40, 90), "Total Land Area: 4.20 Acres", fill=(0, 0, 0))
    buf = io.BytesIO()
    im.save(buf, format="PNG")

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_image(fitz.Rect(20, 20, 575, 822), stream=buf.getvalue())
    doc.save(output_path)
    doc.close()
    return output_path


def create_digitally_signed_pdf(output_path: str, app_id: str = "APP-2026-SIGNED") -> str:
    """Creates a synthetic PDF containing an embedded /Sig signature form widget."""
    base_path = output_path + ".tmp.pdf"
    create_compliant_application_pdf(base_path, app_id=app_id)
    doc = fitz.open(base_path)
    page = doc[0]
    w = fitz.Widget()
    w.field_type = fitz.PDF_WIDGET_TYPE_SIGNATURE
    w.field_name = "AuthorizedSignatoryDSC"
    w.rect = fitz.Rect(50, 720, 250, 800)
    page.add_widget(w)
    doc.save(output_path)
    doc.close()
    if os.path.exists(base_path):
        os.remove(base_path)
    return output_path
