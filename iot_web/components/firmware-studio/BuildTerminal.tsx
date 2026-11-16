'use client'

import { useState } from 'react'
import {
  Terminal,
  Download,
  Play,
  RotateCw,
  CheckCircle2,
  AlertCircle,
  Clock,
  Cpu,
  Usb,
  FileArchive,
  Layers,
} from 'lucide-react'
import type { BuildRecord } from '@/lib/terranode-api'
import { getFirmwareBinaryUrl, getFirmwareSourceUrl } from '@/lib/terranode-api'

interface BuildTerminalProps {
  build: BuildRecord
  onCompile: (forceMock?: boolean) => Promise<void>
  onSwitchToFlash: () => void
  busy: boolean
}

export function BuildTerminal({
  build,
  onCompile,
  onSwitchToFlash,
  busy,
}: BuildTerminalProps) {
  const isCompiled = build.status === 'COMPILED'
  const isFailed = build.status === 'FAILED'
  const isCompiling = build.status === 'COMPILING'

  const binaryUrl = getFirmwareBinaryUrl(build.id)
  const sourceUrl = getFirmwareSourceUrl(build.id)

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header and status banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-xl border border-border bg-card">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-muted-foreground">BUILD ID:</span>
            <span className="text-xs font-mono font-medium text-foreground">{build.id}</span>
          </div>
          <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
            <Cpu className="text-primary" size={18} />
            {build.template_id}
            <span className="text-xs font-mono font-normal text-muted-foreground">
              ({build.target_fqbn})
            </span>
          </h2>
        </div>

        <div className="flex items-center gap-3">
          <div
            className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold flex items-center gap-2 border ${
              isCompiled
                ? 'bg-primary/10 border-primary/30 text-primary'
                : isFailed
                ? 'bg-destructive/10 border-destructive/30 text-destructive'
                : isCompiling
                ? 'bg-accent/10 border-accent/30 text-accent'
                : 'bg-surface-2 border-border text-muted-foreground'
            }`}
          >
            {isCompiled ? (
              <>
                <CheckCircle2 size={14} />
                <span>COMPILED</span>
              </>
            ) : isFailed ? (
              <>
                <AlertCircle size={14} />
                <span>FAILED</span>
              </>
            ) : isCompiling ? (
              <>
                <RotateCw size={14} className="animate-spin" />
                <span>COMPILING</span>
              </>
            ) : (
              <>
                <Clock size={14} />
                <span>{build.status}</span>
              </>
            )}
          </div>

          {isCompiled && (
            <button
              type="button"
              onClick={onSwitchToFlash}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-mono font-medium bg-accent text-accent-foreground hover:opacity-90 transition-opacity"
            >
              <Usb size={14} />
              <span>Grabar en Placa (USB)</span>
            </button>
          )}
        </div>
      </div>

      {/* Terminal logs container */}
      <div className="rounded-xl border border-border bg-[#050b0e] overflow-hidden shadow-2xl">
        <div className="flex items-center justify-between px-4 py-2.5 bg-surface-2 border-b border-border">
          <div className="flex items-center gap-2">
            <div className="flex gap-1.5">
              <div className="w-2.5 h-2.5 rounded-full bg-destructive/60" />
              <div className="w-2.5 h-2.5 rounded-full bg-amber-500/60" />
              <div className="w-2.5 h-2.5 rounded-full bg-primary/60" />
            </div>
            <span className="text-xs font-mono text-muted-foreground ml-2">
              arduino-cli / compilation stdout
            </span>
          </div>

          <div className="text-[11px] font-mono text-muted-foreground">
            {build.completed_at ? 'Finalizado' : isCompiling ? 'En ejecución...' : 'Listo'}
          </div>
        </div>

        <div className="p-4 font-mono text-xs text-foreground/90 overflow-x-auto max-h-96 min-h-60 leading-relaxed whitespace-pre-wrap select-text">
          {build.compiler_output ? (
            build.compiler_output
          ) : (
            <div className="text-muted-foreground py-8 text-center italic">
              Código fuente generado correctamente. Haz clic en "Iniciar Compilación" para generar el archivo binario (.bin) o descarga el código fuente modificado.
            </div>
          )}
        </div>

        {build.checksum_sha256 && (
          <div className="px-4 py-2 bg-surface-2 border-t border-border flex items-center justify-between text-[11px] font-mono text-muted-foreground">
            <span>SHA256 CHECKSUM:</span>
            <span className="text-foreground">{build.checksum_sha256}</span>
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
        <div className="flex items-center gap-3">
          <a
            href={sourceUrl}
            download={`firmware_${build.id}.zip`}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-mono border border-border text-foreground hover:border-accent transition-colors"
            title="Descargar paquete completo con variables reemplazadas"
          >
            <FileArchive size={14} className="text-accent" />
            <span>Descargar Fuentes (.zip)</span>
          </a>

          {isCompiled && (
            <a
              href={binaryUrl}
              download={build.binary_filename || `firmware_${build.id}.bin`}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-mono border border-border text-foreground hover:border-primary transition-colors"
              title="Descargar binario compilado listo para flashear"
            >
              <Download size={14} className="text-primary" />
              <span>Descargar Binario (.bin)</span>
            </a>
          )}
        </div>

        <div className="flex items-center gap-3">
          {!isCompiled && (
            <button
              type="button"
              onClick={() => onCompile(false)}
              disabled={busy || isCompiling}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-xs font-mono font-medium bg-primary text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-50 shadow-md"
            >
              {isCompiling ? (
                <>
                  <RotateCw size={14} className="animate-spin" />
                  <span>Compilando...</span>
                </>
              ) : (
                <>
                  <Play size={14} />
                  <span>Iniciar Compilación (.bin)</span>
                </>
              )}
            </button>
          )}

          {isFailed && (
            <button
              type="button"
              onClick={() => onCompile(false)}
              disabled={busy}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-mono bg-destructive/20 border border-destructive text-destructive hover:bg-destructive/30"
            >
              <RotateCw size={14} />
              <span>Reintentar</span>
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
