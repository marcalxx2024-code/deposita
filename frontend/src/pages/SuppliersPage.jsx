import { useCallback, useEffect, useState } from 'react'
import {
  createSupplier,
  deleteSupplier,
  listSuppliers,
  updateSupplier,
} from '../services/suppliers.js'
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
  const [suppliers, setSuppliers] = useState([])
  const [skip, setSkip] = useState(0)
  const [form, setForm] = useState(emptySupplier)
  const [editingSupplier, setEditingSupplier] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

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
      await loadSuppliers()
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
    try {
      await deleteSupplier(supplier.id)
      setMessage('Fornecedor excluído com sucesso.')
      await loadSuppliers()
    } catch (requestError) {
      setError(requestError.message || 'Não foi possível excluir o fornecedor.')
    }
  }

  return (
    <div className="page">
      <div className="page-header"><h1>Fornecedores</h1><button onClick={openNewSupplier} type="button">Novo fornecedor</button></div>

      {showForm && <form className="panel form-grid" onSubmit={handleSubmit}>
        <h2>{editingSupplier ? 'Editar fornecedor' : 'Novo fornecedor'}</h2>
        <label>Nome<input maxLength="100" minLength="2" onChange={(event) => updateForm('name', event.target.value)} required value={form.name} /></label>
        <label>Contato<input maxLength="100" onChange={(event) => updateForm('contact_name', event.target.value)} value={form.contact_name} /></label>
        <label>Telefone<input maxLength="30" onChange={(event) => updateForm('phone', event.target.value)} value={form.phone} /></label>
        <label>Email<input maxLength="255" onChange={(event) => updateForm('email', event.target.value)} type="email" value={form.email} /></label>
        <div className="form-actions"><button disabled={saving} type="submit">{saving ? 'Salvando...' : 'Salvar'}</button><button disabled={saving} onClick={closeForm} type="button">Cancelar</button></div>
      </form>}

      {message && <p className="status-message">{message}</p>}
      {error && <p className="error-message" role="alert">{error}</p>}
      {loading ? <p>Carregando...</p> : suppliers.length === 0 ? <p>Nenhum fornecedor encontrado.</p> : <div className="data-table-wrapper"><table className="data-table"><thead><tr><th>Nome</th><th>Contato</th><th>Telefone</th><th>Email</th><th>Criado em</th><th>Ações</th></tr></thead><tbody>{suppliers.map((supplier) => <tr className="supplier-row" key={supplier.id}><td data-label="Nome">{supplier.name}</td><td data-label="Contato">{supplier.contact_name || '—'}</td><td data-label="Telefone">{supplier.phone || '—'}</td><td data-label="Email">{supplier.email || '—'}</td><td data-label="Criado em">{formatDateTime(supplier.created_at)}</td><td data-label="Ações"><div className="inline-actions"><button onClick={() => openEditSupplier(supplier)} type="button">Editar</button><button className="button-danger" onClick={() => handleDelete(supplier)} type="button">Excluir</button></div></td></tr>)}</tbody></table></div>}
      <div className="pagination"><button disabled={skip === 0 || loading} onClick={() => setSkip((current) => Math.max(0, current - pageSize))} type="button">Anterior</button><span>Exibindo a partir do item {skip + 1}</span><button disabled={suppliers.length < pageSize || loading} onClick={() => setSkip((current) => current + pageSize)} type="button">Próxima</button></div>
    </div>
  )
}

export default SuppliersPage
