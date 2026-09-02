'use client'

import { formatDriverName } from '@/lib/constants'
import type { NodeHistoryRecord } from '@/lib/terranode-api'

interface NodesHistoryTableProps {
  records: NodeHistoryRecord[]
  nodeIdFilter: string
  onNodeIdChange: (val: string) => void
  loading: boolean
}

export function NodesHistoryTable({
  records,
  nodeIdFilter,
  onNodeIdChange,
  loading,
}: NodesHistoryTableProps) {
  return (
    <div className="history-table-wrapper">
      <div className="table-controls">
        <label className="flex items-center gap-2 text-[11px] text-[var(--muted-foreground)]">
          <span>FILTRAR POR NODO:</span>
          <input
            type="text"
            placeholder="ej. weather_01"
            value={nodeIdFilter}
            onChange={(e) => onNodeIdChange(e.target.value)}
            className="bg-[#081318] border border-[var(--border)] rounded px-2 py-1 text-[11px] text-[var(--foreground)] outline-none"
          />
        </label>
      </div>

      <table className="history-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>FECHA Y HORA</th>
            <th>NODO (NODE_ID)</th>
            <th>DIRECCIÓN IP / PUERTO</th>
            <th>DRIVER HARDARE</th>
            <th>EVENTO DE CONEXIÓN</th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr>
              <td colSpan={6} className="text-center py-6 text-[var(--muted-foreground)]">
                Cargando historial de conexiones de nodos...
              </td>
            </tr>
          ) : records.length === 0 ? (
            <tr>
              <td colSpan={6} className="text-center py-6 text-[var(--muted-foreground)]">
                No hay eventos de conexión registrados.
              </td>
            </tr>
          ) : (
            records.map((r) => (
              <tr key={r.id}>
                <td className="font-mono text-[var(--muted-foreground)]">#{r.id}</td>
                <td className="font-mono text-[var(--accent)]">
                  {new Date(r.timestamp * 1000).toLocaleString()}
                </td>
                <td className="font-bold text-[var(--foreground)]">{r.node_id}</td>
                <td className="font-mono text-[var(--muted-foreground)]">
                  {r.host}:{r.port}
                </td>
                <td className="font-mono">{formatDriverName(r.driver)}</td>
                <td>
                  <span
                    className={`status-pill ${
                      r.event === 'CONNECTED'
                        ? ''
                        : r.event === 'RECONNECTING'
                        ? 'text-amber-400'
                        : 'text-destructive'
                    }`}
                  >
                    <i
                      className={
                        r.event === 'CONNECTED'
                          ? ''
                          : r.event === 'RECONNECTING'
                          ? 'bg-amber-400 shadow-none'
                          : 'bg-destructive shadow-none'
                      }
                    />
                    {r.event}
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
