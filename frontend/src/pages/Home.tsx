import { Link } from 'react-router-dom'

const sections = [
  { to: '/drivers', label: 'Drivers', description: 'All 2025 F1 drivers and their teams.' },
  { to: '/teams', label: 'Teams', description: 'All 10 constructors on the 2025 grid.' },
  { to: '/calendar', label: 'Calendar', description: 'The full 2025 race schedule.' },
  { to: '/standings', label: 'Standings', description: 'Current driver championship standings.' },
]

export default function Home() {
  return (
    <div>
      <div className="py-16 text-center">
        <h1 className="text-5xl font-bold mb-4">
          Grid<span className="text-red-500">Pulse</span>
        </h1>
        <p className="text-gray-400 text-lg max-w-xl mx-auto">
          Your Formula 1 race intelligence platform. Follow the 2025 season — drivers, teams, calendar, and standings.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {sections.map(section => (
          <Link
            key={section.to}
            to={section.to}
            className="bg-gray-900 border border-gray-800 rounded-lg p-6 hover:border-red-500 transition-colors group"
          >
            <h2 className="text-white font-semibold text-lg group-hover:text-red-400 transition-colors">
              {section.label}
            </h2>
            <p className="text-gray-500 text-sm mt-1">{section.description}</p>
          </Link>
        ))}
      </div>
    </div>
  )
}
