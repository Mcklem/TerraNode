'use client'

import type { ScheduleHistoryRecord } from '@/lib/terranode-api'

interface SchedulesHistoryTableProps {
  records: ScheduleHistoryRecord[]
  scheduleIdFilter: string
  deviceIdFilter: string
  onScheduleIdChange: (val: string) => void
  onDeviceIdChange: (val: string) => void
  loading: boolean
}

export function SchedulesHistoryTable({
  records,
  scheduleIdFilter,
  deviceIdFilter,
  onScheduleIdChange,
  onDeviceIdChange,
  loading,
}: SchedulesHistoryTableProps) {
  return (
    <div className="history-table-wrapper">
      <div className="table-controls flex flex-wrap gap-4">
        <label className="flex items-center gap-2 text-[11px] text-[var(--muted-foreground)]">
          <span>TAREA PROGRAMADA:</span>
          <input
            type="text"
            placeholder="ej. riego_matutino_diario"
            value={scheduleIdFilter}
            onChange={(e) => onScheduleIdChange(e.target.value)}
            className="bg-[#081318] border border-[var(--border)] rounded px-2 py-1 text-[11px] text-[var(--foreground)] outline-none"
          />
        </label>

        <label className="flex items-center gap-2 text-[11px] text-[var(--muted-foreground)]">
          <span>ACTUADOR:</span>
          <input
            type="text"
            placeholder="ej. irrigation_pump"
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
            <th>SCHEDULE (ID)</th>
            <th>ACTUADOR (DEVICE)</th>
            <th>COMANDO / ACCIÓN</th>
            <th>FASE / EVENTO</th>
            <th>DURACIÓN</th>
            <th>ESTADO RESULTANTE</th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr>
              <td colSpan={8} className="text-center py-6 text-[var(--muted-foreground)]">
                Cargando historial del scheduler...
              </td>
            </tr>
          ) : records.length === 0 ? (
            <tr>
              <td colSpan={8} className="text-center py-6 text-[var(--muted-foreground)]">
                No hay historial de ejecuciones de tareas programadas registrado.
              </td>
            </tr>
          ) : (
            records.map((r: ScheduleHistoryRecord) => (
              <tr key={r.id}>
                <td className="font-mono text-[var(--muted-foreground)]">#{r.id}</td>
                <td className="font-mono text-[var(--accent)]">
                  {new Date(r.timestamp * 1000).toLocaleString()}
                </td>
                <td className="font-bold font-mono text-[var(--foreground)]">{r.schedule_id}</td>
                <td className="font-mono text-[var(--muted-foreground)]">{r.device_id}</td>
                <td className="font-mono font-bold text-[var(--primary)]">{r.action}</td>
                <td>
                  <span
                    className={`mode ${
                      r.event_type === 'TRIGGERED'
                        ? 'auto'
                        : r.event_type === 'COMPLETED'
                        ? 'manual'
                        : 'text-amber-400 border-amber-600 bg-amber-950/30'
                    }`}
                  >
                    {r.event_type}
                  </span>
                </td>
                <td className="font-mono text-[var(--muted-foreground)]">
                  {r.duration != null ? `${r.duration}s` : '—'}
                </td>
                <td>
                  <span
                    className={`status-pill ${
                      r.status === 'SUCCESS'
                        ? ''
                        : r.status === 'BLOCKED'
                        ? 'text-amber-400'
                        : 'text-destructive'
                    }`}
                  >
                    <i
                      className={
                        r.status === 'SUCCESS'
                          ? ''
                          : r.status === 'BLOCKED'
                          ? 'bg-amber-400 shadow-none'
                          : 'bg-destructive shadow-none'
                      }
                    />
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
