'use client'

import { useState } from 'react'
import {
  Activity,
  ArrowUpRight,
  Gauge,
  Lightbulb,
  RotateCcw,
  SlidersHorizontal,
  Thermometer,
  Zap,
} from 'lucide-react'
import {
  deviceValue,
  getDeviceMetrics,
  type Device,
  type Mode,
} from '@/lib/terranode-api'

interface DeviceCardProps {
  device: Device
  onCommand: (
    device: Device,
    action: string,
    params?: Record<string, any>,
    targetMode?: Mode,
    ttlSeconds?: number | null
  ) => void
  onRestore: (id: string) => void
  busy: boolean
}

const iconFor = (type: string) => {
  switch (type) {
    case 'relay':
      return Zap
    case 'servo':
      return SlidersHorizontal
    case 'soil_moisture':
      return Activity
    case 'bmp180':
      return Thermometer
    case 'ldr':
      return Lightbulb
    default:
      return Gauge
  }
}

const TTL_OPTIONS = [
  { label: '5 min', value: 300 },
  { label: '1 min', value: 60 },
  { label: '30 min', value: 1800 },
  { label: '1 hora', value: 3600 },
  { label: 'Indefinido', value: null },
]

export function DeviceCard({ device, onCommand, onRestore, busy }: DeviceCardProps) {
  const Icon = iconFor(device.type)
  const isRelay = device.type === 'relay'
  const isServo = device.type === 'servo'

  const [angle, setAngle] = useState<number>(device.current_state.angle ?? 45)
  const [selectedTtl, setSelectedTtl] = useState<number | null>(300)

  const metrics = getDeviceMetrics(device)
  const formattedVal = deviceValue(device)

  return (
    <article
      className={`device-card ${device.override_active ? 'is-override' : ''}`}
      aria-label={`Dispositivo ${device.id}`}
    >
      <div className="device-top">
        <div className="device-icon cyan" aria-hidden="true">
          <Icon size={18} />
        </div>
        <div>
          <span className="device-type">{device.type.toUpperCase()}</span>
          <h4>{device.id}</h4>
        </div>
        <span
          className={`mode ${device.override_active ? 'manual' : 'auto'}`}
        >
          {device.control_mode.replaceAll('_', ' ')}
        </span>
      </div>

      {!isRelay && !isServo ? (
        <>
          <div className="reading">
            <b>{formattedVal.replace(/[^0-9.-]/g, '')}</b>
            <span>
              {device.type === 'soil_moisture'
                ? '%'
                : device.type === 'bmp180'
                ? '°C'
                : 'raw'}
            </span>
          </div>

          <div className="sparkline" aria-hidden="true">
            {Array.from({ length: 10 }, (_, i) => (
              <i key={i} />
            ))}
          </div>

          <div className="reading-meta">
            <span>LIVE TELEMETRY</span>
            <span>STATUS: {device.status}</span>
          </div>

          {metrics.length > 0 && (
            <div className="mt-3 grid grid-cols-2 gap-2 border-t border-[var(--border)] pt-2 text-[10px] text-[var(--muted-foreground)]">
              {metrics.map((m) => (
                <div key={m.label}>
                  <span>{m.label}: </span>
                  <strong className="text-[var(--foreground)]">{m.value}</strong>
                </div>
              ))}
            </div>
          )}
        </>
      ) : isRelay ? (
        <div className="relay-control">
          <span>OUTPUT STATE</span>
          <b className={device.current_state.state === 'ON' ? 'on' : ''}>
            <i />
            {formattedVal}
          </b>

          <div className="relay-buttons">
            <button
              type="button"
              disabled={busy}
              className={device.current_state.state === 'ON' ? 'selected' : ''}
              onClick={() =>
                onCommand(device, 'turn_on', {}, 'MANUAL_ON', selectedTtl)
              }
            >
              Turn on
            </button>
            <button
              type="button"
              disabled={busy}
              className={device.current_state.state === 'OFF' ? 'selected-off' : ''}
              onClick={() =>
                onCommand(device, 'turn_off', {}, 'MANUAL_OFF', selectedTtl)
              }
            >
              Turn off
            </button>
          </div>

          <div className="mt-3 flex items-center justify-between text-[9px] text-[var(--muted-foreground)]">
            <span>TTL MANUAL:</span>
            <select
              className="bg-[#081318] border border-[var(--border)] rounded px-1 text-[10px] text-[var(--foreground)]"
              value={selectedTtl === null ? 'null' : selectedTtl}
              onChange={(e) =>
                setSelectedTtl(e.target.value === 'null' ? null : Number(e.target.value))
              }
            >
              {TTL_OPTIONS.map((opt) => (
                <option key={opt.label} value={opt.value === null ? 'null' : opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      ) : (
        <div className="servo-control">
          <div className="servo-label">
            <span>POSITION</span>
            <b>{angle}°</b>
          </div>

          <input
            aria-label={`Ángulo de servo ${device.id}`}
            type="range"
            min="0"
            max="180"
            value={angle}
            onChange={(e) => setAngle(Number(e.target.value))}
          />

          <div className="range-labels">
            <span>0°</span>
            <span>90°</span>
            <span>180°</span>
          </div>

          <div className="mt-2 flex items-center justify-between text-[9px] text-[var(--muted-foreground)]">
            <span>TTL EXPIRATION:</span>
            <select
              className="bg-[#081318] border border-[var(--border)] rounded px-1 text-[10px] text-[var(--foreground)]"
              value={selectedTtl === null ? 'null' : selectedTtl}
              onChange={(e) =>
                setSelectedTtl(e.target.value === 'null' ? null : Number(e.target.value))
              }
            >
              {TTL_OPTIONS.map((opt) => (
                <option key={opt.label} value={opt.value === null ? 'null' : opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            className="apply-button"
            disabled={busy}
            onClick={() =>
              onCommand(
                device,
                'set_position',
                { angle, target_angle: angle },
                'MANUAL_VALUE',
                selectedTtl
              )
            }
          >
            Apply angle <ArrowUpRight size={13} />
          </button>
        </div>
      )}

      {device.override_active && (
        <button
          type="button"
          className="restore-link"
          disabled={busy}
          onClick={() => onRestore(device.id)}
        >
          <RotateCcw size={13} /> Restore AUTO
        </button>
      )}

      <div className="device-foot">
        <span>NODO: {device.node_id}</span>
        <span className="connected-dot">{device.status}</span>
      </div>
    </article>
  )
}
