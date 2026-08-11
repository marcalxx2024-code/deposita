const developmentApiUrl = 'http://127.0.0.1:8000'
const apiBaseUrl =
  import.meta.env.VITE_API_URL || (import.meta.env.DEV ? developmentApiUrl : '')

export async function apiRequest(path, options = {}) {
  const { method = 'GET', headers = {}, body, token, signal } = options
  const requestHeaders = { ...headers }

  if (body !== undefined) {
    requestHeaders['Content-Type'] ??= 'application/json'
  }
  if (token) {
    requestHeaders.Authorization ??= `Bearer ${token}`
  }

  let response
  try {
    response = await fetch(`${apiBaseUrl}${path}`, {
      method,
      headers: requestHeaders,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    })
  } catch {
    const error = new Error(
      'Não foi possível conectar ao servidor. Aguarde um momento e tente novamente.',
    )
    error.code = 'NETWORK_ERROR'
    throw error
  }
  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json')
    ? await response.json()
    : null

  if (!response.ok) {
    const message =
      payload?.error?.message ||
      payload?.detail ||
      (response.status >= 500
        ? 'O servidor está temporariamente indisponível. Tente novamente em instantes.'
        : response.statusText)
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
