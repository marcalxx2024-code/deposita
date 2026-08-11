import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getDashboardSummary } from '../services/dashboard.js'
import { getRecentMovements } from '../services/movements.js'
import { getLowStockProducts } from '../services/products.js'
import { formatDateTime } from '../utils/formatters.js'

function DashboardPage() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true

    async function loadDashboard() {
      try {
        const [summary, lowStockProducts, recentMovements] = await Promise.all([
          getDashboardSummary(),
          getLowStockProducts({ skip: 0, limit: 5 }),
          getRecentMovements({ skip: 0, limit: 5 }),
        ])
        if (active) setData({ summary, lowStockProducts, recentMovements })
      } catch (requestError) {
        if (active) setError(requestError.message || 'Não foi possível carregar o dashboard.')
      } finally {
        if (active) setLoading(false)
      }
    }

    loadDashboard()

    return () => {
      active = false
    }
  }, [])

  if (loading) {
    return <p>Carregando...</p>
  }

  if (error) {
    return <p className="dashboard-error">{error}</p>
  }

  const { summary, lowStockProducts, recentMovements } = data

  return (
    <div className="dashboard-page">
      <h1>Dashboard</h1>

      <section className="dashboard-grid" aria-label="Resumo do estoque">
        <article className="dashboard-card">
          <span>Produtos ativos</span>
          <strong>{summary.total_products}</strong>
        </article>
        <article className="dashboard-card">
          <span>Quantidade em estoque</span>
          <strong>{summary.total_stock_quantity}</strong>
        </article>
        <article className="dashboard-card">
          <span>Produtos com estoque baixo</span>
          <strong>{summary.low_stock_products}</strong>
        </article>
      </section>

      <section className="dashboard-section">
        <div className="dashboard-section__heading">
          <h2>Estoque baixo</h2>
          <Link to="/low-stock">Ver todos</Link>
        </div>
        {lowStockProducts.length === 0 ? (
          <p>Nenhum produto com estoque baixo.</p>
        ) : (
          <ul className="dashboard-list">
            {lowStockProducts.map((product) => (
              <li key={product.id}>
                <strong>{product.name}</strong>
                <span>SKU: {product.sku}</span>
                <span>
                  Estoque: {product.quantity} / mínimo: {product.minimum_quantity}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="dashboard-section">
        <div className="dashboard-section__heading">
          <h2>Movimentações recentes</h2>
          <Link to="/movements">Ver todas</Link>
        </div>
        {recentMovements.length === 0 ? (
          <p>Nenhuma movimentação recente.</p>
        ) : (
          <ul className="dashboard-list">
            {recentMovements.map((movement) => (
              <li key={movement.id}>
                <strong>
                  {movement.movement_type === 'entry' ? 'Entrada' : 'Saída'}: {movement.quantity}
                </strong>
                <span>Produto #{movement.product_id}</span>
                <span>{formatDateTime(movement.created_at)}</span>
                {movement.note && <span>{movement.note}</span>}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}

export default DashboardPage
