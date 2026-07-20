export function parseAcademicHandoff(hash) {
  const raw = String(hash || '').replace(/^#/, '')
  if (!raw) return null
  const params = new URLSearchParams(raw)
  const accessToken = params.get('access_token')?.trim()
  const role = params.get('role')
  if (!accessToken || role !== 'ACADEMIC') return null
  return { accessToken, role }
}
