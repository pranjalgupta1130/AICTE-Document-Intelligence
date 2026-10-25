import React, { useState, useMemo, useEffect, useCallback } from 'react';
import { AuthSession } from '../types/auth';
import { reportService, AuditEventItem } from '../services/api';

interface AuditLogsReportsPageProps {
  session?: AuthSession | null;
  initialBatchId?: string | null;
  onLogout?: () => void;
  onNavigateTab?: (tab: string, batchId?: string) => void;
}

export const AuditLogsReportsPage: React.FC<AuditLogsReportsPageProps> = ({
  session,
  initialBatchId,
  onLogout,
  onNavigateTab,
}) => {
  // Navigation sub-tabs
  const [activeMainTab, setActiveMainTab] = useState<'audit' | 'reports' | 'security'>('audit');

  // Real audit logs state
  const [auditEvents, setAuditEvents] = useState<AuditEventItem[]>([]);
  const [totalEvents, setTotalEvents] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isExporting, setIsExporting] = useState<boolean>(false);

  // Filters
  const [searchQuery, setSearchQuery] = useState<string>(initialBatchId ? initialBatchId : '');
  const [actionFilter, setActionFilter] = useState<string>('ALL');
  const [outcomeFilter, setOutcomeFilter] = useState<string>('ALL');
  const [page, setPage] = useState<number>(0);
  const pageSize = 25;

  // Selected event for inspection modal
  const [selectedEvent, setSelectedEvent] = useState<AuditEventItem | null>(null);
  const [inspectModalOpen, setInspectModalOpen] = useState<boolean>(false);

  // Toast notification
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setStatusMessage(msg);
    setTimeout(() => {
      setStatusMessage(null);
    }, 4500);
  };

  // Determine user institution
  const institutionCode = session?.instCode && session.instCode !== 'HQ-STATUTORY-DELHI' ? session.instCode : undefined;

  // Fetch real audit logs from backend
  const fetchAuditLogs = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await reportService.getAuditLogs({
        institution_id: institutionCode,
        action: actionFilter !== 'ALL' ? actionFilter : undefined,
        outcome: outcomeFilter !== 'ALL' ? outcomeFilter : undefined,
        search: searchQuery.trim() || undefined,
        limit: pageSize,
        offset: page * pageSize,
      });
      setAuditEvents(res.items);
      setTotalEvents(res.total);
    } catch (err: any) {
      console.error('Failed to load audit logs:', err);
      showToast(err.message || 'Failed to load audit events from server');
    } finally {
      setIsLoading(false);
    }
  }, [institutionCode, actionFilter, outcomeFilter, searchQuery, page, pageSize]);

  useEffect(() => {
    fetchAuditLogs();
  }, [fetchAuditLogs]);

  // Dynamic Metrics computed from current result / total
  const { successCount, failureCount } = useMemo(() => {
    let success = 0;
    let failure = 0;
    for (const e of auditEvents) {
      if (e.outcome === 'SUCCESS') success++;
      else failure++;
    }
    return {
      successCount: success,
      failureCount: failure,
    };
  }, [auditEvents]);

  // Export Audit Ledger to CSV via protected backend endpoint
  const handleExportLedger = async (reportType: 'audit_logs' | 'findings' | 'quality_summary' = 'audit_logs') => {
    setIsExporting(true);
    try {
      showToast(`Exporting ${reportType.replace('_', ' ')} with formula protection...`);
      await reportService.exportCsvReport({
        report_type: reportType,
        batch_id: initialBatchId || undefined,
      });
      showToast(`Successfully downloaded authoritative ${reportType.replace('_', ' ')} report.`);
    } catch (err: any) {
      console.error('Export failed:', err);
      showToast(err.message || 'Export failed');
    } finally {
      setIsExporting(false);
    }
  };

  const handleResetFilters = () => {
    setSearchQuery('');
    setActionFilter('ALL');
    setOutcomeFilter('ALL');
    setPage(0);
  };

  const navItemClass = (tabKey: string) =>
    `font-title-md text-title-md px-space-sm h-full flex items-center transition-colors cursor-pointer ${
      tabKey === 'reports'
        ? 'text-primary border-b-2 border-primary font-semibold bg-surface-subtle'
        : 'text-on-surface-variant hover:text-primary hover:bg-surface-subtle'
    }`;

  return (
    <div className="tricolor-slant-bg font-body-md text-on-surface antialiased min-h-screen flex flex-col">
      {/* Toast Notification */}
      {statusMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-primary text-on-primary px-5 py-3 rounded-xl shadow-2xl flex items-center gap-3 border border-border-strong animate-bounce">
          <span className="material-symbols-outlined text-status-verified text-[22px]">verified</span>
          <span className="text-body-sm font-medium">{statusMessage}</span>
          <button
            onClick={() => setStatusMessage(null)}
            className="ml-2 hover:opacity-80 text-primary-fixed cursor-pointer"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>
      )}

      {/* HEADER */}
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
              LIVE PLATFORM
            </span>
          </div>

          <div className="flex items-center gap-space-md">
            <div className="hidden lg:flex items-center gap-space-xs bg-surface-subtle px-space-sm py-space-xs rounded-lg border border-border-subtle">
              <span className="material-symbols-outlined text-outline text-[16px]">school</span>
              <span className="font-code-sm text-code-sm text-on-surface-variant max-w-[280px] truncate">
                {session?.instCode ? `Node (${session.instCode})` : 'AICTE Central Headquarters'}
              </span>
            </div>

            <div className="flex items-center gap-space-xs pl-space-xs border-l border-border-subtle">
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center font-headline-sm text-headline-sm text-on-primary font-bold">
                <span className="material-symbols-outlined text-on-primary text-[18px]">person</span>
              </div>
              <div className="hidden md:flex flex-col">
                <span className="font-label-md text-label-md text-on-surface font-semibold leading-tight">
                  {session?.userEmail || 'Administrative Officer'}
                </span>
                <span className="font-label-sm text-label-sm text-outline leading-tight">
                  {session?.roleTitle || 'Audit Cell'}
                </span>
              </div>
              {onLogout && (
                <button
                  onClick={onLogout}
                  title="Sign Out"
                  className="ml-2 p-1 text-outline hover:text-status-error transition-colors cursor-pointer"
                >
                  <span className="material-symbols-outlined text-[18px]">logout</span>
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Global Navigation Bar */}
        <nav
          aria-label="Portal Navigation"
          className="h-10 w-full px-gutter-md flex items-center gap-space-lg border-t border-border-subtle bg-surface-card overflow-x-auto"
        >
          <button
            onClick={() => onNavigateTab?.('dashboard')}
            className={navItemClass('dashboard')}
          >
            Institution Dashboard
          </button>
          <button
            onClick={() => onNavigateTab?.('import', initialBatchId || undefined)}
            className={navItemClass('import')}
          >
            Bulk Import &amp; Validation
          </button>
          <button
            onClick={() => onNavigateTab?.('findings', initialBatchId || undefined)}
            className={navItemClass('findings')}
          >
            Data Quality &amp; Findings
          </button>
          <button
            onClick={() => onNavigateTab?.('history', initialBatchId || undefined)}
            className={navItemClass('history')}
          >
            Import History
          </button>
          <button
            onClick={() => onNavigateTab?.('aicte-review')}
            className={navItemClass('aicte-review')}
          >
            AICTE Central Review
          </button>
          <button
            onClick={() => onNavigateTab?.('records')}
            className={navItemClass('records')}
          >
            Student Record &amp; Certificate
          </button>
          <button
            onClick={() => onNavigateTab?.('reports')}
            className={navItemClass('reports')}
          >
            Audit Logs &amp; Reports
          </button>
        </nav>

        {/* Sub-ticker status */}
        <div className="h-8 w-full bg-surface-subtle border-t border-b border-border-subtle px-gutter-md flex items-center justify-between text-xs">
          <div className="flex items-center gap-space-xs overflow-hidden">
            <span className="w-2 h-2 rounded-full bg-status-verified animate-pulse shrink-0"></span>
            <span className="font-code-sm text-code-sm text-on-surface font-medium truncate">
              Append-Only Audit Store • {totalEvents} Persisted System Events • DPDP Act 2023 Masking Rules Enforced
            </span>
          </div>
          <div className="hidden sm:flex items-center gap-space-sm shrink-0">
            <span className="font-label-sm text-label-sm text-outline">
              Server-Side Tenant Scoped: {session?.instCode || 'Central'}
            </span>
            <span className="font-label-sm text-label-sm text-status-verified font-medium">
              ● Ledger Synchronized
            </span>
          </div>
        </div>
      </header>

      {/* MAIN CONTAINER */}
      <main className="w-full pt-32 bg-transparent min-h-screen flex-1 pb-24">
        <div className="flex flex-col w-full relative">
          <div className="w-full max-w-[1440px] mx-auto px-gutter-md py-space-xl flex flex-col gap-space-xl">
            {/* Top Statutory Header & Context Bar */}
            <div className="bg-surface-card rounded-xl shadow-sm p-space-xl flex flex-col lg:flex-row lg:items-center justify-between gap-space-lg">
              <div className="flex flex-col gap-space-xs">
                <div className="flex items-center gap-space-sm flex-wrap">
                  <span className="font-headline-lg text-headline-lg text-primary tracking-tight font-bold">
                    Audit Trail &amp; Regulatory Compliance Reports
                  </span>
                  <span className="font-code-sm text-code-sm px-space-sm py-space-2xs rounded-lg bg-surface-subtle text-primary font-semibold flex items-center gap-space-2xs">
                    <span className="w-2 h-2 rounded-full bg-status-verified animate-pulse"></span>
                    AUDIT STORE: APPEND-ONLY
                  </span>
                </div>
                <p className="font-body-md text-body-md text-on-surface-variant max-w-3xl">
                  Authoritative statutory event logs, batch lifecycle transitions, review decisions, and export accountability records under AICTE/NEP 2020 governance.
                </p>

                {/* Scopes & Audit Metadata Badges */}
                <div className="flex items-center gap-space-md mt-space-xs flex-wrap font-code-sm text-code-sm text-on-surface-variant">
                  <div className="flex items-center gap-space-2xs">
                    <span className="material-symbols-outlined text-outline text-[16px]">account_balance</span>
                    <span className="text-outline">Scope:</span>
                    <span className="font-semibold text-primary">
                      {session?.instCode ? `Institution Node (${session.instCode})` : 'AICTE National Central Desk'}
                    </span>
                  </div>
                  <span className="text-outline-variant">•</span>
                  <div className="flex items-center gap-space-2xs">
                    <span className="material-symbols-outlined text-outline text-[16px]">database</span>
                    <span className="text-outline">Persisted Total:</span>
                    <span className="font-semibold text-on-surface">{totalEvents} Events Recorded</span>
                  </div>
                  <span className="text-outline-variant">•</span>
                  <div className="flex items-center gap-space-2xs bg-status-verified-surface px-space-xs py-space-2xs rounded text-status-verified">
                    <span className="material-symbols-outlined text-[15px]">verified</span>
                    <span className="font-semibold">Authoritative Event Store</span>
                  </div>
                </div>
              </div>

              {/* Header Action Buttons */}
              <div className="flex items-center gap-space-sm flex-wrap lg:self-center shrink-0">
                <button
                  onClick={fetchAuditLogs}
                  disabled={isLoading}
                  className="px-space-md py-space-sm bg-surface-subtle hover:bg-surface-container text-on-surface font-label-md text-label-md rounded-lg flex items-center gap-space-xs transition-colors cursor-pointer disabled:opacity-50"
                >
                  <span className={`material-symbols-outlined text-secondary text-[18px] ${isLoading ? 'animate-spin' : ''}`}>
                    refresh
                  </span>
                  <span>{isLoading ? 'Loading Logs...' : 'Refresh Logs'}</span>
                </button>

                <button
                  onClick={() => handleExportLedger('audit_logs')}
                  disabled={isExporting}
                  className="px-space-md py-space-sm bg-secondary text-on-secondary hover:bg-secondary-fixed font-label-md text-label-md rounded-lg flex items-center gap-space-xs transition-colors shadow-sm cursor-pointer disabled:opacity-50"
                >
                  <span className="material-symbols-outlined text-[18px]">file_download</span>
                  <span>Export Audit Logs (.CSV)</span>
                </button>

                <button
                  onClick={() => {
                    setActiveMainTab('reports');
                    const el = document.getElementById('reports-panel');
                    el?.scrollIntoView({ behavior: 'smooth' });
                  }}
                  className="px-space-md py-space-sm bg-primary text-on-primary hover:bg-navy-deep font-label-md text-label-md rounded-lg shadow-sm flex items-center gap-space-xs transition-colors cursor-pointer"
                >
                  <span className="material-symbols-outlined text-[18px]">description</span>
                  <span>Statutory Reports</span>
                </button>
              </div>
            </div>

            {/* Tabbed Navigation Switcher */}
            <div className="flex items-center gap-space-sm bg-surface-subtle p-space-xs rounded-lg overflow-x-auto">
              <button
                id="tab-audit"
                onClick={() => setActiveMainTab('audit')}
                className={`tab-btn px-space-lg py-space-sm rounded-lg font-title-md text-title-md flex items-center gap-space-xs transition-all cursor-pointer ${
                  activeMainTab === 'audit'
                    ? 'bg-surface-card text-primary shadow-sm font-bold'
                    : 'text-on-surface-variant hover:text-primary hover:bg-surface-card/60'
                }`}
              >
                <span className="material-symbols-outlined text-[18px]">receipt_long</span>
                <span>Audit Trail Ledger</span>
                <span className="px-space-xs py-0.5 rounded-full text-label-sm font-label-sm bg-surface-container text-primary font-mono">
                  {totalEvents}
                </span>
              </button>

              <button
                id="tab-reports"
                onClick={() => {
                  setActiveMainTab('reports');
                  const el = document.getElementById('reports-panel');
                  el?.scrollIntoView({ behavior: 'smooth' });
                }}
                className={`tab-btn px-space-lg py-space-sm rounded-lg font-title-md text-title-md flex items-center gap-space-xs transition-all cursor-pointer ${
                  activeMainTab === 'reports'
                    ? 'bg-surface-card text-primary shadow-sm font-bold'
                    : 'text-on-surface-variant hover:text-primary hover:bg-surface-card/60'
                }`}
              >
                <span className="material-symbols-outlined text-[18px]">assessment</span>
                <span>Statutory AICTE Reports</span>
                <span className="px-space-xs py-0.5 rounded-full text-label-sm font-label-sm bg-status-verified-surface text-status-verified font-semibold">
                  3 Ready
                </span>
              </button>

              <button
                id="tab-security"
                onClick={() => setActiveMainTab('security')}
                className={`tab-btn px-space-lg py-space-sm rounded-lg font-title-md text-title-md flex items-center gap-space-xs transition-all cursor-pointer ${
                  activeMainTab === 'security'
                    ? 'bg-surface-card text-primary shadow-sm font-bold'
                    : 'text-on-surface-variant hover:text-primary hover:bg-surface-card/60'
                }`}
              >
                <span className="material-symbols-outlined text-[18px]">security</span>
                <span>Compliance &amp; DPDP Policy</span>
                <span className="w-2 h-2 rounded-full bg-status-verified"></span>
              </button>
            </div>

            {/* Quick KPI Counters */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-space-md">
              {/* Metric 1 */}
              <div className="bg-surface-card rounded-xl p-space-lg shadow-sm flex flex-col justify-between">
                <div className="flex items-center justify-between">
                  <span className="font-label-md text-label-md text-on-surface-variant">TOTAL AUDIT EVENTS</span>
                  <span className="material-symbols-outlined text-secondary text-[20px]">history_edu</span>
                </div>
                <div className="mt-space-md">
                  <span className="font-display-lg text-display-lg text-primary tracking-tight font-bold">
                    {totalEvents}
                  </span>
                  <div className="flex items-center gap-space-2xs mt-space-xs text-status-verified font-label-sm text-label-sm">
                    <span className="material-symbols-outlined text-[14px]">done</span>
                    <span>Persisted in database</span>
                  </div>
                </div>
              </div>

              {/* Metric 2 */}
              <div className="bg-surface-card rounded-xl p-space-lg shadow-sm flex flex-col justify-between">
                <div className="flex items-center justify-between">
                  <span className="font-label-md text-label-md text-on-surface-variant">SUCCESSFUL ACTIONS</span>
                  <span className="material-symbols-outlined text-status-verified text-[20px]">check_circle</span>
                </div>
                <div className="mt-space-md">
                  <span className="font-display-lg text-display-lg text-status-verified tracking-tight font-bold">
                    {successCount}
                  </span>
                  <div className="flex items-center gap-space-2xs mt-space-xs text-on-surface-variant font-label-sm text-label-sm">
                    <span>In active page query</span>
                  </div>
                </div>
              </div>

              {/* Metric 3 */}
              <div className="bg-surface-card rounded-xl p-space-lg shadow-sm flex flex-col justify-between">
                <div className="flex items-center justify-between">
                  <span className="font-label-md text-label-md text-on-surface-variant">BLOCKED / EXCEPTIONS</span>
                  <span className="material-symbols-outlined text-status-error text-[20px]">block</span>
                </div>
                <div className="mt-space-md">
                  <span className="font-display-lg text-display-lg text-status-error tracking-tight font-bold">
                    {failureCount}
                  </span>
                  <div className="flex items-center gap-space-2xs mt-space-xs text-on-surface-variant font-label-sm text-label-sm">
                    <span>Enforced security stops</span>
                  </div>
                </div>
              </div>

              {/* Metric 4 */}
              <div className="bg-surface-card rounded-xl p-space-lg shadow-sm flex flex-col justify-between">
                <div className="flex items-center justify-between">
                  <span className="font-label-md text-label-md text-on-surface-variant">AUDIT INTEGRITY</span>
                  <span className="material-symbols-outlined text-status-verified text-[20px]">lock</span>
                </div>
                <div className="mt-space-md">
                  <span className="font-display-lg text-display-lg text-primary tracking-tight font-bold">100%</span>
                  <div className="flex items-center gap-space-2xs mt-space-xs text-status-verified font-label-sm text-label-sm">
                    <span className="material-symbols-outlined text-[14px]">security</span>
                    <span>Append-Only Non-Destructive</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Audit Trail Table Panel */}
            {(activeMainTab === 'audit' || activeMainTab === 'reports') && (
              <div className="flex flex-col gap-space-lg" id="panel-audit">
                {/* Advanced Filter Toolbar */}
                <div className="bg-surface-card rounded-xl shadow-sm p-space-lg flex flex-col gap-space-md">
                  <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-space-md">
                    {/* Search input */}
                    <div className="relative flex-1 min-w-[280px]">
                      <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-[18px]">
                        search
                      </span>
                      <input
                        type="text"
                        id="auditSearchInput"
                        value={searchQuery}
                        onChange={(e) => {
                          setSearchQuery(e.target.value);
                          setPage(0);
                        }}
                        placeholder="Search by Action, Batch ID, Actor Email, Object..."
                        className="w-full pl-10 pr-10 py-2 bg-surface-subtle text-on-surface font-body-md text-body-md rounded-lg focus:outline-none focus:bg-surface-card border border-border-subtle"
                      />
                      {searchQuery && (
                        <button
                          onClick={() => {
                            setSearchQuery('');
                            setPage(0);
                          }}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-outline hover:text-on-surface cursor-pointer"
                        >
                          <span className="material-symbols-outlined text-[16px]">close</span>
                        </button>
                      )}
                    </div>

                    {/* Filter Dropdowns */}
                    <div className="flex items-center gap-space-xs flex-wrap">
                      {/* Action Type */}
                      <select
                        aria-label="Filter by Action Type"
                        value={actionFilter}
                        onChange={(e) => {
                          setActionFilter(e.target.value);
                          setPage(0);
                        }}
                        className="bg-surface-subtle text-on-surface font-label-md text-label-md py-2 px-space-sm rounded-lg border border-border-subtle focus:outline-none cursor-pointer"
                      >
                        <option value="ALL">All Actions</option>
                        <option value="IMPORT_UPLOAD">IMPORT_UPLOAD</option>
                        <option value="BATCH_VALIDATE">BATCH_VALIDATE</option>
                        <option value="BATCH_SUBMIT">BATCH_SUBMIT</option>
                        <option value="REVIEW_DECISION">REVIEW_DECISION</option>
                        <option value="BATCH_DELETE">BATCH_DELETE</option>
                        <option value="REPORT_EXPORT">REPORT_EXPORT</option>
                      </select>

                      {/* Outcome */}
                      <select
                        aria-label="Filter by Outcome"
                        value={outcomeFilter}
                        onChange={(e) => {
                          setOutcomeFilter(e.target.value);
                          setPage(0);
                        }}
                        className="bg-surface-subtle text-on-surface font-label-md text-label-md py-2 px-space-sm rounded-lg border border-border-subtle focus:outline-none cursor-pointer"
                      >
                        <option value="ALL">All Outcomes</option>
                        <option value="SUCCESS">SUCCESS</option>
                        <option value="FAILURE">FAILURE</option>
                      </select>

                      <button
                        onClick={handleResetFilters}
                        className="text-secondary hover:underline font-semibold px-2 py-1 text-sm cursor-pointer"
                      >
                        Reset
                      </button>
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-xs text-outline pt-1">
                    <span>Showing page {page + 1} ({auditEvents.length} events, {totalEvents} total matching in database)</span>
                    {initialBatchId && (
                      <span className="font-mono bg-surface-subtle px-2 py-0.5 rounded text-primary border border-border-subtle">
                        Batch Scope: {initialBatchId}
                      </span>
                    )}
                  </div>
                </div>

                {/* Audit Trail Table */}
                <div className="bg-surface-card rounded-xl shadow-sm overflow-hidden flex flex-col">
                  <div className="overflow-x-auto w-full">
                    <table className="w-full text-left border-collapse" id="auditTable">
                      <thead>
                        <tr className="bg-surface-canvas text-outline font-label-sm text-label-sm uppercase tracking-wider border-b border-border-subtle">
                          <th className="py-space-md px-space-lg font-semibold min-w-[140px]">Event ID &amp; Time</th>
                          <th className="py-space-md px-space-md font-semibold min-w-[160px]">Action Type</th>
                          <th className="py-space-md px-space-md font-semibold min-w-[180px]">Actor &amp; Role</th>
                          <th className="py-space-md px-space-md font-semibold min-w-[180px]">Target Resource</th>
                          <th className="py-space-md px-space-md font-semibold min-w-[110px]">Outcome</th>
                          <th className="py-space-md px-space-lg font-semibold min-w-[260px]">Statutory Details</th>
                          <th className="py-space-md px-space-md font-semibold min-w-[100px] text-right">Inspect</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border-subtle text-on-surface font-body-sm text-body-sm">
                        {isLoading ? (
                          <tr>
                            <td colSpan={7} className="py-12 text-center text-outline">
                              <span className="material-symbols-outlined text-3xl animate-spin text-secondary block mb-2">
                                refresh
                              </span>
                              <span>Fetching authoritative audit logs from database...</span>
                            </td>
                          </tr>
                        ) : auditEvents.length === 0 ? (
                          <tr>
                            <td colSpan={7} className="py-12 text-center text-outline">
                              <span className="material-symbols-outlined text-4xl text-outline/50 block mb-2">
                                receipt_long
                              </span>
                              <span className="font-semibold block text-base text-on-surface">No audit events match query</span>
                              <span className="text-xs text-on-surface-variant block mt-1">
                                Adjust filters or search criteria to view recorded audit transactions.
                              </span>
                            </td>
                          </tr>
                        ) : (
                          auditEvents.map((evt) => {
                            const isFailure = evt.outcome === 'FAILURE';
                            return (
                              <tr
                                key={evt.id}
                                className={`transition-colors hover:bg-surface-subtle/80 ${
                                  isFailure ? 'bg-status-error-surface/20' : 'bg-surface-card'
                                }`}
                              >
                                <td className="py-space-md px-space-lg align-top">
                                  <div className="flex flex-col">
                                    <span className="font-code-sm text-code-sm font-bold text-primary">
                                      {evt.id}
                                    </span>
                                    <span className="text-outline text-[11px] mt-0.5">
                                      {new Date(evt.timestamp).toLocaleString('en-IN', {
                                        dateStyle: 'short',
                                        timeStyle: 'medium',
                                      })}
                                    </span>
                                  </div>
                                </td>

                                <td className="py-space-md px-space-md align-top">
                                  <span className="font-code-sm text-code-sm px-space-xs py-0.5 rounded font-semibold bg-surface-subtle text-primary border border-border-subtle inline-block">
                                    {evt.action}
                                  </span>
                                </td>

                                <td className="py-space-md px-space-md align-top">
                                  <div className="flex flex-col">
                                    <span className="font-semibold text-on-surface truncate max-w-[180px]" title={evt.actor_email}>
                                      {evt.actor_email}
                                    </span>
                                    <span className="text-outline text-[11px]">{evt.actor_role}</span>
                                    {evt.institution_id && (
                                      <span className="font-code-sm text-code-sm text-secondary text-[10px]">
                                        Node: {evt.institution_id}
                                      </span>
                                    )}
                                  </div>
                                </td>

                                <td className="py-space-md px-space-md align-top">
                                  <div className="flex flex-col">
                                    <span className="font-semibold text-primary font-code-sm text-code-sm">
                                      {evt.object_type}
                                    </span>
                                    <span className="text-outline text-[11px] truncate max-w-[180px]" title={evt.object_id || ''}>
                                      {evt.object_id || 'N/A'}
                                    </span>
                                  </div>
                                </td>

                                <td className="py-space-md px-space-md align-top">
                                  {isFailure ? (
                                    <span className="inline-flex items-center gap-1 font-label-sm text-label-sm px-space-xs py-0.5 rounded bg-status-error-surface text-status-error font-bold border border-status-error-border">
                                      <span className="material-symbols-outlined text-[13px]">block</span>
                                      FAILURE
                                    </span>
                                  ) : (
                                    <span className="inline-flex items-center gap-1 font-label-sm text-label-sm px-space-xs py-0.5 rounded bg-status-verified-surface text-status-verified font-bold border border-status-verified-border">
                                      <span className="material-symbols-outlined text-[13px]">check_circle</span>
                                      SUCCESS
                                    </span>
                                  )}
                                </td>

                                <td className="py-space-md px-space-lg align-top max-w-sm">
                                  <span className="text-on-surface-variant font-body-sm text-body-sm line-clamp-2" title={evt.details || ''}>
                                    {evt.details || '—'}
                                  </span>
                                </td>

                                <td className="py-space-md px-space-md align-top text-right">
                                  <button
                                    onClick={() => {
                                      setSelectedEvent(evt);
                                      setInspectModalOpen(true);
                                    }}
                                    className="px-2 py-1 text-xs rounded bg-surface-subtle text-primary hover:bg-surface-card border border-border-subtle inline-flex items-center gap-1 cursor-pointer"
                                  >
                                    <span className="material-symbols-outlined text-[14px]">visibility</span>
                                    <span>Inspect</span>
                                  </button>
                                </td>
                              </tr>
                            );
                          })
                        )}
                      </tbody>
                    </table>
                  </div>

                  {/* Pagination Footer */}
                  <div className="p-space-md bg-surface-subtle border-t border-border-subtle flex items-center justify-between">
                    <span className="text-xs text-outline">
                      Total {totalEvents} entries recorded
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setPage((p) => Math.max(0, p - 1))}
                        disabled={page === 0 || isLoading}
                        className="px-3 py-1 bg-surface-card border border-border-subtle rounded text-xs font-semibold hover:bg-surface-subtle disabled:opacity-40 cursor-pointer"
                      >
                        Previous
                      </button>
                      <span className="text-xs font-semibold px-2">Page {page + 1}</span>
                      <button
                        onClick={() => setPage((p) => p + 1)}
                        disabled={(page + 1) * pageSize >= totalEvents || isLoading}
                        className="px-3 py-1 bg-surface-card border border-border-subtle rounded text-xs font-semibold hover:bg-surface-subtle disabled:opacity-40 cursor-pointer"
                      >
                        Next
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Sub-tab 2: Statutory AICTE Reports */}
            <div className="flex flex-col gap-space-lg mt-space-xl" id="reports-panel">
              <div className="flex items-center justify-between flex-wrap gap-space-sm border-b border-border-subtle pb-space-sm">
                <div className="flex flex-col">
                  <div className="flex items-center gap-space-xs">
                    <span className="material-symbols-outlined text-primary text-[22px]">library_books</span>
                    <span className="font-headline-md text-headline-md text-primary font-bold">
                      Pre-Configured Statutory AICTE Regulatory Modules
                    </span>
                  </div>
                  <span className="font-body-sm text-body-sm text-on-surface-variant">
                    Authoritative compliance reports formatted to statutory AICTE data specifications with automatic CSV formula protection.
                  </span>
                </div>
                <span className="font-label-sm text-label-sm bg-surface-container px-space-sm py-1 rounded-lg text-primary font-semibold">
                  AUDITED COMPLIANCE
                </span>
              </div>

              {/* 3 Real Report Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-space-lg">
                {/* Module 1: Intake vs Actual Enrolment */}
                <div className="bg-surface-card rounded-xl p-space-xl shadow-sm border border-border-subtle flex flex-col justify-between">
                  <div className="flex flex-col gap-space-sm">
                    <div className="flex items-start justify-between">
                      <div className="w-10 h-10 rounded-lg bg-surface-subtle flex items-center justify-center text-primary">
                        <span className="material-symbols-outlined text-[22px]">balance</span>
                      </div>
                      <span className="font-code-sm text-code-sm px-space-xs py-0.5 rounded bg-surface-subtle text-primary font-bold border border-border-subtle">
                        ANNEXURE-IV
                      </span>
                    </div>
                    <div>
                      <h3 className="font-headline-sm text-headline-sm text-primary font-bold">
                        Data Quality Summary &amp; Intake Reconciliation
                      </h3>
                      <p className="font-body-sm text-body-sm text-on-surface-variant mt-space-xs">
                        Comprehensive summary of approved intake vs actual enrolled students by programme, detailing regular and supernumerary quota usage.
                      </p>
                    </div>
                  </div>

                  <div className="pt-space-lg mt-space-md border-t border-border-subtle">
                    <button
                      onClick={() => handleExportLedger('quality_summary')}
                      disabled={isExporting}
                      className="w-full py-space-sm px-space-md bg-surface-subtle hover:bg-surface-container text-primary font-label-md text-label-md rounded-lg flex items-center justify-center gap-space-xs transition-colors border border-border-subtle cursor-pointer disabled:opacity-50"
                    >
                      <span className="material-symbols-outlined text-[16px]">file_download</span>
                      <span>Download Reconciliation (.CSV)</span>
                    </button>
                  </div>
                </div>

                {/* Module 2: Validation Findings Dossier */}
                <div className="bg-surface-card rounded-xl p-space-xl shadow-sm border border-border-subtle flex flex-col justify-between">
                  <div className="flex flex-col gap-space-sm">
                    <div className="flex items-start justify-between">
                      <div className="w-10 h-10 rounded-lg bg-surface-subtle flex items-center justify-center text-primary">
                        <span className="material-symbols-outlined text-[22px]">rule</span>
                      </div>
                      <span className="font-code-sm text-code-sm px-space-xs py-0.5 rounded bg-surface-subtle text-primary font-bold border border-border-subtle">
                        ANNEXURE-VII
                      </span>
                    </div>
                    <div>
                      <h3 className="font-headline-sm text-headline-sm text-primary font-bold">
                        Data Quality Findings &amp; Discrepancy Dossier
                      </h3>
                      <p className="font-body-sm text-body-sm text-on-surface-variant mt-space-xs">
                        Full itemized export of blocking errors, warnings, rule codes, affected candidate records, and administrative resolutions.
                      </p>
                    </div>
                  </div>

                  <div className="pt-space-lg mt-space-md border-t border-border-subtle">
                    <button
                      onClick={() => handleExportLedger('findings')}
                      disabled={isExporting}
                      className="w-full py-space-sm px-space-md bg-surface-subtle hover:bg-surface-container text-primary font-label-md text-label-md rounded-lg flex items-center justify-center gap-space-xs transition-colors border border-border-subtle cursor-pointer disabled:opacity-50"
                    >
                      <span className="material-symbols-outlined text-[16px]">file_download</span>
                      <span>Download Findings (.CSV)</span>
                    </button>
                  </div>
                </div>

                {/* Module 3: Full Audit Ledger */}
                <div className="bg-surface-card rounded-xl p-space-xl shadow-sm border border-border-subtle flex flex-col justify-between">
                  <div className="flex flex-col gap-space-sm">
                    <div className="flex items-start justify-between">
                      <div className="w-10 h-10 rounded-lg bg-surface-subtle flex items-center justify-center text-primary">
                        <span className="material-symbols-outlined text-[22px]">receipt_long</span>
                      </div>
                      <span className="font-code-sm text-code-sm px-space-xs py-0.5 rounded bg-surface-subtle text-primary font-bold border border-border-subtle">
                        ANNEXURE-XI
                      </span>
                    </div>
                    <div>
                      <h3 className="font-headline-sm text-headline-sm text-primary font-bold">
                        Authoritative System Audit Ledger Export
                      </h3>
                      <p className="font-body-sm text-body-sm text-on-surface-variant mt-space-xs">
                        Complete append-only audit trail including actor emails, roles, timestamps, batch lifecycle submissions, and reviews.
                      </p>
                    </div>
                  </div>

                  <div className="pt-space-lg mt-space-md border-t border-border-subtle">
                    <button
                      onClick={() => handleExportLedger('audit_logs')}
                      disabled={isExporting}
                      className="w-full py-space-sm px-space-md bg-primary hover:bg-navy-deep text-on-primary font-label-md text-label-md rounded-lg flex items-center justify-center gap-space-xs transition-colors shadow-sm cursor-pointer disabled:opacity-50"
                    >
                      <span className="material-symbols-outlined text-[16px]">file_download</span>
                      <span>Download Audit Log (.CSV)</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Sub-tab 3: Compliance & DPDP Policy */}
            {activeMainTab === 'security' && (
              <div className="bg-surface-card rounded-xl shadow-sm p-space-xl flex flex-col gap-space-md border border-border-subtle">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-headline-sm text-headline-sm text-primary font-bold">
                      Data Protection &amp; DPDP Act 2023 Non-Retention Posture
                    </h3>
                    <p className="font-body-sm text-body-sm text-on-surface-variant">
                      Institutional privacy principles, Aadhaar non-retention compliance, and verifiable student record processing.
                    </p>
                  </div>
                  <span className="px-space-sm py-1 bg-status-verified-surface text-status-verified rounded font-bold text-label-sm flex items-center gap-1">
                    <span className="material-symbols-outlined text-[16px]">verified</span>
                    ACTIVE POLICY
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-space-md mt-space-sm">
                  <div className="bg-surface-subtle p-space-md rounded-lg border border-border-subtle">
                    <span className="text-label-sm text-outline block font-semibold">Aadhaar Non-Retention</span>
                    <span className="text-headline-md font-bold text-status-verified">Zero Bytes</span>
                    <span className="text-[12px] text-outline block mt-1">Zero Aadhaar stored; only APAAR identifiers utilized.</span>
                  </div>
                  <div className="bg-surface-subtle p-space-md rounded-lg border border-border-subtle">
                    <span className="text-label-sm text-outline block font-semibold">Data Masking</span>
                    <span className="text-headline-md font-bold text-primary">Enforced</span>
                    <span className="text-[12px] text-outline block mt-1">Identifiers masked in audit logs and public views.</span>
                  </div>
                  <div className="bg-surface-subtle p-space-md rounded-lg border border-border-subtle">
                    <span className="text-label-sm text-outline block font-semibold">Formula Injection Defense</span>
                    <span className="text-headline-md font-bold text-status-verified">Active</span>
                    <span className="text-[12px] text-status-verified block mt-1">CSV export formula sanitization active on all endpoints.</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Inspection Modal Popup */}
      {inspectModalOpen && selectedEvent && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-space-md animate-fade-in"
        >
          <div className="bg-surface-card rounded-xl shadow-xl max-w-lg w-full p-space-xl flex flex-col gap-space-md transform transition-all border border-border-subtle">
            <div className="flex items-center justify-between border-b border-border-subtle pb-3">
              <div className="flex items-center gap-space-xs">
                <span className="material-symbols-outlined text-primary text-[24px]">receipt_long</span>
                <span className="font-headline-sm text-headline-sm text-primary font-bold">
                  Audit Event Details
                </span>
              </div>
              <button
                onClick={() => setInspectModalOpen(false)}
                className="text-outline hover:text-primary cursor-pointer"
              >
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>

            <div className="bg-surface-subtle p-space-md rounded-lg flex flex-col gap-space-xs text-xs">
              <div className="flex justify-between py-1 border-b border-border-subtle">
                <span className="text-outline font-semibold">Event ID:</span>
                <span className="font-mono font-bold text-primary">{selectedEvent.id}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border-subtle">
                <span className="text-outline font-semibold">Action:</span>
                <span className="font-mono font-bold text-on-surface">{selectedEvent.action}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border-subtle">
                <span className="text-outline font-semibold">Timestamp:</span>
                <span className="font-mono text-on-surface">{new Date(selectedEvent.timestamp).toISOString()}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border-subtle">
                <span className="text-outline font-semibold">Actor:</span>
                <span className="font-mono text-on-surface">{selectedEvent.actor_email} ({selectedEvent.actor_role})</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border-subtle">
                <span className="text-outline font-semibold">Institution Scope:</span>
                <span className="font-mono text-on-surface">{selectedEvent.institution_id || 'Global'}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border-subtle">
                <span className="text-outline font-semibold">Target Entity:</span>
                <span className="font-mono text-on-surface">{selectedEvent.object_type}: {selectedEvent.object_id || 'N/A'}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border-subtle">
                <span className="text-outline font-semibold">Outcome:</span>
                <span className={`font-mono font-bold ${selectedEvent.outcome === 'SUCCESS' ? 'text-status-verified' : 'text-status-error'}`}>
                  {selectedEvent.outcome}
                </span>
              </div>
              <div className="pt-2">
                <span className="text-outline font-semibold block mb-1">Details &amp; Metadata:</span>
                <p className="bg-surface-card p-2 rounded border border-border-subtle font-mono text-[11px] break-words text-on-surface">
                  {selectedEvent.details || 'No additional metadata logged.'}
                </p>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setInspectModalOpen(false)}
                className="px-space-lg py-space-sm bg-primary text-on-primary font-label-md text-label-md rounded-lg hover:bg-navy-deep transition-all cursor-pointer"
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

export default AuditLogsReportsPage;
