import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Reads the tutor's reply aloud, sentence by sentence as it streams in.
 *
 * Waiting for the full reply before speaking wastes the whole point of
 * streaming, so `speakStreaming` buffers deltas and flushes each time a
 * sentence closes. `flush` speaks whatever is left when the stream ends.
 */

const SENTENCE_END = /[.!?]["')\]]?\s/;

export function useSpeechSynthesis() {
  const [speaking, setSpeaking] = useState(false);
  const [muted, setMuted] = useState(
    () => localStorage.getItem("tutor.muted") === "true",
  );
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [voiceUri, setVoiceUri] = useState<string>(
    () => localStorage.getItem("tutor.voice") ?? "",
  );

  const bufferRef = useRef("");
  const supported = typeof window !== "undefined" && "speechSynthesis" in window;

  useEffect(() => {
    if (!supported) return;
    const load = () => setVoices(window.speechSynthesis.getVoices());
    load();
    // Chrome populates the list asynchronously after first call.
    window.speechSynthesis.addEventListener("voiceschanged", load);
    return () => window.speechSynthesis.removeEventListener("voiceschanged", load);
  }, [supported]);

  useEffect(() => {
    localStorage.setItem("tutor.muted", String(muted));
  }, [muted]);

  useEffect(() => {
    if (voiceUri) localStorage.setItem("tutor.voice", voiceUri);
  }, [voiceUri]);

  const speak = useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (!supported || muted || !trimmed) return;

      const utterance = new SpeechSynthesisUtterance(trimmed);
      utterance.lang = "en-US";
      const voice = voices.find((v) => v.voiceURI === voiceUri);
      if (voice) utterance.voice = voice;
      utterance.onstart = () => setSpeaking(true);
      utterance.onend = () => setSpeaking(false);
      utterance.onerror = () => setSpeaking(false);
      window.speechSynthesis.speak(utterance);
    },
    [supported, muted, voices, voiceUri],
  );

  /** Feed one streamed delta; speaks as soon as a full sentence is available. */
  const speakStreaming = useCallback(
    (delta: string) => {
      bufferRef.current += delta;
      let match = SENTENCE_END.exec(bufferRef.current);
      while (match) {
        const cut = match.index + match[0].length;
        speak(bufferRef.current.slice(0, cut));
        bufferRef.current = bufferRef.current.slice(cut);
        match = SENTENCE_END.exec(bufferRef.current);
      }
    },
    [speak],
  );

  /** Speak the trailing fragment left after the stream closed. */
  const flush = useCallback(() => {
    const rest = bufferRef.current;
    bufferRef.current = "";
    if (rest.trim()) speak(rest);
  }, [speak]);

  const cancel = useCallback(() => {
    bufferRef.current = "";
    if (supported) window.speechSynthesis.cancel();
    setSpeaking(false);
  }, [supported]);

  return {
    supported,
    speaking,
    muted,
    setMuted,
    voices,
    voiceUri,
    setVoiceUri,
    speak,
    speakStreaming,
    flush,
    cancel,
  };
}
