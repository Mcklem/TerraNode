'use client'

import { Clock, RefreshCw } from 'lucide-react'
import type { ScheduleState } from '@/lib/terranode-api'
import { ScheduleCard } from './ScheduleCard'

interface ScheduleGridProps {
  schedules: ScheduleState[]
  busyId: string
  onTrigger: (scheduleId: string) => void
  onToggle: (scheduleId: string) => void
  onRefresh?: () => void
}

export function ScheduleGrid({
  schedules,
  busyId,
  onTrigger,
  onToggle,
  onRefresh,
}: ScheduleGridProps) {
  return (
    <section className="section-block mt-10" aria-label="Tareas Programadas Activas">
      <div className="section-heading">
        <div>
          <p className="eyebrow">AUTOMATION ENGINE / TIME SCHEDULER</p>
          <h3>
            Scheduled Automations <span className="count-badge">{schedules.length}</span>
          </h3>
        </div>

        {onRefresh && (
          <button
            type="button"
            className="quiet-button"
            onClick={onRefresh}
          >
            <RefreshCw size={14} />
            Actualizar Schedules
          </button>
        )}
      </div>

      {schedules.length === 0 ? (
        <div className="bg-[var(--card)] border border-[var(--border)] rounded p-8 text-center text-[var(--muted-foreground)] font-mono text-[12px]">
          <Clock size={24} className="mx-auto mb-2 opacity-50 text-[var(--accent)]" />
          No hay tareas programadas por tiempo configuradas en la API (`/api/v1/schedules`).
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {schedules.map((schedule) => (
            <ScheduleCard
              key={schedule.id}
              schedule={schedule}
              busyId={busyId}
              onTrigger={onTrigger}
              onToggle={onToggle}
            />
          ))}
        </div>
      )}
    </section>
  )
}
