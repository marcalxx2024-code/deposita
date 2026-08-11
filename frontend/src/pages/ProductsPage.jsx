import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  createProduct,
  deactivateProduct,
  listProducts,
  reactivateProduct,
  updateProduct,
} from '../services/products.js'
import { listSuppliers } from '../services/suppliers.js'
import { useAuth } from '../hooks/useAuth.js'
import { formatCurrency } from '../utils/formatters.js'

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
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [productsData, setProductsData] = useState(null)
  const [suppliers, setSuppliers] = useState([])
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState({ search: '', category: '', low_stock: false, include_inactive: false })
  const [appliedFilters, setAppliedFilters] = useState({})
  const [form, setForm] = useState(emptyProduct)
  const [editingProduct, setEditingProduct] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [loadingSuppliers, setLoadingSuppliers] = useState(true)
  const [processingProductId, setProcessingProductId] = useState(null)
  const [error, setError] = useState('')
  const [supplierError, setSupplierError] = useState('')
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

  useEffect(() => {
    let active = true

    async function loadSupplierOptions() {
      try {
        const data = await listSuppliers({ skip: 0, limit: 100 })
        if (active) setSuppliers(data)
      } catch (requestError) {
        if (active) setSupplierError(requestError.message || 'Não foi possível carregar os fornecedores.')
      } finally {
        if (active) setLoadingSuppliers(false)
      }
    }

    loadSupplierOptions()
    return () => {
      active = false
    }
  }, [])

  const supplierNames = useMemo(
    () => new Map(suppliers.map((supplier) => [supplier.id, supplier.name])),
    [suppliers],
  )

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

    const shouldResetPage = !editingProduct && page !== 1

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
      if (!shouldResetPage) await loadProducts()
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
    setProcessingProductId(product.id)
    try {
      await deactivateProduct(product.id)
      setMessage('Produto inativado com sucesso.')
      await loadProducts()
    } catch (requestError) {
      setError(requestError.message || 'Não foi possível inativar o produto.')
    } finally {
      setProcessingProductId(null)
    }
  }

  async function handleReactivate(product) {
    setError('')
    setMessage('')
    setProcessingProductId(product.id)
    try {
      await reactivateProduct(product.id)
      setMessage('Produto reativado com sucesso.')
      await loadProducts()
    } catch (requestError) {
      setError(requestError.message || 'Não foi possível reativar o produto.')
    } finally {
      setProcessingProductId(null)
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <span className="eyebrow">Catálogo de inventário</span>
          <h1>Produtos</h1>
        </div>
        {isAdmin && <button type="button" onClick={openNewProduct}>Novo produto</button>}
      </div>

      <form className="panel panel--filters form-grid" onSubmit={handleFilterSubmit}>
        <h2 className="panel-title">Filtros</h2>
        <label>Busca<input value={filters.search} onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))} /></label>
        <label>Categoria<input value={filters.category} onChange={(event) => setFilters((current) => ({ ...current, category: event.target.value }))} /></label>
        <label className="checkbox-field"><input checked={filters.low_stock} onChange={(event) => setFilters((current) => ({ ...current, low_stock: event.target.checked }))} type="checkbox" />Estoque baixo</label>
        <label className="checkbox-field"><input checked={filters.include_inactive} onChange={(event) => setFilters((current) => ({ ...current, include_inactive: event.target.checked }))} type="checkbox" />Incluir inativos</label>
        <div className="form-actions"><button className="button-secondary" type="submit">Aplicar filtros</button></div>
      </form>

      {isAdmin && showForm && (
        <form className="panel panel--operation form-grid" onSubmit={handleProductSubmit}>
          <h2>{editingProduct ? 'Editar produto' : 'Novo produto'}</h2>
          <label>SKU<input maxLength="64" onChange={(event) => updateForm('sku', event.target.value)} required value={form.sku} /></label>
          <label>Nome<input maxLength="100" minLength="2" onChange={(event) => updateForm('name', event.target.value)} required value={form.name} /></label>
          <label>Categoria<input maxLength="50" minLength="2" onChange={(event) => updateForm('category', event.target.value)} required value={form.category} /></label>
          {!editingProduct && <label>Quantidade<input min="0" onChange={(event) => updateForm('quantity', event.target.value)} required type="number" value={form.quantity} /></label>}
          <label>Estoque mínimo<input min="0" onChange={(event) => updateForm('minimum_quantity', event.target.value)} required type="number" value={form.minimum_quantity} /></label>
          <label>Preço<input min="0" onChange={(event) => updateForm('price', event.target.value)} required step="0.01" type="number" value={form.price} /></label>
          <label>
            Fornecedor
            <select disabled={saving || loadingSuppliers} onChange={(event) => updateForm('supplier_id', event.target.value)} value={form.supplier_id}>
              <option value="">Sem fornecedor</option>
              {form.supplier_id && !supplierNames.has(Number(form.supplier_id)) && <option value={form.supplier_id}>Fornecedor atual indisponível</option>}
              {suppliers.map((supplier) => <option key={supplier.id} value={supplier.id}>{supplier.name}</option>)}
            </select>
          </label>
          <div className="form-actions">
            <button disabled={saving} type="submit">{saving ? 'Salvando...' : 'Salvar'}</button>
            <button className="button-secondary" disabled={saving} onClick={closeForm} type="button">Cancelar</button>
          </div>
        </form>
      )}

      {message && <p aria-live="polite" className="status-message">{message}</p>}
      {error && <p className="error-message" role="alert">{error}</p>}
      {supplierError && <p className="error-message" role="alert">{supplierError}</p>}
      {loading ? <p aria-live="polite" className="state-message state-message--loading">Carregando produtos...</p> : productsData?.items.length === 0 ? <p className="state-message state-message--empty">Nenhum produto encontrado.</p> : (
        <div className="data-table-wrapper">
          <table className="data-table inventory-table">
            <thead><tr><th>SKU</th><th>Nome</th><th>Categoria</th><th>Quantidade</th><th>Mínimo</th><th>Preço</th><th>Fornecedor</th><th>Status</th><th>Ações</th></tr></thead>
            <tbody>
              {productsData?.items.map((product) => {
                const detailsExpanded = expandedProductIds.has(product.id)
                const lowStock = product.quantity <= product.minimum_quantity
                return (
                  <tr className={`product-row ${detailsExpanded ? 'is-expanded' : ''}`} key={product.id}>
                    <td data-label="SKU"><span className="sku-code">{product.sku}</span></td>
                    <td data-label="Nome"><strong>{product.name}</strong></td>
                    <td className="mobile-secondary" data-label="Categoria" id={`product-${product.id}-category`}>{product.category}</td>
                    <td data-label="Quantidade">
                      <span className={`quantity-value ${lowStock ? 'is-low' : ''}`}>{product.quantity}</span>
                      <span className="mobile-quantity-summary"> atual · mínimo {product.minimum_quantity}</span>
                    </td>
                    <td className="desktop-only-cell" data-label="Mínimo">{product.minimum_quantity}</td>
                    <td className="mobile-secondary" data-label="Preço" id={`product-${product.id}-price`}>{formatCurrency(product.price)}</td>
                    <td className="mobile-secondary" data-label="Fornecedor" id={`product-${product.id}-supplier`}>{product.supplier_id === null ? 'Sem fornecedor' : supplierNames.get(product.supplier_id) || 'Fornecedor indisponível'}</td>
                    <td data-label="Status"><span className={`status-badge ${product.is_active ? 'status-badge--active' : 'status-badge--inactive'}`}>{product.is_active ? 'Ativo' : 'Inativo'}</span></td>
                    <td data-label="Ações">
                      <div className="inline-actions">
                        <button aria-controls={`product-${product.id}-category product-${product.id}-price product-${product.id}-supplier`} aria-expanded={detailsExpanded} className="mobile-details-toggle button-secondary" onClick={() => toggleProductDetails(product.id)} type="button">{detailsExpanded ? 'Ocultar detalhes' : 'Ver detalhes'}</button>
                        {isAdmin && (product.is_active ? (
                          <>
                            <button className="button-secondary" disabled={processingProductId === product.id} onClick={() => openEditProduct(product)} type="button">Editar</button>
                            <button className="button-danger" disabled={processingProductId === product.id} onClick={() => handleDeactivate(product)} type="button">{processingProductId === product.id ? 'Inativando...' : 'Inativar'}</button>
                          </>
                        ) : <button className="button-positive" disabled={processingProductId === product.id} onClick={() => handleReactivate(product)} type="button">{processingProductId === product.id ? 'Reativando...' : 'Reativar'}</button>)}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {productsData && <div className="pagination"><button disabled={page <= 1 || loading} onClick={() => setPage((current) => Math.max(1, current - 1))} type="button">Anterior</button><span>Página {productsData.page} de {productsData.pages}</span><button disabled={page >= productsData.pages || loading} onClick={() => setPage((current) => current + 1)} type="button">Próxima</button></div>}
    </div>
  )
}

export default ProductsPage
