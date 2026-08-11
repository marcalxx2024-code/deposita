import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuth } from '../hooks/useAuth.js'
import { waitForApi } from '../services/health.js'
import LoginPage from './LoginPage.jsx'

vi.mock('../hooks/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../services/health.js', () => ({ waitForApi: vi.fn() }))

function renderLoginPage() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/dashboard" element={<h1>Dashboard de teste</h1>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('LoginPage', () => {
  const login = vi.fn()
  const loginDemo = vi.fn()

  beforeEach(() => {
    login.mockReset()
    loginDemo.mockReset()
    waitForApi.mockReset()
    waitForApi.mockResolvedValue(true)
    useAuth.mockReturnValue({ authenticated: false, login, loginDemo })
  })

  it('exibe a entrada de demonstração', () => {
    renderLoginPage()

    expect(
      screen.getByRole('button', { name: 'Entrar na demonstração' }),
    ).toBeInTheDocument()
  })

  it('entra na demonstração e redireciona para o dashboard', async () => {
    const user = userEvent.setup()
    loginDemo.mockResolvedValue(undefined)
    renderLoginPage()

    await user.click(screen.getByRole('button', { name: 'Entrar na demonstração' }))

    await waitFor(() => expect(loginDemo).toHaveBeenCalledOnce())
    expect(
      await screen.findByRole('heading', { name: 'Dashboard de teste' }),
    ).toBeInTheDocument()
  })

  it('mostra uma mensagem amigável quando a demonstração não conecta', async () => {
    const user = userEvent.setup()
    loginDemo.mockRejectedValue(
      new Error(
        'Não foi possível conectar ao servidor. Aguarde um momento e tente novamente.',
      ),
    )
    renderLoginPage()

    await user.click(screen.getByRole('button', { name: 'Entrar na demonstração' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Não foi possível conectar ao servidor',
    )
  })

  it('informa enquanto prepara uma API que ainda está acordando', async () => {
    const user = userEvent.setup()
    let finishHealthCheck
    waitForApi.mockReturnValue(
      new Promise((resolve) => {
        finishHealthCheck = resolve
      }),
    )
    loginDemo.mockResolvedValue(undefined)
    renderLoginPage()

    await user.click(screen.getByRole('button', { name: 'Entrar na demonstração' }))

    expect(
      screen.getByText('Preparando a demonstração. Isso pode levar alguns segundos.'),
    ).toBeInTheDocument()

    finishHealthCheck(true)
    expect(
      await screen.findByRole('heading', { name: 'Dashboard de teste' }),
    ).toBeInTheDocument()
  })

  it('permite nova tentativa quando a API continua indisponível', async () => {
    const user = userEvent.setup()
    waitForApi.mockResolvedValue(false)
    renderLoginPage()

    await user.click(screen.getByRole('button', { name: 'Entrar na demonstração' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'A demonstração ainda não está disponível',
    )
    expect(loginDemo).not.toHaveBeenCalled()
    expect(
      screen.getByRole('button', { name: 'Entrar na demonstração' }),
    ).toBeEnabled()
  })

  it('mantém o login convencional e redireciona após o sucesso', async () => {
    const user = userEvent.setup()
    login.mockResolvedValue(undefined)
    renderLoginPage()

    await user.type(screen.getByLabelText('Usuário'), 'operador')
    await user.type(screen.getByLabelText('Senha'), 'senha-segura')
    await user.click(screen.getByRole('button', { name: 'Entrar no sistema' }))

    await waitFor(() =>
      expect(login).toHaveBeenCalledWith({
        username: 'operador',
        password: 'senha-segura',
      }),
    )
    expect(
      await screen.findByRole('heading', { name: 'Dashboard de teste' }),
    ).toBeInTheDocument()
  })

  it('exibe o erro devolvido pelo login convencional', async () => {
    const user = userEvent.setup()
    login.mockRejectedValue(new Error('Usuário ou senha inválidos.'))
    renderLoginPage()

    await user.type(screen.getByLabelText('Usuário'), 'operador')
    await user.type(screen.getByLabelText('Senha'), 'incorreta')
    await user.click(screen.getByRole('button', { name: 'Entrar no sistema' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Usuário ou senha inválidos.',
    )
  })
})
