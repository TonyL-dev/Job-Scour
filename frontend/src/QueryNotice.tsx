export function QueryNotice({ query, label }: { query: { isPending: boolean; error: Error | null; refetch: () => unknown }; label: string }) {
  if (query.error) return <div role="alert"><p>{label}: {query.error.message}</p><button type="button" onClick={() => void query.refetch()}>Retry {label.toLowerCase()}</button></div>
  if (query.isPending) return <p role="status">Loading {label.toLowerCase()}…</p>
  return null
}
