import { useCallback, useEffect, useState } from 'react'
import { createStockMovement, getRecentMovements } from '../services/movements.js'
import { listProducts } from '../services/products.js'
import { formatDateTime } from '../utils/formatters.js'

const pageSize = 20

function MovementsPage() {
  const [movements, setMovements] = useState([])
  const [products, setProducts] = useState([])
  const [skip, setSkip] = useState(0)
  const [form, setForm] = useState({ productId: '', movementType: 'entry', quantity: '', note: '' })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [expandedMovementIds, setExpandedMovementIds] = useState(new Set())

  const loadMovements = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setMovements(await getRecentMovements({ skip, limit: pageSize }))
    } catch (requestError) {
      setError(requestError.message || 'Não foi possível carregar as movimentações.')
    } finally {
      setLoading(false)
    }
  }, [skip])

  const loadProducts = useCallback(async () => {
    try {
      const data = await listProducts({ page: 1, pageSize: 100 })
      setProducts(data.items)
    } catch (requestError) {
      setError(requestError.message || 'Não foi possível carregar os produtos.')
    }
  }, [])

  useEffect(() => {
    loadMovements()
  }, [loadMovements])

  useEffect(() => {
    loadProducts()
  }, [loadProducts])

  function toggleMovementDetails(movementId) {
    setExpandedMovementIds((current) => {
      const next = new Set(current)
      if (next.has(movementId)) next.delete(movementId)
      else next.add(movementId)
      return next
    })
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setMessage('')
    try {
      await createStockMovement(Number(form.productId), form.movementType, {
        quantity: Number(form.quantity),
        note: form.note || null,
      })
      setMessage(`${form.movementType === 'entry' ? 'Entrada' : 'Saída'} registrada com sucesso.`)
      setForm({ productId: '', movementType: 'entry', quantity: '', note: '' })
      setSkip(0)
      await Promise.all([loadMovements(), loadProducts()])
    } catch (requestError) {
      setError(requestError.message || 'Não foi possível registrar a movimentação.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <span className="eyebrow">Log de inventário</span>
          <h1>Movimentações</h1>
        </div>
      </div>
      <form className={`panel panel--operation form-grid movement-form movement-form--${form.movementType}`} onSubmit={handleSubmit}>
        <div className="operation-heading">
          <span aria-hidden="true" className="operation-heading__sign">{form.movementType === 'entry' ? '+' : '−'}</span>
          <div><span className="section-kicker">Painel de operação</span><h2>Registrar movimentação</h2></div>
        </div>
        <label>Produto<select disabled={saving || products.length === 0} onChange={(event) => setForm((current) => ({ ...current, productId: event.target.value }))} required value={form.productId}><option value="">Selecione um produto</option>{products.map((product) => <option key={product.id} value={product.id}>{product.sku} — {product.name} ({product.quantity})</option>)}</select></label>
        <label>Tipo<select disabled={saving} onChange={(event) => setForm((current) => ({ ...current, movementType: event.target.value }))} value={form.movementType}><option value="entry">Entrada</option><option value="exit">Saída</option></select></label>
        <label>Quantidade<input disabled={saving} min="1" onChange={(event) => setForm((current) => ({ ...current, quantity: event.target.value }))} required type="number" value={form.quantity} /></label>
        <label>Observação (opcional)<textarea disabled={saving} maxLength="255" onChange={(event) => setForm((current) => ({ ...current, note: event.target.value }))} value={form.note} /></label>
        <div className="form-actions"><button className={form.movementType === 'entry' ? 'button-positive' : 'button-danger'} disabled={saving || products.length === 0} type="submit">{saving ? 'Registrando...' : `Registrar ${form.movementType === 'entry' ? 'entrada' : 'saída'}`}</button></div>
      </form>

      {message && <p aria-live="polite" className="status-message">{message}</p>}
      {error && <p className="error-message" role="alert">{error}</p>}
      {loading ? <p aria-live="polite" className="state-message state-message--loading">Carregando movimentações...</p> : movements.length === 0 ? <p className="state-message state-message--empty">Nenhuma movimentação encontrada.</p> : (
        <div className="data-table-wrapper event-table-wrapper">
          <table className="data-table event-table">
            <thead><tr><th>Tipo</th><th>Quantidade</th><th>Produto</th><th>Data</th><th>Observação</th></tr></thead>
            <tbody>{movements.map((movement) => {
              const detailsExpanded = expandedMovementIds.has(movement.id)
              const isEntry = movement.movement_type === 'entry'
              return (
                <tr className={`movement-row ${isEntry ? 'is-entry' : 'is-exit'} ${detailsExpanded ? 'is-expanded' : ''}`} key={movement.id}>
                  <td data-label="Tipo"><span className={`movement-badge ${isEntry ? 'movement-badge--entry' : 'movement-badge--exit'}`}><span aria-hidden="true">{isEntry ? '+' : '−'}</span>{isEntry ? 'Entrada' : 'Saída'}</span></td>
                  <td data-label="Quantidade"><strong className="quantity-value">{isEntry ? '+' : '−'}{movement.quantity}</strong></td>
                  <td data-label="Produto"><span className="sku-code">#{movement.product_id}</span></td>
                  <td data-label="Data"><time dateTime={movement.created_at}>{formatDateTime(movement.created_at)}</time></td>
                  <td className="mobile-details-cell" data-label="Observação"><span className="mobile-secondary-content">{movement.note || '—'}</span>{movement.note && <button aria-expanded={detailsExpanded} className="mobile-details-toggle button-secondary" onClick={() => toggleMovementDetails(movement.id)} type="button">{detailsExpanded ? 'Ocultar detalhes' : 'Ver detalhes'}</button>}</td>
                </tr>
              )
            })}</tbody>
          </table>
        </div>
      )}
      <div className="pagination"><button disabled={skip === 0 || loading} onClick={() => setSkip((current) => Math.max(0, current - pageSize))} type="button">Anterior</button><span>Exibindo a partir do item {skip + 1}</span><button disabled={movements.length < pageSize || loading} onClick={() => setSkip((current) => current + pageSize)} type="button">Próxima</button></div>
    </div>
  )
}

export default MovementsPage
