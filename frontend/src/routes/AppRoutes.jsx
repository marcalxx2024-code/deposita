import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.js'
import AppLayout from '../layouts/AppLayout.jsx'
import LoginPage from '../pages/LoginPage.jsx'
import PlaceholderPage from '../pages/PlaceholderPage.jsx'
import ProtectedRoute from './ProtectedRoute.jsx'

function AppRoutes() {
  const { loading } = useAuth()

  if (loading) {
    return <main className="loading-state">Carregando...</main>
  }

  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<PlaceholderPage title="Dashboard" />} />
          <Route path="/products" element={<PlaceholderPage title="Produtos" />} />
          <Route path="/movements" element={<PlaceholderPage title="Movimentações" />} />
          <Route path="/suppliers" element={<PlaceholderPage title="Fornecedores" />} />
          <Route path="/low-stock" element={<PlaceholderPage title="Estoque baixo" />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default AppRoutes
