import { AuthCredentials, AuthSession, RoleKey } from '../types/auth';
import { ROLE_DATASETS } from '../data/rolesData';

const SESSION_KEY = 'apaar_auth_session';

export interface BackendUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  institution_id: string | null;
  institution_name: string | null;
  is_active: boolean;
}

export interface BackendTokenResponse {
  access_token: string;
  token_type: string;
  expires_in_seconds: number;
  user: BackendUser;
}

export interface BackendImportPreviewResponse {
  filename: string;
  file_type: string;
  detected_columns: string[];
  suggested_mapping: Record<string, string>;
  total_preview_rows: number;
  sample_rows: Record<string, any>[];
  structural_errors: string[];
  is_valid_structure: boolean;
}

export interface BackendRowError {
  row_number: number;
  field?: string | null;
  value?: string | null;
  message: string;
}

export interface BackendImportCommitResponse {
  batch_id: string;
  institution_id: string;
  source_filename: string;
  academic_year: string;
  version: number;
  status: string;
  total_rows: number;
  valid_rows: number;
  error_rows: number;
  warning_rows: number;
  row_errors: BackendRowError[];
  errors?: BackendRowError[];
}

export interface BackendValidationSummary {
  total_records: number;
  valid_records: number;
  error_count: number;
  warning_count: number;
  info_count: number;
  intake_exceeded_count: number;
  duplicate_candidate_count: number;
}

export interface BackendIntakeReconciliation {
  programme_id: string;
  programme_name: string;
  academic_year: string;
  regular_approved: number;
  regular_enrolled: number;
  regular_exceeded: number;
  supernumerary_approved: number;
  supernumerary_enrolled: number;
  supernumerary_exceeded: number;
  total_approved: number;
  total_enrolled: number;
  total_exceeded: number;
  status: string;
}

export interface BackendValidationResponse {
  batch_id: string;
  institution_id: string;
  status: string;
  validation_summary: BackendValidationSummary;
  intake_reconciliation: BackendIntakeReconciliation[];
  findings_count: number;
  message: string;
}

export interface BackendFinding {
  id: string;
  batch_id: string;
  record_id?: string | null;
  row_number?: number | null;
  field_name?: string | null;
  rule_code: string;
  severity: 'BLOCKING_ERROR' | 'WARNING' | 'INFO';
  message: string;
  expected_value?: string | null;
  actual_value?: string | null;
  suggested_action?: string | null;
  status: 'OPEN' | 'RESOLVED' | 'DISMISSED';
  created_at: string;
}

export interface PaginatedFindings {
  items: BackendFinding[];
  total: number;
}

/**
 * Base API fetch helper that attaches the Bearer token and handles error envelopes
 */
async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const session = authService.getCurrentSession();
  const headers = new Headers(options.headers || {});

  if (session?.token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${session.token}`);
  }

  const response = await fetch(endpoint, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
    try {
      const errJson = await response.json();
      if (errJson.error && typeof errJson.error === 'object') {
        const errObj = errJson.error;
        if (errObj.message) {
          errorMessage = errObj.message;
          if (errObj.details) {
            const detailStr = Array.isArray(errObj.details)
              ? errObj.details.map((d: any) => (typeof d === 'string' ? d : JSON.stringify(d))).join('; ')
              : typeof errObj.details === 'string'
              ? errObj.details
              : JSON.stringify(errObj.details);
            errorMessage = `${errorMessage} (${detailStr})`;
          }
        }
      } else if (errJson.message) {
        errorMessage = errJson.message;
      } else if (errJson.detail) {
        if (Array.isArray(errJson.detail)) {
          errorMessage = errJson.detail.map((d: any) => d.msg || JSON.stringify(d)).join('; ');
        } else if (typeof errJson.detail === 'string') {
          errorMessage = errJson.detail;
        } else {
          errorMessage = JSON.stringify(errJson.detail);
        }
      }
    } catch {
      // ignore JSON parse error for non-JSON error payloads
    }

    if (response.status === 401) {
      authService.logout();
    }
    throw new Error(errorMessage);
  }

  return response.json() as Promise<T>;
}

export const authService = {
  /**
   * Authenticate nodal officer credentials against backend /api/v1/auth/login
   */
  async login(credentials: AuthCredentials, activeRole: RoleKey): Promise<AuthSession> {
    const response = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email: credentials.username.trim(),
        password: credentials.password,
      }),
    });

    if (!response.ok) {
      let msg = 'Authentication failed. Please verify credentials.';
      try {
        const errJson = await response.json();
        if (errJson.error?.message) {
          msg = errJson.error.message;
        } else if (errJson.message) {
          msg = errJson.message;
        } else if (errJson.detail) {
          msg = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
        }
      } catch {
        // fallback msg
      }
      throw new Error(msg);
    }

    const data = (await response.json()) as BackendTokenResponse;
    const roleInfo = ROLE_DATASETS[activeRole];

    const session: AuthSession = {
      token: data.access_token,
      role: activeRole,
      roleTitle: data.user.role || roleInfo.title,
      instCode: data.user.institution_id || credentials.instCode,
      userEmail: data.user.email,
      timestamp: new Date().toISOString(),
      expiresIn: `${Math.round(data.expires_in_seconds / 3600)} hours`,
    };

    localStorage.setItem(SESSION_KEY, JSON.stringify(session));
    return session;
  },

  /**
   * Get currently authenticated user profile from /api/v1/auth/me
   */
  async getCurrentUserProfile(): Promise<BackendUser | null> {
    try {
      return await apiFetch<BackendUser>('/api/v1/auth/me');
    } catch {
      return null;
    }
  },

  /**
   * Get current active session from localStorage
   */
  getCurrentSession(): AuthSession | null {
    try {
      const saved = localStorage.getItem(SESSION_KEY);
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  },

  /**
   * Terminate active session
   */
  logout(): void {
    localStorage.removeItem(SESSION_KEY);
  },
};

export interface InstitutionItem {
  id: string;
  name: string;
  code: string;
  state: string;
  status: string;
}

export const institutionService = {
  /**
   * List accessible institutions
   */
  async listInstitutions(): Promise<{ items: InstitutionItem[]; total: number }> {
    return apiFetch<{ items: InstitutionItem[]; total: number }>('/api/v1/institutions');
  },
};

export interface BatchItem {
  id: string;
  institution_id: string;
  institution_name?: string | null;
  uploader_user_id?: string | null;
  uploader_email?: string | null;
  source_filename: string;
  academic_year: string;
  version: number;
  status: string;
  total_rows: number;
  valid_rows: number;
  error_rows: number;
  warning_rows: number;
  has_original_file: boolean;
  file_size_bytes?: number | null;
  created_at: string;
  updated_at: string;
}

export interface StudentRecordItem {
  id: string;
  batch_id: string;
  institution_id: string;
  programme_id: string;
  apaar_id?: string | null;
  institution_student_id: string;
  student_name?: string | null;
  academic_year: string;
  enrolment_status: string;
  seat_type: string;
  is_nri: boolean;
  is_oci: boolean;
  is_fn: boolean;
  source_row_number?: number | null;
  created_at: string;
}

export interface BatchHistoryEvent {
  id: string;
  action: string;
  actor_email: string;
  actor_role: string;
  outcome: string;
  details?: string | null;
  timestamp: string;
}

export const batchService = {
  /**
   * Upload CSV or XLSX student records to POST /api/v1/imports
   */
  async uploadImportFile(
    file: File,
    academicYear: string = '2026-2027',
    programmeId?: string,
    institutionId?: string
  ): Promise<BackendImportCommitResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('academic_year', academicYear);
    if (programmeId) {
      formData.append('programme_id', programmeId);
    }
    if (institutionId) {
      formData.append('institution_id', institutionId);
    }

    return apiFetch<BackendImportCommitResponse>('/api/v1/imports', {
      method: 'POST',
      body: formData,
    });
  },

  /**
   * Trigger deterministic validation engine on POST /api/v1/batches/{id}/validate
   */
  async validateBatch(batchId: string): Promise<BackendValidationResponse> {
    return apiFetch<BackendValidationResponse>(`/api/v1/batches/${batchId}/validate`, {
      method: 'POST',
    });
  },

  /**
   * Retrieve validation findings for a batch on GET /api/v1/batches/{id}/findings
   */
  async getBatchFindings(
    batchId: string,
    limit: number = 100,
    offset: number = 0,
    severity?: string
  ): Promise<PaginatedFindings> {
    const sevParam = severity ? `&severity=${severity}` : '';
    return apiFetch<PaginatedFindings>(
      `/api/v1/batches/${batchId}/findings?limit=${limit}&offset=${offset}${sevParam}`
    );
  },

  /**
   * List import batches with optional filtering, search, and pagination
   */
  async listBatches(params?: {
    institution_id?: string;
    academic_year?: string;
    status?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<{ items: BatchItem[]; total: number }> {
    const q = new URLSearchParams();
    if (params?.institution_id) q.set('institution_id', params.institution_id);
    if (params?.academic_year) q.set('academic_year', params.academic_year);
    if (params?.status) q.set('status', params.status);
    if (params?.search) q.set('search', params.search);
    if (params?.limit !== undefined) q.set('limit', String(params.limit));
    if (params?.offset !== undefined) q.set('offset', String(params.offset));

    const queryStr = q.toString();
    return apiFetch<{ items: BatchItem[]; total: number }>(`/api/v1/batches${queryStr ? `?${queryStr}` : ''}`);
  },

  /**
   * Retrieve single batch details on GET /api/v1/batches/{id}
   */
  async getBatch(batchId: string): Promise<BatchItem> {
    return apiFetch<BatchItem>(`/api/v1/batches/${batchId}`);
  },

  /**
   * Retrieve student records for a batch on GET /api/v1/batches/{id}/records
   */
  async getBatchRecords(
    batchId: string,
    params?: {
      search?: string;
      programme_id?: string;
      limit?: number;
      offset?: number;
    }
  ): Promise<{ items: StudentRecordItem[]; total: number }> {
    const q = new URLSearchParams();
    if (params?.search) q.set('search', params.search);
    if (params?.programme_id) q.set('programme_id', params.programme_id);
    if (params?.limit !== undefined) q.set('limit', String(params.limit));
    if (params?.offset !== undefined) q.set('offset', String(params.offset));

    const queryStr = q.toString();
    return apiFetch<{ items: StudentRecordItem[]; total: number }>(
      `/api/v1/batches/${batchId}/records${queryStr ? `?${queryStr}` : ''}`
    );
  },

  /**
   * Retrieve batch audit history on GET /api/v1/batches/{id}/history
   */
  async getBatchHistory(batchId: string): Promise<BatchHistoryEvent[]> {
    return apiFetch<BatchHistoryEvent[]>(`/api/v1/batches/${batchId}/history`);
  },

  /**
   * Download original file via browser trigger
   */
  async downloadOriginalFile(batchId: string, filename: string): Promise<void> {
    const session = authService.getCurrentSession();
    const headers = new Headers();
    if (session?.token) {
      headers.set('Authorization', `Bearer ${session.token}`);
    }

    const response = await fetch(`/api/v1/batches/${batchId}/download`, { headers });
    if (!response.ok) {
      let errMsg = 'Failed to download original document.';
      try {
        const errJson = await response.json();
        errMsg = errJson.error?.message || errJson.message || errJson.detail || errMsg;
      } catch {
        // fallback
      }
      throw new Error(errMsg);
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },

  /**
   * Export batch student records to CSV
   */
  async exportRecordsCsv(batchId: string, filename?: string): Promise<void> {
    const session = authService.getCurrentSession();
    const headers = new Headers();
    if (session?.token) {
      headers.set('Authorization', `Bearer ${session.token}`);
    }

    const response = await fetch(`/api/v1/batches/${batchId}/export/records`, { headers });
    if (!response.ok) {
      let errMsg = 'Failed to export records CSV.';
      try {
        const errJson = await response.json();
        errMsg = errJson.error?.message || errJson.message || errJson.detail || errMsg;
      } catch {
        // fallback
      }
      throw new Error(errMsg);
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename || `${batchId}_records.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },

  /**
   * Export validation findings to CSV
   */
  async exportFindingsCsv(batchId: string, filename?: string): Promise<void> {
    const session = authService.getCurrentSession();
    const headers = new Headers();
    if (session?.token) {
      headers.set('Authorization', `Bearer ${session.token}`);
    }

    const response = await fetch(`/api/v1/reports/export?batch_id=${batchId}&report_type=findings`, { headers });
    if (!response.ok) {
      let errMsg = 'Failed to export findings CSV.';
      try {
        const errJson = await response.json();
        errMsg = errJson.error?.message || errJson.message || errJson.detail || errMsg;
      } catch {
        // fallback
      }
      throw new Error(errMsg);
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename || `findings_${batchId}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },

  /**
   * Safely delete an unsubmitted batch and associated student records on DELETE /api/v1/batches/{id}
   */
  async deleteBatch(batchId: string): Promise<{
    success: boolean;
    message: string;
    batch_id: string;
    deleted_records: number;
    deleted_findings: number;
    deleted_matches: number;
  }> {
    return apiFetch<{
      success: boolean;
      message: string;
      batch_id: string;
      deleted_records: number;
      deleted_findings: number;
      deleted_matches: number;
    }>(`/api/v1/batches/${batchId}`, {
      method: 'DELETE',
    });
  },

  /**
   * Submit decision for a batch on POST /api/v1/batches/{batchId}/review
   */
  async reviewBatch(
    batchId: string,
    decision: 'UNDER_REVIEW' | 'ACCEPTED' | 'REJECTED' | 'NEEDS_CORRECTION',
    reason: string
  ): Promise<BatchReviewResponse> {
    return reviewService.reviewBatch(batchId, decision, reason);
  },
};

export interface CandidateStudentRecordDetail {
  id: string;
  student_name?: string | null;
  institution_student_id?: string | null;
  apaar_id?: string | null;
  academic_year?: string | null;
  seat_type?: string | null;
  enrolment_status?: string | null;
  programme_id?: string | null;
  programme?: {
    id: string;
    name: string;
  } | null;
}

export interface CandidateInstitutionDetail {
  id: string;
  name: string;
  code: string;
  state: string;
}

export interface MatchCandidateItem {
  id: string;
  record_a_id: string;
  record_b_id: string;
  institution_a_id: string;
  institution_b_id: string;
  matching_signal: string;
  confidence: number;
  status: 'CANDIDATE' | 'CONFIRMED_DUPLICATE' | 'DISMISSED';
  resolution_reason?: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  created_at?: string | null;
  record_a?: CandidateStudentRecordDetail | null;
  record_b?: CandidateStudentRecordDetail | null;
  institution_a?: CandidateInstitutionDetail | null;
  institution_b?: CandidateInstitutionDetail | null;
}

export interface BatchReviewResponse {
  batch_id: string;
  institution_id: string;
  previous_status: string;
  status: string;
  reviewed_by: string;
  reviewed_at: string;
  reason: string;
  message: string;
}

export const reviewService = {
  /**
   * List cross-institution duplicate match candidates on GET /api/v1/reviews/matches
   */
  async listMatchCandidates(params?: {
    status?: string;
    institution_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<{ items: MatchCandidateItem[]; total: number }> {
    const q = new URLSearchParams();
    if (params?.status) q.set('status', params.status);
    if (params?.institution_id) q.set('institution_id', params.institution_id);
    if (params?.limit !== undefined) q.set('limit', String(params.limit));
    if (params?.offset !== undefined) q.set('offset', String(params.offset));

    const queryStr = q.toString();
    return apiFetch<{ items: MatchCandidateItem[]; total: number }>(
      `/api/v1/reviews/matches${queryStr ? `?${queryStr}` : ''}`
    );
  },

  /**
   * Submit decision for a match candidate on POST /api/v1/reviews/matches/{matchId}
   */
  async reviewMatchCandidate(
    matchId: string,
    status: 'CONFIRMED_DUPLICATE' | 'DISMISSED',
    resolutionReason: string
  ): Promise<MatchCandidateItem> {
    return apiFetch<MatchCandidateItem>(`/api/v1/reviews/matches/${matchId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        status,
        resolution_reason: resolutionReason,
      }),
    });
  },

  /**
   * Submit decision for a batch on POST /api/v1/reviews/batches/{batchId}
   */
  async reviewBatch(
    batchId: string,
    decision: 'UNDER_REVIEW' | 'ACCEPTED' | 'REJECTED' | 'NEEDS_CORRECTION',
    reason: string
  ): Promise<BatchReviewResponse> {
    return apiFetch<BatchReviewResponse>(`/api/v1/reviews/batches/${batchId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        decision,
        reason,
      }),
    });
  },

  /**
   * Submit batch review decision via alias on POST /api/v1/batches/{batchId}/review
   */
  async reviewBatchDirect(
    batchId: string,
    decision: 'UNDER_REVIEW' | 'ACCEPTED' | 'REJECTED' | 'NEEDS_CORRECTION',
    reason: string
  ): Promise<BatchReviewResponse> {
    return apiFetch<BatchReviewResponse>(`/api/v1/batches/${batchId}/review`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        decision,
        reason,
      }),
    });
  },
};

export interface AicteDashboardMetrics {
  academic_year: string;
  total_institutions: number;
  total_submissions: number;
  total_batches: number;
  total_enrolled_students: number;
  total_approved_intake: number;
  aggregate_intake_utilization_pct: number;
  total_open_exceptions: number;
  total_candidate_duplicates: number;
  confirmed_duplicates_count: number;
  dismissed_duplicates_count: number;
  institution_breakdown: Array<{
    institution_id: string;
    institution_name: string;
    state: string;
    total_batches: number;
    latest_status?: string | null;
    total_enrolled: number;
    total_approved: number;
    intake_utilization_pct: number;
    open_exceptions_count: number;
  }>;
  recent_activity: Array<{
    timestamp: string;
    action: string;
    actor_email: string;
    actor_role: string;
    details?: string | null;
    outcome: string;
  }>;
}

export interface ProgrammeIntakeMetric {
  programme_id: string;
  programme_name: string;
  regular_approved: number;
  regular_enrolled: number;
  supernumerary_approved: number;
  supernumerary_enrolled: number;
  total_approved: number;
  total_enrolled: number;
  utilization_pct: number;
  status: 'WITHIN_LIMIT' | 'EXCEEDED';
  enrolled_count?: number;
  admitted_count?: number;
}

export interface SpecialQuotaMetric {
  category: string;
  label: string;
  enrolled: number;
  cap?: number | null;
}

export interface InstitutionDashboardMetrics {
  institution_id: string;
  institution_name: string;
  academic_year: string;
  total_batches: number;
  latest_batch_status?: string | null;
  total_student_records: number;
  valid_records_count: number;
  error_records_count: number;
  missing_apaar_count: number;
  duplicate_flags_count: number;
  intake_utilization_pct: number;
  total_approved_intake: number;
  total_enrolled_students: number;
  programme_intake_breakdown: ProgrammeIntakeMetric[];
  recent_batches: Array<{
    id: string;
    source_filename: string;
    academic_year: string;
    version: number;
    status: string;
    total_rows: number;
    valid_rows: number;
    error_rows: number;
    warning_rows: number;
    created_at: string;
  }>;
  recent_activity: Array<{
    timestamp: string;
    action: string;
    actor_email: string;
    actor_role: string;
    details?: string | null;
    outcome: string;
  }>;
  blocking_findings_count: number;
  warning_findings_count: number;
  available_academic_years: string[];
  special_quota_breakdown: SpecialQuotaMetric[];
  enrolled_finalized_count?: number;
  admitted_count?: number;
}

export interface ApprovedIntakeItem {
  id: string;
  institution_id: string;
  programme_id: string;
  programme_name?: string | null;
  academic_year: string;
  regular_intake: number;
  supernumerary_intake: number;
  total_approved_intake: number;
  supernumerary_policy?: string | null;
}

export const dashboardService = {
  /**
   * Get institution operational metrics on GET /api/v1/dashboard/institution
   */
  async getInstitutionMetrics(params?: {
    academic_year?: string;
    institution_id?: string;
  }): Promise<InstitutionDashboardMetrics> {
    const q = new URLSearchParams();
    if (params?.academic_year) q.set('academic_year', params.academic_year);
    if (params?.institution_id) q.set('institution_id', params.institution_id);

    const queryStr = q.toString();
    return apiFetch<InstitutionDashboardMetrics>(
      `/api/v1/dashboard/institution${queryStr ? `?${queryStr}` : ''}`
    );
  },

  /**
   * Get AICTE national analytics on GET /api/v1/dashboard/aicte
   */
  async getAicteMetrics(): Promise<AicteDashboardMetrics> {
    return apiFetch<AicteDashboardMetrics>('/api/v1/dashboard/aicte');
  },

  /**
   * Get approved intake records on GET /api/v1/intake
   */
  async getApprovedIntake(params?: {
    institution_id?: string;
    academic_year?: string;
    programme_id?: string;
  }): Promise<{ items: ApprovedIntakeItem[]; total: number }> {
    const q = new URLSearchParams();
    if (params?.institution_id) q.set('institution_id', params.institution_id);
    if (params?.academic_year) q.set('academic_year', params.academic_year);
    if (params?.programme_id) q.set('programme_id', params.programme_id);

    const queryStr = q.toString();
    return apiFetch<{ items: ApprovedIntakeItem[]; total: number }>(
      `/api/v1/intake${queryStr ? `?${queryStr}` : ''}`
    );
  },
};

export interface BackendAuditTrailEntry {
  timestamp: string;
  eventType: string;
  actor: string;
  actionDetails: string;
  complianceStatus: string;
  complianceBadgeClass?: string;
}

export interface VerificationResult {
  apaar_id: string;
  provider: string;
  outcome: 'MOCK_VERIFIED' | 'MOCK_NOT_VERIFIED' | 'MOCK_UNAVAILABLE' | 'NEEDS_REVIEW';
  is_official: boolean;
  reference_id: string;
  student_name?: string | null;
  institution_id?: string | null;
  message: string;
  details?: string | null;
  record_id?: string | null;
  institution_student_id?: string | null;
  institution_name?: string | null;
  institution_code?: string | null;
  programme_id?: string | null;
  programme_name?: string | null;
  academic_year?: string | null;
  enrolment_status?: string | null;
  seat_type?: string | null;
  audit_trail: BackendAuditTrailEntry[];
}

export interface CertificatePreview {
  is_synthetic_preview: boolean;
  disclaimer: string;
  institution_name: string;
  institution_code: string;
  student_name: string;
  institution_student_id: string;
  apaar_id: string;
  programme_name: string;
  academic_year: string;
  seat_type: string;
  enrolment_status: string;
  verification_reference: string;
}

export interface StudentSearchResult {
  id: string;
  institution_id: string;
  institution_name?: string | null;
  institution_code?: string | null;
  institution_student_id: string;
  student_name?: string | null;
  apaar_id?: string | null;
  academic_year: string;
  programme_id: string;
  programme_name?: string | null;
  enrolment_status: string;
  seat_type: string;
}

export interface StudentSearchResponse {
  items: StudentSearchResult[];
  total: number;
}

export const verificationService = {
  /**
   * Search student records with institution isolation and APAAR masking
   */
  async searchStudents(params?: {
    q?: string;
    academic_year?: string;
    limit?: number;
    offset?: number;
  }): Promise<StudentSearchResponse> {
    const q = new URLSearchParams();
    if (params?.q) q.set('q', params.q);
    if (params?.academic_year) q.set('academic_year', params.academic_year);
    if (params?.limit !== undefined) q.set('limit', String(params.limit));
    if (params?.offset !== undefined) q.set('offset', String(params.offset));

    const queryStr = q.toString();
    return apiFetch<StudentSearchResponse>(
      `/api/v1/verification/search${queryStr ? `?${queryStr}` : ''}`
    );
  },

  /**
   * Purpose-restricted single-record verification lookup
   */
  async verifyStudent(studentRef: string, simulateOutage = false): Promise<VerificationResult> {
    const query = simulateOutage ? '?simulate_outage=true' : '';
    return apiFetch<VerificationResult>(
      `/api/v1/verification/${encodeURIComponent(studentRef)}${query}`
    );
  },

  /**
   * Synthetic degree certificate preview
   */
  async getCertificatePreview(studentRef: string): Promise<CertificatePreview> {
    return apiFetch<CertificatePreview>(
      `/api/v1/verification/${encodeURIComponent(studentRef)}/certificate`
    );
  },
};

