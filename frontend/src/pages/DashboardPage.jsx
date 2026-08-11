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
    return <p aria-live="polite" className="state-message state-message--loading">Carregando dashboard...</p>
  }

  if (error) {
    return <p className="dashboard-error" role="alert">{error}</p>
  }

  const { summary, lowStockProducts, recentMovements } = data

  return (
    <div className="dashboard-page">
      <header className="dashboard-hero">
        <div>
          <span className="eyebrow">Central de operações</span>
          <h1>Dashboard</h1>
          <p>Visão geral do seu depósito em tempo real.</p>
        </div>
        <div aria-hidden="true" className="warehouse-scene">
          <span className="warehouse-scene__shelf warehouse-scene__shelf--one" />
          <span className="warehouse-scene__shelf warehouse-scene__shelf--two" />
          <span className="warehouse-scene__crate warehouse-scene__crate--one" />
          <span className="warehouse-scene__crate warehouse-scene__crate--two" />
          <span className="warehouse-scene__floor" />
        </div>
      </header>

      <section className="dashboard-grid" aria-label="Resumo do estoque">
        <article className="dashboard-card dashboard-card--products">
          <span aria-hidden="true" className="dashboard-card__icon">□</span>
          <span>Produtos ativos</span>
          <strong>{summary.total_products}</strong>
          <small>itens catalogados</small>
        </article>
        <article className="dashboard-card dashboard-card--stock">
          <span aria-hidden="true" className="dashboard-card__icon">▦</span>
          <span>Quantidade em estoque</span>
          <strong>{summary.total_stock_quantity}</strong>
          <small>unidades disponíveis</small>
        </article>
        <article className="dashboard-card dashboard-card--alert">
          <span aria-hidden="true" className="dashboard-card__icon">!</span>
          <span>Produtos com estoque baixo</span>
          <strong>{summary.low_stock_products}</strong>
          <small>precisam de atenção</small>
        </article>
      </section>

      <section className="dashboard-section dashboard-section--alert">
        <div className="dashboard-section__heading">
          <div>
            <span className="section-kicker">Alerta de inventário</span>
            <h2>Estoque baixo</h2>
          </div>
          <Link className="text-link" to="/low-stock">Ver todos</Link>
        </div>
        {lowStockProducts.length === 0 ? (
          <p className="state-message state-message--empty">Nenhum produto com estoque baixo.</p>
        ) : (
          <ul className="dashboard-list low-stock-list">
            {lowStockProducts.map((product) => (
              <li key={product.id}>
                <span aria-hidden="true" className="item-pixel item-pixel--alert" />
                <span className="dashboard-list__primary">
                  <strong>{product.name}</strong>
                  <span className="sku-code">{product.sku}</span>
                </span>
                <span className="stock-comparison">
                  <span>Atual <strong>{product.quantity}</strong></span>
                  <span>Mínimo <strong>{product.minimum_quantity}</strong></span>
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="dashboard-section dashboard-section--log">
        <div className="dashboard-section__heading">
          <div>
            <span className="section-kicker">Log de eventos</span>
            <h2>Movimentações recentes</h2>
          </div>
          <Link className="text-link" to="/movements">Ver todas</Link>
        </div>
        {recentMovements.length === 0 ? (
          <p className="state-message state-message--empty">Nenhuma movimentação recente.</p>
        ) : (
          <ul className="dashboard-list event-log">
            {recentMovements.map((movement) => {
              const isEntry = movement.movement_type === 'entry'
              return (
                <li className={isEntry ? 'is-entry' : 'is-exit'} key={movement.id}>
                  <span aria-hidden="true" className="movement-sign">{isEntry ? '+' : '−'}</span>
                  <span className="dashboard-list__primary">
                    <strong>{isEntry ? 'Entrada' : 'Saída'} de {movement.quantity}</strong>
                    <span>Produto #{movement.product_id}{movement.note ? ` · ${movement.note}` : ''}</span>
                  </span>
                  <time dateTime={movement.created_at}>{formatDateTime(movement.created_at)}</time>
                </li>
              )
            })}
          </ul>
        )}
      </section>
    </div>
  )
}

export default DashboardPage
