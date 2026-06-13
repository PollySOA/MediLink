import { useEffect, useState, useRef } from "react"
import { useAuth } from "../context/AuthContext"
import { api, formatApiError } from "../services/api"
import type { FictionalPatient, Prescription, AvatarMessage, ProcessedReport } from "../types"
import VoiceButton from "../components/VoiceButton"
import { useVoiceRecorder } from "../hooks/useVoiceRecorder"

type Tab = "myinfo" | "report" | "prescriptions" | "elena"

interface PatientDashboardProps {
  activeTab: Tab
  onTabChange: (tab: Tab) => void
}

export default function PatientDashboard({ activeTab, onTabChange }: PatientDashboardProps) {
  const { user, token } = useAuth()
  const [patient, setPatient] = useState<FictionalPatient | null>(null)
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([])
  const [report, setReport] = useState<ProcessedReport | null>(null)
  const [reportLoading, setReportLoading] = useState(false)
  const [messages, setMessages] = useState<AvatarMessage[]>([])
  const [input, setInput] = useState("")
  const [chatLoading, setChatLoading] = useState(false)
  const [feedbackRequested, setFeedbackRequested] = useState(false)
  const [feedbackLoading, setFeedbackLoading] = useState(false)
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null)
  const [selectedRating, setSelectedRating] = useState<number | null>(null)
  const [feedbackComment, setFeedbackComment] = useState("")
  const [uiError, setUiError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  function escapeRegExp(value: string): string {
    return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
  }

  function alignPatientName(text: string, patientName: string | undefined): string {
    if (!patientName) return text
    const normalizedPatientName = patientName.trim()
    if (!normalizedPatientName) return text

    const nameParts = normalizedPatientName.split(/\s+/).filter(Boolean)
    if (nameParts.length > 1) {
      const duplicatedSuffix = nameParts.slice(1).join(" ")
      const duplicateRegex = new RegExp(escapeRegExp(`${normalizedPatientName} ${duplicatedSuffix}`), "gi")
      if (duplicateRegex.test(text)) {
        return text.replace(duplicateRegex, normalizedPatientName)
      }
    }

    // Keep already-correct salutations intact and only expand the demo first name when needed.
    if (text.toLocaleLowerCase().includes(normalizedPatientName.toLocaleLowerCase())) return text
    return text.replace(/\bCarolina\b/gi, normalizedPatientName)
  }

  const voice = useVoiceRecorder({
    onTranscript: (text) => {
      sendMessage(text)
    },
  })

  useEffect(() => {
    if (!user) return
    api.getPatient(user.id, token ?? undefined).then(p => {
      setPatient(p)
      api.getOwnPatientPrescriptions(p.id, token ?? undefined).then(setPrescriptions)
      loadGreeting(p.id, p.name)
    })
  }, [user])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  async function loadGreeting(patientId: string, patientName?: string) {
    try {
      const res = await api.avatarGreeting(patientId, token ?? undefined)
      setInput("")
      setFeedbackRequested(false)
      setFeedbackLoading(false)
      setFeedbackMessage(null)
      setSelectedRating(null)
      setFeedbackComment("")
      const safeVoice = alignPatientName(res.respuesta_voz, patientName)
      setMessages([{
        role: "assistant",
        content: safeVoice,
        timestamp: new Date(),
      }])
      setUiError(null)
    } catch (e: unknown) {
      setUiError(formatApiError(e, "No se pudo cargar el saludo de Elena"))
    }
  }

  async function handleProcessReport() {
    if (!patient) return
    setReportLoading(true)
    try {
      const r = await api.processReport({ dictation_report: patient.sample_report, patient_id: patient.id, specialty: patient.specialty }, token ?? undefined)
      setReport(r)
      setUiError(null)
    } catch (e: unknown) {
      setUiError(formatApiError(e, "No se pudo generar tu informe"))
    } finally {
      setReportLoading(false)
    }
  }

  async function submitFeedback(rating: number) {
    if (!patient || feedbackLoading) return
    setFeedbackLoading(true)
    setSelectedRating(rating)
    try {
      const res = await api.submitAvatarFeedback(patient.id, rating, feedbackComment, token ?? undefined)
      setFeedbackRequested(false)
      setFeedbackMessage(res.message)
      setFeedbackComment("")
      setUiError(null)
    } catch (e: unknown) {
      setFeedbackMessage(formatApiError(e, "No se pudo guardar la valoracion"))
    } finally {
      setFeedbackLoading(false)
    }
  }

  async function sendMessage(text: string) {
    if (!patient || !text.trim()) return
    const userMsg: AvatarMessage = { role: "user", content: text, timestamp: new Date() }
    setMessages(prev => [...prev, userMsg])
    setInput("")
    setChatLoading(true)
    setFeedbackRequested(false)
    setFeedbackMessage(null)
    setFeedbackComment("")

    const history = messages.map(m => ({ role: m.role, content: m.content }))
    try {
      const res = await api.avatarChat(text, patient.id, history, token ?? undefined)
      const safeVoice = alignPatientName(res.respuesta_voz, patient.name)
      const shouldRequestFeedback = /valora|valorar|valoracion|1 a 5/i.test(safeVoice)
      setMessages(prev => [...prev, {
        role: "assistant",
        content: safeVoice,
        timestamp: new Date(),
      }])
      setFeedbackRequested(shouldRequestFeedback)
      setUiError(null)
    } catch (e: unknown) {
      setMessages(prev => [...prev, {
        role: "assistant",
        content: formatApiError(e, "Lo siento, ha habido un problema. Intentalo de nuevo."),
        timestamp: new Date(),
      }])
      setUiError(formatApiError(e, "No se pudo enviar el mensaje a Elena"))
    } finally {
      setChatLoading(false)
    }
  }

  const tabs: { key: Tab; label: string; icon: string }[] = [
    { key: "elena", label: "Hablar con Elena", icon: "👩‍⚕️" },
    { key: "report", label: "Mi informe", icon: "📋" },
    { key: "prescriptions", label: "Mis recetas", icon: "💊" },
    { key: "myinfo", label: "Mis datos", icon: "👤" },
  ]

  return (
    <div>
      <div className="tab-strip">
        {tabs.map(t => (
          <button key={t.key} onClick={() => onTabChange(t.key)}
            className={`btn ${activeTab === t.key ? "btn-teal" : "btn-ghost"}`}>
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {activeTab === "elena" && (
        <div className="avatar-wrap">
          {uiError && (
            <div className="alert-box alert-warn" style={{ marginBottom: 10 }}>
              {uiError}
            </div>
          )}
          <div className="avatar-header">
            <div className="avatar-face">
              👩‍⚕️
              <div className="avatar-online" />
            </div>
            <div className="avatar-info">
              <h3>Elena</h3>
              <p>Asistente orientativo · Caso guiado de {patient?.name ?? "paciente"} · Disponible ahora</p>
            </div>
            <div className="avatar-meta-pill">
              IA · Phi-3.5-mini
            </div>
          </div>

          <div className="chat-messages">
            {messages.map((m, i) => (
              <div key={i} className={`msg ${m.role}`}>
                {m.role === "assistant" && <div className="msg-avatar">👩‍⚕️</div>}
                <div>
                  <div className="msg-bubble">{m.content}</div>
                  <p className="msg-time">{m.timestamp.toLocaleTimeString("es", { hour: "2-digit", minute: "2-digit" })}</p>
                </div>
              </div>
            ))}
            {chatLoading && (
              <div className="msg assistant">
                <div className="msg-avatar">👩‍⚕️</div>
                <div className="msg-bubble" style={{ color: "var(--text-3)" }}>Elena está escribiendo...</div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <div className="chat-input-area">
            <textarea
              rows={2}
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Escribe tu pregunta a Elena..."
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(input) } }}
            />
            <button className="btn btn-teal" onClick={() => sendMessage(input)} disabled={chatLoading || !input.trim()} style={{ height: "fit-content", alignSelf: "flex-end" }}>
              Enviar
            </button>
          </div>
          {feedbackRequested && (
            <div className="avatar-feedback-box">
              <p className="avatar-feedback-title">¿Cómo valorarías la ayuda de Elena?</p>
              <textarea
                rows={2}
                value={feedbackComment}
                onChange={e => setFeedbackComment(e.target.value)}
                placeholder="Comentario opcional sobre la ayuda recibida"
                maxLength={500}
                style={{ marginBottom: 10 }}
              />
              <div className="avatar-feedback-actions">
                {[1, 2, 3, 4, 5].map(score => (
                  <button
                    key={score}
                    className={`btn btn-ghost btn-sm avatar-rating-btn ${selectedRating === score ? "is-selected" : ""}`}
                    onClick={() => submitFeedback(score)}
                    disabled={feedbackLoading}
                  >
                    {score}
                  </button>
                ))}
              </div>
            </div>
          )}
          {feedbackMessage && (
            <div className="alert-box alert-success" style={{ marginTop: 10 }}>
              <p>{feedbackMessage}</p>
            </div>
          )}
          <div className="chat-voice-area">
            <VoiceButton
              state={voice.state}
              isSupported={voice.isSupported}
              interimText={voice.interimText}
              isElenaThinking={chatLoading}
              onToggle={voice.toggle}
            />
            {voice.errorMsg && (
              <p className="voice-error" role="alert">{voice.errorMsg}</p>
            )}
          </div>
        </div>
      )}

      {activeTab === "report" && (
        <div className="stack">
          <div className="card">
            <p className="card-head">Tu informe médico</p>
            {patient && <p style={{ fontSize: 14, color: "var(--text-2)", marginBottom: 14 }}>{patient.clinical_context}</p>}
            {!report && (
              <button className="btn btn-primary" onClick={handleProcessReport} disabled={reportLoading}>
                {reportLoading ? "Generando resumen..." : "Ver mi informe explicado"}
              </button>
            )}
          </div>

          {report && (
            <>
              <div className="card">
                <div className="row" style={{ justifyContent: "space-between", marginBottom: 14 }}>
                  <p className="card-head" style={{ margin: 0 }}>Tu resumen</p>
                  <span className={`badge badge-${report.humanized.complexity}`}>
                    {report.humanized.complexity === "low" ? "Sin alarma" : report.humanized.complexity === "medium" ? "Seguimiento" : "Atención próxima"}
                  </span>
                </div>
                <p style={{ fontSize: 15, lineHeight: 1.8, marginBottom: 14 }}>{report.humanized.patient_summary}</p>
                {report.humanized.key_findings.length > 0 && (
                  <>
                    <p style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>Puntos principales:</p>
                    <ul style={{ paddingLeft: 18, marginBottom: 12 }}>
                      {report.humanized.key_findings.map((f, i) => <li key={i} style={{ fontSize: 14, marginBottom: 4 }}>{f}</li>)}
                    </ul>
                  </>
                )}
                <div className="alert-box alert-info">{report.humanized.recommended_actions}</div>
                <p style={{ fontSize: 12, color: "var(--text-3)", marginTop: 10, fontStyle: "italic" }}>{report.humanized.disclaimer}</p>
              </div>
              <div style={{ textAlign: "center" }}>
                <button className="btn btn-ghost btn-sm" onClick={() => onTabChange("elena")}>
                  ¿Tienes dudas? Pregúntale a Elena 👩‍⚕️
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {activeTab === "prescriptions" && (
        <div className="stack">
          {prescriptions.length === 0 && <div className="alert-box alert-info">No tienes recetas activas en este momento.</div>}
          {prescriptions.map(rx => (
            <div key={rx.id} className="card">
              <div className="row" style={{ justifyContent: "space-between", marginBottom: 12 }}>
                <div>
                  <p style={{ fontWeight: 700, fontSize: 16 }}>{rx.medication}</p>
                  <p style={{ fontSize: 13, color: "var(--text-2)" }}>Recetado por {rx.doctor_name} · {new Date(rx.created_at).toLocaleDateString("es")}</p>
                </div>
                <span className="badge badge-teal">{rx.dosage}</span>
              </div>
              <div className="grid-2" style={{ marginBottom: 12 }}>
                <div><p style={{ fontSize: 12, color: "var(--text-3)" }}>Frecuencia</p><p style={{ fontSize: 14, fontWeight: 500 }}>{rx.frequency}</p></div>
                <div><p style={{ fontSize: 12, color: "var(--text-3)" }}>Duración</p><p style={{ fontSize: 14, fontWeight: 500 }}>{rx.duration}</p></div>
              </div>
              {rx.humanized_instructions && (
                <div className="alert-box alert-success">
                  <strong>Lo que debes saber:</strong><br />{rx.humanized_instructions}
                </div>
              )}
              {rx.warnings.length > 0 && (
                <div className="alert-box alert-warn" style={{ marginTop: 8 }}>
                  <strong>Precauciones:</strong> {rx.warnings.join(" · ")}
                </div>
              )}
            </div>
          ))}
          {prescriptions.length > 0 && (
            <div style={{ textAlign: "center" }}>
              <button className="btn btn-ghost btn-sm" onClick={() => onTabChange("elena")}>
                ¿Tienes dudas sobre tu medicación? Pregúntale a Elena 👩‍⚕️
              </button>
            </div>
          )}
        </div>
      )}

      {activeTab === "myinfo" && patient && (
        <div className="card">
          <p className="card-head">Tu información</p>
          <div className="stack info-stack" style={{ gap: 8 }}>
            {[
              ["Nombre", patient.name],
              ["Edad", `${patient.age} años`],
              ["Especialidad", patient.specialty],
              ["Contexto clínico", patient.clinical_context],
            ].map(([k, v]) => (
              <div key={k} className="info-row">
                <span className="info-key">{k}</span>
                <span className="info-value">{v}</span>
              </div>
            ))}
            <div className="info-row info-row-block">
              <span className="info-key">Condiciones conocidas</span>
              <div className="info-badges">
                {patient.conditions.map(c => <span key={c} className="badge badge-teal">{c}</span>)}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
