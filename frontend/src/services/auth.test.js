import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiRequest } from './api.js'
import {
  getToken,
  isDemoSession,
  login,
  loginDemo,
  logout,
} from './auth.js'

vi.mock('./api.js', () => ({ apiRequest: vi.fn() }))

describe('auth service', () => {
  beforeEach(() => {
    apiRequest.mockReset()
    localStorage.clear()
  })

  it('chama o endpoint demo e armazena o mesmo tipo de JWT do login normal', async () => {
    apiRequest.mockResolvedValue({ access_token: 'demo-jwt', token_type: 'bearer' })

    await loginDemo()

    expect(apiRequest).toHaveBeenCalledWith('/auth/demo', { method: 'POST' })
    expect(getToken()).toBe('demo-jwt')
    expect(isDemoSession()).toBe(true)
  })

  it('mantém o login convencional e remove uma indicação demo anterior', async () => {
    localStorage.setItem('deposita_demo_session', 'true')
    apiRequest.mockResolvedValue({ access_token: 'regular-jwt', token_type: 'bearer' })

    await login({ username: 'operador', password: 'senha-segura' })

    expect(apiRequest).toHaveBeenCalledWith('/auth/login', {
      method: 'POST',
      body: { username: 'operador', password: 'senha-segura' },
    })
    expect(getToken()).toBe('regular-jwt')
    expect(isDemoSession()).toBe(false)
  })

  it('limpa token e indicação demo no logout', async () => {
    apiRequest.mockResolvedValue({ access_token: 'demo-jwt', token_type: 'bearer' })
    await loginDemo()

    logout()

    expect(getToken()).toBeNull()
    expect(isDemoSession()).toBe(false)
  })

  it('traduz demo desativada para uma mensagem apropriada', async () => {
    const unavailableError = new Error('Not Found')
    unavailableError.status = 404
    apiRequest.mockRejectedValue(unavailableError)

    await expect(loginDemo()).rejects.toThrow(
      'A demonstração não está disponível neste ambiente.',
    )
    expect(getToken()).toBeNull()
  })
})
