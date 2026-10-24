import { RoleData, RoleKey } from '../types/auth';

export const ROLE_DATASETS: Record<RoleKey, RoleData> = {
  admin: {
    key: 'admin',
    shortTitle: 'Inst. Admin',
    subtitle: 'Registrar / Dean',
    icon: 'account_balance',
    title: 'Institution Administrator',
    tag: 'Role Scope: Tier-1 Regulatory Node',
    tagClass: 'bg-primary-fixed text-on-primary-fixed',
    description:
      'Full authority to manage institution profile, execute verified bulk student ingestion, submit regulatory enrollment batches to AICTE central registry, and manage sanctioned program intakes.',
    email: 'admin@nitt.edu',
    pid: 'AICTE-1-49281',
    pwd: 'DemoAccess#2026',
  },
  operator: {
    key: 'operator',
    shortTitle: 'Inst. Operator',
    subtitle: 'Academic Cell',
    icon: 'input',
    title: 'Institution Operator',
    tag: 'Role Scope: Academic Cell Operations',
    tagClass: 'bg-surface-container-high text-on-surface',
    description:
      'Operates CSV / XLSX parsing pipelines, column re-mapping utilities, syntax and format discrepancy resolution, and unvalidated draft student updates.',
    email: 'operator@nitt.edu',
    pid: 'AICTE-1-49281',
    pwd: 'OperatorKey#2026',
  },
  reviewer: {
    key: 'reviewer',
    shortTitle: 'AICTE Admin',
    subtitle: 'Statutory Review',
    icon: 'policy',
    title: 'AICTE Statutory Admin / Reviewer',
    tag: 'Role Scope: Directorate Oversight',
    tagClass: 'bg-status-review-surface text-status-review',
    description:
      'Council authority to detect cross-institution duplicate APAAR requests, inspect regional intake threshold overages, and issue formal gazette approvals.',
    email: 'reviewer@aicte-india.org',
    pid: 'HQ-STATUTORY-DELHI',
    pwd: 'CouncilPass#2026',
  },
  verifier: {
    key: 'verifier',
    shortTitle: 'Ext. Verifier',
    subtitle: 'Employer / HigherEd',
    icon: 'quick_reference_all',
    title: 'External Academic Verifier',
    tag: 'Role Scope: Read-Only Audit Clearance',
    tagClass: 'bg-surface-subtle text-on-surface-variant',
    description:
      'Third-party credential verifier (Higher Ed Council / Vetted Employer) allowed single-record hash checking and cryptographic verification receipts.',
    email: 'verifier@portal.gov.in',
    pid: 'VERIFIER-REG-9810',
    pwd: 'PublicToken#2026',
  },
  evaluator: {
    key: 'evaluator',
    shortTitle: 'Demo Admin',
    subtitle: 'SIH Evaluator',
    icon: 'developer_mode_tv',
    title: 'SIH-2026 Demo Evaluator',
    tag: 'Role Scope: Platform Sandbox Control',
    tagClass: 'bg-status-verified-surface text-status-verified',
    description:
      'SIH Evaluation Jury profile: Instant access to mock adapters, synthetic population resets, edge-case generation, and live duplicate injection tests.',
    email: 'evaluator@sih2026.gov.in',
    pid: 'SIH-EVAL-26263',
    pwd: 'SihPrototype#2026',
  },
};
