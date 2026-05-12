import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getDriver } from '../services/api'
import type { Driver } from '../types'

function StatCard({ label, value }: { label: string; value: string | number | null }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <p className="text-gray-500 text-xs uppercase tracking-widest mb-1">{label}</p>
      <p className="text-white font-semibold">{value ?? '—'}</p>
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="animate-pulse">
      <div className="h-3 w-24 bg-gray-800 rounded mb-10" />
      <div className="flex items-baseline gap-5 mb-10">
        <div className="h-16 w-16 bg-gray-800 rounded" />
        <div>
          <div className="h-8 w-56 bg-gray-800 rounded mb-2" />
          <div className="h-5 w-32 bg-gray-800 rounded" />
        </div>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {Array.from({ length: 4 }, (_, i) => (
          <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-4 h-16" />
        ))}
      </div>
    </div>
  )
}

export default function DriverDetail() {
  const { id } = useParams<{ id: string }>()
  const [driver, setDriver] = useState<Driver | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    getDriver(parseInt(id))
      .then(setDriver)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <LoadingSkeleton />

  if (error) {
    return (
      <div className="page-enter">
        <Link to="/drivers" className="text-gray-500 hover:text-white text-sm transition-colors">
          ← Back to Drivers
        </Link>
        <div className="mt-8 bg-gray-900 border border-red-900/50 rounded-xl p-10 text-center">
          <p className="text-red-400 font-medium">Driver not found</p>
          <p className="text-gray-500 text-sm mt-1">{error}</p>
        </div>
      </div>
    )
  }

  if (!driver) return null

  return (
    <div className="page-enter">
      <Link to="/drivers" className="text-gray-500 hover:text-white text-sm transition-colors inline-block mb-10">
        ← Back to Drivers
      </Link>

      {/* Header */}
      <div className="mb-10">
        <div className="flex items-baseline gap-5 flex-wrap">
          <span className="text-red-500 font-black text-7xl font-mono leading-none opacity-70">
            {driver.driver_number ?? '—'}
          </span>
          <div>
            <h1 className="text-4xl font-black text-white tracking-tight">{driver.full_name}</h1>
            <p className="text-red-400 text-lg mt-1">{driver.team ?? 'No team'}</p>
          </div>
        </div>
        <div className="h-px bg-gradient-to-r from-red-600 to-transparent mt-6" />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard label="Team" value={driver.team} />
        <StatCard label="Nationality" value={driver.nationality} />
        <StatCard label="Number" value={driver.driver_number} />
        <StatCard label="Code" value={driver.code} />
      </div>
    </div>
  )
}
