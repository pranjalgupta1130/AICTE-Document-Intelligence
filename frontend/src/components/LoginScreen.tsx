import React, { useState } from 'react';
import { RoleKey, AuthSession } from '../types/auth';
import { ROLE_DATASETS } from '../data/rolesData';
import { authService } from '../services/api';

interface LoginScreenProps {
  onLoginSuccess?: (session: AuthSession) => void;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({ onLoginSuccess }) => {
  const [activeRoleKey, setActiveRoleKey] = useState<RoleKey>('admin');
  const [username, setUsername] = useState(ROLE_DATASETS.admin.email);
  const [instCode, setInstCode] = useState(ROLE_DATASETS.admin.pid);
  const [password, setPassword] = useState(ROLE_DATASETS.admin.pwd);
  const [showPassword, setShowPassword] = useState(false);
  const [enableDigiLocker, setEnableDigiLocker] = useState(true);
  const [bindTerminal, setBindTerminal] = useState(false);

  // Submission / Loading states
  const [authStatus, setAuthStatus] = useState<'idle' | 'verifying' | 'authorized'>('idle');
  const [authorizedSession, setAuthorizedSession] = useState<AuthSession | null>(null);

  // Flash highlight effect on inputs when role changes
  const [isFlashing, setIsFlashing] = useState(false);

  // Modal states
  const [showForgotModal, setShowForgotModal] = useState(false);
  const [showSsoModal, setShowSsoModal] = useState(false);

  const activeRoleData = ROLE_DATASETS[activeRoleKey];

  const handleRoleSelect = (key: RoleKey) => {
    setActiveRoleKey(key);
    const role = ROLE_DATASETS[key];
    setUsername(role.email);
    setInstCode(role.pid);
    setPassword(role.pwd);

    setIsFlashing(true);
    setTimeout(() => {
      setIsFlashing(false);
    }, 350);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (authStatus !== 'idle') return;

    setAuthStatus('verifying');

    try {
      const session = await authService.login(
        {
          username,
          instCode,
          password,
          enableDigiLocker,
          bindHardwareTerminal: bindTerminal,
        },
        activeRoleKey
      );

      setAuthStatus('authorized');
      setAuthorizedSession(session);

      if (onLoginSuccess) {
        onLoginSuccess(session);
      }
    } catch (err) {
      console.error('Authentication error:', err);
      setAuthStatus('idle');
    }
  };

  const handleResetSessionModal = () => {
    setAuthStatus('idle');
    setAuthorizedSession(null);
  };

  return (
    <div className="tricolor-slant-bg font-body-md text-on-surface antialiased min-h-screen relative overflow-x-hidden selection:bg-primary-fixed selection:text-on-primary-fixed">

      <div className="relative z-10 w-full min-h-screen flex flex-col justify-between py-space-xl px-space-lg">
        {/* Top Header */}
        <header className="max-w-md sm:max-w-4xl w-full mx-auto flex items-center justify-between pb-space-lg">
          <div className="flex items-center gap-space-sm">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center text-on-primary font-headline-sm select-none shadow-sm">
              🏛️
            </div>
            <div className="flex flex-col">
              <span className="font-headline-sm text-headline-sm text-primary tracking-tight leading-none">
                APAAR
              </span>
              <span className="font-label-sm text-label-sm text-on-surface-variant uppercase mt-space-2xs leading-none">
                AICTE / MoE Sovereign Portal
              </span>
            </div>
          </div>
          <div className="flex items-center gap-space-xs text-status-verified font-label-sm text-label-sm px-space-sm py-space-2xs bg-status-verified-surface border border-status-verified-border rounded shadow-sm">
            <span className="material-symbols-outlined text-[14px]">verified</span>
            <span>ISO 27001</span>
          </div>
        </header>

        {/* Main Content */}
        <main className="w-full flex-1 flex items-center justify-center">
          <div className="flex flex-col w-full relative min-h-[calc(100vh-140px)] justify-center items-center py-space-xl">
            {/* Slanted Tricolor Ambient Glow */}
            <div className="absolute inset-0 pointer-events-none overflow-hidden -z-10">
              <div className="absolute -top-32 -left-32 w-[38rem] h-[38rem] rounded-full bg-[#FF9933]/15 blur-[120px] transform -rotate-12" />
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[46rem] h-[28rem] rounded-full bg-surface-container-lowest/70 blur-[90px]" />
              <div className="absolute -bottom-32 -right-32 w-[38rem] h-[38rem] rounded-full bg-[#138808]/14 blur-[130px] transform rotate-12" />
              <div className="absolute inset-0 bg-gradient-to-br from-[#FF9933]/[0.03] via-transparent to-[#138808]/[0.03]" />
            </div>

            <div className="w-full max-w-4xl mx-auto flex flex-col gap-space-lg">
              {/* Header Regulatory & Title Area */}
              <div className="flex flex-col items-center text-center">
                {/* Trust Mark & SIH Pill Tray */}
                <div className="flex flex-wrap items-center justify-center gap-space-xs mb-space-sm">
                  <span className="inline-flex items-center gap-space-xs px-space-sm py-space-2xs rounded bg-surface-card shadow-sm text-primary font-label-sm text-label-sm tracking-wide border border-border-subtle/50">
                    <span className="material-symbols-outlined text-[15px] text-secondary">
                      verified_user
                    </span>
                    SIH-2026 PROTOTYPE • SIH26263
                  </span>
                  <span className="text-on-surface-variant font-label-sm text-label-sm">•</span>
                  <span className="inline-flex items-center gap-space-xs px-space-sm py-space-2xs rounded bg-surface-card shadow-sm text-on-surface-variant font-label-sm text-label-sm border border-border-subtle/50">
                    <span>Ministry of Education</span>
                    <span className="text-outline-variant">/</span>
                    <span>Government of India</span>
                  </span>
                  <span className="inline-flex items-center gap-space-xs px-space-sm py-space-2xs rounded bg-status-verified-surface text-status-verified font-label-sm text-label-sm border border-status-verified-border/40">
                    <span className="w-1.5 h-1.5 rounded-full bg-status-verified animate-pulse" />
                    NeGD Grid Active
                  </span>
                </div>

                <h1 className="font-display-lg text-display-lg text-primary tracking-tight max-w-2xl">
                  Student Data Management &amp; Verification Platform
                </h1>
                <p className="font-body-md text-body-md text-on-surface-variant mt-space-2xs">
                  अखिल भारतीय तकनीकी शिक्षा परिषद | All India Council for Technical Education
                </p>
              </div>

              {/* Main Civic Modernism Authentication Card */}
              <div className="w-full bg-surface-card rounded-xl shadow-xl overflow-hidden border border-border-subtle/70">
                {/* Card Sub-header: Dynamic Role Switcher (Seeded Demo Matrix) */}
                <div className="bg-surface-subtle p-space-md sm:p-space-lg border-b border-border-subtle">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-space-xs mb-space-sm">
                    <div className="flex items-center gap-space-xs">
                      <span className="material-symbols-outlined text-secondary text-[18px]">
                        badge
                      </span>
                      <span className="font-label-md text-label-md uppercase tracking-wider text-on-surface-variant">
                        Target Operating Persona (Seeded Demo Switcher)
                      </span>
                    </div>
                    <span className="font-code-sm text-code-sm text-on-surface-variant">
                      Click role to pre-fill credentials
                    </span>
                  </div>

                  {/* Role Tabs Grid */}
                  <div
                    className="grid grid-cols-2 sm:grid-cols-5 gap-space-xs"
                    id="roleSelectorGroup"
                    role="tablist"
                    aria-label="Role Switcher"
                  >
                    {(Object.keys(ROLE_DATASETS) as RoleKey[]).map((key) => {
                      const role = ROLE_DATASETS[key];
                      const isSelected = activeRoleKey === key;
                      const isEvaluator = key === 'evaluator';

                      return (
                        <button
                          key={key}
                          id={`tab-${key}`}
                          type="button"
                          role="tab"
                          aria-selected={isSelected}
                          onClick={() => handleRoleSelect(key)}
                          className={`role-btn flex flex-col items-start p-space-sm rounded text-left transition-all duration-200 outline-none focus-visible:ring-2 focus-visible:ring-secondary ${
                            isEvaluator ? 'col-span-2 sm:col-span-1' : ''
                          } ${
                            isSelected
                              ? 'bg-primary text-on-primary shadow-sm scale-[1.01]'
                              : 'bg-surface-card hover:bg-surface-container-low text-on-surface border border-border-subtle/60'
                          }`}
                        >
                          <div className="flex items-center gap-space-2xs w-full">
                            <span
                              className={`material-symbols-outlined text-[16px] ${
                                isSelected ? 'text-on-primary' : 'text-secondary'
                              }`}
                            >
                              {role.icon}
                            </span>
                            <span className="font-title-md text-title-md truncate">
                              {role.shortTitle}
                            </span>
                          </div>
                          <span
                            className={`font-label-sm text-label-sm mt-space-2xs truncate w-full ${
                              isSelected ? 'opacity-80' : 'text-on-surface-variant'
                            }`}
                          >
                            {role.subtitle}
                          </span>
                        </button>
                      );
                    })}
                  </div>

                  {/* Role Scope Banner */}
                  <div
                    className="mt-space-md p-space-sm rounded bg-surface-card shadow-sm flex items-start gap-space-sm border border-border-subtle/70"
                    id="roleDescriptor"
                  >
                    <span className="material-symbols-outlined text-secondary text-[20px] mt-0.5 shrink-0">
                      info
                    </span>
                    <div className="flex flex-col min-w-0">
                      <div className="flex items-center gap-space-xs flex-wrap">
                        <span
                          className="font-headline-sm text-headline-sm text-primary"
                          id="roleTitleBadge"
                        >
                          {activeRoleData.title}
                        </span>
                        <span
                          className={`px-space-xs py-space-2xs rounded font-label-sm text-label-sm ${activeRoleData.tagClass}`}
                          id="roleTag"
                        >
                          {activeRoleData.tag}
                        </span>
                      </div>
                      <p
                        className="font-body-sm text-body-sm text-on-surface-variant mt-space-2xs leading-relaxed"
                        id="roleDescription"
                      >
                        {activeRoleData.description}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Authentication Form */}
                <form
                  className="p-space-lg sm:p-space-2xl flex flex-col gap-space-lg"
                  onSubmit={handleSubmit}
                  noValidate={false}
                >
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-space-md">
                    {/* Institutional Email / User ID */}
                    <div className="flex flex-col gap-space-xs">
                      <label
                        className="font-label-md text-label-md text-on-surface flex items-center justify-between"
                        htmlFor="userInput"
                      >
                        <span>Official Institutional Email / AICTE PID</span>
                        <span className="text-on-surface-variant font-label-sm text-label-sm">
                          Required
                        </span>
                      </label>
                      <div className="relative flex items-center">
                        <span className="material-symbols-outlined absolute left-space-md text-on-surface-variant text-[20px] pointer-events-none">
                          account_circle
                        </span>
                        <input
                          id="userInput"
                          name="username"
                          type="text"
                          required
                          value={username}
                          onChange={(e) => setUsername(e.target.value)}
                          placeholder="nodal.officer@domain.gov.in / PID"
                          className={`w-full pl-10 pr-space-md py-space-sm rounded font-body-md text-body-md text-on-surface focus:outline-none focus:bg-surface-card focus:ring-1 focus:ring-secondary shadow-sm transition-colors duration-200 border border-border-subtle ${
                            isFlashing ? 'bg-surface-container-high' : 'bg-surface-subtle'
                          }`}
                        />
                      </div>
                      <span className="font-label-sm text-label-sm text-on-surface-variant">
                        Valid institutional email affiliated with approved AICTE directory.
                      </span>
                    </div>

                    {/* Affiliation PID */}
                    <div className="flex flex-col gap-space-xs">
                      <label
                        className="font-label-md text-label-md text-on-surface flex items-center justify-between"
                        htmlFor="instIdInput"
                      >
                        <span>Institutional Affiliation PID / Nodal Code</span>
                        <span className="text-status-verified font-label-sm text-label-sm flex items-center gap-space-2xs">
                          <span className="material-symbols-outlined text-[13px]">
                            check_circle
                          </span>
                          AISHE Validated
                        </span>
                      </label>
                      <div className="relative flex items-center">
                        <span className="material-symbols-outlined absolute left-space-md text-on-surface-variant text-[20px] pointer-events-none">
                          domain
                        </span>
                        <input
                          id="instIdInput"
                          name="instCode"
                          type="text"
                          required
                          value={instCode}
                          onChange={(e) => setInstCode(e.target.value)}
                          placeholder="e.g. AICTE-1-XXXXXX"
                          className={`w-full pl-10 pr-space-md py-space-sm rounded font-code-sm text-code-sm text-on-surface tracking-wider uppercase focus:outline-none focus:bg-surface-card focus:ring-1 focus:ring-secondary shadow-sm transition-colors duration-200 border border-border-subtle ${
                            isFlashing ? 'bg-surface-container-high' : 'bg-surface-subtle'
                          }`}
                        />
                      </div>
                      <span className="font-label-sm text-label-sm text-on-surface-variant">
                        Permanent Institute ID assigned during council recognition.
                      </span>
                    </div>
                  </div>

                  {/* Password / Security Key */}
                  <div className="flex flex-col gap-space-xs">
                    <div className="flex items-center justify-between">
                      <label
                        className="font-label-md text-label-md text-on-surface"
                        htmlFor="passwordInput"
                      >
                        Password / Hardware Digital Security Token
                      </label>
                      <button
                        type="button"
                        onClick={() => setShowForgotModal(true)}
                        className="font-label-sm text-label-sm text-secondary hover:underline focus:outline-none"
                      >
                        Forgot Institutional Credentials?
                      </button>
                    </div>
                    <div className="relative flex items-center">
                      <span className="material-symbols-outlined absolute left-space-md text-on-surface-variant text-[20px] pointer-events-none">
                        lock
                      </span>
                      <input
                        id="passwordInput"
                        name="password"
                        type={showPassword ? 'text' : 'password'}
                        required
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className={`w-full pl-10 pr-12 py-space-sm rounded font-body-md text-body-md text-on-surface focus:outline-none focus:bg-surface-card focus:ring-1 focus:ring-secondary shadow-sm transition-colors duration-200 border border-border-subtle ${
                          isFlashing ? 'bg-surface-container-high' : 'bg-surface-subtle'
                        }`}
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        title={showPassword ? 'Hide password' : 'Show password'}
                        className="absolute right-space-md text-on-surface-variant hover:text-on-surface p-space-2xs transition-colors rounded focus:outline-none focus-visible:ring-1 focus-visible:ring-secondary"
                      >
                        <span className="material-symbols-outlined text-[20px]" id="pwdToggleIcon">
                          {showPassword ? 'visibility_off' : 'visibility'}
                        </span>
                      </button>
                    </div>
                  </div>

                  {/* Security Checks & Options */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-space-sm p-space-md bg-surface-subtle rounded border border-border-subtle/50">
                    <label className="flex items-center gap-space-sm cursor-pointer select-none">
                      <input
                        id="meripehchaanSSO"
                        type="checkbox"
                        checked={enableDigiLocker}
                        onChange={(e) => setEnableDigiLocker(e.target.checked)}
                        className="w-4 h-4 rounded text-primary focus:ring-secondary border-outline-variant"
                      />
                      <span className="font-body-sm text-body-sm text-on-surface">
                        Enable MeriPehchaan / DigiLocker Sovereign Federation
                      </span>
                    </label>

                    <label className="flex items-center gap-space-sm cursor-pointer select-none">
                      <input
                        id="terminalRemember"
                        type="checkbox"
                        checked={bindTerminal}
                        onChange={(e) => setBindTerminal(e.target.checked)}
                        className="w-4 h-4 rounded text-primary focus:ring-secondary border-outline-variant"
                      />
                      <span className="font-body-sm text-body-sm text-on-surface-variant">
                        Bind hardware terminal for 8 hrs
                      </span>
                    </label>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-space-md pt-space-xs">
                    <button
                      id="submitBtn"
                      type="submit"
                      disabled={authStatus !== 'idle'}
                      className={`flex-1 flex items-center justify-center gap-space-sm px-space-xl py-space-sm font-headline-sm text-headline-sm rounded shadow transition-all duration-200 active:scale-[0.99] disabled:cursor-not-allowed ${
                        authStatus === 'authorized'
                          ? 'bg-status-verified-surface text-status-verified border border-status-verified-border'
                          : authStatus === 'verifying'
                          ? 'bg-primary-container text-on-primary'
                          : 'bg-primary hover:bg-navy-deep text-on-primary'
                      }`}
                    >
                      {authStatus === 'verifying' && (
                        <>
                          <span className="material-symbols-outlined text-[20px] animate-spin">
                            refresh
                          </span>
                          <span>Verifying SHA-256 Token...</span>
                        </>
                      )}
                      {authStatus === 'authorized' && (
                        <>
                          <span className="material-symbols-outlined text-[20px] text-status-verified">
                            verified
                          </span>
                          <span>Session Authorized</span>
                        </>
                      )}
                      {authStatus === 'idle' && (
                        <>
                          <span className="material-symbols-outlined text-[20px]">login</span>
                          <span>Authenticate &amp; Enter Portal</span>
                        </>
                      )}
                    </button>

                    <button
                      type="button"
                      onClick={() => setShowSsoModal(true)}
                      className="flex items-center justify-center gap-space-sm px-space-lg py-space-sm bg-surface-card hover:bg-surface-subtle text-primary font-headline-sm text-headline-sm rounded shadow-sm transition-all border border-border-subtle active:scale-[0.99]"
                    >
                      <span className="material-symbols-outlined text-secondary text-[20px]">
                        shield
                      </span>
                      <span>Parichay / Jan Parichay (National SSO)</span>
                    </button>
                  </div>
                </form>
              </div>

              {/* Security, Regulatory & Audit Footer Strip */}
              <div className="flex flex-col gap-space-md">
                {/* Statutory Restrictive Notice Banner */}
                <div className="p-space-md rounded bg-surface-card shadow-sm flex items-start gap-space-sm border border-border-subtle/70">
                  <span className="material-symbols-outlined text-status-review text-[20px] mt-0.5 shrink-0">
                    gavel
                  </span>
                  <div className="flex flex-col gap-space-2xs text-left">
                    <div className="flex items-center gap-space-xs flex-wrap">
                      <span className="font-label-md text-label-md text-on-surface uppercase tracking-wider font-semibold">
                        Statutory Security Notice
                      </span>
                      <span className="font-code-sm text-code-sm text-on-surface-variant font-mono text-[11px] px-1.5 py-0.5 rounded bg-surface-subtle">
                        SEC 10(1) AICTE ACT 1987 &amp; NEP 2020 MANDATE
                      </span>
                    </div>
                    <p className="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">
                      Access is restricted strictly to authorized institutional nodal officers and
                      AICTE statutory reviewers. All access is cryptographically audited via SHA-256
                      session logging under National Critical Information Infrastructure Protection
                      Centre (NCIIPC) guidelines. Unauthorized attempts trigger automated IP
                      isolation.
                    </p>
                  </div>
                </div>

                {/* Real-time Implementation Brief Compliance Badges */}
                <div className="flex flex-wrap items-center justify-between gap-space-sm p-space-sm bg-surface-subtle rounded font-code-sm text-code-sm text-on-surface-variant border border-border-subtle/50">
                  <div className="flex items-center gap-space-xs">
                    <span className="w-2 h-2 rounded-full bg-status-verified" />
                    <span>
                      Mock APAAR Adapter:{' '}
                      <strong className="text-on-surface font-semibold">
                        Active (Synthetic Dataset v2.4)
                      </strong>
                    </span>
                  </div>
                  <div className="flex items-center gap-space-xs">
                    <span className="material-symbols-outlined text-[15px] text-secondary">
                      lock
                    </span>
                    <span>
                      Server-side RBAC:{' '}
                      <strong className="text-on-surface font-semibold">Strictly Enforced</strong>
                    </span>
                  </div>
                  <div className="flex items-center gap-space-xs">
                    <span className="material-symbols-outlined text-[15px] text-status-verified">
                      shield
                    </span>
                    <span>
                      Compliance:{' '}
                      <strong className="text-on-surface font-semibold">
                        Zero Aadhaar Storage Policy
                      </strong>
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>

        {/* Global Footer */}
        <footer className="max-w-md sm:max-w-4xl w-full mx-auto pt-space-lg text-center border-t border-border-subtle/40">
          <p className="font-label-sm text-label-sm text-on-surface-variant">
            Sovereign Academic Credentials System • National e-Governance Division (NeGD)
            <br />
            Helpline: 1800-111-954 • official.portal@aicte-india.org
          </p>
        </footer>
      </div>

      {/* MODAL 1: Forgot Institutional Credentials */}
      {showForgotModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-deep/60 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-lg bg-surface-card rounded-xl shadow-2xl border border-border-subtle overflow-hidden">
            <div className="bg-primary p-space-lg flex items-center justify-between text-on-primary">
              <div className="flex items-center gap-space-sm">
                <span className="material-symbols-outlined text-[24px]">vpn_key_alert</span>
                <h3 className="font-headline-md text-headline-md font-bold">
                  Institutional Credential Recovery
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowForgotModal(false)}
                className="text-on-primary/80 hover:text-on-primary p-1 rounded"
              >
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>
            <div className="p-space-xl flex flex-col gap-space-md">
              <div className="p-space-sm rounded bg-status-review-surface border border-status-review-border flex items-start gap-space-sm">
                <span className="material-symbols-outlined text-status-review text-[20px] mt-0.5">
                  warning
                </span>
                <p className="font-body-sm text-body-sm text-on-surface">
                  To maintain strict regulatory sovereign integrity under NCIIPC standards,
                  passwords cannot be reset via unverified self-service email links.
                </p>
              </div>

              <div className="flex flex-col gap-space-xs">
                <span className="font-label-md text-label-md font-semibold text-primary">
                  Official Verification Channels:
                </span>
                <ul className="space-y-2 text-body-sm text-on-surface-variant">
                  <li className="flex items-center gap-space-xs">
                    <span className="material-symbols-outlined text-secondary text-[16px]">
                      contact_support
                    </span>
                    <span>Contact your institution nodal officer or registrar.</span>
                  </li>
                  <li className="flex items-center gap-space-xs">
                    <span className="material-symbols-outlined text-secondary text-[16px]">
                      mail
                    </span>
                    <span>
                      Submit encrypted reset request to:{' '}
                      <strong className="text-on-surface font-mono">
                        official.portal@aicte-india.org
                      </strong>
                    </span>
                  </li>
                  <li className="flex items-center gap-space-xs">
                    <span className="material-symbols-outlined text-secondary text-[16px]">
                      call
                    </span>
                    <span>Toll-free National Academic Helpline: 1800-111-954</span>
                  </li>
                </ul>
              </div>

              <div className="pt-space-sm flex justify-end">
                <button
                  type="button"
                  onClick={() => setShowForgotModal(false)}
                  className="px-space-lg py-space-xs bg-primary text-on-primary rounded font-label-md text-label-md shadow hover:bg-navy-deep"
                >
                  Understood &amp; Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: Jan Parichay National SSO */}
      {showSsoModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-deep/60 backdrop-blur-sm">
          <div className="w-full max-w-lg bg-surface-card rounded-xl shadow-2xl border border-border-subtle overflow-hidden">
            <div className="bg-[#0b3b60] p-space-lg flex items-center justify-between text-on-primary">
              <div className="flex items-center gap-space-sm">
                <span className="material-symbols-outlined text-[24px]">verified_user</span>
                <h3 className="font-headline-md text-headline-md font-bold">
                  Jan Parichay National SSO Gateway
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowSsoModal(false)}
                className="text-on-primary/80 hover:text-on-primary p-1 rounded"
              >
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>
            <div className="p-space-xl flex flex-col gap-space-md text-left">
              <div className="flex items-center gap-space-sm p-space-sm rounded bg-surface-subtle border border-border-subtle">
                <div className="w-10 h-10 rounded bg-[#FF9933]/20 flex items-center justify-center text-xl">
                  🇮🇳
                </div>
                <div>
                  <div className="font-title-md text-title-md text-primary">
                    e-Pramaan MoE Sovereign Identity Connector
                  </div>
                  <div className="font-label-sm text-label-sm text-on-surface-variant">
                    National Single Sign-On (NSSO) v3.2 Federation
                  </div>
                </div>
              </div>

              <p className="font-body-sm text-body-sm text-on-surface-variant">
                You are connecting to the centralized Government of India authentication network.
                Please ensure you have your registered Aadhaar / Mobile number or DigiLocker
                credentials ready.
              </p>

              <div className="p-space-sm bg-status-verified-surface border border-status-verified-border rounded text-status-verified font-body-sm text-body-sm flex items-center gap-space-xs">
                <span className="material-symbols-outlined text-[18px]">lock</span>
                <span>SHA-256 mTLS TLS 1.3 End-to-End Encrypted Tunnel Ready</span>
              </div>

              <div className="pt-space-sm flex items-center justify-end gap-space-sm">
                <button
                  type="button"
                  onClick={() => setShowSsoModal(false)}
                  className="px-space-md py-space-xs bg-surface-subtle hover:bg-surface-container-high text-on-surface rounded font-label-md text-label-md"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowSsoModal(false);
                    // trigger login with verifier or evaluator as demo
                    handleRoleSelect('evaluator');
                  }}
                  className="px-space-lg py-space-xs bg-primary hover:bg-navy-deep text-on-primary rounded font-label-md text-label-md shadow flex items-center gap-space-xs"
                >
                  <span>Connect with Jan Parichay</span>
                  <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 3: Successful Authorization Dialog */}
      {authorizedSession && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-deep/60 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-lg bg-surface-card rounded-xl shadow-2xl border border-border-subtle overflow-hidden">
            <div className="bg-status-verified p-space-lg flex items-center justify-between text-on-primary">
              <div className="flex items-center gap-space-sm">
                <span className="material-symbols-outlined text-[26px]">task_alt</span>
                <div>
                  <h3 className="font-headline-md text-headline-md font-bold">
                    Institutional Authentication Successful
                  </h3>
                  <p className="font-label-sm text-label-sm text-white/80">
                    AICTE Central Registry Authorization Complete
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={handleResetSessionModal}
                className="text-on-primary/80 hover:text-on-primary p-1 rounded"
              >
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>

            <div className="p-space-xl flex flex-col gap-space-md">
              <div className="bg-surface-subtle rounded-lg p-space-md border border-border-subtle space-y-2.5">
                <div className="flex justify-between items-center text-sm">
                  <span className="text-on-surface-variant font-medium">Authenticated Persona:</span>
                  <span className="font-semibold text-primary">{authorizedSession.roleTitle}</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-on-surface-variant font-medium">Node ID:</span>
                  <span className="font-mono font-semibold text-secondary">
                    {authorizedSession.instCode}
                  </span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-on-surface-variant font-medium">Official Email:</span>
                  <span className="font-mono text-on-surface">{authorizedSession.userEmail}</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-on-surface-variant font-medium">Access Token:</span>
                  <span className="font-mono text-xs px-2 py-0.5 rounded bg-surface-card border border-border-subtle font-bold text-status-verified">
                    {authorizedSession.token}
                  </span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-on-surface-variant font-medium">Hardware Bound:</span>
                  <span className="font-semibold text-on-surface">
                    {authorizedSession.expiresIn}
                  </span>
                </div>
              </div>

              <div className="p-space-sm bg-status-verified-surface border border-status-verified-border rounded flex items-center gap-space-xs text-status-verified text-sm">
                <span className="material-symbols-outlined text-[18px]">verified</span>
                <span>Session signed with Sovereign NeGD Node Public Key.</span>
              </div>

              <div className="pt-space-sm flex items-center justify-end gap-space-sm">
                <button
                  type="button"
                  onClick={handleResetSessionModal}
                  className="px-space-md py-space-xs bg-surface-subtle hover:bg-surface-container-high text-on-surface rounded font-label-md text-label-md"
                >
                  Log Out / Reset
                </button>
                <button
                  type="button"
                  onClick={() => {
                    alert(
                      `Entering AICTE Regulatory Dashboard for [${authorizedSession.roleTitle}] (${authorizedSession.instCode})`
                    );
                    handleResetSessionModal();
                  }}
                  className="px-space-lg py-space-xs bg-primary hover:bg-navy-deep text-on-primary rounded font-label-md text-label-md shadow flex items-center gap-space-xs"
                >
                  <span>Proceed to Regulatory Dashboard</span>
                  <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LoginScreen;
