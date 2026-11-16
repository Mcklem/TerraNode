'use client'

import React from 'react'
import Link from 'next/link'
import {
  ArrowLeft,
  CheckCircle2,
  Cpu,
  FileCode2,
  FileText,
  Play,
  RefreshCw,
  Save,
  Sliders,
  SlidersHorizontal,
  XCircle,
  AlertTriangle,
} from 'lucide-react'
import type { ConfigStatus, ValidationResult } from '@/lib/config-api'

interface ManagerHeaderProps {
  status: ConfigStatus | null
  validation: ValidationResult | null
  hasUnsavedChanges: boolean
  isSaving: boolean
  isApplying: boolean
  isValidating: boolean
  onSave: () => void
  onApply: () => void
  onValidate: () => void
  onOpenDiff: () => void
  onRefresh: () => void
}

export function ManagerHeader({
  status,
  validation,
  hasUnsavedChanges,
  isSaving,
  isApplying,
  isValidating,
  onSave,
  onApply,
  onValidate,
  onOpenDiff,
  onRefresh,
}: ManagerHeaderProps) {
  const isValid = validation?.valid ?? true
  const errorCount = validation?.errors?.length ?? 0
  const warningCount = validation?.warnings?.length ?? 0
  const isSync = status?.is_synchronized ?? false

  return (
    <header className="topbar">
      <div className="brand">
        <Link
          href="/"
          className="flex items-center gap-2 p-1.5 -ml-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-surface-2 transition-colors mr-2"
          title="Regresar al Dashboard de Operaciones"
        >
          <ArrowLeft size={18} />
        </Link>
        <div className="brand-mark" aria-hidden="true">
          <SlidersHorizontal size={18} />
        </div>
        <div>
          <p className="eyebrow">SYSTEM CONFIGURATION MANAGER</p>
          <h1>
            TerraNode <span>Configuration Manager</span>
          </h1>
        </div>
      </div>

      <div className="header-actions">
        {/* Validation Status Badge */}
        <button
          type="button"
          onClick={onValidate}
          disabled={isValidating}
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono font-medium border transition-colors ${
            isValid
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20'
              : 'bg-rose-500/10 border-rose-500/30 text-rose-400 hover:bg-rose-500/20'
          }`}
          title="Haga clic para volver a validar la configuración"
        >
          {isValid ? (
            <>
              <CheckCircle2 size={13} className="text-emerald-400" />
              <span>CONFIG: VÁLIDA</span>
            </>
          ) : (
            <>
              <XCircle size={13} className="text-rose-400" />
              <span>{errorCount} ERRORES</span>
            </>
          )}
          {warningCount > 0 && (
            <span className="text-amber-400 ml-1">({warningCount} adv.)</span>
          )}
        </button>

        {/* Runtime Sync Badge */}
        <div
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono font-medium border ${
            isSync
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
              : 'bg-amber-500/10 border-amber-500/30 text-amber-400'
          }`}
          title={
            isSync
              ? 'La configuración guardada coincide con la versión en ejecución'
              : 'Hay cambios guardados en disco pendientes de aplicar al runtime'
          }
        >
          <i
            className={`w-2 h-2 rounded-full ${
              isSync ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]' : 'bg-amber-400 animate-pulse'
            }`}
          />
          <span>{isSync ? 'RUNTIME: EN SYNC' : 'PENDIENTE APLICAR'}</span>
        </div>

        {/* Diff preview button */}
        <button
          type="button"
          onClick={onOpenDiff}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-medium border border-border bg-surface-2 text-foreground hover:text-accent hover:border-accent transition-colors"
          title="Ver diferencias contra la configuración activa en disco"
        >
          <FileText size={14} className="text-accent" />
          <span>DIFF</span>
        </button>

        {/* Save button */}
        <button
          type="button"
          onClick={onSave}
          disabled={isSaving || !isValid}
          className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-mono font-medium border transition-colors ${
            hasUnsavedChanges
              ? 'bg-accent text-accent-foreground border-accent hover:bg-accent/90 shadow-sm animate-pulse'
              : 'bg-surface-2 text-foreground border-border hover:bg-surface-3'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
          title="Guardar cambios validados y crear respaldo automático"
        >
          <Save size={14} />
          <span>{isSaving ? 'GUARDANDO...' : hasUnsavedChanges ? 'GUARDAR *' : 'GUARDAR'}</span>
        </button>

        {/* Apply button */}
        <button
          type="button"
          onClick={onApply}
          disabled={isApplying || !isValid}
          className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-mono font-medium border transition-colors ${
            !isSync
              ? 'bg-amber-500 text-black border-amber-400 hover:bg-amber-400 font-semibold shadow-sm'
              : 'bg-surface-2 text-muted-foreground border-border hover:text-foreground hover:bg-surface-3'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
          title="Recargar dinámicamente los subsistemas de hardware con la configuración activa"
        >
          <Play size={14} className={isApplying ? 'animate-spin' : ''} />
          <span>{isApplying ? 'APLICANDO...' : 'APLICAR AL RUNTIME'}</span>
        </button>

        {/* Refresh button */}
        <button
          type="button"
          className="icon-button"
          onClick={onRefresh}
          title="Recargar estado desde el controlador"
          aria-label="Refrescar"
        >
          <RefreshCw size={17} />
        </button>
      </div>
    </header>
  )
}
