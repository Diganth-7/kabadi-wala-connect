import { useCallback } from 'react'
export function useSpeech() {
  return useCallback((text:string) => {
    if (!('speechSynthesis' in window)) return false
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = 'en-IN'
    window.speechSynthesis.speak(utterance)
    return true
  }, [])
}
