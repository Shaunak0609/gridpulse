import { Link } from 'react-router-dom'

const sections = [
  { to: '/drivers', label: 'Drivers', description: 'All 20 drivers on the 2025 grid.' },
  { to: '/teams', label: 'Teams', description: 'All 10 constructors competing in 2025.' },
  { to: '/calendar', label: 'Calendar', description: 'The full 24-race 2025 season schedule.' },
  { to: '/standings', label: 'Standings', description: 'Live driver championship standings.' },
]

export default function Home() {
  return (
    <div className="page-enter">
      {/* Hero */}
      {/* To add a background image: save it as frontend/public/hero.jpg */}
      <div
        className="relative py-20 text-center overflow-hidden rounded-2xl bg-cover bg-center bg-no-repeat"
        style={{ backgroundImage: "url('/hero.jpg')" }}
      >
        {/* Dark overlay — keeps text readable over any background image */}
        <div className="absolute inset-0 bg-gray-950/60 rounded-2xl" />
        {/* Red tint gradient on top of the dark overlay */}
        <div className="absolute inset-0 bg-gradient-to-b from-red-950/30 to-transparent pointer-events-none rounded-2xl" />
        {/* z-10 keeps all content above the overlays */}
        <p className="relative z-10 text-red-500 text-xs font-semibold tracking-widest uppercase mb-4">
          2025 Season
        </p>
        <h1 className="relative z-10 text-6xl font-black mb-4 tracking-tight">
          Grid<span className="text-red-500">Pulse</span>
        </h1>
        <p className="relative z-10 text-gray-400 text-lg max-w-lg mx-auto leading-relaxed">
          Your Formula 1 race intelligence platform. Follow drivers, teams, the calendar, and championship standings.
        </p>
        <Link
          to="/standings"
          className="relative z-10 inline-block mt-8 bg-red-600 hover:bg-red-500 text-white text-sm font-semibold px-6 py-3 rounded-lg transition-colors duration-200"
        >
          View Standings →
        </Link>
      </div>

      {/* Section cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
        {sections.map(section => (
          <Link
            key={section.to}
            to={section.to}
            className="bg-gray-900 border border-gray-800 rounded-xl p-6 hover:border-red-500/60 hover:bg-gray-900/80 transition-all duration-200 hover:-translate-y-0.5 group"
          >
            <h2 className="text-white font-bold text-lg group-hover:text-red-400 transition-colors">
              {section.label}
            </h2>
            <p className="text-gray-500 text-sm mt-1 leading-relaxed">{section.description}</p>
            <span className="text-red-600 text-xs mt-3 inline-block group-hover:translate-x-1 transition-transform duration-200">
              Explore →
            </span>
          </Link>
        ))}
      </div>
    </div>
  )
}
