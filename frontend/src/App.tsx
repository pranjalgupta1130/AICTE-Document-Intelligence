import React, { useState } from 'react';
import { LoginPage } from './pages/LoginPage';
import { AuthSession } from './types/auth';

export const App: React.FC = () => {
  const [session, setSession] = useState<AuthSession | null>(null);

  if (session) {
    return (
      <div className="min-h-screen bg-surface-canvas text-on-surface flex flex-col font-body-md">
        {/* Top Institutional Header */}
        <header className="bg-primary text-on-primary py-3 px-6 shadow-md flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl select-none">🏛️</span>
            <div>
              <div className="font-headline-sm text-sm sm:text-base font-bold tracking-tight">
                APAAR Sovereign Academic Grid
              </div>
              <div className="text-xs text-primary-fixed-dim uppercase tracking-wider">
                AICTE / MoE Verification Node
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="hidden sm:flex flex-col text-right">
              <span className="text-xs font-semibold">{session.roleTitle}</span>
              <span className="text-[11px] text-primary-fixed-dim font-mono">{session.instCode}</span>
            </div>
            <button
              onClick={() => setSession(null)}
              className="px-3 py-1.5 bg-surface-card/10 hover:bg-surface-card/20 text-white rounded text-xs font-medium border border-white/20 transition-all flex items-center gap-1.5"
            >
              <span className="material-symbols-outlined text-[16px]">logout</span>
              <span>Sign Out</span>
            </button>
          </div>
        </header>

        {/* Dashboard Placeholder Banner */}
        <main className="flex-1 max-w-5xl w-full mx-auto p-6 sm:p-10 flex flex-col gap-6">
          <div className="bg-surface-card rounded-xl p-6 sm:p-8 shadow-sm border border-border-subtle flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-status-verified-surface border border-status-verified-border text-status-verified text-xs font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-status-verified animate-ping" />
                Active Session Authenticated
              </div>
              <h2 className="font-headline-lg text-2xl font-bold text-primary">
                Welcome, {session.roleTitle}
              </h2>
              <p className="text-sm text-on-surface-variant font-mono">
                Institutional Node ID: <span className="font-bold text-secondary">{session.instCode}</span> | Email: {session.userEmail}
              </p>
            </div>
            <div className="text-right">
              <div className="text-xs text-on-surface-variant">Active Token</div>
              <div className="font-mono text-xs font-semibold text-status-verified bg-surface-subtle px-2 py-1 rounded border border-border-subtle">
                {session.token}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-surface-card p-6 rounded-xl shadow-sm border border-border-subtle flex flex-col gap-2">
              <span className="material-symbols-outlined text-secondary text-3xl">upload_file</span>
              <h3 className="font-title-md font-bold text-primary">Bulk Student Ingestion</h3>
              <p className="text-xs text-on-surface-variant">
                Upload CSV / XLSX files for APAAR generation and AISHE verification checks.
              </p>
            </div>
            <div className="bg-surface-card p-6 rounded-xl shadow-sm border border-border-subtle flex flex-col gap-2">
              <span className="material-symbols-outlined text-secondary text-3xl">rule_folder</span>
              <h3 className="font-title-md font-bold text-primary">Statutory Rule Engine</h3>
              <p className="text-xs text-on-surface-variant">
                AICTE Approval Process Handbook (APH) compliance checks &amp; cross-document reconciliation.
              </p>
            </div>
            <div className="bg-surface-card p-6 rounded-xl shadow-sm border border-border-subtle flex flex-col gap-2">
              <span className="material-symbols-outlined text-secondary text-3xl">policy</span>
              <h3 className="font-title-md font-bold text-primary">Audit &amp; Non-Forgery Trail</h3>
              <p className="text-xs text-on-surface-variant">
                Cryptographic zero-Aadhaar storage compliance and tamper-proof SHA-256 logs.
              </p>
            </div>
          </div>

          <div className="text-center pt-4">
            <button
              onClick={() => setSession(null)}
              className="text-xs text-secondary hover:underline flex items-center justify-center gap-1 mx-auto"
            >
              <span className="material-symbols-outlined text-[14px]">arrow_back</span>
              <span>Back to Sovereign Login Screen</span>
            </button>
          </div>
        </main>
      </div>
    );
  }

  return <LoginPage onLoginSuccess={(newSession) => setSession(newSession)} />;
};

export default App;
