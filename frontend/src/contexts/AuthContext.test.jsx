import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuth } from '../hooks/useAuth.js'
import {
  getCurrentUser,
  isAuthenticated,
  isDemoSession,
  loginDemo,
  logout,
} from '../services/auth.js'
import { AuthProvider } from './AuthContext.jsx'

vi.mock('../services/auth.js', () => ({
  getCurrentUser: vi.fn(),
  isAuthenticated: vi.fn(),
  isDemoSession: vi.fn(),
  login: vi.fn(),
  loginDemo: vi.fn(),
  logout: vi.fn(),
}))

function AuthConsumer() {
  const auth = useAuth()
  return (
    <div>
      <span>{auth.user?.role || 'sem usuário'}</span>
      <span>{auth.isDemo ? 'Modo demonstração' : 'Sessão normal'}</span>
      <button onClick={auth.loginDemo} type="button">Autenticar demo</button>
    </div>
  )
}

describe('AuthContext', () => {
  beforeEach(() => {
    getCurrentUser.mockReset()
    isAuthenticated.mockReset()
    isDemoSession.mockReset()
    loginDemo.mockReset()
    logout.mockReset()
    isAuthenticated.mockReturnValue(false)
    isDemoSession.mockReturnValue(true)
  })

  it('obtém role pelo /auth/me após o login demo', async () => {
    const user = userEvent.setup()
    loginDemo.mockResolvedValue(undefined)
    getCurrentUser.mockResolvedValue({ id: 7, username: 'demo', role: 'operator' })
    render(<AuthProvider><AuthConsumer /></AuthProvider>)

    await user.click(screen.getByRole('button', { name: 'Autenticar demo' }))

    expect(loginDemo).toHaveBeenCalledOnce()
    expect(getCurrentUser).toHaveBeenCalledOnce()
    expect(await screen.findByText('operator')).toBeInTheDocument()
    expect(screen.getByText('Modo demonstração')).toBeInTheDocument()
  })
})
