import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getDrivers } from '../services/api'
import type { Driver } from '../types'

function DriverCard({ driver }: { driver: Driver }) {
  return (
    <Link
      to={`/drivers/${driver.id}`}
      className="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-red-500/70 transition-all duration-200 hover:-translate-y-0.5 group block"
    >
      <div className="flex items-start justify-between mb-4">
        <span className="text-red-500 font-black text-4xl font-mono leading-none">
          {driver.driver_number ?? '—'}
        </span>
        <span className="text-gray-500 text-xs font-mono bg-gray-800 px-2 py-1 rounded tracking-wider">
          {driver.code}
        </span>
      </div>
      <p className="text-white font-semibold text-base group-hover:text-red-100 transition-colors leading-tight">
        {driver.full_name}
      </p>
      <p className="text-red-400 text-sm mt-1">{driver.team ?? 'No team'}</p>
      <p className="text-gray-600 text-xs mt-1">{driver.nationality ?? '—'}</p>
    </Link>
  )
}

function SkeletonCard() {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 animate-pulse">
      <div className="h-9 w-10 bg-gray-800 rounded mb-4" />
      <div className="h-4 bg-gray-800 rounded w-3/4 mb-2" />
      <div className="h-3 bg-gray-800 rounded w-1/2" />
    </div>
  )
}

export default function Drivers() {
  const [drivers, setDrivers] = useState<Driver[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getDrivers()
      .then(setDrivers)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="page-enter">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Drivers</h1>
        <p className="text-gray-400 mt-1">All 2026 Formula 1 drivers.</p>
      </div>

      {loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }, (_, i) => <SkeletonCard key={i} />)}
        </div>
      )}

      {error && (
        <div className="bg-gray-900 border border-red-900/50 rounded-xl p-8 text-center">
          <p className="text-red-400 font-medium">Failed to load drivers</p>
          <p className="text-gray-500 text-sm mt-1">{error}</p>
          <p className="text-gray-600 text-xs mt-2">Make sure the backend is running on port 8000.</p>
        </div>
      )}

      {drivers && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {drivers.map(driver => <DriverCard key={driver.id} driver={driver} />)}
        </div>
      )}
    </div>
  )
}
