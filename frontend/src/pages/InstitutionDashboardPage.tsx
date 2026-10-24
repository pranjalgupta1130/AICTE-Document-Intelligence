import React, { useState } from 'react';
import { AuthSession } from '../types/auth';

interface InstitutionDashboardPageProps {
  session?: AuthSession | null;
  onLogout?: () => void;
  onNavigateTab?: (tab: string) => void;
}

interface DepartmentRecord {
  id: string;
  code: string;
  name: string;
  sanctioned: number;
  supernumerary: number;
  actualRegular: number;
  actualSuper: number;
  totalEnrolled: number;
  utilization: string;
  hasViolation: boolean;
  excessCount?: number;
  statusText: string;
}

const DEPARTMENT_DATA: DepartmentRecord[] = [
  {
    id: 'dept-cse',
    code: 'BTECH-CSE-01',
    name: 'Computer Science & Engineering',
    sanctioned: 180,
    supernumerary: 18,
    actualRegular: 180,
    actualSuper: 16,
    totalEnrolled: 196,
    utilization: '98.9%',
    hasViolation: false,
    statusText: 'Within Quota',
  },
  {
    id: 'dept-ece',
    code: 'BTECH-ECE-02',
    name: 'Electronics & Communication Engineering',
    sanctioned: 120,
    supernumerary: 12,
    actualRegular: 122,
    actualSuper: 11,
    totalEnrolled: 133,
    utilization: '100.7%',
    hasViolation: true,
    excessCount: 2,
    statusText: 'Exceeded (+2)',
  },
  {
    id: 'dept-mec',
    code: 'BTECH-MEC-03',
    name: 'Mechanical Engineering',
    sanctioned: 120,
    supernumerary: 12,
    actualRegular: 112,
    actualSuper: 8,
    totalEnrolled: 120,
    utilization: '90.9%',
    hasViolation: false,
    statusText: 'Within Quota',
  },
  {
    id: 'dept-eee',
    code: 'BTECH-EEE-04',
    name: 'Electrical & Electronics Engineering',
    sanctioned: 90,
    supernumerary: 9,
    actualRegular: 90,
    actualSuper: 9,
    totalEnrolled: 99,
    utilization: '100.0%',
    hasViolation: false,
    statusText: 'At Capacity',
  },
];

export const InstitutionDashboardPage: React.FC<InstitutionDashboardPageProps> = ({
  session,
  onLogout,
  onNavigateTab,
}) => {
  const [selectedAY, setSelectedAY] = useState<string>('2025-2026');
  const [selectedLevel, setSelectedLevel] = useState<string>('UG');
  const [selectedBatch, setSelectedBatch] = useState<string>('2025-04B');
  const [showUploadModal, setShowUploadModal] = useState<boolean>(false);
  const [showDetailModal, setShowDetailModal] = useState<DepartmentRecord | null>(null);
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Upload simulation state
  const [uploadFileName, setUploadFileName] = useState<string | null>(null);
  const [isProcessingUpload, setIsProcessingUpload] = useState<boolean>(false);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 3500);
  };

  const handleExportQualityReport = () => {
    setIsExporting(true);
    showToast('Compiling Institutional Quality & Compliance Report (PDF/A)...');
    setTimeout(() => {
      setIsExporting(false);
      showToast('Quality Report compiled: NIT_Trichy_Quality_Report_2025-26.pdf');
    }, 1400);
  };

  const handleSimulateUpload = () => {
    if (!uploadFileName) {
      showToast('Please select a CSV or XLSX file to ingest');
      return;
    }
    setIsProcessingUpload(true);
    setTimeout(() => {
      setIsProcessingUpload(false);
      setShowUploadModal(false);
      setUploadFileName(null);
      showToast(`Batch ingested successfully: 142 records validated against AICTE APH 2025-26 rules.`);
    }, 1800);
  };

  return (
    <div className="bg-surface-canvas font-body-md text-on-surface antialiased min-h-screen flex flex-col relative selection:bg-secondary/20">
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
                defaultValue={session?.roleTitle || 'Institution Admin'}
                className="font-label-md text-label-md bg-surface-card border border-border-strong text-primary rounded-lg px-space-sm py-space-xs focus:ring-1 focus:ring-secondary focus:outline-none cursor-pointer"
              >
                <option value="Institution Admin">Institution Admin</option>
                <option value="Institution Operator">Institution Operator</option>
                <option value="AICTE Reviewer">AICTE Reviewer</option>
              </select>
            </div>

            <button
              aria-label="Notifications"
              onClick={() => showToast('Intake Quota Variance alert pending resolution on ECE department.')}
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
            const isActive = tab.id === 'dashboard';
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

      {/* MAIN CONTENT WORKSPACE */}
      <main className="w-full pt-32 bg-surface-canvas min-h-screen">
        <div className="flex flex-col w-full">
          {/* Administrative Action Bar & Scope Filter */}
          <div className="bg-surface-card shadow-sm px-gutter-md py-space-md mb-space-lg border-b border-border-subtle">
            <div className="max-w-[1440px] mx-auto flex flex-col xl:flex-row xl:items-center justify-between gap-space-md">
              {/* Institutional Contextual Hierarchy */}
              <div className="flex flex-col">
                <div className="flex items-center gap-space-xs text-outline">
                  <span className="font-code-sm text-code-sm uppercase tracking-wider text-secondary font-semibold">
                    Institutional Intake Monitor
                  </span>
                  <span className="text-[10px]">•</span>
                  <span className="font-code-sm text-code-sm">
                    AICTE Handbook 2025-26 Standard Compliance
                  </span>
                </div>
                <div className="flex items-baseline gap-space-sm mt-space-2xs">
                  <h1 className="font-headline-lg text-headline-lg text-primary tracking-tight font-bold">
                    National Institute of Technology, Trichy
                  </h1>
                  <span className="font-code-sm text-code-sm px-space-xs py-space-2xs bg-surface-container text-on-surface-variant rounded font-semibold">
                    PID: {session?.instCode || 'AICTE-1-49281'}
                  </span>
                </div>
              </div>

              {/* Quick Filter & Action Ribbon */}
              <div className="flex flex-wrap items-center gap-space-sm">
                <div className="flex items-center gap-space-xs bg-surface-subtle px-space-sm py-space-xs rounded-lg shadow-sm border border-border-subtle">
                  <span className="material-symbols-outlined text-outline text-[18px]">
                    calendar_month
                  </span>
                  <span className="font-label-sm text-label-sm text-outline uppercase font-semibold">
                    AY
                  </span>
                  <select
                    value={selectedAY}
                    onChange={(e) => {
                      setSelectedAY(e.target.value);
                      showToast(`Academic Year switched to ${e.target.value}`);
                    }}
                    className="font-label-md text-label-md bg-transparent text-primary font-semibold focus:outline-none cursor-pointer"
                  >
                    <option value="2025-2026">2025-2026</option>
                    <option value="2024-2025">2024-2025 (Archived)</option>
                    <option value="2023-2024">2023-2024 (Archived)</option>
                  </select>
                </div>

                <div className="flex items-center gap-space-xs bg-surface-subtle px-space-sm py-space-xs rounded-lg shadow-sm border border-border-subtle">
                  <span className="material-symbols-outlined text-outline text-[18px]">
                    school
                  </span>
                  <select
                    value={selectedLevel}
                    onChange={(e) => {
                      setSelectedLevel(e.target.value);
                      showToast(`Level filtered: ${e.target.value}`);
                    }}
                    className="font-label-md text-label-md bg-transparent text-primary font-semibold focus:outline-none cursor-pointer"
                  >
                    <option value="UG">Undergraduate (B.Tech / B.E.)</option>
                    <option value="PG">Postgraduate (M.Tech / M.Arch)</option>
                    <option value="PHD">Doctoral (Ph.D)</option>
                  </select>
                </div>

                <div className="flex items-center gap-space-xs bg-surface-subtle px-space-sm py-space-xs rounded-lg shadow-sm border border-border-subtle">
                  <span className="material-symbols-outlined text-outline text-[18px]">
                    inventory_2
                  </span>
                  <select
                    value={selectedBatch}
                    onChange={(e) => {
                      setSelectedBatch(e.target.value);
                      showToast(`Batch selected: ${e.target.value}`);
                    }}
                    className="font-label-md text-label-md bg-transparent text-on-surface font-semibold focus:outline-none cursor-pointer"
                  >
                    <option value="2025-04B">Batch #2025-04B (Submitted)</option>
                    <option value="2025-04A">Batch #2025-04A (Merged)</option>
                    <option value="2025-03">Batch #2025-03 (Certified)</option>
                  </select>
                </div>

                <div className="h-6 w-px bg-border-strong hidden sm:block"></div>

                <button
                  onClick={() => setShowUploadModal(true)}
                  className="px-space-md py-space-xs bg-primary text-on-primary font-label-md text-label-md rounded shadow-sm hover:bg-navy-deep transition-colors flex items-center gap-space-xs font-semibold cursor-pointer"
                >
                  <span className="material-symbols-outlined text-[16px]">cloud_upload</span>
                  <span>Upload Batch (CSV/XLSX)</span>
                </button>

                <button
                  onClick={handleExportQualityReport}
                  disabled={isExporting}
                  className="px-space-md py-space-xs bg-surface-card text-primary font-label-md text-label-md rounded shadow-sm hover:bg-surface-subtle transition-colors flex items-center gap-space-xs font-semibold cursor-pointer border border-border-subtle"
                >
                  <span
                    className={`material-symbols-outlined text-[16px] ${
                      isExporting ? 'animate-spin' : ''
                    }`}
                  >
                    {isExporting ? 'progress_activity' : 'file_download'}
                  </span>
                  <span>{isExporting ? 'Exporting...' : 'Export Quality Report'}</span>
                </button>
              </div>
            </div>
          </div>

          <div className="max-w-[1440px] w-full mx-auto px-gutter-md space-y-space-2xl pb-space-3xl pt-space-md">
            {/* KPI Operational Cards */}
            <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-space-lg">
              {/* Card 1: Total Enrolled */}
              <div className="bg-surface-card p-space-xl rounded-xl shadow-sm border border-border-subtle flex flex-col justify-between hover:shadow-md transition-shadow">
                <div>
                  <div className="flex items-center justify-between mb-space-sm">
                    <span className="font-label-sm text-label-sm text-outline uppercase tracking-wider font-semibold">
                      Total Enrolled Students
                    </span>
                    <div className="w-9 h-9 rounded-lg bg-surface-subtle flex items-center justify-center text-primary">
                      <span className="material-symbols-outlined text-[20px]">groups</span>
                    </div>
                  </div>
                  <div className="flex items-baseline gap-space-xs my-space-xs">
                    <span className="font-display-lg text-display-lg font-bold text-primary tracking-tight">
                      1,420
                    </span>
                    <span className="font-body-md text-body-md text-outline">
                      / 1,440 Approved
                    </span>
                  </div>
                </div>
                <div className="mt-space-lg pt-space-xs">
                  <div className="flex justify-between items-center mb-space-xs text-body-sm font-body-sm">
                    <span className="text-on-surface-variant">98.6% Capacity Used</span>
                    <span className="text-status-verified font-semibold">20 Available</span>
                  </div>
                  <div className="w-full bg-surface-subtle h-2 rounded-full overflow-hidden">
                    <div className="bg-secondary h-full rounded-full w-[98.6%]"></div>
                  </div>
                </div>
              </div>

              {/* Card 2: Valid APAAR Linked */}
              <div className="bg-surface-card p-space-xl rounded-xl shadow-sm border border-border-subtle flex flex-col justify-between hover:shadow-md transition-shadow">
                <div>
                  <div className="flex items-center justify-between mb-space-sm">
                    <span className="font-label-sm text-label-sm text-outline uppercase tracking-wider font-semibold">
                      APAAR Identity Linkage
                    </span>
                    <div className="w-9 h-9 rounded-lg bg-status-verified-surface flex items-center justify-center text-status-verified">
                      <span className="material-symbols-outlined text-[20px]">verified</span>
                    </div>
                  </div>
                  <div className="flex items-baseline gap-space-xs my-space-xs">
                    <span className="font-display-lg text-display-lg font-bold text-status-verified tracking-tight">
                      1,384
                    </span>
                    <span className="font-body-md text-body-md text-outline">
                      / 1,420 Verified
                    </span>
                  </div>
                </div>
                <div className="mt-space-lg pt-space-xs">
                  <div className="flex justify-between items-center mb-space-xs text-body-sm font-body-sm">
                    <span className="text-on-surface-variant">97.5% Linked</span>
                    <span className="text-status-review font-semibold">36 Pending</span>
                  </div>
                  <div className="w-full bg-surface-subtle h-2 rounded-full overflow-hidden">
                    <div className="bg-status-verified h-full rounded-full w-[97.5%]"></div>
                  </div>
                </div>
              </div>

              {/* Card 3: Verification Findings */}
              <div className="bg-surface-card p-space-xl rounded-xl shadow-sm border border-border-subtle flex flex-col justify-between hover:shadow-md transition-shadow">
                <div>
                  <div className="flex items-center justify-between mb-space-sm">
                    <span className="font-label-sm text-label-sm text-outline uppercase tracking-wider font-semibold">
                      Audit &amp; Validation Findings
                    </span>
                    <div className="w-9 h-9 rounded-lg bg-status-error-surface flex items-center justify-center text-status-error">
                      <span className="material-symbols-outlined text-[20px]">error</span>
                    </div>
                  </div>
                  <div className="flex items-baseline gap-space-xs my-space-xs">
                    <span className="font-display-lg text-display-lg font-bold text-status-error tracking-tight">
                      28
                    </span>
                    <span className="font-body-md text-body-md text-outline">
                      Flagged Records
                    </span>
                  </div>
                </div>
                <div className="mt-space-lg pt-space-xs flex items-center justify-between text-body-sm font-body-sm">
                  <span className="text-status-error font-medium flex items-center gap-space-2xs">
                    <span className="w-2 h-2 rounded-full bg-status-error"></span>
                    12 Blocking
                  </span>
                  <span className="text-status-review font-medium flex items-center gap-space-2xs">
                    <span className="w-2 h-2 rounded-full bg-status-review"></span>
                    16 Warnings
                  </span>
                </div>
              </div>

              {/* Card 4: Quality Score */}
              <div className="bg-surface-card p-space-xl rounded-xl shadow-sm border border-border-subtle flex flex-col justify-between hover:shadow-md transition-shadow">
                <div>
                  <div className="flex items-center justify-between mb-space-sm">
                    <span className="font-label-sm text-label-sm text-outline uppercase tracking-wider font-semibold">
                      Institutional Score
                    </span>
                    <span className="px-space-xs py-space-2xs bg-surface-subtle text-primary font-code-sm text-code-sm rounded font-bold border border-border-subtle">
                      Grade A+
                    </span>
                  </div>
                  <div className="flex items-baseline gap-space-xs my-space-xs">
                    <span className="font-display-lg text-display-lg font-bold text-primary tracking-tight">
                      94.2
                    </span>
                    <span className="font-body-md text-body-md text-outline">
                      / 100 Index
                    </span>
                  </div>
                </div>
                <div className="mt-space-lg pt-space-xs flex items-center justify-between text-center text-body-sm font-body-sm text-outline border-t border-border-subtle pt-space-sm">
                  <div>
                    <strong className="text-primary block font-code-sm">99%</strong>
                    Completeness
                  </div>
                  <div>
                    <strong className="text-primary block font-code-sm">96%</strong>
                    Integrity
                  </div>
                  <div>
                    <strong className="text-primary block font-code-sm">98%</strong>
                    Accuracy
                  </div>
                </div>
              </div>
            </section>

            {/* CRITICAL STATUTORY ALERT: Streamlined Executive Banner */}
            <div className="bg-surface-card border-l-4 border-status-error border-y border-r border-border-subtle p-space-xl rounded-xl shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-space-lg">
              <div className="flex items-start gap-space-md">
                <div className="w-10 h-10 rounded-xl bg-status-error-surface text-status-error flex items-center justify-center shrink-0">
                  <span className="material-symbols-outlined text-[24px]">gavel</span>
                </div>
                <div>
                  <div className="flex items-center gap-space-sm mb-space-2xs flex-wrap">
                    <span className="font-label-md text-label-md font-bold uppercase tracking-wide text-status-error">
                      Intake Quota Variance Detected
                    </span>
                    <span className="text-outline text-label-sm">
                      AICTE Handbook Sec 3.4
                    </span>
                  </div>
                  <p className="font-body-md text-body-md text-on-surface leading-relaxed">
                    <strong className="text-primary">
                      Electronics &amp; Communication Engineering
                    </strong>{' '}
                    exceeded sanctioned intake by{' '}
                    <strong className="text-status-error">2 students</strong>. Institutional certification is temporarily held pending reconciliation.
                  </p>
                </div>
              </div>
              <button
                onClick={() => {
                  if (onNavigateTab) {
                    onNavigateTab('aicte-review');
                  }
                }}
                className="px-space-lg py-space-sm bg-status-error text-on-error font-label-md text-label-md rounded-lg font-semibold hover:bg-navy-deep transition-colors shadow-sm shrink-0 cursor-pointer flex items-center gap-1.5"
              >
                <span>Resolve Variance</span>
                <span className="material-symbols-outlined text-sm">arrow_forward</span>
              </button>
            </div>

            {/* Approved Intake vs Actual Enrolment Reconciliation Grid */}
            <section className="bg-surface-card rounded-xl border border-border-subtle shadow-sm overflow-hidden">
              <div className="p-space-xl bg-surface-card border-b border-border-subtle flex flex-col sm:flex-row sm:items-center justify-between gap-space-sm">
                <div>
                  <h2 className="font-headline-md text-headline-md text-primary tracking-tight font-bold">
                    Intake &amp; Enrolment Reconciliation
                  </h2>
                  <p className="font-body-sm text-body-sm text-on-surface-variant mt-space-2xs">
                    Statutory sanctioned capacity against verified active roster records for AY {selectedAY}.
                  </p>
                </div>
                <div className="flex items-center gap-space-md">
                  <span className="font-code-sm text-code-sm text-outline">
                    Synced 12 mins ago
                  </span>
                  <button
                    onClick={() => showToast('Reconciliation grid refreshed with central database.')}
                    className="p-space-xs text-outline hover:text-primary transition-colors cursor-pointer"
                    title="Refresh Table"
                  >
                    <span className="material-symbols-outlined text-[20px]">refresh</span>
                  </button>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-surface-subtle font-label-sm text-label-sm text-outline uppercase tracking-wider border-b border-border-subtle">
                      <th className="py-space-md px-space-xl font-semibold">
                        Department / Programme
                      </th>
                      <th className="py-space-md px-space-lg font-semibold text-right">
                        Sanctioned
                      </th>
                      <th className="py-space-md px-space-lg font-semibold text-right">
                        Supernumerary
                      </th>
                      <th className="py-space-md px-space-lg font-semibold text-right">
                        Actual Regular
                      </th>
                      <th className="py-space-md px-space-lg font-semibold text-right">
                        Actual Super.
                      </th>
                      <th className="py-space-md px-space-lg font-semibold text-right">
                        Total Enrolled
                      </th>
                      <th className="py-space-md px-space-lg font-semibold text-right">
                        Utilization
                      </th>
                      <th className="py-space-md px-space-lg font-semibold text-center">
                        Status
                      </th>
                      <th className="py-space-md px-space-xl font-semibold text-right">
                        Action
                      </th>
                    </tr>
                  </thead>
                  <tbody className="font-body-md text-body-md text-on-surface divide-y divide-border-subtle">
                    {DEPARTMENT_DATA.map((row) => (
                      <tr
                        key={row.id}
                        className={`transition-colors ${
                          row.hasViolation
                            ? 'bg-status-error-surface/40 hover:bg-status-error-surface/60'
                            : 'hover:bg-surface-subtle'
                        }`}
                      >
                        <td className="py-space-lg px-space-xl font-medium text-primary">
                          <div
                            className={`font-headline-sm text-headline-sm font-bold flex items-center gap-space-xs ${
                              row.hasViolation ? 'text-status-error' : 'text-primary'
                            }`}
                          >
                            <span>{row.name}</span>
                            {row.hasViolation && (
                              <span className="material-symbols-outlined text-[18px]">
                                warning
                              </span>
                            )}
                          </div>
                          <span className="font-code-sm text-code-sm text-outline">
                            {row.code}
                          </span>
                        </td>
                        <td className="py-space-lg px-space-lg text-right font-code-sm text-code-sm text-outline">
                          {row.sanctioned}
                        </td>
                        <td className="py-space-lg px-space-lg text-right font-code-sm text-code-sm text-outline">
                          {row.supernumerary}
                        </td>
                        <td
                          className={`py-space-lg px-space-lg text-right font-code-sm text-code-sm font-semibold ${
                            row.hasViolation ? 'text-status-error font-bold' : 'text-primary'
                          }`}
                        >
                          {row.actualRegular} {row.excessCount ? `(+${row.excessCount})` : ''}
                        </td>
                        <td className="py-space-lg px-space-lg text-right font-code-sm text-code-sm text-outline">
                          {row.actualSuper}
                        </td>
                        <td
                          className={`py-space-lg px-space-lg text-right font-code-sm text-code-sm font-bold ${
                            row.hasViolation ? 'text-status-error' : 'text-primary'
                          }`}
                        >
                          {row.totalEnrolled}
                        </td>
                        <td
                          className={`py-space-lg px-space-lg text-right font-code-sm text-code-sm font-bold ${
                            row.hasViolation
                              ? 'text-status-error'
                              : row.utilization === '100.0%'
                              ? 'text-secondary'
                              : 'text-status-verified'
                          }`}
                        >
                          {row.utilization}
                        </td>
                        <td className="py-space-lg px-space-lg text-center">
                          {row.hasViolation ? (
                            <span className="inline-flex items-center gap-space-2xs px-space-sm py-space-2xs bg-status-error text-on-error font-label-sm text-label-sm rounded-full font-bold">
                              <span className="material-symbols-outlined text-[14px]">
                                error
                              </span>
                              Exceeded (+{row.excessCount})
                            </span>
                          ) : row.utilization === '100.0%' ? (
                            <span className="inline-flex items-center gap-space-2xs px-space-sm py-space-2xs bg-surface-subtle text-primary font-label-sm text-label-sm rounded-full font-semibold border border-border-subtle">
                              <span className="material-symbols-outlined text-[14px]">
                                lock
                              </span>
                              At Capacity
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-space-2xs px-space-sm py-space-2xs bg-status-verified-surface text-status-verified font-label-sm text-label-sm rounded-full font-semibold border border-status-verified-border">
                              <span className="material-symbols-outlined text-[14px]">
                                check_circle
                              </span>
                              Within Quota
                            </span>
                          )}
                        </td>
                        <td className="py-space-lg px-space-xl text-right">
                          {row.hasViolation ? (
                            <button
                              onClick={() => {
                                if (onNavigateTab) {
                                  onNavigateTab('aicte-review');
                                }
                              }}
                              className="px-space-sm py-space-xs bg-status-error text-on-error rounded-lg font-label-sm text-label-sm font-bold hover:bg-navy-deep transition-colors cursor-pointer shadow-sm"
                            >
                              Resolve
                            </button>
                          ) : (
                            <button
                              onClick={() => setShowDetailModal(row)}
                              className="px-space-sm py-space-xs text-primary hover:bg-surface-container rounded-lg font-label-sm text-label-sm font-semibold transition-colors cursor-pointer border border-border-subtle"
                            >
                              View Details
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="bg-surface-subtle font-headline-sm text-headline-sm text-primary border-t-2 border-border-subtle">
                    <tr>
                      <td className="py-space-lg px-space-xl font-bold">
                        Institutional Total ({selectedLevel})
                      </td>
                      <td className="py-space-lg px-space-lg text-right font-code-sm text-code-sm text-outline">
                        510
                      </td>
                      <td className="py-space-lg px-space-lg text-right font-code-sm text-code-sm text-outline">
                        51
                      </td>
                      <td className="py-space-lg px-space-lg text-right font-code-sm text-code-sm font-bold text-primary">
                        504
                      </td>
                      <td className="py-space-lg px-space-lg text-right font-code-sm text-code-sm font-bold text-primary">
                        44
                      </td>
                      <td className="py-space-lg px-space-lg text-right font-code-sm text-code-sm font-bold text-primary">
                        548
                      </td>
                      <td className="py-space-lg px-space-lg text-right font-code-sm text-code-sm text-status-review font-bold">
                        97.6%
                      </td>
                      <td className="py-space-lg px-space-lg text-center">
                        <span className="font-code-sm text-code-sm text-status-error font-bold">
                          1 Variance Item
                        </span>
                      </td>
                      <td className="py-space-lg px-space-xl"></td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </section>

            {/* Bottom Dual Grid: Supernumerary Quota Matrix & Active Pipeline */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-space-xl">
              {/* Quota Distribution */}
              <section className="lg:col-span-2 bg-surface-card p-space-xl rounded-xl border border-border-subtle shadow-sm space-y-space-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-headline-md text-headline-md text-primary tracking-tight font-bold">
                      Special Quota &amp; Supernumerary Seats
                    </h3>
                    <p className="font-body-sm text-body-sm text-on-surface-variant mt-space-2xs">
                      Statutory affirmative action tracking against AICTE limits.
                    </p>
                  </div>
                  <span className="font-code-sm text-code-sm px-space-sm py-space-xs bg-surface-subtle text-primary rounded-lg font-semibold border border-border-subtle">
                    44 Active Seats
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-space-lg pt-space-xs">
                  {/* Quota 1: TFW */}
                  <div className="p-space-lg rounded-xl border border-border-subtle bg-surface-subtle flex flex-col justify-between">
                    <div className="flex items-center justify-between mb-space-xs">
                      <span className="font-label-sm text-label-sm font-semibold text-outline">
                        TFW
                      </span>
                      <span className="text-[11px] font-code-sm text-status-verified font-bold">
                        Cap 25
                      </span>
                    </div>
                    <div className="my-space-xs">
                      <span className="font-display-lg text-display-lg font-bold text-primary">
                        22
                      </span>
                    </div>
                    <div className="w-full bg-border-subtle h-1.5 rounded-full mt-space-xs overflow-hidden">
                      <div className="bg-status-verified h-full rounded-full w-[88%]"></div>
                    </div>
                  </div>

                  {/* Quota 2: EWS */}
                  <div className="p-space-lg rounded-xl border border-border-subtle bg-surface-subtle flex flex-col justify-between">
                    <div className="flex items-center justify-between mb-space-xs">
                      <span className="font-label-sm text-label-sm font-semibold text-outline">
                        EWS
                      </span>
                      <span className="text-[11px] font-code-sm text-secondary font-bold">
                        Cap 51
                      </span>
                    </div>
                    <div className="my-space-xs">
                      <span className="font-display-lg text-display-lg font-bold text-primary">
                        51
                      </span>
                    </div>
                    <div className="w-full bg-border-subtle h-1.5 rounded-full mt-space-xs overflow-hidden">
                      <div className="bg-secondary h-full rounded-full w-[100%]"></div>
                    </div>
                  </div>

                  {/* Quota 3: PMSSS */}
                  <div className="p-space-lg rounded-xl border border-border-subtle bg-surface-subtle flex flex-col justify-between">
                    <div className="flex items-center justify-between mb-space-xs">
                      <span className="font-label-sm text-label-sm font-semibold text-outline">
                        PMSSS
                      </span>
                      <span className="text-[11px] font-code-sm text-primary font-bold">
                        Sanc 15
                      </span>
                    </div>
                    <div className="my-space-xs">
                      <span className="font-display-lg text-display-lg font-bold text-primary">
                        12
                      </span>
                    </div>
                    <div className="w-full bg-border-subtle h-1.5 rounded-full mt-space-xs overflow-hidden">
                      <div className="bg-primary h-full rounded-full w-[80%]"></div>
                    </div>
                  </div>

                  {/* Quota 4: NRI */}
                  <div className="p-space-lg rounded-xl border border-border-subtle bg-surface-subtle flex flex-col justify-between">
                    <div className="flex items-center justify-between mb-space-xs">
                      <span className="font-label-sm text-label-sm font-semibold text-outline">
                        NRI Candidates
                      </span>
                      <span className="text-[11px] font-code-sm text-status-review font-bold">
                        Limit 12
                      </span>
                    </div>
                    <div className="my-space-xs">
                      <span className="font-display-lg text-display-lg font-bold text-primary">
                        6
                      </span>
                    </div>
                    <div className="w-full bg-border-subtle h-1.5 rounded-full mt-space-xs overflow-hidden">
                      <div className="bg-status-review h-full rounded-full w-[50%]"></div>
                    </div>
                  </div>

                  {/* Quota 5: OCI / PIO */}
                  <div className="p-space-lg rounded-xl border border-border-subtle bg-surface-subtle flex flex-col justify-between">
                    <div className="flex items-center justify-between mb-space-xs">
                      <span className="font-label-sm text-label-sm font-semibold text-outline">
                        OCI / PIO
                      </span>
                      <span className="text-[11px] font-code-sm text-primary font-bold">
                        Limit 6
                      </span>
                    </div>
                    <div className="my-space-xs">
                      <span className="font-display-lg text-display-lg font-bold text-primary">
                        3
                      </span>
                    </div>
                    <div className="w-full bg-border-subtle h-1.5 rounded-full mt-space-xs overflow-hidden">
                      <div className="bg-primary h-full rounded-full w-[50%]"></div>
                    </div>
                  </div>

                  {/* Quota 6: FN */}
                  <div className="p-space-lg rounded-xl border border-border-subtle bg-surface-subtle flex flex-col justify-between">
                    <div className="flex items-center justify-between mb-space-xs">
                      <span className="font-label-sm text-label-sm font-semibold text-outline">
                        Foreign Nationals
                      </span>
                      <span className="text-[11px] font-code-sm text-secondary font-bold">
                        Limit 8
                      </span>
                    </div>
                    <div className="my-space-xs">
                      <span className="font-display-lg text-display-lg font-bold text-primary">
                        1
                      </span>
                    </div>
                    <div className="w-full bg-border-subtle h-1.5 rounded-full mt-space-xs overflow-hidden">
                      <div className="bg-secondary h-full rounded-full w-[12.5%]"></div>
                    </div>
                  </div>
                </div>
              </section>

              {/* Active Batch Pipeline & Diagnostic Rail */}
              <section className="bg-surface-card p-space-xl rounded-xl border border-border-subtle shadow-sm flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between pb-space-xs mb-space-xs">
                    <h3 className="font-headline-sm text-headline-sm text-primary tracking-tight font-bold">
                      Ingestion Pipeline
                    </h3>
                    <span className="w-2.5 h-2.5 rounded-full bg-status-verified animate-ping"></span>
                  </div>
                  <span className="font-code-sm text-code-sm text-outline block">
                    Batch #2025-04B • 1,420 Records
                  </span>

                  {/* Pipeline Timeline */}
                  <div className="mt-space-xl space-y-space-lg relative">
                    <div className="absolute left-3.5 top-3 bottom-3 w-0.5 bg-border-subtle z-0"></div>

                    <div className="relative z-10 flex items-start gap-space-md">
                      <div className="w-7 h-7 rounded-full bg-status-verified text-on-primary flex items-center justify-center shrink-0">
                        <span className="material-symbols-outlined text-[16px]">check</span>
                      </div>
                      <div>
                        <span className="font-headline-sm text-headline-sm text-primary block leading-tight font-bold">
                          Schema Lock
                        </span>
                        <span className="font-label-sm text-label-sm text-outline">
                          1,420 valid student nodes
                        </span>
                      </div>
                    </div>

                    <div className="relative z-10 flex items-start gap-space-md">
                      <div className="w-7 h-7 rounded-full bg-status-verified text-on-primary flex items-center justify-center shrink-0">
                        <span className="material-symbols-outlined text-[16px]">verified</span>
                      </div>
                      <div>
                        <span className="font-headline-sm text-headline-sm text-primary block leading-tight font-bold">
                          APAAR Registry Matching
                        </span>
                        <span className="font-label-sm text-label-sm text-outline">
                          1,384 UIDAI tokens linked
                        </span>
                      </div>
                    </div>

                    <div className="relative z-10 flex items-start gap-space-md">
                      <div className="w-7 h-7 rounded-full bg-status-review text-on-primary flex items-center justify-center shrink-0">
                        <span className="material-symbols-outlined text-[16px]">rule</span>
                      </div>
                      <div>
                        <span className="font-headline-sm text-headline-sm text-status-review block leading-tight font-bold">
                          Integrity Review
                        </span>
                        <span className="font-label-sm text-label-sm text-outline">
                          28 active findings flagged
                        </span>
                      </div>
                    </div>

                    <div className="relative z-10 flex items-start gap-space-md opacity-50">
                      <div className="w-7 h-7 rounded-full bg-surface-container text-on-surface-variant flex items-center justify-center shrink-0">
                        <span className="material-symbols-outlined text-[16px]">send</span>
                      </div>
                      <div>
                        <span className="font-headline-sm text-headline-sm text-on-surface-variant block leading-tight font-bold">
                          AICTE Registry Sync
                        </span>
                        <span className="font-label-sm text-label-sm text-outline">
                          Pending issue resolution
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-space-xl pt-space-md border-t border-border-subtle flex items-center justify-between">
                  <button
                    onClick={() => {
                      if (onNavigateTab) {
                        onNavigateTab('findings');
                      }
                      showToast('Navigating to Data Quality & Findings workspace...');
                    }}
                    className="font-label-md text-label-md text-secondary font-bold hover:underline flex items-center gap-space-2xs cursor-pointer"
                  >
                    <span>View Findings in Workspace</span>
                    <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                  </button>
                </div>
              </section>
            </div>
          </div>
        </div>
      </main>

      {/* UPLOAD BATCH MODAL */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-surface-card rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-border-subtle flex flex-col gap-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-border-subtle pb-3">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-2xl">
                  cloud_upload
                </span>
                <h3 className="font-headline-sm text-primary font-bold">
                  Upload Student Batch
                </h3>
              </div>
              <button
                onClick={() => setShowUploadModal(false)}
                className="text-outline hover:text-primary p-1 rounded cursor-pointer"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            <p className="text-xs text-on-surface-variant leading-relaxed">
              Upload institutional student enrolment roster (CSV or XLSX) formatted per AICTE Data Standard Specification v2.4.
            </p>

            {/* Dropzone */}
            <div
              onClick={() => {
                setUploadFileName('NIT_Trichy_Batch_2025_04C_Roster.xlsx');
                showToast('Sample roster file staged: NIT_Trichy_Batch_2025_04C_Roster.xlsx');
              }}
              className="border-2 border-dashed border-secondary/40 hover:border-secondary bg-surface-subtle/60 hover:bg-surface-subtle rounded-xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-colors"
            >
              <span className="material-symbols-outlined text-4xl text-secondary mb-2">
                upload_file
              </span>
              <div className="font-semibold text-sm text-primary">
                {uploadFileName ? uploadFileName : 'Click or drop roster file here'}
              </div>
              <div className="text-xs text-outline mt-1">
                Supports .CSV, .XLSX (Max 25MB • Up to 5,000 student records)
              </div>
            </div>

            <div className="flex items-center justify-between text-xs bg-surface-subtle p-3 rounded-lg border border-border-subtle">
              <span className="text-outline">Validation Scheme:</span>
              <span className="font-mono font-bold text-status-verified">
                APH-2025-RULE-R1-R16
              </span>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-border-subtle">
              <button
                onClick={() => {
                  setShowUploadModal(false);
                  setUploadFileName(null);
                }}
                className="px-4 py-2 rounded-lg text-xs font-semibold text-outline hover:bg-surface-subtle transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleSimulateUpload}
                disabled={isProcessingUpload}
                className="px-4 py-2 rounded-lg text-xs font-semibold bg-primary hover:bg-navy-deep text-white transition-colors cursor-pointer flex items-center gap-1.5 disabled:opacity-75"
              >
                <span
                  className={`material-symbols-outlined text-sm ${
                    isProcessingUpload ? 'animate-spin' : ''
                  }`}
                >
                  {isProcessingUpload ? 'progress_activity' : 'publish'}
                </span>
                <span>{isProcessingUpload ? 'Validating Batch...' : 'Ingest Batch'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* DEPARTMENT DETAIL MODAL */}
      {showDetailModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-surface-card rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-border-subtle flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-border-subtle pb-3">
              <div>
                <div className="text-xs font-mono text-outline">{showDetailModal.code}</div>
                <h3 className="font-headline-sm text-primary font-bold">
                  {showDetailModal.name}
                </h3>
              </div>
              <button
                onClick={() => setShowDetailModal(null)}
                className="text-outline hover:text-primary p-1 rounded cursor-pointer"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 bg-surface-subtle rounded-lg border border-border-subtle">
                <span className="text-outline block">Sanctioned Regular</span>
                <span className="text-base font-bold text-primary font-mono">
                  {showDetailModal.sanctioned}
                </span>
              </div>
              <div className="p-3 bg-surface-subtle rounded-lg border border-border-subtle">
                <span className="text-outline block">Supernumerary Cap</span>
                <span className="text-base font-bold text-primary font-mono">
                  {showDetailModal.supernumerary}
                </span>
              </div>
              <div className="p-3 bg-surface-subtle rounded-lg border border-border-subtle">
                <span className="text-outline block">Actual Enrolled Regular</span>
                <span className="text-base font-bold text-primary font-mono">
                  {showDetailModal.actualRegular}
                </span>
              </div>
              <div className="p-3 bg-surface-subtle rounded-lg border border-border-subtle">
                <span className="text-outline block">Capacity Utilization</span>
                <span className="text-base font-bold text-status-verified font-mono">
                  {showDetailModal.utilization}
                </span>
              </div>
            </div>

            <div className="flex justify-end pt-2 border-t border-border-subtle">
              <button
                onClick={() => setShowDetailModal(null)}
                className="px-4 py-2 bg-primary text-white rounded-lg text-xs font-semibold cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default InstitutionDashboardPage;
