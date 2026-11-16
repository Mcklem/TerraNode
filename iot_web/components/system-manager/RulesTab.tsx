'use client'

import React, { useState } from 'react'
import {
  ArrowRight,
  Bell,
  Check,
  Globe,
  Mail,
  Plus,
  Send,
  Settings,
  Sparkles,
  Trash2,
  X,
  Zap,
} from 'lucide-react'
import type { DeviceConfig, RuleAction, RuleConfig, SchemaMetadata, WebhookConfig } from '@/lib/config-api'

interface RulesTabProps {
  rules: Record<string, RuleConfig>
  devices: Record<string, DeviceConfig>
  schema: SchemaMetadata | null
  webhooks?: Record<string, WebhookConfig>
  onChange: (updatedRules: Record<string, RuleConfig>) => void
}

export function RulesTab({
  rules,
  devices,
  schema,
  webhooks = {},
  onChange,
}: RulesTabProps) {
  const [editingRuleId, setEditingRuleId] = useState<string | null>(null)
  const [isCreating, setIsCreating] = useState(false)

  // Form State
  const [formId, setFormId] = useState('')
  const [formEnabled, setFormEnabled] = useState(true)
  const [formRetrigger, setFormRetrigger] = useState(false)
  const [formCooldown, setFormCooldown] = useState<number | string>('')
  const [formRecoveryMessage, setFormRecoveryMessage] = useState('')
  const [formSensor, setFormSensor] = useState('')
  const [formProperty, setFormProperty] = useState('value')
  const [formOperator, setFormOperator] = useState('<')
  const [formValue, setFormValue] = useState<number | string>(30)
  const [formActions, setFormActions] = useState<RuleAction[]>([])
  const [formError, setFormError] = useState<string | null>(null)

  // Filter available sensors and actuators
  const sensorDevices = Object.entries(devices).filter(([_, d]) =>
    ['ldr', 'bmp180', 'soil_moisture'].includes(d.type?.toLowerCase())
  )
  const actuatorDevices = Object.entries(devices).filter(([_, d]) =>
    ['relay', 'servo', 'led'].includes(d.type?.toLowerCase())
  )

  const operators = schema?.comparison_operators || ['<', '>', '<=', '>=', '==', '!=']

  const getValidPropertiesForSensor = (sensorId: string): string[] => {
    const dev = devices[sensorId]
    if (!dev) return ['value']
    if (dev.type === 'bmp180') return ['temperature', 'pressure', 'altitude', 'value']
    if (dev.type === 'ldr') return ['value', 'raw_value']
    return ['value']
  }

  const getValidCommandsForActuator = (actuatorId: string): string[] => {
    const dev = devices[actuatorId]
    if (!dev) return ['turn_on', 'turn_off']
    if (dev.type === 'servo') return ['set_position', 'turn_on', 'turn_off']
    return ['turn_on', 'turn_off']
  }

  const openCreateModal = () => {
    const defaultSensor = sensorDevices.length > 0 ? sensorDevices[0][0] : ''
    const defaultActuator = actuatorDevices.length > 0 ? actuatorDevices[0][0] : ''

    setFormId('')
    setFormEnabled(true)
    setFormRetrigger(false)
    setFormCooldown('')
    setFormRecoveryMessage('')
    setFormSensor(defaultSensor)
    setFormProperty('value')
    setFormOperator('<')
    setFormValue(30)
    setFormActions(
      defaultActuator
        ? [{ type: 'actuator', device: defaultActuator, command: 'turn_on', args: {} }]
        : []
    )
    setFormError(null)
    setIsCreating(true)
    setEditingRuleId(null)
  }

  const openEditModal = (ruleId: string) => {
    const rule = rules[ruleId]
    if (!rule) return

    setFormId(ruleId)
    setFormEnabled(rule.enabled ?? true)
    setFormRetrigger(rule.retrigger ?? false)
    setFormCooldown(rule.cooldown ?? '')
    setFormRecoveryMessage(rule.recovery_message ?? '')
    setFormSensor(rule.condition?.device || '')
    setFormProperty(rule.condition?.property || 'value')
    setFormOperator(rule.condition?.operator || '<')
    setFormValue(rule.condition?.value ?? 0)
    setFormActions(
      rule.actions && rule.actions.length > 0
        ? rule.actions.map((a) => {
            const isNotif = a.type === 'notification' || !!a.channel
            return {
              ...a,
              type: isNotif ? 'notification' : 'actuator',
            }
          })
        : []
    )
    setFormError(null)
    setEditingRuleId(ruleId)
    setIsCreating(false)
  }

  const handleAddActuatorAction = () => {
    const defaultActuator = actuatorDevices.length > 0 ? actuatorDevices[0][0] : ''
    if (!defaultActuator) return
    setFormActions((prev) => [
      ...prev,
      { type: 'actuator', device: defaultActuator, command: 'turn_on', args: {} },
    ])
  }

  const handleAddNotificationAction = () => {
    setFormActions((prev) => [
      ...prev,
      {
        type: 'notification',
        channel: 'telegram',
        title: 'Alerta de Regla',
        message: 'Condición cumplida para {device}: valor actual {value} (umbral {operator} {threshold})',
      },
    ])
  }

  const handleRemoveAction = (index: number) => {
    setFormActions((prev) => prev.filter((_, idx) => idx !== index))
  }

  const handleActionChange = (index: number, field: string, value: any) => {
    setFormActions((prev) => {
      const next = [...prev]
      if (field === 'type') {
        if (value === 'notification') {
          next[index] = {
            type: 'notification',
            channel: 'telegram',
            title: 'Alerta',
            message: 'Alerta en {device}: valor {value}',
          }
        } else {
          const defaultActuator = actuatorDevices.length > 0 ? actuatorDevices[0][0] : ''
          next[index] = {
            type: 'actuator',
            device: defaultActuator,
            command: 'turn_on',
            args: {},
          }
        }
      } else if (field === 'device') {
        const validCmds = getValidCommandsForActuator(value)
        next[index] = {
          ...next[index],
          device: value,
          command: validCmds[0] || 'turn_on',
          args: {},
        }
      } else if (field === 'command') {
        next[index] = {
          ...next[index],
          command: value,
        }
      } else if (field === 'target_angle') {
        next[index] = {
          ...next[index],
          args: { target_angle: Number(value) },
        }
      } else {
        next[index] = {
          ...next[index],
          [field]: value,
        }
      }
      return next
    })
  }

  const insertActionPlaceholder = (index: number, placeholder: string) => {
    setFormActions((prev) => {
      const next = [...prev]
      const curMsg = next[index].message || ''
      next[index] = {
        ...next[index],
        message: curMsg + placeholder,
      }
      return next
    })
  }

  const handleSaveModal = (e: React.FormEvent) => {
    e.preventDefault()
    const cleanId = formId.trim()
    if (!cleanId) {
      setFormError('El identificador de la regla es obligatorio.')
      return
    }

    if (isCreating && rules[cleanId]) {
      setFormError(`Ya existe una regla con el identificador '${cleanId}'.`)
      return
    }

    if (!formSensor) {
      setFormError('Debe seleccionar un sensor para la condición.')
      return
    }

    if (formActions.length === 0) {
      setFormError('La regla debe tener al menos una acción a ejecutar.')
      return
    }

    const updatedRules = { ...rules }

    if (!isCreating && editingRuleId && editingRuleId !== cleanId) {
      delete updatedRules[editingRuleId]
    }

    const cleanCooldown = formCooldown !== '' ? Number(formCooldown) : undefined
    const cleanRecovery = formRecoveryMessage.trim() || undefined

    updatedRules[cleanId] = {
      enabled: formEnabled,
      retrigger: formRetrigger,
      cooldown: cleanCooldown,
      recovery_message: cleanRecovery,
      condition: {
        device: formSensor,
        property: formProperty,
        operator: formOperator,
        value: Number(formValue),
      },
      actions: formActions.map((act) => {
        if (act.type === 'notification' || act.channel) {
          return {
            type: 'notification',
            channel: act.channel || 'all',
            webhook_id: act.webhook_id || undefined,
            title: act.title?.trim() || undefined,
            message: act.message?.trim() || 'Alerta de regla',
          }
        }
        return {
          device: act.device || '',
          command: act.command || 'turn_on',
          args: act.args && Object.keys(act.args).length > 0 ? act.args : undefined,
        }
      }),
    }

    onChange(updatedRules)
    setIsCreating(false)
    setEditingRuleId(null)
  }

  const handleDeleteRule = (ruleId: string) => {
    if (confirm(`¿Eliminar la regla de automatización '${ruleId}'?`)) {
      const updated = { ...rules }
      delete updated[ruleId]
      onChange(updated)
    }
  }

  const handleToggleEnabled = (ruleId: string) => {
    const rule = rules[ruleId]
    if (!rule) return
    const updated = {
      ...rules,
      [ruleId]: {
        ...rule,
        enabled: !(rule.enabled ?? true),
      },
    }
    onChange(updated)
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-xl border border-border bg-surface-1">
        <div>
          <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
            <Sparkles size={18} className="text-accent" />
            Reglas de Automatización de Hardware
          </h3>
          <p className="text-xs text-muted-foreground mt-1">
            Lógica reactiva local ejecutada por el motor `RuleEngine` en tiempo real, evaluando lecturas de sensores
            y disparando actuadores físicos o alertas multi-canal (Telegram, Email, Webhooks).
          </p>
        </div>

        <button
          type="button"
          onClick={openCreateModal}
          className="px-3.5 py-1.5 text-xs font-mono font-medium bg-accent text-accent-foreground rounded-lg hover:bg-accent/90 shadow-sm flex items-center gap-1.5 self-start sm:self-auto transition-colors"
        >
          <Plus size={14} /> Nueva Regla
        </button>
      </div>

      {/* Rules Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {Object.entries(rules).map(([ruleId, rule]) => {
          const isEnabled = rule.enabled ?? true
          const cond = rule.condition || { device: '?', property: 'value', operator: '==', value: 0 }
          const actions = rule.actions || []

          return (
            <div
              key={ruleId}
              className={`p-5 rounded-xl border transition-all ${
                isEnabled
                  ? 'bg-surface-1 border-border shadow-xs'
                  : 'bg-surface-1/40 border-border/50 opacity-75'
              }`}
            >
              {/* Header Card */}
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`h-2 w-2 rounded-full ${
                        isEnabled ? 'bg-emerald-400' : 'bg-zinc-600'
                      }`}
                    />
                    <h4 className="text-sm font-semibold font-mono text-foreground">{ruleId}</h4>
                  </div>
                  <div className="flex items-center gap-2 mt-1 flex-wrap">
                    {rule.retrigger && (
                      <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px] font-mono">
                        RETRIGGER
                      </span>
                    )}
                    {rule.cooldown ? (
                      <span className="px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] font-mono">
                        Cooldown: {rule.cooldown}s
                      </span>
                    ) : null}
                    {rule.recovery_message ? (
                      <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-mono">
                        Auto-Recuperación
                      </span>
                    ) : null}
                  </div>
                </div>

                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => handleToggleEnabled(ruleId)}
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
                    onClick={() => openEditModal(ruleId)}
                    className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-surface-2 transition-colors"
                  >
                    <Settings size={14} />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDeleteRule(ruleId)}
                    className="p-1.5 rounded-lg text-muted-foreground hover:text-rose-400 hover:bg-surface-2 transition-colors"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              {/* Condition & Actions Visual Pipeline */}
              <div className="mt-4 pt-3 border-t border-border/50 space-y-3 text-xs font-mono">
                {/* Condition Box */}
                <div className="p-2.5 rounded-lg bg-surface-2/60 border border-border">
                  <div className="flex items-center gap-2 text-muted-foreground text-[11px] mb-1">
                    <Zap size={12} className="text-amber-400" />
                    <span>CUANDO SE CUMPLE LA CONDICIÓN:</span>
                  </div>
                  <div className="flex items-center gap-1.5 font-bold text-foreground">
                    <span className="text-accent">{cond.device}</span>
                    <span className="text-muted-foreground font-normal">.{cond.property || 'value'}</span>
                    <span className="px-1.5 py-0.5 rounded bg-surface-3 border border-border text-foreground">
                      {cond.operator}
                    </span>
                    <span className="text-emerald-400 font-mono">{cond.value}</span>
                  </div>
                </div>

                {/* Arrow */}
                <div className="flex justify-center -my-1 text-muted-foreground/60">
                  <ArrowRight size={14} className="rotate-90" />
                </div>

                {/* Actions Box */}
                <div className="p-2.5 rounded-lg bg-surface-2/60 border border-border space-y-1.5">
                  <span className="text-muted-foreground text-[11px]">DISPARAR ACCIONES ({actions.length}):</span>
                  {actions.map((act, idx) => {
                    const isNotif = act.type === 'notification' || !!act.channel
                    if (isNotif) {
                      return (
                        <div
                          key={idx}
                          className="flex items-center justify-between py-1 px-2.5 rounded bg-surface-3/50 text-foreground border border-purple-500/20"
                        >
                          <div className="flex items-center gap-2">
                            <Bell size={12} className="text-purple-400" />
                            <span className="text-[11px]">
                              Notificación:{' '}
                              <strong className="text-purple-400 uppercase font-semibold">
                                {act.channel || 'all'}
                              </strong>
                              {act.webhook_id && (
                                <span className="text-muted-foreground ml-1 font-normal">
                                  ({act.webhook_id})
                                </span>
                              )}
                            </span>
                          </div>
                          <span className="text-[10px] text-muted-foreground max-w-[180px] truncate">
                            {act.message}
                          </span>
                        </div>
                      )
                    }

                    return (
                      <div
                        key={idx}
                        className="flex items-center justify-between py-0.5 px-2 rounded bg-surface-3/50 text-foreground"
                      >
                        <span>
                          <strong className="text-accent">{act.device}</strong> → {act.command}
                        </span>
                        {act.args && Object.keys(act.args).length > 0 && (
                          <span className="text-[10px] text-muted-foreground">
                            {JSON.stringify(act.args)}
                          </span>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          )
        })}

        {Object.keys(rules).length === 0 && (
          <div className="col-span-2 py-12 flex flex-col items-center justify-center border border-dashed border-border rounded-xl text-muted-foreground">
            <Sparkles size={32} className="mb-2 text-muted-foreground/60" />
            <p className="font-sans font-medium text-foreground text-sm">No hay reglas de automatización</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Cree reglas declarativas para responder automáticamente a lecturas de sensores.
            </p>
          </div>
        )}
      </div>

      {/* Modal Add / Edit Rule */}
      {(isCreating || editingRuleId) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4 animate-in fade-in duration-150">
          <div className="bg-surface-1 border border-border rounded-xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface-2/50">
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Sparkles size={16} className="text-accent" />
                {isCreating ? 'Crear Regla de Automatización' : `Editar Regla: ${editingRuleId}`}
              </h3>
              <button
                type="button"
                onClick={() => {
                  setIsCreating(false)
                  setEditingRuleId(null)
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

              {/* Rule ID & Enabled */}
              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2 space-y-1">
                  <label className="text-xs font-mono font-medium text-foreground">
                    Identificador de Regla (`rule_id`) *
                  </label>
                  <input
                    type="text"
                    value={formId}
                    onChange={(e) => setFormId(e.target.value)}
                    placeholder="ej. riego_automatico_suelo"
                    className="w-full px-3 py-1.5 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
                    required
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-mono font-medium text-foreground">
                    Retrigger
                  </label>
                  <label className="flex items-center gap-2 mt-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formRetrigger}
                      onChange={(e) => setFormRetrigger(e.target.checked)}
                      className="rounded border-border accent-accent h-4 w-4"
                    />
                    <span className="text-[11px] font-mono text-muted-foreground">Repetir</span>
                  </label>
                </div>
              </div>

              {/* Cooldown & Recovery */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs font-mono font-medium text-foreground">
                    Enfriamiento Anti-Spam (`cooldown` s)
                  </label>
                  <input
                    type="number"
                    min={0}
                    value={formCooldown}
                    onChange={(e) => setFormCooldown(e.target.value)}
                    placeholder="ej. 300 (5 min)"
                    className="w-full px-3 py-1.5 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
                  />
                  <p className="text-[10px] text-muted-foreground">
                    Segundos mínimos entre alertas consecutivas.
                  </p>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-mono font-medium text-foreground">
                    Aviso de Recuperación
                  </label>
                  <input
                    type="text"
                    value={formRecoveryMessage}
                    onChange={(e) => setFormRecoveryMessage(e.target.value)}
                    placeholder="Humedad normalizada: {value}%"
                    className="w-full px-3 py-1.5 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
                  />
                  <p className="text-[10px] text-muted-foreground">
                    Mensaje enviado al resolverse la condición.
                  </p>
                </div>
              </div>

              {/* Condition Builder */}
              <div className="p-3 rounded-lg border border-border bg-surface-2/40 space-y-3">
                <span className="text-xs font-mono font-semibold text-accent block">
                  CONDICIÓN DISPARADORA
                </span>

                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <label className="text-[11px] font-mono text-muted-foreground">Sensor *</label>
                    <select
                      value={formSensor}
                      onChange={(e) => {
                        const newSensor = e.target.value
                        setFormSensor(newSensor)
                        const validProps = getValidPropertiesForSensor(newSensor)
                        setFormProperty(validProps[0] || 'value')
                      }}
                      className="w-full px-2.5 py-1.5 text-xs font-mono rounded border border-border bg-surface-1 text-foreground"
                    >
                      {sensorDevices.map(([id]) => (
                        <option key={id} value={id}>
                          {id}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] font-mono text-muted-foreground">Propiedad</label>
                    <select
                      value={formProperty}
                      onChange={(e) => setFormProperty(e.target.value)}
                      className="w-full px-2.5 py-1.5 text-xs font-mono rounded border border-border bg-surface-1 text-foreground"
                    >
                      {getValidPropertiesForSensor(formSensor).map((p) => (
                        <option key={p} value={p}>
                          {p}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <label className="text-[11px] font-mono text-muted-foreground">Operador</label>
                    <select
                      value={formOperator}
                      onChange={(e) => setFormOperator(e.target.value)}
                      className="w-full px-2.5 py-1.5 text-xs font-mono rounded border border-border bg-surface-1 text-foreground font-bold"
                    >
                      {operators.map((op) => (
                        <option key={op} value={op}>
                          {op}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] font-mono text-muted-foreground">Valor Umbral</label>
                    <input
                      type="number"
                      step="any"
                      value={formValue}
                      onChange={(e) => setFormValue(e.target.value)}
                      className="w-full px-2.5 py-1.5 text-xs font-mono rounded border border-border bg-surface-1 text-foreground"
                      required
                    />
                  </div>
                </div>
              </div>

              {/* Actions Builder */}
              <div className="p-3 rounded-lg border border-border bg-surface-2/40 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-semibold text-emerald-400">
                    ACCIONES A EJECUTAR ({formActions.length})
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={handleAddActuatorAction}
                      className="text-[11px] font-mono text-accent hover:underline flex items-center gap-1"
                    >
                      <Plus size={12} /> Actuador
                    </button>
                    <span className="text-zinc-600">|</span>
                    <button
                      type="button"
                      onClick={handleAddNotificationAction}
                      className="text-[11px] font-mono text-purple-400 hover:underline flex items-center gap-1"
                    >
                      <Bell size={12} /> Notificación
                    </button>
                  </div>
                </div>

                <div className="space-y-2">
                  {formActions.map((act, idx) => {
                    const isNotification = act.type === 'notification' || !!act.channel
                    const isServo = !isNotification && devices[act.device || '']?.type === 'servo'
                    const validCommands = !isNotification ? getValidCommandsForActuator(act.device || '') : []

                    return (
                      <div
                        key={idx}
                        className={`p-3 rounded-lg border bg-surface-1 flex flex-col gap-2 ${
                          isNotification ? 'border-purple-500/30' : 'border-border'
                        }`}
                      >
                        {/* Action type switch & delete button */}
                        <div className="flex items-center justify-between gap-2 pb-1 border-b border-border/40">
                          <div className="flex items-center gap-2">
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold uppercase ${
                                isNotification
                                  ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20'
                                  : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                              }`}
                            >
                              {isNotification ? 'Notificación' : 'Actuador Hardware'}
                            </span>
                          </div>
                          <button
                            type="button"
                            onClick={() => handleRemoveAction(idx)}
                            className="p-1 rounded text-muted-foreground hover:text-rose-400"
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>

                        {/* Actuator Action Fields */}
                        {!isNotification ? (
                          <div className="space-y-2">
                            <div className="flex items-center gap-2">
                              <select
                                value={act.device}
                                onChange={(e) => handleActionChange(idx, 'device', e.target.value)}
                                className="flex-1 px-2 py-1 text-xs font-mono rounded border border-border bg-surface-2 text-foreground"
                              >
                                {actuatorDevices.map(([id]) => (
                                  <option key={id} value={id}>
                                    {id}
                                  </option>
                                ))}
                              </select>

                              <select
                                value={act.command}
                                onChange={(e) => handleActionChange(idx, 'command', e.target.value)}
                                className="flex-1 px-2 py-1 text-xs font-mono rounded border border-border bg-surface-2 text-foreground font-semibold"
                              >
                                {validCommands.map((cmd) => (
                                  <option key={cmd} value={cmd}>
                                    {cmd}
                                  </option>
                                ))}
                              </select>
                            </div>

                            {/* Servo angle argument if applicable */}
                            {isServo && act.command === 'set_position' && (
                              <div className="flex items-center gap-2 pl-1">
                                <span className="text-[10px] font-mono text-muted-foreground">
                                  Ángulo Objetivo (0°-180°):
                                </span>
                                <input
                                  type="number"
                                  min={0}
                                  max={180}
                                  value={act.args?.target_angle ?? 90}
                                  onChange={(e) =>
                                    handleActionChange(idx, 'target_angle', e.target.value)
                                  }
                                  className="w-20 px-2 py-0.5 text-xs font-mono rounded border border-border bg-surface-2 text-foreground"
                                />
                              </div>
                            )}
                          </div>
                        ) : (
                          /* Notification Action Fields */
                          <div className="space-y-2">
                            <div className="grid grid-cols-2 gap-2">
                              <div>
                                <label className="text-[10px] font-mono text-muted-foreground block mb-0.5">
                                  Canal de Envío
                                </label>
                                <select
                                  value={act.channel || 'all'}
                                  onChange={(e) => handleActionChange(idx, 'channel', e.target.value)}
                                  className="w-full px-2 py-1 text-xs font-mono rounded border border-border bg-surface-2 text-foreground font-semibold"
                                >
                                  <option value="all">Todos los Canales</option>
                                  <option value="telegram">Telegram Bot</option>
                                  <option value="email">Correo (SMTP)</option>
                                  <option value="webhook">Webhook HTTP</option>
                                </select>
                              </div>

                              {act.channel === 'webhook' && (
                                <div>
                                  <label className="text-[10px] font-mono text-muted-foreground block mb-0.5">
                                    Webhook Específico
                                  </label>
                                  <select
                                    value={act.webhook_id || ''}
                                    onChange={(e) => handleActionChange(idx, 'webhook_id', e.target.value)}
                                    className="w-full px-2 py-1 text-xs font-mono rounded border border-border bg-surface-2 text-foreground"
                                  >
                                    <option value="">Todos los Webhooks</option>
                                    {Object.entries(webhooks).map(([wId, wCfg]) => (
                                      <option key={wId} value={wId}>
                                        {wCfg.name || wId}
                                      </option>
                                    ))}
                                  </select>
                                </div>
                              )}
                            </div>

                            <div>
                              <div className="flex items-center justify-between mb-0.5">
                                <label className="text-[10px] font-mono text-muted-foreground">
                                  Mensaje de Alerta
                                </label>
                                <div className="flex gap-1">
                                  {['{device}', '{value}', '{threshold}'].map((tok) => (
                                    <button
                                      key={tok}
                                      type="button"
                                      onClick={() => insertActionPlaceholder(idx, tok)}
                                      className="text-[9px] font-mono px-1 rounded bg-surface-2 border border-border text-muted-foreground hover:text-foreground"
                                    >
                                      + {tok}
                                    </button>
                                  ))}
                                </div>
                              </div>
                              <input
                                type="text"
                                value={act.message || ''}
                                onChange={(e) => handleActionChange(idx, 'message', e.target.value)}
                                placeholder="Alerta en {device}: valor actual {value}"
                                className="w-full px-2 py-1 text-xs font-mono rounded border border-border bg-surface-2 text-foreground"
                                required
                              />
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  })}

                  {formActions.length === 0 && (
                    <p className="text-center text-[11px] font-mono text-muted-foreground py-2">
                      Sin acciones. Haga clic en &quot;Actuador&quot; o &quot;Notificación&quot;.
                    </p>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
                <button
                  type="button"
                  onClick={() => {
                    setIsCreating(false)
                    setEditingRuleId(null)
                  }}
                  className="px-4 py-2 text-xs font-medium text-muted-foreground hover:text-foreground border border-border rounded-lg"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-xs font-mono font-medium bg-accent text-accent-foreground rounded-lg hover:bg-accent/90 shadow-sm"
                >
                  Guardar Regla
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
