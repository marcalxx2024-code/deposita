import { apiRequest } from './api.js'

const tokenStorageKey = 'deposita_access_token'
const demoSessionStorageKey = 'deposita_demo_session'

function storeAuthentication(tokenData, isDemo) {
  if (!tokenData?.access_token || tokenData.token_type?.toLowerCase() !== 'bearer') {
    throw new Error('Resposta de autenticação inválida.')
  }

  localStorage.setItem(tokenStorageKey, tokenData.access_token)
  if (isDemo) localStorage.setItem(demoSessionStorageKey, 'true')
  else localStorage.removeItem(demoSessionStorageKey)
  return tokenData
}

export function getToken() {
  return localStorage.getItem(tokenStorageKey)
}

export function isAuthenticated() {
  return Boolean(getToken())
}

export function isDemoSession() {
  return localStorage.getItem(demoSessionStorageKey) === 'true'
}

export function logout() {
  localStorage.removeItem(tokenStorageKey)
  localStorage.removeItem(demoSessionStorageKey)
}

export async function login(credentials) {
  const tokenData = await apiRequest('/auth/login', {
    method: 'POST',
    body: credentials,
  })
  return storeAuthentication(tokenData, false)
}

export async function loginDemo() {
  try {
    const tokenData = await apiRequest('/auth/demo', { method: 'POST' })
    return storeAuthentication(tokenData, true)
  } catch (error) {
    if (error.status === 404) {
      throw new Error('A demonstração não está disponível neste ambiente.')
    }
    throw error
  }
}

export function getCurrentUser() {
  return apiRequest('/auth/me', { token: getToken() })
}
