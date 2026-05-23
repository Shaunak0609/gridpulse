import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ResponsiveContainer,
} from 'recharts'
import { getSessionAnalytics, getSessionTireAnalytics, compareSessionDrivers } from '../services/api'
import { useAuth } from '../context/AuthContext'
import type {
  SessionAnalytics,
  AnalyticsTireSummary,
  AnalyticsDriverSummary,
  AnalyticsCompoundUsage,
  AnalyticsTeammateComparison,
  AnalyticsRaceContext,
  AnalyticsWeather,
  DriverComparisonAnalytics,
  AnalyticsStintEntry,
} from '../types'

// ─── Formatters ───────────────────────────────────────────────────────────────

function formatLapTime(seconds: number | null): string {
  if (seconds == null) return '—'
  const mins = Math.floor(seconds / 60)
  const secs = (seconds % 60).toFixed(3).padStart(6, '0')
  return `${mins}:${secs}`
}

function formatDelta(delta: number | null): string {
  if (delta == null) return '—'
  const sign = delta <= 0 ? '' : '+'
  return `${sign}${delta.toFixed(3)}s`
}

function formatDate(iso: string | null): string {
  if (!iso) return 'Date TBC'
  return new Date(iso).toLocaleDateString('en-GB', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

// ─── Shared UI primitives ─────────────────────────────────────────────────────

const COMPOUND_STYLES: Record<string, string> = {
  SOFT:         'bg-red-950 text-red-300 border-red-800',
  MEDIUM:       'bg-yellow-950 text-yellow-300 border-yellow-800',
  HARD:         'bg-gray-800 text-gray-200 border-gray-600',
  INTERMEDIATE: 'bg-green-950 text-green-300 border-green-800',
  WET:          'bg-blue-950 text-blue-300 border-blue-800',
}

const COMPOUND_ORDER = ['SOFT', 'MEDIUM', 'HARD', 'INTERMEDIATE', 'WET']

function CompoundBadge({ compound }: { compound: string | null }) {
  if (!compound) return <span className="text-gray-600">—</span>
  const style = COMPOUND_STYLES[compound] ?? 'bg-gray-800 text-gray-400 border-gray-700'
  return (
    <span className={`text-xs font-mono px-1.5 py-0.5 rounded border ${style}`}>
      {compound}
    </span>
  )
}

function FavStar() {
  return (
    <span className="text-red-500 text-sm leading-none shrink-0" title="Favourite driver">
      ★
    </span>
  )
}

function SectionCard({
  title,
  badge,
  empty,
  emptyMessage,
  children,
}: {
  title: string
  badge?: string
  empty: boolean
  emptyMessage: string
  children?: React.ReactNode
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-800">
        <h2 className="text-sm font-semibold text-white">{title}</h2>
        {badge && <span className="text-xs font-mono text-gray-500">{badge}</span>}
      </div>
      {empty ? (
        <div className="px-5 py-8 text-center">
          <p className="text-sm text-gray-600">{emptyMessage}</p>
        </div>
      ) : (
        children
      )}
    </div>
  )
}

// ─── Session pace summary ─────────────────────────────────────────────────────

function SessionPaceSummary({
  fastestLap,
  fastestDriver,
  avgLap,
  hasData,
}: {
  fastestLap: number | null
  fastestDriver: string | null
  avgLap: number | null
  hasData: boolean
}) {
  const stats = [
    { label: 'Fastest lap', value: formatLapTime(fastestLap) },
    { label: 'Set by', value: fastestDriver ?? '—' },
    { label: 'Session average', value: formatLapTime(avgLap) },
  ]

  return (
    <SectionCard
      title="Session Pace"
      empty={!hasData}
      emptyMessage="No lap data has been synced for this session yet."
    >
      <div className="grid grid-cols-3 gap-px bg-gray-800/50">
        {stats.map(s => (
          <div key={s.label} className="bg-gray-900 px-5 py-4">
            <p className="text-gray-600 text-xs mb-1">{s.label}</p>
            <p className="text-white font-mono font-medium text-sm">{s.value}</p>
          </div>
        ))}
      </div>
    </SectionCard>
  )
}

// ─── Driver pace table ────────────────────────────────────────────────────────

function DriverPaceTable({ drivers }: { drivers: AnalyticsDriverSummary[] }) {
  return (
    <SectionCard
      title="Driver Pace"
      badge={`${drivers.length} drivers`}
      empty={drivers.length === 0}
      emptyMessage="No lap data has been synced for this session yet."
    >
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-gray-600 uppercase tracking-wider border-b border-gray-800">
              <th className="px-4 py-2.5 text-left font-medium w-8">#</th>
              <th className="px-4 py-2.5 text-left font-medium">Driver</th>
              <th className="px-4 py-2.5 text-right font-medium">Laps</th>
              <th className="px-4 py-2.5 text-right font-medium">Fastest</th>
              <th className="px-4 py-2.5 text-right font-medium">Average</th>
              <th className="px-4 py-2.5 text-right font-medium hidden sm:table-cell">S1</th>
              <th className="px-4 py-2.5 text-right font-medium hidden sm:table-cell">S2</th>
              <th className="px-4 py-2.5 text-right font-medium hidden sm:table-cell">S3</th>
            </tr>
          </thead>
          <tbody>
            {drivers.map((d, i) => (
              <tr
                key={d.driver_number}
                className={`border-b border-gray-800/40 last:border-0 transition-colors ${
                  d.is_favourite
                    ? 'bg-red-950/10 hover:bg-red-950/20'
                    : 'hover:bg-gray-800/10'
                }`}
              >
                <td className="px-4 py-2.5 text-gray-600 font-mono">{i + 1}</td>
                <td className="px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    {d.is_favourite && <FavStar />}
                    <span className={`font-medium ${d.is_favourite ? 'text-white' : 'text-gray-200'}`}>
                      {d.driver_name}
                    </span>
                    <span className="text-gray-600 font-mono">#{d.driver_number}</span>
                  </div>
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-gray-400">
                  {d.timed_lap_count}
                  {d.lap_count !== d.timed_lap_count && (
                    <span className="text-gray-700"> /{d.lap_count}</span>
                  )}
                </td>
                <td className="px-4 py-2.5 text-right font-mono">
                  {i === 0 && d.fastest_lap != null ? (
                    <span className="text-purple-400 font-medium">{formatLapTime(d.fastest_lap)}</span>
                  ) : (
                    <span className="text-gray-300">{formatLapTime(d.fastest_lap)}</span>
                  )}
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-gray-400">
                  {formatLapTime(d.average_lap)}
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-gray-500 hidden sm:table-cell">
                  {d.best_s1 != null ? d.best_s1.toFixed(3) : '—'}
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-gray-500 hidden sm:table-cell">
                  {d.best_s2 != null ? d.best_s2.toFixed(3) : '—'}
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-gray-500 hidden sm:table-cell">
                  {d.best_s3 != null ? d.best_s3.toFixed(3) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="px-5 py-2 text-xs text-gray-700 border-t border-gray-800/50">
        Laps shown are timed laps (pit-out laps excluded).
        Average is only shown when a driver has 3 or more timed laps.
        Sector times are best recorded values across all laps.
      </p>
    </SectionCard>
  )
}

// ─── Compound pace section ────────────────────────────────────────────────────

function CompoundPaceSection({
  compounds,
  hasCompoundPace,
}: {
  compounds: AnalyticsCompoundUsage[]
  hasCompoundPace: boolean
}) {
  const sorted = [
    ...COMPOUND_ORDER
      .filter(c => compounds.some(u => u.compound === c))
      .map(c => compounds.find(u => u.compound === c)!),
    ...compounds.filter(u => !COMPOUND_ORDER.includes(u.compound)),
  ]

  const emptyMessage = hasCompoundPace
    ? 'No compound pace data available.'
    : 'Compound pace requires stints with lap ranges — not available for this session.'

  return (
    <SectionCard
      title="Pace by Compound"
      badge={sorted.length > 0 ? `${sorted.length} compound${sorted.length !== 1 ? 's' : ''}` : undefined}
      empty={sorted.length === 0}
      emptyMessage={emptyMessage}
    >
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-gray-600 uppercase tracking-wider border-b border-gray-800">
              <th className="px-5 py-2.5 text-left font-medium">Compound</th>
              <th className="px-5 py-2.5 text-right font-medium">Avg lap</th>
              <th className="px-5 py-2.5 text-right font-medium">Fastest lap</th>
              <th className="px-5 py-2.5 text-right font-medium">Drivers</th>
              <th className="px-5 py-2.5 text-right font-medium">Samples</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map(c => (
              <tr
                key={c.compound}
                className="border-b border-gray-800/40 last:border-0 hover:bg-gray-800/10 transition-colors"
              >
                <td className="px-5 py-3">
                  <CompoundBadge compound={c.compound} />
                </td>
                <td className="px-5 py-3 text-right font-mono text-gray-300">
                  {formatLapTime(c.avg_lap_time)}
                </td>
                <td className="px-5 py-3 text-right font-mono text-purple-400">
                  {formatLapTime(c.fastest_lap_time)}
                </td>
                <td className="px-5 py-3 text-right font-mono text-gray-500">
                  {c.driver_count}
                </td>
                <td className="px-5 py-3 text-right font-mono text-gray-600">
                  {c.sample_lap_count}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="px-5 py-2 text-xs text-gray-700 border-t border-gray-800/50">
        Averages are computed from timed laps joined to their stint's lap range.
        A low sample count ({"<"}10) means the average may not be representative.
      </p>
    </SectionCard>
  )
}

// ─── Teammate comparisons section ─────────────────────────────────────────────

function TeammateComparisonsSection({
  comparisons,
}: {
  comparisons: AnalyticsTeammateComparison[]
}) {
  return (
    <SectionCard
      title="Teammate Battle"
      badge={`${comparisons.length} team${comparisons.length !== 1 ? 's' : ''}`}
      empty={comparisons.length === 0}
      emptyMessage="Teammate comparisons require two drivers per team with timed lap data."
    >
      <div className="divide-y divide-gray-800/50">
        {comparisons.map(tc => {
          const aFaster = tc.fastest_delta != null && tc.fastest_delta < 0
          const bFaster = tc.fastest_delta != null && tc.fastest_delta > 0

          return (
            <div key={tc.team_name} className="px-5 py-4">
              <p className="text-xs text-gray-600 font-mono uppercase tracking-wider mb-3">
                {tc.team_name}
              </p>
              <div className="grid grid-cols-3 gap-2 items-center">
                {/* Driver A */}
                <div className={`text-right ${aFaster ? 'text-white' : 'text-gray-400'}`}>
                  <p className="font-medium text-sm">{tc.driver_a_name}</p>
                  <p className="font-mono text-xs text-gray-600">#{tc.driver_a_number}</p>
                  <p className="font-mono text-xs mt-1">{formatLapTime(tc.driver_a_fastest)}</p>
                  <p className="font-mono text-xs text-gray-600">{formatLapTime(tc.driver_a_avg)} avg</p>
                </div>

                {/* Deltas */}
                <div className="text-center">
                  <p className="text-gray-600 text-xs mb-1">fastest Δ</p>
                  <p className={`font-mono text-sm font-medium ${
                    aFaster ? 'text-green-400' : bFaster ? 'text-red-400' : 'text-gray-500'
                  }`}>
                    {formatDelta(tc.fastest_delta)}
                  </p>
                  <p className="text-gray-600 text-xs mt-2 mb-0.5">avg Δ</p>
                  <p className="font-mono text-xs text-gray-500">
                    {formatDelta(tc.avg_delta)}
                  </p>
                </div>

                {/* Driver B */}
                <div className={`text-left ${bFaster ? 'text-white' : 'text-gray-400'}`}>
                  <p className="font-medium text-sm">{tc.driver_b_name}</p>
                  <p className="font-mono text-xs text-gray-600">#{tc.driver_b_number}</p>
                  <p className="font-mono text-xs mt-1">{formatLapTime(tc.driver_b_fastest)}</p>
                  <p className="font-mono text-xs text-gray-600">{formatLapTime(tc.driver_b_avg)} avg</p>
                </div>
              </div>
            </div>
          )
        })}
      </div>
      <p className="px-5 py-2 text-xs text-gray-700 border-t border-gray-800/50">
        Delta = driver A minus driver B in seconds. Negative value means driver A is faster.
      </p>
    </SectionCard>
  )
}

// ─── Race control context section ─────────────────────────────────────────────

function RaceControlContextSection({ rc }: { rc: AnalyticsRaceContext }) {
  const hasSC = rc.safety_car_laps.length > 0
  const hasRF = rc.red_flag_laps.length > 0
  const hasAny = hasSC || hasRF

  return (
    <SectionCard
      title="Race Control Context"
      badge={`${rc.rc_total} total messages`}
      empty={!hasAny}
      emptyMessage={
        rc.rc_total === 0
          ? 'No race control messages synced for this session.'
          : 'No safety car or red flag events recorded in this session.'
      }
    >
      <div className="divide-y divide-gray-800/40">
        {hasSC && (
          <div className="px-5 py-4 flex items-start gap-4">
            <span className="text-xs font-mono px-1.5 py-0.5 rounded bg-orange-950 text-orange-300 border border-orange-800 shrink-0 mt-0.5">
              SAFETY CAR
            </span>
            <div>
              <p className="text-xs text-gray-400 mb-1">
                Laps affected: {rc.safety_car_laps.join(', ')}
              </p>
              <p className="text-xs text-gray-600 italic">
                Lap times on these laps are not representative of true race pace.
              </p>
            </div>
          </div>
        )}
        {hasRF && (
          <div className="px-5 py-4 flex items-start gap-4">
            <span className="text-xs font-mono px-1.5 py-0.5 rounded bg-red-950 text-red-300 border border-red-800 shrink-0 mt-0.5">
              RED FLAG
            </span>
            <div>
              <p className="text-xs text-gray-400 mb-1">
                Laps affected: {rc.red_flag_laps.join(', ')}
              </p>
              <p className="text-xs text-gray-600 italic">
                Lap times on red flag laps are not representative of true race pace.
              </p>
            </div>
          </div>
        )}
      </div>
    </SectionCard>
  )
}

// ─── Weather section ──────────────────────────────────────────────────────────

function WeatherSection({ weather }: { weather: AnalyticsWeather }) {
  const stats = [
    { label: 'Air temp', value: weather.air_temperature != null ? `${weather.air_temperature} °C` : '—' },
    { label: 'Track temp', value: weather.track_temperature != null ? `${weather.track_temperature} °C` : '—' },
    { label: 'Humidity', value: weather.humidity != null ? `${weather.humidity}%` : '—' },
    { label: 'Wind speed', value: weather.wind_speed != null ? `${weather.wind_speed} m/s` : '—' },
    {
      label: 'Rainfall',
      value: weather.rainfall == null ? '—' : weather.rainfall ? 'Yes' : 'No',
      highlight: weather.rainfall === true,
    },
  ]

  return (
    <SectionCard title="Latest Weather" empty={false} emptyMessage="">
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-px bg-gray-800/50">
        {stats.map(s => (
          <div key={s.label} className="bg-gray-900 px-4 py-4">
            <p className="text-gray-600 text-xs mb-1">{s.label}</p>
            <p className={`font-mono font-medium text-sm ${s.highlight ? 'text-blue-400' : 'text-gray-200'}`}>
              {s.value}
            </p>
          </div>
        ))}
      </div>
      <p className="px-5 py-2 text-xs text-gray-700 border-t border-gray-800/50">
        Figures are from the most recent weather sample stored for this session.
      </p>
    </SectionCard>
  )
}

// ─── Charts ───────────────────────────────────────────────────────────────────

const COMPOUND_BAR_COLORS: Record<string, string> = {
  SOFT:         '#ef4444',
  MEDIUM:       '#eab308',
  HARD:         '#9ca3af',
  INTERMEDIATE: '#22c55e',
  WET:          '#60a5fa',
}

const CHART_GRID_STROKE = '#1f2937'
const CHART_TICK_COLOR  = '#6b7280'
const CHART_AXIS_STROKE = '#374151'

function ChartTooltip({ lines }: { lines: { label: string; value: string }[] }) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-xs shadow-lg">
      {lines.map((l, i) => (
        <p key={i} className={i === 0 ? 'text-gray-300' : 'font-mono text-white mt-0.5'}>
          {l.label}{i > 0 ? ': ' : ''}{i > 0 ? l.value : l.label === l.value ? l.value : l.label}
        </p>
      ))}
    </div>
  )
}

function LapCountChart({ drivers }: { drivers: AnalyticsDriverSummary[] }) {
  const data = [...drivers]
    .sort((a, b) => b.timed_lap_count - a.timed_lap_count)
    .slice(0, 15)
    .map(d => ({
      name: d.driver_name.split(' ').slice(-1)[0],
      fullName: d.driver_name,
      value: d.timed_lap_count,
      isFav: d.is_favourite,
    }))

  if (data.length === 0) {
    return <p className="text-sm text-gray-600 text-center py-6">No lap data available.</p>
  }

  const chartHeight = Math.max(180, data.length * 32)

  return (
    <ResponsiveContainer width="100%" height={chartHeight}>
      <BarChart data={data} layout="vertical" margin={{ top: 0, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID_STROKE} horizontal={false} />
        <XAxis
          type="number"
          tick={{ fill: CHART_TICK_COLOR, fontSize: 11 }}
          axisLine={{ stroke: CHART_AXIS_STROKE }}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="name"
          width={88}
          tick={{ fill: '#9ca3af', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          cursor={{ fill: 'rgba(255,255,255,0.03)' }}
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null
            const d = payload[0].payload as typeof data[0]
            return (
              <ChartTooltip
                lines={[
                  { label: d.fullName, value: d.fullName },
                  { label: 'Timed laps', value: String(d.value) },
                ]}
              />
            )
          }}
        />
        <Bar dataKey="value" radius={[0, 3, 3, 0]} maxBarSize={18}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.isFav ? '#dc2626' : '#374151'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

function FastestLapGapChart({ drivers }: { drivers: AnalyticsDriverSummary[] }) {
  const withLap = drivers.filter(d => d.fastest_lap != null)
  if (withLap.length === 0) {
    return <p className="text-sm text-gray-600 text-center py-6">No fastest lap data available.</p>
  }

  const best = Math.min(...withLap.map(d => d.fastest_lap!))
  const data = withLap
    .sort((a, b) => a.fastest_lap! - b.fastest_lap!)
    .slice(0, 15)
    .map(d => ({
      name: d.driver_name.split(' ').slice(-1)[0],
      fullName: d.driver_name,
      fastest: d.fastest_lap!,
      gap: parseFloat((d.fastest_lap! - best).toFixed(3)),
      isFav: d.is_favourite,
    }))

  const chartHeight = Math.max(180, data.length * 32)
  const maxGap = Math.max(...data.map(d => d.gap), 0.1)

  return (
    <ResponsiveContainer width="100%" height={chartHeight}>
      <BarChart data={data} layout="vertical" margin={{ top: 0, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID_STROKE} horizontal={false} />
        <XAxis
          type="number"
          domain={[0, parseFloat((maxGap * 1.1).toFixed(2))]}
          tickFormatter={v => `+${v.toFixed(1)}s`}
          tick={{ fill: CHART_TICK_COLOR, fontSize: 11 }}
          axisLine={{ stroke: CHART_AXIS_STROKE }}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="name"
          width={88}
          tick={{ fill: '#9ca3af', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          cursor={{ fill: 'rgba(255,255,255,0.03)' }}
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null
            const d = payload[0].payload as typeof data[0]
            return (
              <ChartTooltip
                lines={[
                  { label: d.fullName, value: d.fullName },
                  { label: 'Fastest lap', value: formatLapTime(d.fastest) },
                  { label: 'Gap', value: d.gap === 0 ? 'Fastest' : `+${d.gap.toFixed(3)}s` },
                ]}
              />
            )
          }}
        />
        <Bar dataKey="gap" radius={[0, 3, 3, 0]} maxBarSize={18} minPointSize={2}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.isFav ? '#dc2626' : '#4c1d95'} fillOpacity={entry.gap === 0 ? 0.3 : 1} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

function CompoundUsageChart({ compounds }: { compounds: AnalyticsCompoundUsage[] }) {
  if (compounds.length === 0) {
    return <p className="text-sm text-gray-600 text-center py-6">No compound data available.</p>
  }

  const data = [...COMPOUND_ORDER, ...compounds.map(c => c.compound).filter(c => !COMPOUND_ORDER.includes(c))]
    .filter(c => compounds.some(u => u.compound === c))
    .map(c => {
      const usage = compounds.find(u => u.compound === c)!
      return { name: c, value: usage.sample_lap_count, drivers: usage.driver_count }
    })

  const chartHeight = Math.max(120, data.length * 48)

  return (
    <ResponsiveContainer width="100%" height={chartHeight}>
      <BarChart data={data} layout="vertical" margin={{ top: 0, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID_STROKE} horizontal={false} />
        <XAxis
          type="number"
          tick={{ fill: CHART_TICK_COLOR, fontSize: 11 }}
          axisLine={{ stroke: CHART_AXIS_STROKE }}
          tickLine={false}
          label={{ value: 'laps', position: 'insideRight', fill: CHART_TICK_COLOR, fontSize: 10 }}
        />
        <YAxis
          type="category"
          dataKey="name"
          width={88}
          tick={{ fill: '#9ca3af', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          cursor={{ fill: 'rgba(255,255,255,0.03)' }}
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null
            const d = payload[0].payload as typeof data[0]
            return (
              <ChartTooltip
                lines={[
                  { label: d.name, value: d.name },
                  { label: 'Sample laps', value: String(d.value) },
                  { label: 'Drivers', value: String(d.drivers) },
                ]}
              />
            )
          }}
        />
        <Bar dataKey="value" radius={[0, 3, 3, 0]} maxBarSize={28}>
          {data.map((entry, i) => (
            <Cell key={i} fill={COMPOUND_BAR_COLORS[entry.name] ?? '#6b7280'} fillOpacity={0.85} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

function ChartsSection({
  drivers,
  compounds,
  hasLapData,
  hasCompoundPace,
}: {
  drivers: AnalyticsDriverSummary[]
  compounds: AnalyticsCompoundUsage[]
  hasLapData: boolean
  hasCompoundPace: boolean
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div className="px-5 py-3 border-b border-gray-800">
        <h2 className="text-sm font-semibold text-white">Session Charts</h2>
      </div>

      <div className="p-5 space-y-8">
        {/* Row 1: Lap count + Fastest lap gap side by side on wide screens */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">
              Timed Laps per Driver
            </p>
            {hasLapData ? (
              <LapCountChart drivers={drivers} />
            ) : (
              <p className="text-sm text-gray-600 text-center py-6">No lap data available.</p>
            )}
          </div>

          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">
              Gap to Fastest Lap
            </p>
            {hasLapData ? (
              <FastestLapGapChart drivers={drivers} />
            ) : (
              <p className="text-sm text-gray-600 text-center py-6">No lap data available.</p>
            )}
          </div>
        </div>

        {/* Row 2: Compound usage full-width */}
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">
            Laps by Compound
          </p>
          {hasCompoundPace ? (
            <CompoundUsageChart compounds={compounds} />
          ) : (
            <p className="text-sm text-gray-600 text-center py-6">
              Compound data requires stints with lap ranges — not available for this session.
            </p>
          )}
        </div>
      </div>

      <p className="px-5 py-2 text-xs text-gray-700 border-t border-gray-800/50">
        Favourite drivers are highlighted in red. Lap times shown as gap from session fastest.
      </p>
    </div>
  )
}

// ─── Driver comparison ────────────────────────────────────────────────────────

function CompoundSequence({ stints }: { stints: AnalyticsStintEntry[] }) {
  if (stints.length === 0) return <span className="text-gray-600 text-xs">No stint data</span>
  const sorted = [...stints].sort((a, b) => (a.stint_number ?? 0) - (b.stint_number ?? 0))
  return (
    <div className="flex items-center gap-1 flex-wrap">
      {sorted.map((s, i) => (
        <span key={i} className="flex items-center gap-1">
          <CompoundBadge compound={s.compound} />
          {i < sorted.length - 1 && <span className="text-gray-700 text-xs">→</span>}
        </span>
      ))}
    </div>
  )
}

function StintMiniTable({ stints }: { stints: AnalyticsStintEntry[] }) {
  if (stints.length === 0) return null
  const sorted = [...stints].sort((a, b) => (a.stint_number ?? 0) - (b.stint_number ?? 0))
  return (
    <table className="w-full text-xs mt-2">
      <thead>
        <tr className="text-gray-700 uppercase tracking-wider">
          <th className="text-left pb-1 font-medium">Stint</th>
          <th className="text-left pb-1 font-medium">Tyre</th>
          <th className="text-left pb-1 font-medium">Laps</th>
          <th className="text-right pb-1 font-medium">Avg</th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((s, i) => (
          <tr key={i} className="border-t border-gray-800/30">
            <td className="py-1.5 font-mono text-gray-600">S{s.stint_number ?? i + 1}</td>
            <td className="py-1.5"><CompoundBadge compound={s.compound} /></td>
            <td className="py-1.5 font-mono text-gray-500">
              {s.lap_start != null && s.lap_end != null
                ? `L${s.lap_start}–${s.lap_end}`
                : s.lap_start != null ? `L${s.lap_start}+` : '—'}
            </td>
            <td className="py-1.5 text-right font-mono text-gray-400">
              {formatLapTime(s.avg_lap_time)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function ComparisonResult({ result }: { result: DriverComparisonAnalytics }) {
  const { driver_a, driver_b, fastest_delta, avg_delta, driver_a_stints, driver_b_stints } = result
  const aFaster = fastest_delta != null && fastest_delta < 0
  const bFaster = fastest_delta != null && fastest_delta > 0
  const hasStints = driver_a_stints.length > 0 || driver_b_stints.length > 0

  const statRows = [
    { label: 'Timed laps', a: String(driver_a.timed_lap_count), b: String(driver_b.timed_lap_count) },
    { label: 'Fastest lap', a: formatLapTime(driver_a.fastest_lap), b: formatLapTime(driver_b.fastest_lap) },
    { label: 'Average lap', a: formatLapTime(driver_a.average_lap), b: formatLapTime(driver_b.average_lap) },
    { label: 'Best S1', a: driver_a.best_s1?.toFixed(3) ?? '—', b: driver_b.best_s1?.toFixed(3) ?? '—' },
    { label: 'Best S2', a: driver_a.best_s2?.toFixed(3) ?? '—', b: driver_b.best_s2?.toFixed(3) ?? '—' },
    { label: 'Best S3', a: driver_a.best_s3?.toFixed(3) ?? '—', b: driver_b.best_s3?.toFixed(3) ?? '—' },
  ]

  return (
    <div className="border-t border-gray-800">
      {/* Driver name headers */}
      <div className="grid grid-cols-3 gap-px bg-gray-800/50">
        <div className={`bg-gray-900 px-5 py-3 text-right ${!aFaster && bFaster ? 'opacity-50' : ''}`}>
          <p className={`font-semibold text-sm ${aFaster ? 'text-white' : 'text-gray-300'}`}>
            {driver_a.driver_name}
            {driver_a.is_favourite && <span className="text-red-500 ml-1.5 text-xs">★</span>}
          </p>
          <p className="text-gray-600 font-mono text-xs">#{driver_a.driver_number}</p>
        </div>
        <div className="bg-gray-900 px-3 py-3 text-center flex flex-col items-center justify-center">
          <p className="text-gray-700 text-xs font-mono">vs</p>
          {fastest_delta != null && (
            <>
              <p className="font-mono text-base font-bold text-white mt-1">
                {Math.abs(fastest_delta).toFixed(3)}s
              </p>
              <p className="text-gray-600 text-xs mt-0.5">
                {aFaster
                  ? `${driver_a.driver_name.split(' ').pop()} faster`
                  : bFaster
                    ? `${driver_b.driver_name.split(' ').pop()} faster`
                    : 'equal'}
              </p>
            </>
          )}
        </div>
        <div className={`bg-gray-900 px-5 py-3 text-left ${!bFaster && aFaster ? 'opacity-50' : ''}`}>
          <p className={`font-semibold text-sm ${bFaster ? 'text-white' : 'text-gray-300'}`}>
            {driver_b.driver_name}
            {driver_b.is_favourite && <span className="text-red-500 ml-1.5 text-xs">★</span>}
          </p>
          <p className="text-gray-600 font-mono text-xs">#{driver_b.driver_number}</p>
        </div>
      </div>

      {/* Stats */}
      <div className="divide-y divide-gray-800/30">
        {statRows.map(row => (
          <div key={row.label} className="grid grid-cols-3 items-center">
            <div className="px-5 py-2 text-right font-mono text-gray-300 text-xs">{row.a}</div>
            <div className="px-3 py-2 text-center text-gray-600 text-xs">{row.label}</div>
            <div className="px-5 py-2 text-left font-mono text-gray-300 text-xs">{row.b}</div>
          </div>
        ))}
      </div>

      {/* Delta footnote */}
      <div className="px-5 py-2.5 border-t border-gray-800/50 flex items-center justify-center gap-5 text-xs flex-wrap">
        {fastest_delta != null && (
          <span className="text-gray-600">
            Fastest Δ: <span className="font-mono text-gray-400">{formatDelta(fastest_delta)}</span>
          </span>
        )}
        {avg_delta != null && (
          <span className="text-gray-600">
            Avg Δ: <span className="font-mono text-gray-400">{formatDelta(avg_delta)}</span>
          </span>
        )}
        <span className="text-gray-700 italic">negative = Driver 1 faster</span>
      </div>

      {/* Stint breakdown */}
      {hasStints && (
        <div className="border-t border-gray-800/50">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-px bg-gray-800/50">
            <div className="bg-gray-900 px-5 py-4">
              <p className="text-xs text-gray-600 mb-2">{driver_a.driver_name} — stints</p>
              <CompoundSequence stints={driver_a_stints} />
              <StintMiniTable stints={driver_a_stints} />
            </div>
            <div className="bg-gray-900 px-5 py-4">
              <p className="text-xs text-gray-600 mb-2">{driver_b.driver_name} — stints</p>
              <CompoundSequence stints={driver_b_stints} />
              <StintMiniTable stints={driver_b_stints} />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function DriverComparisonSection({
  drivers,
  sessionId,
  token,
}: {
  drivers: AnalyticsDriverSummary[]
  sessionId: number
  token: string | null | undefined
}) {
  const [d1, setD1] = useState<string>('')
  const [d2, setD2] = useState<string>('')
  const [result, setResult] = useState<DriverComparisonAnalytics | null>(null)
  const [comparing, setComparing] = useState(false)
  const [compareError, setCompareError] = useState<string | null>(null)

  function handleChange(which: 'a' | 'b', value: string) {
    if (which === 'a') setD1(value)
    else setD2(value)
    setResult(null)
    setCompareError(null)
  }

  function handleCompare() {
    const num1 = Number(d1)
    const num2 = Number(d2)
    if (!num1 || !num2 || num1 === num2) return
    setComparing(true)
    setResult(null)
    setCompareError(null)
    compareSessionDrivers(sessionId, num1, num2, token)
      .then(setResult)
      .catch((e: Error) => setCompareError(e.message))
      .finally(() => setComparing(false))
  }

  const sameDriver = d1 !== '' && d2 !== '' && d1 === d2
  const canCompare = d1 !== '' && d2 !== '' && !sameDriver && !comparing
  const sortedDrivers = [...drivers].sort((a, b) => a.driver_name.localeCompare(b.driver_name))

  const selectClass =
    'w-full bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-gray-500 transition-colors'

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-800">
        <h2 className="text-sm font-semibold text-white">Driver Comparison</h2>
        <span className="text-xs font-mono text-gray-500">head to head</span>
      </div>

      <div className="px-5 py-4">
        {drivers.length < 2 ? (
          <p className="text-sm text-gray-600 text-center py-4">
            Lap data for at least two drivers is required to compare.
          </p>
        ) : (
          <>
            <div className="flex flex-col sm:flex-row items-stretch sm:items-end gap-3">
              <div className="flex-1">
                <label className="block text-xs text-gray-600 mb-1.5">Driver 1</label>
                <select value={d1} onChange={e => handleChange('a', e.target.value)} className={selectClass}>
                  <option value="">Select driver...</option>
                  {sortedDrivers.map(d => (
                    <option key={d.driver_number} value={d.driver_number}>
                      {d.driver_name} #{d.driver_number}
                    </option>
                  ))}
                </select>
              </div>

              <div className="hidden sm:flex items-center pb-2 px-1 text-gray-700 text-sm font-mono shrink-0">
                vs
              </div>

              <div className="flex-1">
                <label className="block text-xs text-gray-600 mb-1.5">Driver 2</label>
                <select value={d2} onChange={e => handleChange('b', e.target.value)} className={selectClass}>
                  <option value="">Select driver...</option>
                  {sortedDrivers.map(d => (
                    <option key={d.driver_number} value={d.driver_number}>
                      {d.driver_name} #{d.driver_number}
                    </option>
                  ))}
                </select>
              </div>

              <button
                onClick={handleCompare}
                disabled={!canCompare}
                className={`sm:w-auto w-full px-5 py-2 rounded-lg text-sm font-medium transition-colors shrink-0 ${
                  canCompare
                    ? 'bg-red-900 hover:bg-red-800 text-white border border-red-700'
                    : 'bg-gray-800 text-gray-600 border border-gray-700 cursor-not-allowed'
                }`}
              >
                {comparing ? 'Loading…' : 'Compare Drivers'}
              </button>
            </div>

            {sameDriver && (
              <p className="text-xs text-amber-500 mt-2">Please select two different drivers.</p>
            )}
          </>
        )}
      </div>

      {compareError && (
        <div className="px-5 pb-4">
          <p className="text-red-400 text-xs bg-red-950/30 border border-red-900/50 rounded-lg px-3 py-2 leading-relaxed">
            {compareError}
          </p>
        </div>
      )}

      {result && <ComparisonResult result={result} />}
    </div>
  )
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div>
        <div className="h-3 w-24 bg-gray-800 rounded mb-6" />
        <div className="h-8 w-80 bg-gray-800 rounded mb-2" />
        <div className="h-4 w-56 bg-gray-800 rounded mb-1" />
        <div className="h-3 w-40 bg-gray-800 rounded" />
      </div>
      <div className="grid grid-cols-3 gap-px bg-gray-800/50 border border-gray-800 rounded-xl overflow-hidden">
        {[0, 1, 2].map(i => <div key={i} className="bg-gray-900 h-20" />)}
      </div>
      {[0, 1, 2, 3].map(i => (
        <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl h-40" />
      ))}
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AnalyticsDashboardPage() {
  const { id } = useParams<{ id: string }>()
  const sessionId = Number(id)
  const { token, loading: authLoading } = useAuth()

  const [analytics, setAnalytics] = useState<SessionAnalytics | null>(null)
  const [tires, setTires] = useState<AnalyticsTireSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (authLoading || !sessionId) return
    setLoading(true)
    setError(null)

    Promise.all([
      getSessionAnalytics(sessionId, token),
      getSessionTireAnalytics(sessionId, token),
    ])
      .then(([analyticsData, tireData]) => {
        setAnalytics(analyticsData)
        setTires(tireData)
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [sessionId, token, authLoading])

  if (loading || authLoading) {
    return <div className="page-enter"><LoadingSkeleton /></div>
  }

  if (error || !analytics) {
    return (
      <div className="page-enter">
        <Link to="/calendar" className="text-xs text-gray-600 hover:text-gray-400 transition-colors">
          ← Calendar
        </Link>
        <div className="mt-8 text-center">
          <p className="text-red-400 font-medium">Analytics data not found</p>
          {error && <p className="text-gray-600 text-sm mt-1">{error}</p>}
        </div>
      </div>
    )
  }

  const {
    session_id,
    session_name,
    session_type,
    race_name,
    circuit_short_name,
    country_name,
    start_time,
    is_synced,
    has_lap_data,
    has_rc_data,
    has_weather_data,
    session_fastest_lap,
    session_fastest_driver,
    session_avg_lap,
    driver_pace,
    tire_analytics,
    teammate_comparisons,
    race_context,
    weather,
    data_note,
  } = analytics

  // Prefer tire-endpoint data when available, fall back to main response
  const compoundPace = tires?.compound_pace ?? tire_analytics.compound_pace
  const hasCompoundPace = tires?.has_compound_pace ?? tire_analytics.has_compound_pace

  return (
    <div className="page-enter space-y-6">

      {/* Navigation */}
      <div className="flex items-center gap-4 text-xs flex-wrap">
        <Link to="/calendar" className="text-gray-600 hover:text-gray-400 transition-colors">
          ← Calendar
        </Link>
        <Link
          to={`/sessions/${session_id}/dashboard`}
          className="text-gray-600 hover:text-gray-400 transition-colors ml-auto"
        >
          Session dashboard →
        </Link>
        <Link
          to={`/sessions/${session_id}/strategy`}
          className="text-gray-600 hover:text-gray-400 transition-colors"
        >
          Strategy →
        </Link>
      </div>

      {/* Session header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs text-gray-600 uppercase tracking-wider mb-1 font-mono">
            Advanced Analytics · {session_type}
          </p>
          <h1 className="text-2xl font-bold text-white">{session_name}</h1>
          <p className="text-gray-400 text-sm mt-0.5">
            {race_name}
            {circuit_short_name && ` · ${circuit_short_name}`}
            {country_name && `, ${country_name}`}
          </p>
          <p className="text-gray-600 text-xs mt-1 font-mono">{formatDate(start_time)}</p>
        </div>
        <div className="shrink-0">
          {is_synced ? (
            <span className="text-xs bg-green-950 text-green-400 border border-green-800 px-2.5 py-1 rounded-full">
              Synced
            </span>
          ) : (
            <span className="text-xs bg-gray-800 text-gray-500 border border-gray-700 px-2.5 py-1 rounded-full">
              Not synced
            </span>
          )}
        </div>
      </div>

      {/* Not synced notice */}
      {!is_synced && (
        <div className="bg-amber-950/30 border border-amber-800/40 rounded-xl px-5 py-4">
          <p className="text-amber-400 text-sm font-medium">No historical data available</p>
          <p className="text-amber-600/70 text-xs mt-1 leading-relaxed">
            This session has not been synced from OpenF1. Run{' '}
            <code className="text-amber-500/80 font-mono">
              python scripts/sync_openf1_session.py --session-key &lt;key&gt;
            </code>{' '}
            to ingest lap, stint, race control, and weather data.
          </p>
        </div>
      )}

      {/* Data quality note */}
      {data_note && (
        <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl px-5 py-3 flex items-start gap-3">
          <span className="text-gray-500 text-xs mt-0.5 shrink-0">ℹ</span>
          <p className="text-gray-400 text-xs leading-relaxed">{data_note}</p>
        </div>
      )}

      {/* Session pace summary */}
      <SessionPaceSummary
        fastestLap={session_fastest_lap}
        fastestDriver={session_fastest_driver}
        avgLap={session_avg_lap}
        hasData={has_lap_data}
      />

      {/* Charts */}
      <ChartsSection
        drivers={driver_pace}
        compounds={compoundPace}
        hasLapData={has_lap_data}
        hasCompoundPace={hasCompoundPace}
      />

      {/* Driver pace table */}
      <DriverPaceTable drivers={driver_pace} />

      {/* Driver comparison */}
      {has_lap_data && (
        <DriverComparisonSection
          drivers={driver_pace}
          sessionId={session_id}
          token={token}
        />
      )}

      {/* Compound pace */}
      <CompoundPaceSection
        compounds={compoundPace}
        hasCompoundPace={hasCompoundPace}
      />

      {/* Teammate comparisons */}
      <TeammateComparisonsSection comparisons={teammate_comparisons} />

      {/* Race control context */}
      {has_rc_data ? (
        <RaceControlContextSection rc={race_context} />
      ) : (
        <SectionCard
          title="Race Control Context"
          empty
          emptyMessage="No race control messages have been synced for this session."
        />
      )}

      {/* Weather */}
      {has_weather_data && weather ? (
        <WeatherSection weather={weather} />
      ) : (
        <SectionCard
          title="Latest Weather"
          empty
          emptyMessage="No weather data has been synced for this session."
        />
      )}

      {/* Footnote */}
      <p className="text-xs text-center text-gray-700 pb-2">
        Analytics are derived from stored OpenF1 data only. No lap times, sector times, or
        comparisons are invented. Data gaps are shown as empty sections above.
      </p>

    </div>
  )
}
