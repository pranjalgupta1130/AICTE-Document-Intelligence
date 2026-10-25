import React, { useState, useMemo, useRef } from 'react';
import { AuthSession } from '../types/auth';
import { batchService, BackendValidationSummary } from '../services/api';

interface BulkImportValidationPageProps {
  session?: AuthSession | null;
  onLogout?: () => void;
  onNavigateTab?: (tab: string) => void;
}

interface DiagnosticRecord {
  row: number;
  studentId: string;
  apaarId: string;
  category: string;
  status: 'VALID' | 'BLOCKING' | 'DUPLICATE' | 'WARNING';
  note: string;
}

const INITIAL_DIAGNOSTICS: DiagnosticRecord[] = [
  {
    row: 14,
    studentId: 'NITT-2025-014',
    apaarId: '9082-1144-8821',
    category: 'REGULAR',
    status: 'VALID',
    note: 'Format OK • Checksum verified against UIDAI/ABC Mock Registry',
  },
  {
    row: 28,
    studentId: 'NITT-2025-028',
    apaarId: '9082-4412-8821',
    category: 'REGULAR',
    status: 'VALID',
    note: 'Identity verified against Digilocker live seed (Siddharth R. Iyer)',
  },
  {
    row: 42,
    studentId: 'NITT-2025-042',
    apaarId: '[NULL / EMPTY]',
    category: 'EWS',
    status: 'BLOCKING',
    note: 'Field Required by Rule R6 - Mandatory APAAR Identifier Non-Null',
  },
  {
    row: 61,
    studentId: 'NITT-2025-061',
    apaarId: '[MALFORMED_REGEX]',
    category: 'TFW',
    status: 'BLOCKING',
    note: 'Syntactic constraint violation: Expected 12-digit format (xxxx-xxxx-xxxx)',
  },
  {
    row: 77,
    studentId: 'NITT-2025-077',
    apaarId: '8129-3321-9011',
    category: 'REGULAR',
    status: 'DUPLICATE',
    note: 'Collision with Row 108: APAAR Re-assignment Disallowed across records',
  },
  {
    row: 108,
    studentId: 'NITT-2025-108',
    apaarId: '8129-3321-9011',
    category: 'REGULAR',
    status: 'DUPLICATE',
    note: 'Collision with Row 77: In-batch duplicate assignment rejected under Rule R11',
  },
  {
    row: 115,
    studentId: 'NITT-2025-115',
    apaarId: '3488-2910-4491',
    category: 'NRI',
    status: 'WARNING',
    note: 'Rule R4: INCONSISTENT_CATEGORY (NRI requires Passport / OCI Ref)',
  },
  {
    row: 142,
    studentId: 'NITT-2025-142',
    apaarId: '5510-9921-3841',
    category: 'SUPERNUMERARY',
    status: 'WARNING',
    note: 'Rule R8: PMSSS quota verification pending state nodality endorsement',
  },
];

export const BulkImportValidationPage: React.FC<BulkImportValidationPageProps> = ({
  session,
  onLogout,
  onNavigateTab,
}) => {
  const [filterType, setFilterType] = useState<string>('ALL');
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [showComplianceModal, setShowComplianceModal] = useState<boolean>(false);
  const [diagnosticsList, setDiagnosticsList] = useState<DiagnosticRecord[]>(INITIAL_DIAGNOSTICS);

  // Live Batch Processing States
  const [activeBatchId, setActiveBatchId] = useState<string | null>(null);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const [uploadedFileSize, setUploadedFileSize] = useState<string | null>(null);
  const [isLiveBatch, setIsLiveBatch] = useState<boolean>(false);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [isValidating, setIsValidating] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [totalRowsCount, setTotalRowsCount] = useState<number>(1420);
  const [validationSummary, setValidationSummary] = useState<BackendValidationSummary | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 3500);
  };

  const handleDownloadTemplate = () => {
    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [
        'APAAR_ID,INST_STUDENT_ID,PROGRAMME,ACADEMIC_YEAR,SEAT_TYPE,NRI_OCI_FN,ADMISSION_STATUS',
        '9082-1144-8821,NITT-2025-001,BTECH-CSE-01,2025-2026,REGULAR,,CONFIRMED',
        '9082-4412-8821,NITT-2025-002,BTECH-CSE-01,2025-2026,REGULAR,,CONFIRMED',
        '8812-7491-1029,NITT-2025-003,BTECH-ECE-02,2025-2026,EWS,,CONFIRMED',
      ].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', 'AICTE_APAAR_Batch_Template_v2.4.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast('Downloaded official AICTE APH Batch Template (.CSV)');
  };

  const sanitizeCsvValue = (val: string | number): string => {
    const s = String(val ?? '');
    if (s.length > 0 && ['=', '+', '-', '@', '|', '%'].includes(s[0])) {
      return `'\t${s}`;
    }
    return s.replace(/"/g, '""');
  };

  const handleDownloadErrorCsv = () => {
    const errorRows = diagnosticsList.filter(
      (d) => d.status === 'BLOCKING' || d.status === 'DUPLICATE' || d.status === 'WARNING'
    );
    const headers = ['Row_Number', 'Student_ID', 'APAAR_ID', 'Category', 'Violation_Status', 'Diagnostic_Note'];
    const rows = errorRows.map((e) => [
      e.row,
      `"${sanitizeCsvValue(e.studentId)}"`,
      `"${sanitizeCsvValue(e.apaarId)}"`,
      `"${sanitizeCsvValue(e.category)}"`,
      `"${sanitizeCsvValue(e.status)}"`,
      `"${sanitizeCsvValue(e.note)}"`,
    ]);
    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    const filename = activeBatchId ? `${activeBatchId}_Exceptions.csv` : 'BATCH_2025_NITTRICHY_004_Exceptions.csv';
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast(`Downloaded Exception Diagnostic CSV (${errorRows.length} Rows)`);
  };

  const handleTriggerFileSelect = () => {
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
      fileInputRef.current.click();
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // File validation
    const fname = file.name.toLowerCase();
    if (!fname.endsWith('.csv') && !fname.endsWith('.xlsx')) {
      setUploadError('Invalid file type: Please select a CSV (.csv) or Excel (.xlsx) file.');
      showToast('Error: Only .csv and .xlsx files are supported.');
      return;
    }

    if (file.size > 25 * 1024 * 1024) {
      setUploadError('File exceeds size limit: Maximum file size is 25MB.');
      showToast('Error: File size exceeds 25MB limit.');
      return;
    }

    setUploadError(null);
    setIsUploading(true);
    setUploadedFileName(file.name);
    setUploadedFileSize(`${(file.size / (1024 * 1024)).toFixed(2)} MB`);

    try {
      showToast(`Uploading ${file.name} to AICTE Ingestion Pipeline...`);
      const commitRes = await batchService.uploadImportFile(file, '2026-2027');

      setActiveBatchId(commitRes.batch_id);
      setIsLiveBatch(true);
      setTotalRowsCount(commitRes.total_rows);

      showToast(`Batch created: ${commitRes.batch_id} (${commitRes.total_rows} rows ingested).`);

      // Immediately trigger deterministic validation
      await triggerBatchValidation(commitRes.batch_id);
    } catch (err: any) {
      console.error('File upload failed:', err);
      setUploadError(err?.message || 'Failed to upload file to backend.');
      showToast(`Upload failed: ${err?.message || 'Server error'}`);
    } finally {
      setIsUploading(false);
    }
  };

  const triggerBatchValidation = async (batchId: string) => {
    setIsValidating(true);
    try {
      showToast(`Executing deterministic validation on Batch ${batchId}...`);
      const valRes = await batchService.validateBatch(batchId);
      setValidationSummary(valRes.validation_summary);

      // Fetch live explainable findings
      const findingsRes = await batchService.getBatchFindings(batchId, 100);

      const mappedDiagnostics: DiagnosticRecord[] = findingsRes.items.map((f, idx) => {
        let status: 'VALID' | 'BLOCKING' | 'DUPLICATE' | 'WARNING' = 'VALID';
        if (f.severity === 'BLOCKING_ERROR') {
          status = f.rule_code.includes('DUP') ? 'DUPLICATE' : 'BLOCKING';
        } else if (f.severity === 'WARNING') {
          status = 'WARNING';
        }

        return {
          row: f.row_number || (idx + 1),
          studentId: f.record_id ? f.record_id.substring(0, 14) : `REC-${idx + 1}`,
          apaarId: f.actual_value || '[N/A]',
          category: f.field_name ? f.field_name.toUpperCase() : 'STUDENT_RECORD',
          status,
          note: `${f.rule_code}: ${f.message}${f.suggested_action ? ` • Suggestion: ${f.suggested_action}` : ''}`,
        };
      });

      if (mappedDiagnostics.length > 0) {
        setDiagnosticsList(mappedDiagnostics);
      } else {
        // 100% valid records
        setDiagnosticsList([
          {
            row: 1,
            studentId: 'ALL_RECORDS',
            apaarId: 'VERIFIED',
            category: 'COHORT',
            status: 'VALID',
            note: 'All ingested student records passed Verhoeff checksum, syntax, and intake reconciliation checks.',
          },
        ]);
      }

      showToast(`Validation complete: Status is ${valRes.status}. Found ${valRes.findings_count} findings.`);
    } catch (err: any) {
      console.error('Validation failed:', err);
      showToast(`Validation error: ${err?.message || 'Failed to validate batch'}`);
    } finally {
      setIsValidating(false);
    }
  };

  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  const handleDiscardBatch = async () => {
    if (!activeBatchId) {
      // If it's only mock state, reset local UI state
      if (window.confirm('No live batch active. Reset staging workspace to empty state?')) {
        setDiagnosticsList([]);
        setIsLiveBatch(false);
        setValidationSummary(null);
        setUploadedFileName(null);
        showToast('Staging workspace reset.');
      }
      return;
    }

    const confirmMsg =
      `Are you sure you want to permanently delete batch "${activeBatchId}"?\n\n` +
      `WARNING: This will remove all ${totalRowsCount} ingested student records, validation findings, ` +
      `and clear historical duplicate collisions from this batch in the database.\n\n` +
      `This action cannot be undone.`;

    if (!window.confirm(confirmMsg)) {
      return;
    }

    setIsDeleting(true);
    try {
      showToast(`Deleting batch ${activeBatchId} and rolling back records...`);
      const res = await batchService.deleteBatch(activeBatchId);

      setDiagnosticsList([]);
      setActiveBatchId(null);
      setIsLiveBatch(false);
      setValidationSummary(null);
      setUploadedFileName(null);
      setUploadedFileSize(null);
      setUploadError(null);

      showToast(
        `Successfully deleted batch ${res.batch_id} (${res.deleted_records} records, ${res.deleted_findings} findings removed).`
      );
    } catch (err: any) {
      console.error('Batch deletion failed:', err);
      showToast(`Failed to delete batch: ${err?.message || 'Server error'}`);
    } finally {
      setIsDeleting(false);
    }
  };

  const filteredDiagnostics = useMemo(() => {
    if (filterType === 'ALL') return diagnosticsList;
    if (filterType === 'BLOCKING') {
      return diagnosticsList.filter((d) => d.status === 'BLOCKING' || d.status === 'DUPLICATE');
    }
    return diagnosticsList.filter((d) => d.status === filterType);
  }, [filterType, diagnosticsList]);

  return (
    <div className="tricolor-slant-bg font-body-md text-on-surface antialiased min-h-screen flex flex-col relative selection:bg-secondary/20">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-primary text-on-primary px-space-md py-space-sm rounded-lg shadow-xl font-body-sm text-body-sm flex items-center gap-space-xs animate-bounce border border-secondary/40">
          <span className="material-symbols-outlined text-status-verified text-[18px]">
            verified
          </span>
          <span>{toastMessage}</span>
          <button
            onClick={() => setToastMessage(null)}
            className="ml-2 text-white/60 hover:text-white"
          >
            <span className="material-symbols-outlined text-sm">close</span>
          </button>
        </div>
      )}

      {/* TOP INSTITUTIONAL HEADER */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-surface-card border-b border-border-subtle shadow-[0_1px_8px_rgba(0,0,0,0.04)]">
        <div className="h-14 w-full px-gutter-md flex items-center justify-between">
          <div className="flex items-center gap-space-md">
            <div className="flex items-center gap-2">
              <span className="text-2xl select-none" role="img" aria-label="emblem">
                🏛️
              </span>
              <div className="flex flex-col">
                <div className="flex items-center gap-space-xs">
                  <span className="font-headline-sm text-headline-sm text-primary tracking-tight font-bold">
                    APAAR
                  </span>
                  <span className="font-label-sm text-label-sm text-on-surface-variant font-medium">
                    | Student Data Management Platform
                  </span>
                </div>
                <span className="font-label-sm text-label-sm text-outline hidden xl:inline">
                  अखिल भारतीय तकनीकी शिक्षा परिषद | All India Council for Technical Education
                </span>
              </div>
            </div>
            <span className="font-code-sm text-code-sm bg-surface-container-high text-primary px-space-xs py-space-2xs rounded-lg border border-border-strong font-semibold ml-space-xs">
              SIH-2026 PROTOTYPE
            </span>
          </div>

          <div className="flex items-center gap-space-md">
            <div className="hidden lg:flex items-center gap-space-xs bg-surface-subtle px-space-sm py-space-xs rounded-lg border border-border-subtle">
              <span className="material-symbols-outlined text-outline text-[16px]">
                school
              </span>
              <span className="font-code-sm text-code-sm text-on-surface-variant max-w-[280px] truncate">
                {session?.instCode
                  ? `Node (${session.instCode})`
                  : 'National Institute of Technology, Trichy (ID: AICTE-1-49281)'}
              </span>
            </div>

            <div className="relative">
              <select
                defaultValue={session?.roleTitle || 'Institution Operator'}
                className="font-label-md text-label-md bg-surface-card border border-border-strong text-primary rounded-lg px-space-sm py-space-xs focus:ring-1 focus:ring-secondary focus:outline-none cursor-pointer"
              >
                <option value="Institution Admin">Institution Admin</option>
                <option value="Institution Operator">Institution Operator</option>
                <option value="AICTE Reviewer">AICTE Reviewer</option>
              </select>
            </div>

            <button
              aria-label="Notifications"
              onClick={() => showToast('Batch #BATCH-2025-NITTRICHY-004 has 12 blocking errors.')}
              className="relative p-space-xs text-on-surface-variant hover:text-primary transition-colors cursor-pointer"
            >
              <span className="material-symbols-outlined text-[20px]">notifications</span>
              <span className="absolute top-1 right-1 w-2 h-2 bg-status-error rounded-full animate-pulse"></span>
            </button>

            <div className="flex items-center gap-space-xs pl-space-xs border-l border-border-subtle">
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center font-headline-sm text-headline-sm text-on-primary font-bold shadow-sm">
                <span className="material-symbols-outlined text-on-primary text-[18px]">
                  person
                </span>
              </div>
              <div className="hidden md:flex flex-col">
                <span className="font-label-md text-label-md text-on-surface font-semibold leading-tight">
                  {session?.roleTitle || 'RK (Registrar)'}
                </span>
                <span className="font-label-sm text-label-sm text-outline leading-tight">
                  {session?.userEmail || 'Academic Cell'}
                </span>
              </div>
              {onLogout && (
                <button
                  onClick={onLogout}
                  title="Sign Out to Login Page"
                  className="ml-2 p-1.5 hover:bg-surface-subtle text-outline hover:text-status-error rounded-md transition-colors flex items-center gap-1 text-xs cursor-pointer"
                >
                  <span className="material-symbols-outlined text-[18px]">logout</span>
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="h-10 w-full px-gutter-md flex items-center gap-space-lg border-t border-border-subtle bg-surface-card overflow-x-auto">
          {[
            { id: 'dashboard', label: 'Institution Dashboard' },
            { id: 'import', label: 'Bulk Import & Validation' },
            { id: 'findings', label: 'Data Quality & Findings' },
            { id: 'aicte-review', label: 'AICTE Central Review' },
            { id: 'records', label: 'Student Record & Certificate' },
            { id: 'reports', label: 'Audit Logs & Reports' },
          ].map((tab) => {
            const isActive = tab.id === 'import';
            return (
              <button
                key={tab.id}
                onClick={() => {
                  if (onNavigateTab) {
                    onNavigateTab(tab.id);
                  }
                }}
                className={`font-title-md text-title-md px-space-sm h-full flex items-center transition-colors whitespace-nowrap cursor-pointer ${
                  isActive
                    ? 'text-primary border-b-2 border-primary font-semibold bg-surface-subtle'
                    : 'text-on-surface-variant hover:text-primary hover:bg-surface-subtle'
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </nav>

        {/* Real-time Subticker */}
        <div className="h-8 w-full bg-surface-subtle border-t border-b border-border-subtle px-gutter-md flex items-center justify-between text-xs">
          <div className="flex items-center gap-space-xs overflow-hidden">
            <span className="w-2 h-2 rounded-full bg-status-verified animate-pulse shrink-0"></span>
            <span className="font-code-sm text-code-sm text-on-surface font-medium truncate">
              APAAR ID-Based Student Verification Engine • Mock Adapter Active (MOCK_VERIFIED / MOCK_UNAVAILABLE) • Synthetic Dataset v2.4
            </span>
          </div>
          <div className="hidden sm:flex items-center gap-space-sm shrink-0">
            <span className="font-label-sm text-label-sm text-outline">
              Sovereign Security: ISO/IEC 27001 Validated
            </span>
            <span className="font-label-sm text-label-sm text-status-verified font-medium">
              ● Sync Operational
            </span>
          </div>
        </div>
      </header>

      {/* MAIN CONTAINER */}
      <main className="w-full pt-32 bg-transparent min-h-screen pb-16">
        <div className="flex flex-col w-full">
          {/* Top Sovereign Utility Banner & Context Anchor */}
          <div className="w-full bg-surface-card/85 backdrop-blur-md border-b border-border-subtle py-space-xl">
            <div className="max-w-[1440px] mx-auto px-gutter-md flex flex-col md:flex-row md:items-center justify-between gap-space-lg">
              <div>
                <div className="flex items-center gap-space-xs mb-space-xs">
                  <span className="font-code-sm text-code-sm text-outline tracking-wider uppercase">
                    Verification Pipeline
                  </span>
                  <span className="text-outline opacity-60">/</span>
                  <span className="font-code-sm text-code-sm text-secondary font-semibold">
                    Engine SIH-26263
                  </span>
                  <span className="text-outline opacity-60">/</span>
                  <span className="font-code-sm text-code-sm bg-surface-subtle text-primary border border-border-subtle px-space-xs py-space-2xs rounded-lg">
                    Rule Set v4.8.2
                  </span>
                </div>
                <h1 className="font-headline-lg text-headline-lg text-primary tracking-tight font-bold">
                  Bulk Import &amp; Validation Engine
                </h1>
                <p className="font-body-md text-body-md text-on-surface-variant pt-space-2xs">
                  Deterministic pre-ingestion audit against AICTE Sovereign Guidelines and Academic Bank of Credits (ABC) standards.
                </p>
              </div>

              <div className="flex items-center gap-space-md self-start md:self-auto flex-wrap">
                {/* Hidden Real File Input */}
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  accept=".csv,.xlsx"
                  className="hidden"
                />

                <button
                  type="button"
                  onClick={handleTriggerFileSelect}
                  disabled={isUploading || isValidating}
                  className="inline-flex items-center gap-space-xs bg-secondary text-on-secondary px-space-lg py-space-sm rounded-lg hover:bg-secondary-fixed transition-all font-title-md text-title-md shadow-md cursor-pointer disabled:opacity-50"
                >
                  <span className={`material-symbols-outlined text-[18px] ${isUploading ? 'animate-spin' : ''}`}>
                    {isUploading ? 'refresh' : 'upload_file'}
                  </span>
                  <span>{isUploading ? 'Uploading Dataset...' : 'Select Dataset (Upload)'}</span>
                </button>

                <button
                  onClick={handleDownloadTemplate}
                  className="inline-flex items-center gap-space-xs bg-surface-card border border-border-subtle text-primary px-space-lg py-space-sm rounded-lg hover:bg-surface-subtle transition-colors font-title-md text-title-md shadow-sm cursor-pointer"
                >
                  <span className="material-symbols-outlined text-[18px] text-outline">
                    file_download
                  </span>
                  <span>Official Template (XLSX)</span>
                </button>
                <button
                  onClick={() => setShowComplianceModal(true)}
                  className="inline-flex items-center gap-space-xs bg-primary text-on-primary px-space-lg py-space-sm rounded-lg hover:bg-navy-deep transition-all font-title-md text-title-md shadow-sm cursor-pointer"
                  type="button"
                >
                  <span className="material-symbols-outlined text-[18px]">verified</span>
                  <span>Compliance Specs</span>
                </button>
              </div>
            </div>
          </div>

          <div className="max-w-[1440px] w-full mx-auto px-gutter-md py-space-xl space-y-space-xl">
            {/* Step Indicator (Civic Stepper) */}
            <div className="w-full bg-surface-card border border-border-subtle rounded-xl p-space-xl shadow-sm">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-space-xl relative">
                {/* Step 1 */}
                <div className="flex items-start gap-space-md group">
                  <div className="w-9 h-9 rounded-full bg-status-verified-surface text-status-verified flex items-center justify-center shrink-0 border border-status-verified-border">
                    <span className="material-symbols-outlined text-[18px]">check</span>
                  </div>
                  <div className="min-w-0 pt-space-2xs">
                    <span className="font-label-sm text-label-sm text-status-verified block uppercase font-bold tracking-wider">
                      Step 01 • Finished
                    </span>
                    <span className="font-title-md text-title-md text-on-surface block truncate font-semibold">
                      Upload Source Data
                    </span>
                    <span className="font-body-sm text-body-sm text-outline block truncate mt-space-2xs">
                      1.4 MB parsed
                    </span>
                  </div>
                </div>

                {/* Step 2 */}
                <div className="flex items-start gap-space-md group">
                  <div className="w-9 h-9 rounded-full bg-status-verified-surface text-status-verified flex items-center justify-center shrink-0 border border-status-verified-border">
                    <span className="material-symbols-outlined text-[18px]">check</span>
                  </div>
                  <div className="min-w-0 pt-space-2xs">
                    <span className="font-label-sm text-label-sm text-status-verified block uppercase font-bold tracking-wider">
                      Step 02 • Finished
                    </span>
                    <span className="font-title-md text-title-md text-on-surface block truncate font-semibold">
                      Schema Mapping
                    </span>
                    <span className="font-body-sm text-body-sm text-outline block truncate mt-space-2xs">
                      7/7 Mandatory Matched
                    </span>
                  </div>
                </div>

                {/* Step 3 */}
                <div className="flex items-start gap-space-md relative">
                  <div className="w-9 h-9 rounded-full bg-primary text-on-primary flex items-center justify-center shrink-0 shadow-md">
                    <span className="material-symbols-outlined text-[18px]">rule</span>
                  </div>
                  <div className="min-w-0 pt-space-2xs">
                    <span className="font-label-sm text-label-sm text-secondary block uppercase font-bold tracking-wider">
                      Step 03 • In Inspection
                    </span>
                    <span className="font-title-md text-title-md text-primary font-bold block truncate">
                      Rule Verification
                    </span>
                    <span className="font-body-sm text-body-sm text-on-surface-variant block truncate mt-space-2xs">
                      1,420 rows verified
                    </span>
                  </div>
                </div>

                {/* Step 4 */}
                <div className="flex items-start gap-space-md opacity-60">
                  <div className="w-9 h-9 rounded-full bg-surface-subtle text-outline flex items-center justify-center shrink-0 border border-border-subtle">
                    <span className="font-label-md text-label-md font-semibold">04</span>
                  </div>
                  <div className="min-w-0 pt-space-2xs">
                    <span className="font-label-sm text-label-sm text-outline block uppercase tracking-wider font-semibold">
                      Step 04 • Locked
                    </span>
                    <span className="font-title-md text-title-md text-on-surface-variant block truncate">
                      Final Ingestion
                    </span>
                    <span className="font-body-sm text-body-sm text-outline block truncate mt-space-2xs">
                      Pending blocker clearance
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Ingestion Metadata & Batch Anchor Section */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-space-xl">
              <div className="lg:col-span-8 bg-surface-card border border-border-subtle rounded-xl p-space-xl shadow-sm flex flex-col justify-between space-y-space-lg">
                <div>
                  <div className="flex items-center justify-between pb-space-md border-b border-border-subtle">
                    <div className="flex items-center gap-space-sm">
                      <span className="material-symbols-outlined text-secondary text-[22px]">
                        inventory_2
                      </span>
                      <span className="font-title-md text-title-md text-primary uppercase tracking-wide font-bold">
                        Payload Manifest &amp; Session Profile
                      </span>
                    </div>
                    <span className="font-code-sm text-code-sm bg-status-verified-surface text-status-verified border border-status-verified-border px-space-sm py-space-2xs rounded-lg font-semibold">
                      {isLiveBatch ? 'LIVE BATCH ACTIVE' : 'SYNTAX VERIFIED'}
                    </span>
                  </div>

                  {/* Upload Error Banner if any */}
                  {uploadError && (
                    <div className="mt-space-sm p-space-sm rounded bg-status-error-surface border border-status-error-border flex items-center gap-space-sm text-status-error font-body-sm text-body-sm">
                      <span className="material-symbols-outlined text-[20px] shrink-0">error</span>
                      <span className="font-medium">{uploadError}</span>
                    </div>
                  )}

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-space-xl py-space-lg">
                    <div>
                      <span className="font-label-sm text-label-sm text-outline block uppercase tracking-wider">
                        Target Dataset
                      </span>
                      <span
                        className="font-title-md text-title-md text-on-surface font-semibold truncate block mt-space-2xs"
                        title={uploadedFileName || (isLiveBatch ? 'Live Batch' : 'NIT_Trichy_UG_2025.xlsx')}
                      >
                        {uploadedFileName || (isLiveBatch ? 'Uploaded Dataset' : 'NIT_Trichy_UG_2025.xlsx')}
                      </span>
                      <span className="font-body-sm text-body-sm text-on-surface-variant mt-space-2xs block">
                        {uploadedFileSize || '1.4 MB'} • {totalRowsCount} Records
                      </span>
                    </div>
                    <div>
                      <span className="font-label-sm text-label-sm text-outline block uppercase tracking-wider">
                        Session Operator
                      </span>
                      <span className="font-title-md text-title-md text-on-surface font-semibold block truncate mt-space-2xs">
                        {session?.userEmail || session?.roleTitle || 'Operator'}
                      </span>
                      <span className="font-body-sm text-body-sm text-on-surface-variant mt-space-2xs block">
                        {session?.roleTitle || 'Academic Cell'}
                      </span>
                    </div>
                    <div>
                      <span className="font-label-sm text-label-sm text-outline block uppercase tracking-wider">
                        Batch ID &amp; Timestamp
                      </span>
                      <span className="font-code-sm text-code-sm text-primary font-bold block truncate mt-space-2xs">
                        {activeBatchId || 'BATCH-2025-NITTRICHY-004'}
                      </span>
                      <span className="font-body-sm text-body-sm text-on-surface-variant mt-space-2xs block">
                        {isLiveBatch ? 'Active Live Session' : '12 Oct 2025, 14:32 IST'}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex flex-wrap items-center justify-between gap-space-md pt-space-md border-t border-border-subtle text-on-surface-variant">
                  <div className="flex items-center gap-space-xs">
                    <span className="material-symbols-outlined text-[18px] text-status-verified">
                      verified_user
                    </span>
                    <span className="font-body-sm text-body-sm">
                      ISO/IEC 8859 Compliant UTF-8 • Strict Regex Enforcement
                    </span>
                  </div>
                  <span className="font-code-sm text-code-sm bg-surface-subtle text-primary border border-border-subtle px-space-sm py-space-2xs rounded-lg font-medium">
                    Row Buffer: {totalRowsCount} / {totalRowsCount} parsed
                  </span>
                </div>
              </div>

              {/* AICTE Official Schema Spec Card */}
              <div className="lg:col-span-4 bg-primary text-on-primary rounded-xl p-space-xl shadow-sm flex flex-col justify-between space-y-space-md">
                <div className="space-y-space-md">
                  <div className="flex items-center gap-space-sm">
                    <span className="material-symbols-outlined text-[22px] text-secondary-fixed">
                      assignment_turned_in
                    </span>
                    <h2 className="font-headline-sm text-headline-sm text-on-primary font-bold">
                      AICTE Official Schema Spec
                    </h2>
                  </div>
                  <p className="font-body-sm text-body-sm text-surface-container-high leading-relaxed">
                    All submitted payloads must conform to the 7 mandatory regulatory columns before central synchronization.
                  </p>
                  <div className="bg-navy-deep p-space-md rounded-lg space-y-space-xs border border-white/10">
                    <div className="font-code-sm text-code-sm text-secondary-fixed font-semibold tracking-wider uppercase">
                      Mandatory Fields
                    </div>
                    <p className="font-code-sm text-code-sm text-surface-container-high leading-relaxed">
                      APAAR_ID, INST_STUDENT_ID, PROGRAMME, ACADEMIC_YEAR, SEAT_TYPE, NRI_OCI_FN, ADMISSION_STATUS
                    </p>
                  </div>
                </div>
                <div className="pt-space-md">
                  <button
                    onClick={() => setShowComplianceModal(true)}
                    className="w-full inline-flex items-center justify-center gap-space-xs bg-surface-card text-primary py-space-sm px-space-md rounded-lg font-title-md text-title-md hover:bg-surface-subtle transition-colors shadow-sm cursor-pointer"
                  >
                    <span className="material-symbols-outlined text-[18px]">download</span>
                    <span>Format Guide &amp; Samples</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Column Mapping Verification Matrix */}
            <div className="w-full bg-surface-card border border-border-subtle rounded-xl p-space-xl shadow-sm space-y-space-lg">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-space-sm pb-space-sm border-b border-border-subtle">
                <div>
                  <h2 className="font-headline-sm text-headline-sm text-primary font-bold">
                    Column Mapping &amp; Type Verification Matrix
                  </h2>
                  <p className="font-body-sm text-body-sm text-on-surface-variant pt-space-2xs">
                    Registry schema fields verified against institutional incoming columns.
                  </p>
                </div>
                <span className="font-label-sm text-label-sm bg-status-verified-surface text-status-verified border border-status-verified-border px-space-sm py-space-2xs rounded-lg font-semibold self-start sm:self-auto">
                  Auto-Mapped: 7 of 7 Fields
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead className="border-b border-border-subtle">
                    <tr className="text-outline font-label-sm text-label-sm uppercase tracking-wider">
                      <th className="py-space-md px-space-md font-semibold">
                        Standard AICTE Attribute
                      </th>
                      <th className="py-space-md px-space-md font-semibold">Detected Header</th>
                      <th className="py-space-md px-space-md font-semibold">
                        Data Type &amp; Constraint
                      </th>
                      <th className="py-space-md px-space-md font-semibold text-right">
                        Match Integrity
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-subtle font-body-sm text-body-sm">
                    <tr className="hover:bg-surface-subtle/50 transition-colors">
                      <td className="py-space-md px-space-md font-semibold text-primary">
                        APAAR_ID
                      </td>
                      <td className="py-space-md px-space-md font-code-sm text-code-sm text-on-surface-variant">
                        apaar_uid_no
                      </td>
                      <td className="py-space-md px-space-md">
                        <span className="font-code-sm text-code-sm text-on-surface">
                          12-Digit Alphanumeric/Numeric String [Regex: ^[0-9]&#123;4&#125;-[0-9]&#123;4&#125;-[0-9]&#123;4&#125;$]
                        </span>
                      </td>
                      <td className="py-space-md px-space-md text-right">
                        <span className="inline-flex items-center gap-space-2xs text-status-verified font-label-md text-label-md">
                          <span className="material-symbols-outlined text-[16px]">check_circle</span>{' '}
                          Verified
                        </span>
                      </td>
                    </tr>
                    <tr className="hover:bg-surface-subtle/50 transition-colors">
                      <td className="py-space-md px-space-md font-semibold text-primary">
                        INST_STUDENT_ID
                      </td>
                      <td className="py-space-md px-space-md font-code-sm text-code-sm text-on-surface-variant">
                        roll_number
                      </td>
                      <td className="py-space-md px-space-md">
                        <span className="font-code-sm text-code-sm text-on-surface">
                          String [Max 32 Chars, Unique in Inst.]
                        </span>
                      </td>
                      <td className="py-space-md px-space-md text-right">
                        <span className="inline-flex items-center gap-space-2xs text-status-verified font-label-md text-label-md">
                          <span className="material-symbols-outlined text-[16px]">check_circle</span>{' '}
                          Verified
                        </span>
                      </td>
                    </tr>
                    <tr className="hover:bg-surface-subtle/50 transition-colors">
                      <td className="py-space-md px-space-md font-semibold text-primary">
                        PROGRAMME
                      </td>
                      <td className="py-space-md px-space-md font-code-sm text-code-sm text-on-surface-variant">
                        academic_prog_code
                      </td>
                      <td className="py-space-md px-space-md">
                        <span className="font-code-sm text-code-sm text-on-surface">
                          AICTE Approved Academic Discipline Registry Code
                        </span>
                      </td>
                      <td className="py-space-md px-space-md text-right">
                        <span className="inline-flex items-center gap-space-2xs text-status-verified font-label-md text-label-md">
                          <span className="material-symbols-outlined text-[16px]">check_circle</span>{' '}
                          Verified
                        </span>
                      </td>
                    </tr>
                    <tr className="hover:bg-surface-subtle/50 transition-colors">
                      <td className="py-space-md px-space-md font-semibold text-primary">
                        ACADEMIC_YEAR
                      </td>
                      <td className="py-space-md px-space-md font-code-sm text-code-sm text-on-surface-variant">
                        admitted_year
                      </td>
                      <td className="py-space-md px-space-md">
                        <span className="font-code-sm text-code-sm text-on-surface">
                          YYYY-YYYY (Active Cohort: 2025-2026)
                        </span>
                      </td>
                      <td className="py-space-md px-space-md text-right">
                        <span className="inline-flex items-center gap-space-2xs text-status-verified font-label-md text-label-md">
                          <span className="material-symbols-outlined text-[16px]">check_circle</span>{' '}
                          Verified
                        </span>
                      </td>
                    </tr>
                    <tr className="hover:bg-surface-subtle/50 transition-colors">
                      <td className="py-space-md px-space-md font-semibold text-primary">
                        SEAT_TYPE
                      </td>
                      <td className="py-space-md px-space-md font-code-sm text-code-sm text-on-surface-variant">
                        category_quota
                      </td>
                      <td className="py-space-md px-space-md">
                        <span className="font-code-sm text-code-sm text-on-surface">
                          Enum [REGULAR, TFW, EWS, SUPERNUMERARY, NRI]
                        </span>
                      </td>
                      <td className="py-space-md px-space-md text-right">
                        <span className="inline-flex items-center gap-space-2xs text-status-verified font-label-md text-label-md">
                          <span className="material-symbols-outlined text-[16px]">check_circle</span>{' '}
                          Verified
                        </span>
                      </td>
                    </tr>
                    <tr className="hover:bg-surface-subtle/50 transition-colors">
                      <td className="py-space-md px-space-md font-semibold text-primary">
                        NRI_OCI_FN
                      </td>
                      <td className="py-space-md px-space-md font-code-sm text-code-sm text-on-surface-variant">
                        intl_status_flag
                      </td>
                      <td className="py-space-md px-space-md">
                        <span className="font-code-sm text-code-sm text-on-surface">
                          Conditional String [Passport / OCI Card No. if NRI]
                        </span>
                      </td>
                      <td className="py-space-md px-space-md text-right">
                        <span className="inline-flex items-center gap-space-2xs text-status-verified font-label-md text-label-md">
                          <span className="material-symbols-outlined text-[16px]">check_circle</span>{' '}
                          Verified
                        </span>
                      </td>
                    </tr>
                    <tr className="hover:bg-surface-subtle/50 transition-colors">
                      <td className="py-space-md px-space-md font-semibold text-primary">
                        ADMISSION_STATUS
                      </td>
                      <td className="py-space-md px-space-md font-code-sm text-code-sm text-on-surface-variant">
                        adm_state
                      </td>
                      <td className="py-space-md px-space-md">
                        <span className="font-code-sm text-code-sm text-on-surface">
                          Enum [CONFIRMED, PROVISIONAL, CANCELLED]
                        </span>
                      </td>
                      <td className="py-space-md px-space-md text-right">
                        <span className="inline-flex items-center gap-space-2xs text-status-verified font-label-md text-label-md">
                          <span className="material-symbols-outlined text-[16px]">check_circle</span>{' '}
                          Verified
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            {/* Real-time Pre-validation Engine Summary & Console */}
            <div className="w-full bg-surface-card border border-border-subtle rounded-xl p-space-xl shadow-sm space-y-space-xl">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-space-md pb-space-md border-b border-border-subtle">
                <div>
                  <div className="flex items-center gap-space-xs">
                    <span className="w-2.5 h-2.5 rounded-full bg-status-verified"></span>
                    <h2 className="font-headline-sm text-headline-sm text-primary font-bold">
                      Pre-Validation Verification Console
                    </h2>
                  </div>
                  <p className="font-body-sm text-body-sm text-on-surface-variant pt-space-2xs">
                    Syntactic checks, mock sovereign adapter responses, and collision diagnostics complete.
                  </p>
                </div>
                <div className="flex items-center gap-space-xl">
                  <div className="text-right">
                    <span className="font-label-sm text-label-sm text-outline block uppercase tracking-wider">
                      Adapter Latency
                    </span>
                    <span className="font-code-sm text-code-sm text-primary font-semibold">
                      120ms (MOCK_VERIFIED)
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="font-label-sm text-label-sm text-outline block uppercase tracking-wider">
                      Execution Elapsed
                    </span>
                    <span className="font-code-sm text-code-sm text-primary font-semibold">
                      1.8s (100% Parsed)
                    </span>
                  </div>
                </div>
              </div>

              {/* Progress & Breakdown */}
              <div className="space-y-space-md">
                <div className="flex justify-between items-center text-label-sm font-label-sm">
                  <span className="text-primary font-bold uppercase tracking-wider">
                    {isValidating ? 'Validating Dataset...' : `100% Processed (${totalRowsCount} of ${totalRowsCount} Rows)`}
                  </span>
                  <span className="text-on-surface-variant font-code-sm text-code-sm">
                    {isLiveBatch ? `AICTE Engine: Rule Set R1 - R12 Active` : 'Rule Matrix: R1 - R12 Applied'}
                  </span>
                </div>

                <div className="w-full h-2 rounded-full overflow-hidden flex bg-surface-subtle">
                  <div
                    className="bg-status-verified h-full"
                    style={{
                      width: `${
                        totalRowsCount > 0
                          ? ((validationSummary?.valid_records ?? (totalRowsCount - 28)) / totalRowsCount) * 100
                          : 100
                      }%`,
                    }}
                    title="Valid Records"
                  ></div>
                  <div
                    className="bg-status-error h-full"
                    style={{
                      width: `${
                        totalRowsCount > 0
                          ? ((validationSummary?.error_count ?? 12) / totalRowsCount) * 100
                          : 0
                      }%`,
                    }}
                    title="Critical Errors"
                  ></div>
                  <div
                    className="bg-status-review h-full"
                    style={{
                      width: `${
                        totalRowsCount > 0
                          ? ((validationSummary?.warning_count ?? 16) / totalRowsCount) * 100
                          : 0
                      }%`,
                    }}
                    title="Warnings"
                  ></div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-space-lg pt-space-xs">
                  <div
                    onClick={() => setFilterType('VALID')}
                    className={`p-space-lg bg-surface-card border rounded-xl flex items-center justify-between shadow-sm cursor-pointer transition-all ${
                      filterType === 'VALID'
                        ? 'border-status-verified ring-2 ring-status-verified/20'
                        : 'border-status-verified-border hover:bg-surface-subtle'
                    }`}
                  >
                    <div>
                      <span className="font-label-sm text-label-sm text-status-verified uppercase font-bold tracking-wider block">
                        Valid Records
                      </span>
                      <span className="font-headline-lg text-headline-lg text-status-verified font-bold mt-space-2xs block">
                        {validationSummary ? validationSummary.valid_records : 1392}
                      </span>
                      <span className="font-body-sm text-body-sm text-on-surface-variant mt-space-2xs block">
                        {totalRowsCount > 0
                          ? `${Math.round(
                              ((validationSummary?.valid_records ?? 1392) / totalRowsCount) * 100
                            )}% of cohort`
                          : '100%'}
                      </span>
                    </div>
                    <div className="w-10 h-10 rounded-full bg-status-verified-surface flex items-center justify-center">
                      <span className="material-symbols-outlined text-[24px] text-status-verified">
                        check_circle
                      </span>
                    </div>
                  </div>

                  <div
                    onClick={() => setFilterType('BLOCKING')}
                    className={`p-space-lg bg-surface-card border rounded-xl flex items-center justify-between shadow-sm cursor-pointer transition-all ${
                      filterType === 'BLOCKING'
                        ? 'border-status-error ring-2 ring-status-error/20'
                        : 'border-status-error-border hover:bg-surface-subtle'
                    }`}
                  >
                    <div>
                      <span className="font-label-sm text-label-sm text-status-error uppercase font-bold tracking-wider block">
                        Critical Blocking Errors
                      </span>
                      <span className="font-headline-lg text-headline-lg text-status-error font-bold mt-space-2xs block">
                        {validationSummary ? validationSummary.error_count : 12}
                      </span>
                      <span className="font-body-sm text-body-sm text-on-surface-variant mt-space-2xs block">
                        Prevents Ingestion
                      </span>
                    </div>
                    <div className="w-10 h-10 rounded-full bg-status-error-surface flex items-center justify-center">
                      <span className="material-symbols-outlined text-[24px] text-status-error">
                        dangerous
                      </span>
                    </div>
                  </div>

                  <div
                    onClick={() => setFilterType('WARNING')}
                    className={`p-space-lg bg-surface-card border rounded-xl flex items-center justify-between shadow-sm cursor-pointer transition-all ${
                      filterType === 'WARNING'
                        ? 'border-status-review ring-2 ring-status-review/20'
                        : 'border-status-review-border hover:bg-surface-subtle'
                    }`}
                  >
                    <div>
                      <span className="font-label-sm text-label-sm text-status-review uppercase font-bold tracking-wider block">
                        Review Warnings
                      </span>
                      <span className="font-headline-lg text-headline-lg text-status-review font-bold mt-space-2xs block">
                        {validationSummary ? validationSummary.warning_count : 16}
                      </span>
                      <span className="font-body-sm text-body-sm text-on-surface-variant mt-space-2xs block">
                        Conditional Attention
                      </span>
                    </div>
                    <div className="w-10 h-10 rounded-full bg-status-review-surface flex items-center justify-center">
                      <span className="material-symbols-outlined text-[24px] text-status-review">
                        warning
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Sample Record Diagnostics Preview */}
              <div className="space-y-space-md pt-space-md">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-space-xs gap-2">
                  <div className="flex items-center gap-space-sm">
                    <span className="font-title-md text-title-md text-primary font-bold">
                      Sample Record Diagnostics Preview
                    </span>
                    <span className="font-label-sm text-label-sm text-outline">
                      ({filteredDiagnostics.length} items shown)
                    </span>
                  </div>

                  {/* Filter pills */}
                  <div className="flex items-center gap-1.5 text-xs">
                    {['ALL', 'BLOCKING', 'WARNING', 'VALID'].map((f) => (
                      <button
                        key={f}
                        onClick={() => setFilterType(f)}
                        className={`px-2.5 py-1 rounded-md font-semibold cursor-pointer transition-colors ${
                          filterType === f
                            ? 'bg-primary text-white'
                            : 'bg-surface-subtle text-outline hover:text-primary'
                        }`}
                      >
                        {f}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="overflow-x-auto rounded-xl border border-border-subtle">
                  <table className="w-full text-left">
                    <thead className="bg-surface-subtle">
                      <tr className="text-outline font-label-sm text-label-sm uppercase tracking-wider">
                        <th className="py-space-md px-space-md w-16 font-semibold">Row</th>
                        <th className="py-space-md px-space-md font-semibold">
                          Candidate Student ID
                        </th>
                        <th className="py-space-md px-space-md font-semibold">
                          APAAR Identifier
                        </th>
                        <th className="py-space-md px-space-md font-semibold">Seat Category</th>
                        <th className="py-space-md px-space-md font-semibold">Rule Status</th>
                        <th className="py-space-md px-space-md font-semibold">
                          Audit Diagnostic Note
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-subtle font-body-sm text-body-sm bg-surface-card">
                      {filteredDiagnostics.map((rec) => {
                        const isBlock = rec.status === 'BLOCKING' || rec.status === 'DUPLICATE';
                        const isWarn = rec.status === 'WARNING';
                        return (
                          <tr
                            key={rec.row}
                            className={`transition-colors ${
                              isBlock
                                ? 'bg-status-error-surface/30 hover:bg-status-error-surface/50'
                                : isWarn
                                ? 'bg-status-review-surface/40 hover:bg-status-review-surface/60'
                                : 'hover:bg-surface-subtle/50'
                            }`}
                          >
                            <td
                              className={`py-space-md px-space-md font-code-sm text-code-sm font-semibold ${
                                isBlock
                                  ? 'text-status-error font-bold'
                                  : isWarn
                                  ? 'text-status-review font-bold'
                                  : 'text-outline'
                              }`}
                            >
                              {rec.row}
                            </td>
                            <td className="py-space-md px-space-md font-code-sm text-code-sm text-primary font-medium">
                              {rec.studentId}
                            </td>
                            <td
                              className={`py-space-md px-space-md font-code-sm text-code-sm font-semibold ${
                                isBlock
                                  ? 'text-status-error'
                                  : isWarn
                                  ? 'text-status-review'
                                  : 'text-on-surface'
                              }`}
                            >
                              {rec.apaarId}
                            </td>
                            <td className="py-space-md px-space-md">
                              <span className="font-code-sm text-code-sm text-on-surface-variant">
                                {rec.category}
                              </span>
                            </td>
                            <td className="py-space-md px-space-md">
                              {rec.status === 'VALID' && (
                                <span className="inline-flex items-center gap-space-2xs text-status-verified font-label-md text-label-md font-semibold">
                                  <span className="material-symbols-outlined text-[16px]">
                                    check_circle
                                  </span>{' '}
                                  VALID
                                </span>
                              )}
                              {rec.status === 'BLOCKING' && (
                                <span className="inline-flex items-center gap-space-2xs text-status-error font-label-md text-label-md font-semibold">
                                  <span className="material-symbols-outlined text-[16px]">
                                    block
                                  </span>{' '}
                                  BLOCKING
                                </span>
                              )}
                              {rec.status === 'DUPLICATE' && (
                                <span className="inline-flex items-center gap-space-2xs text-status-error font-label-md text-label-md font-semibold">
                                  <span className="material-symbols-outlined text-[16px]">
                                    report
                                  </span>{' '}
                                  DUPLICATE
                                </span>
                              )}
                              {rec.status === 'WARNING' && (
                                <span className="inline-flex items-center gap-space-2xs text-status-review font-label-md text-label-md font-semibold">
                                  <span className="material-symbols-outlined text-[16px]">
                                    warning
                                  </span>{' '}
                                  WARNING
                                </span>
                              )}
                            </td>
                            <td className="py-space-md px-space-md font-code-sm text-code-sm text-on-surface-variant">
                              <span
                                className={
                                  isBlock
                                    ? 'text-status-error font-medium'
                                    : isWarn
                                    ? 'text-status-review font-medium'
                                    : ''
                                }
                              >
                                {rec.note}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* Rule Rationale & Audit Explainability Panel (Bento Insight) */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-space-xl">
              <div className="bg-surface-card border border-border-subtle p-space-xl rounded-xl shadow-sm flex flex-col justify-between space-y-space-md">
                <div className="space-y-space-sm">
                  <div className="flex items-center gap-space-xs text-status-error">
                    <span className="material-symbols-outlined text-[20px]">error_outline</span>
                    <span className="font-label-sm text-label-sm font-bold uppercase tracking-wider">
                      Rule R6 Enforcement
                    </span>
                  </div>
                  <h3 className="font-title-md text-title-md text-primary font-bold">
                    Mandatory Identifier Non-Null
                  </h3>
                  <p className="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">
                    Under NEP 2020 integration mandate, unassigned APAAR records cannot participate in unified credit transfer or degree locker synchronization.
                  </p>
                </div>
                <div className="pt-space-sm border-t border-border-subtle">
                  <span className="font-code-sm text-code-sm text-outline">
                    Affected: 8 records
                  </span>
                </div>
              </div>

              <div className="bg-surface-card border border-border-subtle p-space-xl rounded-xl shadow-sm flex flex-col justify-between space-y-space-md">
                <div className="space-y-space-sm">
                  <div className="flex items-center gap-space-xs text-status-error">
                    <span className="material-symbols-outlined text-[20px]">copy_all</span>
                    <span className="font-label-sm text-label-sm font-bold uppercase tracking-wider">
                      Rule R11 Disambiguation
                    </span>
                  </div>
                  <h3 className="font-title-md text-title-md text-primary font-bold">
                    In-Batch Uniqueness Constraint
                  </h3>
                  <p className="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">
                    A single student APAAR ID was assigned multiple times in this upload session across differing registration lines, causing duplicate identity rejection.
                  </p>
                </div>
                <div className="pt-space-sm border-t border-border-subtle">
                  <span className="font-code-sm text-code-sm text-outline">
                    Affected: 4 collision instances
                  </span>
                </div>
              </div>

              <div className="bg-surface-card border border-border-subtle p-space-xl rounded-xl shadow-sm flex flex-col justify-between space-y-space-md">
                <div className="space-y-space-sm">
                  <div className="flex items-center gap-space-xs text-status-review">
                    <span className="material-symbols-outlined text-[20px]">verified</span>
                    <span className="font-label-sm text-label-sm font-bold uppercase tracking-wider">
                      Rule R4 Foreign Seats
                    </span>
                  </div>
                  <h3 className="font-title-md text-title-md text-primary font-bold">
                    Supernumerary Category Audit
                  </h3>
                  <p className="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">
                    NRI/PIO seats require active passport metadata for foreign national clearance prior to state quota allocation.
                  </p>
                </div>
                <div className="pt-space-sm border-t border-border-subtle">
                  <span className="font-code-sm text-code-sm text-outline">
                    Affected: 16 warnings flagged
                  </span>
                </div>
              </div>
            </div>

            {/* Bottom Sticky Action Bar / Sovereign Approval Control */}
            <div className="w-full bg-surface-card border border-border-subtle rounded-xl p-space-xl shadow-md flex flex-col md:flex-row items-center justify-between gap-space-lg">
              <div className="flex flex-wrap items-center gap-space-md w-full md:w-auto">
                <button
                  onClick={handleDownloadErrorCsv}
                  className="inline-flex items-center gap-space-xs bg-surface-card border border-border-subtle text-primary px-space-lg py-space-sm rounded-lg hover:bg-surface-subtle transition-colors font-title-md text-title-md shadow-sm cursor-pointer"
                  type="button"
                >
                  <span className="material-symbols-outlined text-[18px] text-outline">
                    file_download
                  </span>
                  <span>Download Error CSV (28 Rows)</span>
                </button>
                <button
                  onClick={handleDiscardBatch}
                  disabled={isDeleting}
                  className="inline-flex items-center gap-space-xs bg-status-error-surface border border-status-error-border text-status-error px-space-lg py-space-sm rounded-lg hover:bg-error-container transition-colors font-title-md text-title-md cursor-pointer disabled:opacity-50"
                  type="button"
                >
                  <span className={`material-symbols-outlined text-[18px] ${isDeleting ? 'animate-spin' : ''}`}>
                    {isDeleting ? 'refresh' : 'delete_sweep'}
                  </span>
                  <span>{isDeleting ? 'Deleting Batch...' : activeBatchId ? 'Delete Batch' : 'Reset Workspace'}</span>
                </button>
              </div>

              <div className="flex items-center gap-space-lg w-full md:w-auto justify-end">
                {activeBatchId && (
                  <button
                    onClick={() => triggerBatchValidation(activeBatchId)}
                    disabled={isValidating}
                    className="inline-flex items-center gap-space-xs bg-secondary text-on-secondary px-space-lg py-space-sm rounded-lg hover:bg-secondary-fixed transition-colors font-title-md text-title-md shadow-sm cursor-pointer disabled:opacity-50"
                    type="button"
                  >
                    <span className={`material-symbols-outlined text-[18px] ${isValidating ? 'animate-spin' : ''}`}>
                      refresh
                    </span>
                    <span>{isValidating ? 'Validating...' : 'Re-Validate Batch'}</span>
                  </button>
                )}

                <div className="hidden sm:flex flex-col text-right pr-space-xs">
                  <span className={`font-label-sm text-label-sm font-bold tracking-wider ${
                    (validationSummary ? validationSummary.error_count : 12) > 0 ? 'text-status-error' : 'text-status-verified'
                  }`}>
                    {validationSummary ? validationSummary.error_count : 12} INGESTION BLOCKERS ACTIVE
                  </span>
                  <span className="font-code-sm text-code-sm text-outline mt-space-2xs">
                    {(validationSummary ? validationSummary.error_count : 12) > 0
                      ? 'Resolution required before Step 4'
                      : 'All records clear for submission'}
                  </span>
                </div>
                <button
                  onClick={() => {
                    if (onNavigateTab) {
                      onNavigateTab('aicte-review');
                    }
                  }}
                  className="w-full sm:w-auto inline-flex items-center justify-center gap-space-xs bg-primary text-on-primary px-space-xl py-space-sm rounded-lg hover:bg-navy-deep transition-all font-title-md text-title-md shadow-md focus:ring-2 focus:ring-secondary focus:outline-none cursor-pointer"
                  type="button"
                >
                  <span className="material-symbols-outlined text-[18px]">troubleshoot</span>
                  <span>Open Explainable Findings Review</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* COMPLIANCE SPECIFICATION MODAL */}
      {showComplianceModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-surface-card rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-border-subtle flex flex-col gap-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-border-subtle pb-3">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-2xl">
                  verified
                </span>
                <h3 className="font-headline-sm text-primary font-bold">
                  AICTE / ABC Data Standard Specification v2.4
                </h3>
              </div>
              <button
                onClick={() => setShowComplianceModal(false)}
                className="text-outline hover:text-primary p-1 rounded cursor-pointer"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            <div className="space-y-3 text-xs text-on-surface leading-relaxed max-h-96 overflow-y-auto pr-1">
              <div className="p-3 bg-surface-subtle rounded-lg border border-border-subtle">
                <div className="font-bold text-primary mb-1">Rule R1: Character Encoding</div>
                <div>Files must be UTF-8 encoded without BOM headers. Max record length: 4,096 bytes per line.</div>
              </div>
              <div className="p-3 bg-surface-subtle rounded-lg border border-border-subtle">
                <div className="font-bold text-primary mb-1">Rule R6: APAAR Identification Mandate</div>
                <div>All candidates enrolled under AICTE approved courses must possess an active 12-digit APAAR UID mapped against UIDAI tokens.</div>
              </div>
              <div className="p-3 bg-surface-subtle rounded-lg border border-border-subtle">
                <div className="font-bold text-primary mb-1">Rule R11: Zero In-Batch Collisions</div>
                <div>Duplicate APAAR assignments within the same ingestion payload trigger instant blocker status until reconciled.</div>
              </div>
              <div className="p-3 bg-surface-subtle rounded-lg border border-border-subtle">
                <div className="font-bold text-primary mb-1">Rule R14: SHA-256 Audit Immutability</div>
                <div>All verification actions generate deterministic cryptographic hashes logged to the sovereign audit trail.</div>
              </div>
            </div>

            <div className="flex justify-between items-center pt-3 border-t border-border-subtle">
              <button
                onClick={handleDownloadTemplate}
                className="text-xs text-secondary font-semibold hover:underline flex items-center gap-1 cursor-pointer"
              >
                <span className="material-symbols-outlined text-sm">download</span>
                <span>Download Sample Dataset</span>
              </button>
              <button
                onClick={() => setShowComplianceModal(false)}
                className="px-4 py-2 bg-primary text-white rounded-lg text-xs font-semibold cursor-pointer"
              >
                Close Specification
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default BulkImportValidationPage;
