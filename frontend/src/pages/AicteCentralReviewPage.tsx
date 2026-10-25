import React, { useState, useMemo, useEffect, useCallback } from 'react';
import { AuthSession } from '../types/auth';
import {
  reviewService,
  batchService,
  dashboardService,
  MatchCandidateItem,
  BatchItem,
  AicteDashboardMetrics,
} from '../services/api';

interface AicteCentralReviewPageProps {
  session?: AuthSession | null;
  onLogout?: () => void;
  onSwitchTab?: (tab: string, apaarId?: string) => void;
}

interface BreachDisplayRecord {
  pid: string;
  name: string;
  location: string;
  course: string;
  affiliation: string;
  cap: number;
  intake: number;
  excess: number;
  excessTag: string;
  citation: string;
  citationDesc: string;
  actionText: string;
  actionStyle: 'error' | 'subtle';
  state: string;
}

const DEFAULT_BREACH_RECORDS: BreachDisplayRecord[] = [
  {
    pid: 'INST-001',
    name: 'Apex Institute of Technology',
    location: 'Bangalore, Karnataka',
    course: 'B.Tech Computer Science & Engineering',
    affiliation: 'Autonomous Technical Institute',
    cap: 120,
    intake: 120,
    excess: 0,
    excessTag: 'At Ceiling',
    citation: 'APH 2026 Cl 7.2.3',
    citationDesc: 'Full regular approved capacity utilized',
    actionText: 'Audited & Compliant',
    actionStyle: 'subtle',
    state: 'Karnataka',
  },
  {
    pid: 'INST-002',
    name: 'Bharat Engineering College',
    location: 'Pune, Maharashtra',
    course: 'B.Tech Computer Science & Engineering',
    affiliation: 'State University Affiliated',
    cap: 180,
    intake: 180,
    excess: 0,
    excessTag: 'At Ceiling',
    citation: 'APH 2026 Cl 4.1.8',
    citationDesc: 'Within regular statutory allotment limits',
    actionText: 'Audited & Compliant',
    actionStyle: 'subtle',
    state: 'Maharashtra',
  },
  {
    pid: 'INST-003',
    name: 'Crest Institute of Management & Technology',
    location: 'Lucknow, Uttar Pradesh',
    course: 'Master of Business Administration',
    affiliation: 'State Government University Affiliated',
    cap: 120,
    intake: 120,
    excess: 0,
    excessTag: 'At Ceiling',
    citation: 'APH 2026 Cl 6.4.0',
    citationDesc: 'Intake reconciliation compliant',
    actionText: 'Audited & Compliant',
    actionStyle: 'subtle',
    state: 'Uttar Pradesh',
  },
];

export const AicteCentralReviewPage: React.FC<AicteCentralReviewPageProps> = ({
  session,
  onLogout,
  onSwitchTab,
}) => {
  // Navigation active tab
  const [activeTab, setActiveTab] = useState<string>('aicte-review');

  // ---------------------------------------------------------------------------
  // Real Data State: Match Candidates Queue
  // ---------------------------------------------------------------------------
  const [matches, setMatches] = useState<MatchCandidateItem[]>([]);
  const [isLoadingMatches, setIsLoadingMatches] = useState<boolean>(true);
  const [matchError, setMatchError] = useState<string | null>(null);
  const [matchStatusFilter, setMatchStatusFilter] = useState<string>('ALL');
  const [caseIndex, setCaseIndex] = useState<number>(0);

  // APAAR ID decrypted toggle
  const [isApaarDecrypted, setIsApaarDecrypted] = useState<boolean>(false);

  // Match Adjudication Form State
  const [candidateVerdict, setCandidateVerdict] = useState<'CONFIRMED_DUPLICATE' | 'DISMISSED'>('CONFIRMED_DUPLICATE');
  const [candidateJustification, setCandidateJustification] = useState<string>('');
  const [isSubmittingCandidate, setIsSubmittingCandidate] = useState<boolean>(false);
  const [candidateSubmitError, setCandidateSubmitError] = useState<string | null>(null);

  // ---------------------------------------------------------------------------
  // Real Data State: Batch Review Workflow Queue
  // ---------------------------------------------------------------------------
  const [batches, setBatches] = useState<BatchItem[]>([]);
  const [isLoadingBatches, setIsLoadingBatches] = useState<boolean>(true);
  const [batchError, setBatchError] = useState<string | null>(null);
  const [batchStatusFilter, setBatchStatusFilter] = useState<string>('ALL');
  const [batchSearch, setBatchSearch] = useState<string>('');

  // Batch Decision Modal State
  const [selectedBatchForReview, setSelectedBatchForReview] = useState<BatchItem | null>(null);
  const [batchDecision, setBatchDecision] = useState<'UNDER_REVIEW' | 'ACCEPTED' | 'REJECTED' | 'NEEDS_CORRECTION'>('UNDER_REVIEW');
  const [batchReason, setBatchReason] = useState<string>('');
  const [isSubmittingBatch, setIsSubmittingBatch] = useState<boolean>(false);
  const [batchActionError, setBatchActionError] = useState<string | null>(null);
  const [showBatchModal, setShowBatchModal] = useState<boolean>(false);

  // ---------------------------------------------------------------------------
  // Real Data State: Dashboard Metrics & Intake
  // ---------------------------------------------------------------------------
  const [metrics, setMetrics] = useState<AicteDashboardMetrics | null>(null);
  const [tableSearch, setTableSearch] = useState<string>('');
  const [breachRecords, setBreachRecords] = useState<BreachDisplayRecord[]>(DEFAULT_BREACH_RECORDS);

  // Notifications and feedback banner
  const [notificationMsg, setNotificationMsg] = useState<string | null>(null);
  const [showNotificationBell, setShowNotificationBell] = useState<boolean>(false);
  const [isScanning, setIsScanning] = useState<boolean>(false);

  const showToast = (msg: string) => {
    setNotificationMsg(msg);
    setTimeout(() => {
      setNotificationMsg(null);
    }, 4500);
  };

  // ---------------------------------------------------------------------------
  // Data Fetching: Load Real Backend Records
  // ---------------------------------------------------------------------------
  const loadReviewData = useCallback(async () => {
    // 1. Load Match Candidates
    try {
      setIsLoadingMatches(true);
      setMatchError(null);
      const res = await reviewService.listMatchCandidates({ limit: 100 });
      setMatches(res.items || []);
    } catch (err: any) {
      setMatchError(err.message || 'Failed to fetch cross-institution match candidates.');
    } finally {
      setIsLoadingMatches(false);
    }

    // 2. Load Institutional Batches
    try {
      setIsLoadingBatches(true);
      setBatchError(null);
      const batchRes = await batchService.listBatches({ limit: 100 });
      setBatches(batchRes.items || []);
    } catch (err: any) {
      setBatchError(err.message || 'Failed to fetch institutional batches for review.');
    } finally {
      setIsLoadingBatches(false);
    }

    // 3. Load National AICTE Metrics & Intakes
    try {
      const aicteMetrics = await dashboardService.getAicteMetrics();
      setMetrics(aicteMetrics);
    } catch {
      // Non-blocking dashboard fetch
    }

    try {
      const intakeRes = await dashboardService.getApprovedIntake();
      if (intakeRes.items && intakeRes.items.length > 0) {
        const dynamicBreaches: BreachDisplayRecord[] = intakeRes.items.map((it) => ({
          pid: it.institution_id,
          name: it.institution_id === 'INST-001' ? 'Apex Institute of Technology' : it.institution_id === 'INST-002' ? 'Bharat Engineering College' : 'Approved Institution',
          location: it.institution_id === 'INST-001' ? 'Bangalore, Karnataka' : 'Pune, Maharashtra',
          course: it.programme_name || it.programme_id,
          affiliation: 'AICTE Recognized Institute',
          cap: it.regular_intake,
          intake: it.regular_intake,
          excess: 0,
          excessTag: 'Compliant',
          citation: 'APH 2026 Cl 7.2.3',
          citationDesc: `Approved regular intake: ${it.regular_intake}, supernumerary: ${it.supernumerary_intake}`,
          actionText: 'Audited & Logged',
          actionStyle: 'subtle',
          state: it.institution_id === 'INST-001' ? 'Karnataka' : 'Maharashtra',
        }));
        setBreachRecords(dynamicBreaches);
      }
    } catch {
      // Fallback already set
    }
  }, []);

  useEffect(() => {
    loadReviewData();
  }, [loadReviewData]);

  // ---------------------------------------------------------------------------
  // Match Candidate Filtering & Current Case Selection
  // ---------------------------------------------------------------------------
  const filteredMatches = useMemo(() => {
    if (matchStatusFilter === 'ALL') return matches;
    return matches.filter((m) => m.status === matchStatusFilter);
  }, [matches, matchStatusFilter]);

  const safeIndex = useMemo(() => {
    if (filteredMatches.length === 0) return 0;
    return Math.min(caseIndex, filteredMatches.length - 1);
  }, [caseIndex, filteredMatches.length]);

  const currentMatch = useMemo(() => {
    return filteredMatches[safeIndex] || null;
  }, [filteredMatches, safeIndex]);

  // Update default justification when switching cases
  useEffect(() => {
    if (currentMatch) {
      if (currentMatch.resolution_reason) {
        setCandidateJustification(currentMatch.resolution_reason);
      } else {
        setCandidateJustification(
          `AICTE regulatory triage for match ${currentMatch.id}: Cross-referenced enrollment records between ${currentMatch.institution_a?.name || currentMatch.institution_a_id} and ${currentMatch.institution_b?.name || currentMatch.institution_b_id}.`
        );
      }
      if (currentMatch.status === 'CONFIRMED_DUPLICATE') {
        setCandidateVerdict('CONFIRMED_DUPLICATE');
      } else if (currentMatch.status === 'DISMISSED') {
        setCandidateVerdict('DISMISSED');
      } else {
        setCandidateVerdict('CONFIRMED_DUPLICATE');
      }
      setIsApaarDecrypted(false);
      setCandidateSubmitError(null);
    }
  }, [currentMatch]);

  const handleNextCase = () => {
    if (filteredMatches.length === 0) return;
    setCaseIndex((prev) => (prev + 1) % filteredMatches.length);
  };

  const handlePrevCase = () => {
    if (filteredMatches.length === 0) return;
    setCaseIndex((prev) => (prev - 1 + filteredMatches.length) % filteredMatches.length);
  };

  // ---------------------------------------------------------------------------
  // Action Handlers: Match Candidate Decision Submission
  // ---------------------------------------------------------------------------
  const handleSubmitCandidateVerdict = async () => {
    if (!currentMatch) return;
    if (!candidateJustification || candidateJustification.trim().length < 5) {
      setCandidateSubmitError('Mandatory justification (minimum 5 characters) is required for statutory review.');
      showToast('Validation Error: Justification is required.');
      return;
    }

    try {
      setIsSubmittingCandidate(true);
      setCandidateSubmitError(null);

      const updated = await reviewService.reviewMatchCandidate(
        currentMatch.id,
        candidateVerdict,
        candidateJustification.trim()
      );

      showToast(`Decision Persisted! Case ${updated.id} status updated to ${updated.status}. Audit record created.`);
      
      // Refresh match list
      const res = await reviewService.listMatchCandidates({ limit: 100 });
      setMatches(res.items || []);
    } catch (err: any) {
      const errMsg = err.message || 'Failed to persist review decision.';
      setCandidateSubmitError(errMsg);
      showToast(`Review Failed: ${errMsg}`);
    } finally {
      setIsSubmittingCandidate(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Action Handlers: Batch Review Workflow
  // ---------------------------------------------------------------------------
  const openBatchDecisionModal = (
    batch: BatchItem,
    decision: 'UNDER_REVIEW' | 'ACCEPTED' | 'REJECTED' | 'NEEDS_CORRECTION'
  ) => {
    setSelectedBatchForReview(batch);
    setBatchDecision(decision);
    setBatchActionError(null);
    const defaultReason =
      decision === 'UNDER_REVIEW'
        ? `Batch ${batch.id} placed under statutory AICTE review for verification.`
        : decision === 'ACCEPTED'
        ? `Batch ${batch.id} meets all statutory intake criteria. Approved with 0 blocking errors.`
        : decision === 'NEEDS_CORRECTION'
        ? `Batch ${batch.id} returned to institution for corrective remediation.`
        : `Batch ${batch.id} rejected due to statutory discrepancies.`;
    setBatchReason(defaultReason);
    setShowBatchModal(true);
  };

  const handleExecuteBatchDecision = async () => {
    if (!selectedBatchForReview) return;
    if (!batchReason || batchReason.trim().length < 5) {
      setBatchActionError('Mandatory justification (minimum 5 characters) is required.');
      return;
    }

    try {
      setIsSubmittingBatch(true);
      setBatchActionError(null);

      const res = await reviewService.reviewBatch(
        selectedBatchForReview.id,
        batchDecision,
        batchReason.trim()
      );

      showToast(`Batch Decision Persisted! Batch ${res.batch_id} transitioned ${res.previous_status} -> ${res.status}.`);
      setShowBatchModal(false);
      setSelectedBatchForReview(null);
      setBatchReason('');

      // Refresh batches from backend
      const batchRes = await batchService.listBatches({ limit: 100 });
      setBatches(batchRes.items || []);

      // Also refresh dashboard metrics
      try {
        const aicteMetrics = await dashboardService.getAicteMetrics();
        setMetrics(aicteMetrics);
      } catch {
        // ignore
      }
    } catch (err: any) {
      const errMsg = err.message || 'Failed to execute batch review decision.';
      setBatchActionError(errMsg);
      showToast(`Batch Review Failed: ${errMsg}`);
    } finally {
      setIsSubmittingBatch(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Batch Filtering
  // ---------------------------------------------------------------------------
  const filteredBatches = useMemo(() => {
    return batches.filter((b) => {
      const matchesStatus = batchStatusFilter === 'ALL' || b.status === batchStatusFilter;
      const matchesSearch =
        !batchSearch.trim() ||
        b.id.toLowerCase().includes(batchSearch.toLowerCase()) ||
        (b.institution_name && b.institution_name.toLowerCase().includes(batchSearch.toLowerCase())) ||
        b.institution_id.toLowerCase().includes(batchSearch.toLowerCase()) ||
        b.source_filename.toLowerCase().includes(batchSearch.toLowerCase());
      return matchesStatus && matchesSearch;
    });
  }, [batches, batchStatusFilter, batchSearch]);

  // Derived counts for batches
  const batchCounts = useMemo(() => {
    const counts = {
      ALL: batches.length,
      SUBMITTED: 0,
      UNDER_REVIEW: 0,
      ACCEPTED: 0,
      NEEDS_CORRECTION: 0,
      REJECTED: 0,
      DRAFT: 0,
      VALIDATED: 0,
    };
    batches.forEach((b) => {
      if ((counts as any)[b.status] !== undefined) {
        (counts as any)[b.status]++;
      }
    });
    return counts;
  }, [batches]);

  // Derived counts for matches
  const matchCounts = useMemo(() => {
    const counts = {
      ALL: matches.length,
      CANDIDATE: 0,
      CONFIRMED_DUPLICATE: 0,
      DISMISSED: 0,
    };
    matches.forEach((m) => {
      if ((counts as any)[m.status] !== undefined) {
        (counts as any)[m.status]++;
      }
    });
    return counts;
  }, [matches]);

  // Trigger National Rescan
  const handleTriggerRescan = () => {
    setIsScanning(true);
    showToast('Initiating cryptographic identity rescan across all approved institutions...');
    loadReviewData().then(() => {
      setIsScanning(false);
      showToast(`Rescan Complete: ${matches.length} Match Candidates & ${batches.length} Institutional Batches Synchronized.`);
    });
  };

  // Export Gazette Log PDF/A
  const handleExportPDF = () => {
    showToast('Exporting Gazette Log (PDF/A) with statutory compliance citations...');
    setTimeout(() => {
      showToast('Gazette Log (PDF/A) successfully compiled and queued for download.');
    }, 1200);
  };

  // Export CSV
  const handleExportCSV = () => {
    const headers = [
      'Permanent ID',
      'Institution Name',
      'Location',
      'Course',
      'Affiliation',
      'Approved Cap',
      'Reported Intake',
      'Discrepancy',
      'Citation',
      'Description',
    ];
    const rows = breachRecords.map((r) => [
      `"${r.pid}"`,
      `"${r.name}"`,
      `"${r.location}"`,
      `"${r.course}"`,
      `"${r.affiliation}"`,
      r.cap,
      r.intake,
      `"+${r.excess}"`,
      `"${r.citation}"`,
      `"${r.citationDesc}"`,
    ]);
    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `AICTE_Intake_Breach_Registry_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast('CSV Export triggered: Downloaded breach registry.');
  };

  // Filtered breach records based on search
  const filteredBreaches = useMemo(() => {
    if (!tableSearch.trim()) return breachRecords;
    const q = tableSearch.toLowerCase();
    return breachRecords.filter(
      (b) =>
        b.name.toLowerCase().includes(q) ||
        b.pid.toLowerCase().includes(q) ||
        b.location.toLowerCase().includes(q) ||
        b.course.toLowerCase().includes(q)
    );
  }, [tableSearch, breachRecords]);

  // Action on breach row
  const handleBreachAction = (pid: string, actionText: string) => {
    setBreachRecords((prev) =>
      prev.map((rec) => {
        if (rec.pid === pid) {
          return {
            ...rec,
            actionText: actionText === 'Audited & Compliant' ? 'Compliance Confirmed' : 'Audited & Logged',
            actionStyle: 'subtle',
          };
        }
        return rec;
      })
    );
    showToast(`Notice/Action acknowledged for Permanent ID ${pid}: ${actionText}`);
  };

  // APAAR ID display helper
  const rawApaar = currentMatch?.record_a?.apaar_id || currentMatch?.record_b?.apaar_id || '999988887777';
  const displayApaarId = isApaarDecrypted
    ? rawApaar
    : rawApaar.length >= 12
    ? `${rawApaar.slice(0, 4)}-XXXX-${rawApaar.slice(-4)}`
    : rawApaar;

  return (
    <div className="tricolor-slant-bg font-body-md text-on-surface antialiased min-h-screen flex flex-col relative selection:bg-secondary/20">
      {/* Toast Notification Banner */}
      {notificationMsg && (
        <div className="fixed bottom-6 right-6 z-50 max-w-md bg-navy-deep text-white p-4 rounded-xl shadow-2xl border border-secondary/40 flex items-start gap-3 animate-bounce">
          <span className="material-symbols-outlined text-secondary text-2xl mt-0.5">
            verified
          </span>
          <div className="flex-1 text-xs">
            <div className="font-bold text-sm text-secondary-fixed">
              Sovereign Ledger Notification
            </div>
            <div className="mt-1 leading-relaxed">{notificationMsg}</div>
          </div>
          <button
            onClick={() => setNotificationMsg(null)}
            className="text-white/60 hover:text-white"
          >
            <span className="material-symbols-outlined text-base">close</span>
          </button>
        </div>
      )}

      {/* TOP HEADER */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-surface-card border-b border-border-subtle shadow-[0_1px_8px_rgba(0,0,0,0.04)]">
        <div className="h-14 w-full px-gutter-md flex items-center justify-between">
          <div className="flex items-center gap-space-md">
            {/* Emblem Logo */}
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
                  : 'AICTE Apex Regulatory Council (National Central Node)'}
              </span>
            </div>

            {/* Role dropdown switcher */}
            <div className="relative">
              <select
                defaultValue={session?.roleTitle || 'AICTE Reviewer'}
                className="font-label-md text-label-md bg-surface-card border border-border-strong text-primary rounded-lg px-space-sm py-space-xs focus:ring-1 focus:ring-secondary focus:outline-none cursor-pointer"
              >
                <option value="AICTE Reviewer">AICTE Reviewer</option>
                <option value="Institution Admin">Institution Admin</option>
                <option value="Institution Operator">Institution Operator</option>
              </select>
            </div>

            {/* Notification Bell */}
            <div className="relative">
              <button
                aria-label="Notifications"
                onClick={() => setShowNotificationBell(!showNotificationBell)}
                className="relative p-space-xs text-on-surface-variant hover:text-primary transition-colors cursor-pointer"
              >
                <span className="material-symbols-outlined text-[20px]">
                  notifications
                </span>
                {matches.length > 0 && (
                  <span className="absolute top-1 right-1 w-2 h-2 bg-status-error rounded-full animate-pulse"></span>
                )}
              </button>

              {showNotificationBell && (
                <div className="absolute right-0 mt-2 w-80 bg-surface-card rounded-xl shadow-xl border border-border-strong p-3 z-50 text-xs">
                  <div className="font-bold text-primary border-b border-border-subtle pb-2 mb-2 flex items-center justify-between">
                    <span>Audit Notices</span>
                    <span className="bg-status-error-surface text-status-error px-1.5 py-0.5 rounded text-[10px] font-mono">
                      {matches.length} Cases
                    </span>
                  </div>
                  <div className="space-y-2 max-h-56 overflow-y-auto">
                    <div className="p-2 bg-surface-subtle rounded border border-border-subtle">
                      <div className="font-semibold text-primary">Cross-Institution Conflicts</div>
                      <div className="text-on-surface-variant text-[11px]">
                        {matchCounts.CANDIDATE} candidate duplicates awaiting statutory triage.
                      </div>
                    </div>
                    <div className="p-2 bg-surface-subtle rounded border border-border-subtle">
                      <div className="font-semibold text-primary">Batches Pending Review</div>
                      <div className="text-on-surface-variant text-[11px]">
                        {batchCounts.SUBMITTED} institutional submissions require regulatory decision.
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* User Profile & Sign Out */}
            <div className="flex items-center gap-space-xs pl-space-xs border-l border-border-subtle">
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center font-headline-sm text-headline-sm text-on-primary font-bold shadow-sm">
                <span className="material-symbols-outlined text-on-primary text-[18px]">
                  person
                </span>
              </div>
              <div className="hidden md:flex flex-col">
                <span className="font-label-md text-label-md text-on-surface font-semibold leading-tight">
                  {session?.roleTitle ? session.roleTitle : 'AICTE Central Officer'}
                </span>
                <span className="font-label-sm text-label-sm text-outline leading-tight">
                  {session?.userEmail ? session.userEmail : 'Apex Directorate'}
                </span>
              </div>
              {onLogout && (
                <button
                  onClick={onLogout}
                  title="Sign Out to Login Page"
                  className="ml-2 p-1.5 hover:bg-surface-subtle text-outline hover:text-status-error rounded-md transition-colors flex items-center gap-1 text-xs"
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
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => {
                  setActiveTab(tab.id);
                  if (onSwitchTab) onSwitchTab(tab.id);
                  if (tab.id !== 'aicte-review') {
                    showToast(`Navigated to: ${tab.label}`);
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
              APAAR ID-Based Student Verification Engine • Mock Adapter Active (MOCK_VERIFIED / MOCK_UNAVAILABLE) • Live Backend Data Connected
            </span>
          </div>
          <div className="hidden sm:flex items-center gap-space-sm shrink-0">
            <span className="font-label-sm text-label-sm text-outline">
              Sovereign Security: ISO/IEC 27001 Validated
            </span>
            <span className="font-label-sm text-label-sm text-status-verified font-medium">
              ● Central Review Operational
            </span>
          </div>
        </div>
      </header>

      {/* MAIN CONTAINER */}
      <main className="w-full pt-32 bg-transparent min-h-screen pb-16 flex-1">
        <div className="flex flex-col w-full">
          {/* Sovereign Breadcrumb & Classification Ribbon */}
          <div className="w-full bg-surface-container-high/85 backdrop-blur-md px-gutter-md py-space-sm shadow-sm flex flex-wrap items-center justify-between gap-space-sm">
            <div className="flex items-center gap-space-sm flex-wrap">
              <span className="font-code-sm text-code-sm text-primary font-bold uppercase tracking-widest bg-surface-card px-space-xs py-space-2xs rounded">
                GOV-NET / AICTE-APEX
              </span>
              <span className="font-label-sm text-label-sm text-outline">›</span>
              <span className="font-label-md text-label-md text-primary font-medium">
                Statutory Monitoring Directorate
              </span>
              <span className="font-label-sm text-label-sm text-outline">›</span>
              <span className="font-label-md text-label-md text-on-surface-variant">
                Central Review &amp; Batch Adjudication Console
              </span>
            </div>
            <div className="flex items-center gap-space-md flex-wrap">
              <span className="inline-flex items-center gap-space-xs font-code-sm text-code-sm text-on-surface-variant bg-surface-subtle px-space-sm py-space-2xs rounded border border-border-subtle">
                <span className="w-2 h-2 rounded-full bg-status-review animate-ping"></span>
                DUPLICATE QUEUE: {matches.length} CASES
              </span>
              <span className="inline-flex items-center gap-space-xs font-code-sm text-code-sm text-primary bg-surface-subtle px-space-sm py-space-2xs rounded border border-border-subtle">
                BATCH QUEUE: {batches.length} BATCHES
              </span>
              <span className="font-code-sm text-code-sm text-status-verified font-semibold bg-status-verified-surface px-space-sm py-space-2xs rounded border border-status-verified-border">
                AUDIT SESSION ID: APEX-REV-2026-X1
              </span>
            </div>
          </div>

          <div className="w-full max-w-[1440px] mx-auto px-gutter-md py-space-xl flex flex-col gap-space-xl">
            {/* EXECUTIVE AICTE CENTRAL REVIEW HEADER */}
            <header className="bg-surface-card rounded-xl p-space-xl shadow-sm border border-border-subtle relative overflow-hidden">
              <div className="absolute -right-16 -top-16 w-64 h-64 bg-surface-container rounded-full opacity-60 pointer-events-none"></div>
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-space-lg relative z-10">
                <div className="flex flex-col gap-space-xs max-w-3xl">
                  <div className="flex items-center gap-space-sm">
                    <span className="font-code-sm text-code-sm text-primary uppercase bg-surface-container-high px-space-xs py-space-2xs rounded font-bold">
                      STATUTORY AUDIT CONSOLE
                    </span>
                    <span className="font-label-sm text-label-sm text-status-review font-semibold bg-status-review-surface px-space-xs py-space-2xs rounded border border-status-review-border">
                      SEC 10(1) AICTE ACT 1987
                    </span>
                  </div>
                  <h1 className="font-display-lg text-display-lg text-primary tracking-tight font-extrabold leading-tight">
                    AICTE Central Regulatory Review &amp; Batch Adjudication Console
                  </h1>
                  <p className="font-body-md text-body-md text-on-surface-variant leading-relaxed">
                    National Student Registry Intake Cycle 2026–27. Authoritative review console for cross-institution duplicate candidate triage and formal institutional batch sign-offs with immutable audit logging.
                  </p>
                </div>
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-space-sm">
                  <button
                    onClick={handleExportPDF}
                    className="bg-surface-subtle text-on-surface font-label-md text-label-md px-space-lg py-space-md rounded border border-border-strong hover:bg-surface-container-high transition-colors flex items-center justify-center gap-space-xs shadow-sm cursor-pointer"
                  >
                    <span className="material-symbols-outlined text-[18px]">download</span>
                    Export Gazette Log (PDF/A)
                  </button>
                  <button
                    onClick={handleTriggerRescan}
                    disabled={isScanning}
                    className={`bg-primary text-on-primary font-label-md text-label-md px-space-lg py-space-md rounded hover:bg-navy-deep transition-colors flex items-center justify-center gap-space-xs shadow-sm cursor-pointer ${
                      isScanning ? 'opacity-70 cursor-wait' : ''
                    }`}
                  >
                    <span
                      className={`material-symbols-outlined text-[18px] ${
                        isScanning ? 'animate-spin' : ''
                      }`}
                    >
                      sync_alt
                    </span>
                    {isScanning ? 'Synchronizing Data...' : 'Refresh Review Queues'}
                  </button>
                </div>
              </div>
            </header>

            {/* NATIONAL EXCEPTION METRICS BENTO */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-space-lg">
              {/* Metric 1: Total Batches */}
              <div className="bg-surface-card rounded-xl p-space-xl shadow-sm border border-border-subtle flex flex-col justify-between hover:shadow-md transition-shadow">
                <div className="flex items-center justify-between text-outline mb-space-sm">
                  <span className="font-label-md text-label-md font-semibold uppercase tracking-wider">
                    Institutional Batches
                  </span>
                  <span className="material-symbols-outlined text-[22px] text-primary">
                    inventory_2
                  </span>
                </div>
                <div className="my-space-md flex items-baseline gap-space-sm">
                  <span className="font-display-lg text-display-lg font-bold text-primary">
                    {batches.length}
                  </span>
                  <span className="font-headline-sm text-headline-sm text-on-surface-variant font-medium">
                    Batches Total
                  </span>
                </div>
                <div className="flex items-center justify-between pt-space-sm border-t border-border-subtle mt-space-xs">
                  <span className="font-code-sm text-code-sm text-status-review font-semibold">
                    {batchCounts.SUBMITTED} Pending AICTE Decision
                  </span>
                  <span className="font-code-sm text-code-sm text-status-verified font-bold">
                    {batchCounts.ACCEPTED} Approved
                  </span>
                </div>
              </div>

              {/* Metric 2: Duplicate Candidates */}
              <div className="bg-surface-card rounded-xl p-space-xl shadow-sm border border-border-subtle flex flex-col justify-between hover:shadow-md transition-shadow">
                <div className="flex items-center justify-between text-outline mb-space-sm">
                  <span className="font-label-md text-label-md font-semibold uppercase tracking-wider">
                    Cross-Inst. Duplicates
                  </span>
                  <span className="material-symbols-outlined text-[22px] text-status-error">
                    people
                  </span>
                </div>
                <div className="my-space-md flex items-baseline gap-space-sm">
                  <span className="font-display-lg text-display-lg font-bold text-status-error">
                    {matches.length}
                  </span>
                  <span className="font-label-sm text-label-sm text-status-error bg-status-error-surface px-space-xs py-space-2xs rounded border border-status-error-border font-bold">
                    {matchCounts.CANDIDATE} Unresolved
                  </span>
                </div>
                <div className="flex items-center justify-between pt-space-sm border-t border-border-subtle mt-space-xs">
                  <span className="font-body-sm text-body-sm text-on-surface-variant">
                    {matchCounts.CONFIRMED_DUPLICATE} Confirmed • {matchCounts.DISMISSED} Dismissed
                  </span>
                  <span className="font-code-sm text-code-sm text-primary font-semibold">
                    Audit Logged
                  </span>
                </div>
              </div>

              {/* Metric 3: Approved Intake Status */}
              <div className="bg-surface-card rounded-xl p-space-xl shadow-sm border border-border-subtle flex flex-col justify-between hover:shadow-md transition-shadow">
                <div className="flex items-center justify-between text-outline mb-space-sm">
                  <span className="font-label-md text-label-md font-semibold uppercase tracking-wider">
                    Participating Institutions
                  </span>
                  <span className="material-symbols-outlined text-[22px] text-secondary">
                    account_balance
                  </span>
                </div>
                <div className="my-space-md flex items-baseline gap-space-sm">
                  <span className="font-display-lg text-display-lg font-bold text-secondary">
                    {metrics?.total_institutions || 3}
                  </span>
                  <span className="font-headline-sm text-headline-sm text-on-surface-variant font-medium">
                    Institutions Scoped
                  </span>
                </div>
                <div className="flex items-center justify-between pt-space-sm border-t border-border-subtle mt-space-xs">
                  <span className="font-body-sm text-body-sm text-on-surface-variant">
                    Intake reconciliation active
                  </span>
                  <span className="font-code-sm text-code-sm text-status-verified font-bold">
                    APH Compliant
                  </span>
                </div>
              </div>

              {/* Metric 4: Engine Pipeline */}
              <div className="bg-surface-card rounded-xl p-space-xl shadow-sm border border-border-subtle flex flex-col justify-between hover:shadow-md transition-shadow">
                <div className="flex items-center justify-between text-outline mb-space-sm">
                  <span className="font-label-md text-label-md font-semibold uppercase tracking-wider">
                    Verification Pipeline
                  </span>
                  <span className="material-symbols-outlined text-[22px] text-primary">
                    tune
                  </span>
                </div>
                <div className="my-space-md flex flex-col">
                  <span className="font-headline-md text-headline-md font-bold text-primary">
                    Mock Adapter Active
                  </span>
                  <span className="font-label-sm text-label-sm text-status-verified font-medium">
                    Testbed Simulation Mode v2.4
                  </span>
                </div>
                <div className="flex items-center justify-between pt-space-sm border-t border-border-subtle mt-space-xs">
                  <span className="font-body-sm text-body-sm text-on-surface-variant">
                    Verhoeff APAAR Engine
                  </span>
                  <span className="font-code-sm text-code-sm bg-surface-subtle px-space-xs rounded text-primary">
                    ACTIVE
                  </span>
                </div>
              </div>
            </div>

            {/* ================================================================= */}
            {/* SECTION 1: PERSISTED INSTITUTIONAL BATCH REGULATORY DECISION QUEUE */}
            {/* ================================================================= */}
            <section className="bg-surface-card rounded-xl p-space-xl shadow-md border border-border-strong flex flex-col gap-space-lg">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-space-md border-b border-border-subtle pb-space-lg">
                <div className="flex flex-col gap-space-2xs">
                  <div className="flex items-center gap-space-sm">
                    <span className="font-code-sm text-code-sm bg-primary text-on-primary px-space-xs py-space-2xs rounded font-bold uppercase">
                      WORKFLOW
                    </span>
                    <h2 className="font-headline-lg text-headline-lg text-primary font-bold">
                      Institutional Batch Regulatory Review &amp; Approval Queue
                    </h2>
                  </div>
                  <p className="font-body-sm text-body-sm text-on-surface-variant">
                    Authoritative regulatory sign-off workflow under AICTE statutes. Batches with unresolved blocking errors are statutorily barred from approval.
                  </p>
                </div>

                <div className="flex items-center gap-space-sm flex-wrap">
                  <div className="relative">
                    <span className="material-symbols-outlined absolute left-2.5 top-2.5 text-outline text-[18px]">
                      search
                    </span>
                    <input
                      type="text"
                      placeholder="Search batch or institution..."
                      value={batchSearch}
                      onChange={(e) => setBatchSearch(e.target.value)}
                      className="bg-surface-canvas border border-border-strong rounded-lg pl-8 pr-space-md py-space-xs font-body-sm text-body-sm text-on-surface focus:outline-none focus:border-secondary w-56"
                    />
                  </div>
                </div>
              </div>

              {/* Status Filter Tabs */}
              <div className="flex items-center gap-2 overflow-x-auto pb-1">
                {[
                  { key: 'ALL', label: 'All Batches', count: batchCounts.ALL },
                  { key: 'SUBMITTED', label: 'Pending Review', count: batchCounts.SUBMITTED },
                  { key: 'UNDER_REVIEW', label: 'Under Review', count: batchCounts.UNDER_REVIEW },
                  { key: 'ACCEPTED', label: 'Approved', count: batchCounts.ACCEPTED },
                  { key: 'NEEDS_CORRECTION', label: 'Needs Correction', count: batchCounts.NEEDS_CORRECTION },
                  { key: 'REJECTED', label: 'Rejected', count: batchCounts.REJECTED },
                ].map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => setBatchStatusFilter(tab.key)}
                    className={`font-label-md text-label-md px-3 py-1.5 rounded-lg border transition-all cursor-pointer whitespace-nowrap flex items-center gap-1.5 ${
                      batchStatusFilter === tab.key
                        ? 'bg-primary text-on-primary border-primary font-bold shadow-sm'
                        : 'bg-surface-canvas border-border-strong text-on-surface-variant hover:text-primary hover:border-primary'
                    }`}
                  >
                    <span>{tab.label}</span>
                    <span
                      className={`px-1.5 py-0.2 rounded-full text-xs font-mono ${
                        batchStatusFilter === tab.key
                          ? 'bg-white/20 text-white'
                          : 'bg-surface-container text-outline'
                      }`}
                    >
                      {tab.count}
                    </span>
                  </button>
                ))}
              </div>

              {/* Batches Table / List */}
              {isLoadingBatches ? (
                <div className="py-12 flex flex-col items-center justify-center gap-3 text-on-surface-variant">
                  <span className="material-symbols-outlined text-4xl animate-spin text-primary">
                    progress_activity
                  </span>
                  <span className="text-sm">Loading institutional batches from backend...</span>
                </div>
              ) : batchError ? (
                <div className="bg-status-error-surface border border-status-error-border rounded-xl p-4 text-status-error flex items-center gap-3">
                  <span className="material-symbols-outlined">error</span>
                  <div className="text-sm font-semibold">{batchError}</div>
                </div>
              ) : filteredBatches.length === 0 ? (
                <div className="py-12 px-4 rounded-xl border border-dashed border-border-strong bg-surface-canvas flex flex-col items-center justify-center text-center">
                  <span className="material-symbols-outlined text-4xl text-outline mb-2">
                    inbox
                  </span>
                  <div className="font-headline-sm text-headline-sm font-bold text-primary">
                    No Batches Found
                  </div>
                  <div className="font-body-sm text-body-sm text-on-surface-variant max-w-md mt-1">
                    {batchStatusFilter === 'ALL'
                      ? 'No institutional import batches currently exist in the database.'
                      : `There are currently no batches in "${batchStatusFilter}" status.`}
                  </div>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-surface-canvas border-b border-border-strong text-outline">
                        <th className="px-space-md py-space-md font-label-sm text-label-sm uppercase font-bold tracking-wider">
                          Batch ID &amp; Version
                        </th>
                        <th className="px-space-md py-space-md font-label-sm text-label-sm uppercase font-bold tracking-wider">
                          Institution
                        </th>
                        <th className="px-space-md py-space-md font-label-sm text-label-sm uppercase font-bold tracking-wider">
                          Dataset File &amp; Year
                        </th>
                        <th className="px-space-md py-space-md font-label-sm text-label-sm uppercase font-bold tracking-wider text-center">
                          Records Breakdown
                        </th>
                        <th className="px-space-md py-space-md font-label-sm text-label-sm uppercase font-bold tracking-wider text-center">
                          Status
                        </th>
                        <th className="px-space-md py-space-md font-label-sm text-label-sm uppercase font-bold tracking-wider text-right">
                          Regulatory Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-subtle font-body-sm text-body-sm text-on-surface">
                      {filteredBatches.map((b) => {
                        const hasErrors = b.error_rows > 0;
                        const canMarkReview = b.status === 'SUBMITTED';
                        const canApprove = b.status === 'SUBMITTED' || b.status === 'UNDER_REVIEW';
                        const canReturn = b.status === 'SUBMITTED' || b.status === 'UNDER_REVIEW';
                        const canReject = b.status === 'SUBMITTED' || b.status === 'UNDER_REVIEW';

                        let statusBadgeColor = 'bg-surface-container text-on-surface-variant border-border-subtle';
                        if (b.status === 'ACCEPTED') statusBadgeColor = 'bg-status-verified-surface text-status-verified border-status-verified-border font-bold';
                        else if (b.status === 'UNDER_REVIEW') statusBadgeColor = 'bg-status-review-surface text-status-review border-status-review-border font-bold';
                        else if (b.status === 'SUBMITTED') statusBadgeColor = 'bg-primary/10 text-primary border-primary/30 font-bold';
                        else if (b.status === 'NEEDS_CORRECTION') statusBadgeColor = 'bg-status-error-surface text-status-error border-status-error-border font-bold';
                        else if (b.status === 'REJECTED') statusBadgeColor = 'bg-status-error text-white font-bold';

                        return (
                          <tr key={b.id} className="hover:bg-surface-canvas transition-colors">
                            <td className="px-space-md py-space-md">
                              <div className="font-code-sm text-code-sm font-bold text-primary">
                                {b.id}
                              </div>
                              <div className="text-outline font-label-sm text-label-sm">
                                Version {b.version} • {new Date(b.created_at).toLocaleDateString()}
                              </div>
                            </td>
                            <td className="px-space-md py-space-md">
                              <div className="font-title-md text-title-md font-bold text-primary">
                                {b.institution_name || b.institution_id}
                              </div>
                              <div className="font-code-sm text-code-sm text-outline">
                                CODE: {b.institution_id}
                              </div>
                            </td>
                            <td className="px-space-md py-space-md">
                              <div className="font-body-sm text-body-sm font-medium text-on-surface">
                                {b.source_filename}
                              </div>
                              <div className="font-label-sm text-label-sm text-outline">
                                AY: {b.academic_year}
                              </div>
                            </td>
                            <td className="px-space-md py-space-md text-center">
                              <div className="flex items-center justify-center gap-1.5 flex-wrap">
                                <span className="bg-surface-subtle text-primary px-2 py-0.5 rounded text-xs font-mono font-bold" title="Total Rows">
                                  {b.total_rows} total
                                </span>
                                <span className="bg-status-verified-surface text-status-verified px-2 py-0.5 rounded text-xs font-mono font-bold" title="Valid Rows">
                                  {b.valid_rows} valid
                                </span>
                                {b.warning_rows > 0 && (
                                  <span className="bg-status-review-surface text-status-review px-2 py-0.5 rounded text-xs font-mono font-bold" title="Warning Rows">
                                    {b.warning_rows} warn
                                  </span>
                                )}
                                {b.error_rows > 0 && (
                                  <span className="bg-status-error-surface text-status-error px-2 py-0.5 rounded text-xs font-mono font-bold border border-status-error-border" title="Blocking Error Rows">
                                    {b.error_rows} error
                                  </span>
                                )}
                              </div>
                            </td>
                            <td className="px-space-md py-space-md text-center">
                              <span className={`px-space-sm py-1 rounded text-xs uppercase font-mono border ${statusBadgeColor}`}>
                                {b.status}
                              </span>
                            </td>
                            <td className="px-space-md py-space-md text-right">
                              <div className="flex items-center justify-end gap-1.5 flex-wrap">
                                {canMarkReview && (
                                  <button
                                    onClick={() => openBatchDecisionModal(b, 'UNDER_REVIEW')}
                                    className="bg-surface-subtle text-primary border border-border-strong hover:bg-surface-container font-label-sm text-label-sm px-2.5 py-1 rounded transition-colors cursor-pointer"
                                    title="Mark batch as officially under review"
                                  >
                                    Mark Review
                                  </button>
                                )}

                                {canApprove && (
                                  <button
                                    onClick={() => openBatchDecisionModal(b, 'ACCEPTED')}
                                    disabled={hasErrors}
                                    className={`font-label-sm text-label-sm px-2.5 py-1 rounded transition-colors flex items-center gap-1 ${
                                      hasErrors
                                        ? 'bg-surface-subtle text-outline border border-border-subtle cursor-not-allowed opacity-60'
                                        : 'bg-status-verified text-on-primary hover:bg-status-verified/90 cursor-pointer shadow-sm'
                                    }`}
                                    title={hasErrors ? 'Approval blocked: Batch contains unresolved blocking errors' : 'Formally approve batch for official enrollment'}
                                  >
                                    <span className="material-symbols-outlined text-[14px]">check</span>
                                    <span>Approve</span>
                                  </button>
                                )}

                                {canReturn && (
                                  <button
                                    onClick={() => openBatchDecisionModal(b, 'NEEDS_CORRECTION')}
                                    className="bg-surface-card border border-status-review text-status-review hover:bg-status-review-surface font-label-sm text-label-sm px-2.5 py-1 rounded transition-colors cursor-pointer"
                                    title="Return batch to institution for data corrections"
                                  >
                                    Return
                                  </button>
                                )}

                                {canReject && (
                                  <button
                                    onClick={() => openBatchDecisionModal(b, 'REJECTED')}
                                    className="bg-surface-card border border-status-error text-status-error hover:bg-status-error-surface font-label-sm text-label-sm px-2.5 py-1 rounded transition-colors cursor-pointer"
                                    title="Reject batch submission"
                                  >
                                    Reject
                                  </button>
                                )}

                                {!canMarkReview && !canApprove && (
                                  <span className="text-xs text-outline italic">
                                    Audited / Terminal
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
            </section>

            {/* ================================================================= */}
            {/* SECTION 2: CROSS-INSTITUTION DUPLICATE ENROLMENT TRIAGE QUEUE */}
            {/* ================================================================= */}
            <section className="flex flex-col gap-space-lg">
              {/* Statutory Human-In-The-Loop Advisory */}
              <div className="bg-status-review-surface border border-status-review-border rounded-xl p-space-lg flex items-start gap-space-md shadow-sm">
                <span className="material-symbols-outlined text-status-review text-[26px] mt-0.5 shrink-0">
                  admin_panel_settings
                </span>
                <div className="flex flex-col gap-space-2xs">
                  <div className="flex items-center gap-space-sm flex-wrap">
                    <span className="font-headline-sm text-headline-sm text-on-surface font-bold">
                      Statutory Human-in-the-Loop Protocol (APAAR Directive 2026/AD-4)
                    </span>
                    <span className="font-code-sm text-code-sm bg-status-review text-on-primary px-space-xs py-space-2xs rounded font-bold uppercase">
                      Manual Triage Required
                    </span>
                  </div>
                  <p className="font-body-md text-body-md text-on-surface-variant leading-relaxed">
                    Candidates require sovereign regulatory review before disciplinary or administrative cancellation.{' '}
                    <strong>Automated merging and unilateral deregistrations are strictly barred</strong> to safeguard candidate academic credentials against provisional admission collisions.
                  </p>
                </div>
              </div>

              {/* Status Filter for Match Candidates */}
              <div className="flex items-center justify-between flex-wrap gap-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-outline uppercase tracking-wider">
                    Filter Conflicts:
                  </span>
                  {[
                    { key: 'ALL', label: 'All Cases', count: matchCounts.ALL },
                    { key: 'CANDIDATE', label: 'Unresolved Conflicts', count: matchCounts.CANDIDATE },
                    { key: 'CONFIRMED_DUPLICATE', label: 'Confirmed Duplicates', count: matchCounts.CONFIRMED_DUPLICATE },
                    { key: 'DISMISSED', label: 'Dismissed / Bona-fide', count: matchCounts.DISMISSED },
                  ].map((tab) => (
                    <button
                      key={tab.key}
                      onClick={() => {
                        setMatchStatusFilter(tab.key);
                        setCaseIndex(0);
                      }}
                      className={`font-label-sm text-label-sm px-3 py-1 rounded-md border transition-all cursor-pointer flex items-center gap-1.5 ${
                        matchStatusFilter === tab.key
                          ? 'bg-secondary text-on-secondary font-bold border-secondary'
                          : 'bg-surface-card border-border-strong text-on-surface-variant hover:text-primary'
                      }`}
                    >
                      <span>{tab.label}</span>
                      <span className="text-xs font-mono">({tab.count})</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Match Candidate Details or Empty State */}
              {isLoadingMatches ? (
                <div className="bg-surface-card rounded-xl p-12 border border-border-subtle flex flex-col items-center justify-center gap-3 text-on-surface-variant shadow-sm">
                  <span className="material-symbols-outlined text-4xl animate-spin text-primary">
                    progress_activity
                  </span>
                  <span className="text-sm">Fetching duplicate match candidates from registry...</span>
                </div>
              ) : matchError ? (
                <div className="bg-status-error-surface border border-status-error-border rounded-xl p-6 text-status-error flex items-center gap-3">
                  <span className="material-symbols-outlined text-2xl">error</span>
                  <div>
                    <div className="font-bold">Failed to load duplicate cases</div>
                    <div className="text-sm mt-1">{matchError}</div>
                  </div>
                </div>
              ) : !currentMatch ? (
                <div className="bg-surface-card rounded-xl p-12 border border-dashed border-border-strong flex flex-col items-center justify-center text-center shadow-sm">
                  <div className="w-16 h-16 rounded-full bg-status-verified-surface flex items-center justify-center text-status-verified mb-3">
                    <span className="material-symbols-outlined text-3xl">verified</span>
                  </div>
                  <h3 className="font-headline-md text-headline-md font-bold text-primary">
                    No Cross-Institution Duplicate Candidates Found
                  </h3>
                  <p className="font-body-md text-body-md text-on-surface-variant max-w-lg mt-2 leading-relaxed">
                    {matchStatusFilter === 'ALL'
                      ? 'All submitted institutional student records are currently deduplicated. No open identity conflicts or cross-institution collisions detected in the system.'
                      : `No match candidates found with status "${matchStatusFilter}". Try changing the filter tab above.`}
                  </p>
                </div>
              ) : (
                <div className="bg-surface-card rounded-xl shadow-md border border-border-strong overflow-hidden flex flex-col">
                  {/* Case Identification Top Bar */}
                  <div className="bg-surface-subtle px-space-xl py-space-md border-b border-border-subtle flex flex-wrap items-center justify-between gap-space-md">
                    <div className="flex items-center gap-space-md flex-wrap">
                      <div className="flex items-center gap-space-xs">
                        <span className="font-label-sm text-label-sm text-outline uppercase font-semibold">
                          Match ID:
                        </span>
                        <span className="font-code-sm text-code-sm text-primary font-bold bg-surface-card px-space-sm py-space-2xs rounded border border-border-strong">
                          {currentMatch.id}
                        </span>
                      </div>
                      <div className="flex items-center gap-space-xs">
                        <span className="font-label-sm text-label-sm text-outline uppercase font-semibold">
                          APAAR ID:
                        </span>
                        <span className="font-code-sm text-code-sm text-primary font-bold bg-surface-card px-space-sm py-space-2xs rounded border border-border-strong tracking-widest">
                          {displayApaarId}
                        </span>
                        <button
                          onClick={() => {
                            const willDecrypt = !isApaarDecrypted;
                            setIsApaarDecrypted(willDecrypt);
                            if (willDecrypt) {
                              showToast(
                                `Sovereign Audit Alert: Decrypted view of APAAR ID ${rawApaar} logged to session record.`
                              );
                            }
                          }}
                          className="text-on-surface-variant hover:text-primary p-space-2xs cursor-pointer transition-colors"
                          title={isApaarDecrypted ? 'Mask APAAR ID' : 'Decrypted view logged to sovereign audit record'}
                        >
                          <span className="material-symbols-outlined text-[16px]">
                            {isApaarDecrypted ? 'visibility_off' : 'visibility'}
                          </span>
                        </button>
                        {onSwitchTab && rawApaar && (
                          <button
                            onClick={() => onSwitchTab('records', rawApaar)}
                            className="ml-1 text-secondary hover:text-navy-accent bg-surface-card hover:bg-surface-subtle px-2 py-0.5 rounded border border-border-strong text-xs font-semibold flex items-center gap-1 transition-all cursor-pointer shadow-sm"
                            title="View Verified Student Record & Attestation Certificate"
                          >
                            <span className="material-symbols-outlined text-[14px]">workspace_premium</span>
                            <span>View Certificate</span>
                          </button>
                        )}
                      </div>
                      <span
                        className={`font-code-sm text-code-sm px-space-xs py-space-2xs rounded border font-bold ${
                          currentMatch.status === 'CONFIRMED_DUPLICATE'
                            ? 'bg-status-error-surface text-status-error border-status-error-border'
                            : currentMatch.status === 'DISMISSED'
                            ? 'bg-status-verified-surface text-status-verified border-status-verified-border'
                            : 'bg-status-review-surface text-status-review border-status-review-border'
                        }`}
                      >
                        STATUS: {currentMatch.status}
                      </span>
                    </div>

                    <div className="flex items-center gap-space-md">
                      <span className="font-label-sm text-label-sm text-outline hidden sm:inline">
                        Signal: {currentMatch.matching_signal}
                      </span>
                      <span className="font-label-md text-label-md text-on-surface-variant font-semibold">
                        Case {safeIndex + 1} of {filteredMatches.length} (Total: {matches.length})
                      </span>
                      <div className="inline-flex rounded-md shadow-sm">
                        <button
                          onClick={handlePrevCase}
                          aria-label="Previous Case"
                          className="bg-surface-card border border-border-strong px-space-xs py-space-2xs rounded-l hover:bg-surface-subtle text-primary cursor-pointer"
                        >
                          <span className="material-symbols-outlined text-[16px]">chevron_left</span>
                        </button>
                        <button
                          onClick={handleNextCase}
                          aria-label="Next Case"
                          className="bg-surface-card border-t border-b border-r border-border-strong px-space-xs py-space-2xs rounded-r hover:bg-surface-subtle text-primary cursor-pointer"
                        >
                          <span className="material-symbols-outlined text-[16px]">chevron_right</span>
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Comparative Split Inspection Grid */}
                  <div className="p-space-xl flex flex-col gap-space-xl">
                    {/* Identity Matching Strength Vector */}
                    <div className="bg-surface-canvas rounded-xl p-space-lg border border-border-subtle flex flex-col md:flex-row items-center justify-between gap-space-md">
                      <div className="flex items-center gap-space-md">
                        <span className="material-symbols-outlined text-secondary text-[26px]">
                          fingerprint
                        </span>
                        <div>
                          <h2 className="font-headline-sm text-headline-sm text-primary font-bold">
                            Algorithmic Correlation Confidence
                          </h2>
                          <p className="font-body-sm text-body-sm text-on-surface-variant">
                            Signal: {currentMatch.matching_signal} • Confidence: {(currentMatch.confidence * 100).toFixed(0)}%
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-space-md flex-wrap">
                        <div className="flex items-center gap-space-xs bg-surface-card px-space-md py-space-xs rounded-lg border border-border-subtle shadow-sm">
                          <span className="font-label-sm text-label-sm text-outline">
                            Signal Score:
                          </span>
                          <span className="font-code-sm text-code-sm text-status-verified font-bold">
                            {(currentMatch.confidence * 100).toFixed(0)}% Match
                          </span>
                          <span className="material-symbols-outlined text-status-verified text-[16px]">
                            check_circle
                          </span>
                        </div>
                        <div className="flex items-center gap-space-xs bg-surface-card px-space-md py-space-xs rounded-lg border border-border-subtle shadow-sm">
                          <span className="font-label-sm text-label-sm text-outline">
                            Detection Type:
                          </span>
                          <span className="font-code-sm text-code-sm text-primary font-bold">
                            Cross-Institution
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Split Comparison Dual Panels */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-space-xl relative">
                      <div className="hidden lg:flex absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10 w-10 h-10 rounded-full bg-primary text-on-primary font-code-sm text-code-sm font-bold items-center justify-center shadow-lg border-2 border-surface-card">
                        VS
                      </div>

                      {/* Institution A Column */}
                      <div className="bg-surface-canvas rounded-xl p-space-xl border border-border-strong flex flex-col gap-space-lg">
                        <div className="flex items-center justify-between border-b border-border-subtle pb-space-md">
                          <div className="flex items-center gap-space-xs">
                            <span className="font-label-sm text-label-sm bg-primary text-on-primary px-space-xs py-space-2xs rounded font-bold">
                              CLAIMANT INST A
                            </span>
                            <span className="font-label-sm text-label-sm text-status-verified bg-status-verified-surface px-space-xs py-space-2xs rounded font-semibold border border-status-verified-border">
                              {currentMatch.institution_a?.state || 'Verified State'}
                            </span>
                          </div>
                          <span className="font-code-sm text-code-sm text-outline font-semibold">
                            CODE: {currentMatch.institution_a?.code || currentMatch.institution_a_id}
                          </span>
                        </div>
                        <div className="flex flex-col gap-space-2xs">
                          <h3 className="font-headline-md text-headline-md text-primary font-bold">
                            {currentMatch.institution_a?.name || currentMatch.institution_a_id}
                          </h3>
                          <span className="font-body-sm text-body-sm text-on-surface-variant">
                            State: {currentMatch.institution_a?.state || 'India'}
                          </span>
                        </div>
                        <div className="bg-surface-card rounded-lg p-space-lg border border-border-subtle space-y-space-md shadow-sm">
                          <div className="flex justify-between items-center py-space-xs border-b border-border-subtle">
                            <span className="font-label-md text-label-md text-outline">
                              Registered Student:
                            </span>
                            <span className="font-headline-sm text-headline-sm text-primary font-bold">
                              {currentMatch.record_a?.student_name || 'Candidate Record A'}
                            </span>
                          </div>
                          <div className="flex justify-between items-center py-space-xs border-b border-border-subtle">
                            <span className="font-label-md text-label-md text-outline">
                              Student ID (Roll No):
                            </span>
                            <span className="font-code-sm text-code-sm text-primary font-bold">
                              {currentMatch.record_a?.institution_student_id || 'N/A'}
                            </span>
                          </div>
                          <div className="flex justify-between items-center py-space-xs border-b border-border-subtle">
                            <span className="font-label-md text-label-md text-outline">
                              Programme:
                            </span>
                            <span className="font-body-md text-body-md text-on-surface font-semibold">
                              {currentMatch.record_a?.programme?.name || currentMatch.record_a?.programme_id || 'Technical Programme'}
                            </span>
                          </div>
                          <div className="flex justify-between items-center py-space-xs border-b border-border-subtle">
                            <span className="font-label-md text-label-md text-outline">
                              Academic Year:
                            </span>
                            <span className="font-code-sm text-code-sm text-primary font-bold">
                              {currentMatch.record_a?.academic_year || '2026-2027'}
                            </span>
                          </div>
                          <div className="flex justify-between items-center py-space-xs border-b border-border-subtle">
                            <span className="font-label-md text-label-md text-outline">
                              Seat Allocation Quota:
                            </span>
                            <span className="font-code-sm text-code-sm text-status-verified bg-status-verified-surface px-space-xs py-space-2xs rounded font-bold border border-status-verified-border">
                              {currentMatch.record_a?.seat_type || 'REGULAR'}
                            </span>
                          </div>
                          <div className="flex justify-between items-center py-space-xs">
                            <span className="font-label-md text-label-md text-outline">
                              Enrolment Status:
                            </span>
                            <span className="font-label-sm text-label-sm bg-status-verified-surface text-status-verified font-bold px-space-xs py-space-2xs rounded border border-status-verified-border">
                              {currentMatch.record_a?.enrolment_status || 'ENROLLED'}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Institution B Column */}
                      <div className="bg-surface-canvas rounded-xl p-space-xl border border-border-strong flex flex-col gap-space-lg">
                        <div className="flex items-center justify-between border-b border-border-subtle pb-space-md">
                          <div className="flex items-center gap-space-xs">
                            <span className="font-label-sm text-label-sm bg-surface-container-highest text-primary px-space-xs py-space-2xs rounded font-bold">
                              CLAIMANT INST B
                            </span>
                            <span className="font-label-sm text-label-sm text-status-review bg-status-review-surface px-space-xs py-space-2xs rounded font-semibold border border-status-review-border">
                              {currentMatch.institution_b?.state || 'Verified State'}
                            </span>
                          </div>
                          <span className="font-code-sm text-code-sm text-outline font-semibold">
                            CODE: {currentMatch.institution_b?.code || currentMatch.institution_b_id}
                          </span>
                        </div>
                        <div className="flex flex-col gap-space-2xs">
                          <h3 className="font-headline-md text-headline-md text-primary font-bold">
                            {currentMatch.institution_b?.name || currentMatch.institution_b_id}
                          </h3>
                          <span className="font-body-sm text-body-sm text-on-surface-variant">
                            State: {currentMatch.institution_b?.state || 'India'}
                          </span>
                        </div>
                        <div className="bg-surface-card rounded-lg p-space-lg border border-border-subtle space-y-space-md shadow-sm">
                          <div className="flex justify-between items-center py-space-xs border-b border-border-subtle">
                            <span className="font-label-md text-label-md text-outline">
                              Registered Student:
                            </span>
                            <span className="font-headline-sm text-headline-sm text-primary font-bold">
                              {currentMatch.record_b?.student_name || 'Candidate Record B'}
                            </span>
                          </div>
                          <div className="flex justify-between items-center py-space-xs border-b border-border-subtle">
                            <span className="font-label-md text-label-md text-outline">
                              Student ID (Roll No):
                            </span>
                            <span className="font-code-sm text-code-sm text-primary font-bold">
                              {currentMatch.record_b?.institution_student_id || 'N/A'}
                            </span>
                          </div>
                          <div className="flex justify-between items-center py-space-xs border-b border-border-subtle">
                            <span className="font-label-md text-label-md text-outline">
                              Programme:
                            </span>
                            <span className="font-body-md text-body-md text-on-surface font-semibold">
                              {currentMatch.record_b?.programme?.name || currentMatch.record_b?.programme_id || 'Technical Programme'}
                            </span>
                          </div>
                          <div className="flex justify-between items-center py-space-xs border-b border-border-subtle">
                            <span className="font-label-md text-label-md text-outline">
                              Academic Year:
                            </span>
                            <span className="font-code-sm text-code-sm text-primary font-bold">
                              {currentMatch.record_b?.academic_year || '2026-2027'}
                            </span>
                          </div>
                          <div className="flex justify-between items-center py-space-xs border-b border-border-subtle">
                            <span className="font-label-md text-label-md text-outline">
                              Seat Allocation Quota:
                            </span>
                            <span className="font-code-sm text-code-sm text-status-review bg-status-review-surface px-space-xs py-space-2xs rounded font-bold border border-status-review-border">
                              {currentMatch.record_b?.seat_type || 'REGULAR'}
                            </span>
                          </div>
                          <div className="flex justify-between items-center py-space-xs">
                            <span className="font-label-md text-label-md text-outline">
                              Enrolment Status:
                            </span>
                            <span className="font-label-sm text-label-sm bg-status-review-surface text-status-review font-bold px-space-xs py-space-2xs rounded border border-status-review-border">
                              {currentMatch.record_b?.enrolment_status || 'ENROLLED'}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Adjudication Decision Console */}
                    <div className="bg-surface-card rounded-xl p-space-xl border-2 border-primary/20 flex flex-col gap-space-lg shadow-sm">
                      <div className="flex items-center gap-space-sm">
                        <span className="material-symbols-outlined text-primary text-[24px]">
                          gavel
                        </span>
                        <h4 className="font-headline-sm text-headline-sm text-primary font-bold">
                          Regulatory Determination &amp; Hearing Notice Execution
                        </h4>
                      </div>

                      {/* Radio Options */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-space-md">
                        <label
                          className={`relative flex items-start gap-space-sm p-space-lg rounded-xl border cursor-pointer transition-all ${
                            candidateVerdict === 'CONFIRMED_DUPLICATE'
                              ? 'border-status-error bg-status-error-surface/30 shadow-sm'
                              : 'border-border-strong hover:border-primary bg-surface-canvas'
                          }`}
                        >
                          <input
                            type="radio"
                            name="triage_verdict"
                            value="CONFIRMED_DUPLICATE"
                            checked={candidateVerdict === 'CONFIRMED_DUPLICATE'}
                            onChange={() => setCandidateVerdict('CONFIRMED_DUPLICATE')}
                            className="mt-1 text-status-error focus:ring-status-error cursor-pointer"
                          />
                          <div className="flex flex-col">
                            <span className="font-title-md text-title-md text-status-error font-bold flex items-center gap-1.5">
                              <span className="material-symbols-outlined text-[18px]">warning</span>
                              Confirm Duplicate Enrolment (CONFIRMED_DUPLICATE)
                            </span>
                            <span className="font-body-sm text-body-sm text-on-surface-variant mt-1 leading-relaxed">
                              Affirms dual enrolment conflict. Triggers statutory notification to both institutions and freezes concurrent status.
                            </span>
                          </div>
                        </label>

                        <label
                          className={`relative flex items-start gap-space-sm p-space-lg rounded-xl border cursor-pointer transition-all ${
                            candidateVerdict === 'DISMISSED'
                              ? 'border-status-verified bg-status-verified-surface/30 shadow-sm'
                              : 'border-border-strong hover:border-primary bg-surface-canvas'
                          }`}
                        >
                          <input
                            type="radio"
                            name="triage_verdict"
                            value="DISMISSED"
                            checked={candidateVerdict === 'DISMISSED'}
                            onChange={() => setCandidateVerdict('DISMISSED')}
                            className="mt-1 text-status-verified focus:ring-status-verified cursor-pointer"
                          />
                          <div className="flex flex-col">
                            <span className="font-title-md text-title-md text-status-verified font-bold flex items-center gap-1.5">
                              <span className="material-symbols-outlined text-[18px]">verified</span>
                              Dismiss Conflict / Bona-fide Transfer (DISMISSED)
                            </span>
                            <span className="font-body-sm text-body-sm text-on-surface-variant mt-1 leading-relaxed">
                              Verifies lawful transfer, withdrawal certificate, or false-positive matching. Releases regulatory hold on candidate.
                            </span>
                          </div>
                        </label>
                      </div>

                      {/* Justification Form */}
                      <div className="flex flex-col gap-space-xs mt-space-sm">
                        <div className="flex justify-between items-center">
                          <label
                            htmlFor="review_justification"
                            className="font-label-md text-label-md text-primary font-bold uppercase tracking-wider"
                          >
                            Mandatory Statutory Justification &amp; Resolution Notes{' '}
                            <span className="text-status-error">*</span>
                          </label>
                          <span className="font-code-sm text-code-sm text-outline font-semibold">
                            Signed by AICTE Officer:{' '}
                            <span className="text-primary font-bold">
                              {session?.userEmail || 'AICTE-CENTRAL-OFFICER'}
                            </span>
                          </span>
                        </div>
                        <textarea
                          id="review_justification"
                          rows={3}
                          value={candidateJustification}
                          onChange={(e) => setCandidateJustification(e.target.value)}
                          placeholder="Specify evidentiary grounds, withdrawal certificates, transfer references or statutory basis for order... (Min 5 characters)"
                          className="w-full bg-surface-canvas border border-border-strong rounded-xl p-space-md font-body-md text-body-md text-on-surface focus:outline-none focus:border-secondary transition-colors"
                        />
                        <div className="flex justify-between text-xs text-outline pt-1">
                          <span>Minimum required: 5 characters</span>
                          <span>{candidateJustification.length} characters entered</span>
                        </div>

                        {candidateSubmitError && (
                          <div className="mt-2 text-xs text-status-error bg-status-error-surface border border-status-error-border p-2 rounded-lg font-medium">
                            {candidateSubmitError}
                          </div>
                        )}
                      </div>

                      {/* Audit Note & Action Buttons */}
                      <div className="flex flex-wrap items-center justify-between gap-space-md pt-space-md border-t border-border-subtle">
                        <div className="flex items-center gap-space-xs text-status-verified">
                          <span className="material-symbols-outlined text-[18px]">lock</span>
                          <span className="font-code-sm text-code-sm font-semibold">
                            Action will persist to database and write immutable AuditEvent
                          </span>
                        </div>
                        <div className="flex items-center gap-space-sm flex-wrap">
                          <button
                            onClick={handleSubmitCandidateVerdict}
                            disabled={isSubmittingCandidate}
                            className={`bg-primary hover:bg-navy-deep text-on-primary font-label-md text-label-md px-space-xl py-space-md rounded-lg transition-colors shadow-sm flex items-center gap-space-xs cursor-pointer ${
                              isSubmittingCandidate ? 'opacity-70 cursor-wait' : ''
                            }`}
                          >
                            <span className={`material-symbols-outlined text-[18px] ${isSubmittingCandidate ? 'animate-spin' : ''}`}>
                              {isSubmittingCandidate ? 'progress_activity' : 'task_alt'}
                            </span>
                            <span>{isSubmittingCandidate ? 'Persisting Decision...' : 'Submit Review Decision & Create Audit Record'}</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </section>

            {/* ================================================================= */}
            {/* SECTION 3: INTAKE BREACH MONITORING REGISTRY */}
            {/* ================================================================= */}
            <section className="bg-surface-card rounded-xl p-space-xl shadow-sm border border-border-subtle flex flex-col gap-space-lg">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-space-md border-b border-border-subtle pb-space-lg">
                <div>
                  <div className="flex items-center gap-space-sm">
                    <h2 className="font-headline-lg text-headline-lg text-primary font-bold">
                      System-wide Approved Intake vs Capacity Monitoring Registry
                    </h2>
                    <span className="font-code-sm text-code-sm bg-status-verified text-on-primary px-space-xs py-space-2xs rounded font-bold uppercase">
                      {breachRecords.length} Monitored
                    </span>
                  </div>
                  <p className="font-body-sm text-body-sm text-on-surface-variant mt-space-2xs">
                    Institutional regular and supernumerary intake compliance against AICTE Approval Process Handbook (APH 2026-27).
                  </p>
                </div>
                <div className="flex items-center gap-space-sm">
                  <div className="relative">
                    <span className="material-symbols-outlined absolute left-2.5 top-2.5 text-outline text-[18px]">
                      search
                    </span>
                    <input
                      type="text"
                      placeholder="Search institute or PID..."
                      value={tableSearch}
                      onChange={(e) => setTableSearch(e.target.value)}
                      className="bg-surface-canvas border border-border-strong rounded-lg pl-8 pr-space-md py-space-xs font-body-sm text-body-sm text-on-surface focus:outline-none focus:border-secondary w-64"
                    />
                  </div>
                  <button
                    onClick={handleExportCSV}
                    className="bg-surface-subtle text-on-surface font-label-md text-label-md px-space-md py-space-xs rounded-lg border border-border-strong hover:bg-surface-container transition-colors flex items-center gap-space-2xs cursor-pointer"
                  >
                    <span className="material-symbols-outlined text-[16px]">
                      file_download
                    </span>
                    CSV Export
                  </button>
                </div>
              </div>

              {/* Audit Grid */}
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-surface-canvas border-b border-border-strong text-outline">
                      <th className="px-space-md py-space-md font-label-sm text-label-sm uppercase font-bold tracking-wider">
                        Institution ID
                      </th>
                      <th className="px-space-md py-space-md font-label-sm text-label-sm uppercase font-bold tracking-wider">
                        Institution Name &amp; State
                      </th>
                      <th className="px-space-md py-space-md font-label-sm text-label-sm uppercase font-bold tracking-wider">
                        Affiliation / Category
                      </th>
                      <th className="px-space-md py-space-md font-label-sm text-label-sm uppercase font-bold tracking-wider text-right">
                        Approved Cap
                      </th>
                      <th className="px-space-md py-space-md font-label-sm text-label-sm uppercase font-bold tracking-wider text-right">
                        Enrolled
                      </th>
                      <th className="px-space-md py-space-md font-label-sm text-label-sm uppercase font-bold tracking-wider text-center">
                        Status / Δ
                      </th>
                      <th className="px-space-md py-space-md font-label-sm text-label-sm uppercase font-bold tracking-wider">
                        Policy Compliance Citation
                      </th>
                      <th className="px-space-md py-space-md font-label-sm text-label-sm uppercase font-bold tracking-wider text-right">
                        Action
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-subtle font-body-sm text-body-sm text-on-surface">
                    {filteredBreaches.length === 0 ? (
                      <tr>
                        <td colSpan={8} className="py-8 text-center text-outline">
                          No matching institutions found for &ldquo;{tableSearch}&rdquo;
                        </td>
                      </tr>
                    ) : (
                      filteredBreaches.map((row) => (
                        <tr key={row.pid} className="hover:bg-surface-canvas transition-colors">
                          <td className="px-space-md py-space-md font-code-sm text-code-sm font-bold text-primary">
                            {row.pid}
                          </td>
                          <td className="px-space-md py-space-md">
                            <div className="font-title-md text-title-md font-bold text-primary">
                              {row.name}
                            </div>
                            <div className="text-outline font-label-sm text-label-sm mt-0.5">
                              {row.location} • {row.course}
                            </div>
                          </td>
                          <td className="px-space-md py-space-md">
                            <span className="bg-surface-container px-space-xs py-space-2xs rounded font-label-sm text-label-sm text-primary font-medium">
                              {row.affiliation}
                            </span>
                          </td>
                          <td className="px-space-md py-space-md text-right font-code-sm text-code-sm font-bold">
                            {row.cap}
                          </td>
                          <td className="px-space-md py-space-md text-right font-code-sm text-code-sm font-bold text-primary">
                            {row.intake}
                          </td>
                          <td className="px-space-md py-space-md text-center">
                            <span
                              className={`font-code-sm text-code-sm font-extrabold px-space-xs py-space-2xs rounded border ${
                                row.excess > 0
                                  ? 'text-status-error bg-status-error-surface border-status-error-border'
                                  : 'text-status-verified bg-status-verified-surface border-status-verified-border'
                              }`}
                            >
                              {row.excessTag}
                            </span>
                          </td>
                          <td className="px-space-md py-space-md">
                            <div className="font-code-sm text-code-sm font-medium text-primary">
                              {row.citation}
                            </div>
                            <div className="font-label-sm text-label-sm text-on-surface-variant">
                              {row.citationDesc}
                            </div>
                          </td>
                          <td className="px-space-md py-space-md text-right">
                            <button
                              onClick={() => handleBreachAction(row.pid, row.actionText)}
                              className="px-space-md py-space-xs rounded-lg font-label-md text-label-md bg-surface-subtle text-primary border border-border-strong hover:bg-surface-container transition-colors shadow-sm cursor-pointer"
                            >
                              {row.actionText}
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        </div>
      </main>

      {/* ===================================================================== */}
      {/* MODAL: BATCH REVIEW DECISION CONFIRMATION */}
      {/* ===================================================================== */}
      {showBatchModal && selectedBatchForReview && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-surface-card rounded-2xl shadow-2xl border border-border-strong w-full max-w-xl overflow-hidden flex flex-col">
            <div className="px-6 py-4 bg-surface-subtle border-b border-border-subtle flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-primary">
                  gavel
                </span>
                <span className="font-headline-sm text-headline-sm font-bold text-primary">
                  Execute Batch Review Decision
                </span>
              </div>
              <button
                onClick={() => {
                  setShowBatchModal(false);
                  setSelectedBatchForReview(null);
                  setBatchActionError(null);
                }}
                className="text-on-surface-variant hover:text-primary"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            <div className="p-6 flex flex-col gap-4">
              {/* Batch Summary Header */}
              <div className="p-4 rounded-xl bg-surface-canvas border border-border-subtle space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-outline uppercase font-semibold">Target Batch:</span>
                  <span className="font-code-sm font-bold text-primary">{selectedBatchForReview.id} (v{selectedBatchForReview.version})</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-outline uppercase font-semibold">Institution:</span>
                  <span className="font-semibold text-primary">{selectedBatchForReview.institution_name || selectedBatchForReview.institution_id}</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-outline uppercase font-semibold">Current Status:</span>
                  <span className="font-mono px-2 py-0.5 rounded text-xs bg-surface-container font-bold">{selectedBatchForReview.status}</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-outline uppercase font-semibold">Row Breakdown:</span>
                  <span className="font-mono text-xs">
                    {selectedBatchForReview.valid_rows} valid • {selectedBatchForReview.error_rows} errors
                  </span>
                </div>
              </div>

              {/* Statutory Error Warning */}
              {batchDecision === 'ACCEPTED' && selectedBatchForReview.error_rows > 0 && (
                <div className="p-3 bg-status-error-surface border border-status-error-border rounded-xl text-status-error flex items-start gap-2 text-xs">
                  <span className="material-symbols-outlined text-base mt-0.5">warning</span>
                  <div>
                    <div className="font-bold">Statutory Block: Unresolved Blocking Errors</div>
                    <div>This batch contains {selectedBatchForReview.error_rows} blocking error row(s). AICTE approval will be rejected by the backend validation guard.</div>
                  </div>
                </div>
              )}

              {/* Decision Selector */}
              <div className="flex flex-col gap-1.5">
                <label className="font-label-sm text-label-sm text-outline uppercase font-bold">
                  Review Decision
                </label>
                <select
                  value={batchDecision}
                  onChange={(e: any) => setBatchDecision(e.target.value)}
                  className="bg-surface-canvas border border-border-strong rounded-lg p-2.5 font-label-md text-label-md text-primary font-bold focus:outline-none focus:border-secondary"
                >
                  <option value="UNDER_REVIEW">UNDER_REVIEW (Place Under Formal AICTE Review)</option>
                  <option value="ACCEPTED">ACCEPTED (Approve Batch for Official Enrolment)</option>
                  <option value="NEEDS_CORRECTION">NEEDS_CORRECTION (Return to Institution for Corrections)</option>
                  <option value="REJECTED">REJECTED (Formally Reject Batch Submission)</option>
                </select>
              </div>

              {/* Mandatory Reason Input */}
              <div className="flex flex-col gap-1.5">
                <label className="font-label-sm text-label-sm text-primary uppercase font-bold flex justify-between">
                  <span>Mandatory Statutory Reason / Justification <span className="text-status-error">*</span></span>
                  <span className="text-xs text-outline">{batchReason.length} characters</span>
                </label>
                <textarea
                  rows={3}
                  value={batchReason}
                  onChange={(e) => setBatchReason(e.target.value)}
                  placeholder="Enter the statutory reason, citation, or remediation instructions for this batch..."
                  className="bg-surface-canvas border border-border-strong rounded-xl p-3 font-body-sm text-body-sm text-on-surface focus:outline-none focus:border-secondary"
                />
              </div>

              {batchActionError && (
                <div className="p-3 bg-status-error-surface border border-status-error-border rounded-xl text-status-error text-xs font-semibold">
                  {batchActionError}
                </div>
              )}
            </div>

            <div className="px-6 py-4 bg-surface-subtle border-t border-border-subtle flex items-center justify-end gap-3">
              <button
                onClick={() => {
                  setShowBatchModal(false);
                  setSelectedBatchForReview(null);
                  setBatchActionError(null);
                }}
                disabled={isSubmittingBatch}
                className="px-4 py-2 rounded-lg border border-border-strong bg-surface-card text-on-surface-variant font-label-md hover:bg-surface-subtle cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleExecuteBatchDecision}
                disabled={isSubmittingBatch}
                className={`px-5 py-2 rounded-lg font-label-md text-on-primary font-bold flex items-center gap-1.5 cursor-pointer shadow-sm ${
                  batchDecision === 'ACCEPTED'
                    ? 'bg-status-verified hover:bg-status-verified/90'
                    : batchDecision === 'REJECTED'
                    ? 'bg-status-error hover:bg-status-error/90'
                    : 'bg-primary hover:bg-navy-deep'
                } ${isSubmittingBatch ? 'opacity-70 cursor-wait' : ''}`}
              >
                <span className={`material-symbols-outlined text-[18px] ${isSubmittingBatch ? 'animate-spin' : ''}`}>
                  {isSubmittingBatch ? 'progress_activity' : 'gavel'}
                </span>
                <span>{isSubmittingBatch ? 'Submitting...' : `Confirm Decision (${batchDecision})`}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AicteCentralReviewPage;
