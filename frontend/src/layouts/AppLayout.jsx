import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.js'

const navigationItems = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/products', label: 'Produtos' },
  { to: '/movements', label: 'Movimentações' },
  { to: '/suppliers', label: 'Fornecedores' },
  { to: '/low-stock', label: 'Estoque baixo' },
]

function AppLayout() {
  const { logout, user } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="app-layout">
      <header className="app-layout__header">
        <div className="app-layout__topbar">
          <button
            aria-controls="main-navigation"
            aria-expanded={menuOpen}
            className="menu-toggle"
            onClick={() => setMenuOpen((current) => !current)}
            type="button"
          >
            Menu
          </button>
          <div className="app-layout__user">
            <span>{user?.username}</span>
            <button className="button-secondary" type="button" onClick={handleLogout}>
              Sair
            </button>
          </div>
        </div>
        <nav
          aria-label="Navegação principal"
          className={`app-layout__nav ${menuOpen ? 'is-open' : ''}`}
          id="main-navigation"
        >
          {navigationItems.map((item) => (
            <NavLink
              className={({ isActive }) => (isActive ? 'is-active' : undefined)}
              key={item.to}
              onClick={() => setMenuOpen(false)}
              to={item.to}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="app-layout__content">
        <Outlet />
      </main>
    </div>
  )
}

export default AppLayout
