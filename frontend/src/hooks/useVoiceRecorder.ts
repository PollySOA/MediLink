import { useCallback, useEffect, useRef, useState } from "react"

// ── Tipos mínimos de la Web Speech API ──────────────────────────────────────
interface ISpeechRecognitionResult {
  readonly isFinal: boolean
  readonly 0: { readonly transcript: string }
}
interface ISpeechRecognitionResultList {
  readonly length: number
  readonly resultIndex: number
  [index: number]: ISpeechRecognitionResult
}
interface ISpeechRecognitionEvent extends Event {
  readonly resultIndex: number
  readonly results: ISpeechRecognitionResultList
}
interface ISpeechRecognitionErrorEvent extends Event {
  readonly error: string
}
interface ISpeechRecognition extends EventTarget {
  lang: string
  continuous: boolean
  interimResults: boolean
  maxAlternatives: number
  onstart: (() => void) | null
  onresult: ((ev: ISpeechRecognitionEvent) => void) | null
  onerror: ((ev: ISpeechRecognitionErrorEvent) => void) | null
  onend: (() => void) | null
  start(): void
  stop(): void
}
interface ISpeechRecognitionConstructor {
  new (): ISpeechRecognition
}

export type RecorderState = "idle" | "listening" | "processing" | "error"

interface UseVoiceRecorderOptions {
  /** Llamado con el texto transcrito cuando el usuario deja de hablar */
  onTranscript: (text: string) => void
  /** BCP-47 lang tag. Por defecto "es-ES" */
  lang?: string
}

interface UseVoiceRecorderReturn {
  state: RecorderState
  /** Mensaje de error legible para el usuario */
  errorMsg: string | null
  /** False si el navegador no soporta SpeechRecognition */
  isSupported: boolean
  /** Texto parcial transcrito mientras se habla */
  interimText: string
  start: () => void
  stop: () => void
  toggle: () => void
}

// Compatibilidad webkit/estándar
const SpeechRecognitionAPI: ISpeechRecognitionConstructor | null =
  typeof window === "undefined"
    ? null
    : ((window as unknown as Record<string, unknown>)["SpeechRecognition"] as ISpeechRecognitionConstructor | undefined) ??
      ((window as unknown as Record<string, unknown>)["webkitSpeechRecognition"] as ISpeechRecognitionConstructor | undefined) ??
      null

function cleanTranscript(text: string): string {
  return text
    .replace(/\b(eh+|emm+|mmm+|este+|a ver|pues|bueno)\b/gi, " ")
    .replace(/\s+/g, " ")
    .replace(/\s+([,.;:!?])/g, "$1")
    .trim()
}

export function useVoiceRecorder({
  onTranscript,
  lang = "es-ES",
}: UseVoiceRecorderOptions): UseVoiceRecorderReturn {
  const [state, setState] = useState<RecorderState>("idle")
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [interimText, setInterimText] = useState("")

  const recogRef = useRef<ISpeechRecognition | null>(null)
  const onTranscriptRef = useRef(onTranscript)
  onTranscriptRef.current = onTranscript

  const isSupported = SpeechRecognitionAPI !== null

  const stop = useCallback(() => {
    recogRef.current?.stop()
    recogRef.current = null
    setState("idle")
    setInterimText("")
  }, [])

  const start = useCallback(() => {
    if (!isSupported) {
      setErrorMsg("Tu navegador no soporta el reconocimiento de voz. Prueba con Chrome o Edge.")
      setState("error")
      return
    }
    if (state === "listening") return

    setErrorMsg(null)
    setInterimText("")

    const recog = new SpeechRecognitionAPI()
    recog.lang = lang
    recog.continuous = false
    recog.interimResults = true
    recog.maxAlternatives = 1

    recog.onstart = () => setState("listening")

    recog.onresult = (event: ISpeechRecognitionEvent) => {
      let interim = ""
      let final = ""
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript
        if (event.results[i].isFinal) {
          final += transcript
        } else {
          interim += transcript
        }
      }
      setInterimText(cleanTranscript(interim || final))
      if (final) {
        const cleanedFinal = cleanTranscript(final)
        if (cleanedFinal.length < 3) {
          setErrorMsg("No se ha entendido bien la frase. Prueba a repetirla con un poco mas de claridad.")
          setState("idle")
          setInterimText("")
          return
        }
        setState("processing")
        setInterimText("")
        onTranscriptRef.current(cleanedFinal)
      }
    }

    recog.onerror = (event: ISpeechRecognitionErrorEvent) => {
      const map: Record<string, string> = {
        "no-speech": "No se detectó voz. Habla más cerca del micrófono.",
        "audio-capture": "No se pudo acceder al micrófono. Revisa los permisos.",
        "not-allowed": "Permiso de micrófono denegado. Actívalo en el navegador.",
        "network": "Error de red durante el reconocimiento de voz.",
      }
      setErrorMsg(map[event.error] ?? "Error en el reconocimiento de voz. Inténtalo de nuevo.")
      setState("error")
      recogRef.current = null
    }

    recog.onend = () => {
      if (state !== "processing") setState("idle")
      recogRef.current = null
      setInterimText("")
    }

    recogRef.current = recog
    recog.start()
  }, [isSupported, lang, state])

  const toggle = useCallback(() => {
    if (state === "listening") {
      stop()
    } else if (state === "idle" || state === "error") {
      start()
    }
  }, [state, start, stop])

  // Limpieza al desmontar
  useEffect(() => {
    return () => {
      recogRef.current?.stop()
    }
  }, [])

  return { state, errorMsg, isSupported, interimText, start, stop, toggle }
}
