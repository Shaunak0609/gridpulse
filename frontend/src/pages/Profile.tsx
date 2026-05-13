import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

function ProfileRow({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="flex items-start gap-4 py-4 border-b border-gray-800 last:border-0">
      <span className="text-gray-500 text-xs uppercase tracking-widest w-24 shrink-0 pt-0.5">
        {label}
      </span>
      <span className="text-white text-sm">{value ?? '—'}</span>
    </div>
  )
}

export default function Profile() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/')
  }

  return (
    <div className="page-enter max-w-lg">
      {/* Header */}
      <div className="mb-8">
        <p className="text-red-500 text-xs font-semibold tracking-widest uppercase mb-3">
          Account
        </p>
        <h1 className="text-3xl font-black text-white tracking-tight">Your Profile</h1>
        <p className="text-gray-400 mt-1 text-sm">Your GridPulse account details.</p>
      </div>

      {/* Profile card */}
      <div className="bg-gray-900 border border-gray-800 rounded-2xl px-6 py-2 mb-6">
        <ProfileRow label="Email" value={user?.email} />
        <ProfileRow label="Username" value={user?.username} />
        <ProfileRow label="Timezone" value={user?.timezone} />
      </div>

      {/* Logout */}
      <button
        onClick={handleLogout}
        className="bg-gray-800 hover:bg-gray-700 border border-gray-700 hover:border-red-500/50 text-gray-300 hover:text-white text-sm font-medium px-5 py-2.5 rounded-lg transition-all duration-200"
      >
        Log out
      </button>
    </div>
  )
}
