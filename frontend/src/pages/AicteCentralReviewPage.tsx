import React, { useState, useMemo } from 'react';
import { AuthSession } from '../types/auth';

interface AicteCentralReviewPageProps {
  session?: AuthSession | null;
  onLogout?: () => void;
  onSwitchTab?: (tab: string, apaarId?: string) => void;
}

interface TriageCase {
  id: string;
  ref: string;
  apaarId: string;
  detectedAt: string;
  flagType: string;
  correlation: {
    apaarMatch: string;
    dobMatch: string;
    fuzzyNameMatch: string;
  };
  instA: {
    code: string;
    name: string;
    location: string;
    type: string;
    studentName: string;
    program: string;
    timestamp: string;
    quota: string;
    tuitionFee: string;
    status: string;
    officer: string;
  };
  instB: {
    code: string;
    name: string;
    location: string;
    type: string;
    studentName: string;
    program: string;
    timestamp: string;
    quota: string;
    tuitionFee: string;
    status: string;
    note: string;
  };
  defaultJustification: string;
}

const TRIAGE_CASES: TriageCase[] = [
  {
    id: 'case-1',
    ref: 'XC-DUP-2025-9941',
    apaarId: '9421-8819-4412',
    detectedAt: '23 Jul 2025, 14:22 IST',
    flagType: 'CONCURRENT ADMISSION CONFLICT',
    correlation: {
      apaarMatch: '100% Match',
      dobMatch: '100% Match',
      fuzzyNameMatch: '92% Match',
    },
    instA: {
      code: 'AICTE-1-49281',
      name: 'National Institute of Technology, Trichy',
      location: 'Thuvakudi, Tiruchirappalli, Tamil Nadu (CFTI / Institute of National Importance)',
      type: 'CLAIMANT INST A',
      studentName: 'A. Sharma',
      program: 'B.Tech Computer Science (Year 1)',
      timestamp: '15 Jul 2025 • 11:32:04 IST',
      quota: 'JoSAA Merit (Open/GEN)',
      tuitionFee: 'Fully Remitted (Txn: SBI-98129)',
      status: 'Enrolled & Biometrics Assigned',
      officer: 'Prof. M. Soundararajan (Registrar Academic)',
    },
    instB: {
      code: 'AICTE-1-12048',
      name: 'Vellore Institute of Technology',
      location: 'Katpadi, Vellore, Tamil Nadu (Institution of Eminence / Deemed)',
      type: 'CLAIMANT INST B',
      studentName: 'Abhinav S.',
      program: 'B.Tech Information Technology (Year 1)',
      timestamp: '22 Jul 2025 • 17:08:51 IST',
      quota: 'Management / Institutional Quota',
      tuitionFee: 'Provisional Token Advance (Txn: HDFC-4410)',
      status: 'Enrolled (Orientation Pending)',
      note: 'Candidate likely accepted Seat B without formally processing Seat A release.',
    },
    defaultJustification:
      'Verified admission logs. JoSAA seat surrender receipt #JSA-2025-0982 submitted by candidate on 20-Jul-2025 prior to accepting management seat at VIT. Recommending purge of active state at NIT Trichy.',
  },
  {
    id: 'case-2',
    ref: 'XC-DUP-2025-9942',
    apaarId: '8812-7491-1029',
    detectedAt: '23 Jul 2025, 15:04 IST',
    flagType: 'CONCURRENT ADMISSION CONFLICT',
    correlation: {
      apaarMatch: '100% Match',
      dobMatch: '100% Match',
      fuzzyNameMatch: '98% Match',
    },
    instA: {
      code: 'AICTE-1-20914',
      name: 'COEP Technological University',
      location: 'Shivajinagar, Pune, Maharashtra (Unitary Public University)',
      type: 'CLAIMANT INST A',
      studentName: 'Pooja R. Deshmukh',
      program: 'M.Tech Artificial Intelligence (Year 1)',
      timestamp: '12 Jul 2025 • 09:14:22 IST',
      quota: 'GATE Central Counseling (Open/OBC)',
      tuitionFee: 'Fully Remitted (Txn: BOB-77312)',
      status: 'Enrolled & Biometrics Assigned',
      officer: 'Dr. V. N. Pande (Dean Academics)',
    },
    instB: {
      code: 'AICTE-1-33104',
      name: 'Sardar Patel Institute of Technology',
      location: 'Andheri West, Mumbai, Maharashtra (Autonomous Affiliated)',
      type: 'CLAIMANT INST B',
      studentName: 'Pooja Deshmukh',
      program: 'M.Tech Data Science (Year 1)',
      timestamp: '19 Jul 2025 • 16:45:10 IST',
      quota: 'Institutional Direct Quota',
      tuitionFee: 'Provisional Deposit (Txn: ICICI-1102)',
      status: 'Enrolled (Verification Incomplete)',
      note: 'Dual seat booking suspected across state cap rounds. Physical dossier inspection required.',
    },
    defaultJustification:
      'Candidate is currently attending classes at COEP Tech Pune. Provisional registration at SPIT Mumbai was not confirmed with original transfer certificates.',
  },
  {
    id: 'case-3',
    ref: 'XC-DUP-2025-9943',
    apaarId: '7104-3291-5820',
    detectedAt: '23 Jul 2025, 16:30 IST',
    flagType: 'LATERAL ENTRY COLLISION',
    correlation: {
      apaarMatch: '100% Match',
      dobMatch: '100% Match',
      fuzzyNameMatch: '100% Match',
    },
    instA: {
      code: 'AICTE-1-41901',
      name: 'PSG College of Technology',
      location: 'Peelamedu, Coimbatore, Tamil Nadu (Autonomous Govt-Aided)',
      type: 'CLAIMANT INST A',
      studentName: 'Karthik Subramanian',
      program: 'B.Tech Robotics & Automation (Year 2 Lateral)',
      timestamp: '14 Jul 2025 • 10:11:00 IST',
      quota: 'TNEA Single Window Lateral Merit',
      tuitionFee: 'Fully Remitted (Txn: IOB-55104)',
      status: 'Enrolled & Hostelled',
      officer: 'Dr. K. Prakasan (Principal)',
    },
    instB: {
      code: 'AICTE-1-40291',
      name: 'SSN College of Engineering',
      location: 'Kalavakkam, Chennai, Tamil Nadu (Autonomous / Anna Univ)',
      type: 'CLAIMANT INST B',
      studentName: 'Karthik Subramanian',
      program: 'B.Tech Electronics & Communication (Year 2 Lateral)',
      timestamp: '18 Jul 2025 • 14:02:18 IST',
      quota: 'Management Lateral Merit',
      tuitionFee: 'Full Fee Advance (Txn: AXIS-3901)',
      status: 'Provisional Admission Issued',
      note: 'Dossier duplicate flagged during Anna University central database sync.',
    },
    defaultJustification:
      'Candidate accepted TNEA state merit seat at PSG Tech. Refund application filed with SSN Chennai under UGC/AICTE refund mandate 2025.',
  },
];

interface BreachRecord {
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

const INITIAL_BREACH_RECORDS: BreachRecord[] = [
  {
    pid: '1-3329182',
    name: 'K.J. Somaiya College of Engineering',
    location: 'Mumbai, Maharashtra',
    course: 'B.Tech AI & DS',
    affiliation: 'Autonomous / Somaiya Univ',
    cap: 120,
    intake: 132,
    excess: 12,
    excessTag: '+12 Excess',
    citation: 'APH 2025 Cl 7.2.3',
    citationDesc: 'Over-intake without EWS quota offset',
    actionText: 'Show Cause Notice',
    actionStyle: 'error',
    state: 'Maharashtra',
  },
  {
    pid: '1-4910283',
    name: 'BMS College of Engineering',
    location: 'Bengaluru, Karnataka',
    course: 'M.Tech VLSI Design',
    affiliation: 'Affiliated / VTU Belagavi',
    cap: 24,
    intake: 29,
    excess: 5,
    excessTag: '+5 Excess',
    citation: 'APH 2025 Cl 4.1.8',
    citationDesc: 'Exceeded PG batch limit per faculty cadre',
    actionText: 'Explanations Filed',
    actionStyle: 'subtle',
    state: 'Karnataka',
  },
  {
    pid: '1-1928402',
    name: 'SRM Institute of Science & Technology',
    location: 'Kattankulathur, Tamil Nadu',
    course: 'B.Tech Mechanical',
    affiliation: 'Deemed-to-be-University',
    cap: 180,
    intake: 182,
    excess: 2,
    excessTag: '+2 Excess',
    citation: 'APH 2025 Cl 2.9.1',
    citationDesc: 'Candidate enrolled under J&K PMSSS quota discrepancy',
    actionText: 'Review Supernumerary',
    actionStyle: 'subtle',
    state: 'Tamil Nadu',
  },
  {
    pid: '1-8840192',
    name: 'Dr. A.P.J. Abdul Kalam Technical University Regional Campus',
    location: 'Lucknow, Uttar Pradesh',
    course: 'MCA',
    affiliation: 'State Government University',
    cap: 60,
    intake: 71,
    excess: 11,
    excessTag: '+11 Excess',
    citation: 'APH 2025 Cl 6.4.0',
    citationDesc: 'Unapproved evening section batch merge',
    actionText: 'Show Cause Notice',
    actionStyle: 'error',
    state: 'Uttar Pradesh',
  },
  {
    pid: '1-5519201',
    name: 'COEP Technological University',
    location: 'Pune, Maharashtra',
    course: 'B.Tech Electrical Engineering',
    affiliation: 'Unitary State University',
    cap: 60,
    intake: 66,
    excess: 6,
    excessTag: '+6 Excess',
    citation: 'APH 2025 Cl 3.1.2',
    citationDesc: 'TFWS lateral intake exceeded 5% statutory ceiling',
    actionText: 'Show Cause Notice',
    actionStyle: 'error',
    state: 'Maharashtra',
  },
  {
    pid: '1-7712903',
    name: 'R.V. College of Engineering',
    location: 'Bengaluru, Karnataka',
    course: 'B.Tech Cyber Security',
    affiliation: 'Affiliated / VTU Belagavi',
    cap: 60,
    intake: 64,
    excess: 4,
    excessTag: '+4 Excess',
    citation: 'APH 2025 Cl 5.2.0',
    citationDesc: 'Supernumerary sports / defense quota overflow',
    actionText: 'Review Supernumerary',
    actionStyle: 'subtle',
    state: 'Karnataka',
  },
];

export const AicteCentralReviewPage: React.FC<AicteCentralReviewPageProps> = ({
  session,
  onLogout,
  onSwitchTab,
}) => {
  // Navigation active tab
  const [activeTab, setActiveTab] = useState<string>('aicte-review');

  // Case index
  const [caseIndex, setCaseIndex] = useState<number>(0);
  const currentCase = TRIAGE_CASES[caseIndex];

  // APAAR ID decrypted toggle
  const [isApaarDecrypted, setIsApaarDecrypted] = useState<boolean>(false);

  // Verdict state
  const [verdict, setVerdict] = useState<string>('migration');
  const [justification, setJustification] = useState<string>(
    currentCase.defaultJustification
  );

  // Filter ribbon state
  const [selectedState, setSelectedState] = useState<string>('all');
  const [selectedInstType, setSelectedInstType] = useState<string>('all');
  const [selectedAnomaly, setSelectedAnomaly] = useState<string>('dual');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');

  // Breach Table search & action state
  const [tableSearch, setTableSearch] = useState<string>('');
  const [breachRecords, setBreachRecords] = useState<BreachRecord[]>(
    INITIAL_BREACH_RECORDS
  );

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

  // Switch case handlers
  const handleNextCase = () => {
    const nextIdx = (caseIndex + 1) % TRIAGE_CASES.length;
    setCaseIndex(nextIdx);
    setIsApaarDecrypted(false);
    setJustification(TRIAGE_CASES[nextIdx].defaultJustification);
  };

  const handlePrevCase = () => {
    const prevIdx =
      (caseIndex - 1 + TRIAGE_CASES.length) % TRIAGE_CASES.length;
    setCaseIndex(prevIdx);
    setIsApaarDecrypted(false);
    setJustification(TRIAGE_CASES[prevIdx].defaultJustification);
  };

  // Submit determination
  const handleSubmitVerdict = () => {
    const sha256Mock =
      '0x' +
      Math.random()
        .toString(16)
        .substring(2, 10) +
      Math.random()
        .toString(16)
        .substring(2, 10) +
      '...' +
      Math.random()
        .toString(16)
        .substring(2, 6);

    showToast(
      `Decision Submitted & Signed! Case ${currentCase.ref} archived to Ledger with Hash: ${sha256Mock}`
    );
  };

  // Action on breach row
  const handleBreachAction = (pid: string, actionText: string) => {
    setBreachRecords((prev) =>
      prev.map((rec) => {
        if (rec.pid === pid) {
          return {
            ...rec,
            actionText: actionText === 'Show Cause Notice' ? 'Notice Dispatched' : 'Audited & Logged',
            actionStyle: 'subtle',
          };
        }
        return rec;
      })
    );
    showToast(`Notice/Action triggered for Permanent ID ${pid}: ${actionText}`);
  };

  // Trigger National Rescan
  const handleTriggerRescan = () => {
    setIsScanning(true);
    showToast('Initiating cryptographic identity rescan across 8,940 approved institutions...');
    setTimeout(() => {
      setIsScanning(false);
      showToast('National Rescan Completed: 87 Active Cases verified. Zero Aadhaar vault hash breaches.');
    }, 2000);
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

  // Masked APAAR ID helper
  const maskedApaarId = isApaarDecrypted
    ? currentCase.apaarId
    : currentCase.apaarId.slice(0, 5) + '••••-' + currentCase.apaarId.slice(-4);

  return (
    <div className="bg-surface-canvas font-body-md text-on-surface antialiased min-h-screen flex flex-col relative selection:bg-secondary/20">
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
                  : 'National Institute of Technology, Trichy (ID: AICTE-1-49281)'}
              </span>
            </div>

            {/* Role dropdown switcher */}
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
                <span className="absolute top-1 right-1 w-2 h-2 bg-status-error rounded-full animate-pulse"></span>
              </button>

              {showNotificationBell && (
                <div className="absolute right-0 mt-2 w-80 bg-surface-card rounded-xl shadow-xl border border-border-strong p-3 z-50 text-xs">
                  <div className="font-bold text-primary border-b border-border-subtle pb-2 mb-2 flex items-center justify-between">
                    <span>Audit Notices</span>
                    <span className="bg-status-error-surface text-status-error px-1.5 py-0.5 rounded text-[10px] font-mono">
                      87 Cases
                    </span>
                  </div>
                  <div className="space-y-2 max-h-56 overflow-y-auto">
                    <div className="p-2 bg-surface-subtle rounded border border-border-subtle">
                      <div className="font-semibold text-primary">Concurrent Enrolment Conflict</div>
                      <div className="text-on-surface-variant text-[11px]">
                        Ref: XC-DUP-2025-9941 (NIT Trichy vs VIT Vellore)
                      </div>
                    </div>
                    <div className="p-2 bg-surface-subtle rounded border border-border-subtle">
                      <div className="font-semibold text-primary">Capacity Cap Overrun</div>
                      <div className="text-on-surface-variant text-[11px]">
                        142 Institutions flagged under APH 2025-26 Cl 7.2.3
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
                  {session?.roleTitle ? session.roleTitle : 'RK (Registrar)'}
                </span>
                <span className="font-label-sm text-label-sm text-outline leading-tight">
                  {session?.userEmail ? session.userEmail : 'Academic Cell'}
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
      <main className="w-full pt-32 bg-surface-canvas min-h-screen pb-16 flex-1">
        <div className="flex flex-col w-full">
          {/* Sovereign Breadcrumb & Classification Ribbon */}
          <div className="w-full bg-surface-container-high px-gutter-md py-space-sm shadow-sm flex flex-wrap items-center justify-between gap-space-sm">
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
                Cross-Institution Deduplication &amp; Intake Integrity
              </span>
            </div>
            <div className="flex items-center gap-space-md flex-wrap">
              <span className="inline-flex items-center gap-space-xs font-code-sm text-code-sm text-on-surface-variant bg-surface-subtle px-space-sm py-space-2xs rounded border border-border-subtle">
                <span className="w-2 h-2 rounded-full bg-status-review animate-ping"></span>
                TRIAGE QUEUE: 87 CASES LOCKED
              </span>
              <span className="font-code-sm text-code-sm text-status-verified font-semibold bg-status-verified-surface px-space-sm py-space-2xs rounded border border-status-verified-border">
                AUDIT SESSION ID: APEX-REV-8921-X9
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
                    AICTE Apex Council Student Data Reconciliation Console
                  </h1>
                  <p className="font-body-md text-body-md text-on-surface-variant leading-relaxed">
                    National Ingestion Cycle 2025–26 — 8,940 Approved Institutions Reporting. System-wide cryptographic identity triage against sovereign APAAR records.
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
                    {isScanning ? 'Scanning Database...' : 'Trigger National Rescan'}
                  </button>
                </div>
              </div>

              {/* Spacious Multifaceted Filter Ribbon */}
              <div className="mt-space-xl pt-space-xl border-t border-border-subtle grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-space-md">
                <div className="flex flex-col gap-space-xs">
                  <label className="font-label-sm text-label-sm text-outline font-semibold uppercase tracking-wider">
                    Jurisdiction / State
                  </label>
                  <select
                    value={selectedState}
                    onChange={(e) => setSelectedState(e.target.value)}
                    className="bg-surface-canvas border border-border-strong rounded-lg px-space-md py-space-sm font-body-sm text-body-sm text-on-surface focus:outline-none focus:border-secondary transition-colors"
                  >
                    <option value="all">All Regions (Southern &amp; Western Prime)</option>
                    <option value="TN">Tamil Nadu (State Code: 33)</option>
                    <option value="MH">Maharashtra (State Code: 27)</option>
                    <option value="KA">Karnataka (State Code: 29)</option>
                    <option value="UP">Uttar Pradesh (State Code: 09)</option>
                  </select>
                </div>
                <div className="flex flex-col gap-space-xs">
                  <label className="font-label-sm text-label-sm text-outline font-semibold uppercase tracking-wider">
                    Institution Type
                  </label>
                  <select
                    value={selectedInstType}
                    onChange={(e) => setSelectedInstType(e.target.value)}
                    className="bg-surface-canvas border border-border-strong rounded-lg px-space-md py-space-sm font-body-sm text-body-sm text-on-surface focus:outline-none focus:border-secondary transition-colors"
                  >
                    <option value="all">All Types (Autonomous / Affiliated)</option>
                    <option value="auto">Autonomous Technical Institutes</option>
                    <option value="affil">State University Affiliated Colleges</option>
                    <option value="deemed">Deemed-to-be Universities</option>
                    <option value="cfti">Centrally Funded Technical Institutes</option>
                  </select>
                </div>
                <div className="flex flex-col gap-space-xs">
                  <label className="font-label-sm text-label-sm text-outline font-semibold uppercase tracking-wider">
                    Anomaly Pattern
                  </label>
                  <select
                    value={selectedAnomaly}
                    onChange={(e) => setSelectedAnomaly(e.target.value)}
                    className="bg-surface-canvas border border-border-strong rounded-lg px-space-md py-space-sm font-body-sm text-body-sm text-on-surface focus:outline-none focus:border-secondary transition-colors"
                  >
                    <option value="all">All Flagged Categories</option>
                    <option value="dual">Dual Institutional Enrolment</option>
                    <option value="cap">Intake Cap Overrun</option>
                    <option value="aadhaar">Aadhaar-APAAR Hash Discrepancy</option>
                    <option value="lateral">Unapproved Lateral Shift</option>
                  </select>
                </div>
                <div className="flex flex-col gap-space-xs">
                  <label className="font-label-sm text-label-sm text-outline font-semibold uppercase tracking-wider">
                    Severity Filter
                  </label>
                  <select
                    value={selectedSeverity}
                    onChange={(e) => setSelectedSeverity(e.target.value)}
                    className="bg-surface-canvas border border-border-strong rounded-lg px-space-md py-space-sm font-body-sm text-body-sm text-on-surface focus:outline-none focus:border-secondary transition-colors"
                  >
                    <option value="all">High &amp; Statutory Violation</option>
                    <option value="crit">Critical (Statutory Notice Pending)</option>
                    <option value="mod">Moderate (Documentation Gap)</option>
                    <option value="info">Informational</option>
                  </select>
                </div>
                <div className="flex flex-col justify-end">
                  <button
                    onClick={() =>
                      showToast(
                        `Parameters updated. Filtered triage queue to 87 matching records.`
                      )
                    }
                    className="w-full bg-surface-container text-primary font-label-md text-label-md px-space-md py-space-sm rounded-lg hover:bg-surface-container-high transition-colors flex items-center justify-center gap-space-xs h-10 border border-border-strong cursor-pointer"
                  >
                    <span className="material-symbols-outlined text-[18px]">filter_alt</span>
                    Apply Parameters (87)
                  </button>
                </div>
              </div>
            </header>

            {/* NATIONAL EXCEPTION METRICS BENTO */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-space-lg">
              {/* Metric 1 */}
              <div className="bg-surface-card rounded-xl p-space-xl shadow-sm border border-border-subtle flex flex-col justify-between hover:shadow-md transition-shadow">
                <div className="flex items-center justify-between text-outline mb-space-sm">
                  <span className="font-label-md text-label-md font-semibold uppercase tracking-wider">
                    Submissions Cycle
                  </span>
                  <span className="material-symbols-outlined text-[22px] text-primary">
                    account_balance
                  </span>
                </div>
                <div className="my-space-md flex items-baseline gap-space-sm">
                  <span className="font-display-lg text-display-lg font-bold text-primary">
                    7,420
                  </span>
                  <span className="font-headline-sm text-headline-sm text-on-surface-variant font-medium">
                    / 8,940
                  </span>
                </div>
                <div className="flex items-center justify-between pt-space-sm border-t border-border-subtle mt-space-xs">
                  <div className="w-2/3 bg-surface-subtle h-2 rounded-full overflow-hidden">
                    <div className="bg-primary h-full w-[83%]"></div>
                  </div>
                  <span className="font-code-sm text-code-sm text-status-verified font-bold">
                    83.0% Rep.
                  </span>
                </div>
              </div>

              {/* Metric 2 */}
              <div className="bg-surface-card rounded-xl p-space-xl shadow-sm border border-border-subtle flex flex-col justify-between hover:shadow-md transition-shadow">
                <div className="flex items-center justify-between text-outline mb-space-sm">
                  <span className="font-label-md text-label-md font-semibold uppercase tracking-wider">
                    Intake Breaches
                  </span>
                  <span className="material-symbols-outlined text-[22px] text-status-error">
                    warning
                  </span>
                </div>
                <div className="my-space-md flex items-baseline gap-space-sm">
                  <span className="font-display-lg text-display-lg font-bold text-status-error">
                    142
                  </span>
                  <span className="font-label-sm text-label-sm text-status-error bg-status-error-surface px-space-xs py-space-2xs rounded border border-status-error-border font-bold">
                    +1,240 excess
                  </span>
                </div>
                <div className="flex items-center justify-between pt-space-sm border-t border-border-subtle mt-space-xs">
                  <span className="font-body-sm text-body-sm text-on-surface-variant">
                    Institutions over cap
                  </span>
                  <span className="font-code-sm text-code-sm text-status-error font-semibold">
                    Action Required
                  </span>
                </div>
              </div>

              {/* Metric 3 */}
              <div className="bg-surface-card rounded-xl p-space-xl shadow-sm border border-border-subtle flex flex-col justify-between hover:shadow-md transition-shadow">
                <div className="flex items-center justify-between text-outline mb-space-sm">
                  <span className="font-label-md text-label-md font-semibold uppercase tracking-wider">
                    Cross-Inst. Duplicates
                  </span>
                  <span className="material-symbols-outlined text-[22px] text-status-review">
                    people
                  </span>
                </div>
                <div className="my-space-md flex items-baseline gap-space-sm">
                  <span className="font-display-lg text-display-lg font-bold text-status-review">
                    87
                  </span>
                  <span className="font-body-sm text-body-sm text-on-surface-variant">
                    Cases in Queue
                  </span>
                </div>
                <div className="flex items-center justify-between pt-space-sm border-t border-border-subtle mt-space-xs">
                  <span className="font-body-sm text-body-sm text-on-surface-variant">
                    Avg. resolution time
                  </span>
                  <span className="font-code-sm text-code-sm text-primary font-semibold">
                    3.8 Days
                  </span>
                </div>
              </div>

              {/* Metric 4 */}
              <div className="bg-surface-card rounded-xl p-space-xl shadow-sm border border-border-subtle flex flex-col justify-between hover:shadow-md transition-shadow">
                <div className="flex items-center justify-between text-outline mb-space-sm">
                  <span className="font-label-md text-label-md font-semibold uppercase tracking-wider">
                    Verification Pipeline
                  </span>
                  <span className="material-symbols-outlined text-[22px] text-secondary">
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
                    Deterministic Seed
                  </span>
                  <span className="font-code-sm text-code-sm bg-surface-subtle px-space-xs rounded text-primary">
                    SIH-2026-N2
                  </span>
                </div>
              </div>
            </div>

            {/* MAIN INTERACTIVE SECTION: CROSS-INSTITUTION DUPLICATE ENROLMENT TRIAGE QUEUE */}
            <section className="flex flex-col gap-space-lg">
              {/* Statutory Human-In-The-Loop Advisory */}
              <div className="bg-status-review-surface border border-status-review-border rounded-xl p-space-lg flex items-start gap-space-md shadow-sm">
                <span className="material-symbols-outlined text-status-review text-[26px] mt-0.5 shrink-0">
                  admin_panel_settings
                </span>
                <div className="flex flex-col gap-space-2xs">
                  <div className="flex items-center gap-space-sm flex-wrap">
                    <span className="font-headline-sm text-headline-sm text-on-surface font-bold">
                      Statutory Human-in-the-Loop Protocol (APAAR Directive 2025/AD-4)
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

              {/* Case Card Wrapper */}
              <div className="bg-surface-card rounded-xl shadow-md border border-border-strong overflow-hidden flex flex-col">
                {/* Case Identification Top Bar */}
                <div className="bg-surface-subtle px-space-xl py-space-md border-b border-border-subtle flex flex-wrap items-center justify-between gap-space-md">
                  <div className="flex items-center gap-space-md flex-wrap">
                    <div className="flex items-center gap-space-xs">
                      <span className="font-label-sm text-label-sm text-outline uppercase font-semibold">
                        Triage Case Ref:
                      </span>
                      <span className="font-code-sm text-code-sm text-primary font-bold bg-surface-card px-space-sm py-space-2xs rounded border border-border-strong">
                        {currentCase.ref}
                      </span>
                    </div>
                    <div className="flex items-center gap-space-xs">
                      <span className="font-label-sm text-label-sm text-outline uppercase font-semibold">
                        APAAR ID:
                      </span>
                      <span className="font-code-sm text-code-sm text-primary font-bold bg-surface-card px-space-sm py-space-2xs rounded border border-border-strong tracking-widest">
                        {maskedApaarId}
                      </span>
                      <button
                        onClick={() => {
                          const willDecrypt = !isApaarDecrypted;
                          setIsApaarDecrypted(willDecrypt);
                          if (willDecrypt) {
                            showToast(
                              `Sovereign Audit Alert: Decrypted view of APAAR ID ${currentCase.apaarId} logged to immutable session record.`
                            );
                          }
                        }}
                        className="text-on-surface-variant hover:text-primary p-space-2xs cursor-pointer transition-colors"
                        title={
                          isApaarDecrypted
                            ? 'Mask APAAR ID'
                            : 'Decrypted view logged to sovereign audit record'
                        }
                      >
                        <span className="material-symbols-outlined text-[16px]">
                          {isApaarDecrypted ? 'visibility_off' : 'visibility'}
                        </span>
                      </button>
                      <button
                        onClick={() => {
                          if (onSwitchTab) {
                            onSwitchTab('records', currentCase.apaarId);
                          }
                        }}
                        className="ml-1 text-secondary hover:text-navy-accent bg-surface-card hover:bg-surface-subtle px-2 py-0.5 rounded border border-border-strong text-xs font-semibold flex items-center gap-1 transition-all cursor-pointer shadow-sm"
                        title="View Verified Student Record & Attestation Certificate"
                      >
                        <span className="material-symbols-outlined text-[14px]">workspace_premium</span>
                        <span>View Certificate</span>
                      </button>
                    </div>
                    <span className="font-code-sm text-code-sm bg-status-error-surface text-status-error px-space-xs py-space-2xs rounded border border-status-error-border font-bold">
                      {currentCase.flagType}
                    </span>
                  </div>

                  <div className="flex items-center gap-space-md">
                    <span className="font-label-sm text-label-sm text-outline hidden sm:inline">
                      Detected by Engine: {currentCase.detectedAt}
                    </span>
                    <span className="font-label-md text-label-md text-on-surface-variant font-semibold">
                      Case {caseIndex + 1} of {TRIAGE_CASES.length} (Queue: 87)
                    </span>
                    <div className="inline-flex rounded-md shadow-sm">
                      <button
                        onClick={handlePrevCase}
                        aria-label="Previous Case"
                        className="bg-surface-card border border-border-strong px-space-xs py-space-2xs rounded-l hover:bg-surface-subtle text-primary cursor-pointer"
                      >
                        <span className="material-symbols-outlined text-[16px]">
                          chevron_left
                        </span>
                      </button>
                      <button
                        onClick={handleNextCase}
                        aria-label="Next Case"
                        className="bg-surface-card border-t border-b border-r border-border-strong px-space-xs py-space-2xs rounded-r hover:bg-surface-subtle text-primary cursor-pointer"
                      >
                        <span className="material-symbols-outlined text-[16px]">
                          chevron_right
                        </span>
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
                          Deterministic identity matrix verified via DigiLocker / Aadhaar Vault Token
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-space-md flex-wrap">
                      <div className="flex items-center gap-space-xs bg-surface-card px-space-md py-space-xs rounded-lg border border-border-subtle shadow-sm">
                        <span className="font-label-sm text-label-sm text-outline">
                          APAAR Identifier:
                        </span>
                        <span className="font-code-sm text-code-sm text-status-verified font-bold">
                          {currentCase.correlation.apaarMatch}
                        </span>
                        <span className="material-symbols-outlined text-status-verified text-[16px]">
                          check_circle
                        </span>
                      </div>
                      <div className="flex items-center gap-space-xs bg-surface-card px-space-md py-space-xs rounded-lg border border-border-subtle shadow-sm">
                        <span className="font-label-sm text-label-sm text-outline">
                          Birth Date Vector:
                        </span>
                        <span className="font-code-sm text-code-sm text-status-verified font-bold">
                          {currentCase.correlation.dobMatch}
                        </span>
                        <span className="material-symbols-outlined text-status-verified text-[16px]">
                          check_circle
                        </span>
                      </div>
                      <div className="flex items-center gap-space-xs bg-surface-card px-space-md py-space-xs rounded-lg border border-border-subtle shadow-sm">
                        <span className="font-label-sm text-label-sm text-outline">
                          Fuzzy Token Name:
                        </span>
                        <span className="font-code-sm text-code-sm text-status-review font-bold">
                          {currentCase.correlation.fuzzyNameMatch}
                        </span>
                        <span className="material-symbols-outlined text-status-review text-[16px]">
                          priority_high
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Split Comparison Dual Panels */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-space-xl relative">
                    {/* Midline VS Badge on Desktop */}
                    <div className="hidden lg:flex absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10 w-10 h-10 rounded-full bg-primary text-on-primary font-code-sm text-code-sm font-bold items-center justify-center shadow-lg border-2 border-surface-card">
                      VS
                    </div>

                    {/* Institution A Column */}
                    <div className="bg-surface-canvas rounded-xl p-space-xl border border-border-strong flex flex-col gap-space-lg">
                      <div className="flex items-center justify-between border-b border-border-subtle pb-space-md">
                        <div className="flex items-center gap-space-xs">
                          <span className="font-label-sm text-label-sm bg-primary text-on-primary px-space-xs py-space-2xs rounded font-bold">
                            {currentCase.instA.type}
                          </span>
                          <span className="font-label-sm text-label-sm text-status-verified bg-status-verified-surface px-space-xs py-space-2xs rounded font-semibold border border-status-verified-border">
                            Earlier Timestamp
                          </span>
                        </div>
                        <span className="font-code-sm text-code-sm text-outline font-semibold">
                          CODE: {currentCase.instA.code}
                        </span>
                      </div>
                      <div className="flex flex-col gap-space-2xs">
                        <h3 className="font-headline-md text-headline-md text-primary font-bold">
                          {currentCase.instA.name}
                        </h3>
                        <span className="font-body-sm text-body-sm text-on-surface-variant">
                          {currentCase.instA.location}
                        </span>
                      </div>
                      <div className="bg-surface-card rounded-lg p-space-lg border border-border-subtle space-y-space-md shadow-sm">
                        <div className="flex justify-between items-center py-space-xs border-b border-border-subtle">
                          <span className="font-label-md text-label-md text-outline">
                            Registered Student:
                          </span>
                          <span className="font-headline-sm text-headline-sm text-primary font-bold">
                            {currentCase.instA.studentName}
                          </span>
                        </div>
                        <div className="flex justify-between items-center py-space-xs border-b border-border-subtle">
                          <span className="font-label-md text-label-md text-outline">
                            Program &amp; Year:
                          </span>
                          <span className="font-body-md text-body-md text-on-surface font-semibold">
                            {currentCase.instA.program}
                          </span>
                        </div>
                        <div className="flex justify-between items-center py-space-xs border-b border-border-subtle">
                          <span className="font-label-md text-label-md text-outline">
                            Admission Timestamp:
                          </span>
                          <span className="font-code-sm text-code-sm text-primary font-bold">
                            {currentCase.instA.timestamp}
                          </span>
                        </div>
                        <div className="flex justify-between items-center py-space-xs border-b border-border-subtle">
                          <span className="font-label-md text-label-md text-outline">
                            Seat Allocation Quota:
                          </span>
                          <span className="font-code-sm text-code-sm text-status-verified bg-status-verified-surface px-space-xs py-space-2xs rounded font-bold border border-status-verified-border">
                            {currentCase.instA.quota}
                          </span>
                        </div>
                        <div className="flex justify-between items-center py-space-xs border-b border-border-subtle">
                          <span className="font-label-md text-label-md text-outline">
                            Tuition Fee Ledger:
                          </span>
                          <span className="font-code-sm text-code-sm text-status-verified font-semibold">
                            {currentCase.instA.tuitionFee}
                          </span>
                        </div>
                        <div className="flex justify-between items-center py-space-xs">
                          <span className="font-label-md text-label-md text-outline">
                            Campus Registry Status:
                          </span>
                          <span className="font-label-sm text-label-sm bg-status-verified-surface text-status-verified font-bold px-space-xs py-space-2xs rounded border border-status-verified-border">
                            {currentCase.instA.status}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-space-sm text-on-surface-variant font-body-sm text-body-sm bg-surface-subtle p-space-md rounded-lg border border-border-subtle">
                        <span className="material-symbols-outlined text-[18px] text-primary">
                          verified
                        </span>
                        <span>Reporting Officer: {currentCase.instA.officer}</span>
                      </div>
                    </div>

                    {/* Institution B Column */}
                    <div className="bg-surface-canvas rounded-xl p-space-xl border border-border-strong flex flex-col gap-space-lg">
                      <div className="flex items-center justify-between border-b border-border-subtle pb-space-md">
                        <div className="flex items-center gap-space-xs">
                          <span className="font-label-sm text-label-sm bg-surface-container-highest text-primary px-space-xs py-space-2xs rounded font-bold">
                            {currentCase.instB.type}
                          </span>
                          <span className="font-label-sm text-label-sm text-status-error bg-status-error-surface px-space-xs py-space-2xs rounded font-semibold border border-status-error-border">
                            +7 Days Later
                          </span>
                        </div>
                        <span className="font-code-sm text-code-sm text-outline font-semibold">
                          CODE: {currentCase.instB.code}
                        </span>
                      </div>
                      <div className="flex flex-col gap-space-2xs">
                        <h3 className="font-headline-md text-headline-md text-primary font-bold">
                          {currentCase.instB.name}
                        </h3>
                        <span className="font-body-sm text-body-sm text-on-surface-variant">
                          {currentCase.instB.location}
                        </span>
                      </div>
                      <div className="bg-surface-card rounded-lg p-space-lg border border-border-subtle space-y-space-md shadow-sm">
                        <div className="flex justify-between items-center py-space-xs border-b border-border-subtle">
                          <span className="font-label-md text-label-md text-outline">
                            Registered Student:
                          </span>
                          <span className="font-headline-sm text-headline-sm text-primary font-bold">
                            {currentCase.instB.studentName}
                          </span>
                        </div>
                        <div className="flex justify-between items-center py-space-xs border-b border-border-subtle">
                          <span className="font-label-md text-label-md text-outline">
                            Program &amp; Year:
                          </span>
                          <span className="font-body-md text-body-md text-on-surface font-semibold">
                            {currentCase.instB.program}
                          </span>
                        </div>
                        <div className="flex justify-between items-center py-space-xs border-b border-border-subtle">
                          <span className="font-label-md text-label-md text-outline">
                            Admission Timestamp:
                          </span>
                          <span className="font-code-sm text-code-sm text-primary font-bold">
                            {currentCase.instB.timestamp}
                          </span>
                        </div>
                        <div className="flex justify-between items-center py-space-xs border-b border-border-subtle">
                          <span className="font-label-md text-label-md text-outline">
                            Seat Allocation Quota:
                          </span>
                          <span className="font-code-sm text-code-sm text-status-review bg-status-review-surface px-space-xs py-space-2xs rounded font-bold border border-status-review-border">
                            {currentCase.instB.quota}
                          </span>
                        </div>
                        <div className="flex justify-between items-center py-space-xs border-b border-border-subtle">
                          <span className="font-label-md text-label-md text-outline">
                            Tuition Fee Ledger:
                          </span>
                          <span className="font-code-sm text-code-sm text-status-review font-semibold">
                            {currentCase.instB.tuitionFee}
                          </span>
                        </div>
                        <div className="flex justify-between items-center py-space-xs">
                          <span className="font-label-md text-label-md text-outline">
                            Campus Registry Status:
                          </span>
                          <span className="font-label-sm text-label-sm bg-status-review-surface text-status-review font-bold px-space-xs py-space-2xs rounded border border-status-review-border">
                            {currentCase.instB.status}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-space-sm text-on-surface-variant font-body-sm text-body-sm bg-surface-subtle p-space-md rounded-lg border border-border-subtle">
                        <span className="material-symbols-outlined text-[18px] text-secondary">
                          info
                        </span>
                        <span>{currentCase.instB.note}</span>
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
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-space-md">
                      <label
                        className={`relative flex items-start gap-space-sm p-space-lg rounded-xl border cursor-pointer transition-all ${
                          verdict === 'concurrent'
                            ? 'border-primary bg-surface-subtle shadow-sm'
                            : 'border-border-strong hover:border-primary bg-surface-canvas'
                        }`}
                      >
                        <input
                          type="radio"
                          name="triage_verdict"
                          value="concurrent"
                          checked={verdict === 'concurrent'}
                          onChange={() => setVerdict('concurrent')}
                          className="mt-1 text-primary focus:ring-secondary cursor-pointer"
                        />
                        <div className="flex flex-col">
                          <span className="font-title-md text-title-md text-primary font-bold">
                            Concurrent Enrolment Notice
                          </span>
                          <span className="font-body-sm text-body-sm text-on-surface-variant mt-1 leading-relaxed">
                            Issue official 72-hour notice under Section 11 to candidate and both registrars.
                          </span>
                        </div>
                      </label>

                      <label
                        className={`relative flex items-start gap-space-sm p-space-lg rounded-xl border cursor-pointer transition-all ${
                          verdict === 'migration'
                            ? 'border-primary bg-surface-subtle shadow-sm'
                            : 'border-border-strong hover:border-primary bg-surface-canvas'
                        }`}
                      >
                        <input
                          type="radio"
                          name="triage_verdict"
                          value="migration"
                          checked={verdict === 'migration'}
                          onChange={() => setVerdict('migration')}
                          className="mt-1 text-primary focus:ring-secondary cursor-pointer"
                        />
                        <div className="flex flex-col">
                          <span className="font-title-md text-title-md text-primary font-bold">
                            Permitted Migration / Cancellation
                          </span>
                          <span className="font-body-sm text-body-sm text-on-surface-variant mt-1 leading-relaxed">
                            Accept withdrawal affidavit at Institute A; confirm bona-fide enrolment at Institute B.
                          </span>
                        </div>
                      </label>

                      <label
                        className={`relative flex items-start gap-space-sm p-space-lg rounded-xl border cursor-pointer transition-all ${
                          verdict === 'evidence'
                            ? 'border-primary bg-surface-subtle shadow-sm'
                            : 'border-border-strong hover:border-primary bg-surface-canvas'
                        }`}
                      >
                        <input
                          type="radio"
                          name="triage_verdict"
                          value="evidence"
                          checked={verdict === 'evidence'}
                          onChange={() => setVerdict('evidence')}
                          className="mt-1 text-primary focus:ring-secondary cursor-pointer"
                        />
                        <div className="flex flex-col">
                          <span className="font-title-md text-title-md text-primary font-bold">
                            Request Physical Dossier
                          </span>
                          <span className="font-body-sm text-body-sm text-on-surface-variant mt-1 leading-relaxed">
                            Order Regional Office RO-Chennai to inspect original transfer certificates in person.
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
                          Mandatory Statutory Justification &amp; Gazette Citation{' '}
                          <span className="text-status-error">*</span>
                        </label>
                        <span className="font-code-sm text-code-sm text-outline font-semibold">
                          Signed by Digital Token:{' '}
                          <span className="text-primary font-bold">
                            {session?.instCode ? `APEX-${session.instCode}` : 'RK-AICTE-77'}
                          </span>
                        </span>
                      </div>
                      <textarea
                        id="review_justification"
                        rows={3}
                        value={justification}
                        onChange={(e) => setJustification(e.target.value)}
                        placeholder="Specify evidentiary grounds, cross-checked TC numbers, fee refund reference or statutory basis for order... (Min 25 characters)"
                        className="w-full bg-surface-canvas border border-border-strong rounded-xl p-space-md font-body-md text-body-md text-on-surface focus:outline-none focus:border-secondary transition-colors"
                      />
                      <div className="flex justify-between text-xs text-outline pt-1">
                        <span>Min required: 25 characters</span>
                        <span>{justification.length} characters entered</span>
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex flex-wrap items-center justify-between gap-space-md pt-space-md border-t border-border-subtle">
                      <div className="flex items-center gap-space-xs text-status-verified">
                        <span className="material-symbols-outlined text-[18px]">lock</span>
                        <span className="font-code-sm text-code-sm font-semibold">
                          Action will produce immutable SHA-256 ledger transaction
                        </span>
                      </div>
                      <div className="flex items-center gap-space-sm flex-wrap">
                        <button
                          onClick={() =>
                            showToast(
                              `Flagged Case ${currentCase.ref} for Regional Officer physical review.`
                            )
                          }
                          className="bg-surface-card border border-status-error text-status-error hover:bg-status-error-surface font-label-md text-label-md px-space-lg py-space-md rounded-lg transition-colors flex items-center gap-space-xs shadow-sm cursor-pointer"
                        >
                          <span className="material-symbols-outlined text-[18px]">
                            forward
                          </span>
                          Flag for Regional Officer Review
                        </button>
                        <button
                          onClick={handleSubmitVerdict}
                          className="bg-primary hover:bg-navy-deep text-on-primary font-label-md text-label-md px-space-xl py-space-md rounded-lg transition-colors shadow-sm flex items-center gap-space-xs cursor-pointer"
                        >
                          <span className="material-symbols-outlined text-[18px]">
                            task_alt
                          </span>
                          Submit Review Decision &amp; Create Immutable Audit Record
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            {/* SECTION 4: SYSTEM-WIDE INTAKE VS CAPACITY BREACH MONITORING TABLE */}
            <section className="bg-surface-card rounded-xl p-space-xl shadow-sm border border-border-subtle flex flex-col gap-space-lg">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-space-md border-b border-border-subtle pb-space-lg">
                <div>
                  <div className="flex items-center gap-space-sm">
                    <h2 className="font-headline-lg text-headline-lg text-primary font-bold">
                      System-wide Approved Intake vs Capacity Breach Registry
                    </h2>
                    <span className="font-code-sm text-code-sm bg-status-error text-on-error px-space-xs py-space-2xs rounded font-bold uppercase">
                      142 Flagged
                    </span>
                  </div>
                  <p className="font-body-sm text-body-sm text-on-surface-variant mt-space-2xs">
                    Institutions exceeding statutory seat thresholds authorized under AICTE Approval Process Handbook (APH 2025-26)
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

              {/* Audit Grid with generous row spacing */}
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-surface-canvas border-b border-border-strong text-outline">
                      <th className="px-space-md py-space-md font-label-sm text-label-sm uppercase font-bold tracking-wider">
                        Permanent ID
                      </th>
                      <th className="px-space-md py-space-md font-label-sm text-label-sm uppercase font-bold tracking-wider">
                        Institution Name &amp; State
                      </th>
                      <th className="px-space-md py-space-md font-label-sm text-label-sm uppercase font-bold tracking-wider">
                        Affiliation
                      </th>
                      <th className="px-space-md py-space-md font-label-sm text-label-sm uppercase font-bold tracking-wider text-right">
                        Approved Cap
                      </th>
                      <th className="px-space-md py-space-md font-label-sm text-label-sm uppercase font-bold tracking-wider text-right">
                        Reported Intake
                      </th>
                      <th className="px-space-md py-space-md font-label-sm text-label-sm uppercase font-bold tracking-wider text-center">
                        Discrepancy (Δ)
                      </th>
                      <th className="px-space-md py-space-md font-label-sm text-label-sm uppercase font-bold tracking-wider">
                        Policy Breach Citation
                      </th>
                      <th className="px-space-md py-space-md font-label-sm text-label-sm uppercase font-bold tracking-wider text-right">
                        Statutory Action
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
                        <tr
                          key={row.pid}
                          className="hover:bg-surface-canvas transition-colors"
                        >
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
                          <td className="px-space-md py-space-md text-right font-code-sm text-code-sm font-bold text-status-error">
                            {row.intake}
                          </td>
                          <td className="px-space-md py-space-md text-center">
                            <span
                              className={`font-code-sm text-code-sm font-extrabold px-space-xs py-space-2xs rounded border ${
                                row.excess > 6
                                  ? 'text-status-error bg-status-error-surface border-status-error-border'
                                  : 'text-status-review bg-status-review-surface border-status-review-border'
                              }`}
                            >
                              {row.excessTag}
                            </span>
                          </td>
                          <td className="px-space-md py-space-md">
                            <div
                              className={`font-code-sm text-code-sm font-medium ${
                                row.excess > 6 ? 'text-status-error' : 'text-status-review'
                              }`}
                            >
                              {row.citation}
                            </div>
                            <div className="font-label-sm text-label-sm text-on-surface-variant">
                              {row.citationDesc}
                            </div>
                          </td>
                          <td className="px-space-md py-space-md text-right">
                            <button
                              onClick={() => handleBreachAction(row.pid, row.actionText)}
                              className={`px-space-md py-space-xs rounded-lg font-label-md text-label-md transition-colors shadow-sm cursor-pointer ${
                                row.actionStyle === 'error'
                                  ? 'bg-status-error text-on-error hover:bg-navy-deep'
                                  : 'bg-surface-subtle text-primary border border-border-strong hover:bg-surface-container'
                              }`}
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

              {/* Table Bottom Summary & Compliance Footnote */}
              <div className="bg-surface-subtle rounded-xl p-space-md border border-border-subtle flex flex-col sm:flex-row items-center justify-between gap-space-sm">
                <div className="flex items-center gap-space-xs font-code-sm text-code-sm text-on-surface-variant">
                  <span className="material-symbols-outlined text-status-error text-[18px]">
                    verified_user
                  </span>
                  <span>
                    Automatic penal interest calculator enabled for unregularized seats past 31 August 2025 cutoff.
                  </span>
                </div>
                <div className="flex items-center gap-space-sm">
                  <span className="font-label-sm text-label-sm text-outline">
                    Viewing 1-{filteredBreaches.length} of 142 Infractions
                  </span>
                  <div className="inline-flex rounded-md shadow-sm">
                    <button
                      onClick={() => showToast('Previous page')}
                      className="bg-surface-card border border-border-strong px-space-sm py-space-2xs text-primary font-label-sm text-label-sm rounded-l hover:bg-surface-subtle cursor-pointer"
                    >
                      Prev
                    </button>
                    <button
                      onClick={() => showToast('Next page')}
                      className="bg-surface-card border-t border-b border-r border-border-strong px-space-sm py-space-2xs text-primary font-label-sm text-label-sm rounded-r hover:bg-surface-subtle cursor-pointer"
                    >
                      Next
                    </button>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
};

export default AicteCentralReviewPage;
