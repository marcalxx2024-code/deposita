import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiRequest } from './api.js'
import { waitForApi } from './health.js'

vi.mock('./api.js', () => ({ apiRequest: vi.fn() }))

describe('waitForApi', () => {
  beforeEach(() => {
    apiRequest.mockReset()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('encerra assim que o health check responde', async () => {
    apiRequest.mockResolvedValue({ status: 'online' })

    await expect(waitForApi()).resolves.toBe(true)

    expect(apiRequest).toHaveBeenCalledOnce()
    expect(apiRequest).toHaveBeenCalledWith(
      '/health',
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    )
  })

  it('limita tentativas e retorna false sem polling infinito', async () => {
    apiRequest.mockRejectedValue(new Error('offline'))

    const resultPromise = waitForApi({
      maxAttempts: 3,
      delayMs: 100,
      requestTimeoutMs: 50,
    })
    await vi.runAllTimersAsync()

    await expect(resultPromise).resolves.toBe(false)
    expect(apiRequest).toHaveBeenCalledTimes(3)
  })
})
