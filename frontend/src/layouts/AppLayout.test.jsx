import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { useAuth } from '../hooks/useAuth.js'
import AppLayout from './AppLayout.jsx'

vi.mock('../hooks/useAuth.js', () => ({ useAuth: vi.fn() }))

describe('AppLayout', () => {
  it('identifica discretamente a sessão demo e mantém movimentações disponíveis', () => {
    useAuth.mockReturnValue({
      isDemo: true,
      logout: vi.fn(),
      user: { username: 'conta-publica', role: 'operator' },
    })

    render(
      <MemoryRouter>
        <Routes>
          <Route element={<AppLayout />} path="/">
            <Route index element={<p>Conteúdo</p>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText('Modo demonstração')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Movimentações/ })).toBeInTheDocument()
  })
})
