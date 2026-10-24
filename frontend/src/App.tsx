import React, { useState } from 'react';
import { LoginPage } from './pages/LoginPage';
import { AicteCentralReviewPage } from './pages/AicteCentralReviewPage';
import { StudentRecordCertificatePage } from './pages/StudentRecordCertificatePage';
import { InstitutionDashboardPage } from './pages/InstitutionDashboardPage';
import { BulkImportValidationPage } from './pages/BulkImportValidationPage';
import { DataQualityFindingsPage } from './pages/DataQualityFindingsPage';
import { AuditLogsReportsPage } from './pages/AuditLogsReportsPage';
import { AuthSession } from './types/auth';

export const App: React.FC = () => {
  const [session, setSession] = useState<AuthSession | null>(() => {
    try {
      const stored = localStorage.getItem('apaar_auth_session');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  const [currentTab, setCurrentTab] = useState<string>('aicte-review');
  const [selectedApaarId, setSelectedApaarId] = useState<string>('9082-4412-8821');

  const handleLoginSuccess = (newSession: AuthSession) => {
    setSession(newSession);
    try {
      localStorage.setItem('apaar_auth_session', JSON.stringify(newSession));
    } catch {
      // ignore
    }
  };

  const handleLogout = () => {
    setSession(null);
    setCurrentTab('aicte-review');
    try {
      localStorage.removeItem('apaar_auth_session');
    } catch {
      // ignore
    }
  };

  const handleSwitchTab = (tab: string, apaarId?: string) => {
    if (apaarId) {
      setSelectedApaarId(apaarId);
    }
    setCurrentTab(tab);
  };

  if (session) {
    if (currentTab === 'dashboard') {
      return (
        <InstitutionDashboardPage
          session={session}
          onLogout={handleLogout}
          onNavigateTab={handleSwitchTab}
        />
      );
    }

    if (currentTab === 'import') {
      return (
        <BulkImportValidationPage
          session={session}
          onLogout={handleLogout}
          onNavigateTab={handleSwitchTab}
        />
      );
    }

    if (currentTab === 'findings') {
      return (
        <DataQualityFindingsPage
          session={session}
          onLogout={handleLogout}
          onNavigateTab={handleSwitchTab}
        />
      );
    }

    if (currentTab === 'reports') {
      return (
        <AuditLogsReportsPage
          session={session}
          onLogout={handleLogout}
          onNavigateTab={handleSwitchTab}
        />
      );
    }

    if (currentTab === 'records') {
      return (
        <StudentRecordCertificatePage
          session={session}
          initialApaarId={selectedApaarId}
          onLogout={handleLogout}
          onNavigateTab={handleSwitchTab}
        />
      );
    }

    return (
      <AicteCentralReviewPage
        session={session}
        onLogout={handleLogout}
        onSwitchTab={handleSwitchTab}
      />
    );
  }

  return <LoginPage onLoginSuccess={handleLoginSuccess} />;
};

export default App;


