'use client'

import React from 'react'
import { AlertTriangle, Check, CheckCircle2, ChevronRight, Copy, FileText, Lock, ShieldCheck, X } from 'lucide-react'
import type { DiffResult } from '@/lib/config-api'

interface DiffModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirmSave: () => void
  isSaving: boolean
  diff: DiffResult | null
  title?: string
  description?: string
  confirmButtonText?: string
}

export function DiffModal({
  isOpen,
  onClose,
  onConfirmSave,
  isSaving,
  diff,
  title = 'Revisar Cambios en la Configuración',
  description = 'Verifique las diferencias antes de guardar en el archivo de configuración activo.',
  confirmButtonText = 'Confirmar y Guardar',
}: DiffModalProps) {
  const [copied, setCopied] = React.useState(false)

  if (!isOpen) return null

  const handleCopyDiff = () => {
    if (diff?.unified_diff) {
      navigator.clipboard.writeText(diff.unified_diff)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const diffLines = (diff?.unified_diff || '').split('\n')

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4 animate-in fade-in duration-150">
      <div className="bg-surface-1 border border-border rounded-xl shadow-2xl w-full max-w-6xl max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface-2/50">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-accent/10 border border-accent/20 text-accent">
              <FileText size={18} />
            </div>
            <div>
              <h3 className="text-base font-semibold text-foreground">{title}</h3>
              <p className="text-xs text-muted-foreground">{description}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-surface-3 transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Changes Summary Pills */}
        {diff && (
          <div className="px-6 py-3 border-b border-border bg-surface-1 flex flex-wrap items-center gap-2 text-xs">
            <span className="font-mono text-muted-foreground">Resumen:</span>
            {diff.added_keys.length > 0 && (
              <span className="px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-mono">
                +{diff.added_keys.length} añadidos
              </span>
            )}
            {diff.modified_keys.length > 0 && (
              <span className="px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-400 font-mono">
                ~{diff.modified_keys.length} modificados
              </span>
            )}
            {diff.removed_keys.length > 0 && (
              <span className="px-2 py-0.5 rounded bg-rose-500/10 border border-rose-500/30 text-rose-400 font-mono">
                -{diff.removed_keys.length} eliminados
              </span>
            )}
            {diff.env_changes && diff.env_changes.length > 0 && (
              <span className="px-2 py-0.5 rounded bg-blue-500/10 border border-blue-500/30 text-blue-400 font-mono flex items-center gap-1">
                <Lock size={11} />
                {diff.env_changes.length} en .env
              </span>
            )}
            {!diff.has_changes && (
              <span className="px-2 py-0.5 rounded bg-surface-3 border border-border text-muted-foreground font-mono">
                Sin cambios respecto a la versión guardada
              </span>
            )}
            <div className="ml-auto">
              <button
                type="button"
                onClick={handleCopyDiff}
                className="flex items-center gap-1 px-2.5 py-1 rounded text-xs font-mono text-muted-foreground hover:text-foreground hover:bg-surface-2 transition-colors border border-border"
              >
                {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                <span>{copied ? 'Copiado' : 'Copiar Diff'}</span>
              </button>
            </div>
          </div>
        )}

        {/* Environment Secrets Isolation Banner */}
        {diff?.env_changes && diff.env_changes.length > 0 && (
          <div className="mx-6 my-2.5 p-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 flex items-start gap-3 text-xs shrink-0">
            <div className="p-1.5 rounded-md bg-emerald-500/20 text-emerald-400 shrink-0 mt-0.5">
              <ShieldCheck size={16} />
            </div>
            <div className="space-y-1">
              <p className="font-semibold text-emerald-300">
                Aislamiento Seguro de Credenciales (.env)
              </p>
              <p className="text-emerald-200/80 text-[11px] leading-relaxed">
                Los siguientes datos sensibles han sido detectados en el editor y se aislarán automáticamente en el archivo{' '}
                <code className="font-mono bg-black/40 px-1 py-0.5 rounded text-emerald-300">.env</code>.
                En <code className="font-mono bg-black/40 px-1 py-0.5 rounded text-emerald-300">system.yaml</code> solo se guardará la referencia{' '}
                <code className="font-mono bg-black/40 px-1 py-0.5 rounded text-emerald-300">{'${VAR}'}</code>, garantizando que ninguna clave secreta se exponga en texto plano:
              </p>
              <div className="flex flex-wrap gap-1.5 pt-1">
                {diff.env_changes.map((ec) => (
                  <span
                    key={ec.variable}
                    className="inline-flex items-center gap-1 px-2 py-0.5 font-mono text-[11px] rounded bg-emerald-950/60 border border-emerald-500/40 text-emerald-200"
                  >
                    <Lock size={10} className="text-emerald-400" />
                    {ec.variable}
                    <span className="text-[10px] text-emerald-400/70">
                      ({ec.action === 'created' ? 'nueva' : 'actualizada'})
                    </span>
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Diff Code Viewer */}
        <div className="flex-1 overflow-auto p-4 bg-background font-mono text-xs leading-relaxed">
          {diffLines.length === 0 || !diff?.has_changes ? (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
              <CheckCircle2 size={32} className="text-emerald-400 mb-2" />
              <p className="text-sm font-sans font-medium text-foreground">No se detectaron cambios</p>
              <p className="text-xs text-muted-foreground mt-1">
                La configuración propuesta es idéntica a la guardada en disco.
              </p>
            </div>
          ) : (
            <div className="space-y-0.5 select-text">
              {diffLines.map((line, idx) => {
                let lineClass = 'text-muted-foreground'
                let bgClass = 'hover:bg-surface-2/30'

                if (line.startsWith('+') && !line.startsWith('+++')) {
                  lineClass = 'text-emerald-400'
                  bgClass = 'bg-emerald-950/25 border-l-2 border-emerald-500 pl-1'
                } else if (line.startsWith('-') && !line.startsWith('---')) {
                  lineClass = 'text-rose-400'
                  bgClass = 'bg-rose-950/25 border-l-2 border-rose-500 pl-1'
                } else if (line.startsWith('@@')) {
                  lineClass = 'text-cyan-400 font-bold bg-surface-2/60 px-1 rounded'
                }

                return (
                  <div key={idx} className={`flex items-start py-0.5 px-2 rounded-xs ${bgClass}`}>
                    <span className="w-8 shrink-0 text-right pr-3 select-none text-muted-foreground/50 text-[11px]">
                      {idx + 1}
                    </span>
                    <pre className={`flex-1 whitespace-pre-wrap break-all ${lineClass}`}>{line}</pre>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-border bg-surface-2/50">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <AlertTriangle size={14} className="text-amber-400" />
            <span>Se creará automáticamente un respaldo previo al reemplazo del archivo.</span>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-surface-3 transition-colors border border-border"
            >
              Cancelar
            </button>
            <button
              type="button"
              onClick={onConfirmSave}
              disabled={isSaving || !diff?.has_changes}
              className="flex items-center gap-2 px-5 py-2 rounded-lg text-xs font-medium font-mono bg-accent text-accent-foreground hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
            >
              {isSaving ? 'Guardando...' : confirmButtonText}
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
