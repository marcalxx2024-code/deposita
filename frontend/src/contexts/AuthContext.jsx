import { useEffect, useMemo, useState } from 'react'
import {
  getCurrentUser,
  isAuthenticated,
  isDemoSession,
  login as authenticate,
  loginDemo as authenticateDemo,
  logout as clearToken,
} from '../services/auth.js'
import { AuthContext } from './authContext.js'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [demoSession, setDemoSession] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true

    function handleUnauthorized() {
      clearToken()
      if (active) {
        setUser(null)
        setDemoSession(false)
      }
    }

    async function restoreSession() {
      if (!isAuthenticated()) {
        clearToken()
        if (active) setLoading(false)
        return
      }

      try {
        const currentUser = await getCurrentUser()
        if (active) {
          setUser(currentUser)
          setDemoSession(isDemoSession())
        }
      } catch (error) {
        if (error.status === 401) clearToken()
        if (active) {
          setUser(null)
          setDemoSession(false)
        }
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

  async function restoreAuthenticatedUser() {
    try {
      const currentUser = await getCurrentUser()
      setUser(currentUser)
      setDemoSession(isDemoSession())
    } catch (error) {
      clearToken()
      setUser(null)
      setDemoSession(false)
      throw error
    }
  }

  async function login(credentials) {
    await authenticate(credentials)
    await restoreAuthenticatedUser()
  }

  async function loginDemo() {
    await authenticateDemo()
    await restoreAuthenticatedUser()
  }

  function logout() {
    clearToken()
    setUser(null)
    setDemoSession(false)
  }

  const value = useMemo(
    () => ({
      user,
      isDemo: demoSession,
      loading,
      authenticated: Boolean(user),
      login,
      loginDemo,
      logout,
    }),
    [user, demoSession, loading],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
