'use client'

import React, { useState } from 'react'
import {
  Calendar,
  Check,
  Clock,
  Hourglass,
  Plus,
  Repeat,
  Settings,
  Terminal,
  Trash2,
  X,
  Zap,
} from 'lucide-react'
import type { DeviceConfig, ScheduleConfig, SchemaMetadata } from '@/lib/config-api'

interface SchedulesTabProps {
  schedules: Record<string, ScheduleConfig>
  devices: Record<string, DeviceConfig>
  schema: SchemaMetadata | null
  onChange: (updatedSchedules: Record<string, ScheduleConfig>) => void
}

const ALL_DAYS = [
  { id: 'mon', label: 'Lun' },
  { id: 'tue', label: 'Mar' },
  { id: 'wed', label: 'Mié' },
  { id: 'thu', label: 'Jue' },
  { id: 'fri', label: 'Vie' },
  { id: 'sat', label: 'Sáb' },
  { id: 'sun', label: 'Dom' },
]

export function SchedulesTab({
  schedules,
  devices,
  schema,
  onChange,
}: SchedulesTabProps) {
  const [editingSchedId, setEditingSchedId] = useState<string | null>(null)
  const [isCreating, setIsCreating] = useState(false)

  // Form State
  const [formId, setFormId] = useState('')
  const [formEnabled, setFormEnabled] = useState(true)
  const [formDevice, setFormDevice] = useState('')
  const [formCommand, setFormCommand] = useState('turn_on')
  const [formStopCommand, setFormStopCommand] = useState('turn_off')
  const [formDuration, setFormDuration] = useState<number | string>(300)
  const [formTriggerType, setFormTriggerType] = useState<'daily' | 'interval' | 'cron'>('daily')
  const [formTime, setFormTime] = useState('08:00')
  const [formDays, setFormDays] = useState<string[]>(['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'])
  const [formInterval, setFormInterval] = useState<number | string>(7200)
  const [formRunOnStart, setFormRunOnStart] = useState(true)
  const [formCron, setFormCron] = useState('0 22 * * 1,3,5')
  const [formError, setFormError] = useState<string | null>(null)

  const actuatorDevices = Object.entries(devices).filter(([_, d]) =>
    ['relay', 'servo', 'led'].includes(d.type?.toLowerCase())
  )

  const getValidCommandsForActuator = (actuatorId: string): string[] => {
    const dev = devices[actuatorId]
    if (!dev) return ['turn_on', 'turn_off']
    if (dev.type === 'servo') return ['set_position', 'turn_on', 'turn_off']
    return ['turn_on', 'turn_off']
  }

  const openCreateModal = () => {
    const defaultActuator = actuatorDevices.length > 0 ? actuatorDevices[0][0] : ''
    setFormId('')
    setFormEnabled(true)
    setFormDevice(defaultActuator)
    setFormCommand('turn_on')
    setFormStopCommand('turn_off')
    setFormDuration(300)
    setFormTriggerType('daily')
    setFormTime('08:00')
    setFormDays(['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'])
    setFormInterval(7200)
    setFormRunOnStart(true)
    setFormCron('0 22 * * 1,3,5')
    setFormError(null)
    setIsCreating(true)
    setEditingSchedId(null)
  }

  const openEditModal = (schedId: string) => {
    const sched = schedules[schedId]
    if (!sched) return

    setFormId(schedId)
    setFormEnabled(sched.enabled ?? true)
    setFormDevice(sched.device || '')
    setFormCommand(sched.command || 'turn_on')
    setFormStopCommand(sched.stop_command || '')
    setFormDuration(sched.duration ?? 0)

    if (sched.cron) {
      setFormTriggerType('cron')
      setFormCron(sched.cron)
    } else if (sched.interval) {
      setFormTriggerType('interval')
      setFormInterval(sched.interval)
      setFormRunOnStart(sched.run_on_start ?? false)
    } else {
      setFormTriggerType('daily')
      setFormTime(sched.time || '08:00')
      setFormDays(sched.days || ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'])
    }

    setFormError(null)
    setEditingSchedId(schedId)
    setIsCreating(false)
  }

  const handleDayToggle = (dayId: string) => {
    setFormDays((prev) =>
      prev.includes(dayId) ? prev.filter((d) => d !== dayId) : [...prev, dayId]
    )
  }

  const handleSaveModal = (e: React.FormEvent) => {
    e.preventDefault()
    const cleanId = formId.trim()
    if (!cleanId) {
      setFormError('El identificador de la programación es obligatorio.')
      return
    }

    if (isCreating && schedules[cleanId]) {
      setFormError(`Ya existe una programación con el identificador '${cleanId}'.`)
      return
    }

    if (!formDevice) {
      setFormError('Debe seleccionar un actuador objetivo.')
      return
    }

    const updatedSchedules = { ...schedules }

    if (!isCreating && editingSchedId && editingSchedId !== cleanId) {
      delete updatedSchedules[editingSchedId]
    }

    const newSched: ScheduleConfig = {
      enabled: formEnabled,
      device: formDevice,
      command: formCommand,
    }

    if (formStopCommand) {
      newSched.stop_command = formStopCommand
    }

    if (Number(formDuration) > 0) {
      newSched.duration = Number(formDuration)
    }

    // Set trigger according to selected type
    if (formTriggerType === 'daily') {
      newSched.time = formTime.trim()
      if (formDays.length < 7) {
        newSched.days = formDays
      }
    } else if (formTriggerType === 'interval') {
      newSched.interval = Number(formInterval) || 3600
      newSched.run_on_start = formRunOnStart
    } else if (formTriggerType === 'cron') {
      newSched.cron = formCron.trim()
    }

    updatedSchedules[cleanId] = newSched
    onChange(updatedSchedules)
    setIsCreating(false)
    setEditingSchedId(null)
  }

  const handleDeleteSchedule = (schedId: string) => {
    if (confirm(`¿Eliminar la programación temporal '${schedId}'?`)) {
      const updated = { ...schedules }
      delete updated[schedId]
      onChange(updated)
    }
  }

  const handleToggleEnabled = (schedId: string) => {
    const sched = schedules[schedId]
    if (!sched) return
    const updated = {
      ...schedules,
      [schedId]: {
        ...sched,
        enabled: !(sched.enabled ?? true),
      },
    }
    onChange(updated)
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
            <Calendar size={18} className="text-accent" />
            Programaciones Temporales y Calendario (`schedules`)
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Automatización por hora fija del día, intervalos de repetición, temporizadores activos o expresiones cron.
          </p>
        </div>

        <button
          type="button"
          onClick={openCreateModal}
          disabled={actuatorDevices.length === 0}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-medium bg-accent text-accent-foreground hover:bg-accent/90 transition-colors shadow-sm disabled:opacity-50"
        >
          <Plus size={14} />
          <span>AÑADIR PROGRAMACIÓN</span>
        </button>
      </div>

      {/* Schedules Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {Object.entries(schedules).map(([schedId, sched]) => {
          const isEnabled = sched.enabled ?? true
          const isCron = !!sched.cron
          const isInterval = !!sched.interval
          const isDaily = !!sched.time

          return (
            <div
              key={schedId}
              className={`p-5 rounded-xl border bg-surface-1 transition-all ${
                isEnabled ? 'border-border' : 'border-border/60 opacity-75'
              }`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="p-1.5 rounded-md bg-purple-500/10 border border-purple-500/20 text-purple-400">
                      <Clock size={15} />
                    </span>
                    <h4 className="font-mono font-bold text-sm text-foreground">{schedId}</h4>
                  </div>
                  <div className="flex items-center gap-1.5 mt-1">
                    <span className="px-1.5 py-0.2 rounded text-[9px] font-mono border bg-surface-2 border-border text-muted-foreground">
                      {isCron ? 'CRON 5-CAMPOS' : isInterval ? 'INTERVALO RECURRENTE' : 'DIARIO HH:MM'}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => handleToggleEnabled(schedId)}
                    className={`px-2 py-0.5 rounded text-[10px] font-mono border transition-colors ${
                      isEnabled
                        ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                        : 'bg-surface-2 border-border text-muted-foreground'
                    }`}
                  >
                    {isEnabled ? 'ACTIVA' : 'PAUSADA'}
                  </button>
                  <button
                    type="button"
                    onClick={() => openEditModal(schedId)}
                    className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-surface-2 transition-colors"
                  >
                    <Settings size={14} />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDeleteSchedule(schedId)}
                    className="p-1.5 rounded-lg text-muted-foreground hover:text-rose-400 hover:bg-surface-2 transition-colors"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              {/* Timing Details */}
              <div className="mt-4 pt-3 border-t border-border/50 space-y-2 text-xs font-mono">
                {/* Trigger summary */}
                <div className="flex items-center justify-between p-2 rounded bg-surface-2/60 border border-border">
                  <span className="text-muted-foreground text-[11px] flex items-center gap-1">
                    <Repeat size={12} className="text-accent" /> Frecuencia de Disparo:
                  </span>
                  <strong className="text-foreground">
                    {isCron && <code>{sched.cron}</code>}
                    {isInterval && `Cada ${sched.interval}s ${sched.run_on_start ? '(con arranque)' : ''}`}
                    {isDaily && `${sched.time} ${sched.days ? `[${sched.days.join(',')}]` : '(diario)'}`}
                  </strong>
                </div>

                {/* Actuator & Command */}
                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <span className="text-muted-foreground">Actuador Objetivo: </span>
                    <strong className="text-accent">{sched.device}</strong>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Comando Inicio: </span>
                    <strong className="text-foreground">{sched.command}</strong>
                  </div>
                  {sched.duration != null && (
                    <div>
                      <span className="text-muted-foreground">Duración Activa: </span>
                      <strong className="text-foreground">{sched.duration}s</strong>
                    </div>
                  )}
                  {sched.stop_command && (
                    <div>
                      <span className="text-muted-foreground">Comando Parada: </span>
                      <strong className="text-rose-400">{sched.stop_command}</strong>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )
        })}

        {Object.keys(schedules).length === 0 && (
          <div className="col-span-2 py-12 flex flex-col items-center justify-center border border-dashed border-border rounded-xl text-muted-foreground">
            <Calendar size={32} className="mb-2 text-muted-foreground/60" />
            <p className="font-sans font-medium text-foreground text-sm">No hay programaciones temporales</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Automatice ciclos de riego, ventilación o iluminación mediante temporizadores.
            </p>
          </div>
        )}
      </div>

      {/* Modal Add / Edit Schedule */}
      {(isCreating || editingSchedId) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4 animate-in fade-in duration-150">
          <div className="bg-surface-1 border border-border rounded-xl shadow-2xl w-full max-w-2xl overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface-2/50">
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Calendar size={16} className="text-accent" />
                {isCreating ? 'Añadir Programación Temporal' : `Editar: ${editingSchedId}`}
              </h3>
              <button
                type="button"
                onClick={() => {
                  setIsCreating(false)
                  setEditingSchedId(null)
                }}
                className="p-1 rounded text-muted-foreground hover:text-foreground"
              >
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleSaveModal} className="p-6 space-y-4">
              {formError && (
                <div className="p-3 rounded-lg border border-rose-500/30 bg-rose-500/10 text-rose-300 text-xs">
                  {formError}
                </div>
              )}

              {/* ID */}
              <div className="space-y-1">
                <label className="text-xs font-mono font-medium text-foreground">
                  Identificador de Programación (`schedule_id`) *
                </label>
                <input
                  type="text"
                  value={formId}
                  onChange={(e) => setFormId(e.target.value)}
                  placeholder="ej. riego_matutino_diario"
                  className="w-full px-3 py-1.5 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
                  required
                />
              </div>

              {/* Target Actuator & Commands */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs font-mono font-medium text-foreground">Actuador *</label>
                  <select
                    value={formDevice}
                    onChange={(e) => {
                      const newAct = e.target.value
                      setFormDevice(newAct)
                      const cmds = getValidCommandsForActuator(newAct)
                      setFormCommand(cmds[0] || 'turn_on')
                      setFormStopCommand(cmds[1] || 'turn_off')
                    }}
                    className="w-full px-3 py-1.5 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
                  >
                    {actuatorDevices.map(([id]) => (
                      <option key={id} value={id}>
                        {id}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-mono font-medium text-foreground">Comando Inicio *</label>
                  <select
                    value={formCommand}
                    onChange={(e) => setFormCommand(e.target.value)}
                    className="w-full px-3 py-1.5 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground font-semibold"
                  >
                    {getValidCommandsForActuator(formDevice).map((cmd) => (
                      <option key={cmd} value={cmd}>
                        {cmd}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Duration Timer & Stop Command */}
              <div className="grid grid-cols-2 gap-3 pt-2 border-t border-border">
                <div className="space-y-1">
                  <label className="text-xs font-mono font-medium text-foreground">
                    Duración Activa (segundos)
                  </label>
                  <input
                    type="number"
                    min={0}
                    value={formDuration}
                    onChange={(e) => setFormDuration(Number(e.target.value))}
                    placeholder="900"
                    className="w-full px-3 py-1.5 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground"
                  />
                  <span className="text-[10px] text-muted-foreground">0 = sin temporizador de parada</span>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-mono font-medium text-foreground">
                    Comando al Vencer Duración
                  </label>
                  <select
                    value={formStopCommand}
                    onChange={(e) => setFormStopCommand(e.target.value)}
                    className="w-full px-3 py-1.5 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground"
                  >
                    <option value="">(Ninguno)</option>
                    {getValidCommandsForActuator(formDevice).map((cmd) => (
                      <option key={cmd} value={cmd}>
                        {cmd}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Trigger Type Selector */}
              <div className="p-3 rounded-lg border border-border bg-surface-2/40 space-y-3">
                <span className="text-xs font-mono font-semibold text-accent block">
                  TIPO DE DISPARO TEMPORAL
                </span>

                <div className="grid grid-cols-3 gap-1 p-0.5 rounded-lg bg-surface-1 border border-border">
                  <button
                    type="button"
                    onClick={() => setFormTriggerType('daily')}
                    className={`py-1 text-xs font-mono font-medium rounded transition-colors ${
                      formTriggerType === 'daily'
                        ? 'bg-accent text-accent-foreground shadow-xs'
                        : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    Hora Diaria
                  </button>
                  <button
                    type="button"
                    onClick={() => setFormTriggerType('interval')}
                    className={`py-1 text-xs font-mono font-medium rounded transition-colors ${
                      formTriggerType === 'interval'
                        ? 'bg-accent text-accent-foreground shadow-xs'
                        : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    Intervalo
                  </button>
                  <button
                    type="button"
                    onClick={() => setFormTriggerType('cron')}
                    className={`py-1 text-xs font-mono font-medium rounded transition-colors ${
                      formTriggerType === 'cron'
                        ? 'bg-accent text-accent-foreground shadow-xs'
                        : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    Cron Avanzado
                  </button>
                </div>

                {/* Daily Sub-form */}
                {formTriggerType === 'daily' && (
                  <div className="space-y-3 pt-1">
                    <div className="space-y-1">
                      <label className="text-xs font-mono font-medium text-foreground">
                        Hora de Ejecución (HH:MM 24h)
                      </label>
                      <input
                        type="text"
                        value={formTime}
                        onChange={(e) => setFormTime(e.target.value)}
                        placeholder="08:00"
                        className="w-full px-3 py-1.5 text-xs font-mono rounded border border-border bg-surface-1 text-foreground"
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="text-[11px] font-mono text-muted-foreground block">
                        Días de la Semana Activos
                      </label>
                      <div className="flex flex-wrap gap-1.5">
                        {ALL_DAYS.map((d) => {
                          const isSel = formDays.includes(d.id)
                          return (
                            <button
                              key={d.id}
                              type="button"
                              onClick={() => handleDayToggle(d.id)}
                              className={`px-2.5 py-1 text-xs font-mono rounded border transition-colors ${
                                isSel
                                  ? 'bg-accent/20 border-accent text-accent font-bold'
                                  : 'bg-surface-1 border-border text-muted-foreground hover:text-foreground'
                              }`}
                            >
                              {d.label}
                            </button>
                          )
                        })}
                      </div>
                    </div>
                  </div>
                )}

                {/* Interval Sub-form */}
                {formTriggerType === 'interval' && (
                  <div className="space-y-3 pt-1">
                    <div className="space-y-1">
                      <label className="text-xs font-mono font-medium text-foreground">
                        Periodicidad en Segundos (`interval`)
                      </label>
                      <input
                        type="number"
                        min={1}
                        value={formInterval}
                        onChange={(e) => setFormInterval(Number(e.target.value))}
                        placeholder="7200 (cada 2 horas)"
                        className="w-full px-3 py-1.5 text-xs font-mono rounded border border-border bg-surface-1 text-foreground"
                      />
                    </div>

                    <label className="flex items-center gap-2 cursor-pointer pt-1">
                      <input
                        type="checkbox"
                        checked={formRunOnStart}
                        onChange={(e) => setFormRunOnStart(e.target.checked)}
                        className="rounded border-border accent-accent h-4 w-4"
                      />
                      <span className="text-xs font-mono text-foreground">
                        Ejecutar de inmediato al arrancar el controlador (`run_on_start`)
                      </span>
                    </label>
                  </div>
                )}

                {/* Cron Sub-form */}
                {formTriggerType === 'cron' && (
                  <div className="space-y-2 pt-1">
                    <div className="space-y-1">
                      <label className="text-xs font-mono font-medium text-foreground">
                        Expresión Cron (min hora dom mes dow)
                      </label>
                      <input
                        type="text"
                        value={formCron}
                        onChange={(e) => setFormCron(e.target.value)}
                        placeholder="0 22 * * 1,3,5"
                        className="w-full px-3 py-1.5 text-xs font-mono rounded border border-border bg-surface-1 text-foreground font-bold"
                      />
                    </div>
                    <p className="text-[10px] font-mono text-muted-foreground">
                      Ejemplos: <code>0 8 * * *</code> (diario a las 8am) · <code>*/30 * * * *</code> (cada 30 min)
                    </p>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
                <button
                  type="button"
                  onClick={() => {
                    setIsCreating(false)
                    setEditingSchedId(null)
                  }}
                  className="px-4 py-2 text-xs font-medium text-muted-foreground hover:text-foreground border border-border rounded-lg"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-xs font-mono font-medium bg-accent text-accent-foreground rounded-lg hover:bg-accent/90 shadow-sm"
                >
                  Guardar Programación
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
