import React, { useState, useEffect, useMemo } from 'react';
import { AuthSession } from '../types/auth';
import {
  batchService,
  institutionService,
  BatchItem,
  StudentRecordItem,
  BackendFinding,
  BatchHistoryEvent,
  InstitutionItem,
} from '../services/api';

interface ImportHistoryPageProps {
  session?: AuthSession | null;
  onLogout?: () => void;
  onNavigateTab?: (tab: string, batchId?: string) => void;
  initialSelectedBatchId?: string | null;
}

export const ImportHistoryPage: React.FC<ImportHistoryPageProps> = ({
  session,
  onLogout,
  onNavigateTab,
  initialSelectedBatchId,
}) => {
  // Navigation & session state
  const isAdministrativeUser = useMemo(() => {
    const roleKey = session?.role;
    const roleTitle = (session?.roleTitle || '').toUpperCase();
    return (
      roleKey === 'reviewer' ||
      roleKey === 'evaluator' ||
      roleTitle.includes('AICTE') ||
      roleTitle.includes('DEMO') ||
      roleTitle.includes('EVALUATOR') ||
      roleTitle.includes('REVIEWER')
    );
  }, [session?.role, session?.roleTitle]);

  // Toast notification
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // List batches state
  const [batches, setBatches] = useState<BatchItem[]>([]);
  const [totalBatches, setTotalBatches] = useState<number>(0);
  const [isLoadingBatches, setIsLoadingBatches] = useState<boolean>(true);
  const [batchesError, setBatchesError] = useState<string | null>(null);

  // Filters state
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [filterAcademicYear, setFilterAcademicYear] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [filterInstitutionId, setFilterInstitutionId] = useState<string>('');
  const [institutionsList, setInstitutionsList] = useState<InstitutionItem[]>([]);
  const [pageSize, setPageSize] = useState<number>(10);
  const [currentPage, setCurrentPage] = useState<number>(1);

  // Selected Batch Inspection state
  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(initialSelectedBatchId || null);
  const [selectedBatch, setSelectedBatch] = useState<BatchItem | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState<boolean>(false);
  const [detailTab, setDetailTab] = useState<'overview' | 'records' | 'findings' | 'history'>('overview');

  // Batch records tab state
  const [batchRecords, setBatchRecords] = useState<StudentRecordItem[]>([]);
  const [recordsTotal, setRecordsTotal] = useState<number>(0);
  const [recordsSearch, setRecordsSearch] = useState<string>('');
  const [recordsPage, setRecordsPage] = useState<number>(1);
  const [isLoadingRecords, setIsLoadingRecords] = useState<boolean>(false);

  // Batch findings tab state
  const [findingsList, setFindingsList] = useState<BackendFinding[]>([]);
  const [findingsTotal, setFindingsTotal] = useState<number>(0);
  const [findingsSeverity, setFindingsSeverity] = useState<string>('');
  const [findingsPage, setFindingsPage] = useState<number>(1);
  const [isLoadingFindings, setIsLoadingFindings] = useState<boolean>(false);

  // Batch history tab state
  const [historyEvents, setHistoryEvents] = useState<BatchHistoryEvent[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState<boolean>(false);

  // Deletion modal state
  const [batchToDelete, setBatchToDelete] = useState<BatchItem | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Load institutions list for administrative filter dropdown
  useEffect(() => {
    if (isAdministrativeUser) {
      institutionService
        .listInstitutions()
        .then((res) => setInstitutionsList(res.items || []))
        .catch(() => setInstitutionsList([]));
    }
  }, [isAdministrativeUser]);

  // Load batches function
  const fetchBatches = () => {
    setIsLoadingBatches(true);
    setBatchesError(null);

    const offset = (currentPage - 1) * pageSize;
    batchService
      .listBatches({
        institution_id: isAdministrativeUser ? filterInstitutionId || undefined : undefined,
        academic_year: filterAcademicYear || undefined,
        status: filterStatus || undefined,
        search: searchQuery.trim() || undefined,
        limit: pageSize,
        offset,
      })
      .then((res) => {
        setBatches(res.items || []);
        setTotalBatches(res.total || 0);
      })
      .catch((err) => {
        setBatchesError(err.message || 'Failed to load import batches.');
      })
      .finally(() => {
        setIsLoadingBatches(false);
      });
  };

  useEffect(() => {
    fetchBatches();
  }, [currentPage, pageSize, filterAcademicYear, filterStatus, filterInstitutionId]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
    fetchBatches();
  };

  // Load selected batch details
  useEffect(() => {
    if (!selectedBatchId) {
      setSelectedBatch(null);
      return;
    }

    setIsLoadingDetail(true);
    batchService
      .getBatch(selectedBatchId)
      .then((b) => {
        setSelectedBatch(b);
      })
      .catch((err) => {
        showToast(`Error: ${err.message}`);
        setSelectedBatch(null);
      })
      .finally(() => {
        setIsLoadingDetail(false);
      });
  }, [selectedBatchId]);

  // Load sub-tab data when active
  useEffect(() => {
    if (!selectedBatchId) return;

    if (detailTab === 'records') {
      setIsLoadingRecords(true);
      const offset = (recordsPage - 1) * 10;
      batchService
        .getBatchRecords(selectedBatchId, {
          search: recordsSearch.trim() || undefined,
          limit: 10,
          offset,
        })
        .then((res) => {
          setBatchRecords(res.items || []);
          setRecordsTotal(res.total || 0);
        })
        .catch((err) => showToast(`Failed to load records: ${err.message}`))
        .finally(() => setIsLoadingRecords(false));
    } else if (detailTab === 'findings') {
      setIsLoadingFindings(true);
      const offset = (findingsPage - 1) * 10;
      batchService
        .getBatchFindings(selectedBatchId, 10, offset, findingsSeverity || undefined)
        .then((res) => {
          setFindingsList(res.items || []);
          setFindingsTotal(res.total || 0);
        })
        .catch((err) => showToast(`Failed to load findings: ${err.message}`))
        .finally(() => setIsLoadingFindings(false));
    } else if (detailTab === 'history') {
      setIsLoadingHistory(true);
      batchService
        .getBatchHistory(selectedBatchId)
        .then((evts) => setHistoryEvents(evts || []))
        .catch((err) => showToast(`Failed to load history: ${err.message}`))
        .finally(() => setIsLoadingHistory(false));
    }
  }, [selectedBatchId, detailTab, recordsPage, recordsSearch, findingsPage, findingsSeverity]);

  // File Download Handler
  const handleDownloadOriginal = async (batch: BatchItem) => {
    if (!batch.has_original_file) {
      showToast('Original file unavailable — this document was not retained by the system.');
      return;
    }
    try {
      showToast(`Initiating secure download for ${batch.source_filename}...`);
      await batchService.downloadOriginalFile(batch.id, batch.source_filename);
      showToast(`Downloaded ${batch.source_filename}`);
    } catch (err: any) {
      showToast(`Download failed: ${err.message}`);
    }
  };

  // Deletion execution
  const handleConfirmDelete = async () => {
    if (!batchToDelete) return;
    setIsDeleting(true);
    setDeleteError(null);

    try {
      await batchService.deleteBatch(batchToDelete.id);
      showToast(`Batch ${batchToDelete.id} successfully deleted.`);
      setBatchToDelete(null);
      if (selectedBatchId === batchToDelete.id) {
        setSelectedBatchId(null);
        setSelectedBatch(null);
      }
      fetchBatches();
    } catch (err: any) {
      setDeleteError(err.message || 'Failed to delete dataset.');
    } finally {
      setIsDeleting(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'ACCEPTED':
      case 'VALIDATED':
        return 'bg-status-verified-surface text-status-verified border-status-verified-border';
      case 'SUBMITTED':
      case 'UNDER_REVIEW':
        return 'bg-status-review-surface text-status-review border-status-review-border';
      case 'NEEDS_CORRECTION':
      case 'REJECTED':
        return 'bg-status-error-surface text-status-error border-status-error-border';
      case 'DRAFT':
      default:
        return 'bg-surface-subtle text-primary border-border-subtle';
    }
  };

  return (
    <div className="tricolor-slant-bg font-body-md text-on-surface antialiased min-h-screen flex flex-col relative selection:bg-secondary/20">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-primary text-on-primary px-space-md py-space-sm rounded-lg shadow-xl font-body-sm text-body-sm flex items-center gap-space-xs border border-secondary/40 animate-bounce">
          <span className="material-symbols-outlined text-status-verified text-[18px]">verified</span>
          <span>{toastMessage}</span>
          <button onClick={() => setToastMessage(null)} className="ml-2 text-white/60 hover:text-white">
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
              DATASET REPOSITORY
            </span>
          </div>

          <div className="flex items-center gap-space-md">
            <div className="hidden lg:flex items-center gap-space-xs bg-surface-subtle px-space-sm py-space-xs rounded-lg border border-border-subtle">
              <span className="material-symbols-outlined text-outline text-[16px]">domain</span>
              <span className="font-code-sm text-code-sm text-on-surface-variant max-w-[280px] truncate">
                {session?.instCode ? `Node (${session.instCode})` : 'Apex Institute of Technology'}
              </span>
            </div>

            <div className="flex items-center gap-space-xs pl-space-xs border-l border-border-subtle">
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center font-headline-sm text-headline-sm text-on-primary font-bold shadow-sm">
                <span className="material-symbols-outlined text-on-primary text-[18px]">person</span>
              </div>
              <div className="hidden md:flex flex-col">
                <span className="font-label-md text-label-md text-on-surface font-semibold leading-tight">
                  {session?.roleTitle || 'Operator'}
                </span>
                <span className="font-label-sm text-label-sm text-outline leading-tight">
                  {session?.userEmail || 'Academic Cell'}
                </span>
              </div>
              {onLogout && (
                <button
                  onClick={onLogout}
                  title="Sign Out"
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
            { id: 'history', label: 'Import History & Datasets' },
            { id: 'findings', label: 'Data Quality & Findings' },
            { id: 'aicte-review', label: 'AICTE Central Review' },
            { id: 'records', label: 'Student Record & Certificate' },
            { id: 'reports', label: 'Audit Logs & Reports' },
          ].map((tab) => {
            const isActive = tab.id === 'history';
            return (
              <button
                key={tab.id}
                onClick={() => onNavigateTab?.(tab.id)}
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
      </header>

      {/* MAIN CONTENT AREA */}
      <main className="w-full pt-32 bg-transparent min-h-screen pb-16 flex-1">
        <div className="max-w-[1440px] w-full mx-auto px-gutter-md py-space-lg space-y-space-lg">
          {/* Header Banner */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-space-md bg-surface-card border border-border-subtle rounded-xl p-space-xl shadow-sm">
            <div>
              <div className="flex items-center gap-space-xs mb-space-2xs">
                <span className="font-code-sm text-code-sm text-outline uppercase tracking-wider">
                  Audit Lineage &amp; Compliance Vault
                </span>
                <span className="text-outline opacity-60">/</span>
                <span className="font-code-sm text-code-sm text-secondary font-semibold">
                  Dataset Management
                </span>
              </div>
              <h1 className="font-headline-lg text-headline-lg text-primary tracking-tight font-bold">
                Import History &amp; Dataset Management
              </h1>
              <p className="font-body-md text-body-md text-on-surface-variant pt-space-2xs">
                Traceable historical ledger of all student enrollment submissions, validation exceptions, retained documents, and audit events.
              </p>
            </div>

            <div className="flex items-center gap-space-sm flex-wrap">
              <button
                onClick={() => onNavigateTab?.('import')}
                className="inline-flex items-center gap-space-xs bg-secondary text-on-secondary px-space-lg py-space-sm rounded-lg hover:bg-secondary-fixed transition-all font-title-md text-title-md shadow-md cursor-pointer"
              >
                <span className="material-symbols-outlined text-[18px]">upload_file</span>
                <span>Upload New Batch</span>
              </button>
              <button
                onClick={fetchBatches}
                className="inline-flex items-center gap-space-xs bg-surface-card border border-border-subtle text-primary px-space-md py-space-sm rounded-lg hover:bg-surface-subtle transition-colors font-title-md text-title-md cursor-pointer"
              >
                <span className="material-symbols-outlined text-[18px]">refresh</span>
                <span>Refresh</span>
              </button>
            </div>
          </div>

          {/* Search & Filter Bar */}
          <div className="bg-surface-card border border-border-subtle rounded-xl p-space-md shadow-sm">
            <form onSubmit={handleSearchSubmit} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-space-md items-end">
              <div>
                <label className="text-[11px] font-bold uppercase tracking-wider text-outline block mb-1">
                  Search Batch / File
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Batch ID or file name..."
                    className="w-full bg-surface-subtle border border-border-subtle rounded-lg px-space-sm py-space-xs text-sm text-primary focus:outline-none focus:ring-1 focus:ring-primary pl-8"
                  />
                  <span className="material-symbols-outlined absolute left-2 top-2 text-[16px] text-outline">search</span>
                </div>
              </div>

              {isAdministrativeUser && (
                <div>
                  <label className="text-[11px] font-bold uppercase tracking-wider text-outline block mb-1">
                    Institution Scope
                  </label>
                  <select
                    value={filterInstitutionId}
                    onChange={(e) => {
                      setFilterInstitutionId(e.target.value);
                      setCurrentPage(1);
                    }}
                    className="w-full bg-surface-subtle border border-border-subtle rounded-lg px-space-sm py-space-xs text-sm text-primary focus:outline-none cursor-pointer"
                  >
                    <option value="">All Institutions</option>
                    {institutionsList.map((inst) => (
                      <option key={inst.id} value={inst.id}>
                        {inst.name} ({inst.id})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div>
                <label className="text-[11px] font-bold uppercase tracking-wider text-outline block mb-1">
                  Academic Year
                </label>
                <select
                  value={filterAcademicYear}
                  onChange={(e) => {
                    setFilterAcademicYear(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="w-full bg-surface-subtle border border-border-subtle rounded-lg px-space-sm py-space-xs text-sm text-primary focus:outline-none cursor-pointer"
                >
                  <option value="">All Academic Years</option>
                  <option value="2026-2027">2026-2027</option>
                  <option value="2025-2026">2025-2026</option>
                  <option value="2024-2025">2024-2025</option>
                </select>
              </div>

              <div>
                <label className="text-[11px] font-bold uppercase tracking-wider text-outline block mb-1">
                  Batch Status
                </label>
                <select
                  value={filterStatus}
                  onChange={(e) => {
                    setFilterStatus(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="w-full bg-surface-subtle border border-border-subtle rounded-lg px-space-sm py-space-xs text-sm text-primary focus:outline-none cursor-pointer"
                >
                  <option value="">All Statuses</option>
                  <option value="DRAFT">Draft</option>
                  <option value="VALIDATED">Validated</option>
                  <option value="NEEDS_CORRECTION">Needs Correction</option>
                  <option value="SUBMITTED">Submitted</option>
                  <option value="UNDER_REVIEW">Under Review</option>
                  <option value="ACCEPTED">Accepted</option>
                  <option value="REJECTED">Rejected</option>
                </select>
              </div>

              <div className="flex gap-2">
                <button
                  type="submit"
                  className="flex-1 bg-primary text-on-primary py-space-xs px-space-md rounded-lg font-title-sm text-title-sm hover:bg-navy-deep transition-colors cursor-pointer"
                >
                  Apply Filters
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setSearchQuery('');
                    setFilterAcademicYear('');
                    setFilterStatus('');
                    setFilterInstitutionId('');
                    setCurrentPage(1);
                  }}
                  className="bg-surface-subtle border border-border-subtle text-outline py-space-xs px-space-sm rounded-lg hover:text-primary transition-colors cursor-pointer"
                  title="Reset Filters"
                >
                  Reset
                </button>
              </div>
            </form>
          </div>

          {/* Batches Table Card */}
          <div className="bg-surface-card border border-border-subtle rounded-xl shadow-sm overflow-hidden">
            <div className="p-space-md border-b border-border-subtle flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-secondary text-[20px]">inventory_2</span>
                <span className="font-title-md text-title-md font-bold text-primary">
                  Imported Datasets ({totalBatches.toLocaleString()})
                </span>
              </div>
              <span className="text-xs text-outline">
                Page {currentPage} of {Math.max(1, Math.ceil(totalBatches / pageSize))}
              </span>
            </div>

            {isLoadingBatches ? (
              <div className="py-16 text-center text-outline flex flex-col items-center justify-center gap-2">
                <span className="material-symbols-outlined text-4xl animate-spin text-secondary">refresh</span>
                <p className="font-body-md text-body-md">Loading historical import datasets...</p>
              </div>
            ) : batchesError ? (
              <div className="py-12 px-space-xl text-center">
                <div className="inline-flex items-center gap-2 text-status-error bg-status-error-surface border border-status-error-border p-space-md rounded-lg mb-space-sm">
                  <span className="material-symbols-outlined">error</span>
                  <span>{batchesError}</span>
                </div>
                <div>
                  <button
                    onClick={fetchBatches}
                    className="bg-primary text-on-primary px-space-md py-space-xs rounded-lg text-xs"
                  >
                    Retry Loading
                  </button>
                </div>
              </div>
            ) : batches.length === 0 ? (
              <div className="py-16 text-center text-outline flex flex-col items-center justify-center gap-2">
                <span className="material-symbols-outlined text-5xl text-outline/50">folder_off</span>
                <p className="font-title-md text-title-md font-semibold text-primary">No Import Batches Found</p>
                <p className="font-body-sm text-body-sm text-on-surface-variant max-w-md">
                  No datasets matched your selected filter criteria or no student batches have been imported yet.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-surface-subtle text-outline uppercase tracking-wider border-b border-border-subtle font-semibold">
                      <th className="py-space-sm px-space-md">Batch ID / Version</th>
                      <th className="py-space-sm px-space-md">Institution</th>
                      <th className="py-space-sm px-space-md">Original Filename</th>
                      <th className="py-space-sm px-space-md">Academic Year</th>
                      <th className="py-space-sm px-space-md">Upload Date &amp; Operator</th>
                      <th className="py-space-sm px-space-md text-center">Total Rows</th>
                      <th className="py-space-sm px-space-md text-center">Valid</th>
                      <th className="py-space-sm px-space-md text-center">Errors</th>
                      <th className="py-space-sm px-space-md text-center">Warnings</th>
                      <th className="py-space-sm px-space-md text-center">Status</th>
                      <th className="py-space-sm px-space-md text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-subtle text-on-surface">
                    {batches.map((b) => {
                      const isSelected = selectedBatchId === b.id;
                      const isEligibleForDelete = ['DRAFT', 'VALIDATED', 'NEEDS_CORRECTION'].includes(b.status);

                      return (
                        <tr
                          key={b.id}
                          className={`hover:bg-surface-subtle/70 transition-colors ${isSelected ? 'bg-secondary/10 font-medium' : ''}`}
                        >
                          <td className="py-space-sm px-space-md">
                            <button
                              onClick={() => setSelectedBatchId(b.id)}
                              className="font-code-sm text-code-sm font-bold text-primary hover:text-secondary hover:underline cursor-pointer flex items-center gap-1"
                            >
                              <span>{b.id}</span>
                              <span className="text-[10px] bg-surface-container-high px-1 rounded border border-border-subtle">
                                v{b.version}
                              </span>
                            </button>
                          </td>
                          <td className="py-space-sm px-space-md">
                            <span className="font-semibold block truncate max-w-[180px]" title={b.institution_name || b.institution_id}>
                              {b.institution_name || b.institution_id}
                            </span>
                            <span className="text-[10px] text-outline font-mono">{b.institution_id}</span>
                          </td>
                          <td className="py-space-sm px-space-md font-mono text-[11px] truncate max-w-[160px]" title={b.source_filename}>
                            {b.source_filename}
                          </td>
                          <td className="py-space-sm px-space-md font-semibold">{b.academic_year}</td>
                          <td className="py-space-sm px-space-md">
                            <span className="block">{new Date(b.created_at).toLocaleDateString()} {new Date(b.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                            <span className="text-[10px] text-outline truncate block max-w-[140px]" title={b.uploader_email || 'System'}>
                              {b.uploader_email || 'System'}
                            </span>
                          </td>
                          <td className="py-space-sm px-space-md text-center font-bold">{b.total_rows.toLocaleString()}</td>
                          <td className="py-space-sm px-space-md text-center font-semibold text-status-verified">
                            {b.valid_rows.toLocaleString()}
                          </td>
                          <td className="py-space-sm px-space-md text-center">
                            <span className={`font-semibold ${b.error_rows > 0 ? 'text-status-error' : 'text-outline'}`}>
                              {b.error_rows.toLocaleString()}
                            </span>
                          </td>
                          <td className="py-space-sm px-space-md text-center">
                            <span className={`font-semibold ${b.warning_rows > 0 ? 'text-status-review' : 'text-outline'}`}>
                              {b.warning_rows.toLocaleString()}
                            </span>
                          </td>
                          <td className="py-space-sm px-space-md text-center">
                            <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold border ${getStatusBadge(b.status)}`}>
                              {b.status}
                            </span>
                          </td>
                          <td className="py-space-sm px-space-md text-right whitespace-nowrap">
                            <div className="inline-flex items-center gap-1">
                              <button
                                onClick={() => setSelectedBatchId(b.id)}
                                title="Inspect Batch Details & Records"
                                className="p-1 hover:bg-surface-container-high rounded text-primary hover:text-secondary cursor-pointer"
                              >
                                <span className="material-symbols-outlined text-[18px]">visibility</span>
                              </button>

                              {b.has_original_file ? (
                                <button
                                  onClick={() => handleDownloadOriginal(b)}
                                  title="Download Original Uploaded Document"
                                  className="p-1 hover:bg-surface-container-high rounded text-status-verified hover:text-primary cursor-pointer"
                                >
                                  <span className="material-symbols-outlined text-[18px]">download</span>
                                </button>
                              ) : (
                                <span
                                  title="Original file unavailable — document was not retained by system"
                                  className="p-1 text-outline/40 cursor-not-allowed"
                                >
                                  <span className="material-symbols-outlined text-[18px]">cloud_off</span>
                                </span>
                              )}

                              {isEligibleForDelete ? (
                                <button
                                  onClick={() => {
                                    setBatchToDelete(b);
                                    setDeleteError(null);
                                  }}
                                  title="Safely Delete Unsubmitted Batch"
                                  className="p-1 hover:bg-status-error-surface text-outline hover:text-status-error rounded cursor-pointer"
                                >
                                  <span className="material-symbols-outlined text-[18px]">delete</span>
                                </button>
                              ) : (
                                <span
                                  title={`Cannot delete batch in protected status '${b.status}'`}
                                  className="p-1 text-outline/30 cursor-not-allowed"
                                >
                                  <span className="material-symbols-outlined text-[18px]">lock</span>
                                </span>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* Pagination Controls */}
            {totalBatches > pageSize && (
              <div className="p-space-md border-t border-border-subtle flex items-center justify-between text-xs text-outline">
                <div className="flex items-center gap-2">
                  <span>Rows per page:</span>
                  <select
                    value={pageSize}
                    onChange={(e) => {
                      setPageSize(Number(e.target.value));
                      setCurrentPage(1);
                    }}
                    className="bg-surface-subtle border border-border-subtle rounded px-2 py-1 text-primary focus:outline-none"
                  >
                    <option value={10}>10</option>
                    <option value={25}>25</option>
                    <option value={50}>50</option>
                  </select>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    disabled={currentPage <= 1}
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    className="p-1 rounded bg-surface-subtle border border-border-subtle disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
                  >
                    <span className="material-symbols-outlined text-[16px]">chevron_left</span>
                  </button>
                  <span>
                    {currentPage} / {Math.ceil(totalBatches / pageSize)}
                  </span>
                  <button
                    disabled={currentPage >= Math.ceil(totalBatches / pageSize)}
                    onClick={() => setCurrentPage((p) => p + 1)}
                    className="p-1 rounded bg-surface-subtle border border-border-subtle disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
                  >
                    <span className="material-symbols-outlined text-[16px]">chevron_right</span>
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* DETAIL VIEW SECTION */}
          {selectedBatchId && (
            <div className="bg-surface-card border border-border-strong rounded-xl shadow-md p-space-xl space-y-space-lg scroll-mt-24">
              {isLoadingDetail ? (
                <div className="py-12 text-center text-outline flex items-center justify-center gap-2">
                  <span className="material-symbols-outlined animate-spin text-secondary">refresh</span>
                  <span>Loading batch inspection details...</span>
                </div>
              ) : selectedBatch ? (
                <>
                  {/* Detail Header & Action Bar */}
                  <div className="flex flex-col md:flex-row md:items-center justify-between pb-space-md border-b border-border-subtle gap-space-md">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-primary text-on-primary flex items-center justify-center font-bold">
                        <span className="material-symbols-outlined">folder_open</span>
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h2 className="font-headline-sm text-headline-sm font-bold text-primary">
                            {selectedBatch.id}
                          </h2>
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getStatusBadge(selectedBatch.status)}`}>
                            {selectedBatch.status}
                          </span>
                        </div>
                        <p className="text-xs text-outline font-mono">
                          {selectedBatch.institution_name} • AY {selectedBatch.academic_year} • Version {selectedBatch.version}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 flex-wrap">
                      {selectedBatch.has_original_file ? (
                        <button
                          onClick={() => handleDownloadOriginal(selectedBatch)}
                          className="inline-flex items-center gap-1 bg-surface-card border border-border-subtle text-primary px-space-md py-space-xs rounded-lg text-xs font-semibold hover:bg-surface-subtle cursor-pointer"
                        >
                          <span className="material-symbols-outlined text-[16px] text-secondary">download</span>
                          <span>Download Original</span>
                        </button>
                      ) : (
                        <span className="text-xs text-outline/60 italic bg-surface-subtle px-2 py-1 rounded border border-border-subtle">
                          Original file not retained
                        </span>
                      )}

                      <button
                        onClick={() => batchService.exportRecordsCsv(selectedBatch.id)}
                        className="inline-flex items-center gap-1 bg-surface-card border border-border-subtle text-primary px-space-md py-space-xs rounded-lg text-xs font-semibold hover:bg-surface-subtle cursor-pointer"
                      >
                        <span className="material-symbols-outlined text-[16px] text-primary">table_chart</span>
                        <span>Export Records (CSV)</span>
                      </button>

                      <button
                        onClick={() => batchService.exportFindingsCsv(selectedBatch.id)}
                        className="inline-flex items-center gap-1 bg-surface-card border border-border-subtle text-primary px-space-md py-space-xs rounded-lg text-xs font-semibold hover:bg-surface-subtle cursor-pointer"
                      >
                        <span className="material-symbols-outlined text-[16px] text-status-review">report</span>
                        <span>Export Findings (CSV)</span>
                      </button>

                      <button
                        onClick={() => setSelectedBatchId(null)}
                        className="p-1.5 hover:bg-surface-subtle rounded-md text-outline hover:text-primary cursor-pointer"
                        title="Close Detail View"
                      >
                        <span className="material-symbols-outlined text-[20px]">close</span>
                      </button>
                    </div>
                  </div>

                  {/* Detail Tabs */}
                  <div className="flex items-center gap-space-sm border-b border-border-subtle text-xs font-semibold">
                    {[
                      { id: 'overview', label: 'Batch Overview', icon: 'info' },
                      { id: 'records', label: `Imported Records (${selectedBatch.valid_rows})`, icon: 'people' },
                      { id: 'findings', label: `Validation Findings (${selectedBatch.error_rows + selectedBatch.warning_rows})`, icon: 'rule' },
                      { id: 'history', label: 'Lifecycle Audit Trail', icon: 'history' },
                    ].map((tab) => (
                      <button
                        key={tab.id}
                        onClick={() => setDetailTab(tab.id as any)}
                        className={`flex items-center gap-1.5 py-space-xs px-space-md border-b-2 cursor-pointer transition-colors ${
                          detailTab === tab.id
                            ? 'border-secondary text-secondary font-bold bg-secondary/5 rounded-t-md'
                            : 'border-transparent text-outline hover:text-primary'
                        }`}
                      >
                        <span className="material-symbols-outlined text-[16px]">{tab.icon}</span>
                        <span>{tab.label}</span>
                      </button>
                    ))}
                  </div>

                  {/* TAB 1: OVERVIEW */}
                  {detailTab === 'overview' && (
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-space-md text-xs">
                      <div className="p-space-md rounded-lg bg-surface-subtle border border-border-subtle">
                        <span className="text-outline uppercase block text-[10px] font-bold">Institution Info</span>
                        <span className="font-bold text-primary text-sm block mt-1">{selectedBatch.institution_name}</span>
                        <span className="text-outline font-mono">{selectedBatch.institution_id}</span>
                      </div>
                      <div className="p-space-md rounded-lg bg-surface-subtle border border-border-subtle">
                        <span className="text-outline uppercase block text-[10px] font-bold">Source File Details</span>
                        <span className="font-bold text-primary text-sm block mt-1 truncate" title={selectedBatch.source_filename}>
                          {selectedBatch.source_filename}
                        </span>
                        <span className="text-outline">
                          {selectedBatch.file_size_bytes ? `${(selectedBatch.file_size_bytes / 1024).toFixed(1)} KB` : 'Retained on server'}
                        </span>
                      </div>
                      <div className="p-space-md rounded-lg bg-surface-subtle border border-border-subtle">
                        <span className="text-outline uppercase block text-[10px] font-bold">Row Breakdown</span>
                        <span className="font-bold text-primary text-sm block mt-1">
                          {selectedBatch.total_rows} Total Rows
                        </span>
                        <span className="text-status-verified font-semibold">{selectedBatch.valid_rows} Persisted</span>
                        {' • '}
                        <span className="text-status-error font-semibold">{selectedBatch.error_rows} Rejected</span>
                      </div>
                      <div className="p-space-md rounded-lg bg-surface-subtle border border-border-subtle">
                        <span className="text-outline uppercase block text-[10px] font-bold">Upload Lineage</span>
                        <span className="font-bold text-primary block mt-1">{new Date(selectedBatch.created_at).toLocaleString()}</span>
                        <span className="text-outline">By: {selectedBatch.uploader_email || 'System'}</span>
                      </div>
                    </div>
                  )}

                  {/* TAB 2: IMPORTED STUDENT RECORDS */}
                  {detailTab === 'records' && (
                    <div className="space-y-space-md">
                      <div className="flex items-center justify-between gap-space-md">
                        <div className="relative max-w-xs w-full">
                          <input
                            type="text"
                            value={recordsSearch}
                            onChange={(e) => {
                              setRecordsSearch(e.target.value);
                              setRecordsPage(1);
                            }}
                            placeholder="Filter by roll or student name..."
                            className="w-full bg-surface-subtle border border-border-subtle rounded-lg px-space-sm py-1 text-xs text-primary focus:outline-none pl-8"
                          />
                          <span className="material-symbols-outlined absolute left-2 top-1.5 text-[14px] text-outline">search</span>
                        </div>
                        <span className="text-xs text-outline">{recordsTotal} Records</span>
                      </div>

                      {isLoadingRecords ? (
                        <div className="py-8 text-center text-outline">Loading student records...</div>
                      ) : batchRecords.length === 0 ? (
                        <div className="py-8 text-center text-outline">No student records match search criteria.</div>
                      ) : (
                        <div className="overflow-x-auto border border-border-subtle rounded-lg">
                          <table className="w-full text-left text-xs border-collapse">
                            <thead>
                              <tr className="bg-surface-subtle text-outline font-semibold border-b border-border-subtle">
                                <th className="py-2 px-3">Row #</th>
                                <th className="py-2 px-3">Student Roll ID</th>
                                <th className="py-2 px-3">Student Name</th>
                                <th className="py-2 px-3">APAAR ID (Masked)</th>
                                <th className="py-2 px-3">Programme</th>
                                <th className="py-2 px-3">Seat Type</th>
                                <th className="py-2 px-3">Status</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-border-subtle text-on-surface">
                              {batchRecords.map((r) => (
                                <tr key={r.id} className="hover:bg-surface-subtle/50">
                                  <td className="py-2 px-3 text-outline font-mono">{r.source_row_number || '-'}</td>
                                  <td className="py-2 px-3 font-semibold font-mono">{r.institution_student_id}</td>
                                  <td className="py-2 px-3">{r.student_name || '[Not Provided]'}</td>
                                  <td className="py-2 px-3 font-mono text-secondary font-semibold">
                                    {r.apaar_id || '[PENDING_CREATION]'}
                                  </td>
                                  <td className="py-2 px-3 font-mono">{r.programme_id}</td>
                                  <td className="py-2 px-3">{r.seat_type}</td>
                                  <td className="py-2 px-3">
                                    <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-status-verified-surface text-status-verified">
                                      {r.enrolment_status}
                                    </span>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}

                      {/* Records Pagination */}
                      {recordsTotal > 10 && (
                        <div className="flex items-center justify-between text-xs text-outline pt-2">
                          <span>Showing Page {recordsPage} of {Math.ceil(recordsTotal / 10)}</span>
                          <div className="flex gap-2">
                            <button
                              disabled={recordsPage <= 1}
                              onClick={() => setRecordsPage((p) => p - 1)}
                              className="px-2 py-1 bg-surface-subtle border border-border-subtle rounded disabled:opacity-40"
                            >
                              Prev
                            </button>
                            <button
                              disabled={recordsPage >= Math.ceil(recordsTotal / 10)}
                              onClick={() => setRecordsPage((p) => p + 1)}
                              className="px-2 py-1 bg-surface-subtle border border-border-subtle rounded disabled:opacity-40"
                            >
                              Next
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* TAB 3: VALIDATION FINDINGS */}
                  {detailTab === 'findings' && (
                    <div className="space-y-space-md">
                      <div className="flex items-center justify-between gap-space-md">
                        <select
                          value={findingsSeverity}
                          onChange={(e) => {
                            setFindingsSeverity(e.target.value);
                            setFindingsPage(1);
                          }}
                          className="bg-surface-subtle border border-border-subtle rounded-lg px-space-sm py-1 text-xs text-primary focus:outline-none"
                        >
                          <option value="">All Severity Levels</option>
                          <option value="BLOCKING_ERROR">Blocking Errors Only</option>
                          <option value="WARNING">Warnings Only</option>
                        </select>
                        <span className="text-xs text-outline">{findingsTotal} Findings</span>
                      </div>

                      {isLoadingFindings ? (
                        <div className="py-8 text-center text-outline">Loading findings...</div>
                      ) : findingsList.length === 0 ? (
                        <div className="py-8 text-center text-status-verified font-semibold flex items-center justify-center gap-1">
                          <span className="material-symbols-outlined text-[18px]">check_circle</span>
                          <span>No validation findings recorded for this severity filter.</span>
                        </div>
                      ) : (
                        <div className="overflow-x-auto border border-border-subtle rounded-lg">
                          <table className="w-full text-left text-xs border-collapse">
                            <thead>
                              <tr className="bg-surface-subtle text-outline font-semibold border-b border-border-subtle">
                                <th className="py-2 px-3">Row</th>
                                <th className="py-2 px-3">Field</th>
                                <th className="py-2 px-3">Rule Code</th>
                                <th className="py-2 px-3">Severity</th>
                                <th className="py-2 px-3">Diagnostic Note</th>
                                <th className="py-2 px-3">Remediation Action</th>
                                <th className="py-2 px-3">Status</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-border-subtle text-on-surface">
                              {findingsList.map((f) => (
                                <tr key={f.id} className="hover:bg-surface-subtle/50">
                                  <td className="py-2 px-3 font-mono">{f.row_number || '-'}</td>
                                  <td className="py-2 px-3 font-mono font-semibold">{f.field_name || 'N/A'}</td>
                                  <td className="py-2 px-3 font-mono font-bold text-primary">{f.rule_code}</td>
                                  <td className="py-2 px-3">
                                    <span
                                      className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                        f.severity === 'BLOCKING_ERROR'
                                          ? 'bg-status-error-surface text-status-error'
                                          : 'bg-status-review-surface text-status-review'
                                      }`}
                                    >
                                      {f.severity}
                                    </span>
                                  </td>
                                  <td className="py-2 px-3 max-w-xs">{f.message}</td>
                                  <td className="py-2 px-3 text-outline italic max-w-xs">{f.suggested_action || 'N/A'}</td>
                                  <td className="py-2 px-3">
                                    <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-surface-subtle text-primary border border-border-subtle">
                                      {f.status}
                                    </span>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}

                      {/* Findings Pagination */}
                      {findingsTotal > 10 && (
                        <div className="flex items-center justify-between text-xs text-outline pt-2">
                          <span>Showing Page {findingsPage} of {Math.ceil(findingsTotal / 10)}</span>
                          <div className="flex gap-2">
                            <button
                              disabled={findingsPage <= 1}
                              onClick={() => setFindingsPage((p) => p - 1)}
                              className="px-2 py-1 bg-surface-subtle border border-border-subtle rounded disabled:opacity-40"
                            >
                              Prev
                            </button>
                            <button
                              disabled={findingsPage >= Math.ceil(findingsTotal / 10)}
                              onClick={() => setFindingsPage((p) => p + 1)}
                              className="px-2 py-1 bg-surface-subtle border border-border-subtle rounded disabled:opacity-40"
                            >
                              Next
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* TAB 4: AUDIT TRAIL */}
                  {detailTab === 'history' && (
                    <div className="space-y-space-md">
                      {isLoadingHistory ? (
                        <div className="py-8 text-center text-outline">Loading audit trail...</div>
                      ) : historyEvents.length === 0 ? (
                        <div className="py-8 text-center text-outline">No audit history events logged for this batch.</div>
                      ) : (
                        <div className="space-y-space-sm">
                          {historyEvents.map((evt) => (
                            <div
                              key={evt.id}
                              className="p-space-md rounded-lg bg-surface-subtle border border-border-subtle flex items-start gap-space-md text-xs"
                            >
                              <div className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center shrink-0">
                                <span className="material-symbols-outlined text-[16px]">receipt_long</span>
                              </div>
                              <div className="flex-1">
                                <div className="flex items-center justify-between">
                                  <span className="font-bold text-primary uppercase tracking-wide">{evt.action}</span>
                                  <span className="text-outline text-[11px] font-mono">
                                    {new Date(evt.timestamp).toLocaleString()}
                                  </span>
                                </div>
                                <p className="text-on-surface-variant mt-0.5">{evt.details || 'Lifecycle transition recorded'}</p>
                                <span className="text-[10px] text-outline mt-1 block">
                                  Actor: {evt.actor_email} ({evt.actor_role}) • Outcome: {evt.outcome}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </>
              ) : null}
            </div>
          )}
        </div>
      </main>

      {/* CONFIRMATION DELETION MODAL */}
      {batchToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-surface-card border border-border-subtle rounded-xl max-w-lg w-full p-space-xl shadow-2xl space-y-space-lg">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-full bg-status-error-surface text-status-error flex items-center justify-center shrink-0">
                <span className="material-symbols-outlined text-[24px]">warning</span>
              </div>
              <div>
                <h3 className="font-headline-sm text-headline-sm font-bold text-primary">
                  Confirm Dataset Deletion
                </h3>
                <p className="text-xs text-on-surface-variant pt-1 leading-relaxed">
                  Are you sure you want to permanently delete this unsubmitted import batch? This will remove all associated student records and validation findings from operational staging.
                </p>
              </div>
            </div>

            <div className="bg-surface-subtle p-space-md rounded-lg text-xs space-y-1.5 border border-border-subtle">
              <div className="flex justify-between">
                <span className="text-outline">Batch ID:</span>
                <span className="font-mono font-bold text-primary">{batchToDelete.id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-outline">Institution:</span>
                <span className="font-semibold">{batchToDelete.institution_name || batchToDelete.institution_id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-outline">Source File:</span>
                <span className="font-mono">{batchToDelete.source_filename}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-outline">Total Records:</span>
                <span className="font-bold">{batchToDelete.total_rows}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-outline">Retained Document:</span>
                <span>{batchToDelete.has_original_file ? 'Will also be permanently purged' : 'Not retained'}</span>
              </div>
            </div>

            <div className="text-[11px] text-outline italic">
              Note: Historical compliance audit events are preserved in the permanent statutory audit log.
            </div>

            {deleteError && (
              <div className="p-space-sm rounded bg-status-error-surface border border-status-error-border text-status-error text-xs">
                {deleteError}
              </div>
            )}

            <div className="flex items-center justify-end gap-space-sm pt-space-xs">
              <button
                disabled={isDeleting}
                onClick={() => setBatchToDelete(null)}
                className="px-space-lg py-space-xs rounded-lg text-xs font-semibold text-primary hover:bg-surface-subtle border border-border-subtle cursor-pointer"
              >
                Cancel
              </button>
              <button
                disabled={isDeleting}
                onClick={handleConfirmDelete}
                className="px-space-lg py-space-xs rounded-lg text-xs font-semibold bg-status-error text-white hover:bg-red-700 shadow-sm cursor-pointer inline-flex items-center gap-1"
              >
                {isDeleting ? (
                  <>
                    <span className="material-symbols-outlined text-[16px] animate-spin">refresh</span>
                    <span>Deleting Dataset...</span>
                  </>
                ) : (
                  <span>Delete Dataset</span>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
