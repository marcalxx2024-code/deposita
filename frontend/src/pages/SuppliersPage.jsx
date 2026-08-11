import { useCallback, useEffect, useState } from 'react'
import {
  createSupplier,
  deleteSupplier,
  listSuppliers,
  updateSupplier,
} from '../services/suppliers.js'
import { useAuth } from '../hooks/useAuth.js'
import { formatDateTime } from '../utils/formatters.js'

const pageSize = 20
const emptySupplier = { name: '', contact_name: '', phone: '', email: '' }

function toSupplierForm(supplier) {
  return {
    name: supplier.name,
    contact_name: supplier.contact_name || '',
    phone: supplier.phone || '',
    email: supplier.email || '',
  }
}

function SuppliersPage() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [suppliers, setSuppliers] = useState([])
  const [skip, setSkip] = useState(0)
  const [form, setForm] = useState(emptySupplier)
  const [editingSupplier, setEditingSupplier] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [deletingSupplierId, setDeletingSupplierId] = useState(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [expandedSupplierIds, setExpandedSupplierIds] = useState(new Set())

  const loadSuppliers = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setSuppliers(await listSuppliers({ skip, limit: pageSize }))
    } catch (requestError) {
      setError(requestError.message || 'Não foi possível carregar os fornecedores.')
    } finally {
      setLoading(false)
    }
  }, [skip])

  useEffect(() => {
    loadSuppliers()
  }, [loadSuppliers])

  function updateForm(field, value) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  function openNewSupplier() {
    setEditingSupplier(null)
    setForm(emptySupplier)
    setError('')
    setMessage('')
    setShowForm(true)
  }

  function openEditSupplier(supplier) {
    setEditingSupplier(supplier)
    setForm(toSupplierForm(supplier))
    setError('')
    setMessage('')
    setShowForm(true)
  }

  function closeForm() {
    setEditingSupplier(null)
    setForm(emptySupplier)
    setShowForm(false)
  }

  function toggleSupplierDetails(supplierId) {
    setExpandedSupplierIds((current) => {
      const next = new Set(current)
      if (next.has(supplierId)) next.delete(supplierId)
      else next.add(supplierId)
      return next
    })
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setMessage('')
    const supplierData = {
      name: form.name,
      contact_name: form.contact_name || null,
      phone: form.phone || null,
      email: form.email || null,
    }

    const shouldResetPagination = !editingSupplier && skip !== 0

    try {
      if (editingSupplier) {
        await updateSupplier(editingSupplier.id, supplierData)
        setMessage('Fornecedor atualizado com sucesso.')
      } else {
        await createSupplier(supplierData)
        setMessage('Fornecedor criado com sucesso.')
        setSkip(0)
      }
      closeForm()
      if (!shouldResetPagination) await loadSuppliers()
    } catch (requestError) {
      setError(requestError.message || 'Não foi possível salvar o fornecedor.')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(supplier) {
    if (!window.confirm(`Excluir o fornecedor ${supplier.name}?`)) return
    setError('')
    setMessage('')
    setDeletingSupplierId(supplier.id)
    try {
      await deleteSupplier(supplier.id)
      setMessage('Fornecedor excluído com sucesso.')
      await loadSuppliers()
    } catch (requestError) {
      setError(requestError.message || 'Não foi possível excluir o fornecedor.')
    } finally {
      setDeletingSupplierId(null)
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <div><span className="eyebrow">Rede de abastecimento</span><h1>Fornecedores</h1></div>
        {isAdmin && <button onClick={openNewSupplier} type="button">Novo fornecedor</button>}
      </div>

      {isAdmin && showForm && <form className="panel panel--operation form-grid" onSubmit={handleSubmit}>
        <h2>{editingSupplier ? 'Editar fornecedor' : 'Novo fornecedor'}</h2>
        <label>Nome<input maxLength="100" minLength="2" onChange={(event) => updateForm('name', event.target.value)} required value={form.name} /></label>
        <label>Contato<input maxLength="100" onChange={(event) => updateForm('contact_name', event.target.value)} value={form.contact_name} /></label>
        <label>Telefone<input maxLength="30" onChange={(event) => updateForm('phone', event.target.value)} value={form.phone} /></label>
        <label>Email<input maxLength="255" onChange={(event) => updateForm('email', event.target.value)} type="email" value={form.email} /></label>
        <div className="form-actions"><button disabled={saving} type="submit">{saving ? 'Salvando...' : 'Salvar'}</button><button className="button-secondary" disabled={saving} onClick={closeForm} type="button">Cancelar</button></div>
      </form>}

      {message && <p aria-live="polite" className="status-message">{message}</p>}
      {error && <p className="error-message" role="alert">{error}</p>}
      {loading ? <p aria-live="polite" className="state-message state-message--loading">Carregando fornecedores...</p> : suppliers.length === 0 ? <p className="state-message state-message--empty">Nenhum fornecedor encontrado.</p> : (
        <div className="data-table-wrapper">
          <table className="data-table supplier-table">
            <thead><tr><th>Nome</th><th>Contato</th><th>Telefone</th><th>Email</th><th>Criado em</th><th>Ações</th></tr></thead>
            <tbody>{suppliers.map((supplier) => {
              const detailsExpanded = expandedSupplierIds.has(supplier.id)
              return (
                <tr className={`supplier-row ${detailsExpanded ? 'is-expanded' : ''}`} key={supplier.id}>
                  <td data-label="Nome"><strong>{supplier.name}</strong></td>
                  <td data-label="Contato"><span className="contact-value">{supplier.contact_name || '—'}</span></td>
                  <td className="mobile-secondary" data-label="Telefone" id={`supplier-${supplier.id}-phone`}>{supplier.phone || '—'}</td>
                  <td className="mobile-secondary" data-label="Email" id={`supplier-${supplier.id}-email`}>{supplier.email || '—'}</td>
                  <td className="mobile-secondary" data-label="Criado em" id={`supplier-${supplier.id}-created`}><time dateTime={supplier.created_at}>{formatDateTime(supplier.created_at)}</time></td>
                  <td data-label="Ações"><div className="inline-actions"><button aria-controls={`supplier-${supplier.id}-phone supplier-${supplier.id}-email supplier-${supplier.id}-created`} aria-expanded={detailsExpanded} className="mobile-details-toggle button-secondary" onClick={() => toggleSupplierDetails(supplier.id)} type="button">{detailsExpanded ? 'Ocultar detalhes' : 'Ver detalhes'}</button>{isAdmin && <><button className="button-secondary" disabled={deletingSupplierId === supplier.id} onClick={() => openEditSupplier(supplier)} type="button">Editar</button><button className="button-danger" disabled={deletingSupplierId === supplier.id} onClick={() => handleDelete(supplier)} type="button">{deletingSupplierId === supplier.id ? 'Excluindo...' : 'Excluir'}</button></>}</div></td>
                </tr>
              )
            })}</tbody>
          </table>
        </div>
      )}
      <div className="pagination"><button disabled={skip === 0 || loading} onClick={() => setSkip((current) => Math.max(0, current - pageSize))} type="button">Anterior</button><span>Exibindo a partir do item {skip + 1}</span><button disabled={suppliers.length < pageSize || loading} onClick={() => setSkip((current) => current + pageSize)} type="button">Próxima</button></div>
    </div>
  )
}

export default SuppliersPage
