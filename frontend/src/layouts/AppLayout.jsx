import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.js'

const navigationItems = [
  { to: '/dashboard', label: 'Dashboard', icon: '▦' },
  { to: '/products', label: 'Produtos', icon: '□' },
  { to: '/movements', label: 'Movimentações', icon: '↕' },
  { to: '/suppliers', label: 'Fornecedores', icon: '◇' },
  { to: '/low-stock', label: 'Estoque baixo', icon: '!' },
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
        <div className="brand-lockup">
          <span aria-hidden="true" className="brand-mark"><span /></span>
          <span className="brand-lockup__text">
            <strong>Deposita</strong>
            <small>Inventory System</small>
          </span>
        </div>
        <div className="app-layout__topbar">
          <button
            aria-controls="main-navigation"
            aria-expanded={menuOpen}
            className="menu-toggle"
            onClick={() => setMenuOpen((current) => !current)}
            type="button"
          >
            <span aria-hidden="true" className="menu-toggle__icon">☰</span>
            Menu
          </button>
          <span className="app-layout__mobile-title">Deposita</span>
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
              <span aria-hidden="true" className="nav-icon">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="app-layout__user">
          <div className="user-panel">
            <span aria-hidden="true" className="user-panel__indicator" />
            <span>
              <small>Operador</small>
              <strong>{user?.username}</strong>
            </span>
          </div>
          <button className="button-ghost logout-button" type="button" onClick={handleLogout}>
            Sair
          </button>
        </div>
      </header>
      <main className="app-layout__content">
        <Outlet />
      </main>
    </div>
  )
}

export default AppLayout
