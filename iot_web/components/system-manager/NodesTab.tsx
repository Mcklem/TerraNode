'use client'

import React, { useState } from 'react'
import {
  AlertTriangle,
  Check,
  Eye,
  EyeOff,
  Key,
  Lock,
  Plus,
  Radio,
  Settings,
  Shield,
  Trash2,
  Wifi,
  X,
} from 'lucide-react'
import type { NodeConfig, SchemaMetadata } from '@/lib/config-api'

interface NodesTabProps {
  nodes: Record<string, NodeConfig>
  deviceCountsByNode: Record<string, number>
  schema: SchemaMetadata | null
  onChange: (updatedNodes: Record<string, NodeConfig>) => void
}

export function NodesTab({
  nodes,
  deviceCountsByNode,
  schema,
  onChange,
}: NodesTabProps) {
  const [editingNodeId, setEditingNodeId] = useState<string | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [revealedSecrets, setRevealedSecrets] = useState<Record<string, boolean>>({})

  // Form State
  const [formId, setFormId] = useState('')
  const [formDriver, setFormDriver] = useState('secure_standard_firmata_wifi')
  const [formHost, setFormHost] = useState('')
  const [formPort, setFormPort] = useState(3030)
  const [formAuthKey, setFormAuthKey] = useState('')
  const [formUseTls, setFormUseTls] = useState(false)
  const [formEnabled, setFormEnabled] = useState(true)
  const [formArduinoWait, setFormArduinoWait] = useState(5)
  const [formMaxRetries, setFormMaxRetries] = useState(3)
  const [formTimeout, setFormTimeout] = useState(12)
  const [formError, setFormError] = useState<string | null>(null)

  const openCreateModal = () => {
    setFormId('')
    setFormDriver('secure_standard_firmata_wifi')
    setFormHost('192.168.1.')
    setFormPort(3030)
    setFormAuthKey('')
    setFormUseTls(false)
    setFormEnabled(true)
    setFormArduinoWait(5)
    setFormMaxRetries(3)
    setFormTimeout(12)
    setFormError(null)
    setIsCreating(true)
    setEditingNodeId(null)
  }

  const openEditModal = (nodeId: string) => {
    const node = nodes[nodeId]
    if (!node) return
    setFormId(nodeId)
    setFormDriver(node.driver || 'secure_standard_firmata_wifi')
    setFormHost(node.host || '')
    setFormPort(node.port ?? 3030)
    setFormAuthKey(node.auth_key || '')
    setFormUseTls(node.use_tls ?? false)
    setFormEnabled(node.enabled ?? true)
    setFormArduinoWait(node.arduino_wait ?? 5)
    setFormMaxRetries(node.max_retries ?? 3)
    setFormTimeout(node.timeout ?? 12)
    setFormError(null)
    setEditingNodeId(nodeId)
    setIsCreating(false)
  }

  const handleSaveModal = (e: React.FormEvent) => {
    e.preventDefault()
    const cleanId = formId.trim()
    if (!cleanId) {
      setFormError('El identificador del nodo es obligatorio.')
      return
    }

    if (isCreating && nodes[cleanId]) {
      setFormError(`Ya existe un nodo con el identificador '${cleanId}'.`)
      return
    }

    if (!formDriver) {
      setFormError('Debe seleccionar un controlador/driver.')
      return
    }

    if (formDriver !== 'mock' && !formHost.trim()) {
      setFormError('La dirección IP o host es requerida para nodos físicos.')
      return
    }

    const updatedNodes = { ...nodes }

    // If renaming node
    if (!isCreating && editingNodeId && editingNodeId !== cleanId) {
      delete updatedNodes[editingNodeId]
    }

    const newNodeConfig: NodeConfig = {
      driver: formDriver,
      host: formHost.trim(),
      port: Number(formPort) || 3030,
      enabled: formEnabled,
      arduino_wait: Number(formArduinoWait) || 5,
      max_retries: Number(formMaxRetries) || 3,
      timeout: Number(formTimeout) || 12,
    }

    if (formDriver.includes('secure')) {
      newNodeConfig.auth_key = formAuthKey.trim() || '••••••••'
      newNodeConfig.use_tls = formUseTls
    }

    // Preserve devices attached if node had any
    const existingNode = editingNodeId ? nodes[editingNodeId] : null
    if (existingNode?.devices) {
      newNodeConfig.devices = existingNode.devices
    }

    updatedNodes[cleanId] = newNodeConfig
    onChange(updatedNodes)
    setIsCreating(false)
    setEditingNodeId(null)
  }

  const handleDeleteNode = (nodeId: string) => {
    if (confirm(`¿Está seguro de eliminar el nodo '${nodeId}' y sus dispositivos asociados?`)) {
      const updatedNodes = { ...nodes }
      delete updatedNodes[nodeId]
      onChange(updatedNodes)
    }
  }

  const handleToggleEnabled = (nodeId: string) => {
    const node = nodes[nodeId]
    if (!node) return
    const updated = {
      ...nodes,
      [nodeId]: {
        ...node,
        enabled: !(node.enabled ?? true),
      },
    }
    onChange(updated)
  }

  const toggleSecretReveal = (nodeId: string) => {
    setRevealedSecrets((prev) => ({
      ...prev,
      [nodeId]: !prev[nodeId],
    }))
  }

  const availableDrivers = schema?.supported_drivers || [
    'secure_standard_firmata_wifi',
    'standard_firmata_wifi',
    'mock',
    'firmata',
  ]

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
            <Wifi size={18} className="text-accent" />
            Nodos Hardware NodeMCU / ESP8266 (`nodes`)
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Microcontroladores conectados vía socket TCP WiFi o en simulación local.
          </p>
        </div>
        <button
          type="button"
          onClick={openCreateModal}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-medium bg-accent text-accent-foreground hover:bg-accent/90 transition-colors shadow-sm"
        >
          <Plus size={14} />
          <span>AÑADIR NODO</span>
        </button>
      </div>

      {/* Nodes Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {Object.entries(nodes).map(([nodeId, node]) => {
          const isEnabled = node.enabled ?? true
          const devCount = deviceCountsByNode[nodeId] || (node.devices ? Object.keys(node.devices).length : 0)
          const isSecure = node.driver?.includes('secure')
          const isMock = node.driver === 'mock'
          const isSecretRevealed = revealedSecrets[nodeId]

          return (
            <div
              key={nodeId}
              className={`p-5 rounded-xl border bg-surface-1 transition-all ${
                isEnabled ? 'border-border' : 'border-border/60 opacity-75'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2.5">
                  <div
                    className={`p-2 rounded-lg border ${
                      isMock
                        ? 'bg-purple-500/10 border-purple-500/30 text-purple-400'
                        : isSecure
                        ? 'bg-accent/10 border-accent/30 text-accent'
                        : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                    }`}
                  >
                    <Radio size={18} />
                  </div>
                  <div>
                    <h4 className="font-mono font-bold text-sm text-foreground">{nodeId}</h4>
                    <span className="inline-block px-2 py-0.5 mt-0.5 rounded text-[10px] font-mono border bg-surface-2 border-border text-muted-foreground">
                      {node.driver}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => handleToggleEnabled(nodeId)}
                    className={`px-2 py-0.5 rounded text-[10px] font-mono border transition-colors ${
                      isEnabled
                        ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                        : 'bg-surface-2 border-border text-muted-foreground'
                    }`}
                  >
                    {isEnabled ? 'HABILITADO' : 'PAUSADO'}
                  </button>
                  <button
                    type="button"
                    onClick={() => openEditModal(nodeId)}
                    className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-surface-2 transition-colors"
                    title="Editar propiedades del nodo"
                  >
                    <Settings size={15} />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDeleteNode(nodeId)}
                    className="p-1.5 rounded-lg text-muted-foreground hover:text-rose-400 hover:bg-surface-2 transition-colors"
                    title="Eliminar nodo"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>

              {/* Node Details */}
              <div className="mt-4 pt-3 border-t border-border/50 grid grid-cols-2 gap-y-2 text-xs font-mono">
                <div>
                  <span className="text-muted-foreground text-[11px]">Host / Socket:</span>
                  <p className="text-foreground">{node.host || 'N/A'}:{node.port ?? 3030}</p>
                </div>
                <div>
                  <span className="text-muted-foreground text-[11px]">Dispositivos:</span>
                  <p className="text-foreground">{devCount} conectados</p>
                </div>
                <div>
                  <span className="text-muted-foreground text-[11px]">Timeout / Espera:</span>
                  <p className="text-foreground">{node.timeout ?? 12}s / {node.arduino_wait ?? 5}s</p>
                </div>
                <div>
                  <span className="text-muted-foreground text-[11px]">Reintentos:</span>
                  <p className="text-foreground">{node.max_retries ?? 3} intentos</p>
                </div>

                {/* Auth Key Display if Secure */}
                {isSecure && (
                  <div className="col-span-2 pt-2 border-t border-border/40 flex items-center justify-between">
                    <span className="text-muted-foreground text-[11px] flex items-center gap-1">
                      <Lock size={12} className="text-accent" /> Clave de Autenticación:
                    </span>
                    <div className="flex items-center gap-1.5">
                      <code className="text-foreground text-[11px] bg-surface-2 px-1.5 py-0.5 rounded">
                        {isSecretRevealed ? node.auth_key || '••••••••' : '••••••••'}
                      </code>
                      <button
                        type="button"
                        onClick={() => toggleSecretReveal(nodeId)}
                        className="text-muted-foreground hover:text-foreground"
                      >
                        {isSecretRevealed ? <EyeOff size={12} /> : <Eye size={12} />}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )
        })}

        {Object.keys(nodes).length === 0 && (
          <div className="col-span-2 py-12 flex flex-col items-center justify-center border border-dashed border-border rounded-xl text-muted-foreground">
            <Radio size={32} className="mb-2 text-muted-foreground/60" />
            <p className="font-sans font-medium text-foreground text-sm">No hay nodos configurados</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Haga clic en &quot;AÑADIR NODO&quot; para registrar un microcontrolador ESP8266.
            </p>
          </div>
        )}
      </div>

      {/* Add / Edit Node Modal */}
      {(isCreating || editingNodeId) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4 animate-in fade-in duration-150">
          <div className="bg-surface-1 border border-border rounded-xl shadow-2xl w-full max-w-2xl overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface-2/50">
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Wifi size={16} className="text-accent" />
                {isCreating ? 'Añadir Nuevo Nodo ESP8266' : `Editar Nodo: ${editingNodeId}`}
              </h3>
              <button
                type="button"
                onClick={() => {
                  setIsCreating(false)
                  setEditingNodeId(null)
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

              {/* Node ID */}
              <div className="space-y-1">
                <label className="text-xs font-mono font-medium text-foreground">
                  Identificador del Nodo (`node_id`) *
                </label>
                <input
                  type="text"
                  value={formId}
                  onChange={(e) => setFormId(e.target.value)}
                  placeholder="ej. weather_01"
                  className="w-full px-3 py-1.5 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
                  required
                />
              </div>

              {/* Driver */}
              <div className="space-y-1">
                <label className="text-xs font-mono font-medium text-foreground">
                  Controlador / Driver *
                </label>
                <select
                  value={formDriver}
                  onChange={(e) => setFormDriver(e.target.value)}
                  className="w-full px-3 py-1.5 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
                >
                  {availableDrivers.map((driver) => (
                    <option key={driver} value={driver}>
                      {driver}
                    </option>
                  ))}
                </select>
              </div>

              {/* Host & Port */}
              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2 space-y-1">
                  <label className="text-xs font-mono font-medium text-foreground">
                    IP / Host *
                  </label>
                  <input
                    type="text"
                    value={formHost}
                    onChange={(e) => setFormHost(e.target.value)}
                    placeholder="192.168.1.37"
                    className="w-full px-3 py-1.5 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-mono font-medium text-foreground">
                    Puerto TCP
                  </label>
                  <input
                    type="number"
                    value={formPort}
                    onChange={(e) => setFormPort(Number(e.target.value))}
                    placeholder="3030"
                    className="w-full px-3 py-1.5 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
                  />
                </div>
              </div>

              {/* Secure Auth Key */}
              {formDriver.includes('secure') && (
                <div className="space-y-1">
                  <label className="text-xs font-mono font-medium text-foreground flex items-center justify-between">
                    <span>Clave Secreta (`auth_key`)</span>
                    <span className="text-[10px] text-muted-foreground">Si no se modifica, se preserva</span>
                  </label>
                  <input
                    type="text"
                    value={formAuthKey}
                    onChange={(e) => setFormAuthKey(e.target.value)}
                    placeholder="••••••••"
                    className="w-full px-3 py-1.5 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
                  />
                </div>
              )}

              {/* Advanced Timeouts */}
              <div className="grid grid-cols-3 gap-2 pt-2 border-t border-border">
                <div className="space-y-1">
                  <label className="text-[10px] font-mono text-muted-foreground">
                    Espera Arduino (s)
                  </label>
                  <input
                    type="number"
                    value={formArduinoWait}
                    onChange={(e) => setFormArduinoWait(Number(e.target.value))}
                    className="w-full px-2 py-1 text-xs font-mono rounded border border-border bg-surface-2 text-foreground"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[10px] font-mono text-muted-foreground">
                    Reintentos
                  </label>
                  <input
                    type="number"
                    value={formMaxRetries}
                    onChange={(e) => setFormMaxRetries(Number(e.target.value))}
                    className="w-full px-2 py-1 text-xs font-mono rounded border border-border bg-surface-2 text-foreground"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[10px] font-mono text-muted-foreground">
                    Timeout (s)
                  </label>
                  <input
                    type="number"
                    value={formTimeout}
                    onChange={(e) => setFormTimeout(Number(e.target.value))}
                    className="w-full px-2 py-1 text-xs font-mono rounded border border-border bg-surface-2 text-foreground"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
                <button
                  type="button"
                  onClick={() => {
                    setIsCreating(false)
                    setEditingNodeId(null)
                  }}
                  className="px-4 py-2 text-xs font-medium text-muted-foreground hover:text-foreground border border-border rounded-lg"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-xs font-mono font-medium bg-accent text-accent-foreground rounded-lg hover:bg-accent/90 shadow-sm"
                >
                  Guardar Nodo
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
