import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.js'
import { waitForApi } from '../services/health.js'

function LoginPage() {
  const { authenticated, login, loginDemo } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [preparingDemo, setPreparingDemo] = useState(false)

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

  async function handleDemoLogin() {
    setError('')
    setSubmitting(true)
    setPreparingDemo(true)

    try {
      const apiAvailable = await waitForApi()
      if (!apiAvailable) {
        throw new Error(
          'A demonstração ainda não está disponível. Aguarde um momento e tente novamente.',
        )
      }
      await loginDemo()
      navigate('/dashboard', { replace: true })
    } catch (requestError) {
      setError(
        requestError.message ||
          'Não foi possível iniciar a demonstração. Aguarde um momento e tente novamente.',
      )
    } finally {
      setPreparingDemo(false)
      setSubmitting(false)
    }
  }

  return (
    <main className="login-page">
      <div className="login-shell">
        <div aria-hidden="true" className="login-visual">
          <div className="login-warehouse">
            <span className="login-warehouse__light" />
            <span className="login-warehouse__shelf login-warehouse__shelf--left" />
            <span className="login-warehouse__shelf login-warehouse__shelf--right" />
            <span className="login-warehouse__pallet" />
          </div>
          <p>Organize. Movimente. Controle.</p>
        </div>
        <form className="login-form" onSubmit={handleSubmit}>
          <div className="login-brand">
            <span aria-hidden="true" className="brand-mark brand-mark--large"><span /></span>
            <div><strong>Deposita</strong><span>Inventory Management System</span></div>
          </div>
          <div className="login-form__heading">
            <span className="eyebrow">Acesso do operador</span>
            <h1>Entrar</h1>
            <p>Use suas credenciais para acessar o inventário.</p>
          </div>
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
          {preparingDemo && (
            <p aria-live="polite" className="state-message state-message--loading">
              Preparando a demonstração. Isso pode levar alguns segundos.
            </p>
          )}
          <button disabled={submitting} type="submit">
            {submitting ? 'Entrando...' : 'Entrar no sistema'}
          </button>
          <button
            className="button-secondary"
            disabled={submitting}
            onClick={handleDemoLogin}
            type="button"
          >
            Entrar na demonstração
          </button>
        </form>
      </div>
    </main>
  )
}

export default LoginPage
