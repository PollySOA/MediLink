export type UserRole = "doctor" | "patient"
export type ReportComplexity = "low" | "medium" | "high"

export interface User {
  id: string
  username: string
  full_name: string
  role: UserRole
}

export interface AuthState {
  user: User | null
  token: string | null
}

export interface FictionalPatient {
  id: string
  name: string
  dni: string
  age: number
  gender: "male" | "female" | "other"
  conditions: string[]
  specialty: string
  sample_report: string
  clinical_context: string
  assigned_doctor_id: string
}

export interface PatientSearchResponse {
  items: FictionalPatient[]
  total: number
  page: number
  page_size: number
}

export interface Prescription {
  id: string
  patient_id: string
  doctor_id: string
  doctor_name: string
  medication: string
  dosage: string
  frequency: string
  duration: string
  instructions: string
  warnings: string[]
  created_at: string
  humanized_instructions: string | null
}

export interface HumanizedReport {
  patient_summary: string
  complexity: ReportComplexity
  key_findings: string[]
  recommended_actions: string
  disclaimer: string
}

export interface FHIRDiagnosticReport {
  resource_type: string
  id: string
  status: string
  conclusion: string
  issued: string
}

export interface ProcessedReport {
  report_id: string
  original_text: string
  humanized: HumanizedReport
  fhir_resource: FHIRDiagnosticReport
  idonia_pdf_generated: boolean
  created_at: string
}

export interface IdoniaAccessResponse {
  status: "ok"
  file_id: string
  open_path: string
  resource: "report" | "study"
  magic_link_url?: string
  magic_link_base_url?: string
  magic_link_route?: string
  magic_link_route_urlsafe?: string
  magic_link_pin?: string | null
  password_control?: {
    algorithm?: string
    hash_algorithm?: string
    hash_applied?: boolean
    bundle_items?: {
      image_study?: string
      original_report?: string
      humanized_report?: string
    }
    lopdgdd?: string
  }
  created_at: string
}

export interface AvatarResponse {
  justificacion_seguridad: string
  respuesta_voz: string
}

export interface AvatarFeedbackResponse {
  status: "ok"
  message: string
  average_rating: number | null
  total_ratings: number
}

export interface AvatarFeedbackRequest {
  patient_id: string
  rating: number
  comment?: string | null
}

export interface AvatarFeedbackSummary {
  patient_id: string | null
  total_ratings: number
  average_rating: number | null
  ratings_breakdown: Record<string, number>
}

export interface AvatarMessage {
  role: "user" | "assistant"
  content: string
  timestamp: Date
}

export interface CreatePrescriptionForm {
  patient_id: string
  medication: string
  dosage: string
  frequency: string
  duration: string
  instructions: string
  warnings: string[]
}
