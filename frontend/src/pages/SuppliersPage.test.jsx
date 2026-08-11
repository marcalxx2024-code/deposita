import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuth } from '../hooks/useAuth.js'
import { listSuppliers } from '../services/suppliers.js'
import SuppliersPage from './SuppliersPage.jsx'

vi.mock('../services/suppliers.js', () => ({
  createSupplier: vi.fn(),
  deleteSupplier: vi.fn(),
  listSuppliers: vi.fn(),
  updateSupplier: vi.fn(),
}))
vi.mock('../hooks/useAuth.js', () => ({ useAuth: vi.fn() }))

describe('SuppliersPage', () => {
  beforeEach(() => {
    useAuth.mockReturnValue({ user: { role: 'admin' } })
    listSuppliers.mockResolvedValue([{
      id: 1,
      name: 'Fornecedor Exemplo',
      contact_name: 'Contato',
      phone: '11999999999',
      email: 'contato@example.com',
      created_at: '2026-08-11T10:00:00Z',
    }])
  })

  it('mantém os controles administrativos visíveis para admin', async () => {
    render(<SuppliersPage />)

    expect(await screen.findByText('Fornecedor Exemplo')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Novo fornecedor' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Editar' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Excluir' })).toBeInTheDocument()
  })

  it('mantém a consulta e oculta alterações para operator', async () => {
    useAuth.mockReturnValue({ user: { role: 'operator' } })
    render(<SuppliersPage />)

    expect(await screen.findByText('Fornecedor Exemplo')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Novo fornecedor' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Editar' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Excluir' })).not.toBeInTheDocument()
  })
})
