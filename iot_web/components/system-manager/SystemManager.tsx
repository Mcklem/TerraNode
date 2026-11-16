'use client'

import React, { useEffect, useState } from 'react'
import {
  Bell,
  Calendar,
  CheckCircle2,
  Cpu,
  FileCode2,
  History,
  LayoutDashboard,
  Server,
  Sliders,
  Sparkles,
  Wifi,
} from 'lucide-react'
import type {
  BackupMetadata,
  ConfigStatus,
  DiffResult,
  NormalizedConfig,
  SchemaMetadata,
  ValidationResult,
} from '@/lib/config-api'
import {
  applyConfig,
  convertYamlToModel,
  deleteConfigBackup,
  fetchConfig,
  fetchConfigBackups,
  fetchConfigDiff,
  fetchConfigSchema,
  restoreConfigBackup,
  saveRawYamlConfig,
  saveVisualConfig,
  validateConfig,
} from '@/lib/config-api'
import { DiffModal } from './DiffModal'
import { ManagerHeader } from './ManagerHeader'
import { OverviewTab } from './OverviewTab'
import { SystemSettingsTab } from './SystemSettingsTab'
import { NodesTab } from './NodesTab'
import { DevicesTab } from './DevicesTab'
import { RulesTab } from './RulesTab'
import { SchedulesTab } from './SchedulesTab'
import { NotificationsTab } from './NotificationsTab'
import { RawYamlTab } from './RawYamlTab'
import { HistoryTab } from './HistoryTab'

export function SystemManager() {
  const [activeTab, setActiveTab] = useState<string>('overview')

  // Core Data
  const [config, setConfig] = useState<NormalizedConfig | null>(null)
  const [originalYaml, setOriginalYaml] = useState<string>('')
  const [rawYaml, setRawYaml] = useState<string>('')
  const [status, setStatus] = useState<ConfigStatus | null>(null)
  const [validation, setValidation] = useState<ValidationResult | null>(null)
  const [diff, setDiff] = useState<DiffResult | null>(null)
  const [backups, setBackups] = useState<BackupMetadata[]>([])
  const [schema, setSchema] = useState<SchemaMetadata | null>(null)

  // UI state
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [isApplying, setIsApplying] = useState(false)
  const [isValidating, setIsValidating] = useState(false)
  const [isDiffModalOpen, setIsDiffModalOpen] = useState(false)
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null)

  // Track if visual model was modified
  const [visualDirty, setVisualDirty] = useState(false)

  const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 5000)
  }

  // Load initial data
  const loadData = async () => {
    setIsLoading(true)
    try {
      const [cfgRes, backupsRes, schemaRes] = await Promise.all([
        fetchConfig(true),
        fetchConfigBackups(),
        fetchConfigSchema(),
      ])

      setConfig(cfgRes.config)
      setOriginalYaml(cfgRes.raw_yaml)
      setRawYaml(cfgRes.raw_yaml)
      setStatus(cfgRes.status)
      setValidation(cfgRes.status.validation)
      setBackups(backupsRes)
      setSchema(schemaRes)
      setVisualDirty(false)
    } catch (e: any) {
      showToast(`Error al cargar configuración: ${e.message}`, 'error')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  // Run validation
  const handleValidate = async () => {
    setIsValidating(true)
    try {
      let res: ValidationResult
      if (activeTab === 'raw') {
        res = await validateConfig({ raw_yaml: rawYaml })
      } else if (config) {
        res = await validateConfig({ config })
      } else {
        res = await validateConfig({ raw_yaml: rawYaml })
      }
      setValidation(res)
      if (res.valid) {
        showToast('Validación exitosa: la configuración cumple con todas las reglas.', 'success')
      } else {
        showToast(`Se detectaron ${res.errors.length} errores de validación.`, 'error')
      }
    } catch (e: any) {
      showToast(`Fallo en validación: ${e.message}`, 'error')
    } finally {
      setIsValidating(false)
    }
  }

  const getDiffPayload = () => {
    if (activeTab === 'raw') {
      return { proposed_yaml: rawYaml }
    }
    if (visualDirty && config) {
      return { visual_model: config }
    }
    return { proposed_yaml: rawYaml }
  }

  // Open diff preview
  const handleOpenDiff = async () => {
    try {
      const payload = getDiffPayload()
      const diffRes = await fetchConfigDiff(payload)
      if (diffRes.proposed_yaml && activeTab !== 'raw') {
        setRawYaml(diffRes.proposed_yaml)
      }
      setDiff(diffRes)
      setIsDiffModalOpen(true)
    } catch (e: any) {
      showToast(`Error al generar diff: ${e.message}`, 'error')
    }
  }

  // Prepare Save: generate diff and open confirmation modal
  const handlePrepareSave = async () => {
    try {
      const payload = getDiffPayload()
      const diffRes = await fetchConfigDiff(payload)
      if (diffRes.proposed_yaml && activeTab !== 'raw') {
        setRawYaml(diffRes.proposed_yaml)
      }
      setDiff(diffRes)
      setIsDiffModalOpen(true)
    } catch (e: any) {
      showToast(`Error al preparar guardado: ${e.message}`, 'error')
    }
  }

  // Confirm Save to Disk
  const handleConfirmSave = async () => {
    setIsSaving(true)
    try {
      let res
      if (activeTab === 'raw') {
        res = await saveRawYamlConfig({
          raw_yaml: rawYaml,
          base_checksum: status?.saved_checksum,
          author: 'web_operator',
          description: 'Guardado desde editor YAML directo',
        })
      } else if (config) {
        res = await saveVisualConfig({
          visual_model: config,
          base_checksum: status?.saved_checksum,
          author: 'web_operator',
          description: 'Guardado desde interfaz visual',
        })
      } else {
        res = await saveRawYamlConfig({
          raw_yaml: rawYaml,
          base_checksum: status?.saved_checksum,
        })
      }

      setIsDiffModalOpen(false)
      showToast('Configuración guardada exitosamente y respaldo creado.', 'success')
      setVisualDirty(false)

      // Reload fresh data from backend
      await loadData()
    } catch (e: any) {
      showToast(`Error al guardar: ${e.message}`, 'error')
    } finally {
      setIsSaving(false)
    }
  }

  // Apply saved configuration to runtime
  const handleApply = async () => {
    if (!confirm('¿Desea aplicar la configuración guardada a todos los nodos y dispositivos en ejecución?')) {
      return
    }

    setIsApplying(true)
    try {
      const res = await applyConfig()
      showToast(res.message || 'Configuración aplicada con éxito.', 'success')
      await loadData()
    } catch (e: any) {
      showToast(`Error al aplicar configuración: ${e.message}`, 'error')
    } finally {
      setIsApplying(false)
    }
  }

  // Restore backup
  const handleRestoreBackup = async (backupId: string) => {
    if (!confirm(`¿Está seguro de restaurar el respaldo '${backupId}'? Se creará una instantánea previa de seguridad.`)) {
      return
    }

    try {
      const res = await restoreConfigBackup(backupId, 'web_operator')
      showToast(res.message, 'success')
      await loadData()
    } catch (e: any) {
      showToast(`Fallo al restaurar: ${e.message}`, 'error')
    }
  }

  // Delete backup
  const handleDeleteBackup = async (backupId: string) => {
    if (!confirm(`¿Eliminar permanentemente el respaldo '${backupId}'?`)) {
      return
    }

    try {
      const res = await deleteConfigBackup(backupId)
      showToast(res.message, 'success')
      const updatedBackups = await fetchConfigBackups()
      setBackups(updatedBackups)
    } catch (e: any) {
      showToast(`Error al eliminar: ${e.message}`, 'error')
    }
  }

  // Revert Raw YAML
  const handleRevertRawYaml = () => {
    setRawYaml(originalYaml)
    showToast('Cambios descartados. Contenido restaurado al archivo activo en disco.', 'info')
  }

  // Update visual model helpers
  const handleUpdateSystem = (newSys: any) => {
    if (!config) return
    setConfig({ ...config, system: newSys })
    setVisualDirty(true)
  }

  const handleUpdateNodes = (newNodes: any) => {
    if (!config) return
    setConfig({ ...config, nodes: newNodes })
    setVisualDirty(true)
  }

  const handleUpdateDevices = (newDevs: any) => {
    if (!config) return
    setConfig({ ...config, devices: newDevs })
    setVisualDirty(true)
  }

  const handleUpdateRules = (newRules: any) => {
    if (!config) return
    setConfig({ ...config, rules: newRules })
    setVisualDirty(true)
  }

  const handleUpdateSchedules = (newScheds: any) => {
    if (!config) return
    setConfig({ ...config, schedules: newScheds })
    setVisualDirty(true)
  }

  const handleUpdateNotifications = (newNotif: any) => {
    if (!config) return
    setConfig({ ...config, notifications: newNotif })
    setVisualDirty(true)
  }

  const hasUnsavedChanges = visualDirty || rawYaml !== originalYaml

  // Switch tabs with synchronization between visual model and raw YAML
  const handleTabChange = async (nextTab: string) => {
    if (nextTab === activeTab) return

    // If switching to raw mode and visual model has unsaved modifications:
    if (nextTab === 'raw' && visualDirty && config) {
      try {
        const diffRes = await fetchConfigDiff({ visual_model: config })
        if (diffRes.proposed_yaml) {
          setRawYaml(diffRes.proposed_yaml)
        }
      } catch (err: any) {
        console.error('Error synchronizing visual model to YAML:', err)
      }
    }

    // If switching from raw mode to a visual tab and rawYaml has changes:
    if (activeTab === 'raw' && nextTab !== 'raw' && rawYaml !== originalYaml) {
      try {
        const modelRes = await convertYamlToModel(rawYaml)
        if (modelRes.config) {
          setConfig(modelRes.config)
          setVisualDirty(true)
        }
      } catch (err: any) {
        showToast(`Advertencia: no se pudo sincronizar el modelo visual (${err.message})`, 'error')
      }
    }

    setActiveTab(nextTab)
  }

  // Device counts by parent node
  const deviceCountsByNode: Record<string, number> = {}
  if (config?.devices) {
    Object.values(config.devices).forEach((d) => {
      if (d.node) {
        deviceCountsByNode[d.node] = (deviceCountsByNode[d.node] || 0) + 1
      }
    })
  }

  const tabs = [
    { id: 'overview', label: 'Resumen', icon: LayoutDashboard },
    { id: 'system', label: 'Sistema', icon: Server },
    { id: 'nodes', label: 'Nodos', icon: Wifi, count: Object.keys(config?.nodes || {}).length },
    { id: 'devices', label: 'Dispositivos', icon: Cpu, count: Object.keys(config?.devices || {}).length },
    { id: 'rules', label: 'Reglas', icon: Sparkles, count: Object.keys(config?.rules || {}).length },
    { id: 'schedules', label: 'Horarios', icon: Calendar, count: Object.keys(config?.schedules || {}).length },
    {
      id: 'notifications',
      label: 'Notificaciones',
      icon: Bell,
      count: Object.keys(config?.notifications?.webhooks || {}).length,
    },
    { id: 'raw', label: 'YAML Raw', icon: FileCode2 },
    { id: 'history', label: 'Historial', icon: History, count: backups.length },
  ]

  return (
    <main className="min-h-screen bg-background text-foreground font-sans">
      <ManagerHeader
        status={status}
        validation={validation}
        hasUnsavedChanges={hasUnsavedChanges}
        isSaving={isSaving}
        isApplying={isApplying}
        isValidating={isValidating}
        onSave={handlePrepareSave}
        onApply={handleApply}
        onValidate={handleValidate}
        onOpenDiff={handleOpenDiff}
        onRefresh={loadData}
      />

      <div className="shell py-6">
        {/* Toast Notification */}
        {toast && (
          <div
            className={`fixed bottom-6 right-6 z-50 p-4 rounded-xl shadow-xl border flex items-center gap-3 animate-in fade-in slide-in-from-bottom-2 duration-200 ${
              toast.type === 'success'
                ? 'bg-emerald-950/90 border-emerald-500 text-emerald-200'
                : toast.type === 'error'
                ? 'bg-rose-950/90 border-rose-500 text-rose-200'
                : 'bg-surface-2 border-border text-foreground'
            }`}
          >
            <span className="text-xs font-mono">{toast.message}</span>
            <button
              type="button"
              onClick={() => setToast(null)}
              className="text-xs opacity-70 hover:opacity-100"
            >
              ✕
            </button>
          </div>
        )}

        {/* Tab Navigation Navigation Bar */}
        <div className="flex items-center gap-1.5 border-b border-border mb-6 overflow-x-auto pb-1">
          {tabs.map((tab) => {
            const Icon = tab.icon
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => handleTabChange(tab.id)}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-t-lg text-xs font-mono font-medium transition-colors border-b-2 whitespace-nowrap ${
                  isActive
                    ? 'border-accent text-foreground bg-surface-1 font-bold'
                    : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-surface-2/40'
                }`}
              >
                <Icon size={14} className={isActive ? 'text-accent' : 'text-muted-foreground'} />
                <span>{tab.label}</span>
                {tab.count != null && (
                  <span
                    className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                      isActive ? 'bg-accent/20 text-accent font-bold' : 'bg-surface-2 text-muted-foreground'
                    }`}
                  >
                    {tab.count}
                  </span>
                )}
              </button>
            )
          })}
        </div>

        {/* Tab Contents */}
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-24 text-muted-foreground">
            <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin mb-3" />
            <p className="font-mono text-xs">Cargando configuración de TerraNode…</p>
          </div>
        ) : (
          <>
            {activeTab === 'overview' && (
              <OverviewTab
                config={config}
                status={status}
                validation={validation}
                onNavigateTab={(tab) => handleTabChange(tab)}
                onSave={handlePrepareSave}
                onApply={handleApply}
              />
            )}

            {activeTab === 'system' && (
              <SystemSettingsTab
                system={config?.system || {}}
                onChange={handleUpdateSystem}
              />
            )}

            {activeTab === 'nodes' && (
              <NodesTab
                nodes={config?.nodes || {}}
                deviceCountsByNode={deviceCountsByNode}
                schema={schema}
                onChange={handleUpdateNodes}
              />
            )}

            {activeTab === 'devices' && (
              <DevicesTab
                devices={config?.devices || {}}
                nodes={config?.nodes || {}}
                schema={schema}
                onChange={handleUpdateDevices}
              />
            )}

            {activeTab === 'rules' && (
              <RulesTab
                rules={config?.rules || {}}
                devices={config?.devices || {}}
                schema={schema}
                webhooks={config?.notifications?.webhooks || {}}
                onChange={handleUpdateRules}
              />
            )}

            {activeTab === 'schedules' && (
              <SchedulesTab
                schedules={config?.schedules || {}}
                devices={config?.devices || {}}
                schema={schema}
                onChange={handleUpdateSchedules}
              />
            )}

            {activeTab === 'notifications' && (
              <NotificationsTab
                notifications={config?.notifications}
                onChange={handleUpdateNotifications}
              />
            )}

            {activeTab === 'raw' && (
              <RawYamlTab
                yamlContent={rawYaml}
                originalYaml={originalYaml}
                validation={validation}
                isValidating={isValidating}
                isSaving={isSaving}
                onChange={setRawYaml}
                onValidate={handleValidate}
                onSave={handlePrepareSave}
                onRevert={handleRevertRawYaml}
              />
            )}

            {activeTab === 'history' && (
              <HistoryTab
                backups={backups}
                isLoading={isLoading}
                onRestore={handleRestoreBackup}
                onDelete={handleDeleteBackup}
                onRefresh={async () => {
                  const updated = await fetchConfigBackups()
                  setBackups(updated)
                }}
              />
            )}
          </>
        )}
      </div>

      {/* Diff Modal */}
      <DiffModal
        isOpen={isDiffModalOpen}
        onClose={() => setIsDiffModalOpen(false)}
        onConfirmSave={handleConfirmSave}
        isSaving={isSaving}
        diff={diff}
      />
    </main>
  )
}
