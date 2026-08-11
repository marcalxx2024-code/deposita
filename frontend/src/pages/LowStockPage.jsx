import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { getLowStockProducts } from '../services/products.js'
import { listSuppliers } from '../services/suppliers.js'

const pageSize = 20

function LowStockPage() {
  const [products, setProducts] = useState([])
  const [suppliers, setSuppliers] = useState([])
  const [skip, setSkip] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [expandedProductIds, setExpandedProductIds] = useState(new Set())

  const loadProducts = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setProducts(await getLowStockProducts({ skip, limit: pageSize }))
    } catch (requestError) {
      setError(requestError.message || 'Não foi possível carregar o estoque baixo.')
    } finally {
      setLoading(false)
    }
  }, [skip])

  useEffect(() => {
    loadProducts()
  }, [loadProducts])

  useEffect(() => {
    let active = true
    listSuppliers({ skip: 0, limit: 100 })
      .then((data) => {
        if (active) setSuppliers(data)
      })
      .catch((requestError) => {
        if (active) setError(requestError.message || 'Não foi possível carregar os fornecedores.')
      })
    return () => {
      active = false
    }
  }, [])

  const supplierNames = useMemo(
    () => new Map(suppliers.map((supplier) => [supplier.id, supplier.name])),
    [suppliers],
  )

  function toggleProductDetails(productId) {
    setExpandedProductIds((current) => {
      const next = new Set(current)
      if (next.has(productId)) next.delete(productId)
      else next.add(productId)
      return next
    })
  }

  return (
    <div className="page low-stock-page">
      <div className="page-header alert-page-header">
        <div><span className="eyebrow">Painel de alerta</span><h1>Estoque baixo</h1><p>Itens abaixo do nível mínimo exigem reposição.</p></div>
        <Link className="button-link button-positive" to="/movements?type=entry">Registrar entrada</Link>
      </div>
      {error && <p className="error-message" role="alert">{error}</p>}
      {loading ? <p aria-live="polite" className="state-message state-message--loading">Carregando alertas...</p> : products.length === 0 ? <p className="state-message state-message--empty state-message--healthy">Nenhum produto com estoque baixo.</p> : (
        <div className="data-table-wrapper low-stock-table-wrapper">
          <table className="data-table low-stock-table">
            <thead><tr><th>SKU</th><th>Nome</th><th>Categoria</th><th>Nível do estoque</th><th>Atual</th><th>Mínimo</th><th>Falta</th><th>Fornecedor</th><th>Ação</th></tr></thead>
            <tbody>{products.map((product) => {
              const detailsExpanded = expandedProductIds.has(product.id)
              const missing = Math.max(0, product.minimum_quantity - product.quantity)
              return (
                <tr className={`low-stock-row ${detailsExpanded ? 'is-expanded' : ''}`} key={product.id}>
                  <td data-label="SKU"><span className="sku-code">{product.sku}</span></td>
                  <td data-label="Nome"><strong>{product.name}</strong></td>
                  <td className="mobile-secondary" data-label="Categoria">{product.category}</td>
                  <td className="stock-level-cell" data-label="Nível do estoque"><meter aria-label={`Estoque atual: ${product.quantity} de um mínimo de ${product.minimum_quantity}`} max={Math.max(product.minimum_quantity, 1)} min="0" value={Math.min(product.quantity, product.minimum_quantity)}>{product.quantity} de {product.minimum_quantity}</meter></td>
                  <td data-label="Atual"><span className="quantity-value is-low">{product.quantity}</span></td>
                  <td data-label="Mínimo">{product.minimum_quantity}</td>
                  <td data-label="Falta"><strong className="missing-value">{missing}</strong></td>
                  <td className="mobile-details-cell" data-label="Fornecedor"><span className="mobile-secondary-content" id={`low-stock-${product.id}-supplier`}>{product.supplier_id === null ? 'Sem fornecedor' : supplierNames.get(product.supplier_id) || 'Fornecedor indisponível'}</span><button aria-controls={`low-stock-${product.id}-supplier`} aria-expanded={detailsExpanded} className="mobile-details-toggle button-secondary" onClick={() => toggleProductDetails(product.id)} type="button">{detailsExpanded ? 'Ocultar detalhes' : 'Ver detalhes'}</button></td>
                  <td data-label="Ação"><Link className="table-action-link" to={`/movements?product=${product.id}&type=entry`}>Registrar entrada</Link></td>
                </tr>
              )
            })}</tbody>
          </table>
        </div>
      )}
      <div className="pagination"><button disabled={skip === 0 || loading} onClick={() => setSkip((current) => Math.max(0, current - pageSize))} type="button">Anterior</button><span>Exibindo a partir do item {skip + 1}</span><button disabled={products.length < pageSize || loading} onClick={() => setSkip((current) => current + pageSize)} type="button">Próxima</button></div>
    </div>
  )
}

export default LowStockPage
