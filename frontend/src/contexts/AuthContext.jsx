import { useEffect, useMemo, useState } from 'react'
import {
  getCurrentUser,
  isAuthenticated,
  login as authenticate,
  logout as clearToken,
} from '../services/auth.js'
import { AuthContext } from './authContext.js'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true

    function handleUnauthorized() {
      clearToken()
      if (active) setUser(null)
    }

    async function restoreSession() {
      if (!isAuthenticated()) {
        if (active) setLoading(false)
        return
      }

      try {
        const currentUser = await getCurrentUser()
        if (active) setUser(currentUser)
      } catch (error) {
        if (error.status === 401) clearToken()
        if (active) setUser(null)
      } finally {
        if (active) setLoading(false)
      }
    }

    restoreSession()
    window.addEventListener('deposita:unauthorized', handleUnauthorized)

    return () => {
      active = false
      window.removeEventListener('deposita:unauthorized', handleUnauthorized)
    }
  }, [])

  async function login(credentials) {
    await authenticate(credentials)
    try {
      const currentUser = await getCurrentUser()
      setUser(currentUser)
    } catch (error) {
      clearToken()
      setUser(null)
      throw error
    }
  }

  function logout() {
    clearToken()
    setUser(null)
  }

  const value = useMemo(
    () => ({
      user,
      loading,
      authenticated: Boolean(user),
      login,
      logout,
    }),
    [user, loading],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
