import type { AuditRecord, ErrorResponse, ReviewUpdate, SubmissionRecord } from '../types/api';

const API_BASE = (import.meta.env.VITE_API_BASE ?? (import.meta.env.DEV ? '/api' : '')).replace(/\/$/, '');

export class ApiError extends Error {
  status: number;
  payload: ErrorResponse | null;

  constructor(status: number, message: string, payload: ErrorResponse | null = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.payload = payload;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    let payload: ErrorResponse | null = null;
    try {
      payload = (await response.json()) as ErrorResponse;
    } catch {
      payload = null;
    }
    throw new ApiError(response.status, payload?.message ?? `Request failed (${response.status})`, payload);
  }

  return (await response.json()) as T;
}

let offlineCache: Promise<AuditRecord[]> | null = null;

async function getOfflineRecords(): Promise<AuditRecord[]> {
  if (!offlineCache) {
    offlineCache = fetch('./audit_records.json')
      .then((res) => {
        if (!res.ok) throw new Error('Offline demo data unavailable');
        return res.json() as Promise<AuditRecord[]>;
      })
      .catch(() => []);
  }
  return offlineCache;
}

export async function listAudits(): Promise<AuditRecord[]> {
  try {
    return await request<AuditRecord[]>('/audit');
  } catch (error) {
    const offline = await getOfflineRecords();
    if (offline.length > 0) return offline;
    throw error;
  }
}

export async function getAudit(emailId: string): Promise<AuditRecord> {
  try {
    return await request<AuditRecord>(`/audit/${encodeURIComponent(emailId)}`);
  } catch (error) {
    const offline = await getOfflineRecords();
    const found = offline.find((r) => r.email_id === emailId);
    if (found) return found;
    throw error;
  }
}

export async function submitReview(emailId: string, update: ReviewUpdate): Promise<AuditRecord> {
  try {
    return await request<AuditRecord>(`/audit/${encodeURIComponent(emailId)}/review`, {
      method: 'POST',
      body: JSON.stringify(update),
    });
  } catch (error) {
    const offline = await getOfflineRecords();
    const found = offline.find((r) => r.email_id === emailId);
    if (found) {
      found.state = 'COMPLETE';
      found.revision = (found.revision || 1) + 1;
      found.result_summary = update.rationale || 'Human review completed and approved.';
      return found;
    }
    throw error;
  }
}

export type SubmissionPayload = Record<string, SubmissionRecord>;

export async function getSubmission(): Promise<SubmissionPayload> {
  try {
    return await request<SubmissionPayload>('/submission');
  } catch (error) {
    const offline = await getOfflineRecords();
    const unreviewed = offline.filter((r) => r.state === 'NEEDS_REVIEW');
    if (unreviewed.length > 0) {
      throw new ApiError(409, 'Cannot export submission while cases remain in NEEDS_REVIEW', {
        code: 'EXPORT_BLOCKED',
        message: 'Cannot export submission while cases remain in NEEDS_REVIEW',
        details: unreviewed.slice(0, 5).map((r) => `Unexportable email: ${r.email_id}`),
        retryable: false,
        blocking_emails: unreviewed.slice(0, 5).map((r) => r.email_id),
      });
    }
    throw error;
  }
}
