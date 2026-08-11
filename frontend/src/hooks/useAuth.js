import { useContext } from 'react'
import { AuthContext } from '../contexts/authContext.js'

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === null) {
    throw new Error('useAuth must be used within an AuthProvider.')
  }
  return context
}
