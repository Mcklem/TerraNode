'use client'

import React from 'react'
import {
  Activity,
  AlertTriangle,
  Bell,
  Calendar,
  CheckCircle2,
  Cpu,
  Database,
  FileCode2,
  HardDrive,
  Radio,
  Server,
  Sliders,
  Sparkles,
  Wifi,
  XCircle,
} from 'lucide-react'
import type { ConfigStatus, NormalizedConfig, ValidationResult } from '@/lib/config-api'

interface OverviewTabProps {
  config: NormalizedConfig | null
  status: ConfigStatus | null
  validation: ValidationResult | null
  onNavigateTab: (tabId: string) => void
  onSave: () => void
  onApply: () => void
}

export function OverviewTab({
  config,
  status,
  validation,
  onNavigateTab,
  onSave,
  onApply,
}: OverviewTabProps) {
  const sys = config?.system || {}
  const nodes = config?.nodes || {}
  const devices = config?.devices || {}
  const rules = config?.rules || {}
  const schedules = config?.schedules || {}

  const isSync = status?.is_synchronized ?? false
  const errors = validation?.errors || []
  const warnings = validation?.warnings || []
  const infos = validation?.infos || []

  const sensorCount = Object.values(devices).filter((d) =>
    ['ldr', 'bmp180', 'soil_moisture'].includes(d.type?.toLowerCase())
  ).length
  const actuatorCount = Object.values(devices).filter((d) =>
    ['relay', 'servo', 'led'].includes(d.type?.toLowerCase())
  ).length

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Banner / Sync Notice */}
      {!isSync && (
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-200">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-amber-500/20 text-amber-400">
              <AlertTriangle size={20} />
            </div>
            <div>
              <p className="font-semibold text-sm text-amber-300">
                Cambios pendientes de aplicar al runtime
              </p>
              <p className="text-xs text-amber-200/80">
                La configuración activa guardada en disco difiere de la que se encuentra en memoria del controlador.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onApply}
            className="px-4 py-2 rounded-lg bg-amber-400 text-black text-xs font-mono font-bold hover:bg-amber-300 transition-colors shadow-sm shrink-0"
          >
            APLICAR AHORA
          </button>
        </div>
      )}

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        <div
          onClick={() => onNavigateTab('nodes')}
          className="p-4 rounded-xl border border-border bg-surface-1 hover:border-accent/50 cursor-pointer transition-all hover:shadow-md"
        >
          <div className="flex items-center justify-between text-muted-foreground mb-2">
            <span className="text-xs font-mono">NODOS ESP8266</span>
            <Wifi size={16} className="text-accent" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-foreground">
              {Object.keys(nodes).length}
            </span>
            <span className="text-xs text-muted-foreground">configurados</span>
          </div>
          <p className="text-[11px] text-muted-foreground mt-2">
            {Object.values(nodes).filter((n) => n.enabled !== false).length} habilitados
          </p>
        </div>

        <div
          onClick={() => onNavigateTab('devices')}
          className="p-4 rounded-xl border border-border bg-surface-1 hover:border-accent/50 cursor-pointer transition-all hover:shadow-md"
        >
          <div className="flex items-center justify-between text-muted-foreground mb-2">
            <span className="text-xs font-mono">DISPOSITIVOS</span>
            <Cpu size={16} className="text-emerald-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-foreground">
              {Object.keys(devices).length}
            </span>
            <span className="text-xs text-muted-foreground">totales</span>
          </div>
          <p className="text-[11px] text-muted-foreground mt-2">
            {sensorCount} sensores · {actuatorCount} actuadores
          </p>
        </div>

        <div
          onClick={() => onNavigateTab('rules')}
          className="p-4 rounded-xl border border-border bg-surface-1 hover:border-accent/50 cursor-pointer transition-all hover:shadow-md"
        >
          <div className="flex items-center justify-between text-muted-foreground mb-2">
            <span className="text-xs font-mono">REGLAS AUTO</span>
            <Sparkles size={16} className="text-cyan-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-foreground">
              {Object.keys(rules).length}
            </span>
            <span className="text-xs text-muted-foreground">declaradas</span>
          </div>
          <p className="text-[11px] text-muted-foreground mt-2">
            {Object.values(rules).filter((r) => r.enabled !== false).length} activas
          </p>
        </div>

        <div
          onClick={() => onNavigateTab('schedules')}
          className="p-4 rounded-xl border border-border bg-surface-1 hover:border-accent/50 cursor-pointer transition-all hover:shadow-md"
        >
          <div className="flex items-center justify-between text-muted-foreground mb-2">
            <span className="text-xs font-mono">PROGRAMACIONES</span>
            <Calendar size={16} className="text-purple-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-foreground">
              {Object.keys(schedules).length}
            </span>
            <span className="text-xs text-muted-foreground">temporales</span>
          </div>
          <p className="text-[11px] text-muted-foreground mt-2">
            {Object.values(schedules).filter((s) => s.enabled !== false).length} activas
          </p>
        </div>

        <div
          onClick={() => onNavigateTab('notifications')}
          className="p-4 rounded-xl border border-border bg-surface-1 hover:border-accent/50 cursor-pointer transition-all hover:shadow-md col-span-2 sm:col-span-1"
        >
          <div className="flex items-center justify-between text-muted-foreground mb-2">
            <span className="text-xs font-mono">NOTIFICACIONES</span>
            <Bell size={16} className="text-pink-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-foreground">
              {Object.keys(config?.notifications?.webhooks || {}).length}
            </span>
            <span className="text-xs text-muted-foreground">webhooks</span>
          </div>
          <p className="text-[11px] text-muted-foreground mt-2">
            {config?.notifications?.telegram?.enabled ? 'Telegram ON' : 'Telegram OFF'} ·{' '}
            {config?.notifications?.email?.enabled ? 'Email ON' : 'Email OFF'}
          </p>
        </div>
      </div>

      {/* System Status Details */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left Card: System & Persistence Info */}
        <div className="p-5 rounded-xl border border-border bg-surface-1 space-y-4">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <Server size={16} className="text-accent" />
              Parámetros de Instalación
            </h3>
            <button
              type="button"
              onClick={() => onNavigateTab('system')}
              className="text-xs font-mono text-accent hover:underline"
            >
              Editar Ajustes →
            </button>
          </div>

          <div className="space-y-2.5 text-xs font-mono">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Nombre Instalación:</span>
              <span className="font-semibold text-foreground">{sys.name || 'parcela_controller'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Versión del Sistema:</span>
              <span className="text-foreground">{sys.version || '1.0'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Base de Datos:</span>
              <span className="text-foreground truncate max-w-[400px]" title={sys.database}>
                {sys.database || 'controller.db'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Telemetría Sensores:</span>
              <span className={sys.log_readings ? 'text-emerald-400 font-bold' : 'text-muted-foreground'}>
                {sys.log_readings ? 'HABILITADA' : 'DESHABILITADA'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Evaluación de Reglas:</span>
              <span className={sys.log_rule_evaluations ? 'text-emerald-400 font-bold' : 'text-muted-foreground'}>
                {sys.log_rule_evaluations ? 'HABILITADA' : 'DESHABILITADA'}
              </span>
            </div>
            <div className="flex items-center justify-between pt-2 border-t border-border/50">
              <span className="text-muted-foreground">Archivo Activo:</span>
              <span className="text-foreground truncate max-w-[500px]" title={status?.active_config_path}>
                {status?.active_config_path || 'config/system.yaml'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Checksum Guardado:</span>
              <span className="text-foreground font-mono">
                {status?.saved_checksum ? status.saved_checksum.slice(0, 12) + '…' : 'N/A'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Checksum Runtime:</span>
              <span className="text-foreground font-mono">
                {status?.runtime_checksum ? status.runtime_checksum.slice(0, 12) + '…' : 'N/A'}
              </span>
            </div>
          </div>
        </div>

        {/* Right Card: Multi-level Validation Report */}
        <div className="p-5 rounded-xl border border-border bg-surface-1 space-y-4 flex flex-col">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <CheckCircle2
                size={16}
                className={errors.length === 0 ? 'text-emerald-400' : 'text-rose-400'}
              />
              Diagnóstico de Validación
            </h3>
            <span className="text-xs font-mono text-muted-foreground">
              {errors.length} err · {warnings.length} adv
            </span>
          </div>

          <div className="flex-1 overflow-auto max-h-[220px] space-y-2 text-xs">
            {errors.length === 0 && warnings.length === 0 && infos.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 text-muted-foreground">
                <CheckCircle2 size={32} className="text-emerald-400 mb-2" />
                <p className="font-sans font-medium text-foreground">Configuración 100% Válida</p>
                <p className="text-[11px] text-muted-foreground">
                  Sintaxis YAML, esquema y asignación de pines validados sin conflictos.
                </p>
              </div>
            ) : (
              <>
                {errors.map((err, i) => (
                  <div
                    key={`err-${i}`}
                    className="p-2.5 rounded-lg border border-rose-500/30 bg-rose-500/10 text-rose-300 flex items-start gap-2"
                  >
                    <XCircle size={15} className="text-rose-400 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-mono font-bold text-rose-200">[{err.field}] </span>
                      <span>{err.message}</span>
                      {err.line && (
                        <span className="text-[10px] text-rose-400/80 ml-2 font-mono">
                          (Línea {err.line})
                        </span>
                      )}
                    </div>
                  </div>
                ))}

                {warnings.map((warn, i) => (
                  <div
                    key={`warn-${i}`}
                    className="p-2.5 rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-300 flex items-start gap-2"
                  >
                    <AlertTriangle size={15} className="text-amber-400 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-mono font-bold text-amber-200">[{warn.field}] </span>
                      <span>{warn.message}</span>
                    </div>
                  </div>
                ))}

                {infos.map((info, i) => (
                  <div
                    key={`info-${i}`}
                    className="p-2 rounded-lg border border-cyan-500/30 bg-cyan-500/10 text-cyan-300 flex items-start gap-2 text-[11px]"
                  >
                    <span className="font-mono font-bold">[{info.field}]</span>
                    <span>{info.message}</span>
                  </div>
                ))}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
