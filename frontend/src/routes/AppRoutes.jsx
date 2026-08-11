import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from '../layouts/AppLayout.jsx'
import PlaceholderPage from '../pages/PlaceholderPage.jsx'

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="/login" element={<PlaceholderPage title="Login" />} />
      <Route element={<AppLayout />}>
        <Route path="/dashboard" element={<PlaceholderPage title="Dashboard" />} />
        <Route path="/products" element={<PlaceholderPage title="Produtos" />} />
        <Route path="/movements" element={<PlaceholderPage title="Movimentações" />} />
        <Route path="/suppliers" element={<PlaceholderPage title="Fornecedores" />} />
        <Route path="/low-stock" element={<PlaceholderPage title="Estoque baixo" />} />
      </Route>
    </Routes>
  )
}

export default AppRoutes
