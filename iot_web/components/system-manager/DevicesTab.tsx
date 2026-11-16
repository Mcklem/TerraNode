'use client'

import React, { useState } from 'react'
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  Cpu,
  Gauge,
  Plus,
  Power,
  Radio,
  Settings,
  Sun,
  Thermometer,
  Trash2,
  Waves,
  X,
  Zap,
} from 'lucide-react'
import type { DeviceConfig, NodeConfig, SchemaMetadata } from '@/lib/config-api'

interface DevicesTabProps {
  devices: Record<string, DeviceConfig>
  nodes: Record<string, NodeConfig>
  schema: SchemaMetadata | null
  onChange: (updatedDevices: Record<string, DeviceConfig>) => void
}

export function DevicesTab({
  devices,
  nodes,
  schema,
  onChange,
}: DevicesTabProps) {
  const [editingDevId, setEditingDevId] = useState<string | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [filterNode, setFilterNode] = useState<string>('all')

  // Form State
  const [formId, setFormId] = useState('')
  const [formNode, setFormNode] = useState('')
  const [formType, setFormType] = useState('relay')
  const [formPin, setFormPin] = useState('D5')
  const [formPollInterval, setFormPollInterval] = useState(30)
  const [formActiveLow, setFormActiveLow] = useState(true)
  const [formAddress, setFormAddress] = useState('0x77')
  const [formOss, setFormOss] = useState(0)
  const [formMinAngle, setFormMinAngle] = useState(0)
  const [formMaxAngle, setFormMaxAngle] = useState(180)
  const [formDry, setFormDry] = useState(900)
  const [formWet, setFormWet] = useState(350)
  const [formDark, setFormDark] = useState(1024)
  const [formLight, setFormLight] = useState(100)
  const [formError, setFormError] = useState<string | null>(null)

  const availablePins = schema?.available_pins || [
    'D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'A0',
  ]

  const nodeIds = Object.keys(nodes)

  const openCreateModal = (presetNode?: string) => {
    const targetNode = presetNode || (nodeIds.length > 0 ? nodeIds[0] : '')
    setFormId('')
    setFormNode(targetNode)
    setFormType('relay')
    setFormPin('D5')
    setFormPollInterval(30)
    setFormActiveLow(true)
    setFormAddress('0x77')
    setFormOss(0)
    setFormMinAngle(0)
    setFormMaxAngle(180)
    setFormDry(900)
    setFormWet(350)
    setFormDark(1024)
    setFormLight(100)
    setFormError(null)
    setIsCreating(true)
    setEditingDevId(null)
  }

  const openEditModal = (devId: string) => {
    const dev = devices[devId]
    if (!dev) return

    setFormId(devId)
    setFormNode(dev.node || '')
    setFormType(dev.type || 'relay')
    setFormPin(dev.pin || 'D5')
    setFormPollInterval(dev.poll_interval ?? 30)
    setFormActiveLow(dev.active_low ?? true)
    setFormAddress(typeof dev.address === 'number' ? `0x${dev.address.toString(16)}` : dev.address || '0x77')
    setFormOss(dev.oss ?? 0)
    setFormMinAngle(dev.min_angle ?? 0)
    setFormMaxAngle(dev.max_angle ?? 180)
    setFormDry(dev.calibration?.dry ?? 900)
    setFormWet(dev.calibration?.wet ?? 350)
    setFormDark(dev.calibration?.dark ?? 1024)
    setFormLight(dev.calibration?.light ?? 100)
    setFormError(null)
    setEditingDevId(devId)
    setIsCreating(false)
  }

  const handleSaveModal = (e: React.FormEvent) => {
    e.preventDefault()
    const cleanId = formId.trim()
    if (!cleanId) {
      setFormError('El identificador del dispositivo es obligatorio.')
      return
    }

    if (isCreating && devices[cleanId]) {
      setFormError(`Ya existe un dispositivo con el identificador '${cleanId}'.`)
      return
    }

    if (!formNode) {
      setFormError('Debe seleccionar un nodo padre.')
      return
    }

    // Pin conflict check on same node
    if (formType !== 'bmp180') {
      for (const [otherId, otherDev] of Object.entries(devices)) {
        if (
          otherId !== (editingDevId || cleanId) &&
          otherDev.node === formNode &&
          otherDev.pin === formPin &&
          otherDev.type !== 'bmp180'
        ) {
          setFormError(
            `Conflicto de pines: El pin '${formPin}' ya está asignado al dispositivo '${otherId}' en el nodo '${formNode}'.`
          )
          return
        }
      }
    }

    const updatedDevices = { ...devices }

    if (!isCreating && editingDevId && editingDevId !== cleanId) {
      delete updatedDevices[editingDevId]
    }

    const newDevConfig: DeviceConfig = {
      type: formType,
      node: formNode,
    }

    if (formType === 'bmp180') {
      newDevConfig.bus = 'i2c'
      newDevConfig.address = formAddress.trim() || '0x77'
      newDevConfig.oss = Number(formOss) || 0
      newDevConfig.poll_interval = Number(formPollInterval) || 60
    } else {
      newDevConfig.pin = formPin
    }

    if (['ldr', 'soil_moisture'].includes(formType)) {
      newDevConfig.poll_interval = Number(formPollInterval) || 30
      if (formType === 'soil_moisture') {
        newDevConfig.calibration = { dry: Number(formDry), wet: Number(formWet) }
      } else if (formType === 'ldr') {
        newDevConfig.calibration = { dark: Number(formDark), light: Number(formLight) }
      }
    }

    if (['relay', 'led'].includes(formType)) {
      newDevConfig.active_low = formActiveLow
    }

    if (formType === 'servo') {
      newDevConfig.min_angle = Number(formMinAngle) || 0
      newDevConfig.max_angle = Number(formMaxAngle) || 180
    }

    updatedDevices[cleanId] = newDevConfig
    onChange(updatedDevices)
    setIsCreating(false)
    setEditingDevId(null)
  }

  const handleDeleteDevice = (devId: string) => {
    if (confirm(`¿Eliminar el dispositivo '${devId}'?`)) {
      const updated = { ...devices }
      delete updated[devId]
      onChange(updated)
    }
  }

  // Group devices by node
  const groupedDevices: Record<string, Array<[string, DeviceConfig]>> = {}
  Object.entries(devices).forEach(([devId, dev]) => {
    const parentNode = dev.node || 'unassigned'
    if (filterNode === 'all' || filterNode === parentNode) {
      groupedDevices[parentNode] = groupedDevices[parentNode] || []
      groupedDevices[parentNode].push([devId, dev])
    }
  })

  const getDeviceIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'ldr':
        return <Sun size={16} className="text-amber-400" />
      case 'bmp180':
        return <Thermometer size={16} className="text-cyan-400" />
      case 'soil_moisture':
        return <Waves size={16} className="text-emerald-400" />
      case 'relay':
        return <Power size={16} className="text-accent" />
      case 'servo':
        return <Gauge size={16} className="text-purple-400" />
      case 'led':
        return <Zap size={16} className="text-amber-300" />
      default:
        return <Cpu size={16} className="text-muted-foreground" />
    }
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
            <Cpu size={18} className="text-accent" />
            Sensores y Actuadores (`devices`)
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Definición de hardware acoplado a los pines GPIO / I2C de cada nodo.
          </p>
        </div>

        <div className="flex items-center gap-2 self-stretch sm:self-auto">
          {/* Node Filter */}
          <select
            value={filterNode}
            onChange={(e) => setFilterNode(e.target.value)}
            className="px-2.5 py-1.5 text-xs font-mono rounded-lg border border-border bg-surface-1 text-foreground"
          >
            <option value="all">Todos los nodos ({Object.keys(devices).length})</option>
            {nodeIds.map((n) => (
              <option key={n} value={n}>
                Nodo: {n}
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={() => openCreateModal()}
            disabled={nodeIds.length === 0}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-medium bg-accent text-accent-foreground hover:bg-accent/90 transition-colors shadow-sm disabled:opacity-50"
          >
            <Plus size={14} />
            <span>AÑADIR DISPOSITIVO</span>
          </button>
        </div>
      </div>

      {/* Grouped Devices Cards */}
      {Object.entries(groupedDevices).map(([nodeId, devList]) => (
        <div key={nodeId} className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-2">
              <Radio size={14} className="text-accent" />
              <h4 className="font-mono font-semibold text-xs text-foreground uppercase tracking-wider">
                NODO: {nodeId}
              </h4>
              <span className="text-[11px] font-mono text-muted-foreground">
                ({devList.length} dispositivos)
              </span>
            </div>
            <button
              type="button"
              onClick={() => openCreateModal(nodeId)}
              className="text-[11px] font-mono text-accent hover:underline flex items-center gap-1"
            >
              <Plus size={11} /> Añadir a este nodo
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {devList.map(([devId, dev]) => {
              const isSensor = ['ldr', 'bmp180', 'soil_moisture'].includes(dev.type?.toLowerCase())
              return (
                <div
                  key={devId}
                  className="p-4 rounded-xl border border-border bg-surface-1 hover:border-accent/40 transition-all space-y-3"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="p-2 rounded-lg border bg-surface-2 border-border">
                        {getDeviceIcon(dev.type)}
                      </div>
                      <div>
                        <h5 className="font-mono font-bold text-xs text-foreground">{devId}</h5>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <span
                            className={`px-1.5 py-0.2 rounded text-[9px] font-mono font-semibold border ${
                              isSensor
                                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                                : 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                            }`}
                          >
                            {isSensor ? 'SENSOR' : 'ACTUADOR'}
                          </span>
                          <span className="text-[10px] font-mono text-muted-foreground">
                            {dev.type}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => openEditModal(devId)}
                        className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-surface-2"
                        title="Editar dispositivo"
                      >
                        <Settings size={14} />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteDevice(devId)}
                        className="p-1 rounded text-muted-foreground hover:text-rose-400 hover:bg-surface-2"
                        title="Eliminar dispositivo"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>

                  {/* Specs */}
                  <div className="pt-2 border-t border-border/50 text-[11px] font-mono grid grid-cols-2 gap-y-1 text-muted-foreground">
                    <div>
                      <span>Pin / Bus: </span>
                      <strong className="text-foreground">
                        {dev.bus === 'i2c'
                          ? `I2C (${typeof dev.address === 'number' ? `0x${dev.address.toString(16)}` : dev.address || '0x77'})`
                          : dev.pin}
                      </strong>
                    </div>
                    {dev.poll_interval != null && (
                      <div>
                        <span>Muestreo: </span>
                        <strong className="text-foreground">{dev.poll_interval}s</strong>
                      </div>
                    )}
                    {dev.active_low != null && (
                      <div>
                        <span>Lógica: </span>
                        <strong className="text-foreground">
                          {dev.active_low ? 'active-low' : 'active-high'}
                        </strong>
                      </div>
                    )}
                    {dev.min_angle != null && (
                      <div className="col-span-2">
                        <span>Rango Servo: </span>
                        <strong className="text-foreground">
                          {dev.min_angle}° .. {dev.max_angle}°
                        </strong>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      ))}

      {Object.keys(devices).length === 0 && (
        <div className="py-12 flex flex-col items-center justify-center border border-dashed border-border rounded-xl text-muted-foreground">
          <Cpu size={32} className="mb-2 text-muted-foreground/60" />
          <p className="font-sans font-medium text-foreground text-sm">No hay dispositivos registrados</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Añada sensores y actuadores conectándolos a los nodos ESP8266.
          </p>
        </div>
      )}

      {/* Modal Add / Edit Device */}
      {(isCreating || editingDevId) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4 animate-in fade-in duration-150">
          <div className="bg-surface-1 border border-border rounded-xl shadow-2xl w-full max-w-2xl overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface-2/50">
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Cpu size={16} className="text-accent" />
                {isCreating ? 'Añadir Dispositivo Hardware' : `Editar: ${editingDevId}`}
              </h3>
              <button
                type="button"
                onClick={() => {
                  setIsCreating(false)
                  setEditingDevId(null)
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

              {/* ID & Node */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs font-mono font-medium text-foreground">
                    Identificador (`device_id`) *
                  </label>
                  <input
                    type="text"
                    value={formId}
                    onChange={(e) => setFormId(e.target.value)}
                    placeholder="ej. soil_01"
                    className="w-full px-3 py-1.5 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
                    required
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-mono font-medium text-foreground">
                    Nodo Padre *
                  </label>
                  <select
                    value={formNode}
                    onChange={(e) => setFormNode(e.target.value)}
                    className="w-full px-3 py-1.5 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
                    required
                  >
                    {nodeIds.map((n) => (
                      <option key={n} value={n}>
                        {n}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Device Type */}
              <div className="space-y-1">
                <label className="text-xs font-mono font-medium text-foreground">
                  Tipo de Dispositivo / Driver *
                </label>
                <select
                  value={formType}
                  onChange={(e) => {
                    const newType = e.target.value
                    setFormType(newType)
                    if (newType === 'ldr' || newType === 'soil_moisture') {
                      setFormPin('A0')
                    } else if (newType === 'relay') {
                      setFormPin('D5')
                    } else if (newType === 'servo') {
                      setFormPin('D6')
                    } else if (newType === 'led') {
                      setFormPin('D0')
                    }
                  }}
                  className="w-full px-3 py-1.5 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
                >
                  <optgroup label="Sensores">
                    <option value="ldr">ldr (Sensor de Luz Analógico A0)</option>
                    <option value="bmp180">bmp180 (Temperatura y Presión I2C)</option>
                    <option value="soil_moisture">soil_moisture (Humedad de Suelo A0)</option>
                  </optgroup>
                  <optgroup label="Actuadores">
                    <option value="relay">relay (Relé de Potencia Digital)</option>
                    <option value="servo">servo (Servomotor PWM 0°-180°)</option>
                    <option value="led">led (Indicador Luminoso Digital)</option>
                  </optgroup>
                </select>
              </div>

              {/* Pin Selection for Non-I2C devices */}
              {formType !== 'bmp180' ? (
                <div className="space-y-1">
                  <label className="text-xs font-mono font-medium text-foreground flex items-center justify-between">
                    <span>Pin Físico (`pin`) *</span>
                    <span className="text-[10px] text-muted-foreground">
                      {['ldr', 'soil_moisture'].includes(formType) ? 'Recomendado A0' : 'D0 a D8'}
                    </span>
                  </label>
                  <select
                    value={formPin}
                    onChange={(e) => setFormPin(e.target.value)}
                    className="w-full px-3 py-1.5 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
                  >
                    {availablePins.map((p) => (
                      <option key={p} value={p}>
                        {p}
                      </option>
                    ))}
                  </select>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-xs font-mono font-medium text-foreground">
                      Dirección I2C
                    </label>
                    <input
                      type="text"
                      value={formAddress}
                      onChange={(e) => setFormAddress(e.target.value)}
                      placeholder="0x77"
                      className="w-full px-3 py-1.5 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-mono font-medium text-foreground">
                      Oversampling (OSS)
                    </label>
                    <input
                      type="number"
                      min={0}
                      max={3}
                      value={formOss}
                      onChange={(e) => setFormOss(Number(e.target.value))}
                      className="w-full px-3 py-1.5 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground"
                    />
                  </div>
                </div>
              )}

              {/* Sensor Polling Interval */}
              {['ldr', 'bmp180', 'soil_moisture'].includes(formType) && (
                <div className="space-y-1">
                  <label className="text-xs font-mono font-medium text-foreground">
                    Intervalo de Sondeo (segundos)
                  </label>
                  <input
                    type="number"
                    min={1}
                    value={formPollInterval}
                    onChange={(e) => setFormPollInterval(Number(e.target.value))}
                    className="w-full px-3 py-1.5 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground"
                  />
                </div>
              )}

              {/* Soil Moisture Calibration */}
              {formType === 'soil_moisture' && (
                <div className="grid grid-cols-2 gap-3 pt-2 border-t border-border">
                  <div className="space-y-1">
                    <label className="text-[10px] font-mono text-muted-foreground">
                      Calibración Seco (dry)
                    </label>
                    <input
                      type="number"
                      value={formDry}
                      onChange={(e) => setFormDry(Number(e.target.value))}
                      className="w-full px-2 py-1 text-xs font-mono rounded border border-border bg-surface-2 text-foreground"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] font-mono text-muted-foreground">
                      Calibración Mojado (wet)
                    </label>
                    <input
                      type="number"
                      value={formWet}
                      onChange={(e) => setFormWet(Number(e.target.value))}
                      className="w-full px-2 py-1 text-xs font-mono rounded border border-border bg-surface-2 text-foreground"
                    />
                  </div>
                </div>
              )}

              {/* Relay & LED Active Low Toggle */}
              {['relay', 'led'].includes(formType) && (
                <div className="flex items-center justify-between p-3 rounded-lg border border-border bg-surface-2/40">
                  <div>
                    <p className="text-xs font-mono font-semibold text-foreground">
                      Lógica Invertida (`active_low`)
                    </p>
                    <p className="text-[10px] text-muted-foreground">
                      Activar si el módulo relé o LED se dispara con nivel lógico bajo (0V / LOW).
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    checked={formActiveLow}
                    onChange={(e) => setFormActiveLow(e.target.checked)}
                    className="rounded border-border accent-accent h-4 w-4"
                  />
                </div>
              )}

              {/* Servo Angles */}
              {formType === 'servo' && (
                <div className="grid grid-cols-2 gap-3 pt-2 border-t border-border">
                  <div className="space-y-1">
                    <label className="text-[10px] font-mono text-muted-foreground">
                      Ángulo Mínimo (0°..180°)
                    </label>
                    <input
                      type="number"
                      min={0}
                      max={180}
                      value={formMinAngle}
                      onChange={(e) => setFormMinAngle(Number(e.target.value))}
                      className="w-full px-2 py-1 text-xs font-mono rounded border border-border bg-surface-2 text-foreground"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] font-mono text-muted-foreground">
                      Ángulo Máximo (0°..180°)
                    </label>
                    <input
                      type="number"
                      min={0}
                      max={180}
                      value={formMaxAngle}
                      onChange={(e) => setFormMaxAngle(Number(e.target.value))}
                      className="w-full px-2 py-1 text-xs font-mono rounded border border-border bg-surface-2 text-foreground"
                    />
                  </div>
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
                <button
                  type="button"
                  onClick={() => {
                    setIsCreating(false)
                    setEditingDevId(null)
                  }}
                  className="px-4 py-2 text-xs font-medium text-muted-foreground hover:text-foreground border border-border rounded-lg"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-xs font-mono font-medium bg-accent text-accent-foreground rounded-lg hover:bg-accent/90 shadow-sm"
                >
                  Guardar Dispositivo
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
