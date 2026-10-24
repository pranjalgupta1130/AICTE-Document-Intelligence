import React, { useState, useMemo } from 'react';
import { AuthSession } from '../types/auth';

interface DataQualityFindingsPageProps {
  session?: AuthSession | null;
  onLogout?: () => void;
  onNavigateTab?: (tab: string) => void;
}

interface FindingItem {
  row: number;
  studentId: string;
  name: string;
  branch: string;
  rule: string;
  severity: 'BLOCKING' | 'WARNING' | 'RESOLVED';
  field: string;
  explanation: string;
  suggestedAction: string;
  inputLabel: string;
  inputHint: string;
  placeholder: string;
  defaultVal: string;
  resolvedValue?: string;
  auditNote?: string;
}

const INITIAL_FINDINGS: Record<number, FindingItem> = {
  42: {
    row: 42,
    studentId: 'NITT-2025-CS-042',
    name: 'Aarav K. Sundaram',
    branch: 'B.Tech Computer Science',
    rule: 'RULE-R6-MISSING-APAAR',
    severity: 'BLOCKING',
    field: 'apaar_id',
    explanation:
      'APAAR ID cell is empty. Mandatory academic identifier under AICTE mandate. Without it, academic credits cannot be transferred to the Academic Bank of Credits (ABC).',
    suggestedAction:
      'Input valid 12-digit APAAR syntax (e.g. 7481-9920-3341) verified via ABC registry.',
    inputLabel: 'Rectify APAAR Identifier',
    inputHint: 'Format: XXXX-XXXX-XXXX (12 digits)',
    placeholder: '7481-9920-3341',
    defaultVal: '',
  },
  77: {
    row: 77,
    studentId: 'NITT-2025-ME-077',
    name: 'Priyanka Venkatesh',
    branch: 'B.Tech Mechanical Eng',
    rule: 'RULE-R5-BATCH-DUPLICATE',
    severity: 'BLOCKING',
    field: 'apaar_id',
    explanation:
      'Exact APAAR ID 8129-3321-9011 matches row #108 in same batch. Dual student identity collision detected.',
    suggestedAction:
      'Inspect conflicting rows / Rectify duplicate student ID with correct National Identity register entry.',
    inputLabel: 'Replace with Distinct APAAR ID',
    inputHint: 'Must not collide with row #108',
    placeholder: '8129-3321-9012',
    defaultVal: '8129-3321-9011',
  },
  122: {
    row: 122,
    studentId: 'NITT-2025-ECE-122',
    name: 'Devraj Mukherjee',
    branch: 'B.Tech Electronics & Comm',
    rule: 'RULE-R7-INTAKE-EXCEEDED',
    severity: 'BLOCKING',
    field: 'programme_enrolment',
    explanation:
      'ECE actual enrolment (122) exceeds approved regular intake (120) by 2 seats. AICTE ceiling breach.',
    suggestedAction:
      'Reclassify as approved supernumerary category (e.g., TFW, PMSSS, or EWS) or rectify admission roster.',
    inputLabel: 'Adjust Seat Category Classification',
    inputHint: 'Values: REGULAR | TFW_SUPERNUMERARY | PMSSS_QUOTA | EWS_SUPERNUMERARY',
    placeholder: 'TFW_SUPERNUMERARY',
    defaultVal: 'REGULAR',
  },
  115: {
    row: 115,
    studentId: 'NITT-2025-CIV-115',
    name: 'Rohan Sharma',
    branch: 'B.Tech Civil Engineering',
    rule: 'RULE-R4-SEAT-INCONSISTENCY',
    severity: 'WARNING',
    field: 'nri_status',
    explanation:
      'Marked as NRI quota but nationality listed as Indian without sponsor declaration on file.',
    suggestedAction:
      'Attach upload affidavit token or reclassify quota code to DOMESTIC_OPEN.',
    inputLabel: 'Sponsor Declaration Reference No.',
    inputHint: 'AFFIDAVIT-XXXXXX or update quota',
    placeholder: 'AFFIDAVIT-NITT-2025-881',
    defaultVal: '',
  },
  204: {
    row: 204,
    studentId: 'NITT-2025-EE-204',
    name: 'Kavita Chawla',
    branch: 'B.Tech Electrical Eng',
    rule: 'RULE-R8-SYNTAX-SUSPECT',
    severity: 'WARNING',
    field: 'apaar_id',
    explanation:
      'Mock Adapter check returned MOCK_UNAVAILABLE for gateway response during batch run.',
    suggestedAction:
      'Trigger immediate mock adapter retry probe to clear mock gateway queue.',
    inputLabel: 'Re-trigger Adapter Gateway Protocol',
    inputHint: 'Enter MOCK_VERIFIED to force mock handshake',
    placeholder: 'MOCK_VERIFIED',
    defaultVal: 'MOCK_UNAVAILABLE',
  },
};

export const DataQualityFindingsPage: React.FC<DataQualityFindingsPageProps> = ({
  session,
  onLogout,
  onNavigateTab,
}) => {
  const [findings, setFindings] = useState<Record<number, FindingItem>>(INITIAL_FINDINGS);
  const [activeSelectedRow, setActiveSelectedRow] = useState<number>(42);
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [rulePrefixFilter, setRulePrefixFilter] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState<string>('');

  // Drawer Form State
  const activeFinding = findings[activeSelectedRow] || findings[42];
  const [inputVal, setInputVal] = useState<string>(activeFinding.defaultVal);
  const [auditNote, setAuditNote] = useState<string>('');
  const [toastMessage, setToastMessage] = useState<{ title: string; desc: string } | null>(null);

  const showToast = (title: string, desc: string) => {
    setToastMessage({ title, desc });
    setTimeout(() => {
      setToastMessage(null);
    }, 4500);
  };

  // Switch active row in drawer
  const handleSelectRow = (rowNum: number) => {
    setActiveSelectedRow(rowNum);
    const item = findings[rowNum];
    if (item) {
      setInputVal(item.resolvedValue || item.defaultVal || '');
      setAuditNote(item.auditNote || '');
    }
  };

  // Validation logic for active drawer input
  const validationState = useMemo(() => {
    if (!inputVal || !inputVal.trim()) {
      return {
        isValid: false,
        msg: 'Field cannot remain empty for evaluation.',
        status: 'empty',
      };
    }

    if (
      activeFinding.rule === 'RULE-R6-MISSING-APAAR' ||
      activeFinding.rule === 'RULE-R5-BATCH-DUPLICATE'
    ) {
      const cleanDigits = inputVal.replace(/[^0-9]/g, '');
      if (inputVal === '8129-3321-9011') {
        return {
          isValid: false,
          msg: 'Collision! Matches duplicate row #108 in this batch.',
          status: 'error',
        };
      }
      if (cleanDigits.length === 12) {
        return {
          isValid: true,
          msg: 'Valid 12-digit syntax detected. Ready for automated check.',
          status: 'valid',
        };
      }
      return {
        isValid: false,
        msg: `Need 12 digits (currently ${cleanDigits.length}).`,
        status: 'review',
      };
    }

    // Default valid for other adjustments
    return {
      isValid: true,
      msg: 'Input syntax satisfied. Re-validation enabled.',
      status: 'valid',
    };
  }, [inputVal, activeFinding]);

  // Apply in-place correction
  const handleApplyCorrection = () => {
    setFindings((prev) => {
      const updated = { ...prev };
      const current = updated[activeSelectedRow];
      if (current) {
        updated[activeSelectedRow] = {
          ...current,
          severity: 'RESOLVED',
          resolvedValue: inputVal,
          auditNote: auditNote,
        };
      }
      return updated;
    });

    showToast(
      `Row #${activeSelectedRow} Rectified`,
      `${activeFinding.studentId}: Discrepancy cleared and signed into audit trail.`
    );
  };

  // Counts
  const blockingCount = useMemo(() => {
    return Object.values(findings).filter((f) => f.severity === 'BLOCKING').length;
  }, [findings]);

  const warningCount = useMemo(() => {
    return Object.values(findings).filter((f) => f.severity === 'WARNING').length;
  }, [findings]);

  const resolvedCount = useMemo(() => {
    return Object.values(findings).filter((f) => f.severity === 'RESOLVED').length;
  }, [findings]);

  // Filtered rows for table
  const displayedFindings = useMemo(() => {
    let list = Object.values(findings);

    if (severityFilter !== 'ALL') {
      list = list.filter((item) => item.severity === severityFilter);
    }

    if (rulePrefixFilter !== 'ALL') {
      if (rulePrefixFilter === 'MISSING') list = list.filter((i) => i.rule.includes('MISSING-APAAR'));
      if (rulePrefixFilter === 'DUPLICATES') list = list.filter((i) => i.rule.includes('BATCH-DUPLICATE'));
      if (rulePrefixFilter === 'QUOTA') list = list.filter((i) => i.rule.includes('INTAKE-EXCEEDED'));
      if (rulePrefixFilter === 'CATEGORY') list = list.filter((i) => i.rule.includes('SEAT-INCONSISTENCY'));
      if (rulePrefixFilter === 'GATEWAY') list = list.filter((i) => i.rule.includes('SYNTAX-SUSPECT'));
    }

    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      list = list.filter(
        (i) =>
          i.studentId.toLowerCase().includes(q) ||
          i.name.toLowerCase().includes(q) ||
          i.rule.toLowerCase().includes(q) ||
          String(i.row).includes(q)
      );
    }

    return list;
  }, [findings, severityFilter, rulePrefixFilter, searchTerm]);

  // Export Findings CSV
  const handleExportCSV = () => {
    const headers = ['Row_Number', 'Student_ID', 'Student_Name', 'Programme', 'Rule', 'Severity', 'Explanation'];
    const rows = Object.values(findings).map((f) => [
      f.row,
      `"${f.studentId}"`,
      `"${f.name}"`,
      `"${f.branch}"`,
      `"${f.rule}"`,
      `"${f.severity}"`,
      `"${f.explanation}"`,
    ]);
    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', 'BATCH_2025_NITTRICHY_004_Findings.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast('Export Initiated', 'Downloaded Findings CSV for Batch #BATCH-2025-NITTRICHY-004.');
  };

  const handleFullReeval = () => {
    showToast('Rules Engine Triggered', 'Re-evaluating 1,420 rows against NAD-AICTE v2.4 rule specifications...');
  };

  return (
    <div className="bg-surface-canvas font-body-md text-on-surface antialiased min-h-screen flex flex-col relative selection:bg-secondary/20">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-24 right-8 bg-primary text-on-primary px-space-md py-space-sm rounded-lg shadow-xl flex items-center gap-space-sm z-50 border border-secondary/40 animate-bounce">
          <span className="material-symbols-outlined text-status-verified text-[22px]">
            check_circle
          </span>
          <div className="flex flex-col">
            <span className="font-headline-sm text-headline-sm">{toastMessage.title}</span>
            <span className="font-label-sm text-label-sm text-primary-fixed">{toastMessage.desc}</span>
          </div>
          <button
            onClick={() => setToastMessage(null)}
            className="ml-space-md text-primary-fixed hover:text-on-primary cursor-pointer"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
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
              onClick={() => showToast('Audit Alert', `${blockingCount} blocking findings require rectification.`)}
              className="relative p-space-xs text-on-surface-variant hover:text-primary transition-colors cursor-pointer"
            >
              <span className="material-symbols-outlined text-[20px]">notifications</span>
              {blockingCount > 0 && (
                <span className="absolute top-1 right-1 w-2 h-2 bg-status-error rounded-full animate-pulse"></span>
              )}
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
            const isActive = tab.id === 'findings';
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
      <main className="w-full pt-32 bg-surface-canvas min-h-screen pb-24">
        <div className="flex flex-col w-full">
          {/* Top Sovereign Utility Sub-bar */}
          <section className="w-full bg-surface-card px-gutter-md py-space-sm shadow-sm flex flex-wrap items-center justify-between gap-space-md border-b border-border-subtle">
            <div className="flex items-center gap-space-sm flex-wrap">
              <div className="flex items-center gap-space-xs text-primary font-headline-sm text-headline-sm">
                <span className="material-symbols-outlined text-secondary">fact_check</span>
                <span>Reconciliation &amp; Explainable Findings Engine</span>
              </div>
              <span className="text-outline">/</span>
              <span className="font-code-sm text-code-sm bg-surface-subtle text-on-surface px-space-xs py-space-2xs rounded border border-border-subtle">
                BATCH-2025-NITTRICHY-004
              </span>
              <span className="font-label-sm text-label-sm px-space-xs py-space-2xs bg-status-review-surface text-status-review rounded font-semibold uppercase tracking-wider border border-status-review-border">
                Stage: Ingestion Validation
              </span>
            </div>

            <div className="flex items-center gap-space-sm">
              <span className="font-label-sm text-label-sm text-outline uppercase tracking-wider font-semibold">
                Active Run ID:
              </span>
              <span className="font-code-sm text-code-sm text-on-surface bg-surface-subtle px-space-xs py-space-2xs rounded border border-border-subtle">
                RUN-7749-EVAL
              </span>
              <button
                onClick={handleFullReeval}
                className="flex items-center gap-space-xs px-space-sm py-space-xs bg-surface-subtle text-primary hover:bg-surface-container-high rounded text-label-md font-label-md transition-colors border border-border-subtle cursor-pointer"
              >
                <span className="material-symbols-outlined text-[16px]">refresh</span>
                <span>Re-run Rules Engine</span>
              </button>
            </div>
          </section>

          {/* Main Space */}
          <div className="max-w-7xl mx-auto w-full px-gutter-md py-space-2xl flex flex-col gap-space-2xl">
            {/* Metric Cards Bento */}
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-space-lg">
              {/* Card 1 */}
              <div className="bg-surface-card rounded-xl p-space-xl shadow-sm border border-border-subtle flex flex-col justify-between hover:border-border-strong transition-all">
                <div className="flex items-center justify-between">
                  <span className="font-label-sm text-label-sm text-outline uppercase tracking-wider font-semibold">
                    Ingested Cohort
                  </span>
                  <span className="material-symbols-outlined text-outline text-[20px]">group</span>
                </div>
                <div className="mt-space-lg">
                  <div className="font-display-lg text-display-lg text-primary tracking-tight font-bold">
                    1,420
                  </div>
                  <div className="font-body-sm text-body-sm text-on-surface-variant mt-space-xs flex items-center gap-space-xs">
                    <span className="w-2 h-2 rounded-full bg-secondary"></span>
                    <span>UG &amp; PG Admissions</span>
                  </div>
                </div>
              </div>

              {/* Card 2 */}
              <div className="bg-surface-card rounded-xl p-space-xl shadow-sm border border-border-subtle flex flex-col justify-between hover:border-border-strong transition-all">
                <div className="flex items-center justify-between">
                  <span className="font-label-sm text-label-sm text-outline uppercase tracking-wider font-semibold">
                    Total Flagged
                  </span>
                  <span className="material-symbols-outlined text-status-review text-[20px]">
                    report_problem
                  </span>
                </div>
                <div className="mt-space-lg">
                  <div className="flex items-baseline gap-space-sm">
                    <span className="font-display-lg text-display-lg text-on-surface tracking-tight font-bold">
                      28
                    </span>
                    <span className="font-label-sm text-label-sm text-status-error font-semibold px-2 py-0.5 rounded bg-status-error-surface border border-status-error-border">
                      {blockingCount} Blocking
                    </span>
                  </div>
                  <div className="font-body-sm text-body-sm text-outline mt-space-xs">
                    {warningCount} Review Warnings
                  </div>
                </div>
              </div>

              {/* Card 3 */}
              <div className="bg-surface-card rounded-xl p-space-xl shadow-sm border border-border-subtle flex flex-col justify-between hover:border-border-strong transition-all">
                <div className="flex items-center justify-between">
                  <span className="font-label-sm text-label-sm text-outline uppercase tracking-wider font-semibold">
                    Completeness
                  </span>
                  <span className="font-headline-sm text-headline-sm text-status-verified font-bold">
                    98.2%
                  </span>
                </div>
                <div className="mt-space-lg">
                  <div className="w-full bg-surface-subtle h-1.5 rounded-full overflow-hidden">
                    <div className="bg-status-verified h-full rounded-full w-[98.2%]"></div>
                  </div>
                  <span className="font-body-sm text-body-sm text-outline mt-space-sm block">
                    26 attributes missing
                  </span>
                </div>
              </div>

              {/* Card 4 */}
              <div className="bg-surface-card rounded-xl p-space-xl shadow-sm border border-border-subtle flex flex-col justify-between hover:border-border-strong transition-all">
                <div className="flex items-center justify-between">
                  <span className="font-label-sm text-label-sm text-outline uppercase tracking-wider font-semibold">
                    Syntax Validity
                  </span>
                  <span className="font-headline-sm text-headline-sm text-status-verified font-bold">
                    99.1%
                  </span>
                </div>
                <div className="mt-space-lg">
                  <div className="w-full bg-surface-subtle h-1.5 rounded-full overflow-hidden">
                    <div className="bg-secondary h-full rounded-full w-[99.1%]"></div>
                  </div>
                  <span className="font-body-sm text-body-sm text-outline mt-space-sm block">
                    13 format violations
                  </span>
                </div>
              </div>

              {/* Card 5 */}
              <div className="bg-surface-card rounded-xl p-space-xl shadow-sm border border-border-subtle flex flex-col justify-between hover:border-border-strong transition-all">
                <div className="flex items-center justify-between">
                  <span className="font-label-sm text-label-sm text-outline uppercase tracking-wider font-semibold">
                    Quota Adherence
                  </span>
                  <span className="font-headline-sm text-headline-sm text-status-review font-bold">
                    98.4%
                  </span>
                </div>
                <div className="mt-space-lg">
                  <div className="w-full bg-surface-subtle h-1.5 rounded-full overflow-hidden">
                    <div className="bg-status-review h-full rounded-full w-[98.4%]"></div>
                  </div>
                  <span className="font-body-sm text-body-sm text-outline mt-space-sm block">
                    2 branch deviations
                  </span>
                </div>
              </div>
            </div>

            {/* Filters & Search Toolbar */}
            <div className="bg-surface-card rounded-xl p-space-lg shadow-sm border border-border-subtle flex flex-col gap-space-lg">
              <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-space-lg">
                {/* Severity Pills */}
                <div className="flex items-center gap-space-xs bg-surface-subtle p-space-2xs rounded-lg overflow-x-auto border border-border-subtle">
                  <button
                    onClick={() => setSeverityFilter('ALL')}
                    className={`px-space-md py-space-xs rounded-lg font-label-md text-label-md font-semibold transition-all cursor-pointer ${
                      severityFilter === 'ALL'
                        ? 'text-primary bg-surface-card shadow-sm'
                        : 'text-on-surface-variant hover:bg-surface-card/60'
                    }`}
                  >
                    All Findings (28)
                  </button>
                  <button
                    onClick={() => setSeverityFilter('BLOCKING')}
                    className={`px-space-md py-space-xs rounded-lg font-label-md text-label-md font-semibold transition-all flex items-center gap-space-xs cursor-pointer ${
                      severityFilter === 'BLOCKING'
                        ? 'text-status-error bg-surface-card shadow-sm'
                        : 'text-status-error hover:bg-surface-card/60'
                    }`}
                  >
                    <span className="w-2 h-2 rounded-full bg-status-error"></span>
                    <span>Blocking Error ({blockingCount})</span>
                  </button>
                  <button
                    onClick={() => setSeverityFilter('WARNING')}
                    className={`px-space-md py-space-xs rounded-lg font-label-md text-label-md font-semibold transition-all flex items-center gap-space-xs cursor-pointer ${
                      severityFilter === 'WARNING'
                        ? 'text-status-review bg-surface-card shadow-sm'
                        : 'text-status-review hover:bg-surface-card/60'
                    }`}
                  >
                    <span className="w-2 h-2 rounded-full bg-status-review"></span>
                    <span>Review Warning ({warningCount})</span>
                  </button>
                  <button
                    onClick={() => setSeverityFilter('RESOLVED')}
                    className={`px-space-md py-space-xs rounded-lg font-label-md text-label-md font-semibold transition-all flex items-center gap-space-xs cursor-pointer ${
                      severityFilter === 'RESOLVED'
                        ? 'text-status-verified bg-surface-card shadow-sm'
                        : 'text-status-verified hover:bg-surface-card/60'
                    }`}
                  >
                    <span className="w-2 h-2 rounded-full bg-status-verified"></span>
                    <span>Resolved ({resolvedCount})</span>
                  </button>
                </div>

                {/* Search Bar */}
                <div className="flex items-center gap-space-md flex-1 max-w-xl">
                  <div className="relative w-full">
                    <span className="material-symbols-outlined absolute left-3 top-2.5 text-outline text-[18px]">
                      search
                    </span>
                    <input
                      type="text"
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      placeholder="Search by Student ID, APAAR ID, or Row..."
                      className="w-full pl-9 pr-12 py-space-xs bg-surface-subtle border border-border-subtle rounded-lg text-body-md font-body-md text-on-surface focus:outline-none focus:ring-1 focus:ring-secondary placeholder-outline transition-colors focus:bg-surface-card"
                    />
                    <span className="font-code-sm text-code-sm text-outline absolute right-3 top-2 px-1.5 py-0.5 bg-surface-card rounded border border-border-subtle text-[10px]">
                      Ctrl+F
                    </span>
                  </div>
                </div>
              </div>

              {/* Rule Filter Pills */}
              <div className="flex items-center gap-space-sm flex-wrap border-t border-border-subtle pt-space-md">
                <span className="font-label-sm text-label-sm text-outline uppercase font-semibold mr-space-xs">
                  Rule Filter:
                </span>
                {[
                  { id: 'MISSING', label: 'Missing APAAR (8)' },
                  { id: 'DUPLICATES', label: 'Batch Duplicates (3)' },
                  { id: 'QUOTA', label: 'Intake Quota Ceiling (2)' },
                  { id: 'CATEGORY', label: 'Category Inconsistency (9)' },
                  { id: 'GATEWAY', label: 'Gateway Lifecycle (6)' },
                ].map((rf) => (
                  <button
                    key={rf.id}
                    onClick={() =>
                      setRulePrefixFilter((prev) => (prev === rf.id ? 'ALL' : rf.id))
                    }
                    className={`px-space-sm py-space-xs rounded-full font-code-sm text-code-sm transition-colors cursor-pointer border ${
                      rulePrefixFilter === rf.id
                        ? 'bg-primary text-white border-primary'
                        : 'bg-surface-subtle text-on-surface-variant border-border-subtle hover:text-primary hover:bg-surface-container-high'
                    }`}
                  >
                    {rf.label}
                  </button>
                ))}
                <button
                  onClick={() => {
                    setSeverityFilter('ALL');
                    setRulePrefixFilter('ALL');
                    setSearchTerm('');
                  }}
                  className="font-label-sm text-label-sm text-secondary hover:underline ml-auto font-medium cursor-pointer"
                >
                  Reset Filters
                </button>
              </div>
            </div>

            {/* Split Workspace: Left Findings Table + Right Rectification Drawer */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-space-xl items-start">
              {/* Left Column (8 Cols) */}
              <div className="lg:col-span-8 flex flex-col gap-space-xl">
                <div className="bg-surface-card rounded-xl shadow-sm border border-border-subtle overflow-hidden flex flex-col">
                  <div className="px-space-xl py-space-md bg-surface-card border-b border-border-subtle flex items-center justify-between">
                    <div className="flex items-center gap-space-md">
                      <span className="font-headline-sm text-headline-sm text-primary font-bold">
                        Explainable Validation Discrepancies
                      </span>
                      <span className="font-label-sm text-label-sm bg-surface-subtle text-on-surface-variant px-space-sm py-0.5 rounded-full font-medium border border-border-subtle">
                        {displayedFindings.length} Visible
                      </span>
                    </div>
                    <div className="flex items-center gap-space-xs text-outline font-label-sm text-label-sm">
                      <span className="material-symbols-outlined text-[16px] text-status-verified">
                        verified_user
                      </span>
                      <span>Deterministic Hierarchy</span>
                    </div>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left">
                      <thead>
                        <tr className="bg-surface-subtle/50 text-outline font-label-sm text-label-sm uppercase tracking-wider border-b border-border-subtle">
                          <th className="py-space-md px-space-xl w-16">Row</th>
                          <th className="py-space-md px-space-lg">Student Identifier</th>
                          <th className="py-space-md px-space-lg">Rule &amp; Severity</th>
                          <th className="py-space-md px-space-lg">Discrepancy Details</th>
                          <th className="py-space-md px-space-lg text-right">Operational Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border-subtle font-body-sm text-body-sm">
                        {displayedFindings.length === 0 ? (
                          <tr>
                            <td colSpan={5} className="py-8 text-center text-outline">
                              No discrepancies match the active filters.
                            </td>
                          </tr>
                        ) : (
                          displayedFindings.map((item) => {
                            const isSelected = item.row === activeSelectedRow;
                            return (
                              <tr
                                key={item.row}
                                onClick={() => handleSelectRow(item.row)}
                                className={`transition-colors cursor-pointer ${
                                  isSelected
                                    ? 'ring-2 ring-secondary bg-surface-subtle'
                                    : item.severity === 'RESOLVED'
                                    ? 'bg-status-verified-surface/30 hover:bg-status-verified-surface/50'
                                    : item.severity === 'BLOCKING'
                                    ? 'bg-status-error-surface/10 hover:bg-status-error-surface/20'
                                    : 'hover:bg-surface-subtle/30'
                                }`}
                              >
                                <td className="py-space-lg px-space-xl font-code-sm text-code-sm font-semibold text-outline">
                                  #{item.row}
                                </td>
                                <td className="py-space-lg px-space-lg">
                                  <div className="flex flex-col">
                                    <span className="font-code-sm text-code-sm font-bold text-primary">
                                      {item.studentId}
                                    </span>
                                    <span className="font-body-sm text-body-sm text-outline mt-0.5">
                                      {item.branch}
                                    </span>
                                  </div>
                                </td>
                                <td className="py-space-lg px-space-lg">
                                  <div className="flex flex-col gap-space-xs items-start">
                                    {item.severity === 'RESOLVED' && (
                                      <span className="inline-flex items-center gap-1 font-label-sm text-label-sm px-space-xs py-0.5 rounded-md bg-status-verified-surface text-status-verified font-bold border border-status-verified-border">
                                        <span className="material-symbols-outlined text-[13px]">
                                          check_circle
                                        </span>
                                        Resolved
                                      </span>
                                    )}
                                    {item.severity === 'BLOCKING' && (
                                      <span className="inline-flex items-center gap-1 font-label-sm text-label-sm px-space-xs py-0.5 rounded-md bg-status-error-surface text-status-error font-semibold border border-status-error-border">
                                        <span className="material-symbols-outlined text-[13px]">
                                          cancel
                                        </span>
                                        Blocking
                                      </span>
                                    )}
                                    {item.severity === 'WARNING' && (
                                      <span className="inline-flex items-center gap-1 font-label-sm text-label-sm px-space-xs py-0.5 rounded-md bg-status-review-surface text-status-review font-semibold border border-status-review-border">
                                        <span className="material-symbols-outlined text-[13px]">
                                          warning
                                        </span>
                                        Warning
                                      </span>
                                    )}
                                    <span className="font-code-sm text-code-sm text-on-surface-variant">
                                      {item.rule}
                                    </span>
                                  </div>
                                </td>
                                <td className="py-space-lg px-space-lg max-w-xs">
                                  <div className="flex flex-col gap-0.5">
                                    <span className="font-code-sm text-code-sm font-semibold text-primary">
                                      {item.field}
                                    </span>
                                    <span className="text-on-surface-variant font-body-sm text-body-sm">
                                      {item.resolvedValue ? (
                                        <span className="text-status-verified font-mono font-semibold">
                                          ✓ Corrected: {item.resolvedValue}
                                        </span>
                                      ) : (
                                        item.explanation
                                      )}
                                    </span>
                                  </div>
                                </td>
                                <td className="py-space-lg px-space-lg text-right">
                                  {item.severity === 'RESOLVED' ? (
                                    <span className="text-status-verified text-xs font-semibold inline-flex items-center gap-1">
                                      <span className="material-symbols-outlined text-[16px]">
                                        verified
                                      </span>
                                      Audited
                                    </span>
                                  ) : (
                                    <button
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        handleSelectRow(item.row);
                                      }}
                                      className={`px-space-md py-space-xs rounded-lg text-label-md font-label-md transition-colors shadow-sm inline-flex items-center gap-1.5 cursor-pointer ${
                                        item.severity === 'BLOCKING'
                                          ? 'bg-primary text-on-primary hover:bg-navy-deep'
                                          : 'bg-surface-subtle text-primary hover:bg-surface-container-high border border-border-subtle'
                                      }`}
                                    >
                                      <span className="material-symbols-outlined text-[15px]">
                                        edit
                                      </span>
                                      <span>
                                        {item.severity === 'BLOCKING' ? 'Fix Field' : 'Verify'}
                                      </span>
                                    </button>
                                  )}
                                </td>
                              </tr>
                            );
                          })
                        )}
                      </tbody>
                    </table>
                  </div>

                  <div className="px-space-xl py-space-md bg-surface-card flex items-center justify-between text-body-sm font-body-sm text-outline border-t border-border-subtle">
                    <span>
                      Showing findings 1-{displayedFindings.length} of 28
                    </span>
                    <div className="flex items-center gap-space-xs">
                      <span className="px-space-md py-space-xs bg-primary text-on-primary rounded-lg font-bold text-label-sm">
                        1
                      </span>
                    </div>
                  </div>
                </div>

                {/* National Academic Rule Architecture Cards */}
                <div className="bg-surface-card rounded-xl p-space-xl shadow-sm border border-border-subtle">
                  <div className="flex items-center justify-between mb-space-md">
                    <span className="font-headline-sm text-headline-sm text-primary font-bold flex items-center gap-space-xs">
                      <span className="material-symbols-outlined text-secondary text-[20px]">
                        menu_book
                      </span>
                      <span>National Academic Rule Architecture</span>
                    </span>
                    <span className="font-label-sm text-label-sm text-outline font-code-sm">
                      v2.4 Spec
                    </span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-space-md">
                    <div className="p-space-md rounded-lg border border-border-subtle bg-surface-subtle/30">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-code-sm text-code-sm font-bold text-primary">
                          RULE-R6 / R5
                        </span>
                        <span className="font-label-sm text-label-sm text-status-error font-bold">
                          Blocking
                        </span>
                      </div>
                      <p className="text-on-surface-variant font-body-sm text-body-sm">
                        Identity verification requirement. Valid 12-digit verifiable APAAR required.
                      </p>
                    </div>

                    <div className="p-space-md rounded-lg border border-border-subtle bg-surface-subtle/30">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-code-sm text-code-sm font-bold text-primary">
                          RULE-R7
                        </span>
                        <span className="font-label-sm text-label-sm text-status-error font-bold">
                          Blocking
                        </span>
                      </div>
                      <p className="text-on-surface-variant font-body-sm text-body-sm">
                        Sanction Limits. Enrolment exceeding AICTE approved intake ceiling blocked.
                      </p>
                    </div>

                    <div className="p-space-md rounded-lg border border-border-subtle bg-surface-subtle/30">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-code-sm text-code-sm font-bold text-primary">
                          RULE-R4 / R8
                        </span>
                        <span className="font-label-sm text-label-sm text-status-review font-bold">
                          Warning
                        </span>
                      </div>
                      <p className="text-on-surface-variant font-body-sm text-body-sm">
                        Lapses &amp; Gateway retries. Permits provisional import subject to 15-day affidavit.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right Column (4 Cols): Rectification Drawer */}
              <div className="lg:col-span-4 flex flex-col gap-space-md">
                <div className="bg-surface-card rounded-xl shadow-sm border border-border-subtle overflow-hidden sticky top-36">
                  <div className="p-space-xl border-b border-border-subtle flex items-center justify-between">
                    <div className="flex items-center gap-space-sm">
                      <div className="w-9 h-9 rounded-lg bg-surface-subtle flex items-center justify-center text-primary">
                        <span className="material-symbols-outlined text-[20px]">tune</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="font-headline-sm text-headline-sm text-primary font-bold">
                          Discrepancy Rectification
                        </span>
                        <span className="font-body-sm text-body-sm text-outline">
                          Targeting: Row #{activeFinding.row}
                        </span>
                      </div>
                    </div>
                    <span className="font-code-sm text-code-sm bg-surface-subtle text-on-surface-variant px-space-xs py-1 rounded border border-border-subtle">
                      INSPECTION
                    </span>
                  </div>

                  <div className="p-space-xl flex flex-col gap-space-lg">
                    {/* Student Metadata Card */}
                    <div className="p-space-md bg-surface-subtle/60 rounded-xl border border-border-subtle flex flex-col gap-space-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-label-sm text-label-sm text-outline uppercase font-semibold">
                          Student
                        </span>
                        <span className="font-code-sm text-code-sm font-bold text-primary">
                          {activeFinding.studentId}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="font-label-sm text-label-sm text-outline uppercase font-semibold">
                          Name
                        </span>
                        <span className="font-body-md text-body-md text-on-surface font-semibold">
                          {activeFinding.name}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="font-label-sm text-label-sm text-outline uppercase font-semibold">
                          Trigger
                        </span>
                        <span className="font-code-sm text-code-sm text-status-error font-semibold">
                          {activeFinding.rule}
                        </span>
                      </div>
                    </div>

                    {/* Root-cause box */}
                    <div className="bg-status-error-surface/40 p-space-md rounded-xl border border-status-error-border flex flex-col gap-space-xs">
                      <div className="flex items-center gap-1.5 text-status-error font-label-md text-label-md font-bold">
                        <span className="material-symbols-outlined text-[16px]">info</span>
                        <span>Root-Cause Explanation:</span>
                      </div>
                      <p className="font-body-sm text-body-sm text-on-surface">
                        {activeFinding.explanation}
                      </p>
                      <div className="bg-surface-card p-space-sm rounded-lg border border-border-subtle mt-1 text-label-sm font-label-sm">
                        <span className="text-outline block">Recommended Solution:</span>
                        <span className="text-primary font-medium mt-0.5 block">
                          {activeFinding.suggestedAction}
                        </span>
                      </div>
                    </div>

                    {/* Rectify Input Form */}
                    <div className="flex flex-col gap-space-xs">
                      <label
                        className="font-label-md text-label-md text-on-surface font-semibold flex items-center justify-between"
                        htmlFor="inputFieldVal"
                      >
                        <span>{activeFinding.inputLabel}</span>
                        <span className="font-code-sm text-code-sm text-outline font-normal">
                          {activeFinding.inputHint}
                        </span>
                      </label>
                      <div className="relative">
                        <input
                          id="inputFieldVal"
                          type="text"
                          value={inputVal}
                          onChange={(e) => setInputVal(e.target.value)}
                          placeholder={activeFinding.placeholder}
                          maxLength={32}
                          className="w-full px-space-md py-space-sm bg-surface-card border border-border-strong rounded-lg font-code-sm text-code-sm text-primary tracking-wider focus:outline-none focus:ring-2 focus:ring-secondary text-base"
                        />
                        <div className="absolute right-3 top-3 flex items-center">
                          {validationState.status === 'valid' && (
                            <span className="material-symbols-outlined text-status-verified text-[18px]">
                              check_circle
                            </span>
                          )}
                          {validationState.status === 'error' && (
                            <span className="material-symbols-outlined text-status-error text-[18px]">
                              error
                            </span>
                          )}
                          {validationState.status === 'review' && (
                            <span className="material-symbols-outlined text-status-review text-[18px]">
                              pending
                            </span>
                          )}
                          {validationState.status === 'empty' && (
                            <span className="material-symbols-outlined text-outline text-[18px]">
                              edit_note
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Live Feedback Message */}
                      <div
                        className={`p-space-xs rounded text-label-sm font-label-sm flex items-center gap-space-xs ${
                          validationState.status === 'valid'
                            ? 'bg-status-verified-surface text-status-verified font-semibold'
                            : validationState.status === 'error'
                            ? 'bg-status-error-surface text-status-error font-semibold'
                            : validationState.status === 'review'
                            ? 'bg-status-review-surface text-status-review'
                            : 'bg-surface-subtle text-outline'
                        }`}
                      >
                        <span className="material-symbols-outlined text-[14px]">checklist</span>
                        <span>{validationState.msg}</span>
                      </div>
                    </div>

                    {/* Audit Trail Justification */}
                    <div className="flex flex-col gap-space-xs">
                      <label
                        className="font-label-md text-label-md text-on-surface-variant font-semibold"
                        htmlFor="auditNote"
                      >
                        Audit Trail Justification
                      </label>
                      <textarea
                        id="auditNote"
                        rows={2}
                        value={auditNote}
                        onChange={(e) => setAuditNote(e.target.value)}
                        placeholder="Reference student DigiLocker verified affidavit or dispatch number..."
                        className="w-full p-space-sm bg-surface-card border border-border-subtle rounded-lg text-body-sm font-body-sm text-on-surface focus:outline-none focus:ring-1 focus:ring-secondary placeholder-outline"
                      />
                    </div>

                    {/* Drawer Action Buttons */}
                    <div className="flex flex-col gap-space-sm pt-space-xs">
                      <button
                        onClick={handleApplyCorrection}
                        disabled={!validationState.isValid}
                        className="w-full py-space-sm px-space-md bg-primary text-on-primary rounded-lg font-title-md text-title-md font-semibold hover:bg-navy-deep disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm flex items-center justify-center gap-space-xs cursor-pointer"
                      >
                        <span className="material-symbols-outlined text-[18px]">
                          check_circle
                        </span>
                        <span>Save &amp; Re-evaluate Finding</span>
                      </button>

                      <button
                        onClick={() =>
                          showToast(
                            'Escalated to Registrar Desk',
                            `Ticket #REG-${activeSelectedRow}-DISPATCH dispatched with encrypted row payload.`
                          )
                        }
                        className="w-full py-space-xs px-space-md bg-surface-subtle text-primary hover:bg-surface-container-high rounded-lg font-label-md text-label-md transition-colors flex items-center justify-center gap-space-xs border border-border-subtle cursor-pointer"
                      >
                        <span className="material-symbols-outlined text-[16px]">
                          forward_to_inbox
                        </span>
                        <span>Escalate to Registrar Desk</span>
                      </button>
                    </div>

                    <div className="pt-space-sm border-t border-border-subtle flex items-center justify-between text-label-sm font-label-sm text-outline">
                      <span>Auditor: NIT-TRICHY-ADM</span>
                      <span>SHA256 Signed</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* BOTTOM STICKY ADMINISTRATIVE ACTION FOOTER */}
      <footer className="sticky bottom-0 left-0 right-0 z-30 bg-surface-card p-space-md shadow-[0_-4px_12px_rgba(0,0,0,0.06)] border-t border-border-subtle">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-space-md">
          {/* Left Warning Callout */}
          <div className="flex items-center gap-space-sm">
            <div className="w-9 h-9 rounded bg-status-error-surface text-status-error flex items-center justify-center flex-shrink-0">
              <span className="material-symbols-outlined text-[22px]">gavel</span>
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-space-xs">
                <span className="font-title-md text-title-md text-primary font-bold">
                  {blockingCount} Blocking Errors Outstanding
                </span>
                <span className="font-label-sm text-label-sm px-1.5 py-0.5 rounded bg-status-error-surface text-status-error font-semibold">
                  Strict Regulatory Block
                </span>
              </div>
              <span className="font-body-sm text-body-sm text-on-surface-variant">
                All blocking errors must be resolved or justified under AICTE Sovereign Academic Standard before final ingestion sync.
              </span>
            </div>
          </div>

          {/* Right Action CTAs */}
          <div className="flex items-center gap-space-sm w-full md:w-auto justify-end flex-wrap">
            <button
              onClick={handleExportCSV}
              className="px-space-md py-space-sm bg-surface-subtle text-primary hover:bg-surface-container-high rounded font-title-md text-title-md font-semibold transition-colors flex items-center gap-space-xs border border-border-subtle cursor-pointer"
            >
              <span className="material-symbols-outlined text-[18px]">file_download</span>
              <span>Export Findings CSV</span>
            </button>

            <button
              onClick={handleFullReeval}
              className="px-space-md py-space-sm bg-surface-subtle text-primary hover:bg-surface-container-high rounded font-title-md text-title-md font-semibold transition-colors flex items-center gap-space-xs border border-border-subtle cursor-pointer"
            >
              <span className="material-symbols-outlined text-[18px]">rule</span>
              <span>Run Revalidation Checks</span>
            </button>

            <button
              disabled={blockingCount > 0}
              onClick={() => {
                showToast(
                  'Payload Synchronized',
                  'Batch #BATCH-2025-NITTRICHY-004 submitted to AICTE Central Sovereign Depository.'
                );
              }}
              title={
                blockingCount > 0
                  ? `Resolve ${blockingCount} blocking errors to unlock submission`
                  : 'Ready to submit to AICTE Repository'
              }
              className={`px-space-lg py-space-sm rounded font-headline-sm text-headline-sm font-semibold transition-all flex items-center gap-space-xs shadow-sm cursor-pointer ${
                blockingCount > 0
                  ? 'bg-primary text-on-primary opacity-40 cursor-not-allowed'
                  : 'bg-status-verified text-white hover:bg-status-verified/90'
              }`}
            >
              <span className="material-symbols-outlined text-[20px]">cloud_upload</span>
              <span>Submit Batch to AICTE Repository</span>
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default DataQualityFindingsPage;
