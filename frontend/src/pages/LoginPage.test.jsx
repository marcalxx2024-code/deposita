import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuth } from '../hooks/useAuth.js'
import LoginPage from './LoginPage.jsx'

vi.mock('../hooks/useAuth.js', () => ({ useAuth: vi.fn() }))

describe('LoginPage', () => {
  const login = vi.fn()

  beforeEach(() => {
    login.mockReset()
    useAuth.mockReturnValue({ authenticated: false, login })
  })

  it('envia as credenciais pelo fluxo de autenticação', async () => {
    const user = userEvent.setup()
    login.mockResolvedValue(undefined)
    render(<MemoryRouter><LoginPage /></MemoryRouter>)

    await user.type(screen.getByLabelText('Usuário'), 'operador')
    await user.type(screen.getByLabelText('Senha'), 'senha-segura')
    await user.click(screen.getByRole('button', { name: 'Entrar no sistema' }))

    await waitFor(() => expect(login).toHaveBeenCalledWith({ username: 'operador', password: 'senha-segura' }))
  })

  it('exibe o erro devolvido pela autenticação', async () => {
    const user = userEvent.setup()
    login.mockRejectedValue(new Error('Usuário ou senha inválidos.'))
    render(<MemoryRouter><LoginPage /></MemoryRouter>)

    await user.type(screen.getByLabelText('Usuário'), 'operador')
    await user.type(screen.getByLabelText('Senha'), 'incorreta')
    await user.click(screen.getByRole('button', { name: 'Entrar no sistema' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Usuário ou senha inválidos.')
  })
})
