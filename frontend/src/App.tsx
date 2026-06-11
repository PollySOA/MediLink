import { useState } from "react"
import { AuthProvider, useAuth } from "./context/AuthContext"
import LoginPage from "./pages/LoginPage"
import DoctorDashboard from "./pages/DoctorDashboard"
import PatientDashboard from "./pages/PatientDashboard"
import { api, formatApiError, resolveIdoniaOpenUrl } from "./services/api"
import "./app.css"

type DoctorTab = "patients" | "report" | "prescribe"
type PatientTab = "elena" | "report" | "prescriptions" | "myinfo"

function AppContent() {
  const { user, token, logout } = useAuth()
  const [doctorTab, setDoctorTab] = useState<DoctorTab>("patients")
  const [patientTab, setPatientTab] = useState<PatientTab>("elena")
  const [openingIdonia, setOpeningIdonia] = useState(false)
  const [idoniaError, setIdoniaError] = useState<string | null>(null)
  const [idoniaSuccess, setIdoniaSuccess] = useState<string | null>(null)

  if (!user) return <LoginPage />

  const activeUser = user

  const apiBase = import.meta.env.VITE_API_URL ?? "http://localhost:8000"

  const idoniaContextLabel = activeUser.role === "patient"
    ? `Caso actual: ${activeUser.full_name} · ${activeUser.id}`
    : "Idonia abre la carpeta del paciente seleccionado en el panel médico"

  const patientIdoniaSteps = [
    "1. Pulsa abrir informe o estudio.",
    "2. Se abrirá Idonia en otra pestaña.",
    "3. Copia el PIN que te mostramos aquí y escríbelo en Idonia.",
  ]

  async function handleOpenIdonia(resource: "report" | "study") {
    if (activeUser.role !== "patient") return

    try {
      setOpeningIdonia(true)
      setIdoniaError(null)
      setIdoniaSuccess(null)
      const access = await api.createIdoniaAccess(activeUser.id, resource, token ?? undefined)
      if (access.status === "ok") {
        const openUrl = resolveIdoniaOpenUrl(access, apiBase)
        window.open(openUrl, "_blank", "noopener,noreferrer")
        const baseMessage = resource === "study" ? "Estudio radiológico preparado en Idonia" : "Informe preparado en Idonia"
        setIdoniaSuccess(access.magic_link_pin ? `${baseMessage}. PIN: ${access.magic_link_pin}` : baseMessage)
      }
    } catch (error) {
      setIdoniaError(formatApiError(error, "No se pudo abrir Idonia"))
    } finally {
      setOpeningIdonia(false)
    }
  }

  const doctorNavItems: { key: DoctorTab; label: string }[] = [
    { key: "patients", label: "👥 Mis pacientes" },
    { key: "report", label: "📋 Informes" },
    { key: "prescribe", label: "💊 Recetas" },
  ]

  const patientNavItems: { key: PatientTab; label: string }[] = [
    { key: "elena", label: "👩‍⚕️ Elena (asistente orientativo)" },
    { key: "report", label: "📋 Mi informe" },
    { key: "prescriptions", label: "💊 Mis recetas" },
    { key: "myinfo", label: "👤 Mis datos" },
  ]

  return (
    <div className="app-layout">
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">
            <div className="brand-mark">
              <svg viewBox="0 0 16 16"><path d="M8 1a7 7 0 1 0 0 14A7 7 0 0 0 8 1zm1 4v2h2a1 1 0 1 1 0 2H9v2a1 1 0 1 1-2 0V9H5a1 1 0 1 1 0-2h2V5a1 1 0 0 1 2 0z"/></svg>
            </div>
            <span className="brand-name">Medi<span>Link</span></span>
          </div>
          <div className="topbar-right">
            <span className={`role-badge ${user.role}`}>
              {user.role === "doctor" ? "Médico" : "Paciente"}
            </span>
            <span className="user-name">{user.full_name}</span>
            <button className="btn btn-ghost btn-sm" onClick={logout}>Salir</button>
          </div>
        </div>
      </header>

      <div className="app-shell">
        <aside className="sidebar">
          <div className="nav-section">
            <p className="nav-label">{user.role === "doctor" ? "Panel médico" : "Mi salud"}</p>
            {user.role === "doctor" ? (
              <>
                {doctorNavItems.map(item => (
                  <button
                    key={item.key}
                    type="button"
                    className={`nav-item nav-icon ${doctorTab === item.key ? "active" : ""}`}
                    onClick={() => setDoctorTab(item.key)}
                  >
                    {item.label}
                  </button>
                ))}
              </>
            ) : (
              <>
                {patientNavItems.map(item => (
                  <button
                    key={item.key}
                    type="button"
                    className={`nav-item nav-icon ${patientTab === item.key ? "active" : ""}`}
                    onClick={() => setPatientTab(item.key)}
                  >
                    {item.label}
                  </button>
                ))}
              </>
            )}
          </div>
          {user.role === "patient" ? (
            <div className="nav-section" style={{ marginTop: 16 }}>
              <p className="nav-label">Idonia</p>
              <p className="patient-card-subtitle" style={{ marginBottom: 8 }}>{idoniaContextLabel}</p>
              <div className="alert-box alert-info" style={{ marginBottom: 10, lineHeight: 1.5 }}>
                {patientIdoniaSteps.map(step => <div key={step}>{step}</div>)}
              </div>
              <button
                type="button"
                className="nav-item nav-icon"
                onClick={() => handleOpenIdonia("report")}
                disabled={openingIdonia}
              >
                {openingIdonia ? "⏳ Preparando Idonia..." : "🔗 Abrir informe del paciente en Idonia"}
              </button>
              <button
                type="button"
                className="nav-item nav-icon"
                onClick={() => handleOpenIdonia("study")}
                disabled={openingIdonia}
              >
                {openingIdonia ? "⏳ Preparando Idonia..." : "🩻 Abrir estudio radiológico del paciente en Idonia"}
              </button>
              {idoniaError ? <p className="idonia-status idonia-status-error">{idoniaError}</p> : null}
              {idoniaSuccess ? <p className="idonia-status idonia-status-success">{idoniaSuccess}</p> : null}
            </div>
          ) : null}
        </aside>

        <main className="main-area">
          <div className="page-head">
            {user.role === "doctor" ? (
              <>
                <h1 className="page-title">Panel médico</h1>
                <p className="page-sub">Gestiona informes, recetas y pacientes asignados</p>
              </>
            ) : (
              <>
                <h1 className="page-title">Modo paciente</h1>
                <p className="page-sub">Demo clínica con Elena y explicaciones médicas en lenguaje claro</p>
              </>
            )}
          </div>
          <div className="card" style={{ marginBottom: 16 }}>
            <p className="card-head">Contexto Idonia</p>
            <p className="patient-card-subtitle" style={{ lineHeight: 1.6 }}>{idoniaContextLabel}</p>
            {user.role === "patient" && (
              <p className="patient-card-subtitle" style={{ marginTop: 8, lineHeight: 1.6 }}>
                Usa el PIN que devuelve la misma acción de Idonia para este caso. No reutilices el PIN de otro paciente.
              </p>
            )}
          </div>
          {user.role === "doctor" ? (
            <DoctorDashboard activeTab={doctorTab} onTabChange={setDoctorTab} />
          ) : (
            <PatientDashboard activeTab={patientTab} onTabChange={setPatientTab} />
          )}
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}
