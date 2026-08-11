import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { listProducts } from '../services/products.js'
import { listSuppliers } from '../services/suppliers.js'
import ProductsPage from './ProductsPage.jsx'

vi.mock('../services/products.js', () => ({
  createProduct: vi.fn(),
  deactivateProduct: vi.fn(),
  listProducts: vi.fn(),
  reactivateProduct: vi.fn(),
  updateProduct: vi.fn(),
}))

vi.mock('../services/suppliers.js', () => ({ listSuppliers: vi.fn() }))

describe('ProductsPage', () => {
  beforeEach(() => {
    listProducts.mockResolvedValue({
      items: [{
        id: 1,
        name: 'Parafuso industrial',
        category: 'Fixadores',
        quantity: 25,
        minimum_quantity: 10,
        price: 28.9,
        sku: 'PAR-001',
        supplier_id: 4,
        is_active: true,
      }],
      page: 1,
      pages: 1,
      total: 1,
    })
    listSuppliers.mockResolvedValue([{ id: 4, name: 'Metal Forte' }])
  })

  it('lista produtos com preço em reais e fornecedor por nome', async () => {
    render(<ProductsPage />)

    expect(await screen.findByText('Parafuso industrial')).toBeInTheDocument()
    expect(screen.getByText(/R\$\s*28,90/)).toBeInTheDocument()
    expect(screen.getByText('Metal Forte')).toBeInTheDocument()
    expect(listProducts).toHaveBeenCalled()
  })

  it('abre o fluxo principal de criação com fornecedor selecionável por nome', async () => {
    const user = userEvent.setup()
    render(<ProductsPage />)

    await screen.findByText('Parafuso industrial')
    await user.click(screen.getByRole('button', { name: 'Novo produto' }))

    expect(screen.getByRole('heading', { name: 'Novo produto' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Metal Forte' })).toBeInTheDocument()
  })
})
