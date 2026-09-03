'use client'

import { Calendar, Clock, Play, Power, RotateCcw, Zap } from 'lucide-react'
import type { ScheduleState } from '@/lib/terranode-api'

interface ScheduleCardProps {
  schedule: ScheduleState
  busyId: string
  onTrigger: (scheduleId: string) => void
  onToggle: (scheduleId: string) => void
}

export function ScheduleCard({
  schedule,
  busyId,
  onTrigger,
  onToggle,
}: ScheduleCardProps) {
  const isBusy = busyId === `sched-${schedule.id}`

  // Format frequency information
  const frequencyInfo: string[] = []
  if (schedule.time) frequencyInfo.push(`Hora: ${schedule.time}`)
  if (schedule.cron) frequencyInfo.push(`Cron: ${schedule.cron}`)
  if (schedule.interval) frequencyInfo.push(`Cada ${schedule.interval}s`)
  if (schedule.days && schedule.days.length > 0) {
    frequencyInfo.push(`Días: ${schedule.days.join(', ')}`)
  }

  const formattedLastRun = schedule.last_run_timestamp
    ? new Date(schedule.last_run_timestamp * 1000).toLocaleString()
    : 'Nunca ejecutado'

  return (
    <article className="device-card bg-[var(--card)] border border-[var(--border)] rounded p-4 relative flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Clock size={18} className="text-[var(--accent)]" />
            <h4 className="font-mono font-bold text-[14px] text-[var(--foreground)] truncate max-w-[200px]" title={schedule.id}>
              {schedule.id}
            </h4>
          </div>

          <span
            className={`status-pill ${
              schedule.is_duration_active
                ? 'text-amber-400'
                : schedule.enabled
                ? ''
                : 'text-destructive'
            }`}
          >
            <i
              className={
                schedule.is_duration_active
                  ? 'bg-amber-400 animate-ping'
                  : schedule.enabled
                  ? ''
                  : 'bg-destructive shadow-none'
              }
            />
            {schedule.is_duration_active
              ? 'DURACIÓN ACTIVA'
              : schedule.enabled
              ? 'ACTIVO'
              : 'PAUSADO'}
          </span>
        </div>

        <div className="text-[11px] font-mono text-[var(--muted-foreground)] space-y-1 mb-4 bg-[#050e12] p-2.5 rounded border border-[var(--border)]">
          <div className="flex justify-between">
            <span>OBJETIVO:</span>
            <strong className="text-[var(--foreground)]">{schedule.device}</strong>
          </div>
          <div className="flex justify-between">
            <span>INICIO:</span>
            <strong className="text-[var(--primary)]">{schedule.command}</strong>
          </div>
          {schedule.stop_command && (
            <div className="flex justify-between">
              <span>PARADA ({schedule.duration_seconds}s):</span>
              <strong className="text-amber-400">{schedule.stop_command}</strong>
            </div>
          )}
        </div>

        <div className="text-[10px] font-mono text-[var(--muted-foreground)] space-y-1 mb-4">
          <div className="flex items-center gap-1.5 text-[var(--accent)]">
            <Calendar size={12} />
            <span>FRECUENCIA:</span>
          </div>
          <p className="pl-4 text-[11px] text-[var(--foreground)] font-semibold">
            {frequencyInfo.length > 0 ? frequencyInfo.join(' | ') : 'Manual / Sin frecuencia fija'}
          </p>
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between text-[9px] font-mono text-[var(--muted-foreground)] mb-3 pt-2 border-t border-[var(--border)]">
          <span>ÚLTIMA EJECUCIÓN:</span>
          <span>{formattedLastRun}</span>
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            className="quiet-button flex-1 justify-center text-[11px] border-[var(--border)] hover:border-[var(--accent)]"
            disabled={isBusy}
            onClick={() => onTrigger(schedule.id)}
            title="Disparar manualmente la tarea"
          >
            <Play size={13} className="text-[var(--accent)]" />
            Disparar
          </button>

          <button
            type="button"
            className={`quiet-button flex-1 justify-center text-[11px] ${
              schedule.enabled
                ? 'border-amber-900/60 text-amber-400 hover:bg-amber-950/30'
                : 'border-emerald-900/60 text-emerald-400 hover:bg-emerald-950/30'
            }`}
            disabled={isBusy}
            onClick={() => onToggle(schedule.id)}
            title={schedule.enabled ? 'Pausar automatización' : 'Activar automatización'}
          >
            <Power size={13} />
            {schedule.enabled ? 'Pausar' : 'Activar'}
          </button>
        </div>
      </div>
    </article>
  )
}
