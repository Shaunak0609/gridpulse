import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { login, isAuthenticated, loading } = useAuth()
  const navigate = useNavigate()

  if (loading) return null
  if (isAuthenticated) return <Navigate to="/" replace />

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      await login({ email, password })
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-enter min-h-[70vh] flex items-center justify-center">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <p className="text-red-500 text-xs font-semibold tracking-widest uppercase mb-3">
            Welcome back
          </p>
          <h1 className="text-3xl font-black text-white tracking-tight">
            Sign in to Grid<span className="text-red-500">Pulse</span>
          </h1>
          <p className="text-gray-500 text-sm mt-2">
            Don't have an account?{' '}
            <Link to="/signup" className="text-red-400 hover:text-red-300 transition-colors">
              Sign up
            </Link>
          </p>
        </div>

        {/* Card */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8">
          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            <div>
              <label className="block text-xs text-gray-400 uppercase tracking-widest mb-2">
                Email
              </label>
              <input
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white text-sm placeholder-gray-600 focus:outline-none focus:border-red-500 transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs text-gray-400 uppercase tracking-widest mb-2">
                Password
              </label>
              <input
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white text-sm placeholder-gray-600 focus:outline-none focus:border-red-500 transition-colors"
              />
            </div>

            {error && (
              <div className="bg-red-950/50 border border-red-800 rounded-lg px-4 py-3">
                <p className="text-red-400 text-sm">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-red-600 hover:bg-red-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-sm py-3 rounded-lg transition-colors duration-200 mt-1"
            >
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
