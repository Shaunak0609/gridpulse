import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { signup } from '../services/api'

export default function Signup() {
  const { login, isAuthenticated, loading } = useAuth()
  const navigate = useNavigate()

  if (loading) return null
  if (isAuthenticated) return <Navigate to="/" replace />

  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [timezone, setTimezone] = useState(
    Intl.DateTimeFormat().resolvedOptions().timeZone
  )
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      await signup({ email, password, username: username || undefined, timezone })
      // Automatically log in after account creation
      await login({ email, password })
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Signup failed.')
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
            Create your account
          </p>
          <h1 className="text-3xl font-black text-white tracking-tight">
            Join Grid<span className="text-red-500">Pulse</span>
          </h1>
          <p className="text-gray-500 text-sm mt-2">
            Already have an account?{' '}
            <Link to="/login" className="text-red-400 hover:text-red-300 transition-colors">
              Sign in
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
                Username <span className="text-gray-600 normal-case tracking-normal">(optional)</span>
              </label>
              <input
                type="text"
                autoComplete="username"
                value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder="e.g. verstappen_fan"
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
                autoComplete="new-password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white text-sm placeholder-gray-600 focus:outline-none focus:border-red-500 transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs text-gray-400 uppercase tracking-widest mb-2">
                Timezone
              </label>
              <input
                type="text"
                value={timezone}
                onChange={e => setTimezone(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white text-sm placeholder-gray-600 focus:outline-none focus:border-red-500 transition-colors"
              />
              <p className="text-gray-600 text-xs mt-1.5">
                Detected from your browser. You can edit this.
              </p>
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
              {loading ? 'Creating account…' : 'Create account'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
