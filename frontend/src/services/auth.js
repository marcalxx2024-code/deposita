import { apiRequest } from './api.js'

const tokenStorageKey = 'deposita_access_token'

export function getToken() {
  return localStorage.getItem(tokenStorageKey)
}

export function isAuthenticated() {
  return Boolean(getToken())
}

export function logout() {
  localStorage.removeItem(tokenStorageKey)
}

export async function login(credentials) {
  const tokenData = await apiRequest('/auth/login', {
    method: 'POST',
    body: credentials,
  })

  if (!tokenData?.access_token || tokenData.token_type?.toLowerCase() !== 'bearer') {
    throw new Error('Resposta de autenticação inválida.')
  }

  localStorage.setItem(tokenStorageKey, tokenData.access_token)
  return tokenData
}

export function getCurrentUser() {
  return apiRequest('/auth/me', { token: getToken() })
}
