import { useState } from "react"
import { api, formatApiError } from "../services/api"
import { useAuth } from "../context/AuthContext"
import idoniaLogo from "../assets/idonia-logo.svg"

export default function LoginPage() {
  const { login } = useAuth()
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError("")
    try {
      const res = await api.login(username, password)
      login(res.user, res.access_token)
    } catch (e: unknown) {
      setError(formatApiError(e, "Usuario o contrasena incorrectos"))
    } finally {
      setLoading(false)
    }
  }

  function fillDemo(u: string) {
    setUsername(u)
    setPassword("demo1234")
  }

  const doctors = [
    { label: "Dr. Carlos García (Traumatología)", u: "dr.garcia" },
    { label: "Dra. Ana López (Interna)", u: "dr.lopez" },
  ]
  
  const patients = [
    { label: "Carolina R. (paciente rodilla)", u: "alejandro.m" },
    { label: "Carmen R. (cardiología)", u: "carmen.r" },
    { label: "Rosa F. (neumología)", u: "rosa.f" },
    { label: "Miguel D. (cardiología)", u: "miguel.d" },
    { label: "Isabel M. (neurología)", u: "isabel.m" },
  ]

  return (
    <div className="login-screen">
      <div className="login-card">
        <div className="login-logo">
          <img src={idoniaLogo} alt="Idonia" className="login-idonia-logo" />
          <h1>Medi<span>Link</span></h1>
          <p>Interoperabilidad y Humanización Médica</p>
          <p style={{ fontSize: 11, color: "#9ca3af", marginTop: 2 }}>I Hackathon IABiomed · Reto Idonia</p>
        </div>

        <form onSubmit={handleLogin} className="stack" aria-label="Formulario de login">
          <div>
            <label htmlFor="username">Usuario</label>
            <input 
              id="username"
              value={username} 
              onChange={e => setUsername(e.target.value)} 
              placeholder="ej: dr.garcia" 
              required 
              aria-required="true"
              aria-describedby="username-help"
            />
            <p id="username-help" className="hint" style={{ fontSize: 12, marginTop: 4 }}>Selecciona un nombre de la lista debajo</p>
          </div>
          <div>
            <label htmlFor="password">Contraseña</label>
            <input 
              id="password"
              type="password" 
              value={password} 
              onChange={e => setPassword(e.target.value)} 
              placeholder="demo1234" 
              required 
              aria-required="true"
            />
          </div>
          {error && <p className="error-msg" role="alert">{error}</p>}
          <button 
            className="btn btn-primary" 
            type="submit" 
            disabled={loading} 
            style={{ width: "100%", justifyContent: "center", padding: "12px" }}
            aria-label={loading ? "Iniciando sesión" : "Acceder a MediLink"}
          >
            {loading ? "Entrando..." : "Acceder"}
          </button>
        </form>

        <div className="demo-hint" role="region" aria-label="Cuentas de demostración">
          <p style={{ marginBottom: 8 }}><strong>🏥 Médicos</strong> (contraseña: demo1234)</p>
          <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 12 }}>
            {doctors.map(({ label, u }) => (
              <button 
                key={u} 
                onClick={() => fillDemo(u)} 
                style={{ 
                  background: "none", 
                  border: "1px solid #e5e7eb",
                  textAlign: "left", 
                  cursor: "pointer", 
                  padding: "8px 10px",
                  fontSize: 14, 
                  color: "#1a56db",
                  borderRadius: "6px",
                  transition: "background 0.12s"
                }}
                onMouseEnter={e => (e.currentTarget.style.background = "#ebf5ff")}
                onMouseLeave={e => (e.currentTarget.style.background = "none")}
                aria-label={`Acceder como ${label}`}
              >
                {label}
              </button>
            ))}
          </div>
          
          <p style={{ marginBottom: 8 }}><strong>👤 Pacientes</strong> (contraseña: demo1234)</p>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {patients.map(({ label, u }) => (
              <button 
                key={u} 
                onClick={() => fillDemo(u)} 
                style={{ 
                  background: "none", 
                  border: "1px solid #e5e7eb",
                  textAlign: "left", 
                  cursor: "pointer", 
                  padding: "8px 10px",
                  fontSize: 14, 
                  color: "#1a56db",
                  borderRadius: "6px",
                  transition: "background 0.12s"
                }}
                onMouseEnter={e => (e.currentTarget.style.background = "#ecfeff")}
                onMouseLeave={e => (e.currentTarget.style.background = "none")}
                aria-label={`Acceder como ${label}`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
