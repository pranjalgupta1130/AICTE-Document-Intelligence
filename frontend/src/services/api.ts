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
      if (errJson.message) {
        errorMessage = errJson.message;
      } else if (errJson.detail) {
        errorMessage = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore JSON parse error
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
        if (errJson.message) {
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

export const batchService = {
  /**
   * Upload CSV or XLSX student records to POST /api/v1/imports
   */
  async uploadImportFile(
    file: File,
    academicYear: string = '2026-2027',
    programmeId?: string
  ): Promise<BackendImportCommitResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('academic_year', academicYear);
    if (programmeId) {
      formData.append('programme_id', programmeId);
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
    offset: number = 0
  ): Promise<PaginatedFindings> {
    return apiFetch<PaginatedFindings>(
      `/api/v1/batches/${batchId}/findings?limit=${limit}&offset=${offset}`
    );
  },

  /**
   * List import batches for the current institution
   */
  async listBatches(limit: number = 50, offset: number = 0): Promise<{ items: any[]; total: number }> {
    return apiFetch<{ items: any[]; total: number }>(`/api/v1/batches?limit=${limit}&offset=${offset}`);
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
};
