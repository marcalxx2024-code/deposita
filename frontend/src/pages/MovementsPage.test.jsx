import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getRecentMovements } from '../services/movements.js'
import { listProducts } from '../services/products.js'
import MovementsPage from './MovementsPage.jsx'

vi.mock('../services/movements.js', () => ({
  createStockMovement: vi.fn(),
  getRecentMovements: vi.fn(),
}))

vi.mock('../services/products.js', () => ({
  getProduct: vi.fn(),
  listProducts: vi.fn(),
}))

describe('MovementsPage', () => {
  beforeEach(() => {
    listProducts.mockResolvedValue({
      items: [{ id: 3, sku: 'CX-003', name: 'Caixa reforçada', quantity: 12, is_active: true }],
    })
    getRecentMovements.mockResolvedValue([
      { id: 1, product_id: 3, movement_type: 'entry', quantity: 5, note: null, created_at: '2026-08-11T10:00:00Z' },
      { id: 2, product_id: 3, movement_type: 'exit', quantity: 2, note: null, created_at: '2026-08-11T11:00:00Z' },
    ])
  })

  it('diferencia entrada e saída por sinal, texto e classe semântica', async () => {
    render(<MemoryRouter><MovementsPage /></MemoryRouter>)

    const entryQuantity = await screen.findByText('+5')
    const exitQuantity = screen.getByText('−2')

    expect(entryQuantity).toHaveClass('movement-quantity--entry')
    expect(exitQuantity).toHaveClass('movement-quantity--exit')
    expect(exitQuantity).not.toHaveClass('movement-quantity--entry')
    expect(screen.getByText('Entrada', { selector: '.movement-badge' })).toBeInTheDocument()
    expect(screen.getByText('Saída', { selector: '.movement-badge' })).toBeInTheDocument()
  })

  it('pré-seleciona produto e entrada recebidos pelo fluxo de estoque baixo', async () => {
    render(<MemoryRouter initialEntries={['/movements?product=3&type=entry']}><MovementsPage /></MemoryRouter>)

    expect(await screen.findByLabelText('Produto')).toHaveValue('3')
    expect(screen.getByLabelText('Tipo')).toHaveValue('entry')
  })
})
