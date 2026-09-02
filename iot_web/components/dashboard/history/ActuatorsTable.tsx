'use client'

import type { ActuatorHistoryRecord } from '@/lib/terranode-api'

interface ActuatorsTableProps {
  records: ActuatorHistoryRecord[]
  deviceIdFilter: string
  sourceFilter: string
  onDeviceIdChange: (val: string) => void
  onSourceChange: (val: string) => void
  loading: boolean
}

export function ActuatorsTable({
  records,
  deviceIdFilter,
  sourceFilter,
  onDeviceIdChange,
  onSourceChange,
  loading,
}: ActuatorsTableProps) {
  return (
    <div className="history-table-wrapper">
      <div className="table-controls flex flex-wrap gap-4">
        <label className="flex items-center gap-2 text-[11px] text-[var(--muted-foreground)]">
          <span>FILTRAR POR ACTUADOR:</span>
          <input
            type="text"
            placeholder="ej. pump_01, vent_servo"
            value={deviceIdFilter}
            onChange={(e) => onDeviceIdChange(e.target.value)}
            className="bg-[#081318] border border-[var(--border)] rounded px-2 py-1 text-[11px] text-[var(--foreground)] outline-none"
          />
        </label>

        <label className="flex items-center gap-2 text-[11px] text-[var(--muted-foreground)]">
          <span>ORIGEN:</span>
          <select
            value={sourceFilter}
            onChange={(e) => onSourceChange(e.target.value)}
            className="bg-[#081318] border border-[var(--border)] rounded px-2 py-1 text-[11px] text-[var(--foreground)] outline-none"
          >
            <option value="">Todos los orígenes</option>
            <option value="LIVE_MANUAL">LIVE_MANUAL (Manual UI)</option>
            <option value="RULE_ENGINE">RULE_ENGINE (Regla)</option>
            <option value="SYSTEM">SYSTEM (Sistema)</option>
          </select>
        </label>
      </div>

      <table className="history-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>FECHA Y HORA</th>
            <th>ACTUADOR (DEVICE_ID)</th>
            <th>ACCIÓN / ESTADO APLICADO</th>
            <th>ORIGEN (SOURCE)</th>
            <th>OPERADOR / REGLA (USER_ID)</th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr>
              <td colSpan={6} className="text-center py-6 text-[var(--muted-foreground)]">
                Cargando registros de actuadores...
              </td>
            </tr>
          ) : records.length === 0 ? (
            <tr>
              <td colSpan={6} className="text-center py-6 text-[var(--muted-foreground)]">
                No hay historial de actuadores registrado.
              </td>
            </tr>
          ) : (
            records.map((r) => (
              <tr key={r.id}>
                <td className="font-mono text-[var(--muted-foreground)]">#{r.id}</td>
                <td className="font-mono text-[var(--accent)]">
                  {new Date(r.timestamp * 1000).toLocaleString()}
                </td>
                <td className="font-bold text-[var(--foreground)]">{r.device_id}</td>
                <td>
                  <span className="font-mono font-bold text-[var(--primary)]">
                    {r.state}
                  </span>
                </td>
                <td>
                  <span
                    className={`mode ${
                      r.source === 'LIVE_MANUAL' ? 'manual' : 'auto'
                    }`}
                  >
                    {r.source || 'SYSTEM'}
                  </span>
                </td>
                <td className="font-mono text-[11px] text-[var(--muted-foreground)]">
                  {r.user_id || '—'}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
