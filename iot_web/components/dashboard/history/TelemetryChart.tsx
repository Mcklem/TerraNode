'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Download, TrendingUp, RefreshCw, Activity } from 'lucide-react'
import {
  fetchDevices,
  fetchMeasurementsHistory,
  type Device,
  type MeasurementRecord,
} from '@/lib/terranode-api'

export function TelemetryChart() {
  const [sensorDevices, setSensorDevices] = useState<string[]>([])
  const [selectedDevice, setSelectedDevice] = useState<string>('')
  const [timeRangeHours, setTimeRangeHours] = useState<number>(24)

  const [measurements, setMeasurements] = useState<MeasurementRecord[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [hasCheckedInit, setHasCheckedInit] = useState<boolean>(false)

  const abortRef = useRef<AbortController | null>(null)

  // 1. Independent Discovery of Sensor Devices
  const discoverSensors = useCallback(async () => {
    try {
      const [devs, recentMeas] = await Promise.all([
        fetchDevices().catch(() => [] as Device[]),
        fetchMeasurementsHistory(undefined, 100, 0).catch(() => ({ data: [] })),
      ])

      const sensorSet = new Set<string>()

      // Prioritize sensors that already have active measurements in database
      if (Array.isArray(recentMeas?.data)) {
        recentMeas.data.forEach((m) => {
          if (m.device_id) sensorSet.add(m.device_id)
        })
      }

      // Add remaining registered sensor devices
      devs.forEach((d) => {
        if (d.type !== 'relay' && d.type !== 'servo') {
          sensorSet.add(d.id)
        }
      })

      const list = Array.from(sensorSet)
      setSensorDevices(list)

      if (list.length > 0 && !selectedDevice) {
        setSelectedDevice(list[0])
      }
    } catch {
      // Handle discovery failure gracefully
    } finally {
      setHasCheckedInit(true)
    }
  }, [selectedDevice])

  useEffect(() => {
    discoverSensors()
  }, [discoverSensors])

  // 2. Independent API Fetch for the Selected Sensor & Time Range
  const loadSensorData = useCallback(async () => {
    if (!selectedDevice) {
      setLoading(false)
      return
    }

    if (abortRef.current) {
      abortRef.current.abort()
    }
    const controller = new AbortController()
    abortRef.current = controller

    setLoading(true)

    try {
      // Dedicated API request for up to 500 measurements of this specific sensor
      const res = await fetchMeasurementsHistory(
        selectedDevice,
        500,
        0,
        controller.signal,
        'desc'
      )

      const records = Array.isArray(res?.data) ? res.data : []
      setMeasurements(records)
    } catch (e: any) {
      if (e?.name !== 'AbortError') {
        setMeasurements([])
      }
    } finally {
      setLoading(false)
    }
  }, [selectedDevice])

  useEffect(() => {
    if (selectedDevice) {
      loadSensorData()
    }
  }, [selectedDevice, loadSensorData])

  // Filter fetched measurements by time range relative to latest measurement or current time
  const filteredData = useMemo(() => {
    if (!measurements.length) return []

    const devMeasurements = measurements
      .filter((m) => m.value !== null && m.value !== undefined && !isNaN(Number(m.value)))
      .sort((a, b) => a.timestamp - b.timestamp)

    if (!devMeasurements.length) return []

    const maxTs = Math.max(...devMeasurements.map((m) => m.timestamp))
    const nowTs = Date.now() / 1000
    const anchorTime = Math.max(maxTs, nowTs)
    const cutoff = anchorTime - timeRangeHours * 3600

    return devMeasurements.filter((m) => m.timestamp >= cutoff)
  }, [measurements, timeRangeHours])

  // Compute Statistics
  const stats = useMemo(() => {
    if (!filteredData.length) return { min: 0, max: 0, avg: 0, latest: 0, count: 0, unit: '' }
    const values = filteredData.map((d) => Number(d.value))
    const min = Math.min(...values)
    const max = Math.max(...values)
    const sum = values.reduce((a, b) => a + b, 0)
    const avg = sum / values.length
    const latest = values[values.length - 1]
    const unit = filteredData[0]?.unit || ''
    return { min, max, avg, latest, count: values.length, unit }
  }, [filteredData])

  // CSV Exporter
  const downloadCSV = () => {
    if (!filteredData.length) return
    const headers = 'ID,Timestamp,Fecha_ISO,Sensor,Valor,Unidad,Estado\n'
    const rows = filteredData
      .map((m) => {
        const iso = new Date(m.timestamp * 1000).toISOString()
        return `${m.id},${m.timestamp},"${iso}","${m.device_id}",${m.value},"${m.unit || ''}","${m.status}"`
      })
      .join('\n')

    const blob = new Blob([headers + rows], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `terranode_telemetry_${selectedDevice.toLowerCase()}_${timeRangeHours}h.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  // SVG Chart points & Area polygon
  const { linePath, areaPath, points } = useMemo(() => {
    if (filteredData.length < 2) return { linePath: '', areaPath: '', points: [] }
    const width = 800
    const height = 180
    const padding = 28
    const topPadding = 24
    const bottomPadding = 32

    const values = filteredData.map((d) => Number(d.value))
    const minVal = Math.min(...values)
    const maxVal = Math.max(...values)
    const valRange = maxVal - minVal || 1

    const startTime = filteredData[0].timestamp
    const endTime = filteredData[filteredData.length - 1].timestamp
    const timeRange = endTime - startTime || 1

    const pts = filteredData.map((d) => {
      const x = padding + ((d.timestamp - startTime) / timeRange) * (width - 2 * padding)
      const y = height - bottomPadding - ((Number(d.value) - minVal) / valRange) * (height - topPadding - bottomPadding)
      return { x, y, val: Number(d.value), ts: d.timestamp }
    })

    const line = pts.map((p, idx) => `${idx === 0 ? 'M' : 'L'} ${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
    const firstX = pts[0].x.toFixed(1)
    const lastX = pts[pts.length - 1].x.toFixed(1)
    const bottomY = (height - bottomPadding).toFixed(1)

    const area = `${line} L ${lastX},${bottomY} L ${firstX},${bottomY} Z`

    return { linePath: line, areaPath: area, points: pts }
  }, [filteredData])

  // Helper for time formatting
  const formatTimeStr = (ts: number) => {
    const d = new Date(ts * 1000)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }

  const formatDateStr = (ts: number) => {
    const d = new Date(ts * 1000)
    return `${d.getDate()}/${d.getMonth() + 1} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
  }

  // If initial check done and no sensor devices exist in system at all, hide section completely
  if (hasCheckedInit && sensorDevices.length === 0) {
    return null
  }

  return (
    <div className="mb-6 rounded-lg border border-[var(--border)] bg-[#071318] p-5 shadow-lg font-sans">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 mb-4 border-b border-[var(--border)]">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-[var(--primary)]/10 text-[var(--primary)] border border-[var(--primary)]/20">
            <Activity size={18} />
          </div>
          <div>
            <p className="eyebrow font-mono text-[10px] tracking-wider text-[var(--muted-foreground)] uppercase">
              TELEMETRÍA Y ANALÍTICA DE SENSORES
            </p>
            <h3 className="text-base font-semibold text-[var(--foreground)] tracking-tight">
              Análisis Temporal: <span className="text-[var(--primary)] font-mono">{selectedDevice || 'Cargando...'}</span>
            </h3>
          </div>
        </div>

        {/* Filter Controls (Direct API Requests) */}
        <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
          {/* Sensor Selector (Strictly Sensor Devices) */}
          <select
            value={selectedDevice}
            onChange={(e) => setSelectedDevice(e.target.value)}
            disabled={loading || sensorDevices.length === 0}
            className="bg-[#050e12] border border-[var(--border)] text-[var(--foreground)] rounded px-3 py-1.5 focus:outline-none focus:border-[var(--primary)] transition-colors cursor-pointer disabled:opacity-50"
          >
            {sensorDevices.map((dev) => (
              <option key={dev} value={dev}>
                Sensor: {dev}
              </option>
            ))}
          </select>

          {/* Time Range Selector */}
          <select
            value={timeRangeHours}
            onChange={(e) => setTimeRangeHours(Number(e.target.value))}
            disabled={loading}
            className="bg-[#050e12] border border-[var(--border)] text-[var(--foreground)] rounded px-3 py-1.5 focus:outline-none focus:border-[var(--primary)] transition-colors cursor-pointer disabled:opacity-50"
          >
            <option value={1}>Última 1h</option>
            <option value={6}>Últimas 6h</option>
            <option value={24}>Últimas 24h</option>
            <option value={168}>Últimos 7 días</option>
          </select>

          <button
            type="button"
            onClick={loadSensorData}
            disabled={loading}
            className="quiet-button px-2.5 py-1.5 text-[11px]"
            title="Actualizar datos de la API"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          </button>

          {/* CSV Download Button */}
          <button
            type="button"
            onClick={downloadCSV}
            disabled={!filteredData.length}
            className="quiet-button px-3 py-1.5 text-[11px] text-[var(--primary)] border-[var(--primary)]/40 hover:bg-[var(--primary)]/10"
          >
            <Download size={13} />
            CSV
          </button>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4 font-mono">
        <div className="p-3 rounded border border-[var(--border)] bg-[#050e12]">
          <p className="text-[10px] text-[var(--muted-foreground)] uppercase">ÚLTIMO VALOR</p>
          <p className="text-lg font-bold text-[var(--primary)]">
            {stats.count ? `${stats.latest.toFixed(1)} ${stats.unit}` : '—'}
          </p>
        </div>

        <div className="p-3 rounded border border-[var(--border)] bg-[#050e12]">
          <p className="text-[10px] text-[var(--muted-foreground)] uppercase">MÍNIMO</p>
          <p className="text-lg font-bold text-[var(--foreground)]">
            {stats.count ? `${stats.min.toFixed(1)} ${stats.unit}` : '—'}
          </p>
        </div>

        <div className="p-3 rounded border border-[var(--border)] bg-[#050e12]">
          <p className="text-[10px] text-[var(--muted-foreground)] uppercase">PROMEDIO</p>
          <p className="text-lg font-bold text-[var(--accent)]">
            {stats.count ? `${stats.avg.toFixed(1)} ${stats.unit}` : '—'}
          </p>
        </div>

        <div className="p-3 rounded border border-[var(--border)] bg-[#050e12]">
          <p className="text-[10px] text-[var(--muted-foreground)] uppercase">MÁXIMO / MUESTRAS</p>
          <p className="text-lg font-bold text-[var(--foreground)]">
            {stats.count ? `${stats.max.toFixed(1)} ${stats.unit}` : '—'}
            <span className="text-xs text-[var(--muted-foreground)] font-normal ml-1.5">({stats.count})</span>
          </p>
        </div>
      </div>

      {/* SVG Chart Display with Text Scale Labels */}
      <div className="relative w-full rounded border border-[var(--border)] bg-[#04090c] p-4 overflow-hidden">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-12 text-center text-[var(--muted-foreground)] font-mono text-xs">
            <RefreshCw size={24} className="mb-2 animate-spin opacity-50 text-[var(--primary)]" />
            <p>Consultando API para telemetría de <span className="text-[var(--foreground)]">{selectedDevice}</span>...</p>
          </div>
        ) : filteredData.length >= 2 ? (
          <svg viewBox="0 0 800 180" className="w-full h-48 overflow-visible select-none">
            <defs>
              <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#9eff62" stopOpacity="0.25" />
                <stop offset="100%" stopColor="#9eff62" stopOpacity="0.0" />
              </linearGradient>
            </defs>

            {/* Grid lines */}
            <line x1="28" y1="24" x2="772" y2="24" stroke="var(--border)" strokeDasharray="3 3" opacity="0.6" />
            <line x1="28" y1="86" x2="772" y2="86" stroke="var(--border)" strokeDasharray="3 3" opacity="0.6" />
            <line x1="28" y1="148" x2="772" y2="148" stroke="var(--border)" strokeDasharray="3 3" opacity="0.6" />

            {/* Area Fill */}
            <path d={areaPath} fill="url(#chartGradient)" />

            {/* Line Path */}
            <path
              d={linePath}
              fill="none"
              stroke="#9eff62"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />

            {/* Y-Axis Value Labels in Text */}
            <text x="34" y="20" fill="var(--muted-foreground)" fontSize="9" fontFamily="var(--font-mono)">
              MÁX: {stats.max.toFixed(1)} {stats.unit}
            </text>
            <text x="34" y="82" fill="var(--muted-foreground)" fontSize="9" fontFamily="var(--font-mono)">
              PROM: {stats.avg.toFixed(1)} {stats.unit}
            </text>
            <text x="34" y="144" fill="var(--muted-foreground)" fontSize="9" fontFamily="var(--font-mono)">
              MÍN: {stats.min.toFixed(1)} {stats.unit}
            </text>

            {/* X-Axis Time Labels in Text */}
            {points.length >= 2 && (
              <g fill="var(--muted-foreground)" fontSize="9" fontFamily="var(--font-mono)">
                {/* Start Time Label */}
                <text x="28" y="172" textAnchor="start">
                  {formatDateStr(points[0].ts)}
                </text>

                {/* Mid Time Label */}
                {points.length > 2 && (
                  <text x="400" y="172" textAnchor="middle">
                    {formatTimeStr(points[Math.floor(points.length / 2)].ts)}
                  </text>
                )}

                {/* End Time Label */}
                <text x="772" y="172" textAnchor="end" fill="#9eff62" fontWeight="bold">
                  {formatTimeStr(points[points.length - 1].ts)} (Última)
                </text>
              </g>
            )}

            {/* Active Endpoint Dot */}
            {points.length > 0 && (
              <circle
                cx={points[points.length - 1].x}
                cy={points[points.length - 1].y}
                r="4.5"
                fill="#9eff62"
                stroke="#04090c"
                strokeWidth="2"
                className="animate-pulse"
              />
            )}
          </svg>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-center text-[var(--muted-foreground)] font-mono text-xs">
            <TrendingUp size={24} className="mb-2 opacity-40 text-[var(--primary)]" />
            <p>Insuficientes datos de telemetría para <span className="text-[var(--foreground)]">{selectedDevice}</span> en las últimas {timeRangeHours}h.</p>
          </div>
        )}
      </div>
    </div>
  )
}
