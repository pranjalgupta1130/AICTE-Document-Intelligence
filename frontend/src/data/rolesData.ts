import { RoleData, RoleKey } from '../types/auth';

export const ROLE_DATASETS: Record<RoleKey, RoleData> = {
  admin: {
    key: 'admin',
    shortTitle: 'Inst. Admin',
    subtitle: 'Apex Institute',
    icon: 'account_balance',
    title: 'Institution Administrator',
    tag: 'Role Scope: Tier-1 Regulatory Node',
    tagClass: 'bg-primary-fixed text-on-primary-fixed',
    description:
      'Full authority to manage institution profile, execute verified bulk student ingestion, submit regulatory enrollment batches to AICTE central registry, and manage sanctioned program intakes.',
    email: 'apex_admin@apex.edu.in',
    pid: 'INST-001',
    pwd: 'DemoPassword@2026',
  },
  operator: {
    key: 'operator',
    shortTitle: 'Inst. Operator',
    subtitle: 'Apex Institute',
    icon: 'input',
    title: 'Institution Operator',
    tag: 'Role Scope: Academic Cell Operations',
    tagClass: 'bg-surface-container-high text-on-surface',
    description:
      'Operates CSV / XLSX parsing pipelines, column re-mapping utilities, syntax and format discrepancy resolution, and unvalidated draft student updates.',
    email: 'apex_operator@apex.edu.in',
    pid: 'INST-001',
    pwd: 'DemoPassword@2026',
  },
  reviewer: {
    key: 'reviewer',
    shortTitle: 'AICTE Admin',
    subtitle: 'National Council',
    icon: 'policy',
    title: 'AICTE Statutory Admin / Reviewer',
    tag: 'Role Scope: Directorate Oversight',
    tagClass: 'bg-status-review-surface text-status-review',
    description:
      'Council authority to detect cross-institution duplicate APAAR requests, inspect regional intake threshold overages, and issue formal gazette approvals.',
    email: 'aicte_admin@aicte.gov.in',
    pid: 'HQ-STATUTORY-DELHI',
    pwd: 'DemoPassword@2026',
  },
  verifier: {
    key: 'verifier',
    shortTitle: 'Bharat Admin',
    subtitle: 'Bharat Eng College',
    icon: 'quick_reference_all',
    title: 'Cross-Tenant College Admin',
    tag: 'Role Scope: INST-002 Boundary Isolation',
    tagClass: 'bg-surface-subtle text-on-surface-variant',
    description:
      'Institution Admin for secondary college (INST-002) demonstrating tenant data isolation and cross-institution candidate duplicate review.',
    email: 'bharat_admin@bharat.edu.in',
    pid: 'INST-002',
    pwd: 'DemoPassword@2026',
  },
  evaluator: {
    key: 'evaluator',
    shortTitle: 'Demo Admin',
    subtitle: 'National Scope',
    icon: 'developer_mode_tv',
    title: 'SIH-2026 Demo Evaluator',
    tag: 'Role Scope: Platform Sandbox Control',
    tagClass: 'bg-status-verified-surface text-status-verified',
    description:
      'SIH Evaluation Jury profile: Instant access to mock adapters, synthetic population resets, edge-case generation, and live duplicate injection tests.',
    email: 'demo_admin@apaar.gov.in',
    pid: 'SIH-EVAL-26263',
    pwd: 'DemoPassword@2026',
  },
};
