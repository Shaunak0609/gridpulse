import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

// ─── Icons (inline SVG — no library needed) ──────────────────────────────────

function GearIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  )
}

function ChevronDown({ open }: { open: boolean }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" className={`w-3 h-3 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="6 9 12 15 18 9" />
    </svg>
  )
}

// ─── Nav link groups ──────────────────────────────────────────────────────────

const raceInfoLinks = [
  { to: '/drivers', label: 'Drivers' },
  { to: '/teams', label: 'Teams' },
  { to: '/standings', label: 'Standings' },
  { to: '/calendar', label: 'Calendar' },
]

const myGridPulseLinks = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/ai', label: 'AI Race Assistant' },
  { to: '/notifications', label: 'Notifications' },
  { to: '/reminders', label: 'Reminders' },
]

// ─── Dropdown component ───────────────────────────────────────────────────────

function NavDropdown({
  label,
  links,
  open,
  onToggle,
  onClose,
}: {
  label: string
  links: { to: string; label: string }[]
  open: boolean
  onToggle: () => void
  onClose: () => void
}) {
  return (
    <div className="relative">
      <button
        onClick={onToggle}
        className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm transition-colors duration-200 ${
          open ? 'text-white bg-gray-800' : 'text-gray-400 hover:text-white hover:bg-gray-800/60'
        }`}
      >
        {label}
        <ChevronDown open={open} />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1.5 w-48 bg-gray-900 border border-gray-700 rounded-xl shadow-xl overflow-hidden z-50">
          {links.map(link => (
            <NavLink
              key={link.to}
              to={link.to}
              onClick={onClose}
              className={({ isActive }) =>
                `block px-4 py-2.5 text-sm transition-colors duration-150 ${
                  isActive
                    ? 'text-red-400 bg-gray-800'
                    : 'text-gray-300 hover:text-white hover:bg-gray-800'
                }`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Navbar ───────────────────────────────────────────────────────────────────

export default function Navbar() {
  const { isAuthenticated, user, logout } = useAuth()
  const navigate = useNavigate()
  const [raceInfoOpen, setRaceInfoOpen] = useState(false)
  const [myHubOpen, setMyHubOpen] = useState(false)

  function handleLogout() {
    logout()
    navigate('/')
  }

  function closeAll() {
    setRaceInfoOpen(false)
    setMyHubOpen(false)
  }

  return (
    <>
      {/* Invisible backdrop — clicking outside any open dropdown closes it */}
      {(raceInfoOpen || myHubOpen) && (
        <div className="fixed inset-0 z-40" onClick={closeAll} aria-hidden="true" />
      )}

      <nav className="bg-gray-900 border-b border-gray-800 relative z-50">
        <div className="max-w-6xl mx-auto px-4 flex items-center justify-between h-16 gap-4">

          {/* Logo */}
          <Link
            to="/"
            onClick={closeAll}
            className="text-white font-bold text-xl tracking-tight shrink-0"
          >
            Grid<span className="text-red-500">Pulse</span>
          </Link>

          {/* Centre — dropdowns */}
          <div className="flex items-center gap-1 min-w-0">
            <NavDropdown
              label="Race Info"
              links={raceInfoLinks}
              open={raceInfoOpen}
              onToggle={() => { setRaceInfoOpen(o => !o); setMyHubOpen(false) }}
              onClose={closeAll}
            />

            {isAuthenticated && (
              <NavDropdown
                label="My GridPulse"
                links={myGridPulseLinks}
                open={myHubOpen}
                onToggle={() => { setMyHubOpen(o => !o); setRaceInfoOpen(false) }}
                onClose={closeAll}
              />
            )}
          </div>

          {/* Right — auth controls */}
          <div className="flex items-center gap-2 shrink-0">
            {isAuthenticated ? (
              <>
                <NavLink
                  to="/profile"
                  onClick={closeAll}
                  className={({ isActive }) =>
                    `text-sm truncate max-w-[120px] transition-colors ${
                      isActive ? 'text-red-400 font-medium' : 'text-gray-400 hover:text-white'
                    }`
                  }
                >
                  {user?.username ?? user?.email}
                </NavLink>

                <NavLink
                  to="/settings"
                  onClick={closeAll}
                  title="Settings"
                  className={({ isActive }) =>
                    `p-2 rounded-lg transition-colors duration-200 ${
                      isActive ? 'text-red-400' : 'text-gray-400 hover:text-white hover:bg-gray-800'
                    }`
                  }
                >
                  <GearIcon />
                </NavLink>

                <button
                  onClick={handleLogout}
                  className="text-xs text-gray-500 hover:text-white border border-gray-700 hover:border-gray-500 px-3 py-1.5 rounded-lg transition-colors duration-200 whitespace-nowrap"
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
                  className="text-xs bg-red-600 hover:bg-red-500 text-white font-semibold px-3 py-1.5 rounded-lg transition-colors duration-200 whitespace-nowrap"
                >
                  Sign up
                </Link>
              </>
            )}
          </div>

        </div>
      </nav>
    </>
  )
}
