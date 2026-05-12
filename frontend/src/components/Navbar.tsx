import { Link, NavLink } from 'react-router-dom'

const navLinks = [
  { to: '/drivers', label: 'Drivers' },
  { to: '/teams', label: 'Teams' },
  { to: '/calendar', label: 'Calendar' },
  { to: '/standings', label: 'Standings' },
]

export default function Navbar() {
  return (
    <nav className="bg-gray-900 border-b border-gray-800">
      <div className="max-w-6xl mx-auto px-4 flex items-center justify-between h-16">
        <Link to="/" className="text-white font-bold text-xl tracking-tight">
          Grid<span className="text-red-500">Pulse</span>
        </Link>
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
      </div>
    </nav>
  )
}
