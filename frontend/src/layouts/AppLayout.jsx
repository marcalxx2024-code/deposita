import { Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.js'

function AppLayout() {
  const { logout, user } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="app-layout">
      <header className="app-layout__header">
        <span>{user?.username}</span>
        <button type="button" onClick={handleLogout}>
          Sair
        </button>
      </header>
      <main className="app-layout__content">
        <Outlet />
      </main>
    </div>
  )
}

export default AppLayout
