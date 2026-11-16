'use client'

import React, { useState } from 'react'
import {
  AlertTriangle,
  Archive,
  Check,
  Clock,
  Copy,
  Eye,
  FileText,
  History,
  RefreshCw,
  RotateCcw,
  Trash2,
  User,
  X,
} from 'lucide-react'
import type { BackupMetadata } from '@/lib/config-api'
import { fetchBackupDetail } from '@/lib/config-api'

interface HistoryTabProps {
  backups: BackupMetadata[]
  isLoading: boolean
  onRestore: (backupId: string) => void
  onDelete: (backupId: string) => void
  onRefresh: () => void
}

export function HistoryTab({
  backups,
  isLoading,
  onRestore,
  onDelete,
  onRefresh,
}: HistoryTabProps) {
  const [inspectingBackupId, setInspectingBackupId] = useState<string | null>(null)
  const [inspectingYaml, setInspectingYaml] = useState<string>('')
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [copied, setCopied] = useState(false)

  const handleInspect = async (backupId: string) => {
    setInspectingBackupId(backupId)
    setLoadingDetail(true)
    try {
      const res = await fetchBackupDetail(backupId)
      setInspectingYaml(res.raw_yaml)
    } catch (e: any) {
      setInspectingYaml(`# Error al cargar respaldo: ${e.message}`)
    } finally {
      setLoadingDetail(false)
    }
  }

  const handleCopyYaml = () => {
    navigator.clipboard.writeText(inspectingYaml)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const formatDate = (isoStr: string) => {
    try {
      const d = new Date(isoStr)
      return d.toLocaleString('es-ES', {
        dateStyle: 'medium',
        timeStyle: 'short',
      })
    } catch {
      return isoStr
    }
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
            <History size={18} className="text-accent" />
            Historial de Versiones y Respaldos (`config/backups/`)
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Instantáneas automáticas previas a cada guardado y puntos de restauración (rollback).
          </p>
        </div>

        <button
          type="button"
          onClick={onRefresh}
          disabled={isLoading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono border border-border bg-surface-2 text-foreground hover:bg-surface-3 transition-colors"
        >
          <RefreshCw size={13} className={isLoading ? 'animate-spin' : ''} />
          <span>Refrescar Respaldos</span>
        </button>
      </div>

      {/* Backups List */}
      <div className="space-y-3">
        {backups.map((b, idx) => {
          const isLatest = idx === 0
          return (
            <div
              key={b.id}
              className={`p-4 rounded-xl border bg-surface-1 transition-all ${
                isLatest ? 'border-accent/40 bg-surface-1/90' : 'border-border'
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="p-1 rounded bg-surface-2 text-accent">
                      <Archive size={14} />
                    </span>
                    <h4 className="font-mono font-bold text-xs text-foreground">{b.id}</h4>
                    {isLatest && (
                      <span className="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-accent/20 border border-accent/40 text-accent">
                        MÁS RECIENTE
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">{b.description}</p>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => handleInspect(b.id)}
                    className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-mono border border-border bg-surface-2 text-foreground hover:border-accent transition-colors"
                    title="Ver contenido YAML del respaldo"
                  >
                    <Eye size={13} />
                    <span>Inspeccionar</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => onRestore(b.id)}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-mono font-medium bg-amber-500/10 border border-amber-500/30 text-amber-300 hover:bg-amber-500/20 transition-colors"
                    title="Restaurar este respaldo como configuración activa"
                  >
                    <RotateCcw size={13} />
                    <span>Rollback</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => onDelete(b.id)}
                    disabled={backups.length <= 1}
                    className="p-1.5 rounded-lg text-muted-foreground hover:text-rose-400 hover:bg-surface-2 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                    title="Eliminar este respaldo"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              {/* Metadata strip */}
              <div className="mt-3 pt-2 border-t border-border/50 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] font-mono text-muted-foreground">
                <span className="flex items-center gap-1">
                  <Clock size={11} /> {formatDate(b.timestamp)}
                </span>
                <span className="flex items-center gap-1">
                  <User size={11} /> {b.author}
                </span>
                <span>Tamaño: {(b.size_bytes / 1024).toFixed(1)} KB</span>
                <span title={b.checksum}>
                  Hash: <code>{b.checksum.slice(0, 10)}…</code>
                </span>

                {b.diff_summary && (
                  <div className="ml-auto flex items-center gap-1.5 text-[10px]">
                    {b.diff_summary.added && b.diff_summary.added.length > 0 && (
                      <span className="text-emerald-400">+{b.diff_summary.added.length}</span>
                    )}
                    {b.diff_summary.modified && b.diff_summary.modified.length > 0 && (
                      <span className="text-amber-400">~{b.diff_summary.modified.length}</span>
                    )}
                    {b.diff_summary.removed && b.diff_summary.removed.length > 0 && (
                      <span className="text-rose-400">-{b.diff_summary.removed.length}</span>
                    )}
                  </div>
                )}
              </div>
            </div>
          )
        })}

        {backups.length === 0 && !isLoading && (
          <div className="py-12 flex flex-col items-center justify-center border border-dashed border-border rounded-xl text-muted-foreground">
            <Archive size={32} className="mb-2 text-muted-foreground/60" />
            <p className="font-sans font-medium text-foreground text-sm">No hay respaldos guardados</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Los respaldos se generan automáticamente cada vez que se guarda una configuración.
            </p>
          </div>
        )}
      </div>

      {/* Inspect Backup Modal */}
      {inspectingBackupId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4 animate-in fade-in duration-150">
          <div className="bg-surface-1 border border-border rounded-xl shadow-2xl w-full max-w-6xl max-h-[85vh] flex flex-col overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface-2/50">
              <div className="flex items-center gap-2">
                <FileText size={16} className="text-accent" />
                <h3 className="text-sm font-semibold text-foreground">
                  Inspección de Respaldo: <span className="font-mono">{inspectingBackupId}</span>
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setInspectingBackupId(null)}
                className="p-1 rounded text-muted-foreground hover:text-foreground"
              >
                <X size={16} />
              </button>
            </div>

            <div className="px-6 py-2 border-b border-border bg-surface-1 flex items-center justify-between">
              <span className="text-xs font-mono text-muted-foreground">
                Vista de solo lectura del archivo histórico YAML
              </span>
              <button
                type="button"
                onClick={handleCopyYaml}
                className="flex items-center gap-1 px-2.5 py-1 rounded text-xs font-mono text-muted-foreground hover:text-foreground hover:bg-surface-2 border border-border"
              >
                {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                <span>{copied ? 'Copiado' : 'Copiar Contenido'}</span>
              </button>
            </div>

            <div className="flex-1 overflow-auto p-4 bg-[#0d1117] text-[#e6edf3] font-mono text-xs leading-relaxed">
              {loadingDetail ? (
                <div className="flex items-center justify-center py-20 text-muted-foreground">
                  Cargando respaldo...
                </div>
              ) : (
                <pre className="whitespace-pre">{inspectingYaml}</pre>
              )}
            </div>

            <div className="flex items-center justify-between px-6 py-3 border-t border-border bg-surface-2/50">
              <button
                type="button"
                onClick={() => setInspectingBackupId(null)}
                className="px-4 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground border border-border rounded-lg"
              >
                Cerrar
              </button>
              <button
                type="button"
                onClick={() => {
                  const id = inspectingBackupId
                  setInspectingBackupId(null)
                  onRestore(id)
                }}
                className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-mono font-bold bg-amber-500 text-black rounded-lg hover:bg-amber-400 shadow-sm"
              >
                <RotateCcw size={13} />
                <span>Restaurar Esta Versión</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
