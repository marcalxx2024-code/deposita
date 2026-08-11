import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getLowStockProducts } from '../services/products.js'

const pageSize = 20

function LowStockPage() {
  const [products, setProducts] = useState([])
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

  function toggleProductDetails(productId) {
    setExpandedProductIds((current) => {
      const next = new Set(current)
      if (next.has(productId)) next.delete(productId)
      else next.add(productId)
      return next
    })
  }

  return (
    <div className="page">
      <div className="page-header"><h1>Estoque baixo</h1><Link to="/movements">Registrar entrada</Link></div>
      {error && <p className="error-message" role="alert">{error}</p>}
      {loading ? <p>Carregando...</p> : products.length === 0 ? <p>Nenhum produto com estoque baixo.</p> : <div className="data-table-wrapper"><table className="data-table"><thead><tr><th>SKU</th><th>Nome</th><th>Categoria</th><th>Quantidade</th><th>Mínimo</th><th>Falta</th><th>Fornecedor</th></tr></thead><tbody>{products.map((product) => { const detailsExpanded = expandedProductIds.has(product.id); return <tr className={`low-stock-row ${detailsExpanded ? 'is-expanded' : ''}`} key={product.id}><td data-label="SKU">{product.sku}</td><td data-label="Nome">{product.name}</td><td className="mobile-secondary" data-label="Categoria">{product.category}</td><td data-label="Quantidade">{product.quantity}</td><td data-label="Mínimo">{product.minimum_quantity}</td><td data-label="Falta">{Math.max(0, product.minimum_quantity - product.quantity)}</td><td className="mobile-details-cell" data-label="Fornecedor"><span className="mobile-secondary-content">{product.supplier_id ?? '—'}</span><button aria-expanded={detailsExpanded} className="mobile-details-toggle button-secondary" onClick={() => toggleProductDetails(product.id)} type="button">{detailsExpanded ? 'Ocultar detalhes' : 'Ver detalhes'}</button></td></tr> })}</tbody></table></div>}
      <div className="pagination"><button disabled={skip === 0 || loading} onClick={() => setSkip((current) => Math.max(0, current - pageSize))} type="button">Anterior</button><span>Exibindo a partir do item {skip + 1}</span><button disabled={products.length < pageSize || loading} onClick={() => setSkip((current) => current + pageSize)} type="button">Próxima</button></div>
    </div>
  )
}

export default LowStockPage
