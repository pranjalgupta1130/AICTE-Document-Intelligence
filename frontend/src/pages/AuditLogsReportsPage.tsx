import React, { useState, useMemo } from 'react';
import { AuthSession } from '../types/auth';

interface AuditLogsReportsPageProps {
  session?: AuthSession | null;
  onLogout?: () => void;
  onNavigateTab?: (tab: string) => void;
}

interface AuditEvent {
  id: string;
  timestamp: string;
  category: string;
  subCategory: string;
  actor: string;
  actorOrg: string;
  actorIp: string;
  targetEntity: string;
  targetSub: string;
  targetDetail?: string;
  outcome: 'SUCCESS' | 'RESOLVED' | 'BLOCKED' | 'VERIFIED' | 'EXPORTED' | 'FLAGGED' | 'COMPLIANT';
  notes: string;
  hashShort: string;
  hashFull: string;
  role: string;
}

const INITIAL_AUDIT_EVENTS: AuditEvent[] = [
  {
    id: 'EVT-2025-08914',
    timestamp: 'Today, 14:32:08 IST',
    category: 'BATCH_SUBMISSION',
    subCategory: 'Direct Bulk Ingestion',
    actor: 'admin@nitt.edu',
    actorOrg: 'NIT Trichy (C-49281)',
    actorIp: 'IP: 14.139.182.20',
    targetEntity: 'Batch #2024-B09 (120 Rows)',
    targetSub: 'B.Tech CSE Semester 1',
    targetDetail: 'APAAR Assigned: 118 records',
    outcome: 'SUCCESS',
    notes: 'Ingestion schema v2.4 validated. All 120 student records matched structural integrity. Zero unmasked Aadhaar retention verified.',
    hashShort: 'sha256: 8f4a...9b12',
    hashFull: '8f4a21074e5b6c891290bb3ac8912ef098481cbda78213894bf8921092487192',
    role: 'Institution Admin',
  },
  {
    id: 'EVT-2025-08902',
    timestamp: 'Today, 13:45:19 IST',
    category: 'DUPLICATE_ADJUDICATION',
    subCategory: 'Affidavit Override',
    actor: 'aicte.ro.south@aicte-india.org',
    actorOrg: 'AICTE Central Desk (RO-S)',
    actorIp: 'IP: 164.100.12.89',
    targetEntity: 'APAAR: ••••-••••-8921',
    targetSub: 'Colliding: NITT vs. Anna Univ',
    targetDetail: 'Seat ID: SEAT-TN-2024',
    outcome: 'RESOLVED',
    notes: 'Cross-institution collision dismissed. Dual-admission affidavit #AFF-2024-901 approved by Regional Officer. Seat released at previous inst.',
    hashShort: 'sha256: 3c2e...7d04',
    hashFull: '3c2e5541ba924ee7d04a621748231904128941bcdef128941298418920194812',
    role: 'AICTE Reviewer',
  },
  {
    id: 'EVT-2025-08889',
    timestamp: 'Today, 11:14:02 IST',
    category: 'VALIDATION_RUN',
    subCategory: 'Intake Quota Gate',
    actor: 'operator@coep.ac.in',
    actorOrg: 'COEP Pune (C-41582)',
    actorIp: 'IP: 103.21.58.114',
    targetEntity: 'Batch #COEP-MECH-04',
    targetSub: 'Attempted: 194 / Quota: 180',
    targetDetail: 'Surplus: 14 unapproved seats',
    outcome: 'BLOCKED',
    notes: 'Statutory Rule 4(A) Violation: Actual enrolment registrations exceed sanctioned AICTE ceiling. Ingestion halted pending Academic Council resolution.',
    hashShort: 'sha256: 1a9f...e62b',
    hashFull: '1a9fe62b14589d9841bbce829370144910294182930418293041892301928341',
    role: 'Institution Operator',
  },
  {
    id: 'EVT-2025-08871',
    timestamp: 'Today, 09:20:44 IST',
    category: 'MOCK_VERIFY_QUERY',
    subCategory: 'External BGV Engine',
    actor: 'bgv-agent@infosys.com',
    actorOrg: 'External Verifier (Infosys HR)',
    actorIp: 'API Client #CL-9481',
    targetEntity: 'APAAR: ••••-••••-4129',
    targetSub: 'Degree: B.Tech ECE (Grad 2024)',
    targetDetail: 'JNTUH Hyderabad',
    outcome: 'VERIFIED',
    notes: 'Mock Adapter returned MOCK_VERIFIED. Cryptographic certificate signature validated against State Board master keys. Zero PII transmitted.',
    hashShort: 'sha256: 7e8d...1503',
    hashFull: '7e8d54109848fde15039128038ab141092841092481092481092841029481203',
    role: 'External Verifier',
  },
  {
    id: 'EVT-2025-08865',
    timestamp: 'Yesterday, 18:04:12 IST',
    category: 'RECORD_CORRECTION',
    subCategory: 'Name Syntax Realignment',
    actor: 'registrar@vnit.ac.in',
    actorOrg: 'VNIT Nagpur (C-41444)',
    actorIp: 'IP: 14.139.112.55',
    targetEntity: 'APAAR: ••••-••••-6019',
    targetSub: 'Field: student_legal_name',
    targetDetail: 'Enrolment: 2023-VNIT-049',
    outcome: 'SUCCESS',
    notes: 'Name transliteration corrected against Class 10th Gazette certificate #GZ-881. Prior hash chained. Reason code: SPELLING_GAZETTE_UPDATE.',
    hashShort: 'sha256: 52a1...bc90',
    hashFull: '52a104928bcf8912bc9001928374189201948129034812904812904812904812',
    role: 'Institution Admin',
  },
  {
    id: 'EVT-2025-08840',
    timestamp: 'Yesterday, 16:11:30 IST',
    category: 'DATA_EXPORT',
    subCategory: 'Accreditation Dossier',
    actor: 'nba.evaluator@nic.in',
    actorOrg: 'NBA Peer Review Committee',
    actorIp: 'IP: 164.100.24.11',
    targetEntity: 'NIT Trichy Institutional Pack',
    targetSub: 'Format: Encrypted XML + PDF',
    targetDetail: 'Record Count: 4,120',
    outcome: 'EXPORTED',
    notes: 'Authorized statutory export under NEP 2020 Institutional Review guidelines. Cryptographic watermark #NBA-NITT-2024 embedded in output payload.',
    hashShort: 'sha256: 99c0...6b17',
    hashFull: '99c0491823abce126b1700941824109284102948120948120948120948120948',
    role: 'AICTE Reviewer',
  },
  {
    id: 'EVT-2025-08812',
    timestamp: 'Yesterday, 12:40:05 IST',
    category: 'VALIDATION_RUN',
    subCategory: 'DOB Out-of-Bounds',
    actor: 'operator@svce.ac.in',
    actorOrg: 'SVCE Chennai (C-16521)',
    actorIp: 'IP: 182.73.19.4',
    targetEntity: 'APAAR: ••••-••••-1194',
    targetSub: 'Date of Birth: 2017-04-12',
    targetDetail: 'Enrolment: B.Tech 2024',
    outcome: 'FLAGGED',
    notes: 'Age anomaly detected (computed age: 7 years for undergraduate admissions). Record isolated to exception queue; institute notified for re-verification.',
    hashShort: 'sha256: 4b18...71ef',
    hashFull: '4b1871ef49201bcde11940128941290481209481209481209481209481209481',
    role: 'Institution Operator',
  },
  {
    id: 'EVT-2025-08798',
    timestamp: '2 days ago, 23:59:00 IST',
    category: 'ZERO_AADHAAR_PURGE',
    subCategory: 'Automated Cron Sweep',
    actor: 'system.daemon@apaar.gov.in',
    actorOrg: 'Central Cryptographic Daemon',
    actorIp: 'Node: Secure Enclave 01',
    targetEntity: 'Ingestion Memory Buffer (Daily)',
    targetSub: 'Transient Hash Registers',
    targetDetail: 'Status: Zero residual bytes',
    outcome: 'COMPLIANT',
    notes: 'Section 17 DPDP Act 2023 purge routine executed. Memory sanitization completed across 14 server clusters. Zero biometric residues logged.',
    hashShort: 'sha256: 22fb...0041',
    hashFull: '22fb0041928471bcfe0019248719204918204918204918204918204918204918',
    role: 'AICTE Reviewer',
  },
];

export const AuditLogsReportsPage: React.FC<AuditLogsReportsPageProps> = ({
  session,
  onLogout,
  onNavigateTab,
}) => {
  // Navigation / Tabs
  const [activeMainTab, setActiveMainTab] = useState<'audit' | 'reports' | 'access' | 'security'>('audit');

  // Search & Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('ALL');
  const [roleFilter, setRoleFilter] = useState('ALL');
  const [outcomeFilter, setOutcomeFilter] = useState('ALL');
  const [highSevOnly, setHighSevOnly] = useState(false);
  const [page, setPage] = useState(1);

  // Verification Modal State
  const [verifyModalOpen, setVerifyModalOpen] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);

  // Status Feedback Toast / Banner
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isVerifyingChain, setIsVerifyingChain] = useState(false);

  const showToast = (msg: string) => {
    setStatusMessage(msg);
    setTimeout(() => {
      setStatusMessage(null);
    }, 4500);
  };

  // Integrity Check Action
  const handleVerifyChainIntegrity = () => {
    setIsVerifyingChain(true);
    setTimeout(() => {
      setIsVerifyingChain(false);
      showToast('All 142,890 blocks cryptographically validated against Merkle Root #0x9d4b...c81f. Custody integrity is 100% intact.');
    }, 900);
  };

  const handleCopyMerkleRoot = () => {
    const root = '0x9d4b892a01f8274381bcfe099238914c81f';
    if (navigator.clipboard) {
      navigator.clipboard.writeText(root);
    }
    showToast(`Merkle Root copied to clipboard: ${root}`);
  };

  const handleExportLedger = () => {
    showToast('Preparing encrypted immutable audit ledger stream (CSV & Signed JSON-LD). Total 142,890 records. Export initiated.');
  };

  const handleDownloadReport = (name: string) => {
    showToast(`Generating certified regulatory dataset for [${name}]. Stamped with sovereign cryptographic watermark.`);
  };

  const handlePreviewReport = (name: string) => {
    showToast(`Rendering official statutory PDF document preview for [${name}] in secure sandbox.`);
  };

  const handleOpenVerifyModal = (evt: AuditEvent) => {
    setSelectedEvent(evt);
    setVerifyModalOpen(true);
  };

  // Filter Logic
  const filteredEvents = useMemo(() => {
    return INITIAL_AUDIT_EVENTS.filter((evt) => {
      // High severity chip filter
      if (highSevOnly && !(evt.outcome === 'BLOCKED' || evt.outcome === 'FLAGGED')) {
        return false;
      }

      // Category filter
      if (categoryFilter !== 'ALL' && evt.category !== categoryFilter) {
        return false;
      }

      // Role filter
      if (roleFilter !== 'ALL' && evt.role !== roleFilter) {
        return false;
      }

      // Outcome filter
      if (outcomeFilter !== 'ALL') {
        if (outcomeFilter === 'SUCCESS' && !(evt.outcome === 'SUCCESS' || evt.outcome === 'RESOLVED' || evt.outcome === 'VERIFIED' || evt.outcome === 'COMPLIANT' || evt.outcome === 'EXPORTED')) {
          return false;
        }
        if (outcomeFilter === 'FLAGGED' && evt.outcome !== 'FLAGGED') {
          return false;
        }
        if (outcomeFilter === 'BLOCKED' && evt.outcome !== 'BLOCKED') {
          return false;
        }
      }

      // Text search
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const corpus = `${evt.id} ${evt.category} ${evt.subCategory} ${evt.actor} ${evt.actorOrg} ${evt.targetEntity} ${evt.targetSub} ${evt.notes} ${evt.hashShort}`.toLowerCase();
        if (!corpus.includes(q)) {
          return false;
        }
      }

      return true;
    });
  }, [searchQuery, categoryFilter, roleFilter, outcomeFilter, highSevOnly]);

  const handleResetFilters = () => {
    setSearchQuery('');
    setCategoryFilter('ALL');
    setRoleFilter('ALL');
    setOutcomeFilter('ALL');
    setHighSevOnly(false);
  };

  const navItemClass = (tabKey: string) =>
    `font-title-md text-title-md px-space-sm h-full flex items-center transition-colors cursor-pointer ${
      tabKey === 'reports'
        ? 'text-primary border-b-2 border-primary font-semibold bg-surface-subtle'
        : 'text-on-surface-variant hover:text-primary hover:bg-surface-subtle'
    }`;

  return (
    <div className="bg-surface-canvas font-body-md text-on-surface antialiased min-h-screen flex flex-col">
      {/* Toast Notification */}
      {statusMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-primary text-on-primary px-5 py-3 rounded-xl shadow-2xl flex items-center gap-3 border border-border-strong animate-bounce">
          <span className="material-symbols-outlined text-status-verified text-[22px]">verified</span>
          <span className="text-body-sm font-medium">{statusMessage}</span>
          <button
            onClick={() => setStatusMessage(null)}
            className="ml-2 hover:opacity-80 text-outline-variant"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>
      )}

      {/* HEADER */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-surface-card border-b border-border-subtle shadow-[0_1px_8px_rgba(0,0,0,0.04)]">
        <div className="h-14 w-full px-gutter-md flex items-center justify-between">
          <div className="flex items-center gap-space-md">
            <img
              alt="APAAR Institutional Emblem"
              className="h-8 w-auto object-contain"
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuAaDEyLEv46LqmVmOolAQ568T3Js9d8CoEogjfbUtbNBCOEMpfk4MiwwGOmaCvUV7h2wNERscyMwcmjVrhIzQ0gZhpgz-3MWx0hyQKclksESVAUjzqPmPIkNvPfnAtmo4Ba0U3DPRZs-MYA6Bh4Akgf0aOTGUjEBtEMqFqp-Ae_x5f9WV0JJt6m9I5dMZC7zDKAqKc2BE1rzPvfzNHWF4ZkCLwPWTNf6DFkPCZ2EqrN"
            />
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
            <span className="font-code-sm text-code-sm bg-surface-container-high text-primary px-space-xs py-space-2xs rounded-lg border border-border-strong font-semibold ml-space-xs">
              SIH-2026 PROTOTYPE
            </span>
          </div>

          <div className="flex items-center gap-space-md">
            <div className="hidden lg:flex items-center gap-space-xs bg-surface-subtle px-space-sm py-space-xs rounded-lg border border-border-subtle">
              <span className="material-symbols-outlined text-outline text-[16px]">school</span>
              <span className="font-code-sm text-code-sm text-on-surface-variant max-w-[280px] truncate">
                {session?.instCode || 'National Institute of Technology, Trichy (ID: AICTE-1-49281)'}
              </span>
            </div>

            <div className="relative">
              <select
                aria-label="Active Security Role Context"
                defaultValue={session?.role || 'Institution Admin'}
                className="font-label-md text-label-md bg-surface-card border border-border-strong text-primary rounded-lg px-space-sm py-space-xs focus:ring-1 focus:ring-secondary focus:outline-none"
              >
                <option>Institution Admin</option>
                <option>Institution Operator</option>
                <option>AICTE Reviewer</option>
              </select>
            </div>

            <button
              aria-label="Notifications"
              className="relative p-space-xs text-on-surface-variant hover:text-primary transition-colors"
            >
              <span className="material-symbols-outlined text-[20px]">notifications</span>
              <span className="absolute top-1 right-1 w-2 h-2 bg-status-error rounded-full"></span>
            </button>

            <div className="flex items-center gap-space-xs pl-space-xs border-l border-border-subtle">
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center font-headline-sm text-headline-sm text-on-primary font-bold">
                <span className="material-symbols-outlined text-on-primary text-[18px]">person</span>
              </div>
              <div className="hidden md:flex flex-col">
                <span className="font-label-md text-label-md text-on-surface font-semibold leading-tight">
                  {session?.userEmail || 'RK (Registrar)'}
                </span>
                <span className="font-label-sm text-label-sm text-outline leading-tight">
                  {session?.roleTitle || 'Academic Cell'}
                </span>
              </div>
              {onLogout && (
                <button
                  onClick={onLogout}
                  title="Sign Out"
                  className="ml-2 p-1 text-outline hover:text-status-error transition-colors"
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
            onClick={() => onNavigateTab?.('import')}
            className={navItemClass('import')}
          >
            Bulk Import &amp; Validation
          </button>
          <button
            onClick={() => onNavigateTab?.('findings')}
            className={navItemClass('findings')}
          >
            Data Quality &amp; Findings
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
        <div className="h-8 w-full bg-surface-subtle border-t border-b border-border-subtle px-gutter-md flex items-center justify-between">
          <div className="flex items-center gap-space-xs">
            <span className="w-2 h-2 rounded-full bg-status-verified animate-pulse"></span>
            <span className="font-code-sm text-code-sm text-on-surface font-medium">
              APAAR ID-Based Student Verification Engine • Mock Adapter Active (MOCK_VERIFIED / MOCK_UNAVAILABLE) • Synthetic Dataset v2.4
            </span>
          </div>
          <div className="flex items-center gap-space-sm">
            <span className="font-label-sm text-label-sm text-outline">Sovereign Security: ISO/IEC 27001 Validated</span>
            <span className="font-label-sm text-label-sm text-status-verified font-medium">● Sync Operational</span>
          </div>
        </div>
      </header>

      {/* MAIN CONTAINER */}
      <main className="w-full pt-32 bg-surface-canvas min-h-screen flex-1">
        <div className="flex flex-col w-full relative">
          {/* Ambient Indian Tricolor Background Layer */}
          <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
            <div className="absolute -top-40 -left-40 w-[600px] h-[600px] rounded-full bg-[#FF9933]/10 blur-3xl transform -rotate-12"></div>
            <div className="absolute top-1/3 left-1/4 w-[800px] h-[400px] bg-surface-canvas/90 blur-2xl transform rotate-45"></div>
            <div className="absolute -bottom-40 -right-40 w-[650px] h-[650px] rounded-full bg-[#138808]/10 blur-3xl transform rotate-12"></div>
            <div className="absolute inset-0 bg-gradient-to-br from-[#FF9933]/[0.04] via-transparent to-[#138808]/[0.05]"></div>
          </div>

          <div className="w-full max-w-[1440px] mx-auto px-gutter-md py-space-xl flex flex-col gap-space-xl">
            {/* Top Statutory Header & Context Bar */}
            <div className="bg-surface-card rounded-xl shadow-sm p-space-xl flex flex-col lg:flex-row lg:items-center justify-between gap-space-lg">
              <div className="flex flex-col gap-space-xs">
                <div className="flex items-center gap-space-sm flex-wrap">
                  <span className="font-headline-lg text-headline-lg text-primary tracking-tight">
                    Audit Trail &amp; Regulatory Compliance Reports
                  </span>
                  <span className="font-code-sm text-code-sm px-space-sm py-space-2xs rounded-lg bg-surface-subtle text-primary font-semibold flex items-center gap-space-2xs">
                    <span className="w-2 h-2 rounded-full bg-status-verified animate-pulse"></span>
                    LEDGER: APPEND-ONLY IMMUTABLE
                  </span>
                </div>
                <p className="font-body-md text-body-md text-on-surface-variant max-w-3xl">
                  Immutable statutory event logs, cryptographic access verification trail, and AICTE/NEP 2020 regulatory compliance report generation engine.
                </p>

                {/* Sovereign Scopes & Cryptographic Metadata Badges */}
                <div className="flex items-center gap-space-md mt-space-xs flex-wrap font-code-sm text-code-sm text-on-surface-variant">
                  <div className="flex items-center gap-space-2xs">
                    <span className="material-symbols-outlined text-outline text-[16px]">account_balance</span>
                    <span className="text-outline">Scope:</span>
                    <span className="font-semibold text-primary">All Affiliated Institutions / Central Node</span>
                  </div>
                  <span className="text-outline-variant">•</span>
                  <div className="flex items-center gap-space-2xs">
                    <span className="material-symbols-outlined text-outline text-[16px]">schedule</span>
                    <span className="text-outline">Sync Window:</span>
                    <span className="font-semibold text-on-surface">Today, 14:38:12 IST</span>
                  </div>
                  <span className="text-outline-variant">•</span>
                  <div className="flex items-center gap-space-2xs bg-status-verified-surface px-space-xs py-space-2xs rounded text-status-verified">
                    <span className="material-symbols-outlined text-[15px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                      verified
                    </span>
                    <span className="font-semibold">SHA-256 Checksum Verified (Epoch #8492)</span>
                  </div>
                </div>
              </div>

              {/* Header Action Buttons */}
              <div className="flex items-center gap-space-sm flex-wrap lg:self-center shrink-0">
                <button
                  id="verifyHashBtn"
                  onClick={handleVerifyChainIntegrity}
                  disabled={isVerifyingChain}
                  className="px-space-md py-space-sm bg-surface-subtle hover:bg-surface-container text-on-surface font-label-md text-label-md rounded-lg flex items-center gap-space-xs transition-colors"
                >
                  <span className={`material-symbols-outlined text-secondary text-[18px] ${isVerifyingChain ? 'animate-spin' : ''}`}>
                    {isVerifyingChain ? 'sync' : 'verified_user'}
                  </span>
                  <span>{isVerifyingChain ? 'Verifying Chain...' : 'Verify Integrity Hash'}</span>
                </button>

                <button
                  onClick={handleExportLedger}
                  className="px-space-md py-space-sm bg-surface-subtle hover:bg-surface-container text-primary font-label-md text-label-md rounded-lg flex items-center gap-space-xs transition-colors"
                >
                  <span className="material-symbols-outlined text-primary text-[18px]">file_download</span>
                  <span>Export Ledger (CSV/JSON)</span>
                </button>

                <button
                  onClick={() => {
                    setActiveMainTab('reports');
                    const el = document.getElementById('reports-panel');
                    el?.scrollIntoView({ behavior: 'smooth' });
                  }}
                  className="px-space-md py-space-sm bg-primary-container hover:bg-navy-deep text-on-primary font-label-md text-label-md rounded-lg shadow-sm flex items-center gap-space-xs transition-colors"
                >
                  <span className="material-symbols-outlined text-on-primary text-[18px]">description</span>
                  <span>Generate Official Report</span>
                </button>
              </div>
            </div>

            {/* Tabbed Navigation Switcher */}
            <div className="flex items-center gap-space-sm bg-surface-subtle p-space-xs rounded-lg overflow-x-auto">
              <button
                id="tab-audit"
                onClick={() => setActiveMainTab('audit')}
                className={`tab-btn px-space-lg py-space-sm rounded-lg font-title-md text-title-md flex items-center gap-space-xs transition-all ${
                  activeMainTab === 'audit'
                    ? 'bg-surface-card text-primary shadow-sm font-bold'
                    : 'text-on-surface-variant hover:text-primary hover:bg-surface-card/60'
                }`}
              >
                <span className="material-symbols-outlined text-[18px]">receipt_long</span>
                <span>Immutable Audit Trail</span>
                <span className="px-space-xs py-0.5 rounded-full text-label-sm font-label-sm bg-surface-container text-primary">
                  142.8k
                </span>
              </button>

              <button
                id="tab-reports"
                onClick={() => {
                  setActiveMainTab('reports');
                  const el = document.getElementById('reports-panel');
                  el?.scrollIntoView({ behavior: 'smooth' });
                }}
                className={`tab-btn px-space-lg py-space-sm rounded-lg font-title-md text-title-md flex items-center gap-space-xs transition-all ${
                  activeMainTab === 'reports'
                    ? 'bg-surface-card text-primary shadow-sm font-bold'
                    : 'text-on-surface-variant hover:text-primary hover:bg-surface-card/60'
                }`}
              >
                <span className="material-symbols-outlined text-[18px]">assessment</span>
                <span>Regulatory &amp; Accreditation Reports</span>
                <span className="px-space-xs py-0.5 rounded-full text-label-sm font-label-sm bg-status-verified-surface text-status-verified">
                  4 Ready
                </span>
              </button>

              <button
                id="tab-access"
                onClick={() => setActiveMainTab('access')}
                className={`tab-btn px-space-lg py-space-sm rounded-lg font-title-md text-title-md flex items-center gap-space-xs transition-all ${
                  activeMainTab === 'access'
                    ? 'bg-surface-card text-primary shadow-sm font-bold'
                    : 'text-on-surface-variant hover:text-primary hover:bg-surface-card/60'
                }`}
              >
                <span className="material-symbols-outlined text-[18px]">policy</span>
                <span>Verification &amp; Access Queries</span>
                <span className="px-space-xs py-0.5 rounded-full text-label-sm font-label-sm bg-surface-container text-primary">
                  18.4k
                </span>
              </button>

              <button
                id="tab-security"
                onClick={() => setActiveMainTab('security')}
                className={`tab-btn px-space-lg py-space-sm rounded-lg font-title-md text-title-md flex items-center gap-space-xs transition-all ${
                  activeMainTab === 'security'
                    ? 'bg-surface-card text-primary shadow-sm font-bold'
                    : 'text-on-surface-variant hover:text-primary hover:bg-surface-card/60'
                }`}
              >
                <span className="material-symbols-outlined text-[18px]">security</span>
                <span>Security &amp; Compliance Health</span>
                <span className="w-2 h-2 rounded-full bg-status-verified"></span>
              </button>
            </div>

            {/* Section A: Audit Analytics & Quick KPI Counters */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-space-md">
              {/* Metric 1 */}
              <div className="bg-surface-card rounded-xl p-space-lg shadow-sm flex flex-col justify-between relative overflow-hidden group">
                <div className="flex items-center justify-between">
                  <span className="font-label-md text-label-md text-on-surface-variant">TOTAL AUDIT EVENTS</span>
                  <span className="material-symbols-outlined text-secondary text-[20px]">history_edu</span>
                </div>
                <div className="mt-space-md">
                  <span className="font-display-lg text-display-lg text-primary tracking-tight font-bold">142,890</span>
                  <div className="flex items-center gap-space-2xs mt-space-xs text-status-verified font-label-sm text-label-sm">
                    <span className="material-symbols-outlined text-[14px]">trending_up</span>
                    <span>+2,410 today (All Batches)</span>
                  </div>
                </div>
                <div className="w-full bg-surface-container h-1 rounded-full mt-space-md overflow-hidden">
                  <div className="bg-primary h-full w-[88%]"></div>
                </div>
              </div>

              {/* Metric 2 */}
              <div className="bg-surface-card rounded-xl p-space-lg shadow-sm flex flex-col justify-between">
                <div className="flex items-center justify-between">
                  <span className="font-label-md text-label-md text-on-surface-variant">DISCREPANCIES TRIAGED</span>
                  <span className="material-symbols-outlined text-status-review text-[20px]">warning_amber</span>
                </div>
                <div className="mt-space-md">
                  <span className="font-display-lg text-display-lg text-primary tracking-tight font-bold">1,248</span>
                  <div className="flex items-center gap-space-2xs mt-space-xs text-status-review font-label-sm text-label-sm">
                    <span className="material-symbols-outlined text-[14px]">flag</span>
                    <span>98.2% Adjudication rate</span>
                  </div>
                </div>
                <div className="w-full bg-surface-container h-1 rounded-full mt-space-md overflow-hidden">
                  <div className="bg-status-review h-full w-[94%]"></div>
                </div>
              </div>

              {/* Metric 3 */}
              <div className="bg-surface-card rounded-xl p-space-lg shadow-sm flex flex-col justify-between">
                <div className="flex items-center justify-between">
                  <span className="font-label-md text-label-md text-on-surface-variant">VERIFICATION QUERIES</span>
                  <span className="material-symbols-outlined text-primary text-[20px]">badge</span>
                </div>
                <div className="mt-space-md">
                  <span className="font-display-lg text-display-lg text-primary tracking-tight font-bold">18,432</span>
                  <div className="flex items-center gap-space-2xs mt-space-xs text-on-surface-variant font-label-sm text-label-sm">
                    <span className="material-symbols-outlined text-[14px]">done_all</span>
                    <span>100% Mock Engine Synced</span>
                  </div>
                </div>
                <div className="w-full bg-surface-container h-1 rounded-full mt-space-md overflow-hidden">
                  <div className="bg-secondary h-full w-[72%]"></div>
                </div>
              </div>

              {/* Metric 4 */}
              <div className="bg-surface-card rounded-xl p-space-lg shadow-sm flex flex-col justify-between">
                <div className="flex items-center justify-between">
                  <span className="font-label-md text-label-md text-on-surface-variant">LOGGED INSTITUTIONS</span>
                  <span className="material-symbols-outlined text-primary text-[20px]">domain</span>
                </div>
                <div className="mt-space-md">
                  <span className="font-display-lg text-display-lg text-primary tracking-tight font-bold">487</span>
                  <div className="flex items-center gap-space-2xs mt-space-xs text-on-surface-variant font-label-sm text-label-sm">
                    <span>Affiliated AICTE Institutes</span>
                  </div>
                </div>
                <div className="w-full bg-surface-container h-1 rounded-full mt-space-md overflow-hidden">
                  <div className="bg-primary-container h-full w-[100%]"></div>
                </div>
              </div>

              {/* Metric 5 */}
              <div className="bg-surface-card rounded-xl p-space-lg shadow-sm flex flex-col justify-between">
                <div className="flex items-center justify-between">
                  <span className="font-label-md text-label-md text-status-verified font-bold">CUSTODY INTEGRITY</span>
                  <span className="material-symbols-outlined text-status-verified text-[20px]">lock</span>
                </div>
                <div className="mt-space-md">
                  <span className="font-display-lg text-display-lg text-status-verified tracking-tight font-bold">100%</span>
                  <div className="flex items-center gap-space-2xs mt-space-xs text-status-verified font-label-sm text-label-sm">
                    <span className="material-symbols-outlined text-[14px]">security</span>
                    <span>0 Tamper / Zero Discontinuity</span>
                  </div>
                </div>
                <div className="w-full bg-status-verified-surface h-1 rounded-full mt-space-md overflow-hidden">
                  <div className="bg-status-verified h-full w-full"></div>
                </div>
              </div>
            </div>

            {/* Sub-tab 1: Immutable Audit Trail */}
            {(activeMainTab === 'audit' || activeMainTab === 'reports') && (
              <div className="flex flex-col gap-space-lg" id="panel-audit">
                {/* Advanced Audit Filter Toolbar */}
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
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Search by Event ID, Masked APAAR (••••-••••-8921), Batch ID or Actor..."
                        className="w-full pl-10 pr-16 py-2 bg-surface-subtle text-on-surface font-body-md text-body-md rounded-lg focus:outline-none focus:bg-surface-card shadow-inner"
                      />
                      <kbd className="absolute right-3 top-1/2 -translate-y-1/2 font-code-sm text-code-sm text-outline bg-surface-card px-1.5 py-0.5 rounded shadow-sm text-[10px]">
                        Ctrl+K
                      </kbd>
                    </div>

                    {/* Quick Dropdowns */}
                    <div className="flex items-center gap-space-xs flex-wrap">
                      {/* Event Category */}
                      <select
                        aria-label="Filter by Event Category"
                        value={categoryFilter}
                        onChange={(e) => setCategoryFilter(e.target.value)}
                        className="bg-surface-subtle text-on-surface font-label-md text-label-md py-2 px-space-sm rounded-lg focus:outline-none"
                      >
                        <option value="ALL">All Categories</option>
                        <option value="BATCH_SUBMISSION">Batch Submission</option>
                        <option value="VALIDATION_RUN">Validation Run</option>
                        <option value="DUPLICATE_ADJUDICATION">Duplicate Adjudication</option>
                        <option value="RECORD_CORRECTION">Record Correction</option>
                        <option value="DATA_EXPORT">Data Export</option>
                        <option value="MOCK_VERIFY_QUERY">Verification Query</option>
                        <option value="ZERO_AADHAAR_PURGE">DPDP Zero-Aadhaar Purge</option>
                      </select>

                      {/* Actor Role */}
                      <select
                        aria-label="Filter by Actor Role"
                        value={roleFilter}
                        onChange={(e) => setRoleFilter(e.target.value)}
                        className="bg-surface-subtle text-on-surface font-label-md text-label-md py-2 px-space-sm rounded-lg focus:outline-none"
                      >
                        <option value="ALL">All Roles</option>
                        <option value="Institution Admin">Institution Admin</option>
                        <option value="Institution Operator">Institution Operator</option>
                        <option value="AICTE Reviewer">AICTE Reviewer</option>
                        <option value="External Verifier">External Verifier</option>
                      </select>

                      {/* Status Outcome */}
                      <select
                        aria-label="Filter by Status Outcome"
                        value={outcomeFilter}
                        onChange={(e) => setOutcomeFilter(e.target.value)}
                        className="bg-surface-subtle text-on-surface font-label-md text-label-md py-2 px-space-sm rounded-lg focus:outline-none"
                      >
                        <option value="ALL">All Outcomes</option>
                        <option value="SUCCESS">SUCCESS / RESOLVED</option>
                        <option value="FLAGGED">FLAGGED / REVIEW</option>
                        <option value="BLOCKED">BLOCKED</option>
                      </select>

                      {/* Time Window */}
                      <select
                        aria-label="Filter by Time Window"
                        defaultValue="Last 7 Days"
                        className="bg-surface-subtle text-on-surface font-label-md text-label-md py-2 px-space-sm rounded-lg focus:outline-none"
                      >
                        <option>Last 24 Hours</option>
                        <option>Last 7 Days</option>
                        <option>Session 2024-25</option>
                        <option>Custom Date Range...</option>
                      </select>
                    </div>
                  </div>

                  {/* Filter Action Chips & Summary Bar */}
                  <div className="flex items-center justify-between flex-wrap gap-space-sm pt-space-xs">
                    <div className="flex items-center gap-space-xs flex-wrap">
                      <span className="font-label-sm text-label-sm text-outline uppercase tracking-wider">
                        Quick Filters:
                      </span>
                      <button
                        onClick={() => setHighSevOnly(!highSevOnly)}
                        className={`font-label-sm text-label-sm px-space-sm py-1 rounded-full flex items-center gap-space-2xs transition-colors ${
                          highSevOnly
                            ? 'bg-status-error text-on-error'
                            : 'bg-surface-subtle hover:bg-status-error-surface text-on-surface-variant hover:text-status-error'
                        }`}
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-status-error"></span>
                        <span>Only High-Severity &amp; Blocked</span>
                      </button>

                      <button
                        onClick={() => {
                          setCategoryFilter('DUPLICATE_ADJUDICATION');
                          setHighSevOnly(false);
                        }}
                        className="font-label-sm text-label-sm px-space-sm py-1 rounded-full bg-surface-subtle hover:bg-surface-container text-on-surface-variant flex items-center gap-space-2xs transition-colors"
                      >
                        <span className="material-symbols-outlined text-[13px]">published_with_changes</span>
                        <span>Affidavit Duplicate Triage</span>
                      </button>

                      <button
                        onClick={() => {
                          setCategoryFilter('ZERO_AADHAAR_PURGE');
                          setHighSevOnly(false);
                        }}
                        className="font-label-sm text-label-sm px-space-sm py-1 rounded-full bg-status-verified-surface text-status-verified flex items-center gap-space-2xs"
                      >
                        <span className="material-symbols-outlined text-[13px]">lock_reset</span>
                        <span>DPDP Non-Retention Events</span>
                      </button>
                    </div>

                    <div className="flex items-center gap-space-sm font-label-sm text-label-sm text-on-surface-variant">
                      <span id="activeEventCount">
                        Showing {filteredEvents.length} of {INITIAL_AUDIT_EVENTS.length} verified events (142,890 in ledger)
                      </span>
                      <button
                        onClick={handleResetFilters}
                        className="text-secondary hover:underline font-semibold ml-space-xs"
                      >
                        Reset
                      </button>
                    </div>
                  </div>
                </div>

                {/* Section C: Immutable Audit Trail Table */}
                <div className="bg-surface-card rounded-xl shadow-sm overflow-hidden flex flex-col">
                  {/* Table Subheader Bar */}
                  <div className="bg-surface-subtle px-space-lg py-space-sm flex items-center justify-between flex-wrap gap-space-xs">
                    <div className="flex items-center gap-space-sm">
                      <span className="material-symbols-outlined text-primary text-[18px]">verified</span>
                      <span className="font-headline-sm text-headline-sm text-primary">
                        Cryptographically Sequenced Event Ledger
                      </span>
                    </div>
                    <div className="flex items-center gap-space-xs">
                      <span className="font-code-sm text-code-sm text-outline">Merkle Root:</span>
                      <span className="font-code-sm text-code-sm font-bold text-on-surface bg-surface-card px-space-xs py-0.5 rounded shadow-sm">
                        0x9d4b...c81f
                      </span>
                      <button
                        onClick={handleCopyMerkleRoot}
                        className="text-outline hover:text-primary p-0.5"
                        title="Copy Root Hash"
                      >
                        <span className="material-symbols-outlined text-[16px]">content_copy</span>
                      </button>
                    </div>
                  </div>

                  {/* Responsive Table Container */}
                  <div className="overflow-x-auto w-full">
                    <table className="w-full text-left border-collapse" id="auditTable">
                      <thead>
                        <tr className="bg-surface-canvas text-outline font-label-sm text-label-sm uppercase tracking-wider">
                          <th className="py-space-md px-space-lg font-semibold min-w-[140px]">Event ID &amp; Time</th>
                          <th className="py-space-md px-space-md font-semibold min-w-[180px]">Action &amp; Category</th>
                          <th className="py-space-md px-space-md font-semibold min-w-[200px]">Actor &amp; Origin</th>
                          <th className="py-space-md px-space-md font-semibold min-w-[220px]">Target Entity (Masked)</th>
                          <th className="py-space-md px-space-md font-semibold min-w-[120px]">Outcome</th>
                          <th className="py-space-md px-space-lg font-semibold min-w-[260px]">Statutory Notes / Reason</th>
                          <th className="py-space-md px-space-md font-semibold min-w-[160px] text-right">Hash &amp; Proof</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y-0 text-on-surface font-body-sm text-body-sm">
                        {filteredEvents.map((evt) => {
                          const isBlocked = evt.outcome === 'BLOCKED';
                          const isFlagged = evt.outcome === 'FLAGGED';
                          const rowBg = isBlocked
                            ? 'bg-status-error-surface/30 hover:bg-status-error-surface/50'
                            : isFlagged
                            ? 'bg-status-review-surface/20 hover:bg-status-review-surface/40'
                            : 'hover:bg-surface-subtle/80 bg-surface-card';

                          return (
                            <tr key={evt.id} className={`${rowBg} transition-colors group`}>
                              <td className="py-space-md px-space-lg align-top">
                                <div className="flex flex-col">
                                  <span
                                    className={`font-code-sm text-code-sm font-bold ${
                                      isBlocked
                                        ? 'text-status-error'
                                        : isFlagged
                                        ? 'text-status-review'
                                        : 'text-primary'
                                    }`}
                                  >
                                    {evt.id}
                                  </span>
                                  <span className="text-outline text-[11px] mt-0.5">{evt.timestamp}</span>
                                </div>
                              </td>

                              <td className="py-space-md px-space-md align-top">
                                <div className="flex flex-col gap-1 items-start">
                                  <span
                                    className={`font-label-sm text-label-sm px-space-xs py-0.5 rounded font-semibold ${
                                      isBlocked
                                        ? 'bg-status-error-surface text-status-error'
                                        : isFlagged
                                        ? 'bg-status-review-surface text-status-review'
                                        : evt.category === 'ZERO_AADHAAR_PURGE'
                                        ? 'bg-status-verified-surface text-status-verified'
                                        : 'bg-surface-container text-primary'
                                    }`}
                                  >
                                    {evt.category}
                                  </span>
                                  <span className="text-outline text-[11px]">{evt.subCategory}</span>
                                </div>
                              </td>

                              <td className="py-space-md px-space-md align-top">
                                <div className="flex flex-col">
                                  <span className="font-semibold text-on-surface">{evt.actor}</span>
                                  <span className="text-outline text-[11px]">{evt.actorOrg}</span>
                                  <span className="font-code-sm text-code-sm text-outline mt-0.5">{evt.actorIp}</span>
                                </div>
                              </td>

                              <td className="py-space-md px-space-md align-top">
                                <div className="flex flex-col">
                                  <span
                                    className={`font-semibold ${
                                      isBlocked
                                        ? 'text-status-error'
                                        : isFlagged
                                        ? 'text-status-review'
                                        : 'text-primary'
                                    }`}
                                  >
                                    {evt.targetEntity}
                                  </span>
                                  <span className="text-outline text-[11px]">{evt.targetSub}</span>
                                  {evt.targetDetail && (
                                    <span className="text-outline text-[11px]">{evt.targetDetail}</span>
                                  )}
                                </div>
                              </td>

                              <td className="py-space-md px-space-md align-top">
                                {isBlocked && (
                                  <span className="inline-flex items-center gap-1 font-label-sm text-label-sm px-space-xs py-0.5 rounded bg-status-error-surface text-status-error font-bold">
                                    <span className="material-symbols-outlined text-[13px]">block</span>
                                    BLOCKED
                                  </span>
                                )}
                                {isFlagged && (
                                  <span className="inline-flex items-center gap-1 font-label-sm text-label-sm px-space-xs py-0.5 rounded bg-status-review-surface text-status-review font-bold">
                                    <span className="material-symbols-outlined text-[13px]">warning</span>
                                    FLAGGED
                                  </span>
                                )}
                                {evt.outcome === 'SUCCESS' && (
                                  <span className="inline-flex items-center gap-1 font-label-sm text-label-sm px-space-xs py-0.5 rounded bg-status-verified-surface text-status-verified font-bold">
                                    <span className="material-symbols-outlined text-[13px]">check_circle</span>
                                    SUCCESS
                                  </span>
                                )}
                                {evt.outcome === 'RESOLVED' && (
                                  <span className="inline-flex items-center gap-1 font-label-sm text-label-sm px-space-xs py-0.5 rounded bg-status-verified-surface text-status-verified font-bold">
                                    <span className="material-symbols-outlined text-[13px]">verified</span>
                                    RESOLVED
                                  </span>
                                )}
                                {evt.outcome === 'VERIFIED' && (
                                  <span className="inline-flex items-center gap-1 font-label-sm text-label-sm px-space-xs py-0.5 rounded bg-status-verified-surface text-status-verified font-bold">
                                    <span className="material-symbols-outlined text-[13px]">check_circle</span>
                                    VERIFIED
                                  </span>
                                )}
                                {evt.outcome === 'EXPORTED' && (
                                  <span className="inline-flex items-center gap-1 font-label-sm text-label-sm px-space-xs py-0.5 rounded bg-status-verified-surface text-status-verified font-bold">
                                    <span className="material-symbols-outlined text-[13px]">lock</span>
                                    EXPORTED
                                  </span>
                                )}
                                {evt.outcome === 'COMPLIANT' && (
                                  <span className="inline-flex items-center gap-1 font-label-sm text-label-sm px-space-xs py-0.5 rounded bg-status-verified-surface text-status-verified font-bold">
                                    <span className="material-symbols-outlined text-[13px]">check_circle</span>
                                    COMPLIANT
                                  </span>
                                )}
                              </td>

                              <td className="py-space-md px-space-lg align-top">
                                <p
                                  className={`text-body-sm line-clamp-2 ${
                                    isBlocked
                                      ? 'text-status-error font-medium'
                                      : 'text-on-surface'
                                  }`}
                                >
                                  {evt.notes}
                                </p>
                              </td>

                              <td className="py-space-md px-space-md align-top text-right">
                                <div className="flex flex-col items-end gap-1">
                                  <span className="font-code-sm text-code-sm text-primary font-medium bg-surface-subtle px-1.5 py-0.5 rounded">
                                    {evt.hashShort}
                                  </span>
                                  <button
                                    onClick={() => handleOpenVerifyModal(evt)}
                                    className="text-secondary hover:text-navy-deep font-label-sm text-label-sm flex items-center gap-0.5"
                                  >
                                    <span className="material-symbols-outlined text-[13px]">done</span> Verify
                                  </button>
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>

                  {/* Table Pagination & Ledger Seal Footer */}
                  <div className="bg-surface-canvas px-space-lg py-space-sm flex items-center justify-between flex-wrap gap-space-sm">
                    <div className="flex items-center gap-space-xs text-outline font-body-sm text-body-sm">
                      <span>
                        Showing records 1 - {filteredEvents.length} of 142,890
                      </span>
                      <span className="text-outline-variant">•</span>
                      <span className="font-code-sm text-code-sm text-status-verified font-semibold">
                        Ledger Block #94,821 Sealed
                      </span>
                    </div>

                    <div className="flex items-center gap-space-xs">
                      <button
                        disabled={page === 1}
                        onClick={() => setPage((p) => Math.max(1, p - 1))}
                        className="px-space-sm py-1 bg-surface-card hover:bg-surface-subtle text-outline rounded text-label-md font-label-md disabled:opacity-40"
                      >
                        Previous
                      </button>
                      <span className="px-space-sm py-1 bg-primary text-on-primary font-label-sm text-label-sm rounded font-bold">
                        {page}
                      </span>
                      <button
                        onClick={() => {
                          setPage(2);
                          showToast('Loaded ledger page 2: blocks #94,801 - #94,820.');
                        }}
                        className="px-space-sm py-1 bg-surface-card hover:bg-surface-subtle text-on-surface rounded text-label-md font-label-md"
                      >
                        2
                      </button>
                      <button
                        onClick={() => {
                          setPage(3);
                          showToast('Loaded ledger page 3: blocks #94,781 - #94,800.');
                        }}
                        className="px-space-sm py-1 bg-surface-card hover:bg-surface-subtle text-on-surface rounded text-label-md font-label-md"
                      >
                        3
                      </button>
                      <span className="text-outline font-label-sm text-label-sm px-1">...</span>
                      <button
                        onClick={() => {
                          setPage(17862);
                          showToast('Loaded genesis block epoch page 17,862.');
                        }}
                        className="px-space-sm py-1 bg-surface-card hover:bg-surface-subtle text-on-surface rounded text-label-md font-label-md"
                      >
                        17862
                      </button>
                      <button
                        onClick={() => {
                          setPage((p) => p + 1);
                          showToast(`Viewing subsequent page of ledger records.`);
                        }}
                        className="px-space-sm py-1 bg-surface-card hover:bg-surface-subtle text-on-surface rounded text-label-md font-label-md"
                      >
                        Next
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Sub-tab 2: Regulatory Report Generation Cards */}
            <div className="flex flex-col gap-space-lg" id="reports-panel">
              <div className="flex items-center justify-between flex-wrap gap-space-sm">
                <div className="flex flex-col">
                  <div className="flex items-center gap-space-xs">
                    <span className="material-symbols-outlined text-primary text-[22px]">library_books</span>
                    <span className="font-headline-md text-headline-md text-primary">
                      Pre-Configured Statutory AICTE Regulatory Modules
                    </span>
                  </div>
                  <span className="font-body-sm text-body-sm text-on-surface-variant">
                    Deterministic audit statements formatted strictly to statutory reporting annexures for approval renewals, NBA accreditation, and central council audits.
                  </span>
                </div>
                <span className="font-label-sm text-label-sm bg-surface-container px-space-sm py-1 rounded-lg text-primary font-semibold">
                  STAMPED VERSION: AICTE-AP-2025.1
                </span>
              </div>

              {/* 4 Strategic Report Cards in Bento Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-space-lg">
                {/* Module 1: Intake vs Actual Enrolment */}
                <div className="bg-surface-card rounded-xl p-space-xl shadow-sm flex flex-col justify-between relative overflow-hidden group">
                  <div className="flex flex-col gap-space-sm">
                    <div className="flex items-start justify-between">
                      <div className="w-10 h-10 rounded-lg bg-surface-container flex items-center justify-center text-primary">
                        <span className="material-symbols-outlined text-[22px]">balance</span>
                      </div>
                      <span className="font-code-sm text-code-sm px-space-xs py-0.5 rounded bg-surface-subtle text-primary font-bold">
                        ANNEXURE-IV (A)
                      </span>
                    </div>
                    <div>
                      <h3 className="font-headline-sm text-headline-sm text-primary font-bold">
                        Intake vs. Actual Enrolment Reconciliation Statement
                      </h3>
                      <p className="font-body-sm text-body-sm text-on-surface-variant mt-space-xs">
                        Exhaustive cross-comparison of Approved Institutional Intake, Supernumerary Quotas (EWS, TFW, J&amp;K, PMSSS), and actual student registrations with delta arithmetic flags.
                      </p>
                    </div>

                    <div className="bg-surface-subtle p-space-sm rounded-lg flex items-center justify-between text-body-sm font-body-sm mt-space-xs">
                      <div>
                        <span className="text-outline text-[12px] block">Approved Intake:</span>
                        <span className="font-semibold text-primary">1,480 Seats</span>
                      </div>
                      <div>
                        <span className="text-outline text-[12px] block">Actual Enrolled:</span>
                        <span className="font-semibold text-on-surface">1,462 Students</span>
                      </div>
                      <div>
                        <span className="text-outline text-[12px] block">Status:</span>
                        <span className="font-semibold text-status-verified flex items-center gap-0.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-status-verified"></span> Within Quota
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-space-sm pt-space-lg mt-space-md">
                    <button
                      onClick={() => handleDownloadReport('Annexure-IV (A) Intake Reconciliation CSV')}
                      className="flex-1 py-space-sm px-space-md bg-surface-subtle hover:bg-surface-container text-on-surface font-label-md text-label-md rounded-lg flex items-center justify-center gap-space-xs transition-colors"
                    >
                      <span className="material-symbols-outlined text-[16px]">grid_on</span>
                      <span>Download CSV</span>
                    </button>
                    <button
                      onClick={() => handlePreviewReport('Annexure-IV (A) Intake Reconciliation PDF')}
                      className="flex-1 py-space-sm px-space-md bg-primary hover:bg-navy-deep text-on-primary font-label-md text-label-md rounded-lg flex items-center justify-center gap-space-xs transition-colors shadow-sm"
                    >
                      <span className="material-symbols-outlined text-[16px]">picture_as_pdf</span>
                      <span>Preview Signed PDF</span>
                    </button>
                  </div>
                </div>

                {/* Module 2: APAAR Academic Identity Sync */}
                <div className="bg-surface-card rounded-xl p-space-xl shadow-sm flex flex-col justify-between relative overflow-hidden group">
                  <div className="flex flex-col gap-space-sm">
                    <div className="flex items-start justify-between">
                      <div className="w-10 h-10 rounded-lg bg-surface-container flex items-center justify-center text-primary">
                        <span className="material-symbols-outlined text-[22px]">badge</span>
                      </div>
                      <span className="font-code-sm text-code-sm px-space-xs py-0.5 rounded bg-surface-subtle text-primary font-bold">
                        ANNEXURE-VII
                      </span>
                    </div>
                    <div>
                      <h3 className="font-headline-sm text-headline-sm text-primary font-bold">
                        Student Academic Identity &amp; APAAR Sync Registry
                      </h3>
                      <p className="font-body-sm text-body-sm text-on-surface-variant mt-space-xs">
                        Comprehensive registry of verified 12-digit APAAR identifiers, student identity completeness rate, syntax-validity statistics, and pending mock sync adapter queues.
                      </p>
                    </div>

                    <div className="bg-surface-subtle p-space-sm rounded-lg flex items-center justify-between text-body-sm font-body-sm mt-space-xs">
                      <div>
                        <span className="text-outline text-[12px] block">Verified APAARs:</span>
                        <span className="font-semibold text-primary">4,120 / 4,120</span>
                      </div>
                      <div>
                        <span className="text-outline text-[12px] block">Sync Readiness:</span>
                        <span className="font-semibold text-status-verified">100.0%</span>
                      </div>
                      <div>
                        <span className="text-outline text-[12px] block">Mock Adapter:</span>
                        <span className="font-semibold text-secondary">ACTIVE</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-space-sm pt-space-lg mt-space-md">
                    <button
                      onClick={() => handleDownloadReport('Annexure-VII APAAR Identity Matrix CSV')}
                      className="flex-1 py-space-sm px-space-md bg-surface-subtle hover:bg-surface-container text-on-surface font-label-md text-label-md rounded-lg flex items-center justify-center gap-space-xs transition-colors"
                    >
                      <span className="material-symbols-outlined text-[16px]">grid_on</span>
                      <span>Export CSV Matrix</span>
                    </button>
                    <button
                      onClick={() => handlePreviewReport('Annexure-VII APAAR Registry Report PDF')}
                      className="flex-1 py-space-sm px-space-md bg-primary hover:bg-navy-deep text-on-primary font-label-md text-label-md rounded-lg flex items-center justify-center gap-space-xs transition-colors shadow-sm"
                    >
                      <span className="material-symbols-outlined text-[16px]">file_open</span>
                      <span>Generate Report</span>
                    </button>
                  </div>
                </div>

                {/* Module 3: Duplicate & Candidate Collision Audit */}
                <div className="bg-surface-card rounded-xl p-space-xl shadow-sm flex flex-col justify-between relative overflow-hidden group">
                  <div className="flex flex-col gap-space-sm">
                    <div className="flex items-start justify-between">
                      <div className="w-10 h-10 rounded-lg bg-surface-container flex items-center justify-center text-primary">
                        <span className="material-symbols-outlined text-[22px]">call_split</span>
                      </div>
                      <span className="font-code-sm text-code-sm px-space-xs py-0.5 rounded bg-surface-subtle text-primary font-bold">
                        ANNEXURE-XI (DUPS)
                      </span>
                    </div>
                    <div>
                      <h3 className="font-headline-sm text-headline-sm text-primary font-bold">
                        Candidate Enrolment Collision &amp; Duplicate Audit
                      </h3>
                      <p className="font-body-sm text-body-sm text-on-surface-variant mt-space-xs">
                        Audited chronicle of all multi-institution seat collisions, dual-admission alerts, administrative dismissals, affidavit references, and regional officer digital signatures.
                      </p>
                    </div>

                    <div className="bg-surface-subtle p-space-sm rounded-lg flex items-center justify-between text-body-sm font-body-sm mt-space-xs">
                      <div>
                        <span className="text-outline text-[12px] block">Collisions Detected:</span>
                        <span className="font-semibold text-status-review">42 cases</span>
                      </div>
                      <div>
                        <span className="text-outline text-[12px] block">Affidavit Resolved:</span>
                        <span className="font-semibold text-status-verified">39 resolved</span>
                      </div>
                      <div>
                        <span className="text-outline text-[12px] block">Under Review:</span>
                        <span className="font-semibold text-status-error">3 pending</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-space-sm pt-space-lg mt-space-md">
                    <button
                      onClick={() => handleDownloadReport('Annexure-XI Collision & Duplicate Triage CSV')}
                      className="flex-1 py-space-sm px-space-md bg-surface-subtle hover:bg-surface-container text-on-surface font-label-md text-label-md rounded-lg flex items-center justify-center gap-space-xs transition-colors"
                    >
                      <span className="material-symbols-outlined text-[16px]">file_download</span>
                      <span>Export Triage Ledger</span>
                    </button>
                    <button
                      onClick={() => handlePreviewReport('Annexure-XI Collision Triage Audit PDF')}
                      className="flex-1 py-space-sm px-space-md bg-primary hover:bg-navy-deep text-on-primary font-label-md text-label-md rounded-lg flex items-center justify-center gap-space-xs transition-colors shadow-sm"
                    >
                      <span className="material-symbols-outlined text-[16px]">summarize</span>
                      <span>Generate Audit PDF</span>
                    </button>
                  </div>
                </div>

                {/* Module 4: Zero-Aadhaar Privacy & Access Disclosure Report */}
                <div className="bg-surface-card rounded-xl p-space-xl shadow-sm flex flex-col justify-between relative overflow-hidden group">
                  <div className="flex flex-col gap-space-sm">
                    <div className="flex items-start justify-between">
                      <div className="w-10 h-10 rounded-lg bg-surface-container flex items-center justify-center text-primary">
                        <span className="material-symbols-outlined text-[22px]">security</span>
                      </div>
                      <span className="font-code-sm text-code-sm px-space-xs py-0.5 rounded bg-status-verified-surface text-status-verified font-bold">
                        DPDP-2023 CERT
                      </span>
                    </div>
                    <div>
                      <h3 className="font-headline-sm text-headline-sm text-primary font-bold">
                        Zero-Aadhaar Privacy &amp; Access Disclosure Report
                      </h3>
                      <p className="font-body-sm text-body-sm text-on-surface-variant mt-space-xs">
                        Statutory attestation proving mathematical non-retention of biometric credentials, instant SHA-256 one-way salt scrubbing, and Zero-Knowledge verification integrity.
                      </p>
                    </div>

                    <div className="bg-surface-subtle p-space-sm rounded-lg flex items-center justify-between text-body-sm font-body-sm mt-space-xs">
                      <div>
                        <span className="text-outline text-[12px] block">Aadhaar Stored:</span>
                        <span className="font-semibold text-status-verified">0 (Strictly Prohibited)</span>
                      </div>
                      <div>
                        <span className="text-outline text-[12px] block">Audit Proof:</span>
                        <span className="font-semibold text-status-verified">Pass (Cert #DP-991)</span>
                      </div>
                      <div>
                        <span className="text-outline text-[12px] block">Encryption:</span>
                        <span className="font-semibold text-on-surface">AES-256-GCM</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-space-sm pt-space-lg mt-space-md">
                    <button
                      onClick={() => handleDownloadReport('DPDP-2023 Non-Retention Certificate CSV')}
                      className="flex-1 py-space-sm px-space-md bg-surface-subtle hover:bg-surface-container text-on-surface font-label-md text-label-md rounded-lg flex items-center justify-center gap-space-xs transition-colors"
                    >
                      <span className="material-symbols-outlined text-[16px]">fingerprint</span>
                      <span>Zero-Storage Proof</span>
                    </button>
                    <button
                      onClick={() => handlePreviewReport('DPDP-2023 Cryptographic Audit Package')}
                      className="flex-1 py-space-sm px-space-md bg-status-verified hover:bg-status-verified/90 text-on-primary font-label-md text-label-md rounded-lg flex items-center justify-center gap-space-xs transition-colors shadow-sm"
                    >
                      <span className="material-symbols-outlined text-[16px]">verified</span>
                      <span>Download Audit Package</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Sub-tab 3: Verification & Access Queries Overview (when active) */}
            {activeMainTab === 'access' && (
              <div className="bg-surface-card rounded-xl shadow-sm p-space-xl flex flex-col gap-space-md">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-headline-sm text-headline-sm text-primary font-bold">
                      Direct Verification &amp; Access Queries Journal
                    </h3>
                    <p className="font-body-sm text-body-sm text-on-surface-variant">
                      Cryptographically recorded query access logs from authorized credential verification clients (Employers, Universities, and Credential Banks).
                    </p>
                  </div>
                  <span className="px-space-sm py-1 bg-surface-subtle rounded text-status-verified font-bold text-label-sm">
                    MOCK ADAPTER REAL-TIME STREAM
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-space-md mt-space-sm">
                  <div className="bg-surface-subtle p-space-md rounded-lg border border-border-subtle">
                    <span className="text-label-sm text-outline block">Today's Total Lookups</span>
                    <span className="text-headline-lg font-bold text-primary">1,482</span>
                    <span className="text-body-sm text-status-verified block mt-1">99.8% Successful matches</span>
                  </div>
                  <div className="bg-surface-subtle p-space-md rounded-lg border border-border-subtle">
                    <span className="text-label-sm text-outline block">Median Latency</span>
                    <span className="text-headline-lg font-bold text-secondary">42 ms</span>
                    <span className="text-body-sm text-outline block mt-1">Zero-Knowledge Token Proof</span>
                  </div>
                  <div className="bg-surface-subtle p-space-md rounded-lg border border-border-subtle">
                    <span className="text-label-sm text-outline block">Unresolved / Unavailable</span>
                    <span className="text-headline-lg font-bold text-status-review">3</span>
                    <span className="text-body-sm text-status-review block mt-1">MOCK_UNAVAILABLE returned</span>
                  </div>
                </div>
              </div>
            )}

            {/* Sub-tab 4: Security & Compliance Health (when active) */}
            {activeMainTab === 'security' && (
              <div className="bg-surface-card rounded-xl shadow-sm p-space-xl flex flex-col gap-space-md">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-headline-sm text-headline-sm text-primary font-bold">
                      Sovereign Cryptographic Health &amp; Compliance Enclave
                    </h3>
                    <p className="font-body-sm text-body-sm text-on-surface-variant">
                      Real-time statutory security posture, DPDP Act 2023 non-retention parameters, and hardware security module (HSM) key lifecycle indicators.
                    </p>
                  </div>
                  <span className="px-space-sm py-1 bg-status-verified-surface text-status-verified rounded font-bold text-label-sm flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-status-verified animate-ping"></span>
                    ACTIVE DEFENSE
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-space-md mt-space-sm">
                  <div className="bg-surface-subtle p-space-md rounded-lg border border-border-subtle">
                    <span className="text-label-sm text-outline block">Aadhaar Non-Retention</span>
                    <span className="text-headline-md font-bold text-status-verified">Zero Bytes</span>
                    <span className="text-[12px] text-outline block mt-1">Memory sanitization every batch</span>
                  </div>
                  <div className="bg-surface-subtle p-space-md rounded-lg border border-border-subtle">
                    <span className="text-label-sm text-outline block">Merkle Chain Depth</span>
                    <span className="text-headline-md font-bold text-primary">142,890 Blocks</span>
                    <span className="text-[12px] text-outline block mt-1">Root signed by AICTE HSM</span>
                  </div>
                  <div className="bg-surface-subtle p-space-md rounded-lg border border-border-subtle">
                    <span className="text-label-sm text-outline block">Encryption at Rest</span>
                    <span className="text-headline-md font-bold text-primary">AES-256-GCM</span>
                    <span className="text-[12px] text-outline block mt-1">Key rotation every 90 days</span>
                  </div>
                  <div className="bg-surface-subtle p-space-md rounded-lg border border-border-subtle">
                    <span className="text-label-sm text-outline block">Statutory Audit Status</span>
                    <span className="text-headline-md font-bold text-status-verified">ISO 27001</span>
                    <span className="text-[12px] text-status-verified block mt-1">Compliant &amp; Certified</span>
                  </div>
                </div>
              </div>
            )}

            {/* Institutional Trust & Statutory Compliance Notice */}
            <div className="bg-surface-card rounded-xl p-space-xl shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-space-lg">
              <div className="flex items-start gap-space-md">
                <div className="w-12 h-12 rounded-lg bg-surface-subtle shrink-0 flex items-center justify-center text-primary">
                  <span className="material-symbols-outlined text-[28px]">gavel</span>
                </div>
                <div className="flex flex-col">
                  <span className="font-title-md text-title-md text-primary font-bold">
                    Statutory Compliance: Section 10(1) AICTE Act 1987 &amp; DPDP Act 2023
                  </span>
                  <p className="font-body-sm text-body-sm text-on-surface-variant max-w-4xl mt-space-2xs">
                    This administrative audit ledger conforms to Rule FR-13/NFR-03 Append-Only Ledger Standards. Modifications to historical entries are mathematically prevented via chained SHA-256 Merkle root verification. No biometric or Aadhaar numbers are persisted within this environment under any circumstances.
                  </p>
                  <span className="font-code-sm text-code-sm text-outline mt-space-xs">
                    System Instance: AICTE-CENTRAL-NODE-SOUTH • ISO/IEC 27001 ISMS Validated • Synthetic Demonstration Environment
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-space-xs shrink-0 self-start md:self-center">
                <div className="w-3 h-3 rounded-full bg-status-verified"></div>
                <span className="font-label-sm text-label-sm text-status-verified font-bold uppercase tracking-wider">
                  Audit Chain Intact
                </span>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Verification Modal Popup */}
      {verifyModalOpen && selectedEvent && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="verifyModalTitle"
          className="fixed inset-0 z-50 bg-on-surface/60 backdrop-blur-sm flex items-center justify-center p-space-md animate-fade-in"
        >
          <div className="bg-surface-card rounded-xl shadow-xl max-w-lg w-full p-space-xl flex flex-col gap-space-md transform transition-all border border-border-subtle">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-space-xs">
                <span className="material-symbols-outlined text-status-verified text-[24px]">verified</span>
                <span id="verifyModalTitle" className="font-headline-sm text-headline-sm text-primary">
                  Cryptographic Proof Check
                </span>
              </div>
              <button
                onClick={() => setVerifyModalOpen(false)}
                className="text-outline hover:text-primary"
              >
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>

            <div className="bg-surface-subtle p-space-md rounded-lg flex flex-col gap-space-xs">
              <span className="font-label-sm text-label-sm text-outline uppercase">
                Target Event Reference
              </span>
              <span className="font-code-sm text-code-sm font-bold text-primary">
                {selectedEvent.id} ({selectedEvent.category})
              </span>

              <span className="font-label-sm text-label-sm text-outline uppercase mt-space-xs">
                Chained SHA-256 Digest
              </span>
              <span className="font-code-sm text-code-sm text-on-surface break-all bg-surface-card p-space-xs rounded shadow-inner border border-border-subtle">
                {selectedEvent.hashFull}
              </span>

              <div className="flex items-center justify-between text-outline text-[12px] mt-1">
                <span>Timestamp: {selectedEvent.timestamp}</span>
                <span>Actor: {selectedEvent.actor}</span>
              </div>
            </div>

            <div className="flex items-center gap-space-sm p-space-sm rounded-lg bg-status-verified-surface text-status-verified font-body-sm text-body-sm">
              <span className="material-symbols-outlined text-[20px]">task_alt</span>
              <span>
                Signature confirmed against Central Council Root Key (RSA-4096 / SHA-256). Zero tampering detected in Merkle tree node.
              </span>
            </div>

            <div className="flex justify-end gap-space-sm pt-space-xs">
              <button
                onClick={() => {
                  navigator.clipboard?.writeText(selectedEvent.hashFull);
                  showToast('Hash copied to clipboard');
                }}
                className="px-space-md py-space-sm bg-surface-subtle hover:bg-surface-container text-on-surface font-label-md text-label-md rounded-lg"
              >
                Copy Hash
              </button>
              <button
                onClick={() => setVerifyModalOpen(false)}
                className="px-space-lg py-space-sm bg-primary text-on-primary font-label-md text-label-md rounded-lg"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
