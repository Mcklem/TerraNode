'use client'

import { Fragment, useState } from 'react'
import { ChevronDown, ChevronRight, Code } from 'lucide-react'
import type { EventRecord } from '@/lib/terranode-api'

interface EventsHistoryTableProps {
  records: EventRecord[]
  topicFilter: string
  onTopicChange: (val: string) => void
  loading: boolean
}

export function EventsHistoryTable({
  records,
  topicFilter,
  onTopicChange,
  loading,
}: EventsHistoryTableProps) {
  const [expandedId, setExpandedId] = useState<number | null>(null)

  const toggleExpand = (id: number) => {
    setExpandedId((prev) => (prev === id ? null : id))
  }

  return (
    <div className="history-table-wrapper">
      <div className="table-controls">
        <label className="flex items-center gap-2 text-[11px] text-[var(--muted-foreground)]">
          <span>FILTRAR POR TÓPICO:</span>
          <input
            type="text"
            placeholder="ej. rule.triggered, command.executed"
            value={topicFilter}
            onChange={(e) => onTopicChange(e.target.value)}
            className="bg-[#081318] border border-[var(--border)] rounded px-2 py-1 text-[11px] text-[var(--foreground)] outline-none"
          />
        </label>
      </div>

      <table className="history-table">
        <thead>
          <tr>
            <th className="w-8"></th>
            <th>ID</th>
            <th>FECHA Y HORA</th>
            <th>TÓPICO (TOPIC)</th>
            <th>EMISOR (SENDER)</th>
            <th>PAYLOAD JSON</th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr>
              <td colSpan={6} className="text-center py-6 text-[var(--muted-foreground)]">
                Cargando registro de eventos...
              </td>
            </tr>
          ) : records.length === 0 ? (
            <tr>
              <td colSpan={6} className="text-center py-6 text-[var(--muted-foreground)]">
                No hay eventos registrados en la auditoría.
              </td>
            </tr>
          ) : (
            records.map((r: EventRecord) => {
              const isExpanded = expandedId === r.id
              let parsedJson: any = null
              try {
                parsedJson = JSON.parse(r.payload)
              } catch {
                parsedJson = r.payload
              }

              return (
                <Fragment key={r.id}>
                  <tr
                    className="cursor-pointer hover:bg-[#0c1e24]"
                    onClick={() => toggleExpand(r.id)}
                  >
                    <td>
                      {isExpanded ? (
                        <ChevronDown size={14} className="text-[var(--accent)]" />
                      ) : (
                        <ChevronRight size={14} className="text-[var(--muted-foreground)]" />
                      )}
                    </td>
                    <td className="font-mono text-[var(--muted-foreground)]">#{r.id}</td>
                    <td className="font-mono text-[var(--accent)]">
                      {new Date(r.timestamp * 1000).toLocaleString()}
                    </td>
                    <td className="font-bold font-mono text-[var(--primary)]">{r.topic}</td>
                    <td className="font-mono text-[var(--muted-foreground)]">{r.sender}</td>
                    <td className="font-mono text-[10px] text-[var(--muted-foreground)] truncate max-w-[200px]">
                      {r.payload}
                    </td>
                  </tr>

                  {isExpanded && (
                    <tr key={`${r.id}-detail`}>
                      <td colSpan={6} className="bg-[#050e12] p-4 border-b border-[var(--border)]">
                        <div className="flex items-center gap-2 text-[10px] font-mono text-[var(--accent)] mb-2">
                          <Code size={13} />
                          <span>PAYLOAD DETALLADO DE EVENTO #{r.id}</span>
                        </div>
                        <pre className="bg-[#081318] p-3 rounded text-[11px] font-mono text-[var(--primary)] overflow-auto max-h-48 border border-[var(--border)]">
                          {typeof parsedJson === 'object'
                            ? JSON.stringify(parsedJson, null, 2)
                            : String(parsedJson)}
                        </pre>
                      </td>
                    </tr>
                  )}
                </Fragment>
              )
            })
          )}
        </tbody>
      </table>
    </div>
  )
}
