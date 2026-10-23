// Match the backend's conservative sentence boundary rule.
export function summaryError(text: string): boolean {
  return text.length > 500 || /[\r\n]|[.!?]+["')\]]*\s+\S/.test(text.trim())
}
