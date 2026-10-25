import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Browser speech-to-text via the Web Speech API.
 *
 * The transcript never leaves the browser as audio — only the recognised text
 * is sent to the server. Chromium-only in practice, and the page must be on
 * localhost or HTTPS or the microphone permission is denied outright.
 *
 * TypeScript's DOM lib still has no SpeechRecognition types, hence the local
 * declarations.
 */

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}
interface SpeechRecognitionResult {
  readonly length: number;
  isFinal: boolean;
  [index: number]: SpeechRecognitionAlternative;
}
interface SpeechRecognitionResultList {
  readonly length: number;
  [index: number]: SpeechRecognitionResult;
}
interface SpeechRecognitionEvent extends Event {
  resultIndex: number;
  results: SpeechRecognitionResultList;
}
interface SpeechRecognitionErrorEvent extends Event {
  error: string;
  message: string;
}
interface SpeechRecognitionLike extends EventTarget {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  start(): void;
  stop(): void;
  abort(): void;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  onstart: (() => void) | null;
}
type SpeechRecognitionCtor = new () => SpeechRecognitionLike;

function getRecognitionCtor(): SpeechRecognitionCtor | null {
  const w = window as unknown as {
    SpeechRecognition?: SpeechRecognitionCtor;
    webkitSpeechRecognition?: SpeechRecognitionCtor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

const ERROR_MESSAGES: Record<string, string> = {
  "not-allowed": "Microphone permission denied. Allow it in the address bar and try again.",
  "service-not-allowed": "Speech recognition is blocked. The page must be on localhost or HTTPS.",
  "no-speech": "Didn't catch that — try again.",
  network: "Speech recognition lost its network connection.",
  aborted: "",
};

export interface UseSpeechRecognitionOptions {
  lang?: string;
  /** Called once per finalised utterance. */
  onResult: (transcript: string) => void;
}

export function useSpeechRecognition({
  lang = "en-US",
  onResult,
}: UseSpeechRecognitionOptions) {
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState("");
  const [error, setError] = useState<string | null>(null);

  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  // Kept in a ref so restarting recognition doesn't need the callback in the
  // effect's dependency list (it changes on every render of the parent).
  const onResultRef = useRef(onResult);
  onResultRef.current = onResult;

  const supported = getRecognitionCtor() !== null;

  useEffect(() => {
    const Ctor = getRecognitionCtor();
    if (!Ctor) return;

    const recognition = new Ctor();
    recognition.lang = lang;
    // Push-to-talk: one utterance per press. Continuous mode drifts and fires
    // spurious finals when the room is noisy.
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      setListening(true);
      setError(null);
    };

    recognition.onresult = (event) => {
      let finalText = "";
      let interimText = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        if (result.isFinal) finalText += result[0].transcript;
        else interimText += result[0].transcript;
      }
      setInterim(interimText);
      const trimmed = finalText.trim();
      if (trimmed) {
        setInterim("");
        onResultRef.current(trimmed);
      }
    };

    recognition.onerror = (event) => {
      const message = ERROR_MESSAGES[event.error] ?? `Speech error: ${event.error}`;
      if (message) setError(message);
      setListening(false);
    };

    recognition.onend = () => {
      setListening(false);
      setInterim("");
    };

    recognitionRef.current = recognition;
    return () => {
      recognition.onresult = null;
      recognition.onerror = null;
      recognition.onend = null;
      recognition.abort();
      recognitionRef.current = null;
    };
  }, [lang]);

  const start = useCallback(() => {
    try {
      recognitionRef.current?.start();
    } catch {
      // start() throws if it is already running; harmless.
    }
  }, []);

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
  }, []);

  const toggle = useCallback(() => {
    if (listening) stop();
    else start();
  }, [listening, start, stop]);

  return { supported, listening, interim, error, start, stop, toggle };
}
