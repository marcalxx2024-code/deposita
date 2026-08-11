import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiRequest } from './api.js'

describe('apiRequest', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  it('não expõe o erro técnico quando a conexão falha', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    await expect(apiRequest('/health')).rejects.toThrow(
      'Não foi possível conectar ao servidor. Aguarde um momento e tente novamente.',
    )
  })

  it('usa VITE_API_URL no build hospedado', async () => {
    vi.stubEnv('VITE_API_URL', 'https://api.deposita.example.com')
    vi.resetModules()
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => 'application/json' },
      json: async () => ({ status: 'online' }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const { apiRequest: configuredApiRequest } = await import('./api.js')

    await configuredApiRequest('/health')

    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.deposita.example.com/health',
      expect.objectContaining({ method: 'GET' }),
    )
  })
})
