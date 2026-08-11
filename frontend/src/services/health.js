import { apiRequest } from './api.js'

const defaultMaxAttempts = 8
const defaultDelayMs = 3000
const defaultRequestTimeoutMs = 10000

function delay(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds))
}

export async function waitForApi(options = {}) {
  const {
    maxAttempts = defaultMaxAttempts,
    delayMs = defaultDelayMs,
    requestTimeoutMs = defaultRequestTimeoutMs,
  } = options

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), requestTimeoutMs)

    try {
      await apiRequest('/health', { signal: controller.signal })
      return true
    } catch {
      if (attempt === maxAttempts) return false
    } finally {
      clearTimeout(timeoutId)
    }

    await delay(delayMs)
  }

  return false
}
