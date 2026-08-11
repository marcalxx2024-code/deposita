import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.js'

function LoginPage() {
  const { authenticated, login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (authenticated) {
    return <Navigate to="/dashboard" replace />
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSubmitting(true)

    try {
      await login({ username, password })
      navigate('/dashboard', { replace: true })
    } catch (requestError) {
      setError(requestError.message || 'Não foi possível entrar.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="login-page">
      <form className="login-form" onSubmit={handleSubmit}>
        <h1>Entrar</h1>
        <label>
          Usuário
          <input
            autoComplete="username"
            disabled={submitting}
            onChange={(event) => setUsername(event.target.value)}
            required
            value={username}
          />
        </label>
        <label>
          Senha
          <input
            autoComplete="current-password"
            disabled={submitting}
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
        </label>
        {error && <p className="login-form__error" role="alert">{error}</p>}
        <button disabled={submitting} type="submit">
          {submitting ? 'Entrando...' : 'Entrar'}
        </button>
      </form>
    </main>
  )
}

export default LoginPage
