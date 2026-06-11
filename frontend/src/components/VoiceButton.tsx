import { useEffect, useRef } from "react"
import type { RecorderState } from "../hooks/useVoiceRecorder"

interface VoiceButtonProps {
  state: RecorderState
  isSupported: boolean
  interimText: string
  /** Texto que Elena está "pensando" (procesando) */
  isElenaThinking: boolean
  onToggle: () => void
}

const STATE_LABELS: Record<RecorderState, string> = {
  idle:       "Hablar con Elena",
  listening:  "Escuchando... (pulsa para parar)",
  processing: "Elena está pensando...",
  error:      "Reintentar",
}

const STATE_ICONS: Record<RecorderState, string> = {
  idle:       "🎤",
  listening:  "⏹",
  processing: "⏳",
  error:      "🎤",
}

export default function VoiceButton({
  state,
  isSupported,
  interimText,
  isElenaThinking,
  onToggle,
}: VoiceButtonProps) {
  const displayState: RecorderState = isElenaThinking ? "processing" : state
  const isActive = displayState === "listening"
  const isDisabled = !isSupported || displayState === "processing"

  // Ref para el canvas de onda sonora decorativa
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animRef = useRef<number>(0)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext("2d")
    if (!ctx) return

    if (!isActive) {
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      cancelAnimationFrame(animRef.current)
      return
    }

    let t = 0
    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      const bars = 18
      const barW = canvas.width / (bars * 2 - 1)
      for (let i = 0; i < bars; i++) {
        const amp = 0.3 + 0.7 * Math.abs(Math.sin(t * 3 + i * 0.6))
        const h = amp * canvas.height * 0.75
        const x = i * (barW + barW)
        const y = (canvas.height - h) / 2
        ctx.fillStyle = `rgba(220,38,38,${0.6 + amp * 0.4})`
        ctx.beginPath()
        ctx.roundRect(x, y, barW, h, barW / 2)
        ctx.fill()
      }
      t += 0.06
      animRef.current = requestAnimationFrame(draw)
    }

    animRef.current = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(animRef.current)
  }, [isActive])

  return (
    <div className="voice-btn-wrap" aria-label="Control de voz para hablar con Elena">
      {/* Onda sonora animada */}
      <canvas
        ref={canvasRef}
        className="voice-wave"
        width={160}
        height={36}
        aria-hidden="true"
        style={{ opacity: isActive ? 1 : 0 }}
      />

      {/* Botón principal */}
      <button
        className={`voice-btn voice-btn-${displayState}`}
        onClick={onToggle}
        disabled={isDisabled}
        aria-label={STATE_LABELS[displayState]}
        aria-pressed={isActive}
        aria-live="polite"
      >
        <span className="voice-btn-icon" aria-hidden="true">
          {displayState === "processing"
            ? <span className="voice-spinner" />
            : STATE_ICONS[displayState]}
        </span>
        <span className="voice-btn-label">{STATE_LABELS[displayState]}</span>
      </button>

      {/* Transcripción parcial en tiempo real */}
      {interimText && (
        <p className="voice-interim" role="status" aria-live="polite">
          <span aria-hidden="true">💬</span> {interimText}
        </p>
      )}

      {/* Aviso si el navegador no soporta la API */}
      {!isSupported && (
        <p className="voice-unsupported" role="alert">
          Reconocimiento de voz no disponible en este navegador.
          Usa Chrome o Edge para esta función.
        </p>
      )}
    </div>
  )
}
