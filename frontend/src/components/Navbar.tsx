import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const publicNavLinks = [
  { to: '/drivers', label: 'Drivers' },
  { to: '/teams', label: 'Teams' },
  { to: '/calendar', label: 'Calendar' },
  { to: '/standings', label: 'Standings' },
]

const authNavLinks = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/ai', label: 'AI' },
  { to: '/reminders', label: 'Reminders' },
  { to: '/notifications', label: 'Notifications' },
  { to: '/settings', label: 'Settings' },
]

export default function Navbar() {
  const { isAuthenticated, user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/')
  }

  const navLinks = isAuthenticated
    ? [...publicNavLinks, ...authNavLinks]
    : publicNavLinks

  return (
    <nav className="bg-gray-900 border-b border-gray-800">
      <div className="max-w-6xl mx-auto px-4 flex items-center justify-between h-16">
        {/* Logo */}
        <Link to="/" className="text-white font-bold text-xl tracking-tight shrink-0">
          Grid<span className="text-red-500">Pulse</span>
        </Link>

        {/* Centre nav links */}
        <div className="flex gap-6">
          {navLinks.map(link => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                isActive
                  ? 'text-red-400 font-medium text-sm'
                  : 'text-gray-400 hover:text-white text-sm transition-colors'
              }
            >
              {link.label}
            </NavLink>
          ))}
        </div>

        {/* Right — auth controls */}
        <div className="flex items-center gap-3 shrink-0">
          {isAuthenticated ? (
            <>
              <NavLink
                to="/profile"
                className={({ isActive }) =>
                  isActive
                    ? 'text-red-400 font-medium text-sm'
                    : 'text-gray-400 hover:text-white text-sm transition-colors'
                }
              >
                {user?.username ?? user?.email}
              </NavLink>
              <button
                onClick={handleLogout}
                className="text-xs text-gray-500 hover:text-white border border-gray-700 hover:border-gray-500 px-3 py-1.5 rounded-lg transition-colors duration-200"
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink
                to="/login"
                className={({ isActive }) =>
                  isActive
                    ? 'text-red-400 font-medium text-sm'
                    : 'text-gray-400 hover:text-white text-sm transition-colors'
                }
              >
                Log in
              </NavLink>
              <Link
                to="/signup"
                className="text-xs bg-red-600 hover:bg-red-500 text-white font-semibold px-3 py-1.5 rounded-lg transition-colors duration-200"
              >
                Sign up
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}
