import type {
  AvatarFeedbackRequest, FictionalPatient, Prescription, ProcessedReport,
  AvatarFeedbackResponse, AvatarFeedbackSummary, AvatarResponse, CreatePrescriptionForm, IdoniaAccessResponse, PatientSearchResponse, User
} from "../types"

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000"

type ApiErrorPayload = {
  code?: string
  message?: string
  detail?: string
  details?: unknown
  trace_id?: string
}

export class ApiError extends Error {
  code?: string
  details?: unknown
  traceId?: string
  status?: number

  constructor(message: string, options?: { code?: string; details?: unknown; traceId?: string; status?: number }) {
    super(message)
    this.name = "ApiError"
    this.code = options?.code
    this.details = options?.details
    this.traceId = options?.traceId
    this.status = options?.status
  }
}

function normalizeApiErrorPayload(err: unknown): ApiErrorPayload {
  if (!err || typeof err !== "object") return {}
  const record = err as Record<string, unknown>
  return {
    code: typeof record.code === "string" ? record.code : undefined,
    message: typeof record.message === "string" ? record.message : undefined,
    detail: typeof record.detail === "string" ? record.detail : undefined,
    details: record.details,
    trace_id: typeof record.trace_id === "string" ? record.trace_id : undefined,
  }
}

function toApiError(err: unknown, status: number): ApiError {
  const payload = normalizeApiErrorPayload(err)
  const message = payload.message ?? payload.detail ?? "Error desconocido"
  return new ApiError(message, {
    code: payload.code,
    details: payload.details,
    traceId: payload.trace_id,
    status,
  })
}

export function formatApiError(error: unknown, fallback = "Error desconocido"): string {
  if (error instanceof ApiError) {
    const traceChunk = error.traceId ? ` | trace_id: ${error.traceId}` : ""
    return `${error.message}${traceChunk}`
  }
  if (error instanceof Error) return error.message || fallback
  return fallback
}

async function req<T>(path: string, options?: RequestInit, token?: string | null): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" }
  if (token) headers["Authorization"] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, { headers, ...options })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw toApiError(err, res.status)
  }
  return res.json()
}

export const api = {
  login(username: string, password: string) {
    return req<{ access_token: string; user: User }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    })
  },

  demoAccounts() {
    return req<{ doctors: object[]; patients: object[] }>("/api/auth/demo-accounts")
  },

  getPatients(token?: string) {
    return req<FictionalPatient[]>("/api/patients/", undefined, token)
  },

  getPatient(id: string, token?: string) {
    return req<FictionalPatient>(`/api/patients/${id}`, undefined, token)
  },

  getPatientSummary(id: string, token?: string) {
    return req<{ patient: FictionalPatient; prescriptions_count: number; latest_prescription: Prescription | null }>(
      `/api/patients/${id}/summary`, undefined, token
    )
  },

  searchPatients(params: { name?: string; dni?: string; page?: number; page_size?: number }, token?: string) {
    const search = new URLSearchParams()
    if (params.name) search.set("name", params.name)
    if (params.dni) search.set("dni", params.dni)
    search.set("page", String(params.page ?? 1))
    search.set("page_size", String(params.page_size ?? 10))
    return req<PatientSearchResponse>(`/api/patients/search?${search.toString()}`, undefined, token)
  },

  getDoctorPatients(token?: string) {
    return req<FictionalPatient[]>(`/api/doctor/patients`, undefined, token)
  },

  createPrescription(form: CreatePrescriptionForm, token?: string) {
    return req<Prescription>(`/api/doctor/prescriptions`, {
      method: "POST",
      body: JSON.stringify(form),
    }, token)
  },

  getPatientPrescriptions(patientId: string, token?: string) {
    return req<Prescription[]>(`/api/doctor/prescriptions/${patientId}`, undefined, token)
  },

  processReport(body: { dictation_report: string; patient_id?: string; specialty?: string }, token?: string) {
    return req<ProcessedReport>("/api/reports/process", { method: "POST", body: JSON.stringify(body) }, token)
  },

  createIdoniaAccess(patientId: string, resource: "report" | "study", token?: string) {
    return req<IdoniaAccessResponse>(`/api/reports/patients/${patientId}/idonia-link?resource=${resource}`, {
      method: "POST",
    }, token)
  },

  avatarGreeting(patientId: string, token?: string) {
    return req<AvatarResponse>(
      `/api/avatar/greeting/${patientId}`, undefined, token
    )
  },

  avatarChat(message: string, patientId: string, history: { role: string; content: string }[], token?: string) {
    return req<AvatarResponse>("/api/avatar/chat", {
      method: "POST",
      body: JSON.stringify({
        message,
        patient_id: patientId,
        conversation_history: history,
      }),
    }, token)
  },

  submitAvatarFeedback(patientId: string, rating: number, comment?: string, token?: string) {
    const body: AvatarFeedbackRequest = { patient_id: patientId, rating, comment: comment?.trim() || undefined }
    return req<AvatarFeedbackResponse>("/api/avatar/feedback", {
      method: "POST",
      body: JSON.stringify(body),
    }, token)
  },

  getAvatarFeedbackSummary(patientId?: string, token?: string) {
    const suffix = patientId ? `?patient_id=${encodeURIComponent(patientId)}` : ""
    return req<AvatarFeedbackSummary>(`/api/avatar/feedback/summary${suffix}`, undefined, token)
  },

  downloadPDF(dictationReport: string, token?: string): Promise<Blob> {
    const headers: Record<string, string> = { "Content-Type": "application/json" }
    if (token) headers["Authorization"] = `Bearer ${token}`
    return fetch(`${BASE}/api/reports/process/pdf`, {
      method: "POST",
      headers,
      body: JSON.stringify({ dictation_report: dictationReport }),
    }).then(async r => {
      if (!r.ok) {
        const err = await r.json().catch(() => ({ detail: r.statusText }))
        throw toApiError(err, r.status)
      }
      return r.blob()
    })
  },
}
