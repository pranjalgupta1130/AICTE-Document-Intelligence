import os
import json
import csv
import hashlib

def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

out_dir = os.path.abspath('test-data/hardcoded-demo-data')
os.makedirs(out_dir, exist_ok=True)

# 1. DEPARTMENT_DATA
dept_data = [
    {
        'id': 'dept-cse',
        'code': 'BTECH-CSE-01',
        'name': 'Computer Science & Engineering',
        'sanctioned': 180,
        'supernumerary': 18,
        'actualRegular': 180,
        'actualSuper': 16,
        'totalEnrolled': 196,
        'utilization': '98.9%',
        'hasViolation': False,
        'excessCount': None,
        'statusText': 'Within Quota',
    },
    {
        'id': 'dept-ece',
        'code': 'BTECH-ECE-02',
        'name': 'Electronics & Communication Engineering',
        'sanctioned': 120,
        'supernumerary': 12,
        'actualRegular': 122,
        'actualSuper': 11,
        'totalEnrolled': 133,
        'utilization': '100.7%',
        'hasViolation': True,
        'excessCount': 2,
        'statusText': 'Exceeded (+2)',
    },
    {
        'id': 'dept-mec',
        'code': 'BTECH-MEC-03',
        'name': 'Mechanical Engineering',
        'sanctioned': 120,
        'supernumerary': 12,
        'actualRegular': 112,
        'actualSuper': 8,
        'totalEnrolled': 120,
        'utilization': '90.9%',
        'hasViolation': False,
        'excessCount': None,
        'statusText': 'Within Quota',
    },
    {
        'id': 'dept-eee',
        'code': 'BTECH-EEE-04',
        'name': 'Electrical & Electronics Engineering',
        'sanctioned': 90,
        'supernumerary': 9,
        'actualRegular': 90,
        'actualSuper': 9,
        'totalEnrolled': 99,
        'utilization': '100.0%',
        'hasViolation': False,
        'excessCount': None,
        'statusText': 'At Capacity',
    },
]

dept_fields = ['id', 'code', 'name', 'sanctioned', 'supernumerary', 'actualRegular', 'actualSuper', 'totalEnrolled', 'utilization', 'hasViolation', 'excessCount', 'statusText']
with open(os.path.join(out_dir, 'department_data.csv'), 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=dept_fields)
    writer.writeheader()
    for row in dept_data:
        r = row.copy()
        if r['excessCount'] is None:
            r['excessCount'] = ''
        writer.writerow(r)

# 2. INITIAL_DIAGNOSTICS
diag_data = [
    {
        'row': 14,
        'studentId': 'NITT-2025-014',
        'apaarId': '9082-1144-8821',
        'category': 'REGULAR',
        'status': 'VALID',
        'note': 'Format OK • Syntactic checksum verified against Mock APAAR Adapter (Simulated • is_official=False)',
    },
    {
        'row': 28,
        'studentId': 'NITT-2025-028',
        'apaarId': '9082-4412-8821',
        'category': 'REGULAR',
        'status': 'VALID',
        'note': 'Simulated verification via Mock APAAR Adapter (Siddharth R. Iyer • is_official=False)',
    },
    {
        'row': 42,
        'studentId': 'NITT-2025-042',
        'apaarId': '[NULL / EMPTY]',
        'category': 'EWS',
        'status': 'BLOCKING',
        'note': 'Field Required by Rule R6 - Mandatory APAAR Identifier Non-Null',
    },
    {
        'row': 61,
        'studentId': 'NITT-2025-061',
        'apaarId': '[MALFORMED_REGEX]',
        'category': 'TFW',
        'status': 'BLOCKING',
        'note': 'Syntactic constraint violation: Expected 12-digit format (xxxx-xxxx-xxxx)',
    },
    {
        'row': 77,
        'studentId': 'NITT-2025-077',
        'apaarId': '8129-3321-9011',
        'category': 'REGULAR',
        'status': 'DUPLICATE',
        'note': 'Collision with Row 108: APAAR Re-assignment Disallowed across records',
    },
    {
        'row': 108,
        'studentId': 'NITT-2025-108',
        'apaarId': '8129-3321-9011',
        'category': 'REGULAR',
        'status': 'DUPLICATE',
        'note': 'Collision with Row 77: In-batch duplicate assignment rejected under Rule R11',
    },
    {
        'row': 115,
        'studentId': 'NITT-2025-115',
        'apaarId': '3488-2910-4491',
        'category': 'NRI',
        'status': 'WARNING',
        'note': 'Rule R4: INCONSISTENT_CATEGORY (NRI requires Passport / OCI Ref)',
    },
    {
        'row': 142,
        'studentId': 'NITT-2025-142',
        'apaarId': '5510-9921-3841',
        'category': 'SUPERNUMERARY',
        'status': 'WARNING',
        'note': 'Rule R8: PMSSS quota verification pending state nodality endorsement',
    },
]

diag_fields = ['row', 'studentId', 'apaarId', 'category', 'status', 'note']
with open(os.path.join(out_dir, 'initial_diagnostics.csv'), 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=diag_fields)
    writer.writeheader()
    writer.writerows(diag_data)

# 3. INITIAL_FINDINGS
findings_data = {
    42: {
        'row': 42,
        'studentId': 'NITT-2025-CS-042',
        'name': 'Aarav K. Sundaram',
        'branch': 'B.Tech Computer Science',
        'rule': 'RULE-R6-MISSING-APAAR',
        'severity': 'BLOCKING',
        'field': 'apaar_id',
        'explanation': 'APAAR ID cell is empty. Mandatory academic identifier under AICTE mandate. Without it, academic credits cannot be transferred to the Academic Bank of Credits (ABC).',
        'suggestedAction': 'Input valid 12-digit APAAR syntax (e.g. 7481-9920-3341) verified via ABC registry.',
        'inputLabel': 'Rectify APAAR Identifier',
        'inputHint': 'Format: XXXX-XXXX-XXXX (12 digits)',
        'placeholder': '7481-9920-3341',
        'defaultVal': '',
    },
    77: {
        'row': 77,
        'studentId': 'NITT-2025-ME-077',
        'name': 'Priyanka Venkatesh',
        'branch': 'B.Tech Mechanical Eng',
        'rule': 'RULE-R5-BATCH-DUPLICATE',
        'severity': 'BLOCKING',
        'field': 'apaar_id',
        'explanation': 'Exact APAAR ID 8129-3321-9011 matches row #108 in same batch. Dual student identity collision detected.',
        'suggestedAction': 'Inspect conflicting rows / Rectify duplicate student ID with correct National Identity register entry.',
        'inputLabel': 'Replace with Distinct APAAR ID',
        'inputHint': 'Must not collide with row #108',
        'placeholder': '8129-3321-9012',
        'defaultVal': '8129-3321-9011',
    },
    122: {
        'row': 122,
        'studentId': 'NITT-2025-ECE-122',
        'name': 'Devraj Mukherjee',
        'branch': 'B.Tech Electronics & Comm',
        'rule': 'RULE-R7-INTAKE-EXCEEDED',
        'severity': 'BLOCKING',
        'field': 'programme_enrolment',
        'explanation': 'ECE actual enrolment (122) exceeds approved regular intake (120) by 2 seats. AICTE ceiling breach.',
        'suggestedAction': 'Reclassify as approved supernumerary category (e.g., TFW, PMSSS, or EWS) or rectify admission roster.',
        'inputLabel': 'Adjust Seat Category Classification',
        'inputHint': 'Values: REGULAR | TFW_SUPERNUMERARY | PMSSS_QUOTA | EWS_SUPERNUMERARY',
        'placeholder': 'TFW_SUPERNUMERARY',
        'defaultVal': 'REGULAR',
    },
    115: {
        'row': 115,
        'studentId': 'NITT-2025-CIV-115',
        'name': 'Rohan Sharma',
        'branch': 'B.Tech Civil Engineering',
        'rule': 'RULE-R4-SEAT-INCONSISTENCY',
        'severity': 'WARNING',
        'field': 'nri_status',
        'explanation': 'Marked as NRI quota but nationality listed as Indian without sponsor declaration on file.',
        'suggestedAction': 'Attach upload affidavit token or reclassify quota code to DOMESTIC_OPEN.',
        'inputLabel': 'Sponsor Declaration Reference No.',
        'inputHint': 'AFFIDAVIT-XXXXXX or update quota',
        'placeholder': 'AFFIDAVIT-NITT-2025-881',
        'defaultVal': '',
    },
    204: {
        'row': 204,
        'studentId': 'NITT-2025-EE-204',
        'name': 'Kavita Chawla',
        'branch': 'B.Tech Electrical Eng',
        'rule': 'RULE-R8-SYNTAX-SUSPECT',
        'severity': 'WARNING',
        'field': 'apaar_id',
        'explanation': 'Mock Adapter check returned MOCK_UNAVAILABLE for gateway response during batch run.',
        'suggestedAction': 'Trigger immediate mock adapter retry probe to clear mock gateway queue.',
        'inputLabel': 'Re-trigger Adapter Gateway Protocol',
        'inputHint': 'Enter MOCK_VERIFIED to force mock handshake',
        'placeholder': 'MOCK_VERIFIED',
        'defaultVal': 'MOCK_UNAVAILABLE',
    },
}

findings_fields = ['row', 'studentId', 'name', 'branch', 'rule', 'severity', 'field', 'explanation', 'suggestedAction', 'inputLabel', 'inputHint', 'placeholder', 'defaultVal']
with open(os.path.join(out_dir, 'initial_findings.csv'), 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=findings_fields)
    writer.writeheader()
    for k in sorted(findings_data.keys()):
        writer.writerow(findings_data[k])

# 4. MOCK_PROFILES + MOCK_PROFILE_AUDIT_TRAIL (Relational lossless design)
profiles_data = {
    '9082-4412-8821': {
        'apaarId': '9082-4412-8821',
        'instStudentId': 'NITT-2025-CSE-0142',
        'fullName': 'SIDDHARTH R. IYER',
        'initials': 'SI',
        'institution': 'National Institute of Technology, Trichy',
        'institutionCode': 'AICTE-1-49281',
        'programme': 'B.Tech (Computer Science & Engineering)',
        'faculty': 'Faculty of Engineering & Technology',
        'batch': '2025–2029',
        'term': '2025-2026 • Sem 1',
        'enrolmentStatus': 'Active Regular',
        'seatQuota': 'AICTE Open Merit',
        'verificationStatus': 'MOCK_VERIFIED',
        'verificationRef': 'MOCK-APR-2025-882190-SIG',
        'verificationHash': '8f4c2e...b39a',
        'signatureHash': '3a9f7d...410b28',
        'signedDate': '12-OCT-2025 14:35 UTC',
        'systemId': 'SYS#49281-25',
        'auditTrail': [
            {
                'timestamp': '12 Oct 2025, 16:10:04 IST',
                'eventType': 'Verification Query',
                'icon': 'visibility',
                'iconColor': 'text-secondary',
                'actor': 'AICTE-VERIF-9912 (Reviewer)',
                'actionDetails': 'Purpose-limited identity lookup executed against APAAR 9082-4412-8821.',
                'complianceStatus': 'LOGGED & SIGNED',
                'complianceBadgeClass': 'bg-status-verified-surface text-status-verified border-status-verified-border',
            },
            {
                'timestamp': '12 Oct 2025, 14:35:19 IST',
                'eventType': 'Mock Adapter Attestation',
                'icon': 'check_circle',
                'iconColor': 'text-status-verified',
                'actor': 'ENGINE-ADAPTER-MOCK-V2',
                'actionDetails': 'Status logged as MOCK_VERIFIED. Signature: MOCK-APR-2025-882190.',
                'complianceStatus': 'VERIFIED',
                'complianceBadgeClass': 'bg-status-verified-surface text-status-verified border-status-verified-border',
            },
            {
                'timestamp': '12 Oct 2025, 14:34:02 IST',
                'eventType': 'Syntactic Schema Check',
                'icon': 'rule',
                'iconColor': 'text-outline',
                'actor': 'PARSER-SCHEMA-V4',
                'actionDetails': 'Syntactic and field constraint validation passed (Rules R1 to R8 zero defect).',
                'complianceStatus': 'PASSED (8/8)',
                'complianceBadgeClass': 'bg-status-verified-surface text-status-verified border-status-verified-border',
            },
            {
                'timestamp': '12 Oct 2025, 14:32:11 IST',
                'eventType': 'Batch Ingestion',
                'icon': 'upload_file',
                'iconColor': 'text-outline',
                'actor': 'R. Krishnamurthy (Op ID #2910)',
                'actionDetails': 'Record imported into batch #BATCH-2025-NITTRICHY-004.',
                'complianceStatus': 'COMMITTED',
                'complianceBadgeClass': 'bg-surface-subtle text-on-surface-variant border-border-subtle',
            },
        ],
    },
    '9421-8819-4412': {
        'apaarId': '9421-8819-4412',
        'instStudentId': 'NITT-2025-CSE-0098',
        'fullName': 'A. SHARMA',
        'initials': 'AS',
        'institution': 'National Institute of Technology, Trichy',
        'institutionCode': 'AICTE-1-49281',
        'programme': 'B.Tech (Computer Science)',
        'faculty': 'Faculty of Engineering & Technology',
        'batch': '2025–2029',
        'term': '2025-2026 • Sem 1',
        'enrolmentStatus': 'Under Triage Review',
        'seatQuota': 'JoSAA Merit (Open/GEN)',
        'verificationStatus': 'MOCK_VERIFIED',
        'verificationRef': 'MOCK-APR-2025-994101-XC',
        'verificationHash': '9941a2...c11f',
        'signatureHash': '4b1e9c...88102a',
        'signedDate': '15-JUL-2025 11:32 UTC',
        'systemId': 'SYS#49281-99',
        'auditTrail': [
            {
                'timestamp': '23 Jul 2025, 14:22:00 IST',
                'eventType': 'Triage Conflict Flagged',
                'icon': 'warning',
                'iconColor': 'text-status-review',
                'actor': 'AICTE-APEX-TRIAGE-ENGINE',
                'actionDetails': 'Concurrent admission detected across NIT Trichy and VIT Vellore.',
                'complianceStatus': 'TRIAGE QUEUE',
                'complianceBadgeClass': 'bg-status-review-surface text-status-review border-status-review-border',
            },
            {
                'timestamp': '15 Jul 2025, 11:32:04 IST',
                'eventType': 'JoSAA Seat Allocation',
                'icon': 'verified',
                'iconColor': 'text-status-verified',
                'actor': 'JOSAA-CENTRAL-PORTAL',
                'actionDetails': 'JoSAA round 3 merit allocation confirmed with fee remitted.',
                'complianceStatus': 'VERIFIED',
                'complianceBadgeClass': 'bg-status-verified-surface text-status-verified border-status-verified-border',
            },
        ],
    },
    '8812-7491-1029': {
        'apaarId': '8812-7491-1029',
        'instStudentId': 'COEP-2025-AI-0012',
        'fullName': 'POOJA R. DESHMUKH',
        'initials': 'PD',
        'institution': 'COEP Technological University, Pune',
        'institutionCode': 'AICTE-1-20914',
        'programme': 'M.Tech (Artificial Intelligence)',
        'faculty': 'School of Computer Engineering',
        'batch': '2025–2027',
        'term': '2025-2026 • Sem 1',
        'enrolmentStatus': 'Active Regular',
        'seatQuota': 'GATE Central Counseling (Open/OBC)',
        'verificationStatus': 'MOCK_VERIFIED',
        'verificationRef': 'MOCK-APR-2025-749102-SIG',
        'verificationHash': '2c88fd...7a4e',
        'signatureHash': '8b77a0...920141',
        'signedDate': '12-JUL-2025 09:14 UTC',
        'systemId': 'SYS#20914-12',
        'auditTrail': [
            {
                'timestamp': '19 Jul 2025, 16:45:10 IST',
                'eventType': 'Dual Application Warning',
                'icon': 'info',
                'iconColor': 'text-secondary',
                'actor': 'MAHA-CET-GRID',
                'actionDetails': 'State counseling duplicate check matched with SPIT Mumbai.',
                'complianceStatus': 'MONITORED',
                'complianceBadgeClass': 'bg-status-review-surface text-status-review border-status-review-border',
            },
            {
                'timestamp': '12 Jul 2025, 09:14:22 IST',
                'eventType': 'GATE Enrolment Confirmed',
                'icon': 'check_circle',
                'iconColor': 'text-status-verified',
                'actor': 'Dr. V. N. Pande (Dean)',
                'actionDetails': 'Candidate biometrics and GATE scorecard validated.',
                'complianceStatus': 'COMMITTED',
                'complianceBadgeClass': 'bg-status-verified-surface text-status-verified border-status-verified-border',
            },
        ],
    },
}

profile_fields = ['apaarId', 'instStudentId', 'fullName', 'initials', 'institution', 'institutionCode', 'programme', 'faculty', 'batch', 'term', 'enrolmentStatus', 'seatQuota', 'verificationStatus', 'verificationRef', 'verificationHash', 'signatureHash', 'signedDate', 'systemId', 'auditTrailJson']

profile_audit_fields = ['apaarId', 'auditOrder', 'timestamp', 'eventType', 'icon', 'iconColor', 'actor', 'actionDetails', 'complianceStatus', 'complianceBadgeClass']

with open(os.path.join(out_dir, 'mock_profiles.csv'), 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=profile_fields)
    writer.writeheader()
    for k, p in profiles_data.items():
        row = p.copy()
        row['auditTrailJson'] = json.dumps(row['auditTrail'])
        del row['auditTrail']
        writer.writerow(row)

with open(os.path.join(out_dir, 'mock_profile_audit_trail.csv'), 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=profile_audit_fields)
    writer.writeheader()
    for k, p in profiles_data.items():
        for order, a in enumerate(p['auditTrail']):
            arow = a.copy()
            arow['apaarId'] = k
            arow['auditOrder'] = order + 1
            writer.writerow(arow)

# 5. TRIAGE_CASES
triage_data = [
    {
        'id': 'case-1',
        'ref': 'XC-DUP-2025-9941',
        'apaarId': '9421-8819-4412',
        'detectedAt': '23 Jul 2025, 14:22 IST',
        'flagType': 'CONCURRENT ADMISSION CONFLICT',
        'correlation': {
            'apaarMatch': '100% Match',
            'dobMatch': '100% Match',
            'fuzzyNameMatch': '92% Match',
        },
        'instA': {
            'code': 'AICTE-1-49281',
            'name': 'National Institute of Technology, Trichy',
            'location': 'Thuvakudi, Tiruchirappalli, Tamil Nadu (CFTI / Institute of National Importance)',
            'type': 'CLAIMANT INST A',
            'studentName': 'A. Sharma',
            'program': 'B.Tech Computer Science (Year 1)',
            'timestamp': '15 Jul 2025 • 11:32:04 IST',
            'quota': 'JoSAA Merit (Open/GEN)',
            'tuitionFee': 'Fully Remitted (Txn: SBI-98129)',
            'status': 'Enrolled & Biometrics Assigned',
            'officer': 'Prof. M. Soundararajan (Registrar Academic)',
        },
        'instB': {
            'code': 'AICTE-1-12048',
            'name': 'Vellore Institute of Technology',
            'location': 'Katpadi, Vellore, Tamil Nadu (Institution of Eminence / Deemed)',
            'type': 'CLAIMANT INST B',
            'studentName': 'Abhinav S.',
            'program': 'B.Tech Information Technology (Year 1)',
            'timestamp': '22 Jul 2025 • 17:08:51 IST',
            'quota': 'Management / Institutional Quota',
            'tuitionFee': 'Provisional Token Advance (Txn: HDFC-4410)',
            'status': 'Enrolled (Orientation Pending)',
            'note': 'Candidate likely accepted Seat B without formally processing Seat A release.',
        },
        'defaultJustification': 'Verified admission logs. JoSAA seat surrender receipt #JSA-2025-0982 submitted by candidate on 20-Jul-2025 prior to accepting management seat at VIT. Recommending purge of active state at NIT Trichy.',
    },
    {
        'id': 'case-2',
        'ref': 'XC-DUP-2025-9942',
        'apaarId': '8812-7491-1029',
        'detectedAt': '23 Jul 2025, 15:04 IST',
        'flagType': 'CONCURRENT ADMISSION CONFLICT',
        'correlation': {
            'apaarMatch': '100% Match',
            'dobMatch': '100% Match',
            'fuzzyNameMatch': '98% Match',
        },
        'instA': {
            'code': 'AICTE-1-20914',
            'name': 'COEP Technological University',
            'location': 'Shivajinagar, Pune, Maharashtra (Unitary Public University)',
            'type': 'CLAIMANT INST A',
            'studentName': 'Pooja R. Deshmukh',
            'program': 'M.Tech Artificial Intelligence (Year 1)',
            'timestamp': '12 Jul 2025 • 09:14:22 IST',
            'quota': 'GATE Central Counseling (Open/OBC)',
            'tuitionFee': 'Fully Remitted (Txn: BOB-77312)',
            'status': 'Enrolled & Biometrics Assigned',
            'officer': 'Dr. V. N. Pande (Dean Academics)',
        },
        'instB': {
            'code': 'AICTE-1-33104',
            'name': 'Sardar Patel Institute of Technology',
            'location': 'Andheri West, Mumbai, Maharashtra (Autonomous Affiliated)',
            'type': 'CLAIMANT INST B',
            'studentName': 'Pooja Deshmukh',
            'program': 'M.Tech Data Science (Year 1)',
            'timestamp': '19 Jul 2025 • 16:45:10 IST',
            'quota': 'Institutional Direct Quota',
            'tuitionFee': 'Provisional Deposit (Txn: ICICI-1102)',
            'status': 'Enrolled (Verification Incomplete)',
            'note': 'Dual seat booking suspected across state cap rounds. Physical dossier inspection required.',
        },
        'defaultJustification': 'Candidate is currently attending classes at COEP Tech Pune. Provisional registration at SPIT Mumbai was not confirmed with original transfer certificates.',
    },
    {
        'id': 'case-3',
        'ref': 'XC-DUP-2025-9943',
        'apaarId': '7104-3291-5820',
        'detectedAt': '23 Jul 2025, 16:30 IST',
        'flagType': 'LATERAL ENTRY COLLISION',
        'correlation': {
            'apaarMatch': '100% Match',
            'dobMatch': '100% Match',
            'fuzzyNameMatch': '100% Match',
        },
        'instA': {
            'code': 'AICTE-1-41901',
            'name': 'PSG College of Technology',
            'location': 'Peelamedu, Coimbatore, Tamil Nadu (Autonomous Govt-Aided)',
            'type': 'CLAIMANT INST A',
            'studentName': 'Karthik Subramanian',
            'program': 'B.Tech Robotics & Automation (Year 2 Lateral)',
            'timestamp': '14 Jul 2025 • 10:11:00 IST',
            'quota': 'TNEA Single Window Lateral Merit',
            'tuitionFee': 'Fully Remitted (Txn: IOB-55104)',
            'status': 'Enrolled & Hostelled',
            'officer': 'Dr. K. Prakasan (Principal)',
        },
        'instB': {
            'code': 'AICTE-1-40291',
            'name': 'SSN College of Engineering',
            'location': 'Kalavakkam, Chennai, Tamil Nadu (Autonomous / Anna Univ)',
            'type': 'CLAIMANT INST B',
            'studentName': 'Karthik Subramanian',
            'program': 'B.Tech Electronics & Communication (Year 2 Lateral)',
            'timestamp': '18 Jul 2025 • 14:02:18 IST',
            'quota': 'Management Lateral Merit',
            'tuitionFee': 'Full Fee Advance (Txn: AXIS-3901)',
            'status': 'Provisional Admission Issued',
            'note': 'Dossier duplicate flagged during Anna University central database sync.',
        },
        'defaultJustification': 'Candidate accepted TNEA state merit seat at PSG Tech. Refund application filed with SSN Chennai under UGC/AICTE refund mandate 2025.',
    },
]

triage_fields = [
    'id', 'ref', 'apaarId', 'detectedAt', 'flagType',
    'correlation_apaarMatch', 'correlation_dobMatch', 'correlation_fuzzyNameMatch',
    'instA_code', 'instA_name', 'instA_location', 'instA_type', 'instA_studentName', 'instA_program', 'instA_timestamp', 'instA_quota', 'instA_tuitionFee', 'instA_status', 'instA_officer',
    'instB_code', 'instB_name', 'instB_location', 'instB_type', 'instB_studentName', 'instB_program', 'instB_timestamp', 'instB_quota', 'instB_tuitionFee', 'instB_status', 'instB_note',
    'defaultJustification'
]

with open(os.path.join(out_dir, 'triage_cases.csv'), 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=triage_fields)
    writer.writeheader()
    for t in triage_data:
        r = {
            'id': t['id'],
            'ref': t['ref'],
            'apaarId': t['apaarId'],
            'detectedAt': t['detectedAt'],
            'flagType': t['flagType'],
            'correlation_apaarMatch': t['correlation']['apaarMatch'],
            'correlation_dobMatch': t['correlation']['dobMatch'],
            'correlation_fuzzyNameMatch': t['correlation']['fuzzyNameMatch'],
            'instA_code': t['instA']['code'],
            'instA_name': t['instA']['name'],
            'instA_location': t['instA']['location'],
            'instA_type': t['instA']['type'],
            'instA_studentName': t['instA']['studentName'],
            'instA_program': t['instA']['program'],
            'instA_timestamp': t['instA']['timestamp'],
            'instA_quota': t['instA']['quota'],
            'instA_tuitionFee': t['instA']['tuitionFee'],
            'instA_status': t['instA']['status'],
            'instA_officer': t['instA']['officer'],
            'instB_code': t['instB']['code'],
            'instB_name': t['instB']['name'],
            'instB_location': t['instB']['location'],
            'instB_type': t['instB']['type'],
            'instB_studentName': t['instB']['studentName'],
            'instB_program': t['instB']['program'],
            'instB_timestamp': t['instB']['timestamp'],
            'instB_quota': t['instB']['quota'],
            'instB_tuitionFee': t['instB']['tuitionFee'],
            'instB_status': t['instB']['status'],
            'instB_note': t['instB']['note'],
            'defaultJustification': t['defaultJustification'],
        }
        writer.writerow(r)

# 6. INITIAL_AUDIT_EVENTS
audit_data = [
    {
        'id': 'EVT-2025-08914',
        'timestamp': 'Today, 14:32:08 IST',
        'category': 'BATCH_SUBMISSION',
        'subCategory': 'Direct Bulk Ingestion',
        'actor': 'admin@nitt.edu',
        'actorOrg': 'NIT Trichy (C-49281)',
        'actorIp': 'IP: 14.139.182.20',
        'targetEntity': 'Batch #2024-B09 (120 Rows)',
        'targetSub': 'B.Tech CSE Semester 1',
        'targetDetail': 'APAAR Assigned: 118 records',
        'outcome': 'SUCCESS',
        'notes': 'Ingestion schema v2.4 validated. All 120 student records matched structural integrity. Zero unmasked Aadhaar retention verified.',
        'hashShort': 'sha256: 8f4a...9b12',
        'hashFull': '8f4a21074e5b6c891290bb3ac8912ef098481cbda78213894bf8921092487192',
        'role': 'Institution Admin',
    },
    {
        'id': 'EVT-2025-08902',
        'timestamp': 'Today, 13:45:19 IST',
        'category': 'DUPLICATE_ADJUDICATION',
        'subCategory': 'Affidavit Override',
        'actor': 'aicte.ro.south@aicte-india.org',
        'actorOrg': 'AICTE Central Desk (RO-S)',
        'actorIp': 'IP: 164.100.12.89',
        'targetEntity': 'APAAR: ••••-••••-8921',
        'targetSub': 'Colliding: NITT vs. Anna Univ',
        'targetDetail': 'Seat ID: SEAT-TN-2024',
        'outcome': 'RESOLVED',
        'notes': 'Cross-institution collision dismissed. Dual-admission affidavit #AFF-2024-901 approved by Regional Officer. Seat released at previous inst.',
        'hashShort': 'sha256: 3c2e...7d04',
        'hashFull': '3c2e5541ba924ee7d04a621748231904128941bcdef128941298418920194812',
        'role': 'AICTE Reviewer',
    },
    {
        'id': 'EVT-2025-08889',
        'timestamp': 'Today, 11:14:02 IST',
        'category': 'VALIDATION_RUN',
        'subCategory': 'Intake Quota Gate',
        'actor': 'operator@coep.ac.in',
        'actorOrg': 'COEP Pune (C-41582)',
        'actorIp': 'IP: 103.21.58.114',
        'targetEntity': 'Batch #COEP-MECH-04',
        'targetSub': 'Attempted: 194 / Quota: 180',
        'targetDetail': 'Surplus: 14 unapproved seats',
        'outcome': 'BLOCKED',
        'notes': 'Statutory Rule 4(A) Violation: Actual enrolment registrations exceed sanctioned AICTE ceiling. Ingestion halted pending Academic Council resolution.',
        'hashShort': 'sha256: 1a9f...e62b',
        'hashFull': '1a9fe62b14589d9841bbce829370144910294182930418293041892301928341',
        'role': 'Institution Operator',
    },
    {
        'id': 'EVT-2025-08871',
        'timestamp': 'Today, 09:20:44 IST',
        'category': 'MOCK_VERIFY_QUERY',
        'subCategory': 'External BGV Engine',
        'actor': 'bgv-agent@infosys.com',
        'actorOrg': 'External Verifier (Infosys HR)',
        'actorIp': 'API Client #CL-9481',
        'targetEntity': 'APAAR: ••••-••••-4129',
        'targetSub': 'Degree: B.Tech ECE (Grad 2024)',
        'targetDetail': 'JNTUH Hyderabad',
        'outcome': 'VERIFIED',
        'notes': 'Mock Adapter returned MOCK_VERIFIED. Cryptographic certificate signature validated against State Board master keys. Zero PII transmitted.',
        'hashShort': 'sha256: 7e8d...1503',
        'hashFull': '7e8d54109848fde15039128038ab141092841092481092481092841029481203',
        'role': 'External Verifier',
    },
    {
        'id': 'EVT-2025-08865',
        'timestamp': 'Yesterday, 18:04:12 IST',
        'category': 'RECORD_CORRECTION',
        'subCategory': 'Name Syntax Realignment',
        'actor': 'registrar@vnit.ac.in',
        'actorOrg': 'VNIT Nagpur (C-41444)',
        'actorIp': 'IP: 14.139.112.55',
        'targetEntity': 'APAAR: ••••-••••-6019',
        'targetSub': 'Field: student_legal_name',
        'targetDetail': 'Enrolment: 2023-VNIT-049',
        'outcome': 'SUCCESS',
        'notes': 'Name transliteration corrected against Class 10th Gazette certificate #GZ-881. Prior hash chained. Reason code: SPELLING_GAZETTE_UPDATE.',
        'hashShort': 'sha256: 52a1...bc90',
        'hashFull': '52a104928bcf8912bc9001928374189201948129034812904812904812904812',
        'role': 'Institution Admin',
    },
    {
        'id': 'EVT-2025-08840',
        'timestamp': 'Yesterday, 16:11:30 IST',
        'category': 'DATA_EXPORT',
        'subCategory': 'Accreditation Dossier',
        'actor': 'nba.evaluator@nic.in',
        'actorOrg': 'NBA Peer Review Committee',
        'actorIp': 'IP: 164.100.24.11',
        'targetEntity': 'NIT Trichy Institutional Pack',
        'targetSub': 'Format: Encrypted XML + PDF',
        'targetDetail': 'Record Count: 4,120',
        'outcome': 'EXPORTED',
        'notes': 'Authorized statutory export under NEP 2020 Institutional Review guidelines. Cryptographic watermark #NBA-NITT-2024 embedded in output payload.',
        'hashShort': 'sha256: 99c0...6b17',
        'hashFull': '99c0491823abce126b1700941824109284102948120948120948120948120948',
        'role': 'AICTE Reviewer',
    },
    {
        'id': 'EVT-2025-08812',
        'timestamp': 'Yesterday, 12:40:05 IST',
        'category': 'VALIDATION_RUN',
        'subCategory': 'DOB Out-of-Bounds',
        'actor': 'operator@svce.ac.in',
        'actorOrg': 'SVCE Chennai (C-16521)',
        'actorIp': 'IP: 182.73.19.4',
        'targetEntity': 'APAAR: ••••-••••-1194',
        'targetSub': 'Date of Birth: 2017-04-12',
        'targetDetail': 'Enrolment: B.Tech 2024',
        'outcome': 'FLAGGED',
        'notes': 'Age anomaly detected (computed age: 7 years for undergraduate admissions). Record isolated to exception queue; institute notified for re-verification.',
        'hashShort': 'sha256: 4b18...71ef',
        'hashFull': '4b1871ef49201bcde11940128941290481209481209481209481209481209481',
        'role': 'Institution Operator',
    },
    {
        'id': 'EVT-2025-08798',
        'timestamp': '2 days ago, 23:59:00 IST',
        'category': 'ZERO_AADHAAR_PURGE',
        'subCategory': 'Automated Cron Sweep',
        'actor': 'system.daemon@apaar.gov.in',
        'actorOrg': 'Central Cryptographic Daemon',
        'actorIp': 'Node: Secure Enclave 01',
        'targetEntity': 'Ingestion Memory Buffer (Daily)',
        'targetSub': 'Transient Hash Registers',
        'targetDetail': 'Status: Zero residual bytes',
        'outcome': 'COMPLIANT',
        'notes': 'Section 17 DPDP Act 2023 purge routine executed. Memory sanitization completed across 14 server clusters. Zero biometric residues logged.',
        'hashShort': 'sha256: 22fb...0041',
        'hashFull': '22fb0041928471bcfe0019248719204918204918204918204918204918204918',
        'role': 'AICTE Reviewer',
    },
]

audit_fields = ['id', 'timestamp', 'category', 'subCategory', 'actor', 'actorOrg', 'actorIp', 'targetEntity', 'targetSub', 'targetDetail', 'outcome', 'notes', 'hashShort', 'hashFull', 'role']
with open(os.path.join(out_dir, 'initial_audit_events.csv'), 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=audit_fields)
    writer.writeheader()
    writer.writerows(audit_data)

# 7. INITIAL_BREACH_RECORDS (Discovered in AicteCentralReviewPage.tsx)
breach_data = [
    {
        'pid': '1-3329182',
        'name': 'K.J. Somaiya College of Engineering',
        'location': 'Mumbai, Maharashtra',
        'course': 'B.Tech AI & DS',
        'affiliation': 'Autonomous / Somaiya Univ',
        'cap': 120,
        'intake': 132,
        'excess': 12,
        'excessTag': '+12 Excess',
        'citation': 'APH 2025 Cl 7.2.3',
        'citationDesc': 'Over-intake without EWS quota offset',
        'actionText': 'Show Cause Notice',
        'actionStyle': 'error',
        'state': 'Maharashtra',
    },
    {
        'pid': '1-4910283',
        'name': 'BMS College of Engineering',
        'location': 'Bengaluru, Karnataka',
        'course': 'M.Tech VLSI Design',
        'affiliation': 'Affiliated / VTU Belagavi',
        'cap': 24,
        'intake': 29,
        'excess': 5,
        'excessTag': '+5 Excess',
        'citation': 'APH 2025 Cl 4.1.8',
        'citationDesc': 'Exceeded PG batch limit per faculty cadre',
        'actionText': 'Explanations Filed',
        'actionStyle': 'subtle',
        'state': 'Karnataka',
    },
    {
        'pid': '1-1928402',
        'name': 'SRM Institute of Science & Technology',
        'location': 'Kattankulathur, Tamil Nadu',
        'course': 'B.Tech Mechanical',
        'affiliation': 'Deemed-to-be-University',
        'cap': 180,
        'intake': 182,
        'excess': 2,
        'excessTag': '+2 Excess',
        'citation': 'APH 2025 Cl 2.9.1',
        'citationDesc': 'Candidate enrolled under J&K PMSSS quota discrepancy',
        'actionText': 'Review Supernumerary',
        'actionStyle': 'subtle',
        'state': 'Tamil Nadu',
    },
    {
        'pid': '1-8840192',
        'name': 'Dr. A.P.J. Abdul Kalam Technical University Regional Campus',
        'location': 'Lucknow, Uttar Pradesh',
        'course': 'MCA',
        'affiliation': 'State Government University',
        'cap': 60,
        'intake': 71,
        'excess': 11,
        'excessTag': '+11 Excess',
        'citation': 'APH 2025 Cl 6.4.0',
        'citationDesc': 'Unapproved evening section batch merge',
        'actionText': 'Show Cause Notice',
        'actionStyle': 'error',
        'state': 'Uttar Pradesh',
    },
    {
        'pid': '1-5519201',
        'name': 'COEP Technological University',
        'location': 'Pune, Maharashtra',
        'course': 'B.Tech Electrical Engineering',
        'affiliation': 'Unitary State University',
        'cap': 60,
        'intake': 66,
        'excess': 6,
        'excessTag': '+6 Excess',
        'citation': 'APH 2025 Cl 3.1.2',
        'citationDesc': 'TFWS lateral intake exceeded 5% statutory ceiling',
        'actionText': 'Show Cause Notice',
        'actionStyle': 'error',
        'state': 'Maharashtra',
    },
    {
        'pid': '1-7712903',
        'name': 'R.V. College of Engineering',
        'location': 'Bengaluru, Karnataka',
        'course': 'B.Tech Cyber Security',
        'affiliation': 'Affiliated / VTU Belagavi',
        'cap': 60,
        'intake': 64,
        'excess': 4,
        'excessTag': '+4 Excess',
        'citation': 'APH 2025 Cl 5.2.0',
        'citationDesc': 'Supernumerary sports / defense quota overflow',
        'actionText': 'Review Supernumerary',
        'actionStyle': 'subtle',
        'state': 'Karnataka',
    },
]

breach_fields = ['pid', 'name', 'location', 'course', 'affiliation', 'cap', 'intake', 'excess', 'excessTag', 'citation', 'citationDesc', 'actionText', 'actionStyle', 'state']
with open(os.path.join(out_dir, 'initial_breach_records.csv'), 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=breach_fields)
    writer.writeheader()
    writer.writerows(breach_data)

# 8. ROLE_DATASETS (Discovered in frontend/src/data/rolesData.ts)
roles_data = [
    {
        'key': 'admin',
        'shortTitle': 'Inst. Admin',
        'subtitle': 'Apex Institute',
        'icon': 'account_balance',
        'title': 'Institution Administrator',
        'tag': 'Role Scope: Tier-1 Regulatory Node',
        'tagClass': 'bg-primary-fixed text-on-primary-fixed',
        'description': 'Full authority to manage institution profile, execute verified bulk student ingestion, submit regulatory enrollment batches to AICTE central registry, and manage sanctioned program intakes.',
        'email': 'apex_admin@apex.edu.in',
        'pid': 'INST-001',
        'pwd': 'DemoPassword@2026',
    },
    {
        'key': 'operator',
        'shortTitle': 'Inst. Operator',
        'subtitle': 'Apex Institute',
        'icon': 'input',
        'title': 'Institution Operator',
        'tag': 'Role Scope: Academic Cell Operations',
        'tagClass': 'bg-surface-container-high text-on-surface',
        'description': 'Operates CSV / XLSX parsing pipelines, column re-mapping utilities, syntax and format discrepancy resolution, and unvalidated draft student updates.',
        'email': 'apex_operator@apex.edu.in',
        'pid': 'INST-001',
        'pwd': 'DemoPassword@2026',
    },
    {
        'key': 'reviewer',
        'shortTitle': 'AICTE Admin',
        'subtitle': 'National Council',
        'icon': 'policy',
        'title': 'AICTE Statutory Admin / Reviewer',
        'tag': 'Role Scope: Directorate Oversight',
        'tagClass': 'bg-status-review-surface text-status-review',
        'description': 'Council authority to detect cross-institution duplicate APAAR requests, inspect regional intake threshold overages, and issue formal gazette approvals.',
        'email': 'aicte_admin@aicte.gov.in',
        'pid': 'HQ-STATUTORY-DELHI',
        'pwd': 'DemoPassword@2026',
    },
    {
        'key': 'verifier',
        'shortTitle': 'Bharat Admin',
        'subtitle': 'Bharat Eng College',
        'icon': 'quick_reference_all',
        'title': 'Cross-Tenant College Admin',
        'tag': 'Role Scope: INST-002 Boundary Isolation',
        'tagClass': 'bg-surface-subtle text-on-surface-variant',
        'description': 'Institution Admin for secondary college (INST-002) demonstrating tenant data isolation and cross-institution candidate duplicate review.',
        'email': 'bharat_admin@bharat.edu.in',
        'pid': 'INST-002',
        'pwd': 'DemoPassword@2026',
    },
    {
        'key': 'evaluator',
        'shortTitle': 'Demo Admin',
        'subtitle': 'National Scope',
        'icon': 'developer_mode_tv',
        'title': 'SIH-2026 Demo Evaluator',
        'tag': 'Role Scope: Platform Sandbox Control',
        'tagClass': 'bg-status-verified-surface text-status-verified',
        'description': 'SIH Evaluation Jury profile: Instant access to mock adapters, synthetic population resets, edge-case generation, and live duplicate injection tests.',
        'email': 'demo_admin@apaar.gov.in',
        'pid': 'SIH-EVAL-26263',
        'pwd': 'DemoPassword@2026',
    },
]

role_fields = ['key', 'shortTitle', 'subtitle', 'icon', 'title', 'tag', 'tagClass', 'description', 'email', 'pid', 'pwd']
with open(os.path.join(out_dir, 'role_datasets.csv'), 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=role_fields)
    writer.writeheader()
    writer.writerows(roles_data)

print('Export complete. Generating manifest...')

manifest = {
    'version': '1.0.0',
    'exported_at': '2026-10-25T14:07:00Z',
    'datasets': [
        {
            'source_file': 'frontend/src/pages/InstitutionDashboardPage.tsx',
            'constant_name': 'DEPARTMENT_DATA',
            'output_file': 'department_data.csv',
            'record_count': len(dept_data),
            'columns': dept_fields,
            'sha256': sha256_file(os.path.join(out_dir, 'department_data.csv'))
        },
        {
            'source_file': 'frontend/src/pages/BulkImportValidationPage.tsx',
            'constant_name': 'INITIAL_DIAGNOSTICS',
            'output_file': 'initial_diagnostics.csv',
            'record_count': len(diag_data),
            'columns': diag_fields,
            'sha256': sha256_file(os.path.join(out_dir, 'initial_diagnostics.csv'))
        },
        {
            'source_file': 'frontend/src/pages/DataQualityFindingsPage.tsx',
            'constant_name': 'INITIAL_FINDINGS',
            'output_file': 'initial_findings.csv',
            'record_count': len(findings_data),
            'columns': findings_fields,
            'sha256': sha256_file(os.path.join(out_dir, 'initial_findings.csv'))
        },
        {
            'source_file': 'frontend/src/pages/StudentRecordCertificatePage.tsx',
            'constant_name': 'MOCK_PROFILES',
            'output_file': 'mock_profiles.csv',
            'record_count': len(profiles_data),
            'columns': profile_fields,
            'sha256': sha256_file(os.path.join(out_dir, 'mock_profiles.csv')),
            'nested_relations': [
                {
                    'relation_name': 'auditTrail',
                    'output_file': 'mock_profile_audit_trail.csv',
                    'record_count': sum(len(p['auditTrail']) for p in profiles_data.values()),
                    'columns': profile_audit_fields,
                    'foreign_key': 'apaarId',
                    'sha256': sha256_file(os.path.join(out_dir, 'mock_profile_audit_trail.csv'))
                }
            ]
        },
        {
            'source_file': 'frontend/src/pages/AicteCentralReviewPage.tsx',
            'constant_name': 'TRIAGE_CASES',
            'output_file': 'triage_cases.csv',
            'record_count': len(triage_data),
            'columns': triage_fields,
            'sha256': sha256_file(os.path.join(out_dir, 'triage_cases.csv'))
        },
        {
            'source_file': 'frontend/src/pages/AuditLogsReportsPage.tsx',
            'constant_name': 'INITIAL_AUDIT_EVENTS',
            'output_file': 'initial_audit_events.csv',
            'record_count': len(audit_data),
            'columns': audit_fields,
            'sha256': sha256_file(os.path.join(out_dir, 'initial_audit_events.csv'))
        },
        {
            'source_file': 'frontend/src/pages/AicteCentralReviewPage.tsx',
            'constant_name': 'INITIAL_BREACH_RECORDS',
            'output_file': 'initial_breach_records.csv',
            'record_count': len(breach_data),
            'columns': breach_fields,
            'sha256': sha256_file(os.path.join(out_dir, 'initial_breach_records.csv'))
        },
        {
            'source_file': 'frontend/src/data/rolesData.ts',
            'constant_name': 'ROLE_DATASETS',
            'output_file': 'role_datasets.csv',
            'record_count': len(roles_data),
            'columns': role_fields,
            'sha256': sha256_file(os.path.join(out_dir, 'role_datasets.csv'))
        }
    ]
}

with open(os.path.join(out_dir, 'manifest.json'), 'w', encoding='utf-8') as f:
    json.dump(manifest, f, indent=2)

print('Manifest saved successfully.')
