import { useState } from "react"
import { api, formatApiError } from "../services/api"
import { useAuth } from "../context/AuthContext"

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

  return (
    <div className="login-screen">
      <div className="login-card">
        <div className="login-logo">
          <h1>Medi<span>Link</span></h1>
          <p>Interoperabilidad y Humanización Médica</p>
          <p style={{ fontSize: 11, color: "#9ca3af", marginTop: 2 }}>I Hackathon IABiomed · Reto Idonia</p>
        </div>

        <form onSubmit={handleLogin} className="stack">
          <div>
            <label>Usuario</label>
            <input value={username} onChange={e => setUsername(e.target.value)} placeholder="dr.garcia o un usuario demo" required />
          </div>
          <div>
            <label>Contraseña</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="demo1234" required />
          </div>
          {error && <p className="error-msg">{error}</p>}
          <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: "100%", justifyContent: "center", padding: "10px" }}>
            {loading ? "Entrando..." : "Acceder"}
          </button>
        </form>

        <div className="demo-hint">
          <p style={{ marginBottom: 8 }}><strong>Cuentas de demo</strong> (contraseña: demo1234)</p>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {[
              { label: "Dr. Carlos García (Traumatología)", u: "dr.garcia" },
              { label: "Dra. Ana López (Interna)", u: "dr.lopez" },
              { label: "Carolina R. (paciente rodilla)", u: "alejandro.m" },
              { label: "Carmen R. (paciente cardiología)", u: "carmen.r" },
              { label: "Rosa F. (paciente neumología)", u: "rosa.f" },
              { label: "Miguel D. (paciente cardiología)", u: "miguel.d" },
              { label: "Isabel M. (paciente neurología)", u: "isabel.m" },
            ].map(({ label, u }) => (
              <button key={u} onClick={() => fillDemo(u)} style={{ background: "none", border: "none", textAlign: "left", cursor: "pointer", padding: "2px 0", fontSize: 12, color: "#1a56db" }}>
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
