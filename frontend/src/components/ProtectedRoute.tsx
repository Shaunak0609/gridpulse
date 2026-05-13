import { Navigate } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from '../context/AuthContext'

export default function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, loading } = useAuth()

  // Wait for the token-restore check to finish before deciding anything.
  // Without this, a logged-in user refreshing /profile would briefly see
  // a redirect to /login before the session is restored.
  if (loading) return null

  if (!isAuthenticated) return <Navigate to="/login" replace />

  return <>{children}</>
}
