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
      <h1>Movimentações</h1>
      <form className="panel form-grid" onSubmit={handleSubmit}>
        <h2>Registrar movimentação</h2>
        <label>Produto<select disabled={saving || products.length === 0} onChange={(event) => setForm((current) => ({ ...current, productId: event.target.value }))} required value={form.productId}><option value="">Selecione um produto</option>{products.map((product) => <option key={product.id} value={product.id}>{product.sku} — {product.name} ({product.quantity})</option>)}</select></label>
        <label>Tipo<select disabled={saving} onChange={(event) => setForm((current) => ({ ...current, movementType: event.target.value }))} value={form.movementType}><option value="entry">Entrada</option><option value="exit">Saída</option></select></label>
        <label>Quantidade<input disabled={saving} min="1" onChange={(event) => setForm((current) => ({ ...current, quantity: event.target.value }))} required type="number" value={form.quantity} /></label>
        <label>Observação (opcional)<textarea disabled={saving} maxLength="255" onChange={(event) => setForm((current) => ({ ...current, note: event.target.value }))} value={form.note} /></label>
        <div className="form-actions"><button disabled={saving || products.length === 0} type="submit">{saving ? 'Registrando...' : 'Registrar'}</button></div>
      </form>

      {message && <p className="status-message">{message}</p>}
      {error && <p className="error-message" role="alert">{error}</p>}
      {loading ? <p>Carregando...</p> : movements.length === 0 ? <p>Nenhuma movimentação encontrada.</p> : <div className="data-table-wrapper"><table className="data-table"><thead><tr><th>Tipo</th><th>Quantidade</th><th>Produto</th><th>Data</th><th>Observação</th></tr></thead><tbody>{movements.map((movement) => <tr className="movement-row" key={movement.id}><td data-label="Tipo">{movement.movement_type === 'entry' ? 'Entrada' : 'Saída'}</td><td data-label="Quantidade">{movement.quantity}</td><td data-label="Produto">#{movement.product_id}</td><td data-label="Data">{formatDateTime(movement.created_at)}</td><td data-label="Observação">{movement.note || '—'}</td></tr>)}</tbody></table></div>}
      <div className="pagination"><button disabled={skip === 0 || loading} onClick={() => setSkip((current) => Math.max(0, current - pageSize))} type="button">Anterior</button><span>Exibindo a partir do item {skip + 1}</span><button disabled={movements.length < pageSize || loading} onClick={() => setSkip((current) => current + pageSize)} type="button">Próxima</button></div>
    </div>
  )
}

export default MovementsPage
