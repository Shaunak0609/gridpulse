import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { getCurrentUser, login as apiLogin } from '../services/api'
import type { AuthUser, LoginPayload } from '../types'

const TOKEN_KEY = 'gridpulse_token'

// ─── Shape of everything AuthContext provides ────────────────────────────────

interface AuthContextValue {
  user: AuthUser | null
  token: string | null
  isAuthenticated: boolean
  loading: boolean
  login: (payload: LoginPayload) => Promise<void>
  loginWithToken: (token: string) => Promise<AuthUser>
  refreshUser: () => Promise<void>
  logout: () => void
}

// ─── Create the context ──────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextValue | null>(null)

// ─── Provider ────────────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  // On app load: check if a token is saved and try to restore the session.
  useEffect(() => {
    const saved = localStorage.getItem(TOKEN_KEY)
    if (!saved) {
      setLoading(false)
      return
    }

    getCurrentUser(saved)
      .then(fetchedUser => {
        setToken(saved)
        setUser(fetchedUser)
      })
      .catch(() => {
        // Token is expired or invalid — clear it so the user is logged out.
        localStorage.removeItem(TOKEN_KEY)
      })
      .finally(() => setLoading(false))
  }, [])

  async function login(payload: LoginPayload) {
    const { access_token } = await apiLogin(payload)
    localStorage.setItem(TOKEN_KEY, access_token)

    const fetchedUser = await getCurrentUser(access_token)
    setToken(access_token)
    setUser(fetchedUser)
  }

  // Used after Google sign-in: the token arrives via URL, not from a form submit.
  // Returns the fetched user so the caller can inspect it (e.g. check for missing username).
  async function loginWithToken(incomingToken: string): Promise<AuthUser> {
    const fetchedUser = await getCurrentUser(incomingToken)
    localStorage.setItem(TOKEN_KEY, incomingToken)
    setToken(incomingToken)
    setUser(fetchedUser)
    return fetchedUser
  }

  // Re-fetches /users/me and updates state — call this after updating profile
  // so the navbar and other components immediately reflect the new username.
  async function refreshUser() {
    const saved = token ?? localStorage.getItem(TOKEN_KEY)
    if (!saved) return
    const fetchedUser = await getCurrentUser(saved)
    setUser(fetchedUser)
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY)
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: user !== null,
        loading,
        login,
        loginWithToken,
        refreshUser,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

// ─── Hook ────────────────────────────────────────────────────────────────────

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
