'use client'

import { useEffect, useState } from 'react'
import { Calendar, Clock, Pause, Play, Power, RotateCw, Timer } from 'lucide-react'
import type { ScheduleState } from '@/lib/terranode-api'

interface ScheduleCardProps {
  schedule: ScheduleState
  busyId: string
  onTrigger: (scheduleId: string) => void
  onToggle: (scheduleId: string) => void
}

const DOW_NAMES: Record<string, string> = {
  '0': 'domingos',
  '1': 'lunes',
  '2': 'martes',
  '3': 'miércoles',
  '4': 'jueves',
  '5': 'viernes',
  '6': 'sábados',
  '7': 'domingos',
}

const SPANISH_DAY_NAMES: Record<string, string> = {
  mon: 'lunes',
  tue: 'martes',
  wed: 'miércoles',
  thu: 'jueves',
  fri: 'viernes',
  sat: 'sábados',
  sun: 'domingos',
}

function matchCronField(fieldStr: string, val: number, isDow = false): boolean {
  if (fieldStr === '*') return true
  if (fieldStr.includes(',')) {
    return fieldStr.split(',').some((part) => matchCronField(part.trim(), val, isDow))
  }
  if (fieldStr.startsWith('*/')) {
    const step = parseInt(fieldStr.replace('*/', ''), 10)
    if (isNaN(step) || step <= 0) return false
    return val % step === 0
  }
  if (fieldStr.includes('-')) {
    const [low, high] = fieldStr.split('-').map(Number)
    if (isNaN(low) || isNaN(high)) return false
    return val >= low && val <= high
  }
  const num = parseInt(fieldStr, 10)
  if (isNaN(num)) return false
  if (isDow && (num === 7 || num === 0)) return val === 0 || val === 7
  return num === val
}

function getNextCronDate(cronStr: string, fromDate = new Date()): Date | null {
  const parts = cronStr.trim().split(/\s+/)
  if (parts.length !== 5) return null

  const [minPart, hourPart, domPart, monthPart, dowPart] = parts

  const iter = new Date(fromDate.getTime())
  iter.setSeconds(0, 0)
  iter.setMinutes(iter.getMinutes() + 1)

  const maxIter = 525600
  let count = 0

  while (count < maxIter) {
    const m = iter.getMinutes()
    const h = iter.getHours()
    const dom = iter.getDate()
    const month = iter.getMonth() + 1
    const dow = iter.getDay()

    if (
      matchCronField(minPart, m) &&
      matchCronField(hourPart, h) &&
      matchCronField(domPart, dom) &&
      matchCronField(monthPart, month) &&
      matchCronField(dowPart, dow, true)
    ) {
      return iter
    }

    if (!matchCronField(monthPart, month)) {
      iter.setMonth(iter.getMonth() + 1, 1)
      iter.setHours(0, 0, 0, 0)
    } else if (!matchCronField(domPart, dom) || !matchCronField(dowPart, dow, true)) {
      iter.setDate(iter.getDate() + 1)
      iter.setHours(0, 0, 0, 0)
    } else if (!matchCronField(hourPart, h)) {
      iter.setHours(iter.getHours() + 1, 0, 0, 0)
    } else {
      iter.setMinutes(iter.getMinutes() + 1)
    }
    count++
  }
  return null
}

function getCronHumanDescription(cronStr: string): string {
  const parts = cronStr.trim().split(/\s+/)
  if (parts.length !== 5) return `Cron (${cronStr})`

  const [minPart, hourPart, domPart, monthPart, dowPart] = parts

  if (minPart.startsWith('*/') && hourPart === '*' && domPart === '*' && dowPart === '*') {
    const step = minPart.replace('*/', '')
    return `Cada ${step} minutos`
  }

  if (minPart === '0' && hourPart.startsWith('*/') && domPart === '*' && dowPart === '*') {
    const step = hourPart.replace('*/', '')
    return `Cada ${step} horas`
  }

  let timeText = ''
  if (!minPart.includes('*') && !hourPart.includes('*')) {
    const hh = hourPart.padStart(2, '0')
    const mm = minPart.padStart(2, '0')
    timeText = `A las ${hh}:${mm}`
  }

  let daysText = ''
  if (dowPart !== '*') {
    const days = dowPart.split(',').map((d) => DOW_NAMES[d.trim()] || d.trim())
    if (days.length === 1) {
      daysText = `los ${days[0]}`
    } else if (days.length > 1) {
      const last = days.pop()
      daysText = `los ${days.join(', ')} y ${last}`
    }
  } else if (domPart === '*' && monthPart === '*') {
    daysText = 'todos los días'
  }

  if (timeText && daysText) {
    return `${timeText}, ${daysText}`
  }
  if (timeText) {
    return `${timeText}`
  }

  return `Cron (${cronStr})`
}

function formatDaysList(days: string[]): string {
  const translated = days.map((d) => SPANISH_DAY_NAMES[d.toLowerCase().slice(0, 3)] || d)
  if (translated.length === 7) return 'todos los días'
  if (translated.length === 1) return `los ${translated[0]}`
  const last = translated.pop()
  return `los ${translated.join(', ')} y ${last}`
}

function formatIntervalHuman(seconds: number): string {
  if (seconds < 60) return `Cada ${seconds} segundos`
  const mins = Math.floor(seconds / 60)
  if (mins < 60) return `Cada ${mins} minutos`
  const hrs = Math.floor(mins / 60)
  const remMins = mins % 60
  if (remMins === 0) return `Cada ${hrs} hora${hrs > 1 ? 's' : ''}`
  return `Cada ${hrs}h ${remMins}m`
}

export function formatScheduleFrequency(schedule: ScheduleState): { humanText: string; badgeText?: string } {
  // 1. Cron
  if (schedule.cron) {
    return {
      humanText: getCronHumanDescription(schedule.cron),
      badgeText: `cron: ${schedule.cron}`,
    }
  }

  // 2. Interval
  if (schedule.interval && schedule.interval > 0) {
    return {
      humanText: formatIntervalHuman(schedule.interval),
      badgeText: `intervalo: ${schedule.interval}s`,
    }
  }

  // 3. Time + Days
  if (schedule.time) {
    const daysStr = schedule.days && schedule.days.length > 0
      ? formatDaysList(schedule.days)
      : 'todos los días'
    return {
      humanText: `A las ${schedule.time}, ${daysStr}`,
      badgeText: `hora fija: ${schedule.time}`,
    }
  }

  return { humanText: 'Manual / A demanda' }
}

function getNextExecutionText(schedule: ScheduleState): string {
  if (!schedule.enabled) {
    return 'Pausado (deshabilitado)'
  }

  // 1. Cron pattern
  if (schedule.cron) {
    const nextDate = getNextCronDate(schedule.cron)
    if (nextDate) {
      const now = new Date()
      const diffMs = nextDate.getTime() - now.getTime()
      const diffSec = Math.round(diffMs / 1000)

      const isToday = nextDate.toDateString() === now.toDateString()
      const tomorrow = new Date(now)
      tomorrow.setDate(tomorrow.getDate() + 1)
      const isTomorrow = nextDate.toDateString() === tomorrow.toDateString()

      const timeFormatted = nextDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

      if (diffSec <= 0) return 'En breve (próximo ciclo)'
      if (diffSec < 60) return `En ${diffSec}s`
      if (isToday) return `Hoy a las ${timeFormatted}`
      if (isTomorrow) return `Mañana a las ${timeFormatted}`

      const dayName = nextDate.toLocaleDateString('es-ES', { weekday: 'short' })
      return `${dayName} a las ${timeFormatted}`
    }
    return getCronHumanDescription(schedule.cron)
  }

  // 2. Interval-based
  if (schedule.interval && schedule.interval > 0) {
    const last = schedule.last_run_timestamp ? schedule.last_run_timestamp * 1000 : Date.now()
    const nextMs = last + schedule.interval * 1000
    const diffSec = Math.round((nextMs - Date.now()) / 1000)
    if (diffSec <= 0) return 'En breve (próximo ciclo)'
    if (diffSec < 60) return `En ${diffSec}s`
    if (diffSec < 3600) return `En ${Math.round(diffSec / 60)} min`
    return `En ${(diffSec / 3600).toFixed(1)} hrs (${new Date(nextMs).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})`
  }

  // 3. Time-of-day based (e.g. "08:00")
  if (schedule.time) {
    const [hours, minutes] = schedule.time.split(':').map(Number)
    const now = new Date()
    const target = new Date()
    target.setHours(hours, minutes, 0, 0)

    if (target.getTime() <= now.getTime()) {
      target.setDate(target.getDate() + 1)
    }

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

  return 'A demanda / Manual'
}

export function ScheduleCard({
  schedule,
  busyId,
  onTrigger,
  onToggle,
}: ScheduleCardProps) {
  const isBusy = busyId === `sched-${schedule.id}`

  // Local timer state to tick every second when duration is active
  const [nowSec, setNowSec] = useState<number>(() => Math.floor(Date.now() / 1000))

  useEffect(() => {
    if (!schedule.is_duration_active) return
    const interval = setInterval(() => {
      setNowSec(Math.floor(Date.now() / 1000))
    }, 1000)
    return () => clearInterval(interval)
  }, [schedule.is_duration_active])

  // Duration progress calculations
  const totalDuration = schedule.duration_seconds || 0
  const startTs = schedule.last_run_timestamp || nowSec
  const elapsedSec = schedule.is_duration_active ? Math.max(0, nowSec - startTs) : 0
  const remainingSec = schedule.is_duration_active ? Math.max(0, totalDuration - elapsedSec) : 0
  const progressPercent =
    totalDuration > 0 && schedule.is_duration_active
      ? Math.min(100, Math.max(0, Math.round((elapsedSec / totalDuration) * 100)))
      : 0

  const formatSecs = (sec: number) => {
    const m = Math.floor(sec / 60)
    const s = Math.floor(sec % 60)
    if (m > 0) return `${m}m ${s}s`
    return `${s}s`
  }

  const freq = formatScheduleFrequency(schedule)
  const formattedLastRun = schedule.last_run_timestamp
    ? new Date(schedule.last_run_timestamp * 1000).toLocaleString()
    : 'Nunca ejecutado'

  const formattedNextRun = getNextExecutionText(schedule)

  return (
    <article
      className={`device-card bg-[var(--card)] border rounded p-4 relative flex flex-col justify-between space-y-3 transition-all ${
        schedule.is_duration_active
          ? 'border-amber-500/70 shadow-[0_0_15px_rgba(245,158,11,0.25)] bg-[#120e08]/90'
          : 'border-[var(--border)] hover:border-[var(--accent)]/40'
      }`}
    >
      <div className="space-y-3">
        {/* Card Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock size={18} className="text-[var(--accent)] shrink-0" />
            <h4
              className="font-mono font-bold text-[14px] text-[var(--foreground)] truncate max-w-[180px]"
              title={schedule.id}
            >
              {schedule.id}
            </h4>
          </div>

          <span
            className={`status-pill font-mono font-bold shrink-0 ${
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
              ? 'EJECUTANDO'
              : schedule.enabled
              ? 'ACTIVO'
              : 'PAUSADO'}
          </span>
        </div>

        {/* Target and Action Commands */}
        <div className="text-[11px] font-mono text-[var(--muted-foreground)] space-y-1 bg-[#050e12] p-2.5 rounded border border-[var(--border)]">
          <div className="flex justify-between">
            <span>OBJETIVO:</span>
            <strong className="text-[var(--foreground)] font-semibold">{schedule.device}</strong>
          </div>
          <div className="flex justify-between">
            <span>COMANDO INICIO:</span>
            <strong className="text-[var(--primary)] font-semibold">{schedule.command}</strong>
          </div>
          {schedule.stop_command && (
            <div className="flex justify-between">
              <span>COMANDO PARADA:</span>
              <strong className="text-amber-400 font-semibold">{schedule.stop_command}</strong>
            </div>
          )}
        </div>

        {/* Homogeneous Frequency and Duration Box */}
        <div className="text-[11px] font-mono text-[var(--muted-foreground)] bg-[#07151a] p-2.5 rounded border border-[var(--border)] space-y-2">
          <div className="flex items-center justify-between gap-2">
            <span className="flex items-center gap-1.5 text-[var(--accent)] font-semibold shrink-0">
              <Calendar size={12} /> FRECUENCIA:
            </span>
            <div className="text-right truncate max-w-[210px]" title={freq.humanText}>
              <strong className="text-[var(--foreground)] font-semibold block truncate">
                {freq.humanText}
              </strong>
              {freq.badgeText && (
                <span className="text-[9px] text-cyan-400 font-mono bg-cyan-950/70 px-1.5 py-0.5 rounded border border-cyan-500/40 inline-block mt-0.5">
                  {freq.badgeText}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center justify-between pt-1.5 border-t border-[var(--border)]/60">
            <span className="flex items-center gap-1.5 text-amber-400 font-semibold shrink-0">
              <Timer size={12} /> DURACIÓN:
            </span>
            <strong className="text-amber-300 font-bold font-mono">
              {schedule.duration_seconds > 0 ? formatSecs(schedule.duration_seconds) : 'Sin límite de tiempo'}
            </strong>
          </div>
        </div>

        {/* Live Duration Progress Bar (when duration is active) */}
        {schedule.is_duration_active && (
          <div className="bg-[#1c140a] border border-amber-500/60 rounded-lg p-2.5 space-y-1.5 shadow-[0_0_12px_rgba(245,158,11,0.2)]">
            <div className="flex items-center justify-between text-[10px] font-mono">
              <span className="text-amber-400 font-bold flex items-center gap-1">
                <Timer size={12} className="animate-spin text-amber-400 shrink-0" />
                TIEMPO RESTANTE: {formatSecs(remainingSec)}
              </span>
              <span className="text-amber-300 font-bold">{progressPercent}%</span>
            </div>

            {/* Progress Bar Track */}
            <div className="w-full h-2 bg-[#0e0a05] rounded-full overflow-hidden border border-amber-500/40">
              <div
                className="h-full bg-gradient-to-r from-amber-500 via-amber-400 to-yellow-300 rounded-full transition-all duration-1000 ease-linear shadow-[0_0_8px_rgba(245,158,11,0.6)]"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>
        )}

        {/* Execution History Metadata (Last & Next) */}
        <div className="text-[10px] font-mono bg-[#071318] p-2 rounded border border-[var(--border)] space-y-1.5">
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
      </div>

      {/* Action Buttons */}
      <div className="flex items-center gap-2 pt-2">
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
    </article>
  )
}
