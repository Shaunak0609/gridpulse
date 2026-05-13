import { useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function GoogleCallback() {
  const { loginWithToken } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const didRun = useRef(false)

  useEffect(() => {
    // Strict Mode mounts twice in development — the ref prevents a double login.
    if (didRun.current) return
    didRun.current = true

    const token = searchParams.get('token')

    if (!token) {
      navigate('/login')
      return
    }

    loginWithToken(token)
      .then(() => navigate('/'))
      .catch(() => navigate('/login'))
  }, [])

  return (
    <div className="min-h-[70vh] flex items-center justify-center">
      <p className="text-gray-500 text-sm">Signing you in…</p>
    </div>
  )
}
