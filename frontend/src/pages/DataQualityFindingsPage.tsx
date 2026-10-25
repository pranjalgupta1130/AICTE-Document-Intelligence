import React, { useState, useMemo, useEffect, useCallback } from 'react';
import { AuthSession } from '../types/auth';
import {
  batchService,
  reportService,
  reviewService,
  BatchItem,
  BackendFinding,
} from '../services/api';

interface DataQualityFindingsPageProps {
  session?: AuthSession | null;
  initialBatchId?: string | null;
  onLogout?: () => void;
  onNavigateTab?: (tab: string, batchId?: string) => void;
}

export const DataQualityFindingsPage: React.FC<DataQualityFindingsPageProps> = ({
  session,
  initialBatchId,
  onLogout,
  onNavigateTab,
}) => {
  // Batch and findings state
  const [selectedBatchId, setSelectedBatchId] = useState<string>(initialBatchId || '');
  const [availableBatches, setAvailableBatches] = useState<BatchItem[]>([]);
  const [selectedBatch, setSelectedBatch] = useState<BatchItem | null>(null);
  const [findings, setFindings] = useState<BackendFinding[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [isResolving, setIsResolving] = useState<boolean>(false);

  // Active finding for detail drawer
  const [activeFindingId, setActiveFindingId] = useState<string | null>(null);
  const [auditNote, setAuditNote] = useState<string>('');

  // Filters
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [rulePrefixFilter, setRulePrefixFilter] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState<string>('');

  // Toast notification
  const [toastMessage, setToastMessage] = useState<{ title: string; desc: string; type?: 'SUCCESS' | 'ERROR' | 'INFO' } | null>(null);

  const showToast = (title: string, desc: string, type: 'SUCCESS' | 'ERROR' | 'INFO' = 'SUCCESS') => {
    setToastMessage({ title, desc, type });
    setTimeout(() => {
      setToastMessage(null);
    }, 4500);
  };

  // Determine user role and institution
  const institutionCode = session?.instCode && session.instCode !== 'HQ-STATUTORY-DELHI' ? session.instCode : undefined;

  // Load available batches on mount
  useEffect(() => {
    let isMounted = true;
    const fetchBatches = async () => {
      try {
        const res = await batchService.listBatches({
          institution_id: institutionCode,
          limit: 50,
        });
        if (isMounted) {
          setAvailableBatches(res.items);
          if (res.items.length > 0 && !selectedBatchId) {
            // Default to first batch or initialBatchId
            const defaultId = initialBatchId || res.items[0].id;
            setSelectedBatchId(defaultId);
            const found = res.items.find((b) => b.id === defaultId);
            if (found) setSelectedBatch(found);
          }
        }
      } catch (err: any) {
        console.error('Failed to load batches:', err);
      }
    };
    fetchBatches();
    return () => {
      isMounted = false;
    };
  }, [institutionCode, initialBatchId]);

  // Keep selectedBatch in sync with selectedBatchId
  useEffect(() => {
    if (selectedBatchId && availableBatches.length > 0) {
      const found = availableBatches.find((b) => b.id === selectedBatchId);
      setSelectedBatch(found || null);
    } else if (!selectedBatchId) {
      setSelectedBatch(null);
    }
  }, [selectedBatchId, availableBatches]);

  // Fetch findings based on active filters
  const loadFindings = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await reportService.getFindings({
        batch_id: selectedBatchId || undefined,
        institution_id: institutionCode,
        severity: severityFilter !== 'ALL' ? severityFilter : undefined,
        status: statusFilter !== 'ALL' ? statusFilter : undefined,
        rule_code: rulePrefixFilter !== 'ALL' ? rulePrefixFilter : undefined,
        search: searchTerm.trim() || undefined,
        limit: 150,
      });
      setFindings(res.items);
      // If active finding is not in new list, pick the first one
      if (res.items.length > 0) {
        if (!activeFindingId || !res.items.some((f) => f.id === activeFindingId)) {
          setActiveFindingId(res.items[0].id);
        }
      } else {
        setActiveFindingId(null);
      }
    } catch (err: any) {
      console.error('Failed to load findings:', err);
      showToast('Error', err.message || 'Failed to fetch findings from server', 'ERROR');
    } finally {
      setIsLoading(false);
    }
  }, [selectedBatchId, institutionCode, severityFilter, statusFilter, rulePrefixFilter, searchTerm]);

  useEffect(() => {
    loadFindings();
  }, [loadFindings]);

  // Active finding object
  const activeFinding = useMemo(() => {
    if (!activeFindingId) return null;
    return findings.find((f) => f.id === activeFindingId) || null;
  }, [findings, activeFindingId]);

  // Reset audit note when active finding changes
  useEffect(() => {
    setAuditNote('');
  }, [activeFindingId]);

  // Metrics calculation
  const { totalCount, blockingCount, warningCount, resolvedCount } = useMemo(() => {
    let total = findings.length;
    let blocking = 0;
    let warning = 0;
    let resolved = 0;
    for (const f of findings) {
      if (f.status === 'RESOLVED' || f.status === 'DISMISSED') {
        resolved++;
      } else if (f.severity === 'BLOCKING_ERROR') {
        blocking++;
      } else if (f.severity === 'WARNING') {
        warning++;
      }
    }
    return {
      totalCount: total,
      blockingCount: blocking,
      warningCount: warning,
      resolvedCount: resolved,
    };
  }, [findings]);

  // Handle Finding Resolution
  const handleResolveFinding = async (decision: 'RESOLVED' | 'DISMISSED') => {
    if (!activeFinding) return;
    setIsResolving(true);
    try {
      const reason = auditNote.trim() || `${decision} via institutional quality review workspace`;
      await reviewService.reviewFinding(activeFinding.id, decision, reason);
      showToast(
        decision === 'RESOLVED' ? 'Finding Remediated' : 'Finding Dismissed',
        `Finding ${activeFinding.id} (${activeFinding.rule_code}) recorded into immutable audit trail.`
      );
      setAuditNote('');
      await loadFindings();
    } catch (err: any) {
      console.error('Resolution failed:', err);
      showToast('Action Blocked', err.message || 'Failed to record remediation decision', 'ERROR');
    } finally {
      setIsResolving(false);
    }
  };

  // Export Findings CSV
  const handleExportCSV = async () => {
    setIsExporting(true);
    try {
      await reportService.exportCsvReport({
        report_type: 'findings',
        batch_id: selectedBatchId || undefined,
      });
      showToast('Export Initiated', 'Validation findings CSV downloaded with formula protection.');
    } catch (err: any) {
      console.error('Export failed:', err);
      showToast('Export Failed', err.message || 'Failed to download report', 'ERROR');
    } finally {
      setIsExporting(false);
    }
  };

  // Unique rule codes for filter pills
  const availableRuleCodes = useMemo(() => {
    const set = new Set<string>();
    findings.forEach((f) => set.add(f.rule_code));
    return Array.from(set).sort();
  }, [findings]);

  return (
    <div className="tricolor-slant-bg font-body-md text-on-surface antialiased min-h-screen flex flex-col relative selection:bg-secondary/20">
      {/* Toast Notification */}
      {toastMessage && (
        <div
          className={`fixed bottom-24 right-8 text-on-primary px-space-md py-space-sm rounded-lg shadow-xl flex items-center gap-space-sm z-50 border border-secondary/40 animate-bounce ${
            toastMessage.type === 'ERROR' ? 'bg-status-error' : 'bg-primary'
          }`}
        >
          <span className="material-symbols-outlined text-status-verified text-[22px]">
            {toastMessage.type === 'ERROR' ? 'error' : 'check_circle'}
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
              LIVE PLATFORM
            </span>
          </div>

          <div className="flex items-center gap-space-md">
            <div className="hidden lg:flex items-center gap-space-xs bg-surface-subtle px-space-sm py-space-xs rounded-lg border border-border-subtle">
              <span className="material-symbols-outlined text-outline text-[16px]">
                school
              </span>
              <span className="font-code-sm text-code-sm text-on-surface-variant max-w-[280px] truncate">
                {session?.instCode ? `Node (${session.instCode})` : 'AICTE Central Headquarters'}
              </span>
            </div>

            <div className="flex items-center gap-space-xs pl-space-xs border-l border-border-subtle">
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center font-headline-sm text-headline-sm text-on-primary font-bold shadow-sm">
                <span className="material-symbols-outlined text-on-primary text-[18px]">
                  person
                </span>
              </div>
              <div className="hidden md:flex flex-col">
                <span className="font-label-md text-label-md text-on-surface font-semibold leading-tight">
                  {session?.roleTitle || 'Institutional Officer'}
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
            { id: 'history', label: 'Import History' },
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
                    onNavigateTab(tab.id, selectedBatchId || undefined);
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
              {selectedBatch
                ? `Active Ingestion Batch: ${selectedBatch.id} (${selectedBatch.source_filename}) • Total: ${selectedBatch.total_rows} • Valid: ${selectedBatch.valid_rows} • Errors: ${selectedBatch.error_rows}`
                : 'All Persisted Institutional Batches Scope • Deterministic NAD-AICTE Engine Active'}
            </span>
          </div>
          <div className="hidden sm:flex items-center gap-space-sm shrink-0">
            <span className="font-label-sm text-label-sm text-status-verified font-medium">
              ● Database Synchronized
            </span>
          </div>
        </div>
      </header>

      {/* MAIN CONTAINER */}
      <main className="w-full pt-32 bg-transparent min-h-screen pb-24">
        <div className="flex flex-col w-full">
          {/* Top Sovereign Utility Sub-bar */}
          <section className="w-full bg-transparent px-gutter-md py-space-sm flex flex-wrap items-center justify-between gap-space-md border-b border-border-subtle/60 backdrop-blur-[2px]">
            <div className="flex items-center gap-space-sm flex-wrap">
              <div className="flex items-center gap-space-xs text-primary font-headline-sm text-headline-sm">
                <span className="material-symbols-outlined text-secondary">fact_check</span>
                <span>Reconciliation &amp; Explainable Findings Engine</span>
              </div>
              <span className="text-outline">/</span>

              {/* Batch Selector Dropdown */}
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-outline font-semibold uppercase">Batch:</span>
                <select
                  value={selectedBatchId}
                  onChange={(e) => setSelectedBatchId(e.target.value)}
                  className="font-code-sm text-code-sm bg-surface-card text-on-surface px-space-xs py-1 rounded border border-border-strong focus:outline-none focus:ring-1 focus:ring-secondary cursor-pointer"
                >
                  <option value="">All Batches (Institution Scope)</option>
                  {availableBatches.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.id} ({b.source_filename} - {b.status})
                    </option>
                  ))}
                </select>
              </div>

              {selectedBatch && (
                <span className="font-label-sm text-label-sm px-space-xs py-space-2xs bg-status-review-surface text-status-review rounded font-semibold uppercase tracking-wider border border-status-review-border">
                  Status: {selectedBatch.status}
                </span>
              )}
            </div>

            <div className="flex items-center gap-space-sm flex-wrap">
              <button
                onClick={loadFindings}
                disabled={isLoading}
                className="flex items-center gap-space-xs px-space-sm py-space-xs bg-surface-card text-primary hover:bg-surface-subtle rounded text-label-md font-label-md transition-colors border border-border-subtle cursor-pointer disabled:opacity-50"
              >
                <span className={`material-symbols-outlined text-[16px] ${isLoading ? 'animate-spin' : ''}`}>
                  refresh
                </span>
                <span>Refresh Findings</span>
              </button>

              <button
                onClick={handleExportCSV}
                disabled={isExporting}
                className="flex items-center gap-space-xs px-space-sm py-space-xs bg-secondary text-on-secondary hover:bg-secondary-fixed rounded text-label-md font-label-md transition-colors shadow-sm cursor-pointer disabled:opacity-50"
              >
                <span className="material-symbols-outlined text-[16px]">file_download</span>
                <span>Export Findings (.CSV)</span>
              </button>
            </div>
          </section>

          {/* Main Space */}
          <div className="max-w-7xl mx-auto w-full px-gutter-md py-space-2xl flex flex-col gap-space-2xl">
            {/* Metric Cards Bento */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-space-lg">
              {/* Card 1: Ingested Cohort / Active Batch */}
              <div className="bg-surface-card rounded-xl p-space-xl shadow-sm border border-border-subtle flex flex-col justify-between hover:border-border-strong transition-all">
                <div className="flex items-center justify-between">
                  <span className="font-label-sm text-label-sm text-outline uppercase tracking-wider font-semibold">
                    {selectedBatch ? 'Batch Records' : 'Total Findings'}
                  </span>
                  <span className="material-symbols-outlined text-outline text-[20px]">
                    {selectedBatch ? 'group' : 'data_object'}
                  </span>
                </div>
                <div className="mt-space-lg">
                  <div className="font-display-lg text-display-lg text-primary tracking-tight font-bold">
                    {selectedBatch ? selectedBatch.total_rows.toLocaleString() : totalCount}
                  </div>
                  <div className="font-body-sm text-body-sm text-on-surface-variant mt-space-xs flex items-center gap-space-xs">
                    <span className="w-2 h-2 rounded-full bg-secondary"></span>
                    <span>{selectedBatch ? `${selectedBatch.valid_rows} Valid Rows Persisted` : 'Across active batches'}</span>
                  </div>
                </div>
              </div>

              {/* Card 2: Critical Blocking Errors */}
              <div className="bg-surface-card rounded-xl p-space-xl shadow-sm border border-border-subtle flex flex-col justify-between hover:border-border-strong transition-all">
                <div className="flex items-center justify-between">
                  <span className="font-label-sm text-label-sm text-outline uppercase tracking-wider font-semibold">
                    Critical Blocking Errors
                  </span>
                  <span className="material-symbols-outlined text-status-error text-[20px]">
                    cancel
                  </span>
                </div>
                <div className="mt-space-lg">
                  <div className="flex items-baseline gap-space-sm">
                    <span className="font-display-lg text-display-lg text-status-error tracking-tight font-bold">
                      {blockingCount}
                    </span>
                    <span className="font-label-sm text-label-sm text-status-error font-semibold px-2 py-0.5 rounded bg-status-error-surface border border-status-error-border">
                      Blocks Ingestion
                    </span>
                  </div>
                  <div className="font-body-sm text-body-sm text-outline mt-space-xs">
                    Must be resolved prior to submission
                  </div>
                </div>
              </div>

              {/* Card 3: Non-Blocking Warnings */}
              <div className="bg-surface-card rounded-xl p-space-xl shadow-sm border border-border-subtle flex flex-col justify-between hover:border-border-strong transition-all">
                <div className="flex items-center justify-between">
                  <span className="font-label-sm text-label-sm text-outline uppercase tracking-wider font-semibold">
                    Review Warnings
                  </span>
                  <span className="material-symbols-outlined text-status-review text-[20px]">
                    warning
                  </span>
                </div>
                <div className="mt-space-lg">
                  <div className="flex items-baseline gap-space-sm">
                    <span className="font-display-lg text-display-lg text-status-review tracking-tight font-bold">
                      {warningCount}
                    </span>
                    <span className="font-label-sm text-label-sm text-status-review font-semibold px-2 py-0.5 rounded bg-status-review-surface border border-status-review-border">
                      Provisional
                    </span>
                  </div>
                  <div className="font-body-sm text-body-sm text-outline mt-space-xs">
                    Allowable for submission review
                  </div>
                </div>
              </div>

              {/* Card 4: Resolved / Remediated */}
              <div className="bg-surface-card rounded-xl p-space-xl shadow-sm border border-border-subtle flex flex-col justify-between hover:border-border-strong transition-all">
                <div className="flex items-center justify-between">
                  <span className="font-label-sm text-label-sm text-outline uppercase tracking-wider font-semibold">
                    Resolved Findings
                  </span>
                  <span className="font-headline-sm text-headline-sm text-status-verified font-bold">
                    {resolvedCount}
                  </span>
                </div>
                <div className="mt-space-lg">
                  <div className="w-full bg-surface-subtle h-1.5 rounded-full overflow-hidden">
                    <div
                      className="bg-status-verified h-full rounded-full transition-all"
                      style={{
                        width: `${totalCount > 0 ? Math.min(100, Math.round((resolvedCount / totalCount) * 100)) : 0}%`,
                      }}
                    ></div>
                  </div>
                  <span className="font-body-sm text-body-sm text-outline mt-space-sm block">
                    {totalCount > 0 ? `${Math.round((resolvedCount / totalCount) * 100)}% rectified in audit log` : '0%'}
                  </span>
                </div>
              </div>
            </div>

            {/* Filters & Search Toolbar */}
            <div className="bg-surface-card rounded-xl p-space-lg shadow-sm border border-border-subtle flex flex-col gap-space-lg">
              <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-space-lg">
                {/* Severity & Status Pills */}
                <div className="flex items-center gap-space-xs bg-surface-subtle p-space-2xs rounded-lg overflow-x-auto border border-border-subtle">
                  <button
                    onClick={() => {
                      setSeverityFilter('ALL');
                      setStatusFilter('ALL');
                    }}
                    className={`px-space-md py-space-xs rounded-lg font-label-md text-label-md font-semibold transition-all cursor-pointer ${
                      severityFilter === 'ALL' && statusFilter === 'ALL'
                        ? 'text-primary bg-surface-card shadow-sm'
                        : 'text-on-surface-variant hover:bg-surface-card/60'
                    }`}
                  >
                    All Findings ({totalCount})
                  </button>
                  <button
                    onClick={() => {
                      setSeverityFilter('BLOCKING_ERROR');
                      setStatusFilter('ALL');
                    }}
                    className={`px-space-md py-space-xs rounded-lg font-label-md text-label-md font-semibold transition-all flex items-center gap-space-xs cursor-pointer ${
                      severityFilter === 'BLOCKING_ERROR'
                        ? 'text-status-error bg-surface-card shadow-sm'
                        : 'text-status-error hover:bg-surface-card/60'
                    }`}
                  >
                    <span className="w-2 h-2 rounded-full bg-status-error"></span>
                    <span>Blocking ({blockingCount})</span>
                  </button>
                  <button
                    onClick={() => {
                      setSeverityFilter('WARNING');
                      setStatusFilter('ALL');
                    }}
                    className={`px-space-md py-space-xs rounded-lg font-label-md text-label-md font-semibold transition-all flex items-center gap-space-xs cursor-pointer ${
                      severityFilter === 'WARNING'
                        ? 'text-status-review bg-surface-card shadow-sm'
                        : 'text-status-review hover:bg-surface-card/60'
                    }`}
                  >
                    <span className="w-2 h-2 rounded-full bg-status-review"></span>
                    <span>Warnings ({warningCount})</span>
                  </button>
                  <button
                    onClick={() => {
                      setSeverityFilter('ALL');
                      setStatusFilter('RESOLVED');
                    }}
                    className={`px-space-md py-space-xs rounded-lg font-label-md text-label-md font-semibold transition-all flex items-center gap-space-xs cursor-pointer ${
                      statusFilter === 'RESOLVED'
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
                      placeholder="Search by Rule, Record ID, Row, or Field..."
                      className="w-full pl-9 pr-12 py-space-xs bg-surface-subtle border border-border-subtle rounded-lg text-body-md font-body-md text-on-surface focus:outline-none focus:ring-1 focus:ring-secondary placeholder-outline transition-colors focus:bg-surface-card"
                    />
                    {searchTerm && (
                      <button
                        onClick={() => setSearchTerm('')}
                        className="absolute right-3 top-2.5 text-outline hover:text-on-surface cursor-pointer"
                      >
                        <span className="material-symbols-outlined text-[16px]">close</span>
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* Dynamic Rule Filter Pills */}
              {availableRuleCodes.length > 0 && (
                <div className="flex items-center gap-space-sm flex-wrap border-t border-border-subtle pt-space-md">
                  <span className="font-label-sm text-label-sm text-outline uppercase font-semibold mr-space-xs">
                    Rule Codes:
                  </span>
                  {availableRuleCodes.map((rc) => (
                    <button
                      key={rc}
                      onClick={() => setRulePrefixFilter((prev) => (prev === rc ? 'ALL' : rc))}
                      className={`px-space-sm py-space-xs rounded-full font-code-sm text-code-sm transition-colors cursor-pointer border ${
                        rulePrefixFilter === rc
                          ? 'bg-primary text-white border-primary'
                          : 'bg-surface-subtle text-on-surface-variant border-border-subtle hover:text-primary hover:bg-surface-container-high'
                      }`}
                    >
                      {rc}
                    </button>
                  ))}
                  <button
                    onClick={() => {
                      setSeverityFilter('ALL');
                      setStatusFilter('ALL');
                      setRulePrefixFilter('ALL');
                      setSearchTerm('');
                    }}
                    className="font-label-sm text-label-sm text-secondary hover:underline ml-auto font-medium cursor-pointer"
                  >
                    Reset Filters
                  </button>
                </div>
              )}
            </div>

            {/* Split Workspace: Left Findings Table + Right Rectification Drawer */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-space-xl items-start">
              {/* Left Column (8 Cols): Findings Table */}
              <div className="lg:col-span-8 flex flex-col gap-space-xl">
                <div className="bg-surface-card rounded-xl shadow-sm border border-border-subtle overflow-hidden flex flex-col">
                  <div className="px-space-xl py-space-md bg-surface-card border-b border-border-subtle flex items-center justify-between">
                    <div className="flex items-center gap-space-md">
                      <span className="font-headline-sm text-headline-sm text-primary font-bold">
                        Persisted Validation Discrepancies
                      </span>
                      <span className="font-label-sm text-label-sm bg-surface-subtle text-on-surface-variant px-space-sm py-0.5 rounded-full font-medium border border-border-subtle">
                        {findings.length} Listed
                      </span>
                    </div>
                    <div className="flex items-center gap-space-xs text-outline font-label-sm text-label-sm">
                      <span className="material-symbols-outlined text-[16px] text-status-verified">
                        verified_user
                      </span>
                      <span>Authoritative Backend Audit</span>
                    </div>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left">
                      <thead>
                        <tr className="bg-surface-subtle/50 text-outline font-label-sm text-label-sm uppercase tracking-wider border-b border-border-subtle">
                          <th className="py-space-md px-space-xl w-16">Row</th>
                          <th className="py-space-md px-space-lg">Candidate / Record</th>
                          <th className="py-space-md px-space-lg">Rule &amp; Severity</th>
                          <th className="py-space-md px-space-lg">Field &amp; Cause</th>
                          <th className="py-space-md px-space-lg text-right">Status / Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border-subtle font-body-sm text-body-sm">
                        {isLoading ? (
                          <tr>
                            <td colSpan={5} className="py-12 text-center text-outline">
                              <span className="material-symbols-outlined text-3xl animate-spin text-secondary block mb-2">
                                refresh
                              </span>
                              <span>Loading authoritative findings from database...</span>
                            </td>
                          </tr>
                        ) : findings.length === 0 ? (
                          <tr>
                            <td colSpan={5} className="py-12 text-center text-outline">
                              <span className="material-symbols-outlined text-4xl text-outline/50 block mb-2">
                                task_alt
                              </span>
                              <span className="font-semibold block text-base text-on-surface">
                                No discrepancies match the active filters
                              </span>
                              <span className="text-xs text-on-surface-variant block mt-1">
                                {selectedBatch
                                  ? `Batch ${selectedBatch.id} has no outstanding findings for the selected filter criteria.`
                                  : 'Select another batch or reset filters to view findings.'}
                              </span>
                            </td>
                          </tr>
                        ) : (
                          findings.map((item) => {
                            const isSelected = item.id === activeFindingId;
                            const isBlocking = item.severity === 'BLOCKING_ERROR';
                            const isWarning = item.severity === 'WARNING';
                            const isResolved = item.status === 'RESOLVED' || item.status === 'DISMISSED';

                            return (
                              <tr
                                key={item.id}
                                onClick={() => setActiveFindingId(item.id)}
                                className={`transition-colors cursor-pointer ${
                                  isSelected
                                    ? 'ring-2 ring-secondary bg-surface-subtle'
                                    : isResolved
                                    ? 'bg-status-verified-surface/20 hover:bg-status-verified-surface/40'
                                    : isBlocking
                                    ? 'bg-status-error-surface/10 hover:bg-status-error-surface/25'
                                    : 'hover:bg-surface-subtle/30'
                                }`}
                              >
                                <td className="py-space-lg px-space-xl font-code-sm text-code-sm font-semibold text-outline">
                                  {item.row_number ? `#${item.row_number}` : '—'}
                                </td>
                                <td className="py-space-lg px-space-lg">
                                  <div className="flex flex-col">
                                    <span className="font-code-sm text-code-sm font-bold text-primary">
                                      {item.record_id || item.batch_id}
                                    </span>
                                    <span className="font-body-sm text-body-sm text-outline mt-0.5">
                                      Batch: {item.batch_id}
                                    </span>
                                  </div>
                                </td>
                                <td className="py-space-lg px-space-lg">
                                  <div className="flex flex-col gap-space-xs items-start">
                                    {isResolved && (
                                      <span className="inline-flex items-center gap-1 font-label-sm text-label-sm px-space-xs py-0.5 rounded-md bg-status-verified-surface text-status-verified font-bold border border-status-verified-border">
                                        <span className="material-symbols-outlined text-[13px]">
                                          check_circle
                                        </span>
                                        {item.status}
                                      </span>
                                    )}
                                    {!isResolved && isBlocking && (
                                      <span className="inline-flex items-center gap-1 font-label-sm text-label-sm px-space-xs py-0.5 rounded-md bg-status-error-surface text-status-error font-semibold border border-status-error-border">
                                        <span className="material-symbols-outlined text-[13px]">
                                          cancel
                                        </span>
                                        BLOCKING
                                      </span>
                                    )}
                                    {!isResolved && isWarning && (
                                      <span className="inline-flex items-center gap-1 font-label-sm text-label-sm px-space-xs py-0.5 rounded-md bg-status-review-surface text-status-review font-semibold border border-status-review-border">
                                        <span className="material-symbols-outlined text-[13px]">
                                          warning
                                        </span>
                                        WARNING
                                      </span>
                                    )}
                                    <span className="font-code-sm text-code-sm text-on-surface-variant">
                                      {item.rule_code}
                                    </span>
                                  </div>
                                </td>
                                <td className="py-space-lg px-space-lg max-w-xs">
                                  <div className="flex flex-col gap-0.5">
                                    <span className="font-code-sm text-code-sm font-semibold text-primary">
                                      {item.field_name || 'record'}
                                    </span>
                                    <span className="text-on-surface-variant font-body-sm text-body-sm line-clamp-2" title={item.message}>
                                      {item.message}
                                    </span>
                                  </div>
                                </td>
                                <td className="py-space-lg px-space-lg text-right">
                                  {isResolved ? (
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
                                        setActiveFindingId(item.id);
                                      }}
                                      className={`px-space-md py-space-xs rounded-lg text-label-md font-label-md transition-colors shadow-sm inline-flex items-center gap-1.5 cursor-pointer ${
                                        isBlocking
                                          ? 'bg-primary text-on-primary hover:bg-navy-deep'
                                          : 'bg-surface-subtle text-primary hover:bg-surface-container-high border border-border-subtle'
                                      }`}
                                    >
                                      <span className="material-symbols-outlined text-[15px]">
                                        edit
                                      </span>
                                      <span>{isBlocking ? 'Remediate' : 'Review'}</span>
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
                      Showing {findings.length} findings for active query
                    </span>
                    <div className="flex items-center gap-space-xs">
                      <span className="font-code-sm text-code-sm text-on-surface">
                        Deterministic Rules Engine v2.4
                      </span>
                    </div>
                  </div>
                </div>

                {/* Rule Specifications & Architecture Panel */}
                <div className="bg-surface-card rounded-xl p-space-xl shadow-sm border border-border-subtle">
                  <div className="flex items-center justify-between mb-space-md">
                    <span className="font-headline-sm text-headline-sm text-primary font-bold flex items-center gap-space-xs">
                      <span className="material-symbols-outlined text-secondary text-[20px]">
                        menu_book
                      </span>
                      <span>National Academic Rule Specifications</span>
                    </span>
                    <span className="font-label-sm text-label-sm text-outline font-code-sm">
                      AICTE/NAD-2026 Mandate
                    </span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-space-md">
                    <div className="p-space-md rounded-lg border border-border-subtle bg-surface-subtle/30">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-code-sm text-code-sm font-bold text-primary">
                          APAAR Identifier Rules
                        </span>
                        <span className="font-label-sm text-label-sm text-status-error font-bold">
                          Blocking
                        </span>
                      </div>
                      <p className="text-on-surface-variant font-body-sm text-body-sm">
                        Syntax validation (12 digits, Verhoeff checksum) and intra-batch uniqueness. Missing or invalid APAAR blocks submission.
                      </p>
                    </div>

                    <div className="p-space-md rounded-lg border border-border-subtle bg-surface-subtle/30">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-code-sm text-code-sm font-bold text-primary">
                          Approved Intake Ceilings
                        </span>
                        <span className="font-label-sm text-label-sm text-status-error font-bold">
                          Blocking
                        </span>
                      </div>
                      <p className="text-on-surface-variant font-body-sm text-body-sm">
                        Enrolment cannot breach sanctioned regular and supernumerary quotas without official AICTE variation approvals.
                      </p>
                    </div>

                    <div className="p-space-md rounded-lg border border-border-subtle bg-surface-subtle/30">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-code-sm text-code-sm font-bold text-primary">
                          Cross-Match &amp; Gateway
                        </span>
                        <span className="font-label-sm text-label-sm text-status-review font-bold">
                          Warning
                        </span>
                      </div>
                      <p className="text-on-surface-variant font-body-sm text-body-sm">
                        Cross-institutional collision flags and gateway availability probes require institutional documentation or clerical review.
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
                          Finding Inspection
                        </span>
                        <span className="font-body-sm text-body-sm text-outline">
                          {activeFinding
                            ? `Row ${activeFinding.row_number || 'N/A'} • ${activeFinding.rule_code}`
                            : 'Select a finding to inspect'}
                        </span>
                      </div>
                    </div>
                    <span className="font-code-sm text-code-sm bg-surface-subtle text-on-surface-variant px-space-xs py-1 rounded border border-border-subtle">
                      AUDIT
                    </span>
                  </div>

                  {activeFinding ? (
                    <div className="p-space-xl flex flex-col gap-space-lg">
                      {/* Finding Metadata Card */}
                      <div className="p-space-md bg-surface-subtle/60 rounded-xl border border-border-subtle flex flex-col gap-space-xs">
                        <div className="flex items-center justify-between">
                          <span className="font-label-sm text-label-sm text-outline uppercase font-semibold">
                            Finding ID
                          </span>
                          <span className="font-code-sm text-code-sm font-bold text-primary">
                            {activeFinding.id}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="font-label-sm text-label-sm text-outline uppercase font-semibold">
                            Affected Field
                          </span>
                          <span className="font-code-sm text-code-sm font-semibold text-on-surface">
                            {activeFinding.field_name || 'Record-level'}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="font-label-sm text-label-sm text-outline uppercase font-semibold">
                            Rule Code
                          </span>
                          <span className="font-code-sm text-code-sm font-bold text-primary">
                            {activeFinding.rule_code}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="font-label-sm text-label-sm text-outline uppercase font-semibold">
                            Severity
                          </span>
                          <span
                            className={`font-label-sm text-label-sm font-bold px-2 py-0.5 rounded ${
                              activeFinding.severity === 'BLOCKING_ERROR'
                                ? 'bg-status-error-surface text-status-error'
                                : 'bg-status-review-surface text-status-review'
                            }`}
                          >
                            {activeFinding.severity}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="font-label-sm text-label-sm text-outline uppercase font-semibold">
                            Status
                          </span>
                          <span className="font-label-sm text-label-sm font-bold text-status-verified">
                            {activeFinding.status}
                          </span>
                        </div>
                      </div>

                      {/* Explanation & Suggested Action */}
                      <div
                        className={`p-space-md rounded-xl border flex flex-col gap-space-xs ${
                          activeFinding.severity === 'BLOCKING_ERROR'
                            ? 'bg-status-error-surface/40 border-status-error-border'
                            : 'bg-status-review-surface/40 border-status-review-border'
                        }`}
                      >
                        <div
                          className={`flex items-center gap-1.5 font-label-md text-label-md font-bold ${
                            activeFinding.severity === 'BLOCKING_ERROR'
                              ? 'text-status-error'
                              : 'text-status-review'
                          }`}
                        >
                          <span className="material-symbols-outlined text-[16px]">info</span>
                          <span>Explanation:</span>
                        </div>
                        <p className="font-body-sm text-body-sm text-on-surface">
                          {activeFinding.message}
                        </p>
                        {activeFinding.suggested_action && (
                          <div className="bg-surface-card p-space-sm rounded-lg border border-border-subtle mt-1 text-label-sm font-label-sm">
                            <span className="text-outline block font-semibold">Recommended Corrective Action:</span>
                            <span className="text-primary font-medium mt-0.5 block">
                              {activeFinding.suggested_action}
                            </span>
                          </div>
                        )}
                        {(activeFinding.expected_value || activeFinding.actual_value) && (
                          <div className="grid grid-cols-2 gap-2 mt-1 text-xs font-mono">
                            <div className="bg-surface-card p-2 rounded border border-border-subtle">
                              <span className="text-outline block text-[10px] uppercase font-sans">Expected:</span>
                              <span className="text-status-verified font-bold">{activeFinding.expected_value || 'Valid value'}</span>
                            </div>
                            <div className="bg-surface-card p-2 rounded border border-border-subtle">
                              <span className="text-outline block text-[10px] uppercase font-sans">Observed:</span>
                              <span className="text-status-error font-bold">{activeFinding.actual_value || 'None'}</span>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Regulatory Notice on In-Place Rectification */}
                      <div className="bg-surface-subtle p-3 rounded-lg border border-border-subtle text-xs text-on-surface-variant flex items-start gap-2">
                        <span className="material-symbols-outlined text-secondary text-base shrink-0 mt-0.5">
                          policy
                        </span>
                        <div>
                          <span className="font-semibold text-primary block">Data Rectification Mandate:</span>
                          To permanently correct student records, modify your source CSV and re-upload via Bulk Import &amp; Validation. To resolve explainable discrepancies with administrative justification, submit a signed audit decision below.
                        </div>
                      </div>

                      {/* Audit Justification Input */}
                      {activeFinding.status === 'OPEN' && (
                        <div className="flex flex-col gap-space-xs">
                          <label
                            className="font-label-md text-label-md text-on-surface-variant font-semibold"
                            htmlFor="auditNote"
                          >
                            Audit Trail Justification / Document Reference
                          </label>
                          <textarea
                            id="auditNote"
                            rows={3}
                            value={auditNote}
                            onChange={(e) => setAuditNote(e.target.value)}
                            placeholder="Enter administrative justification, affidavit reference, or reason for remediation..."
                            className="w-full p-space-sm bg-surface-card border border-border-subtle rounded-lg text-body-sm font-body-sm text-on-surface focus:outline-none focus:ring-1 focus:ring-secondary placeholder-outline"
                          />
                        </div>
                      )}

                      {/* Drawer Action Buttons */}
                      {activeFinding.status === 'OPEN' ? (
                        <div className="flex flex-col gap-space-sm pt-space-xs">
                          <button
                            onClick={() => handleResolveFinding('RESOLVED')}
                            disabled={isResolving}
                            className="w-full py-space-sm px-space-md bg-primary text-on-primary rounded-lg font-title-md text-title-md font-semibold hover:bg-navy-deep disabled:opacity-50 transition-all shadow-sm flex items-center justify-center gap-space-xs cursor-pointer"
                          >
                            <span className={`material-symbols-outlined text-[18px] ${isResolving ? 'animate-spin' : ''}`}>
                              {isResolving ? 'hourglass_top' : 'check_circle'}
                            </span>
                            <span>{isResolving ? 'Recording...' : 'Mark as Remediated'}</span>
                          </button>

                          <button
                            onClick={() => handleResolveFinding('DISMISSED')}
                            disabled={isResolving}
                            className="w-full py-space-xs px-space-md bg-surface-subtle text-primary hover:bg-surface-container-high rounded-lg font-label-md text-label-md transition-colors flex items-center justify-center gap-space-xs border border-border-subtle cursor-pointer disabled:opacity-50"
                          >
                            <span className="material-symbols-outlined text-[16px]">
                              rule_folder
                            </span>
                            <span>Dismiss with Administrative Note</span>
                          </button>
                        </div>
                      ) : (
                        <div className="p-3 bg-status-verified-surface rounded-lg border border-status-verified-border text-center text-status-verified font-semibold text-sm flex items-center justify-center gap-2">
                          <span className="material-symbols-outlined text-[18px]">verified</span>
                          <span>Finding marked as {activeFinding.status}</span>
                        </div>
                      )}

                      {/* Cross Page Navigation in Drawer */}
                      <div className="pt-space-sm border-t border-border-subtle flex flex-col gap-2">
                        <span className="text-xs text-outline font-semibold uppercase">Cross-Page Navigation:</span>
                        <div className="grid grid-cols-2 gap-2">
                          <button
                            onClick={() => onNavigateTab?.('import', activeFinding.batch_id)}
                            className="px-2 py-1.5 text-xs font-semibold rounded bg-surface-subtle text-primary hover:bg-surface-card border border-border-subtle text-left truncate flex items-center gap-1 cursor-pointer"
                          >
                            <span className="material-symbols-outlined text-[14px]">upload_file</span>
                            <span>Ingestion Page</span>
                          </button>
                          <button
                            onClick={() => onNavigateTab?.('history', activeFinding.batch_id)}
                            className="px-2 py-1.5 text-xs font-semibold rounded bg-surface-subtle text-primary hover:bg-surface-card border border-border-subtle text-left truncate flex items-center gap-1 cursor-pointer"
                          >
                            <span className="material-symbols-outlined text-[14px]">history</span>
                            <span>Import History</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="p-12 text-center text-outline">
                      <span className="material-symbols-outlined text-4xl block mb-2 text-outline/40">
                        find_in_page
                      </span>
                      <span>Select a discrepancy row on the left to inspect root-cause analysis and execute remediation.</span>
                    </div>
                  )}
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
            <div
              className={`w-9 h-9 rounded flex items-center justify-center flex-shrink-0 ${
                blockingCount > 0
                  ? 'bg-status-error-surface text-status-error'
                  : 'bg-status-verified-surface text-status-verified'
              }`}
            >
              <span className="material-symbols-outlined text-[22px]">
                {blockingCount > 0 ? 'gavel' : 'verified'}
              </span>
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-space-xs">
                <span className="font-title-md text-title-md text-primary font-bold">
                  {blockingCount > 0
                    ? `${blockingCount} Blocking Errors Active`
                    : 'Zero Blocking Errors Active'}
                </span>
                <span
                  className={`font-label-sm text-label-sm px-1.5 py-0.5 rounded font-semibold ${
                    blockingCount > 0
                      ? 'bg-status-error-surface text-status-error'
                      : 'bg-status-verified-surface text-status-verified'
                  }`}
                >
                  {blockingCount > 0 ? 'Strict Regulatory Block' : 'Ready for Final Submission'}
                </span>
              </div>
              <span className="font-body-sm text-body-sm text-on-surface-variant">
                {blockingCount > 0
                  ? 'All blocking errors must be rectified in source data or resolved before final batch submission to AICTE.'
                  : 'All student records in active batch conform to AICTE statutory intake and identifier policies.'}
              </span>
            </div>
          </div>

          {/* Right Action CTAs */}
          <div className="flex items-center gap-space-sm w-full md:w-auto justify-end flex-wrap">
            <button
              onClick={handleExportCSV}
              disabled={isExporting}
              className="px-space-md py-space-sm bg-surface-subtle text-primary hover:bg-surface-container-high rounded font-title-md text-title-md font-semibold transition-colors flex items-center gap-space-xs border border-border-subtle cursor-pointer disabled:opacity-50"
            >
              <span className="material-symbols-outlined text-[18px]">file_download</span>
              <span>Export CSV</span>
            </button>

            <button
              onClick={() => onNavigateTab?.('import', selectedBatchId || undefined)}
              className="px-space-md py-space-sm bg-surface-subtle text-primary hover:bg-surface-container-high rounded font-title-md text-title-md font-semibold transition-colors flex items-center gap-space-xs border border-border-subtle cursor-pointer"
            >
              <span className="material-symbols-outlined text-[18px]">upload_file</span>
              <span>Open Bulk Ingestion</span>
            </button>

            <button
              onClick={() => onNavigateTab?.('reports', selectedBatchId || undefined)}
              className="px-space-md py-space-sm bg-surface-subtle text-primary hover:bg-surface-container-high rounded font-title-md text-title-md font-semibold transition-colors flex items-center gap-space-xs border border-border-subtle cursor-pointer"
            >
              <span className="material-symbols-outlined text-[18px]">receipt_long</span>
              <span>Audit Logs</span>
            </button>

            {selectedBatch && (selectedBatch.status === 'VALIDATED' || selectedBatch.status === 'DRAFT') && (
              <button
                disabled={blockingCount > 0}
                onClick={async () => {
                  try {
                    await batchService.submitBatch(selectedBatch.id, true);
                    showToast('Submission Complete', `Batch ${selectedBatch.id} locked and submitted to Central Review.`);
                    await loadFindings();
                  } catch (err: any) {
                    showToast('Submission Rejected', err.message || 'Cannot submit batch', 'ERROR');
                  }
                }}
                title={
                  blockingCount > 0
                    ? `Resolve ${blockingCount} blocking errors to unlock submission`
                    : 'Submit batch to Central Review'
                }
                className={`px-space-lg py-space-sm rounded font-headline-sm text-headline-sm font-semibold transition-all flex items-center gap-space-xs shadow-sm cursor-pointer ${
                  blockingCount > 0
                    ? 'bg-primary text-on-primary opacity-40 cursor-not-allowed'
                    : 'bg-status-verified text-white hover:bg-status-verified/90'
                }`}
              >
                <span className="material-symbols-outlined text-[20px]">cloud_upload</span>
                <span>Submit to AICTE Central Review</span>
              </button>
            )}
          </div>
        </div>
      </footer>
    </div>
  );
};

export default DataQualityFindingsPage;
