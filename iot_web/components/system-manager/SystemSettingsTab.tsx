'use client'

import React from 'react'
import { Database, FileText, Info, Save, Server, Sliders } from 'lucide-react'

interface SystemSettingsProps {
  system: {
    name?: string
    version?: string
    database?: string
    log_readings?: boolean
    log_rule_evaluations?: boolean
    [key: string]: any
  }
  onChange: (updated: any) => void
}

export function SystemSettingsTab({ system, onChange }: SystemSettingsProps) {
  const handleChange = (key: string, value: any) => {
    onChange({
      ...system,
      [key]: value,
    })
  }

  return (
    <div className="max-w-5xl space-y-6 animate-in fade-in duration-200">
      <div className="p-6 rounded-xl border border-border bg-surface-1 space-y-6">
        <div>
          <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
            <Server size={18} className="text-accent" />
            Configuración General del Sistema (`system`)
          </h3>
          <p className="text-xs text-muted-foreground mt-1">
            Define la identidad global de la instalación, la base de datos de persistencia SQLite y el nivel de telemetría en consola.
          </p>
        </div>

        <div className="space-y-4">
          {/* Installation Name */}
          <div className="space-y-1.5">
            <label className="text-xs font-mono font-medium text-foreground">
              Nombre de Instalación (`system.name`)
            </label>
            <input
              type="text"
              value={system.name || ''}
              onChange={(e) => handleChange('name', e.target.value)}
              placeholder="parcela_controller"
              className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
            />
            <p className="text-[11px] text-muted-foreground">
              Identificador único del controlador central en la red local.
            </p>
          </div>

          {/* System Version */}
          <div className="space-y-1.5">
            <label className="text-xs font-mono font-medium text-foreground">
              Versión del Sistema (`system.version`)
            </label>
            <input
              type="text"
              value={system.version || ''}
              onChange={(e) => handleChange('version', e.target.value)}
              placeholder="1.0"
              className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
            />
            <p className="text-[11px] text-muted-foreground">
              Cadena de versión del despliegue para auditoría.
            </p>
          </div>

          {/* Database Path */}
          <div className="space-y-1.5">
            <label className="text-xs font-mono font-medium text-foreground">
              Ruta de Base de Datos SQLite (`system.database`)
            </label>
            <div className="relative">
              <input
                type="text"
                value={system.database || ''}
                onChange={(e) => handleChange('database', e.target.value)}
                placeholder="controller.db"
                className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent pl-8"
              />
              <Database size={14} className="absolute left-2.5 top-2.5 text-muted-foreground" />
            </div>
            <p className="text-[11px] text-muted-foreground">
              Nombre de archivo relativo o ruta absoluta a la base de datos SQLite para telemetría histórica.
            </p>
          </div>

          {/* Logging Toggles */}
          <div className="pt-4 border-t border-border space-y-4">
            <div className="flex items-center justify-between p-3 rounded-lg border border-border bg-surface-2/40">
              <div>
                <p className="text-xs font-mono font-semibold text-foreground">
                  Registrar Lecturas de Sensores en Consola (`log_readings`)
                </p>
                <p className="text-[11px] text-muted-foreground">
                  Emite trazas periódicas de telemetría de sensores en la salida estándar del controlador.
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={system.log_readings ?? true}
                  onChange={(e) => handleChange('log_readings', e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-9 h-5 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-accent"></div>
              </label>
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg border border-border bg-surface-2/40">
              <div>
                <p className="text-xs font-mono font-semibold text-foreground">
                  Registrar Evaluación de Reglas (`log_rule_evaluations`)
                </p>
                <p className="text-[11px] text-muted-foreground">
                  Registra logs detallados en consola cada vez que el motor evalúa condiciones y dispara acciones.
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={system.log_rule_evaluations ?? true}
                  onChange={(e) => handleChange('log_rule_evaluations', e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-9 h-5 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-accent"></div>
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
