'use client'

import type { MeasurementRecord } from '@/lib/terranode-api'

interface MeasurementsTableProps {
  records: MeasurementRecord[]
  deviceIdFilter: string
  onDeviceIdChange: (val: string) => void
  loading: boolean
}

export function MeasurementsTable({
  records,
  deviceIdFilter,
  onDeviceIdChange,
  loading,
}: MeasurementsTableProps) {
  return (
    <div className="history-table-wrapper">
      <div className="table-controls">
        <label className="flex items-center gap-2 text-[11px] text-[var(--muted-foreground)]">
          <span>FILTRAR POR SENSOR:</span>
          <input
            type="text"
            placeholder="ej. ldr_01, environment_01"
            value={deviceIdFilter}
            onChange={(e) => onDeviceIdChange(e.target.value)}
            className="bg-[#081318] border border-[var(--border)] rounded px-2 py-1 text-[11px] text-[var(--foreground)] outline-none"
          />
        </label>
      </div>

      <table className="history-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>FECHA Y HORA</th>
            <th>SENSOR (DEVICE_ID)</th>
            <th>VALOR MEDIDO</th>
            <th>UNIDAD</th>
            <th>ESTADO</th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr>
              <td colSpan={6} className="text-center py-6 text-[var(--muted-foreground)]">
                Cargando registros de sensores...
              </td>
            </tr>
          ) : records.length === 0 ? (
            <tr>
              <td colSpan={6} className="text-center py-6 text-[var(--muted-foreground)]">
                No hay mediciones registradas en la base de datos.
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
                <td className="font-mono font-bold">
                  {r.value != null ? r.value : '—'}
                </td>
                <td className="font-mono text-[var(--muted-foreground)]">
                  {r.unit || 'raw'}
                </td>
                <td>
                  <span
                    className={`status-pill ${
                      r.status === 'OK' ? '' : 'text-destructive'
                    }`}
                  >
                    <i className={r.status !== 'OK' ? 'bg-destructive shadow-none' : ''} />
                    {r.status}
                  </span>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
