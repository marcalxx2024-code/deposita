import { useCallback, useEffect, useState } from 'react'
import {
  createProduct,
  deactivateProduct,
  listProducts,
  reactivateProduct,
  updateProduct,
} from '../services/products.js'

const emptyProduct = {
  name: '',
  category: '',
  quantity: '',
  minimum_quantity: '',
  price: '',
  sku: '',
  supplier_id: '',
}

function toProductForm(product) {
  return {
    name: product.name,
    category: product.category,
    quantity: String(product.quantity),
    minimum_quantity: String(product.minimum_quantity),
    price: String(product.price),
    sku: product.sku,
    supplier_id: product.supplier_id ? String(product.supplier_id) : '',
  }
}

function ProductsPage() {
  const [productsData, setProductsData] = useState(null)
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState({ search: '', category: '', low_stock: false, include_inactive: false })
  const [appliedFilters, setAppliedFilters] = useState({})
  const [form, setForm] = useState(emptyProduct)
  const [editingProduct, setEditingProduct] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [expandedProductIds, setExpandedProductIds] = useState(new Set())

  const loadProducts = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await listProducts({ page, pageSize: 20, ...appliedFilters })
      setProductsData(data)
    } catch (requestError) {
      setError(requestError.message || 'Não foi possível carregar os produtos.')
    } finally {
      setLoading(false)
    }
  }, [appliedFilters, page])

  useEffect(() => {
    loadProducts()
  }, [loadProducts])

  function updateForm(field, value) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  function handleFilterSubmit(event) {
    event.preventDefault()
    setPage(1)
    setAppliedFilters({
      ...(filters.search.trim() && { search: filters.search.trim() }),
      ...(filters.category.trim() && { category: filters.category.trim() }),
      ...(filters.low_stock && { low_stock: true }),
      ...(filters.include_inactive && { include_inactive: true }),
    })
  }

  function openNewProduct() {
    setEditingProduct(null)
    setForm(emptyProduct)
    setError('')
    setMessage('')
    setShowForm(true)
  }

  function openEditProduct(product) {
    setEditingProduct(product)
    setForm(toProductForm(product))
    setError('')
    setMessage('')
    setShowForm(true)
  }

  function closeForm() {
    setShowForm(false)
    setEditingProduct(null)
    setForm(emptyProduct)
  }

  function toggleProductDetails(productId) {
    setExpandedProductIds((current) => {
      const next = new Set(current)
      if (next.has(productId)) next.delete(productId)
      else next.add(productId)
      return next
    })
  }

  async function handleProductSubmit(event) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setMessage('')

    const productData = {
      name: form.name,
      category: form.category,
      minimum_quantity: Number(form.minimum_quantity),
      price: Number(form.price),
      sku: form.sku,
      supplier_id: form.supplier_id === '' ? null : Number(form.supplier_id),
    }
    if (!editingProduct) productData.quantity = Number(form.quantity)

    try {
      if (editingProduct) {
        await updateProduct(editingProduct.id, productData)
        setMessage('Produto atualizado com sucesso.')
      } else {
        await createProduct(productData)
        setMessage('Produto criado com sucesso.')
        setPage(1)
      }
      closeForm()
      await loadProducts()
    } catch (requestError) {
      setError(requestError.message || 'Não foi possível salvar o produto.')
    } finally {
      setSaving(false)
    }
  }

  async function handleDeactivate(product) {
    if (!window.confirm(`Inativar o produto ${product.name}?`)) return
    setError('')
    setMessage('')
    try {
      await deactivateProduct(product.id)
      setMessage('Produto inativado com sucesso.')
      await loadProducts()
    } catch (requestError) {
      setError(requestError.message || 'Não foi possível inativar o produto.')
    }
  }

  async function handleReactivate(product) {
    setError('')
    setMessage('')
    try {
      await reactivateProduct(product.id)
      setMessage('Produto reativado com sucesso.')
      await loadProducts()
    } catch (requestError) {
      setError(requestError.message || 'Não foi possível reativar o produto.')
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Produtos</h1>
        <button type="button" onClick={openNewProduct}>Novo produto</button>
      </div>

      <form className="panel form-grid" onSubmit={handleFilterSubmit}>
        <label>Busca<input value={filters.search} onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))} /></label>
        <label>Categoria<input value={filters.category} onChange={(event) => setFilters((current) => ({ ...current, category: event.target.value }))} /></label>
        <label className="checkbox-field"><input checked={filters.low_stock} onChange={(event) => setFilters((current) => ({ ...current, low_stock: event.target.checked }))} type="checkbox" />Estoque baixo</label>
        <label className="checkbox-field"><input checked={filters.include_inactive} onChange={(event) => setFilters((current) => ({ ...current, include_inactive: event.target.checked }))} type="checkbox" />Incluir inativos</label>
        <div className="form-actions"><button type="submit">Filtrar</button></div>
      </form>

      {showForm && (
        <form className="panel form-grid" onSubmit={handleProductSubmit}>
          <h2>{editingProduct ? 'Editar produto' : 'Novo produto'}</h2>
          <label>SKU<input maxLength="64" onChange={(event) => updateForm('sku', event.target.value)} required value={form.sku} /></label>
          <label>Nome<input maxLength="100" minLength="2" onChange={(event) => updateForm('name', event.target.value)} required value={form.name} /></label>
          <label>Categoria<input maxLength="50" minLength="2" onChange={(event) => updateForm('category', event.target.value)} required value={form.category} /></label>
          {!editingProduct && <label>Quantidade<input min="0" onChange={(event) => updateForm('quantity', event.target.value)} required type="number" value={form.quantity} /></label>}
          <label>Estoque mínimo<input min="0" onChange={(event) => updateForm('minimum_quantity', event.target.value)} required type="number" value={form.minimum_quantity} /></label>
          <label>Preço<input min="0" onChange={(event) => updateForm('price', event.target.value)} required step="0.01" type="number" value={form.price} /></label>
          <label>Fornecedor (ID opcional)<input min="1" onChange={(event) => updateForm('supplier_id', event.target.value)} type="number" value={form.supplier_id} /></label>
          <div className="form-actions"><button disabled={saving} type="submit">{saving ? 'Salvando...' : 'Salvar'}</button><button disabled={saving} onClick={closeForm} type="button">Cancelar</button></div>
        </form>
      )}

      {message && <p className="status-message">{message}</p>}
      {error && <p className="error-message" role="alert">{error}</p>}
      {loading ? <p>Carregando...</p> : productsData?.items.length === 0 ? <p>Nenhum produto encontrado.</p> : (
        <div className="data-table-wrapper"><table className="data-table"><thead><tr><th>SKU</th><th>Nome</th><th>Categoria</th><th>Quantidade</th><th>Mínimo</th><th>Preço</th><th>Fornecedor</th><th>Status</th><th>Ações</th></tr></thead><tbody>
          {productsData?.items.map((product) => { const detailsExpanded = expandedProductIds.has(product.id); return <tr className={`product-row ${detailsExpanded ? 'is-expanded' : ''}`} key={product.id}><td data-label="SKU">{product.sku}</td><td data-label="Nome">{product.name}</td><td className="mobile-secondary" data-label="Categoria">{product.category}</td><td data-label="Quantidade"><span className="desktop-only-cell">{product.quantity}</span><span className="mobile-quantity-summary">{product.quantity} (mínimo: {product.minimum_quantity})</span></td><td className="desktop-only-cell" data-label="Mínimo">{product.minimum_quantity}</td><td className="mobile-secondary" data-label="Preço">{product.price}</td><td className="mobile-secondary" data-label="Fornecedor">{product.supplier_id ?? '—'}</td><td data-label="Status">{product.is_active ? 'Ativo' : 'Inativo'}</td><td data-label="Ações"><div className="inline-actions"><button aria-expanded={detailsExpanded} className="mobile-details-toggle button-secondary" onClick={() => toggleProductDetails(product.id)} type="button">{detailsExpanded ? 'Ocultar detalhes' : 'Ver detalhes'}</button>{product.is_active ? <><button onClick={() => openEditProduct(product)} type="button">Editar</button><button className="button-danger" onClick={() => handleDeactivate(product)} type="button">Inativar</button></> : <button onClick={() => handleReactivate(product)} type="button">Reativar</button>}</div></td></tr> })}
        </tbody></table></div>
      )}

      {productsData && <div className="pagination"><button disabled={page <= 1 || loading} onClick={() => setPage((current) => Math.max(1, current - 1))} type="button">Anterior</button><span>Página {productsData.page} de {productsData.pages}</span><button disabled={page >= productsData.pages || loading} onClick={() => setPage((current) => current + 1)} type="button">Próxima</button></div>}
    </div>
  )
}

export default ProductsPage
