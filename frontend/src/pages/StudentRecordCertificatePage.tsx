import React, { useState } from 'react';
import { AuthSession } from '../types/auth';

interface StudentRecordCertificatePageProps {
  session?: AuthSession | null;
  initialApaarId?: string;
  onLogout?: () => void;
  onNavigateTab?: (tab: string) => void;
}

interface StudentProfile {
  apaarId: string;
  instStudentId: string;
  fullName: string;
  initials: string;
  institution: string;
  institutionCode: string;
  programme: string;
  faculty: string;
  batch: string;
  term: string;
  enrolmentStatus: string;
  seatQuota: string;
  verificationStatus: string;
  verificationRef: string;
  verificationHash: string;
  signatureHash: string;
  signedDate: string;
  systemId: string;
  auditTrail: {
    timestamp: string;
    eventType: string;
    icon: string;
    iconColor: string;
    actor: string;
    actionDetails: string;
    complianceStatus: string;
    complianceBadgeClass: string;
  }[];
}

const MOCK_PROFILES: Record<string, StudentProfile> = {
  '9082-4412-8821': {
    apaarId: '9082-4412-8821',
    instStudentId: 'NITT-2025-CSE-0142',
    fullName: 'SIDDHARTH R. IYER',
    initials: 'SI',
    institution: 'National Institute of Technology, Trichy',
    institutionCode: 'AICTE-1-49281',
    programme: 'B.Tech (Computer Science & Engineering)',
    faculty: 'Faculty of Engineering & Technology',
    batch: '2025–2029',
    term: '2025-2026 • Sem 1',
    enrolmentStatus: 'Active Regular',
    seatQuota: 'AICTE Open Merit',
    verificationStatus: 'MOCK_VERIFIED',
    verificationRef: 'MOCK-APR-2025-882190-SIG',
    verificationHash: '8f4c2e...b39a',
    signatureHash: '3a9f7d...410b28',
    signedDate: '12-OCT-2025 14:35 UTC',
    systemId: 'SYS#49281-25',
    auditTrail: [
      {
        timestamp: '12 Oct 2025, 16:10:04 IST',
        eventType: 'Verification Query',
        icon: 'visibility',
        iconColor: 'text-secondary',
        actor: 'AICTE-VERIF-9912 (Reviewer)',
        actionDetails: 'Purpose-limited identity lookup executed against APAAR 9082-4412-8821.',
        complianceStatus: 'LOGGED & SIGNED',
        complianceBadgeClass: 'bg-status-verified-surface text-status-verified border-status-verified-border',
      },
      {
        timestamp: '12 Oct 2025, 14:35:19 IST',
        eventType: 'Mock Adapter Attestation',
        icon: 'check_circle',
        iconColor: 'text-status-verified',
        actor: 'ENGINE-ADAPTER-MOCK-V2',
        actionDetails: 'Status logged as MOCK_VERIFIED. Signature: MOCK-APR-2025-882190.',
        complianceStatus: 'VERIFIED',
        complianceBadgeClass: 'bg-status-verified-surface text-status-verified border-status-verified-border',
      },
      {
        timestamp: '12 Oct 2025, 14:34:02 IST',
        eventType: 'Syntactic Schema Check',
        icon: 'rule',
        iconColor: 'text-outline',
        actor: 'PARSER-SCHEMA-V4',
        actionDetails: 'Syntactic and field constraint validation passed (Rules R1 to R8 zero defect).',
        complianceStatus: 'PASSED (8/8)',
        complianceBadgeClass: 'bg-status-verified-surface text-status-verified border-status-verified-border',
      },
      {
        timestamp: '12 Oct 2025, 14:32:11 IST',
        eventType: 'Batch Ingestion',
        icon: 'upload_file',
        iconColor: 'text-outline',
        actor: 'R. Krishnamurthy (Op ID #2910)',
        actionDetails: 'Record imported into batch #BATCH-2025-NITTRICHY-004.',
        complianceStatus: 'COMMITTED',
        complianceBadgeClass: 'bg-surface-subtle text-on-surface-variant border-border-subtle',
      },
    ],
  },
  '9421-8819-4412': {
    apaarId: '9421-8819-4412',
    instStudentId: 'NITT-2025-CSE-0098',
    fullName: 'A. SHARMA',
    initials: 'AS',
    institution: 'National Institute of Technology, Trichy',
    institutionCode: 'AICTE-1-49281',
    programme: 'B.Tech (Computer Science)',
    faculty: 'Faculty of Engineering & Technology',
    batch: '2025–2029',
    term: '2025-2026 • Sem 1',
    enrolmentStatus: 'Under Triage Review',
    seatQuota: 'JoSAA Merit (Open/GEN)',
    verificationStatus: 'MOCK_VERIFIED',
    verificationRef: 'MOCK-APR-2025-994101-XC',
    verificationHash: '9941a2...c11f',
    signatureHash: '4b1e9c...88102a',
    signedDate: '15-JUL-2025 11:32 UTC',
    systemId: 'SYS#49281-99',
    auditTrail: [
      {
        timestamp: '23 Jul 2025, 14:22:00 IST',
        eventType: 'Triage Conflict Flagged',
        icon: 'warning',
        iconColor: 'text-status-review',
        actor: 'AICTE-APEX-TRIAGE-ENGINE',
        actionDetails: 'Concurrent admission detected across NIT Trichy and VIT Vellore.',
        complianceStatus: 'TRIAGE QUEUE',
        complianceBadgeClass: 'bg-status-review-surface text-status-review border-status-review-border',
      },
      {
        timestamp: '15 Jul 2025, 11:32:04 IST',
        eventType: 'JoSAA Seat Allocation',
        icon: 'verified',
        iconColor: 'text-status-verified',
        actor: 'JOSAA-CENTRAL-PORTAL',
        actionDetails: 'JoSAA round 3 merit allocation confirmed with fee remitted.',
        complianceStatus: 'VERIFIED',
        complianceBadgeClass: 'bg-status-verified-surface text-status-verified border-status-verified-border',
      },
    ],
  },
  '8812-7491-1029': {
    apaarId: '8812-7491-1029',
    instStudentId: 'COEP-2025-AI-0012',
    fullName: 'POOJA R. DESHMUKH',
    initials: 'PD',
    institution: 'COEP Technological University, Pune',
    institutionCode: 'AICTE-1-20914',
    programme: 'M.Tech (Artificial Intelligence)',
    faculty: 'School of Computer Engineering',
    batch: '2025–2027',
    term: '2025-2026 • Sem 1',
    enrolmentStatus: 'Active Regular',
    seatQuota: 'GATE Central Counseling (Open/OBC)',
    verificationStatus: 'MOCK_VERIFIED',
    verificationRef: 'MOCK-APR-2025-749102-SIG',
    verificationHash: '2c88fd...7a4e',
    signatureHash: '8b77a0...920141',
    signedDate: '12-JUL-2025 09:14 UTC',
    systemId: 'SYS#20914-12',
    auditTrail: [
      {
        timestamp: '19 Jul 2025, 16:45:10 IST',
        eventType: 'Dual Application Warning',
        icon: 'info',
        iconColor: 'text-secondary',
        actor: 'MAHA-CET-GRID',
        actionDetails: 'State counseling duplicate check matched with SPIT Mumbai.',
        complianceStatus: 'MONITORED',
        complianceBadgeClass: 'bg-status-review-surface text-status-review border-status-review-border',
      },
      {
        timestamp: '12 Jul 2025, 09:14:22 IST',
        eventType: 'GATE Enrolment Confirmed',
        icon: 'check_circle',
        iconColor: 'text-status-verified',
        actor: 'Dr. V. N. Pande (Dean)',
        actionDetails: 'Candidate biometrics and GATE scorecard validated.',
        complianceStatus: 'COMMITTED',
        complianceBadgeClass: 'bg-status-verified-surface text-status-verified border-status-verified-border',
      },
    ],
  },
};

export const StudentRecordCertificatePage: React.FC<StudentRecordCertificatePageProps> = ({
  session,
  initialApaarId = '9082-4412-8821',
  onLogout,
  onNavigateTab,
}) => {
  const [searchInput, setSearchInput] = useState<string>(initialApaarId);
  const [activeProfileKey, setActiveProfileKey] = useState<string>(initialApaarId);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [isExportingPdf, setIsExportingPdf] = useState<boolean>(false);
  const [isVerifyingChain, setIsVerifyingChain] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const profile = MOCK_PROFILES[activeProfileKey] || MOCK_PROFILES['9082-4412-8821'];

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 3500);
  };

  const copyToClipboard = (text: string, keyName: string) => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text).then(() => {
        setCopiedKey(keyName);
        showToast(`Copied to clipboard: ${text}`);
        setTimeout(() => {
          setCopiedKey(null);
        }, 1800);
      });
    }
  };

  const triggerSearchLookup = () => {
    const term = searchInput.trim();
    if (!term) {
      showToast('Please enter an APAAR ID or Institutional Student ID');
      return;
    }

    // Match by APAAR or Inst ID
    const foundKey = Object.keys(MOCK_PROFILES).find((k) => {
      const p = MOCK_PROFILES[k];
      return (
        k.toLowerCase() === term.toLowerCase() ||
        p.instStudentId.toLowerCase() === term.toLowerCase() ||
        p.fullName.toLowerCase().includes(term.toLowerCase())
      );
    });

    if (foundKey) {
      setActiveProfileKey(foundKey);
      showToast(`Record verified successfully under Rule R14 for ${MOCK_PROFILES[foundKey].fullName}`);
    } else {
      showToast(`Lookup initiated for ${term}. Mock record synchronized.`);
    }
  };

  const triggerPdfExport = () => {
    setIsExportingPdf(true);
    setTimeout(() => {
      setIsExportingPdf(false);
      showToast(`Signed Audit Receipt PDF generated (Ref: ${profile.verificationRef})`);
    }, 1500);
  };

  const refreshAuditTrail = () => {
    setIsVerifyingChain(true);
    setTimeout(() => {
      setIsVerifyingChain(false);
      showToast('Cryptographic chain verified. Merkle Tree hash validity 100%.');
    }, 800);
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

      {/* TOP HEADER */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-surface-card border-b border-border-subtle shadow-[0_1px_8px_rgba(0,0,0,0.04)] print:hidden">
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
                defaultValue={session?.roleTitle || 'AICTE Reviewer'}
                className="font-label-md text-label-md bg-surface-card border border-border-strong text-primary rounded-lg px-space-sm py-space-xs focus:ring-1 focus:ring-secondary focus:outline-none cursor-pointer"
              >
                <option value="Institution Admin">Institution Admin</option>
                <option value="Institution Operator">Institution Operator</option>
                <option value="AICTE Reviewer">AICTE Reviewer</option>
              </select>
            </div>

            <button
              aria-label="Notifications"
              onClick={() => showToast('All statutory compliance logs are synchronized.')}
              className="relative p-space-xs text-on-surface-variant hover:text-primary transition-colors cursor-pointer"
            >
              <span className="material-symbols-outlined text-[20px]">notifications</span>
              <span className="absolute top-1 right-1 w-2 h-2 bg-status-error rounded-full"></span>
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
            const isActive = tab.id === 'records';
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

      {/* MAIN CONTENT AREA */}
      <main className="w-full pt-32 bg-surface-canvas min-h-screen pb-16 flex-1 print:pt-4 print:pb-0 print:bg-white">
        <div className="flex flex-col w-full">
          {/* Top Sovereign Micro Notification Strip */}
          <div className="w-full bg-surface-container px-gutter-md py-space-xs text-on-surface flex flex-wrap items-center justify-between gap-space-sm shadow-sm print:hidden">
            <div className="flex items-center gap-space-xs flex-wrap">
              <span className="material-symbols-outlined text-[18px] text-secondary">
                verified_user
              </span>
              <span className="font-code-sm text-code-sm font-semibold tracking-wide uppercase text-primary">
                RULE R14 AUDIT LOG ENFORCED:
              </span>
              <span className="font-body-sm text-body-sm text-on-surface-variant">
                Indian Sovereign Academic Data Registry Directive 2024 • All lookups immutably tracked with tamper-evident SHA-256 seal
              </span>
            </div>
            <div className="flex items-center gap-space-md">
              <span className="font-code-sm text-code-sm bg-surface-card px-space-xs py-space-2xs rounded text-outline font-mono">
                SESSION: AICTE-VERIF-9912
              </span>
              <span className="font-label-sm text-label-sm text-status-verified flex items-center gap-1 font-semibold">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-status-verified animate-ping"></span>
                Live Cryptographic Ledger
              </span>
            </div>
          </div>

          <div className="w-full max-w-7xl mx-auto px-gutter-md py-space-2xl flex flex-col gap-space-2xl print:p-0 print:gap-4">
            {/* 1. Record Lookup & Verification Header */}
            <div className="w-full bg-surface-card rounded-xl p-space-xl shadow-sm border border-border-subtle flex flex-col lg:flex-row lg:items-center justify-between gap-space-xl print:hidden">
              <div className="flex flex-col gap-space-xs max-w-xl">
                <div className="flex items-center gap-space-xs">
                  <span className="font-label-sm text-label-sm uppercase tracking-widest text-secondary font-bold">
                    Registry Inspection Engine
                  </span>
                  <span className="font-code-sm text-code-sm px-space-xs py-space-2xs bg-surface-subtle text-outline rounded font-mono font-medium border border-border-subtle">
                    REV: 2025.10
                  </span>
                </div>
                <h1 className="font-headline-lg text-headline-lg text-primary tracking-tight font-bold">
                  Academic Credential &amp; Dual ID Verification
                </h1>
                <p className="font-body-md text-body-md text-on-surface-variant leading-relaxed">
                  Purpose-limited retrieval by Student Academic Identifier under Sovereign Security protocols. Records are authenticated against the central APAAR registry.
                </p>
              </div>

              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-space-md w-full lg:w-auto">
                <div className="relative flex-1 sm:w-80">
                  <div className="absolute inset-y-0 left-0 pl-space-md flex items-center pointer-events-none">
                    <span className="material-symbols-outlined text-outline text-[18px]">
                      fingerprint
                    </span>
                  </div>
                  <input
                    type="text"
                    value={searchInput}
                    onChange={(e) => setSearchInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') triggerSearchLookup();
                    }}
                    placeholder="Enter APAAR (xxxx-xxxx-xxxx)"
                    className="w-full pl-10 pr-12 py-space-sm bg-surface-subtle hover:bg-surface-canvas text-on-surface font-code-sm text-code-sm rounded-lg border border-border-subtle transition-all focus:outline-none focus:ring-2 focus:ring-secondary/40 focus:border-secondary"
                  />
                  <div className="absolute inset-y-0 right-0 pr-space-sm flex items-center">
                    <span className="font-code-sm text-code-sm px-2 py-0.5 bg-surface-card border border-border-subtle text-outline rounded text-[10px] font-mono shadow-sm">
                      ↵
                    </span>
                  </div>
                </div>
                <button
                  onClick={triggerSearchLookup}
                  className="bg-primary text-on-primary hover:bg-navy-deep px-space-xl py-space-sm rounded-lg font-title-md text-title-md flex items-center justify-center gap-space-xs transition-all shadow-sm active:scale-95 cursor-pointer"
                >
                  <span className="material-symbols-outlined text-[18px]">search_check</span>
                  <span>Verify Record</span>
                </button>
              </div>
            </div>

            {/* Quick Record Switcher Pills */}
            <div className="flex items-center gap-2 flex-wrap text-xs print:hidden -mt-4">
              <span className="text-outline font-semibold">Demo Profiles:</span>
              {Object.keys(MOCK_PROFILES).map((key) => {
                const item = MOCK_PROFILES[key];
                const isSelected = activeProfileKey === key;
                return (
                  <button
                    key={key}
                    onClick={() => {
                      setActiveProfileKey(key);
                      setSearchInput(key);
                      showToast(`Loaded Profile: ${item.fullName}`);
                    }}
                    className={`px-2.5 py-1 rounded-full border transition-all cursor-pointer font-mono ${
                      isSelected
                        ? 'bg-primary text-white border-primary shadow-sm font-semibold'
                        : 'bg-surface-card text-on-surface-variant border-border-subtle hover:bg-surface-subtle'
                    }`}
                  >
                    {item.fullName.split(' ')[0]} ({item.apaarId})
                  </button>
                );
              })}
            </div>

            {/* Main Content Workspace: Bento Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-space-xl print:grid-cols-12">
              {/* 2. Verified Student Academic Identity Record (Left Panel - 4 Cols) */}
              <div className="lg:col-span-4 flex flex-col gap-space-xl print:col-span-4">
                <div className="bg-surface-card rounded-xl p-space-xl shadow-sm border border-border-subtle flex flex-col gap-space-lg">
                  <div className="flex items-center justify-between pb-space-md border-b border-border-subtle">
                    <span className="font-label-sm text-label-sm px-space-sm py-1 bg-status-verified-surface text-status-verified rounded-full font-semibold flex items-center gap-1.5 border border-status-verified-border">
                      <span className="material-symbols-outlined text-[14px]">verified</span>
                      Verified Academic Identity
                    </span>
                    <span className="font-code-sm text-code-sm text-outline font-mono">
                      {profile.systemId}
                    </span>
                  </div>

                  <div className="flex items-center gap-space-md py-space-xs">
                    <div className="w-14 h-14 rounded-full bg-surface-container-high flex items-center justify-center text-primary font-headline-md text-headline-md font-bold shadow-sm">
                      {profile.initials}
                    </div>
                    <div className="flex flex-col min-w-0">
                      <span className="font-headline-sm text-headline-sm font-bold text-primary truncate">
                        {profile.fullName}
                      </span>
                      <span className="font-body-sm text-body-sm text-on-surface-variant">
                        Synthetic Profile
                      </span>
                      <div className="mt-1 flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-status-verified"></span>
                        <span className="font-label-sm text-label-sm font-semibold text-status-verified">
                          {profile.verificationStatus}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Identification Keys Block */}
                  <div className="bg-surface-subtle/40 rounded-xl p-space-md flex flex-col gap-space-md border border-border-subtle">
                    <div className="flex flex-col">
                      <span className="font-label-sm text-label-sm uppercase tracking-wider text-outline font-medium">
                        Institutional Student ID
                      </span>
                      <div className="flex items-center justify-between mt-1">
                        <span className="font-code-sm text-code-sm font-mono font-bold text-primary">
                          {profile.instStudentId}
                        </span>
                        <button
                          onClick={() => copyToClipboard(profile.instStudentId, 'instId')}
                          className="text-outline hover:text-primary p-1 rounded transition-colors cursor-pointer"
                          title="Copy Inst ID"
                        >
                          <span
                            className={`material-symbols-outlined text-[16px] ${
                              copiedKey === 'instId' ? 'text-status-verified' : ''
                            }`}
                          >
                            {copiedKey === 'instId' ? 'check' : 'content_copy'}
                          </span>
                        </button>
                      </div>
                    </div>

                    <div className="h-px bg-border-subtle w-full"></div>

                    <div className="flex flex-col">
                      <div className="flex items-center justify-between">
                        <span className="font-label-sm text-label-sm uppercase tracking-wider text-secondary font-semibold">
                          APAAR Identifier
                        </span>
                        <span className="font-label-sm text-label-sm text-status-verified bg-status-verified-surface px-2 py-0.5 rounded-full border border-status-verified-border">
                          Live Seed
                        </span>
                      </div>
                      <div className="flex items-center justify-between mt-1">
                        <span className="font-code-sm text-code-sm font-mono font-bold text-primary tracking-widest text-[15px]">
                          {profile.apaarId}
                        </span>
                        <button
                          onClick={() => copyToClipboard(profile.apaarId, 'apaarId')}
                          className="text-outline hover:text-primary p-1 rounded transition-colors cursor-pointer"
                          title="Copy APAAR ID"
                        >
                          <span
                            className={`material-symbols-outlined text-[16px] ${
                              copiedKey === 'apaarId' ? 'text-status-verified' : ''
                            }`}
                          >
                            {copiedKey === 'apaarId' ? 'check' : 'content_copy'}
                          </span>
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Attributes Details Table */}
                  <div className="flex flex-col divide-y divide-border-subtle text-on-surface">
                    <div className="flex justify-between items-center py-space-xs">
                      <span className="font-body-sm text-body-sm text-on-surface-variant">
                        Institution
                      </span>
                      <span className="font-title-md text-title-md text-primary text-right font-medium max-w-[210px] truncate">
                        {profile.institution} ({profile.institutionCode})
                      </span>
                    </div>
                    <div className="flex justify-between items-center py-space-xs">
                      <span className="font-body-sm text-body-sm text-on-surface-variant">
                        Programme
                      </span>
                      <span className="font-title-md text-title-md text-primary text-right font-medium">
                        {profile.programme}
                      </span>
                    </div>
                    <div className="flex justify-between items-center py-space-xs">
                      <span className="font-body-sm text-body-sm text-on-surface-variant">
                        Academic Term
                      </span>
                      <span className="font-body-sm text-body-sm font-medium text-primary">
                        {profile.term}
                      </span>
                    </div>
                    <div className="flex justify-between items-center py-space-xs">
                      <span className="font-body-sm text-body-sm text-on-surface-variant">
                        Enrolment Status
                      </span>
                      <span className="font-code-sm text-code-sm bg-status-verified-surface text-status-verified px-2 py-0.5 rounded font-medium border border-status-verified-border">
                        {profile.enrolmentStatus}
                      </span>
                    </div>
                    <div className="flex justify-between items-center py-space-xs">
                      <span className="font-body-sm text-body-sm text-on-surface-variant">
                        Seat Quota
                      </span>
                      <span className="font-body-sm text-body-sm text-primary font-medium">
                        {profile.seatQuota}
                      </span>
                    </div>
                  </div>

                  {/* Verification Signature Hash */}
                  <div className="bg-surface-subtle rounded-lg p-space-sm flex flex-col gap-1 text-[11px] font-mono text-outline border border-border-subtle">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-on-surface-variant uppercase tracking-wider">
                        Verification Adapter
                      </span>
                      <span className="text-status-verified font-semibold">
                        {profile.verificationStatus}
                      </span>
                    </div>
                    <div className="truncate text-outline">REF: {profile.verificationRef}</div>
                    <div className="truncate text-outline">
                      HASH: {profile.verificationHash} (SHA-256 Validated)
                    </div>
                  </div>
                </div>

                {/* Statutory Accreditation Card */}
                <div className="bg-primary-container text-on-primary rounded-xl p-space-xl shadow-sm flex flex-col gap-space-sm relative overflow-hidden print:hidden">
                  <div className="absolute -right-6 -bottom-6 w-28 h-28 bg-surface-container/10 rounded-full pointer-events-none"></div>
                  <div className="flex items-center gap-space-xs text-secondary-fixed">
                    <span className="material-symbols-outlined text-[20px]">account_balance</span>
                    <span className="font-label-md text-label-md uppercase tracking-wider font-bold">
                      Statutory Accreditation
                    </span>
                  </div>
                  <p className="font-body-sm text-body-sm text-on-primary-container leading-relaxed">
                    Identity linkage completed pursuant to National Academic Depository (NAD) and AICTE Regulation Section 14-B.
                  </p>
                  <div className="flex items-center gap-space-lg pt-space-xs flex-wrap">
                    <div className="flex items-center gap-1.5 font-code-sm text-code-sm text-secondary-fixed">
                      <span className="material-symbols-outlined text-[16px]">lock</span>
                      <span>Encrypted at Rest</span>
                    </div>
                    <div className="flex items-center gap-1.5 font-code-sm text-code-sm text-secondary-fixed">
                      <span className="material-symbols-outlined text-[16px]">gavel</span>
                      <span>Rule R16 Compliant</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* 3. Official Synthetic Certificate Preview (Right Panel - 8 Cols) */}
              <div className="lg:col-span-8 flex flex-col gap-space-xl print:col-span-8">
                {/* Actions Toolbar */}
                <div className="bg-surface-card rounded-xl p-space-md shadow-sm border border-border-subtle flex flex-wrap items-center justify-between gap-space-md print:hidden">
                  <div className="flex items-center gap-space-sm pl-space-xs">
                    <span className="material-symbols-outlined text-secondary text-[22px]">
                      workspace_premium
                    </span>
                    <span className="font-title-md text-title-md text-primary font-bold">
                      Formal Electronic Credential Receipt
                    </span>
                    <span className="font-code-sm text-code-sm px-2 py-0.5 bg-status-review-surface text-status-review font-semibold rounded border border-status-review-border">
                      R16 PROTOTYPE SPEC
                    </span>
                  </div>

                  <div className="flex items-center flex-wrap gap-space-xs">
                    <button
                      onClick={() => window.print()}
                      className="px-space-md py-1.5 bg-surface-subtle hover:bg-surface-container text-primary rounded-lg font-title-md text-title-md flex items-center gap-1.5 transition-colors border border-border-subtle shadow-sm cursor-pointer"
                    >
                      <span className="material-symbols-outlined text-[18px]">print</span>
                      <span>Print</span>
                    </button>

                    <button
                      id="exportBtn"
                      onClick={triggerPdfExport}
                      disabled={isExportingPdf}
                      className="px-space-lg py-1.5 bg-secondary text-on-secondary hover:bg-navy-accent rounded-lg font-title-md text-title-md flex items-center gap-1.5 transition-all shadow-sm cursor-pointer disabled:opacity-75"
                    >
                      <span
                        className={`material-symbols-outlined text-[18px] ${
                          isExportingPdf ? 'animate-spin' : ''
                        }`}
                      >
                        {isExportingPdf ? 'progress_activity' : 'download_for_offline'}
                      </span>
                      <span>{isExportingPdf ? 'Generating Signed PDF...' : 'Export Signed PDF'}</span>
                    </button>

                    <button
                      onClick={() => {
                        if (onNavigateTab) {
                          onNavigateTab('aicte-review');
                        }
                      }}
                      className="px-space-md py-1.5 bg-surface-card hover:bg-surface-subtle text-on-surface-variant hover:text-primary rounded-lg font-title-md text-title-md flex items-center gap-1 transition-colors border border-border-subtle cursor-pointer"
                      title="Back to Central Review Console"
                    >
                      <span className="material-symbols-outlined text-[18px]">arrow_back</span>
                      <span className="hidden sm:inline">Central Review</span>
                    </button>
                  </div>
                </div>

                {/* Certificate Rendered Canvas */}
                <div
                  id="printableCertificate"
                  className="relative bg-surface-card rounded-xl p-space-xl lg:p-space-3xl shadow-sm border border-border-subtle overflow-hidden bg-gradient-to-b from-surface-card via-surface-canvas/20 to-surface-card print:border-2 print:border-black print:p-6"
                >
                  {/* Ornate Guilloche Border */}
                  <div className="absolute inset-0 pointer-events-none p-4">
                    <svg
                      className="w-full h-full text-border-strong opacity-20"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <rect
                        fill="none"
                        height="100%"
                        rx="8"
                        stroke="currentColor"
                        strokeDasharray="6 4"
                        strokeWidth="1.5"
                        width="100%"
                        x="0"
                        y="0"
                      />
                      <rect
                        fill="none"
                        height="calc(100% - 16px)"
                        rx="6"
                        stroke="currentColor"
                        strokeWidth="0.75"
                        width="calc(100% - 16px)"
                        x="8"
                        y="8"
                      />
                    </svg>
                  </div>

                  <div className="relative z-10 flex flex-col gap-space-xl text-center items-center">
                    {/* Header Emblems & Government Entity */}
                    <div className="w-full flex items-center justify-between px-space-md sm:px-space-xl">
                      <div className="flex flex-col items-center gap-1.5">
                        <div className="w-14 h-14 rounded-full bg-surface-subtle border border-border-strong flex items-center justify-center text-primary shadow-sm">
                          <span className="material-symbols-outlined text-3xl">account_balance</span>
                        </div>
                        <span className="font-code-sm text-code-sm text-outline font-semibold tracking-tighter">
                          AICTE NEW DELHI
                        </span>
                      </div>

                      <div className="flex flex-col items-center max-w-md">
                        <span className="font-label-sm text-label-sm tracking-[0.25em] text-secondary font-bold uppercase">
                          Government of India • Ministry of Education
                        </span>
                        <span className="font-headline-lg text-headline-lg text-primary tracking-tight font-extrabold mt-1">
                          ALL INDIA COUNCIL FOR TECHNICAL EDUCATION
                        </span>
                        <span className="font-title-md text-title-md text-on-surface-variant font-medium mt-0.5">
                          National Academic Identity Depository Registry (APAAR)
                        </span>
                        <div className="h-0.5 w-24 bg-primary/40 mt-2 rounded-full"></div>
                      </div>

                      <div className="flex flex-col items-center gap-1.5">
                        <div className="w-14 h-14 rounded-full bg-surface-subtle border border-border-strong flex items-center justify-center text-secondary shadow-sm">
                          <span className="material-symbols-outlined text-3xl">school</span>
                        </div>
                        <span className="font-code-sm text-code-sm text-outline font-semibold tracking-tighter">
                          INSTITUTION REGISTRY
                        </span>
                      </div>
                    </div>

                    {/* Proclamation Banner */}
                    <div className="flex flex-col items-center max-w-2xl px-space-md">
                      <span className="font-label-md text-label-md px-space-lg py-1 bg-surface-subtle text-primary rounded-full uppercase tracking-widest font-bold border border-border-subtle">
                        Student Enrolment &amp; Credential Attestation
                      </span>
                      <p className="font-body-lg text-body-lg text-on-surface mt-space-md leading-relaxed text-center font-serif italic text-[15px]">
                        &ldquo;This certifies that the candidate whose Institutional ID and sovereign APAAR ID are recorded below has fulfilled the statutory prerequisite enrolment requirements and is recognized under the National Unified Educational Registry schema.&rdquo;
                      </p>
                    </div>

                    {/* Candidate Identity Dossier Box */}
                    <div className="w-full max-w-xl bg-surface-canvas rounded-xl p-space-xl border border-border-subtle flex flex-col items-center gap-space-sm shadow-sm print:bg-white">
                      <span className="font-label-sm text-label-sm uppercase tracking-wider text-outline font-semibold">
                        Candidate Attested Name
                      </span>
                      <span className="font-display-lg text-display-lg text-primary font-bold tracking-tight">
                        {profile.fullName}
                      </span>
                      <div className="flex flex-wrap items-center justify-center gap-space-sm text-on-surface-variant font-body-sm text-body-sm mt-0.5">
                        <span>{profile.faculty}</span>
                        <span>•</span>
                        <span className="font-semibold text-primary">{profile.programme}</span>
                        <span>•</span>
                        <span>Batch: {profile.batch}</span>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-space-md w-full mt-space-md pt-space-xs">
                        <div className="bg-surface-card p-space-md rounded-lg border border-border-subtle shadow-sm flex flex-col items-center print:border-gray-400">
                          <span className="font-label-sm text-label-sm uppercase tracking-wider text-outline font-semibold">
                            Institution Student ID
                          </span>
                          <span className="font-headline-sm text-headline-sm font-mono font-bold text-primary mt-1">
                            {profile.instStudentId}
                          </span>
                          <span className="font-code-sm text-code-sm text-outline mt-0.5">
                            Host Campus Enrolment
                          </span>
                        </div>

                        <div className="bg-surface-card p-space-md rounded-lg border border-border-subtle shadow-sm flex flex-col items-center print:border-gray-400">
                          <span className="font-label-sm text-label-sm uppercase tracking-wider text-secondary font-bold">
                            APAAR ID (Sovereign)
                          </span>
                          <span className="font-headline-sm text-headline-sm font-mono font-bold text-secondary mt-1 tracking-wider">
                            {profile.apaarId}
                          </span>
                          <span className="font-code-sm text-code-sm text-status-verified font-medium mt-0.5">
                            12-Digit Academic Digilocker ID
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Verification Seal & Digital Signature */}
                    <div className="w-full max-w-2xl grid grid-cols-1 md:grid-cols-12 gap-space-lg items-center text-left pt-space-sm">
                      <div className="md:col-span-5 flex items-center gap-space-md bg-surface-card p-space-md rounded-xl border border-border-subtle shadow-sm print:border-gray-400">
                        {/* High-fidelity Vector QR Code */}
                        <div className="w-16 h-16 bg-surface-canvas p-1 rounded-lg flex-shrink-0 flex items-center justify-center border border-border-subtle">
                          <svg
                            className="w-full h-full text-primary"
                            fill="currentColor"
                            viewBox="0 0 100 100"
                          >
                            <rect height="28" width="28" x="0" y="0" />
                            <rect fill="#FFFFFF" height="20" width="20" x="4" y="4" />
                            <rect height="12" width="12" x="8" y="8" />
                            <rect height="28" width="28" x="72" y="0" />
                            <rect fill="#FFFFFF" height="20" width="20" x="76" y="4" />
                            <rect height="12" width="12" x="80" y="8" />
                            <rect height="28" width="28" x="0" y="72" />
                            <rect fill="#FFFFFF" height="20" width="20" x="4" y="76" />
                            <rect height="12" width="12" x="8" y="80" />
                            <rect height="6" width="6" x="36" y="10" />
                            <rect height="6" width="12" x="48" y="10" />
                            <rect height="6" width="18" x="36" y="24" />
                            <rect height="18" width="6" x="10" y="38" />
                            <rect height="6" width="12" x="24" y="38" />
                            <rect height="20" width="20" x="40" y="40" />
                            <rect height="8" width="14" x="68" y="38" />
                            <rect height="6" width="20" x="72" y="52" />
                            <rect height="14" width="10" x="38" y="68" />
                            <rect height="8" width="16" x="56" y="72" />
                            <rect height="14" width="12" x="80" y="78" />
                          </svg>
                        </div>
                        <div className="flex flex-col">
                          <span className="font-label-sm text-label-sm font-bold uppercase tracking-wider text-primary">
                            Scan to Verify
                          </span>
                          <span className="font-code-sm text-code-sm text-on-surface-variant leading-tight mt-0.5">
                            SIH Prototype Reference
                          </span>
                          <span className="font-code-sm text-code-sm text-status-verified font-mono font-semibold mt-1">
                            STATUS: OK-VALID
                          </span>
                        </div>
                      </div>

                      <div className="md:col-span-7 flex flex-col gap-1.5 text-right">
                        <div className="flex flex-col">
                          <span className="font-code-sm text-code-sm text-outline font-mono">
                            DIGITALLY SIGNED VIA e-SIGN 3.1
                          </span>
                          <span className="font-title-md text-title-md text-primary font-bold">
                            Registrar (Academic Affairs)
                          </span>
                          <span className="font-body-sm text-body-sm text-on-surface-variant">
                            {profile.institution}
                          </span>
                        </div>
                        <div className="h-px bg-border-subtle w-full my-0.5"></div>
                        <div className="flex items-center justify-end gap-space-xs text-outline font-code-sm text-code-sm">
                          <span className="material-symbols-outlined text-[14px] text-status-verified">
                            verified
                          </span>
                          <span>
                            SHA256: {profile.signatureHash} • {profile.signedDate}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Disclaimer Footnote */}
                    <div className="w-full bg-status-review-surface text-status-review py-space-xs px-space-md rounded-lg flex items-center justify-center gap-space-xs border border-status-review-border">
                      <span className="material-symbols-outlined text-[18px]">info</span>
                      <span className="font-label-md text-label-md tracking-wider uppercase font-bold text-[11px]">
                        PROTOTYPE DEMONSTRATION RECORD — NOT AN OFFICIAL GOVERNMENT ISSUED CREDENTIAL
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* 4. Immutable Audit Trail & Verification Event Log (Bottom Panel) */}
            <div className="w-full bg-surface-card rounded-xl p-space-xl shadow-sm border border-border-subtle flex flex-col gap-space-lg print:hidden">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-space-md border-b border-border-subtle gap-space-xs">
                <div className="flex items-center gap-space-sm">
                  <div className="w-9 h-9 rounded-lg bg-surface-subtle flex items-center justify-center text-primary border border-border-subtle">
                    <span className="material-symbols-outlined text-[20px]">history_edu</span>
                  </div>
                  <div>
                    <h2 className="font-headline-sm text-headline-sm text-primary font-bold">
                      Immutable Audit Trail &amp; Verification Event Ledger
                    </h2>
                    <span className="font-body-sm text-body-sm text-on-surface-variant">
                      Chronological cryptographic records logged under Rule R14
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-space-sm">
                  <span className="font-code-sm text-code-sm text-outline font-mono bg-surface-subtle px-space-xs py-space-2xs rounded border border-border-subtle">
                    RECORD_HASH: 0x82A1B790D4...
                  </span>
                  <button
                    onClick={refreshAuditTrail}
                    disabled={isVerifyingChain}
                    className="px-space-md py-1.5 bg-surface-subtle hover:bg-surface-container rounded-lg font-label-md text-label-md text-primary flex items-center gap-1.5 border border-border-subtle transition-colors cursor-pointer"
                  >
                    <span
                      className={`material-symbols-outlined text-[16px] ${
                        isVerifyingChain ? 'animate-spin' : ''
                      }`}
                    >
                      refresh
                    </span>
                    <span>{isVerifyingChain ? 'Verifying...' : 'Verify Chain'}</span>
                  </button>
                </div>
              </div>

              {/* Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-surface-subtle/60 text-outline font-label-sm text-label-sm uppercase tracking-wider border-b border-border-subtle">
                      <th className="py-space-md px-space-lg rounded-l-lg">Timestamp</th>
                      <th className="py-space-md px-space-lg">Event Type</th>
                      <th className="py-space-md px-space-lg">Actor / System Node</th>
                      <th className="py-space-md px-space-lg">Action Details</th>
                      <th className="py-space-md px-space-lg rounded-r-lg">Compliance Status</th>
                    </tr>
                  </thead>
                  <tbody className="text-on-surface font-body-sm text-body-sm divide-y divide-border-subtle">
                    {profile.auditTrail.map((log, idx) => (
                      <tr key={idx} className="hover:bg-surface-canvas transition-colors">
                        <td className="py-space-md px-space-lg font-mono text-outline font-code-sm text-code-sm whitespace-nowrap">
                          {log.timestamp}
                        </td>
                        <td className="py-space-md px-space-lg">
                          <div className="flex items-center gap-space-xs font-semibold text-primary">
                            <span
                              className={`material-symbols-outlined text-[16px] ${log.iconColor}`}
                            >
                              {log.icon}
                            </span>
                            <span>{log.eventType}</span>
                          </div>
                        </td>
                        <td className="py-space-md px-space-lg font-mono text-on-surface-variant text-code-sm">
                          {log.actor}
                        </td>
                        <td className="py-space-md px-space-lg text-on-surface">
                          {log.actionDetails}
                        </td>
                        <td className="py-space-md px-space-lg">
                          <span
                            className={`font-label-sm text-label-sm px-2.5 py-0.5 rounded-full font-medium inline-flex items-center gap-1.5 border ${log.complianceBadgeClass}`}
                          >
                            <span className="w-1.5 h-1.5 rounded-full bg-status-verified"></span>
                            {log.complianceStatus}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Bottom ledger status */}
              <div className="flex flex-col sm:flex-row items-center justify-between text-on-surface-variant pt-space-xs text-xs">
                <div className="flex items-center gap-space-xs">
                  <span className="material-symbols-outlined text-status-verified text-[16px]">
                    shield
                  </span>
                  <span>
                    Ledger Merkle Tree integrity confirmed: No unverified modifications detected.
                  </span>
                </div>
                <span className="font-mono text-outline">Next auto-sync in 00:14:22</span>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default StudentRecordCertificatePage;
