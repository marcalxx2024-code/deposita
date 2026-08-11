import { apiRequest } from './api.js'
import { getToken } from './auth.js'

export function getDashboardSummary() {
  return apiRequest('/dashboard/summary', { token: getToken() })
}
