import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.js'
import AppLayout from '../layouts/AppLayout.jsx'
import DashboardPage from '../pages/DashboardPage.jsx'
import LoginPage from '../pages/LoginPage.jsx'
import MovementsPage from '../pages/MovementsPage.jsx'
import ProductsPage from '../pages/ProductsPage.jsx'
import LowStockPage from '../pages/LowStockPage.jsx'
import SuppliersPage from '../pages/SuppliersPage.jsx'
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
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/products" element={<ProductsPage />} />
          <Route path="/movements" element={<MovementsPage />} />
          <Route path="/suppliers" element={<SuppliersPage />} />
          <Route path="/low-stock" element={<LowStockPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default AppRoutes
