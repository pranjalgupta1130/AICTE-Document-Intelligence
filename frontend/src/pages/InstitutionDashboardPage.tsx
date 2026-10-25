import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { AuthSession } from '../types/auth';
import {
  dashboardService,
  InstitutionDashboardMetrics,
  ProgrammeIntakeMetric,
  SpecialQuotaMetric,
} from '../services/api';

interface InstitutionDashboardPageProps {
  session?: AuthSession | null;
  onLogout?: () => void;
  onNavigateTab?: (tab: string) => void;
}

export const InstitutionDashboardPage: React.FC<InstitutionDashboardPageProps> = ({
  session,
  onLogout,
  onNavigateTab,
}) => {
  const [metrics, setMetrics] = useState<InstitutionDashboardMetrics | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedAY, setSelectedAY] = useState<string>('');
  const [selectedLevel, setSelectedLevel] = useState<string>('UG');
  const [selectedBatchId, setSelectedBatchId] = useState<string>('');
  const [showDetailModal, setShowDetailModal] = useState<ProgrammeIntakeMetric | null>(null);
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 3500);
  };

  const fetchDashboardData = useCallback(async (ay?: string) => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await dashboardService.getInstitutionMetrics(
        ay ? { academic_year: ay } : undefined
      );
      setMetrics(data);
      if (!ay && data.academic_year) {
        setSelectedAY(data.academic_year);
      }
      if (data.recent_batches && data.recent_batches.length > 0) {
        setSelectedBatchId(data.recent_batches[0].id);
      }
    } catch (err: any) {
      console.error('Failed to load institution dashboard:', err);
      setError(err.message || 'Failed to retrieve institution operational metrics from server.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboardData(selectedAY || undefined);
  }, [fetchDashboardData, selectedAY]);

  const handleExportQualityReport = () => {
    setIsExporting(true);
    showToast('Compiling Institutional Quality & Compliance Report (PDF/A)...');
    setTimeout(() => {
      setIsExporting(false);
      const instNameClean = (metrics?.institution_name || 'Institution').replace(/\s+/g, '_');
      showToast(`Quality Report compiled: ${instNameClean}_Quality_Report_${selectedAY || 'AY'}.pdf`);
    }, 1200);
  };

  // Derived calculations
  const totalStudents = metrics?.total_student_records ?? 0;
  const missingApaar = metrics?.missing_apaar_count ?? 0;
  const verifiedApaar = Math.max(0, totalStudents - missingApaar);
  const apaarPercent = totalStudents > 0 ? Math.round((verifiedApaar / totalStudents) * 100) : 0;

  const validRows = metrics?.valid_records_count ?? 0;
  const errorRows = metrics?.error_records_count ?? 0;
  const processedRows = validRows + errorRows;
  const validPercent = processedRows > 0 ? Math.round((validRows / processedRows) * 100) : 100;

  const blockingFindings = metrics?.blocking_findings_count ?? 0;
  const warningFindings = metrics?.warning_findings_count ?? 0;
  const totalFindings = blockingFindings + warningFindings;

  const totalActiveCandidates = metrics?.total_enrolled_students ?? 0;
  const enrolledFinalized = metrics?.enrolled_finalized_count ?? 0;
  const admittedCount = metrics?.admitted_count ?? 0;
  const totalCapacityExcess = Math.max(0, totalActiveCandidates - (metrics?.total_approved_intake ?? 0));
  const remainingCapacity = Math.max(0, (metrics?.total_approved_intake ?? 0) - totalActiveCandidates);

  const activeBatch = useMemo(() => {
    if (!metrics?.recent_batches || metrics.recent_batches.length === 0) return null;
    return metrics.recent_batches.find((b) => b.id === selectedBatchId) || metrics.recent_batches[0];
  }, [metrics, selectedBatchId]);

  const exceededProgrammes = useMemo(() => {
    return (metrics?.programme_intake_breakdown || []).filter(
      (p) =>
        p.status === 'EXCEEDED' ||
        p.total_enrolled > p.total_approved ||
        p.regular_enrolled > p.regular_approved ||
        p.supernumerary_enrolled > p.supernumerary_approved
    );
  }, [metrics]);

  // Table summary calculations
  const tableTotals = useMemo(() => {
    const list = metrics?.programme_intake_breakdown || [];
    const regSanctioned = list.reduce((sum, p) => sum + p.regular_approved, 0);
    const superSanctioned = list.reduce((sum, p) => sum + p.supernumerary_approved, 0);
    const regEnrolled = list.reduce((sum, p) => sum + p.regular_enrolled, 0);
    const superEnrolled = list.reduce((sum, p) => sum + p.supernumerary_enrolled, 0);
    const totEnrolled = list.reduce((sum, p) => sum + p.total_enrolled, 0);
    const totSanctioned = regSanctioned + superSanctioned;
    const util = totSanctioned > 0 ? ((totEnrolled / totSanctioned) * 100).toFixed(1) : '0.0';
    return {
      regSanctioned,
      superSanctioned,
      regEnrolled,
      superEnrolled,
      totEnrolled,
      totSanctioned,
      util,
    };
  }, [metrics]);

  const hasCapacityBaseline = useMemo(() => {
    return (
      (metrics?.programme_intake_breakdown && metrics.programme_intake_breakdown.length > 0) &&
      tableTotals.totSanctioned > 0
    );
  }, [metrics, tableTotals.totSanctioned]);

  const nriCount = useMemo(() => {
    const nri = metrics?.special_quota_breakdown?.find((q) => q.category === 'NRI');
    return nri ? nri.enrolled : 0;
  }, [metrics]);

  const availableYears = useMemo(() => {
    if (metrics?.available_academic_years && metrics.available_academic_years.length > 0) {
      return metrics.available_academic_years;
    }
    return ['2026-2027', '2025-2026', '2024-2025'];
  }, [metrics]);

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
              <span className="font-code-sm text-code-sm text-on-surface-variant max-w-[320px] truncate">
                {metrics?.institution_name
                  ? `${metrics.institution_name} (${metrics.institution_id})`
                  : session?.instCode
                  ? `Node (${session.instCode})`
                  : 'Authenticated Institution Node'}
              </span>
            </div>

            <div className="relative">
              <span className="font-label-md text-label-md bg-surface-card border border-border-strong text-primary rounded-lg px-space-sm py-space-xs inline-block">
                {session?.roleTitle || 'Institution Admin'}
              </span>
            </div>

            <button
              aria-label="Notifications"
              onClick={() => {
                if (exceededProgrammes.length > 0) {
                  showToast(`Intake Quota Variance alert pending resolution on ${exceededProgrammes[0].programme_name}.`);
                } else {
                  showToast('No outstanding regulatory alerts.');
                }
              }}
              className="relative p-space-xs text-on-surface-variant hover:text-primary transition-colors cursor-pointer"
            >
              <span className="material-symbols-outlined text-[20px]">notifications</span>
              {exceededProgrammes.length > 0 && (
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
                  {session?.roleTitle || 'Registrar'}
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
              APAAR ID-Based Verification Engine • Live Database Scoped to {metrics?.institution_name || 'Institution'} • AY {selectedAY || '2026-2027'}
            </span>
          </div>
          <div className="hidden sm:flex items-center gap-space-sm shrink-0">
            <span className="font-label-sm text-label-sm text-outline">
              Security: Role-Scoped Access Controls
            </span>
            <span className="font-label-sm text-label-sm text-status-verified font-medium">
              ● Database: SQLite Ledger Active (Local)
            </span>
          </div>
        </div>
      </header>

      {/* MAIN CONTENT WORKSPACE */}
      <main className="w-full pt-32 bg-transparent min-h-screen">
        <div className="flex flex-col w-full">
          {/* Administrative Action Bar & Scope Filter */}
          <div className="bg-surface-card/85 backdrop-blur-md shadow-sm px-gutter-md py-space-md mb-space-lg border-b border-border-subtle">
            <div className="max-w-[1440px] mx-auto flex flex-col xl:flex-row xl:items-center justify-between gap-space-md">
              {/* Institutional Contextual Hierarchy */}
              <div className="flex flex-col">
                <div className="flex items-center gap-space-xs text-outline">
                  <span className="font-code-sm text-code-sm uppercase tracking-wider text-secondary font-semibold">
                    Institutional Intake Monitor
                  </span>
                  <span className="text-[10px]">•</span>
                  <span className="font-code-sm text-code-sm">
                    AICTE Handbook Approved Capacity Compliance
                  </span>
                </div>
                <div className="flex items-baseline gap-space-sm mt-space-2xs">
                  <h1 className="font-headline-lg text-headline-lg text-primary tracking-tight font-bold">
                    {metrics?.institution_name || (session?.instCode ? `Institution (${session.instCode})` : 'Institutional Dashboard')}
                  </h1>
                  <span className="font-code-sm text-code-sm px-space-xs py-space-2xs bg-surface-container text-on-surface-variant rounded font-semibold">
                    PID: {metrics?.institution_id || session?.instCode || 'ID: --'}
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
                    {availableYears.map((yr) => (
                      <option key={yr} value={yr}>
                        {yr}
                      </option>
                    ))}
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

                {metrics?.recent_batches && metrics.recent_batches.length > 0 && (
                  <div className="flex items-center gap-space-xs bg-surface-subtle px-space-sm py-space-xs rounded-lg shadow-sm border border-border-subtle">
                    <span className="material-symbols-outlined text-outline text-[18px]">
                      inventory_2
                    </span>
                    <select
                      value={selectedBatchId}
                      onChange={(e) => {
                        setSelectedBatchId(e.target.value);
                        const b = metrics.recent_batches.find((item) => item.id === e.target.value);
                        if (b) {
                          showToast(`Batch selected: ${b.source_filename} (${b.status})`);
                        }
                      }}
                      className="font-label-md text-label-md bg-transparent text-on-surface font-semibold focus:outline-none cursor-pointer max-w-[200px] truncate"
                    >
                      {metrics.recent_batches.map((b) => (
                        <option key={b.id} value={b.id}>
                          {b.source_filename} (v{b.version} • {b.status})
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                <div className="h-6 w-px bg-border-strong hidden sm:block"></div>

                <button
                  onClick={() => {
                    if (onNavigateTab) {
                      onNavigateTab('import');
                    } else {
                      showToast('Navigate to Bulk Import & Validation to ingest student batches.');
                    }
                  }}
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
            {/* Loading State Banner */}
            {isLoading && !metrics && (
              <div className="bg-surface-card p-space-2xl rounded-xl border border-border-subtle shadow-sm flex flex-col items-center justify-center gap-space-md">
                <span className="material-symbols-outlined text-4xl text-primary animate-spin">
                  progress_activity
                </span>
                <p className="font-body-md text-on-surface-variant font-medium">
                  Loading institutional metrics from central registry for AY {selectedAY || '2026-2027'}...
                </p>
              </div>
            )}

            {/* Error State Banner */}
            {error && (
              <div className="bg-status-error-surface border-l-4 border-status-error p-space-xl rounded-xl shadow-sm flex items-start justify-between gap-space-md">
                <div className="flex items-start gap-space-md">
                  <span className="material-symbols-outlined text-status-error text-[28px]">
                    error
                  </span>
                  <div>
                    <h3 className="font-headline-sm text-status-error font-bold">
                      Failed to Retrieve Operational Metrics
                    </h3>
                    <p className="font-body-sm text-on-surface-variant mt-1">{error}</p>
                  </div>
                </div>
                <button
                  onClick={() => fetchDashboardData(selectedAY || undefined)}
                  className="px-space-md py-space-xs bg-status-error text-on-error rounded font-label-sm font-semibold hover:bg-navy-deep transition-colors cursor-pointer shrink-0"
                >
                  Retry
                </button>
              </div>
            )}

            {/* Empty State Banner (0 student records in selected year) */}
            {!isLoading && metrics && metrics.total_student_records === 0 && (
              <div className="bg-surface-subtle border border-border-subtle p-space-xl rounded-xl shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-space-md">
                <div className="flex items-center gap-space-md">
                  <div className="w-10 h-10 rounded-full bg-surface-container flex items-center justify-center text-outline">
                    <span className="material-symbols-outlined text-[24px]">folder_off</span>
                  </div>
                  <div>
                    <h4 className="font-headline-sm text-primary font-bold">
                      No Student Records for AY {selectedAY}
                    </h4>
                    <p className="font-body-sm text-on-surface-variant">
                      No active enrolment roster has been uploaded for this academic year. Statutory intake limits remain configured below.
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => onNavigateTab && onNavigateTab('import')}
                  className="px-space-md py-space-xs bg-primary text-on-primary rounded font-label-sm font-semibold hover:bg-navy-deep transition-colors cursor-pointer shrink-0 flex items-center gap-1"
                >
                  <span className="material-symbols-outlined text-sm">upload_file</span>
                  <span>Upload Roster for {selectedAY}</span>
                </button>
              </div>
            )}

            {/* KPI Operational Cards */}
            <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-space-lg">
              {/* Card 1: Total Enrolled & Admitted */}
              <div className="bg-surface-card p-space-xl rounded-xl shadow-sm border border-border-subtle flex flex-col justify-between hover:shadow-md transition-shadow">
                <div>
                  <div className="flex items-center justify-between mb-space-sm">
                    <span className="font-label-sm text-label-sm text-outline uppercase tracking-wider font-semibold">
                      Admitted &amp; Enrolled Intake
                    </span>
                    <div className="w-9 h-9 rounded-lg bg-surface-subtle flex items-center justify-center text-primary">
                      <span className="material-symbols-outlined text-[20px]">groups</span>
                    </div>
                  </div>
                  <div className="flex items-baseline gap-space-xs my-space-xs">
                    <span className="font-display-lg text-display-lg font-bold text-primary tracking-tight">
                      {totalActiveCandidates.toLocaleString()}
                    </span>
                    <span className="font-body-md text-body-md text-outline">
                      / {(metrics?.total_approved_intake ?? 0).toLocaleString()} Approved
                    </span>
                  </div>
                </div>
                <div className="mt-space-lg pt-space-xs">
                  <div className="flex justify-between items-center mb-space-xs text-body-sm font-body-sm">
                    <span className="text-on-surface-variant font-medium">
                      {enrolledFinalized} Enrolled • {admittedCount} Admitted
                    </span>
                    {totalCapacityExcess > 0 ? (
                      <span className="text-status-error font-semibold">
                        +{totalCapacityExcess.toLocaleString()} Over Sanctioned
                      </span>
                    ) : (
                      <span className="text-status-verified font-semibold">
                        {remainingCapacity.toLocaleString()} Available
                      </span>
                    )}
                  </div>
                  <div className="w-full bg-surface-subtle h-2 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        totalCapacityExcess > 0 ? 'bg-status-error' : 'bg-secondary'
                      }`}
                      style={{
                        width: `${Math.min(100, metrics?.intake_utilization_pct ?? 0)}%`,
                      }}
                    ></div>
                  </div>
                </div>
              </div>

              {/* Card 2: APAAR Identifier Coverage */}
              <div className="bg-surface-card p-space-xl rounded-xl shadow-sm border border-border-subtle flex flex-col justify-between hover:shadow-md transition-shadow">
                <div>
                  <div className="flex items-center justify-between mb-space-sm">
                    <span className="font-label-sm text-label-sm text-outline uppercase tracking-wider font-semibold">
                      APAAR Identifier Coverage
                    </span>
                    <div className="w-9 h-9 rounded-lg bg-status-verified-surface flex items-center justify-center text-status-verified">
                      <span className="material-symbols-outlined text-[20px]">badge</span>
                    </div>
                  </div>
                  <div className="flex items-baseline gap-space-xs my-space-xs">
                    <span className="font-display-lg text-display-lg font-bold text-status-verified tracking-tight">
                      {verifiedApaar.toLocaleString()}
                    </span>
                    <span className="font-body-md text-body-md text-outline">
                      / {totalStudents.toLocaleString()} Records
                    </span>
                  </div>
                </div>
                <div className="mt-space-lg pt-space-xs">
                  <div className="flex justify-between items-center mb-space-xs text-body-sm font-body-sm">
                    <span className="text-on-surface-variant">{apaarPercent}% Populated</span>
                    <span className="text-status-review font-semibold">
                      {missingApaar.toLocaleString()} Missing / Unassigned
                    </span>
                  </div>
                  <div className="w-full bg-surface-subtle h-2 rounded-full overflow-hidden">
                    <div
                      className="bg-status-verified h-full rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(100, apaarPercent)}%` }}
                    ></div>
                  </div>
                </div>
              </div>

              {/* Card 3: Open Validation Findings */}
              <div className="bg-surface-card p-space-xl rounded-xl shadow-sm border border-border-subtle flex flex-col justify-between hover:shadow-md transition-shadow">
                <div>
                  <div className="flex items-center justify-between mb-space-sm">
                    <span className="font-label-sm text-label-sm text-outline uppercase tracking-wider font-semibold">
                      Open Validation Findings
                    </span>
                    <div className="w-9 h-9 rounded-lg bg-status-error-surface flex items-center justify-center text-status-error">
                      <span className="material-symbols-outlined text-[20px]">error</span>
                    </div>
                  </div>
                  <div className="flex items-baseline gap-space-xs my-space-xs">
                    <span className="font-display-lg text-display-lg font-bold text-status-error tracking-tight">
                      {totalFindings}
                    </span>
                    <span className="font-body-md text-body-md text-outline">
                      Open Exceptions
                    </span>
                  </div>
                </div>
                <div className="mt-space-lg pt-space-xs flex items-center justify-between text-body-sm font-body-sm">
                  <span className="text-status-error font-medium flex items-center gap-space-2xs">
                    <span className="w-2 h-2 rounded-full bg-status-error"></span>
                    {blockingFindings} Blocking
                  </span>
                  <span className="text-status-review font-medium flex items-center gap-space-2xs">
                    <span className="w-2 h-2 rounded-full bg-status-review"></span>
                    {warningFindings} Warnings
                  </span>
                </div>
              </div>

              {/* Card 4: Dataset Quality Pass Rate */}
              <div className="bg-surface-card p-space-xl rounded-xl shadow-sm border border-border-subtle flex flex-col justify-between hover:shadow-md transition-shadow">
                <div>
                  <div className="flex items-center justify-between mb-space-sm">
                    <span className="font-label-sm text-label-sm text-outline uppercase tracking-wider font-semibold">
                      Dataset Quality Pass Rate
                    </span>
                    <span className="px-space-xs py-space-2xs bg-surface-subtle text-primary font-code-sm text-code-sm rounded font-bold border border-border-subtle">
                      Latest: {metrics?.latest_batch_status || 'READY'}
                    </span>
                  </div>
                  <div className="flex items-baseline gap-space-xs my-space-xs">
                    <span className="font-display-lg text-display-lg font-bold text-primary tracking-tight">
                      {validPercent}%
                    </span>
                    <span className="font-body-md text-body-md text-outline">
                      Valid Roster Rows
                    </span>
                  </div>
                </div>
                <div className="mt-space-lg pt-space-xs flex items-center justify-between text-center text-body-sm font-body-sm text-outline border-t border-border-subtle pt-space-sm">
                  <div>
                    <strong className="text-primary block font-code-sm">
                      {validRows.toLocaleString()}
                    </strong>
                    Valid Rows
                  </div>
                  <div>
                    <strong className="text-primary block font-code-sm">
                      {errorRows.toLocaleString()}
                    </strong>
                    Errors
                  </div>
                  <div>
                    <strong className="text-primary block font-code-sm">
                      {metrics?.total_batches ?? 0}
                    </strong>
                    Batches
                  </div>
                </div>
              </div>
            </section>

            {/* CRITICAL STATUTORY ALERT: Dynamic Compliance Banner */}
            {!hasCapacityBaseline ? (
              <div className="bg-surface-card border-l-4 border-outline border-y border-r border-border-subtle p-space-lg rounded-xl shadow-sm flex flex-col sm:flex-row items-center justify-between gap-space-md">
                <div className="flex items-center gap-space-md">
                  <div className="w-9 h-9 rounded-lg bg-surface-subtle text-outline flex items-center justify-center shrink-0">
                    <span className="material-symbols-outlined text-[22px]">help_outline</span>
                  </div>
                  <div>
                    <span className="font-label-md text-label-md font-bold text-primary">
                      Intake Capacity Baseline Unverified
                    </span>
                    <p className="font-body-sm text-body-sm text-on-surface-variant">
                      Approved intake limits are not configured for AY {selectedAY}. Capacity compliance cannot be certified.
                    </p>
                  </div>
                </div>
                <span className="font-code-sm text-code-sm text-outline font-semibold bg-surface-subtle px-space-sm py-space-2xs rounded-lg border border-border-subtle">
                  UNVERIFIED
                </span>
              </div>
            ) : exceededProgrammes.length > 0 ? (
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
                        AICTE Handbook Sanctioned Capacity Rule
                      </span>
                    </div>
                    <p className="font-body-md text-body-md text-on-surface leading-relaxed">
                      <strong className="text-primary">
                        {exceededProgrammes.map((p) => p.programme_name).join(', ')}
                      </strong>{' '}
                      exceeded approved intake limits ({exceededProgrammes.map((p) => `${p.total_enrolled} active vs ${p.total_approved} sanctioned`).join(', ')}). Central regulatory reconciliation is required.
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
            ) : (
              <div className="bg-surface-card border-l-4 border-status-verified border-y border-r border-border-subtle p-space-lg rounded-xl shadow-sm flex flex-col sm:flex-row items-center justify-between gap-space-md">
                <div className="flex items-center gap-space-md">
                  <div className="w-9 h-9 rounded-lg bg-status-verified-surface text-status-verified flex items-center justify-center shrink-0">
                    <span className="material-symbols-outlined text-[22px]">check_circle</span>
                  </div>
                  <div>
                    <span className="font-label-md text-label-md font-bold text-primary">
                      Sanctioned Intake Capacity Verified
                    </span>
                    <p className="font-body-sm text-body-sm text-on-surface-variant">
                      All {metrics?.programme_intake_breakdown.length ?? 0} active academic programmes are operating strictly within approved AICTE ceilings for AY {selectedAY}.
                    </p>
                  </div>
                </div>
                <span className="font-code-sm text-code-sm text-status-verified font-semibold bg-status-verified-surface px-space-sm py-space-2xs rounded-lg border border-status-verified-border">
                  COMPLIANT
                </span>
              </div>
            )}

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
                    {metrics ? `Live Database (${metrics.institution_id})` : 'Syncing...'}
                  </span>
                  <button
                    onClick={() => {
                      fetchDashboardData(selectedAY);
                      showToast('Reconciliation grid refreshed with central database.');
                    }}
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
                    {metrics && metrics.programme_intake_breakdown.length > 0 ? (
                      metrics.programme_intake_breakdown.map((row) => {
                        const regExcess = Math.max(0, row.regular_enrolled - row.regular_approved);
                        const superExcess = Math.max(0, row.supernumerary_enrolled - row.supernumerary_approved);
                        const totExcess = Math.max(0, row.total_enrolled - row.total_approved);
                        const hasViolation = row.status === 'EXCEEDED' || totExcess > 0 || regExcess > 0 || superExcess > 0;
                        const excessCount = Math.max(totExcess, regExcess + superExcess);

                        return (
                          <tr
                            key={row.programme_id}
                            className={`transition-colors ${
                              hasViolation
                                ? 'bg-status-error-surface/40 hover:bg-status-error-surface/60'
                                : 'hover:bg-surface-subtle'
                            }`}
                          >
                            <td className="py-space-lg px-space-xl font-medium text-primary">
                              <div
                                className={`font-headline-sm text-headline-sm font-bold flex items-center gap-space-xs ${
                                  hasViolation ? 'text-status-error' : 'text-primary'
                                }`}
                              >
                                <span>{row.programme_name}</span>
                                {hasViolation && (
                                  <span className="material-symbols-outlined text-[18px]">
                                    warning
                                  </span>
                                )}
                              </div>
                              <span className="font-code-sm text-code-sm text-outline">
                                {row.programme_id}
                              </span>
                            </td>
                            <td className="py-space-lg px-space-lg text-right font-code-sm text-code-sm text-outline">
                              {row.regular_approved}
                            </td>
                            <td className="py-space-lg px-space-lg text-right font-code-sm text-code-sm text-outline">
                              {row.supernumerary_approved}
                            </td>
                            <td
                              className={`py-space-lg px-space-lg text-right font-code-sm text-code-sm font-semibold ${
                                regExcess > 0 ? 'text-status-error font-bold' : 'text-primary'
                              }`}
                            >
                              {row.regular_enrolled} {regExcess > 0 ? `(+${regExcess})` : ''}
                            </td>
                            <td
                              className={`py-space-lg px-space-lg text-right font-code-sm text-code-sm ${
                                superExcess > 0 ? 'text-status-error font-bold' : 'text-outline'
                              }`}
                            >
                              {row.supernumerary_enrolled} {superExcess > 0 ? `(+${superExcess})` : ''}
                            </td>
                            <td
                              className={`py-space-lg px-space-lg text-right font-code-sm text-code-sm font-bold ${
                                hasViolation ? 'text-status-error' : 'text-primary'
                              }`}
                            >
                              {row.total_enrolled}
                            </td>
                            <td
                              className={`py-space-lg px-space-lg text-right font-code-sm text-code-sm font-bold ${
                                hasViolation
                                  ? 'text-status-error'
                                  : row.utilization_pct >= 100
                                  ? 'text-secondary'
                                  : 'text-status-verified'
                              }`}
                            >
                              {row.utilization_pct}%
                            </td>
                            <td className="py-space-lg px-space-lg text-center">
                              {hasViolation ? (
                                <span className="inline-flex items-center gap-space-2xs px-space-sm py-space-2xs bg-status-error text-on-error font-label-sm text-label-sm rounded-full font-bold">
                                  <span className="material-symbols-outlined text-[14px]">
                                    error
                                  </span>
                                  Exceeded (+{excessCount})
                                </span>
                              ) : row.utilization_pct >= 100 ? (
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
                              {hasViolation ? (
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
                        );
                      })
                    ) : (
                      <tr>
                        <td
                          colSpan={9}
                          className="py-12 text-center text-outline font-body-md"
                        >
                          No programme intake records found for academic year {selectedAY}.
                        </td>
                      </tr>
                    )}
                  </tbody>
                  {metrics && metrics.programme_intake_breakdown.length > 0 && (
                    <tfoot className="bg-surface-subtle font-headline-sm text-headline-sm text-primary border-t-2 border-border-subtle">
                      <tr>
                        <td className="py-space-lg px-space-xl font-bold">
                          Institutional Total ({selectedLevel})
                        </td>
                        <td className="py-space-lg px-space-lg text-right font-code-sm text-code-sm text-outline">
                          {tableTotals.regSanctioned}
                        </td>
                        <td className="py-space-lg px-space-lg text-right font-code-sm text-code-sm text-outline">
                          {tableTotals.superSanctioned}
                        </td>
                        <td className="py-space-lg px-space-lg text-right font-code-sm text-code-sm font-bold text-primary">
                          {tableTotals.regEnrolled}
                        </td>
                        <td className="py-space-lg px-space-lg text-right font-code-sm text-code-sm font-bold text-primary">
                          {tableTotals.superEnrolled}
                        </td>
                        <td className="py-space-lg px-space-lg text-right font-code-sm text-code-sm font-bold text-primary">
                          {tableTotals.totEnrolled}
                        </td>
                        <td className="py-space-lg px-space-lg text-right font-code-sm text-code-sm text-status-review font-bold">
                          {tableTotals.util}%
                        </td>
                        <td className="py-space-lg px-space-lg text-center">
                          <span
                            className={`font-code-sm text-code-sm font-bold ${
                              exceededProgrammes.length > 0
                                ? 'text-status-error'
                                : 'text-status-verified'
                            }`}
                          >
                            {tableTotals.totSanctioned === 0
                              ? 'Unverified'
                              : exceededProgrammes.length > 0
                              ? `${exceededProgrammes.length} Variance Item${exceededProgrammes.length > 1 ? 's' : ''}`
                              : 'Ceilings Verified'}
                          </span>
                        </td>
                        <td className="py-space-lg px-space-xl"></td>
                      </tr>
                    </tfoot>
                  )}
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
                      Statutory affirmative action tracking against AICTE limits derived from active database records.
                    </p>
                  </div>
                  <span className="font-code-sm text-code-sm px-space-sm py-space-xs bg-surface-subtle text-primary rounded-lg font-semibold border border-border-subtle">
                    {tableTotals.superEnrolled} Supernumerary ({nriCount} Regular NRI)
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-space-lg pt-space-xs">
                  {(metrics?.special_quota_breakdown || [
                    { category: 'TFW', label: 'Tuition Fee Waiver (TFW)', enrolled: 0 },
                    { category: 'EWS', label: 'Economically Weaker Section (EWS)', enrolled: 0 },
                    { category: 'PMSSS', label: 'Prime Minister Special Scheme (PMSSS)', enrolled: 0 },
                    { category: 'NRI', label: 'Non-Resident Indian (NRI)', enrolled: 0 },
                    { category: 'OCI', label: 'Overseas Citizen of India (OCI)', enrolled: 0 },
                    { category: 'FN', label: 'Foreign Nationals (FN)', enrolled: 0 },
                  ]).map((quota: SpecialQuotaMetric) => (
                    <div
                      key={quota.category}
                      className="p-space-lg rounded-xl border border-border-subtle bg-surface-subtle flex flex-col justify-between"
                    >
                      <div className="flex items-center justify-between mb-space-xs">
                        <span className="font-label-sm text-label-sm font-semibold text-outline">
                          {quota.category}
                        </span>
                        <span className="text-[11px] font-code-sm text-outline">
                          {quota.label}
                        </span>
                      </div>
                      <div className="my-space-xs">
                        <span className="font-display-lg text-display-lg font-bold text-primary">
                          {quota.enrolled}
                        </span>
                        <span className="text-xs text-outline ml-1 font-body-sm">
                          Enrolled
                        </span>
                      </div>
                      <div className="w-full bg-border-subtle h-1.5 rounded-full mt-space-xs overflow-hidden">
                        <div
                          className="bg-primary h-full rounded-full transition-all duration-300"
                          style={{
                            width: `${Math.min(100, quota.enrolled > 0 ? Math.max(15, quota.enrolled * 10) : 0)}%`,
                          }}
                        ></div>
                      </div>
                    </div>
                  ))}
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
                    {activeBatch
                      ? `${activeBatch.source_filename} (v${activeBatch.version}) • ${activeBatch.total_rows.toLocaleString()} Records`
                      : `No batches active for AY ${selectedAY}`}
                  </span>
                  {activeBatch && (
                    <span className="font-label-sm text-label-sm text-on-surface-variant block mt-1">
                      Batch Lifecycle Status: <strong className="font-code-sm text-primary">{activeBatch.status}</strong>
                    </span>
                  )}

                  {/* Pipeline Timeline */}
                  <div className="mt-space-xl space-y-space-lg relative">
                    <div className="absolute left-3.5 top-3 bottom-3 w-0.5 bg-border-subtle z-0"></div>

                    <div className="relative z-10 flex items-start gap-space-md">
                      <div className="w-7 h-7 rounded-full bg-status-verified text-on-primary flex items-center justify-center shrink-0">
                        <span className="material-symbols-outlined text-[16px]">check</span>
                      </div>
                      <div>
                        <span className="font-headline-sm text-headline-sm text-primary block leading-tight font-bold">
                          Schema &amp; Format Lock
                        </span>
                        <span className="font-label-sm text-label-sm text-outline">
                          {activeBatch ? `${activeBatch.valid_rows.toLocaleString()} valid roster rows` : 'Unavailable'}
                        </span>
                      </div>
                    </div>

                    <div className="relative z-10 flex items-start gap-space-md">
                      <div
                        className={`w-7 h-7 rounded-full text-on-primary flex items-center justify-center shrink-0 ${
                          activeBatch && activeBatch.valid_rows > 0 ? 'bg-status-verified' : 'bg-surface-container text-on-surface-variant'
                        }`}
                      >
                        <span className="material-symbols-outlined text-[16px]">verified</span>
                      </div>
                      <div>
                        <span className="font-headline-sm text-headline-sm text-primary block leading-tight font-bold">
                          APAAR Identifier Coverage
                        </span>
                        <span className="font-label-sm text-label-sm text-outline">
                          {activeBatch ? `${activeBatch.valid_rows.toLocaleString()} records with APAAR identifiers populated` : 'Unavailable'}
                        </span>
                      </div>
                    </div>

                    <div className="relative z-10 flex items-start gap-space-md">
                      <div
                        className={`w-7 h-7 rounded-full text-on-primary flex items-center justify-center shrink-0 ${
                          activeBatch && (activeBatch.error_rows + activeBatch.warning_rows > 0) ? 'bg-status-review' : 'bg-status-verified'
                        }`}
                      >
                        <span className="material-symbols-outlined text-[16px]">
                          {activeBatch && (activeBatch.error_rows + activeBatch.warning_rows > 0) ? 'rule' : 'check'}
                        </span>
                      </div>
                      <div>
                        <span
                          className={`font-headline-sm text-headline-sm block leading-tight font-bold ${
                            activeBatch && (activeBatch.error_rows + activeBatch.warning_rows > 0) ? 'text-status-review' : 'text-primary'
                          }`}
                        >
                          Integrity Review
                        </span>
                        <span className="font-label-sm text-label-sm text-outline">
                          {activeBatch
                            ? (activeBatch.error_rows + activeBatch.warning_rows > 0
                              ? `${activeBatch.error_rows} errors, ${activeBatch.warning_rows} warnings flagged`
                              : '0 integrity findings in batch')
                            : 'Unavailable'}
                        </span>
                      </div>
                    </div>

                    <div className="relative z-10 flex items-start gap-space-md">
                      <div
                        className={`w-7 h-7 rounded-full text-on-primary flex items-center justify-center shrink-0 ${
                          activeBatch?.status === 'ACCEPTED'
                            ? 'bg-status-verified'
                            : activeBatch?.status === 'SUBMITTED' || activeBatch?.status === 'UNDER_REVIEW'
                            ? 'bg-secondary'
                            : 'bg-surface-container text-on-surface-variant'
                        }`}
                      >
                        <span className="material-symbols-outlined text-[16px]">send</span>
                      </div>
                      <div>
                        <span className="font-headline-sm text-headline-sm text-on-surface-variant block leading-tight font-bold">
                          AICTE Central Submission
                        </span>
                        <span className="font-label-sm text-label-sm text-outline">
                          {activeBatch ? `Status: ${activeBatch.status}` : 'Awaiting submission'}
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

      {/* PROGRAMME DETAIL MODAL */}
      {showDetailModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-surface-card rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-border-subtle flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-border-subtle pb-3">
              <div>
                <div className="text-xs font-mono text-outline">{showDetailModal.programme_id}</div>
                <h3 className="font-headline-sm text-primary font-bold">
                  {showDetailModal.programme_name}
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
                  {showDetailModal.regular_approved}
                </span>
              </div>
              <div className="p-3 bg-surface-subtle rounded-lg border border-border-subtle">
                <span className="text-outline block">Supernumerary Cap</span>
                <span className="text-base font-bold text-primary font-mono">
                  {showDetailModal.supernumerary_approved}
                </span>
              </div>
              <div className="p-3 bg-surface-subtle rounded-lg border border-border-subtle">
                <span className="text-outline block">Actual Regular Candidates</span>
                <span className="text-base font-bold text-primary font-mono">
                  {showDetailModal.regular_enrolled}
                </span>
                {showDetailModal.enrolled_count !== undefined && (
                  <span className="text-[10px] text-outline block mt-0.5">
                    {showDetailModal.enrolled_count} Enrolled • {showDetailModal.admitted_count} Admitted
                  </span>
                )}
              </div>
              <div className="p-3 bg-surface-subtle rounded-lg border border-border-subtle">
                <span className="text-outline block">Capacity Utilization</span>
                <span className="text-base font-bold text-status-verified font-mono">
                  {showDetailModal.utilization_pct}%
                </span>
                <span className="text-[10px] text-outline block mt-0.5">
                  Status: {showDetailModal.status}
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
