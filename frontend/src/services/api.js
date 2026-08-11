const developmentApiUrl = 'http://127.0.0.1:8000'
const apiBaseUrl =
  import.meta.env.VITE_API_URL || (import.meta.env.DEV ? developmentApiUrl : '')

export async function apiRequest(path, options = {}) {
  const { method = 'GET', headers = {}, body, token } = options
  const requestHeaders = { ...headers }

  if (body !== undefined) {
    requestHeaders['Content-Type'] ??= 'application/json'
  }
  if (token) {
    requestHeaders.Authorization ??= `Bearer ${token}`
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    method,
    headers: requestHeaders,
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json')
    ? await response.json()
    : null

  if (!response.ok) {
    const message = payload?.error?.message || payload?.detail || response.statusText
    const error = new Error(message || 'Não foi possível concluir a solicitação.')
    error.status = response.status
    error.payload = payload
    if (response.status === 401) {
      window.dispatchEvent(new Event('deposita:unauthorized'))
    }
    throw error
  }

  return payload
}
