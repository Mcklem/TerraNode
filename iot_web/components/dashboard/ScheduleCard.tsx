'use client'

import { Calendar, Clock, Pause, Play, Power, RotateCw } from 'lucide-react'
import type { ScheduleState } from '@/lib/terranode-api'

interface ScheduleCardProps {
  schedule: ScheduleState
  busyId: string
  onTrigger: (scheduleId: string) => void
  onToggle: (scheduleId: string) => void
}

function getNextExecutionText(schedule: ScheduleState): string {
  if (!schedule.enabled) {
    return 'Pausado (deshabilitado)'
  }

  // 1. Interval-based
  if (schedule.interval && schedule.interval > 0) {
    const last = schedule.last_run_timestamp ? schedule.last_run_timestamp * 1000 : Date.now()
    const nextMs = last + schedule.interval * 1000
    const diffSec = Math.round((nextMs - Date.now()) / 1000)
    if (diffSec <= 0) return 'En breve (próximo ciclo)'
    if (diffSec < 60) return `En ${diffSec}s`
    if (diffSec < 3600) return `En ${Math.round(diffSec / 60)} min`
    return `En ${(diffSec / 3600).toFixed(1)} hrs (${new Date(nextMs).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})`
  }

  // 2. Time-of-day based (e.g. "08:00")
  if (schedule.time) {
    const [hours, minutes] = schedule.time.split(':').map(Number)
    const now = new Date()
    const target = new Date()
    target.setHours(hours, minutes, 0, 0)

    // If target time today has already passed, set to tomorrow
    if (target.getTime() <= now.getTime()) {
      target.setDate(target.getDate() + 1)
    }

    // Handle specific active days if configured (e.g. ["mon", "tue"])
    if (schedule.days && schedule.days.length > 0) {
      const dayNames = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']
      const targetDays = schedule.days.map((d) => d.toLowerCase().slice(0, 3))
      let attempts = 0
      while (attempts < 7 && !targetDays.includes(dayNames[target.getDay()])) {
        target.setDate(target.getDate() + 1)
        attempts++
      }
    }

    const isToday = target.toDateString() === now.toDateString()
    const tomorrow = new Date(now)
    tomorrow.setDate(tomorrow.getDate() + 1)
    const isTomorrow = target.toDateString() === tomorrow.toDateString()

    const timeFormatted = target.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    if (isToday) return `Hoy a las ${timeFormatted}`
    if (isTomorrow) return `Mañana a las ${timeFormatted}`
    const dayName = target.toLocaleDateString('es-ES', { weekday: 'short' })
    return `${dayName} a las ${timeFormatted}`
  }

  // 3. Cron pattern
  if (schedule.cron) {
    if (schedule.cron.startsWith('*/')) {
      const mins = parseInt(schedule.cron.replace('*/', ''), 10)
      if (!isNaN(mins)) return `Cada ${mins} min`
    }
    return `Según patrón Cron (${schedule.cron})`
  }

  return 'A demanda / Manual'
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

  const formattedNextRun = getNextExecutionText(schedule)

  return (
    <article className="device-card bg-[var(--card)] border border-[var(--border)] rounded p-4 relative flex flex-col justify-between hover:border-[var(--accent)]/40 transition-all">
      <div>
        {/* Card Header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Clock size={18} className="text-[var(--accent)]" />
            <h4
              className="font-mono font-bold text-[14px] text-[var(--foreground)] truncate max-w-[190px]"
              title={schedule.id}
            >
              {schedule.id}
            </h4>
          </div>

          <span
            className={`status-pill font-mono font-bold ${
              schedule.is_duration_active
                ? 'text-amber-400 border-amber-500/50 bg-amber-950/40'
                : schedule.enabled
                ? 'text-emerald-400 border-emerald-500/50 bg-emerald-950/40'
                : 'text-destructive border-red-500/50 bg-red-950/40'
            }`}
          >
            <i
              className={
                schedule.is_duration_active
                  ? 'bg-amber-400 animate-ping'
                  : schedule.enabled
                  ? 'bg-emerald-400'
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

        {/* Target and Action Info */}
        <div className="text-[11px] font-mono text-[var(--muted-foreground)] space-y-1 mb-3.5 bg-[#050e12] p-2.5 rounded border border-[var(--border)]">
          <div className="flex justify-between">
            <span>OBJETIVO:</span>
            <strong className="text-[var(--foreground)]">{schedule.device}</strong>
          </div>
          <div className="flex justify-between">
            <span>COMANDO INICIO:</span>
            <strong className="text-[var(--primary)]">{schedule.command}</strong>
          </div>
          {schedule.stop_command && (
            <div className="flex justify-between">
              <span>COMANDO PARADA ({schedule.duration_seconds}s):</span>
              <strong className="text-amber-400">{schedule.stop_command}</strong>
            </div>
          )}
        </div>

        {/* Schedule Frequency */}
        <div className="text-[10px] font-mono text-[var(--muted-foreground)] space-y-1 mb-3.5">
          <div className="flex items-center gap-1.5 text-[var(--accent)] font-semibold">
            <Calendar size={12} />
            <span>FRECUENCIA CONFIGURADA:</span>
          </div>
          <p className="pl-4 text-[11px] text-[var(--foreground)] font-semibold">
            {frequencyInfo.length > 0 ? frequencyInfo.join(' | ') : 'Manual / Sin frecuencia fija'}
          </p>
        </div>
      </div>

      <div>
        {/* Execution Metadata (Last & Next) */}
        <div className="text-[10px] font-mono bg-[#071318] p-2 rounded border border-[var(--border)] mb-3 space-y-1.5">
          <div className="flex items-center justify-between text-[var(--muted-foreground)]">
            <span>ÚLTIMA EJECUCIÓN:</span>
            <span className="text-[var(--foreground)] font-medium">{formattedLastRun}</span>
          </div>

          <div className="flex items-center justify-between pt-1 border-t border-[var(--border)]/60">
            <span className="flex items-center gap-1 text-[var(--accent)] font-semibold">
              <RotateCw size={11} className={schedule.enabled ? 'animate-spin-slow' : ''} />
              PRÓXIMA EJECUCIÓN:
            </span>
            <span
              className={`font-bold ${
                schedule.enabled ? 'text-[var(--accent)]' : 'text-[var(--muted-foreground)] line-through'
              }`}
            >
              {formattedNextRun}
            </span>
          </div>
        </div>

        {/* Action Buttons with Fixed Height (h-9) & No-Wrap */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            className={`flex-1 h-9 flex items-center justify-center gap-1.5 text-[11px] font-mono font-semibold px-2 whitespace-nowrap rounded transition-all ${
              schedule.is_duration_active
                ? 'bg-amber-500/10 border border-amber-500/40 text-amber-400 cursor-not-allowed opacity-85'
                : 'quiet-button border border-[var(--border)] hover:border-[var(--accent)] hover:bg-[#0c1e24]'
            }`}
            disabled={isBusy || schedule.is_duration_active}
            onClick={() => onTrigger(schedule.id)}
            title={
              schedule.is_duration_active
                ? 'La automatización se encuentra actualmente en período de duración activa'
                : 'Disparar manualmente la tarea de inmediato'
            }
          >
            {schedule.is_duration_active ? (
              <>
                <RotateCw size={13} className="text-amber-400 animate-spin shrink-0" />
                <span>En Ejecución...</span>
              </>
            ) : (
              <>
                <Play size={13} className="text-[var(--accent)] fill-current shrink-0" />
                <span>Disparar Ahora</span>
              </>
            )}
          </button>

          <button
            type="button"
            className={`flex-1 h-9 flex items-center justify-center gap-1.5 text-[11px] font-mono font-bold px-2 whitespace-nowrap rounded transition-all shadow-md ${
              schedule.enabled
                ? 'bg-amber-500/20 border border-amber-500/80 text-amber-400 hover:bg-amber-500/35 hover:border-amber-400 shadow-[0_0_12px_rgba(245,158,11,0.2)]'
                : 'bg-emerald-500/20 border border-emerald-500 text-emerald-400 hover:bg-emerald-500/35 hover:border-emerald-400 shadow-[0_0_14px_rgba(16,185,129,0.3)]'
            }`}
            disabled={isBusy}
            onClick={() => onToggle(schedule.id)}
            title={schedule.enabled ? 'Pausar esta automatización' : 'Activar esta automatización'}
          >
            {schedule.enabled ? (
              <>
                <Pause size={13} className="text-amber-400 fill-amber-400/40 shrink-0" />
                <span>Pausar Schedule</span>
              </>
            ) : (
              <>
                <Power size={13} className="text-emerald-400 shrink-0" />
                <span>Activar Schedule</span>
              </>
            )}
          </button>
        </div>
      </div>
    </article>
  )
}
