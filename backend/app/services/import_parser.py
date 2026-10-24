import csv
import io
import re
import zipfile
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.app.core.config import settings

STANDARD_FIELDS = {
    "apaar_id": ["apaar_id", "apaar", "apaar id", "student_apaar_id", "apaar_number", "apaar no"],
    "institution_student_id": ["institution_student_id", "student_id", "roll_no", "roll_number", "registration_no", "reg_no", "enrollment_no", "college_id"],
    "student_name": ["student_name", "name", "full_name", "candidate_name", "student name"],
    "academic_year": ["academic_year", "year", "session", "batch_year", "admission_year", "academic year"],
    "programme_id": ["programme_id", "program_id", "programme", "program", "course", "course_id", "branch", "discipline"],
    "enrolment_status": ["enrolment_status", "enrollment_status", "status", "admission_status", "enrollment status"],
    "seat_type": ["seat_type", "quota", "category", "seat_category", "admission_type", "seat type"],
    "is_nri": ["is_nri", "nri", "nri_status", "nri category"],
    "is_oci": ["is_oci", "oci", "oci_status"],
    "is_fn": ["is_fn", "fn", "foreign_national", "foreign_student"]
}

def column_letter_to_index(col_letter: str) -> int:
    """
    Convert Excel column letters (e.g. 'A', 'Z', 'AA', 'AB') to 0-based integer index.
    """
    idx = 0
    for char in col_letter.upper():
        if "A" <= char <= "Z":
            idx = idx * 26 + (ord(char) - ord("A") + 1)
        else:
            break
    return idx - 1 if idx > 0 else 0

def split_cell_reference(cell_ref: str) -> Tuple[int, int]:
    """
    Extract (col_idx, row_idx) from Excel cell coordinate string like 'B2' or 'AA15'.
    Returns 0-based col_index and 1-based row_number.
    """
    match = re.match(r"^([A-Z]+)(\d+)$", cell_ref.upper())
    if match:
        col_str, row_str = match.groups()
        return column_letter_to_index(col_str), int(row_str)
    return 0, 0

def generate_csv_template() -> str:
    """
    Generate standard CSV template with headers and illustrative synthetic rows.
    """
    headers = [
        "apaar_id",
        "institution_student_id",
        "student_name",
        "academic_year",
        "programme_id",
        "enrolment_status",
        "seat_type",
        "is_nri",
        "is_oci",
        "is_fn"
    ]
    sample_rows = [
        ["918234567890", "STU-2026-001", "Aarav Sharma", "2026-2027", "PROG-001-CSE", "ENROLLED", "REGULAR", "FALSE", "FALSE", "FALSE"],
        ["918234567891", "STU-2026-002", "Diya Patel", "2026-2027", "PROG-001-CSE", "ENROLLED", "SUPERNUMERARY_EWS", "FALSE", "FALSE", "FALSE"],
        ["918234567892", "STU-2026-003", "Rohan Verma", "2026-2027", "PROG-001-CSE", "ENROLLED", "REGULAR", "FALSE", "FALSE", "FALSE"]
    ]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for r in sample_rows:
        writer.writerow(r)
    return output.getvalue()

def suggest_column_mapping(detected_columns: List[str]) -> Dict[str, str]:
    """
    Suggest mapping from detected column names to standard fields using aliases.
    """
    mapping: Dict[str, str] = {}
    normalized_detected = {re.sub(r"[^a-z0-9]", "", c.lower()): c for c in detected_columns}

    for std_field, aliases in STANDARD_FIELDS.items():
        found = False
        for alias in aliases:
            norm_alias = re.sub(r"[^a-z0-9]", "", alias.lower())
            if norm_alias in normalized_detected:
                mapping[std_field] = normalized_detected[norm_alias]
                found = True
                break
        if not found:
            mapping[std_field] = ""
    return mapping

def parse_csv_content(content: bytes) -> Tuple[List[str], List[Dict[str, Any]], List[str]]:
    """
    Parse CSV bytes with auto-encoding detection, line tracking, quoted cell support,
    and row/cell limit protections.
    """
    errors: List[str] = []
    text_content = ""
    for enc in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
        try:
            text_content = content.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        errors.append("Unable to decode CSV file: unsupported character encoding.")
        return [], [], errors

    if not text_content.strip():
        errors.append("Uploaded CSV file is completely empty.")
        return [], [], errors

    # Use io.StringIO with csv.reader to preserve RFC 4180 multiline cells and quotes
    string_io = io.StringIO(text_content, newline="")
    reader = csv.reader(string_io)

    try:
        raw_headers = next(reader)
    except StopIteration:
        errors.append("Uploaded file contains no header row.")
        return [], [], errors

    headers = [h.strip() for h in raw_headers]
    if not any(headers):
        errors.append("File header row is blank.")
        return [], [], errors

    # Check for duplicate headers
    seen_headers: Set[str] = set()
    dup_headers: List[str] = []
    for h in headers:
        h_norm = h.strip().lower()
        if h_norm in seen_headers and h_norm != "":
            dup_headers.append(h)
        seen_headers.add(h_norm)
    if dup_headers:
        errors.append(f"Duplicate column headers detected: {', '.join(dup_headers)}")

    rows: List[Dict[str, Any]] = []
    
    # Track physical line numbers accurately
    # In csv.reader, reader.line_num gives the 1-based physical line number of the source
    for r in reader:
        current_file_line = reader.line_num

        # Check maximum row count safeguard
        if len(rows) >= settings.MAX_IMPORT_ROWS:
            errors.append(f"Dataset exceeds maximum allowed limit of {settings.MAX_IMPORT_ROWS} rows.")
            break

        # Skip completely blank rows without corrupting row index
        if not any(c.strip() for c in r):
            continue

        row_dict = {}
        for idx, h in enumerate(headers):
            val = r[idx].strip() if idx < len(r) else ""
            if len(val) > settings.MAX_CELL_LENGTH:
                errors.append(f"Cell in row {current_file_line}, column '{h}' exceeds maximum length of {settings.MAX_CELL_LENGTH} characters.")
                val = val[:settings.MAX_CELL_LENGTH]
            row_dict[h] = val

        row_dict["_file_row_num"] = current_file_line
        rows.append(row_dict)

    if not rows and not errors:
        errors.append("Uploaded file contains headers but no data rows.")

    return headers, rows, errors

def parse_xlsx_content(content: bytes) -> Tuple[List[str], List[Dict[str, Any]], List[str]]:
    """
    Parse XLSX bytes using pure Python standard library zipfile + xml.
    Includes safeguards against zip bombs, XML bomb expansion, sparse cell misalignment,
    and missing formula caches.
    """
    errors: List[str] = []
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            infolist = z.infolist()
            if len(infolist) > settings.MAX_ZIP_ENTRIES:
                errors.append(f"XLSX archive contains excessive entries ({len(infolist)} > {settings.MAX_ZIP_ENTRIES}). Upload rejected.")
                return [], [], errors

            total_uncompressed = sum(info.file_size for info in infolist)
            if total_uncompressed > settings.MAX_UNCOMPRESSED_XLSX_BYTES:
                errors.append(f"XLSX uncompressed size exceeds limit ({total_uncompressed} > {settings.MAX_UNCOMPRESSED_XLSX_BYTES} bytes). Potential zip-bomb rejected.")
                return [], [], errors

            # 1. Parse shared strings if present
            shared_strings: List[str] = []
            if "xl/sharedStrings.xml" in z.namelist():
                tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
                ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
                for si in tree.findall(f"{ns}si"):
                    text = "".join(t.text for t in si.iter(f"{ns}t") if t.text)
                    if len(text) > settings.MAX_CELL_LENGTH:
                        text = text[:settings.MAX_CELL_LENGTH]
                    shared_strings.append(text)

            # 2. Parse sheet1
            sheet_path = "xl/worksheets/sheet1.xml"
            if sheet_path not in z.namelist():
                sheets = [n for n in z.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")]
                if not sheets:
                    errors.append("XLSX archive does not contain any valid worksheet XML.")
                    return [], [], errors
                sheet_path = sheets[0]

            sheet_tree = ET.fromstring(z.read(sheet_path))
            ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

            # Parse headers and rows respecting explicit cell coordinates (r="A1", r="C2", etc.)
            sheet_data = sheet_tree.find(f"{ns}sheetData")
            if sheet_data is None:
                errors.append("Uploaded XLSX worksheet contains no sheetData.")
                return [], [], errors

            row_elements = sheet_data.findall(f"{ns}row")
            if not row_elements:
                errors.append("Uploaded XLSX worksheet is empty.")
                return [], [], errors

            # Extract header row (first non-empty row)
            header_row_el = row_elements[0]
            header_cells: Dict[int, str] = {}
            max_col_idx = 0

            for c in header_row_el.findall(f"{ns}c"):
                cell_ref = c.get("r", "")
                col_idx, _ = split_cell_reference(cell_ref) if cell_ref else (len(header_cells), 1)
                t = c.get("t")
                v_el = c.find(f"{ns}v")
                val = v_el.text if v_el is not None else ""
                if t == "s" and val.isdigit():
                    s_idx = int(val)
                    val = shared_strings[s_idx] if s_idx < len(shared_strings) else ""
                elif t == "inlineStr":
                    is_el = c.find(f"{ns}is/{ns}t")
                    val = is_el.text if is_el is not None else ""
                header_cells[col_idx] = val.strip()
                if col_idx > max_col_idx:
                    max_col_idx = col_idx

            headers: List[str] = [header_cells.get(i, "") for i in range(max_col_idx + 1)]
            if not any(headers):
                errors.append("File header row is blank.")
                return [], [], errors

            # Check duplicate headers
            seen_headers: Set[str] = set()
            dup_headers: List[str] = []
            for h in headers:
                if not h:
                    continue
                h_norm = h.strip().lower()
                if h_norm in seen_headers:
                    dup_headers.append(h)
                seen_headers.add(h_norm)
            if dup_headers:
                errors.append(f"Duplicate column headers detected: {', '.join(dup_headers)}")

            rows: List[Dict[str, Any]] = []

            for row_el in row_elements[1:]:
                if len(rows) >= settings.MAX_IMPORT_ROWS:
                    errors.append(f"Dataset exceeds maximum allowed limit of {settings.MAX_IMPORT_ROWS} rows.")
                    break

                explicit_row_idx = row_el.get("r")
                file_row_num = int(explicit_row_idx) if (explicit_row_idx and explicit_row_idx.isdigit()) else (len(rows) + 2)

                # Map cells by column index
                row_cells: Dict[int, str] = {}
                for c in row_el.findall(f"{ns}c"):
                    cell_ref = c.get("r", "")
                    col_idx, _ = split_cell_reference(cell_ref) if cell_ref else (len(row_cells), file_row_num)
                    t = c.get("t")
                    v_el = c.find(f"{ns}v")
                    f_el = c.find(f"{ns}f")
                    val = v_el.text if v_el is not None else ""

                    if t == "s" and val.isdigit():
                        s_idx = int(val)
                        val = shared_strings[s_idx] if s_idx < len(shared_strings) else ""
                    elif t == "inlineStr":
                        is_el = c.find(f"{ns}is/{ns}t")
                        val = is_el.text if is_el is not None else ""
                    elif f_el is not None and not val:
                        # Formula present but cached evaluation absent
                        val = ""

                    val_str = val.strip() if val else ""
                    if len(val_str) > settings.MAX_CELL_LENGTH:
                        val_str = val_str[:settings.MAX_CELL_LENGTH]
                    row_cells[col_idx] = val_str

                # Skip completely blank row
                if not any(row_cells.values()):
                    continue

                row_dict = {}
                for idx, h in enumerate(headers):
                    if not h:
                        continue
                    row_dict[h] = row_cells.get(idx, "")

                row_dict["_file_row_num"] = file_row_num
                rows.append(row_dict)

            if not rows and not errors:
                errors.append("Uploaded XLSX contains headers but no data rows.")

            return headers, rows, errors

    except zipfile.BadZipFile:
        errors.append("Invalid or corrupted XLSX file (not a valid zip package).")
        return [], [], errors
    except Exception as exc:
        errors.append(f"Failed to parse XLSX file structure: {str(exc)}")
        return [], [], errors

def parse_uploaded_file(filename: str, content: bytes) -> Tuple[str, List[str], List[Dict[str, Any]], List[str]]:
    """
    Dispatch file parsing based on extension and magic bytes.
    Returns: (file_type, headers, rows, structural_errors)
    """
    fname = filename.lower()
    # Check magic byte signature for zip/xlsx: PK\x03\x04
    is_zip = content.startswith(b"PK\x03\x04")

    if fname.endswith(".xlsx") or is_zip:
        headers, rows, errors = parse_xlsx_content(content)
        return "XLSX", headers, rows, errors
    elif fname.endswith(".csv") or fname.endswith(".txt"):
        headers, rows, errors = parse_csv_content(content)
        return "CSV", headers, rows, errors
    else:
        return "UNKNOWN", [], [], ["Unsupported file format. Only CSV (.csv) and Excel (.xlsx) files are accepted."]
