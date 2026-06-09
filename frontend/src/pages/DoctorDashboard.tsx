import { useEffect, useState } from "react"
import { useAuth } from "../context/AuthContext"
import { api, formatApiError } from "../services/api"
import type { AvatarFeedbackSummary, FictionalPatient, ProcessedReport, CreatePrescriptionForm, Prescription } from "../types"

type Tab = "patients" | "report" | "prescribe"

interface DoctorDashboardProps {
  activeTab: Tab
  onTabChange: (tab: Tab) => void
}

export default function DoctorDashboard({ activeTab, onTabChange }: DoctorDashboardProps) {
  const { user, token } = useAuth()
  const [patients, setPatients] = useState<FictionalPatient[]>([])
  const [selected, setSelected] = useState<FictionalPatient | null>(null)
  const [reportText, setReportText] = useState("")
  const [specialty, setSpecialty] = useState("")
  const [processedReport, setProcessedReport] = useState<ProcessedReport | null>(null)
  const [reportLoading, setReportLoading] = useState(false)
  const [reportError, setReportError] = useState("")
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([])
  const [prescForm, setPrescForm] = useState<Partial<CreatePrescriptionForm>>({})
  const [prescLoading, setPrescLoading] = useState(false)
  const [prescSuccess, setPrescSuccess] = useState(false)
  const [avatarFeedback, setAvatarFeedback] = useState<AvatarFeedbackSummary | null>(null)
  const [searchTerm, setSearchTerm] = useState("")
  const [searchMeta, setSearchMeta] = useState<{ total: number; page: number; page_size: number } | null>(null)
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchError, setSearchError] = useState("")
  const [idoniaLink, setIdoniaLink] = useState<string | null>(null)
  const [idoniaLoading, setIdoniaLoading] = useState(false)
  const [idoniaError, setIdoniaError] = useState("")

  useEffect(() => {
    if (user) {
      void reloadMyPatients()
    }
  }, [user, token])

  async function reloadMyPatients() {
    try {
      const data = await api.getDoctorPatients(token ?? undefined)
      setPatients(data)
      setSearchMeta(null)
      setSearchError("")
    } catch (e: unknown) {
      setSearchError(formatApiError(e, "No se pudieron cargar tus pacientes"))
    }
  }

  async function handleSearchPatients() {
    setSearchError("")
    if (!searchTerm.trim()) {
      await reloadMyPatients()
      return
    }

    setSearchLoading(true)
    try {
      const isLikelyDni = /\d/.test(searchTerm)
      const result = await api.searchPatients(
        {
          name: isLikelyDni ? undefined : searchTerm.trim(),
          dni: isLikelyDni ? searchTerm.trim() : undefined,
          page: 1,
          page_size: 10,
        },
        token ?? undefined,
      )
      setPatients(result.items)
      setSearchMeta({ total: result.total, page: result.page, page_size: result.page_size })
    } catch (e: unknown) {
      setSearchError(formatApiError(e, "No se pudo realizar la busqueda"))
    } finally {
      setSearchLoading(false)
    }
  }

  function selectPatient(p: FictionalPatient) {
    setSelected(p)
    setReportText(p.sample_report)
    setSpecialty(p.specialty)
    setProcessedReport(null)
    setReportError("")
    setPrescSuccess(false)
    setAvatarFeedback(null)
    setIdoniaLink(null)
    setIdoniaError("")
    api.getPatientPrescriptions(p.id, token ?? undefined).then(setPrescriptions)
    api
      .getAvatarFeedbackSummary(p.id, token ?? undefined)
      .then(setAvatarFeedback)
      .catch((e: unknown) => {
        setAvatarFeedback(null)
        setSearchError(formatApiError(e, "No se pudieron cargar las valoraciones del asistente"))
      })
  }

  function handleQuickClinicalAction(p: FictionalPatient) {
    selectPatient(p)
    onTabChange("report")
  }

  async function handleCreateIdoniaLink() {
    if (!selected) return
    setIdoniaLoading(true)
    setIdoniaError("")
    try {
      const response = await api.createIdoniaAccess(selected.id, "report", token ?? undefined)
      setIdoniaLink(response.magic_link_url ?? response.open_path)
    } catch (e: unknown) {
      setIdoniaError(formatApiError(e, "No se pudo generar acceso de Idonia"))
    } finally {
      setIdoniaLoading(false)
    }
  }

  async function handleProcessReport() {
    if (!selected || !reportText) return
    setReportLoading(true)
    setReportError("")
    try {
      const r = await api.processReport({ dictation_report: reportText, patient_id: selected.id, specialty }, token ?? undefined)
      setProcessedReport(r)
    } catch (e: unknown) {
      setReportError(formatApiError(e, "Error procesando el informe"))
    } finally {
      setReportLoading(false)
    }
  }

  async function handlePrescribe() {
    if (!selected || !prescForm.medication) return
    setPrescLoading(true)
    try {
      const rx = await api.createPrescription({ ...(prescForm as CreatePrescriptionForm), patient_id: selected.id }, token ?? undefined)
      setPrescriptions(prev => [...prev, rx])
      setPrescSuccess(true)
      setPrescForm({})
    } finally {
      setPrescLoading(false)
    }
  }

  const tabs: { key: Tab; label: string; icon: string }[] = [
    { key: "patients", label: "Mis pacientes", icon: "👥" },
    { key: "report", label: "Procesar informe", icon: "📋" },
    { key: "prescribe", label: "Emitir receta", icon: "💊" },
  ]

  return (
    <div className="stack" style={{ gap: 0 }}>
      <div className="tab-strip">
        {tabs.map(t => (
          <button key={t.key} onClick={() => onTabChange(t.key)}
            className={`btn ${activeTab === t.key ? "btn-primary" : "btn-ghost"}`}>
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {activeTab === "patients" && (
        <div className="stack">
          <div className="card">
            <p className="card-head">Busqueda clinica</p>
            <div className="row" style={{ gap: 8, alignItems: "center" }}>
              <input
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                placeholder="Buscar por nombre o DNI"
                style={{ flex: 1 }}
              />
              <button className="btn btn-primary" onClick={handleSearchPatients} disabled={searchLoading}>
                {searchLoading ? "Buscando..." : "Buscar"}
              </button>
              <button className="btn btn-ghost" onClick={() => { setSearchTerm(""); void reloadMyPatients() }}>
                Limpiar
              </button>
            </div>
            {searchMeta && (
              <p className="patient-card-subtitle" style={{ marginTop: 8 }}>
                {searchMeta.total} resultado(s) · pagina {searchMeta.page} · tamano {searchMeta.page_size}
              </p>
            )}
            {searchError && <p className="error-msg" style={{ marginTop: 8 }}>{searchError}</p>}
          </div>

          {patients.map(p => (
            <div key={p.id} className="card patient-card" style={{ cursor: "pointer", border: selected?.id === p.id ? "2px solid var(--blue)" : undefined }}
              onClick={() => selectPatient(p)}>
              <div className="row" style={{ justifyContent: "space-between" }}>
                <div>
                  <p style={{ fontWeight: 600, fontSize: 15 }}>{p.name}</p>
                  <p className="patient-card-subtitle">{p.age} años · {p.specialty} · {p.clinical_context}</p>
                </div>
                <span className="badge badge-blue">{p.id}</span>
              </div>
              <div style={{ display: "flex", gap: 6, marginTop: 8, flexWrap: "wrap" }}>
                {p.conditions.map(c => <span key={c} className="badge badge-teal">{c}</span>)}
              </div>
              <div className="row" style={{ marginTop: 10 }}>
                <button className="btn btn-primary" onClick={(e) => { e.stopPropagation(); handleQuickClinicalAction(p) }}>
                  Accion clinica rapida
                </button>
              </div>
            </div>
          ))}
          {selected && avatarFeedback && (
            <div className="card">
              <p className="card-head">Valoración de Elena</p>
              <div className="row" style={{ justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <div>
                  <p style={{ fontSize: 14, fontWeight: 600 }}>{selected.name}</p>
                  <p className="patient-card-subtitle">Satisfacción del paciente con las explicaciones del asistente</p>
                </div>
                <span className="badge badge-teal">
                  {avatarFeedback.average_rating !== null ? `${avatarFeedback.average_rating.toFixed(1)}/5` : "Sin media"}
                </span>
              </div>
              <p style={{ fontSize: 13, color: "var(--text-2)", marginBottom: 10 }}>
                {avatarFeedback.total_ratings > 0
                  ? `${avatarFeedback.total_ratings} valoración${avatarFeedback.total_ratings === 1 ? "" : "es"} registrada${avatarFeedback.total_ratings === 1 ? "" : "s"}`
                  : "Todavía no hay valoraciones registradas para este paciente."}
              </p>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {[1, 2, 3, 4, 5].map(score => (
                  <span key={score} className="badge badge-blue">
                    {score}: {avatarFeedback.ratings_breakdown[String(score)] ?? 0}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === "report" && (
        <div className="stack">
          {!selected && <div className="alert-box alert-info">Selecciona un paciente en "Mis pacientes" primero.</div>}
          {selected && (
            <>
              <div className="card">
                <p className="card-head">Paciente: {selected.name}</p>
                <div className="stack">
                  <div>
                    <label>Informe médico</label>
                    <textarea rows={7} value={reportText} onChange={e => setReportText(e.target.value)} />
                  </div>
                  <div>
                    <label>Especialidad</label>
                    <input value={specialty} onChange={e => setSpecialty(e.target.value)} />
                  </div>
                  <div className="row">
                    <button className="btn btn-primary" onClick={handleProcessReport} disabled={reportLoading || !reportText}>
                      {reportLoading ? "Procesando con IA..." : "Procesar y humanizar"}
                    </button>
                    <button className="btn btn-ghost" onClick={handleCreateIdoniaLink} disabled={idoniaLoading}>
                      {idoniaLoading ? "Generando acceso Idonia..." : "Acceso Idonia en 1 clic"}
                    </button>
                    {processedReport && (
                      <button className="btn btn-ghost" onClick={() => {
                        const blob = new Blob([JSON.stringify(processedReport.fhir_resource, null, 2)], { type: "application/json" })
                        const a = document.createElement("a"); a.href = URL.createObjectURL(blob)
                        a.download = `fhir-${processedReport.report_id.slice(0,8)}.json`; a.click()
                      }}>Exportar FHIR</button>
                    )}
                  </div>
                  {reportError && <p className="error-msg">{reportError}</p>}
                  {idoniaError && <p className="error-msg">{idoniaError}</p>}
                  {idoniaLink && (
                    <div className="alert-box alert-success">
                      Acceso listo: <a href={idoniaLink} target="_blank" rel="noreferrer">Abrir recurso de Idonia</a>
                    </div>
                  )}
                </div>
              </div>

              {processedReport && (
                <>
                  <div className="card">
                    <p className="card-head">Informe para el paciente <span className={`badge badge-${processedReport.humanized.complexity}`} style={{ marginLeft: 8, textTransform: "none", fontWeight: 400 }}>
                      {processedReport.humanized.complexity === "low" ? "Complejidad baja" : processedReport.humanized.complexity === "medium" ? "Media" : "Alta"}
                    </span></p>
                    <p style={{ fontSize: 15, lineHeight: 1.75, marginBottom: 14 }}>{processedReport.humanized.patient_summary}</p>
                    {processedReport.humanized.key_findings.length > 0 && (
                      <ul style={{ paddingLeft: 18, marginBottom: 12 }}>
                        {processedReport.humanized.key_findings.map((f, i) => <li key={i} style={{ fontSize: 14, marginBottom: 4 }}>{f}</li>)}
                      </ul>
                    )}
                    <div className="alert-box alert-info">{processedReport.humanized.recommended_actions}</div>
                    <p style={{ fontSize: 12, color: "var(--text-3)", marginTop: 10, fontStyle: "italic" }}>{processedReport.humanized.disclaimer}</p>
                  </div>
                </>
              )}
            </>
          )}
        </div>
      )}

      {activeTab === "prescribe" && (
        <div className="stack">
          {!selected && <div className="alert-box alert-info">Selecciona un paciente en "Mis pacientes" primero.</div>}
          {selected && (
            <>
              <div className="card">
                <p className="card-head">Nueva receta para {selected.name}</p>
                <div className="grid-2">
                  <div><label>Medicamento</label><input value={prescForm.medication ?? ""} onChange={e => setPrescForm(p => ({ ...p, medication: e.target.value }))} placeholder="Ibuprofeno" /></div>
                  <div><label>Dosis</label><input value={prescForm.dosage ?? ""} onChange={e => setPrescForm(p => ({ ...p, dosage: e.target.value }))} placeholder="600mg" /></div>
                  <div><label>Frecuencia</label><input value={prescForm.frequency ?? ""} onChange={e => setPrescForm(p => ({ ...p, frequency: e.target.value }))} placeholder="Cada 8 horas" /></div>
                  <div><label>Duración</label><input value={prescForm.duration ?? ""} onChange={e => setPrescForm(p => ({ ...p, duration: e.target.value }))} placeholder="7 días" /></div>
                </div>
                <div style={{ marginTop: 12 }}>
                  <label>Instrucciones para el paciente</label>
                  <textarea rows={3} value={prescForm.instructions ?? ""} onChange={e => setPrescForm(p => ({ ...p, instructions: e.target.value }))} placeholder="Tomar con alimentos, reposo relativo..." />
                </div>
                <div style={{ marginTop: 12 }} className="row">
                  <button className="btn btn-primary" onClick={handlePrescribe} disabled={prescLoading || !prescForm.medication}>
                    {prescLoading ? "Emitiendo receta..." : "Emitir receta"}
                  </button>
                </div>
                {prescSuccess && <div className="alert-box alert-success" style={{ marginTop: 10 }}>Receta emitida y explicada al paciente en lenguaje claro.</div>}
              </div>

              {prescriptions.length > 0 && (
                <div className="card">
                  <p className="card-head">Recetas activas</p>
                  <div className="stack" style={{ gap: 10 }}>
                    {prescriptions.map(rx => (
                      <div key={rx.id} className="rx-card">
                        <div className="row" style={{ justifyContent: "space-between", marginBottom: 4 }}>
                          <span style={{ fontWeight: 600, fontSize: 14 }}>{rx.medication} {rx.dosage}</span>
                          <span className="badge badge-blue">{rx.id}</span>
                        </div>
                        <p style={{ fontSize: 13, color: "var(--text-2)" }}>{rx.frequency} · {rx.duration}</p>
                        {rx.humanized_instructions && (
                          <div className="alert-box alert-info" style={{ marginTop: 8, fontSize: 13 }}>
                            <strong>Versión paciente:</strong> {rx.humanized_instructions}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
