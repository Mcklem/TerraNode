'use client'

import { useState, useEffect } from 'react'
import {
  History,
  Download,
  FileArchive,
  RotateCw,
  CheckCircle2,
  AlertCircle,
  Clock,
  Usb,
  ExternalLink,
} from 'lucide-react'
import type { BuildRecord } from '@/lib/terranode-api'
import {
  fetchFirmwareHistory,
  getFirmwareBinaryUrl,
  getFirmwareSourceUrl,
} from '@/lib/terranode-api'

interface BuildHistoryTableProps {
  onSelectBuild: (build: BuildRecord) => void
}

export function BuildHistoryTable({ onSelectBuild }: BuildHistoryTableProps) {
  const [builds, setBuilds] = useState<BuildRecord[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadHistory = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await fetchFirmwareHistory(50, 0)
      setBuilds(data.builds || [])
      setTotal(data.total || 0)
    } catch (err: any) {
      setError(err.message || 'Error al cargar el historial de compilaciones.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadHistory()
  }, [])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <History className="text-primary" size={20} />
            Historial de Builds y Auditoría
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Registro de compilaciones anteriores guardadas en <code>controller.db</code>. Puedes volver a descargar binarios o flashear placas directamente.
          </p>
        </div>

        <button
          type="button"
          onClick={loadHistory}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono border border-border text-foreground hover:border-accent transition-colors"
        >
          <RotateCw size={14} className={loading ? 'animate-spin' : ''} />
          <span>Refrescar</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl border border-destructive/40 bg-destructive/10 text-destructive text-sm flex items-start gap-3">
          <AlertCircle size={18} className="shrink-0 mt-0.5" />
          <p>{error}</p>
        </div>
      )}

      {loading ? (
        <div className="p-12 text-center text-muted-foreground font-mono text-xs">
          Cargando historial desde base de datos...
        </div>
      ) : builds.length === 0 ? (
        <div className="text-center py-12 border border-dashed border-border rounded-xl">
          <Clock size={36} className="mx-auto text-muted-foreground mb-3 opacity-60" />
          <p className="text-sm font-medium text-muted-foreground">
            Aún no se han generado compilaciones de firmware.
          </p>
        </div>
      ) : (
        <div className="rounded-xl border border-border bg-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-surface-2 border-b border-border text-muted-foreground uppercase text-[10px]">
                <tr>
                  <th className="py-3 px-4">Fecha y Hora</th>
                  <th className="py-3 px-4">Plantilla / Versión</th>
                  <th className="py-3 px-4">Placa (FQBN)</th>
                  <th className="py-3 px-4">Estado</th>
                  <th className="py-3 px-4">Checksum SHA256</th>
                  <th className="py-3 px-4 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {builds.map((b) => {
                  const dateStr = new Date(b.timestamp * 1000).toLocaleString()
                  const isCompiled = b.status === 'COMPILED'
                  const isFailed = b.status === 'FAILED'

                  return (
                    <tr key={b.id} className="hover:bg-surface-2/50 transition-colors">
                      <td className="py-3 px-4 text-foreground whitespace-nowrap">
                        {dateStr}
                      </td>
                      <td className="py-3 px-4">
                        <span className="font-semibold text-foreground">{b.template_id}</span>
                        <span className="text-muted-foreground ml-1.5">v{b.template_version}</span>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">{b.target_fqbn}</td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold border ${
                            isCompiled
                              ? 'bg-primary/10 border-primary/30 text-primary'
                              : isFailed
                              ? 'bg-destructive/10 border-destructive/30 text-destructive'
                              : 'bg-surface-2 border-border text-muted-foreground'
                          }`}
                        >
                          {isCompiled ? (
                            <CheckCircle2 size={12} />
                          ) : isFailed ? (
                            <AlertCircle size={12} />
                          ) : (
                            <Clock size={12} />
                          )}
                          {b.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground max-w-[150px] truncate" title={b.checksum_sha256 || ''}>
                        {b.checksum_sha256 ? b.checksum_sha256.substring(0, 12) + '…' : '—'}
                      </td>
                      <td className="py-3 px-4 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => onSelectBuild(b)}
                            className="p-1.5 rounded hover:bg-surface-2 text-muted-foreground hover:text-accent transition-colors"
                            title="Ver detalles o grabar por USB"
                          >
                            <Usb size={15} />
                          </button>

                          <a
                            href={getFirmwareSourceUrl(b.id)}
                            download={`firmware_${b.id}.zip`}
                            className="p-1.5 rounded hover:bg-surface-2 text-muted-foreground hover:text-foreground transition-colors"
                            title="Descargar fuentes (.zip)"
                          >
                            <FileArchive size={15} />
                          </a>

                          {isCompiled && (
                            <a
                              href={getFirmwareBinaryUrl(b.id)}
                              download={b.binary_filename || `firmware_${b.id}.bin`}
                              className="p-1.5 rounded hover:bg-surface-2 text-muted-foreground hover:text-primary transition-colors"
                              title="Descargar binario (.bin)"
                            >
                              <Download size={15} />
                            </a>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
