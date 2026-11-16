'use client'

import React, { useEffect, useRef, useState } from 'react'
import {
  AlertCircle,
  AlertTriangle,
  Check,
  CheckCircle2,
  Copy,
  FileCode2,
  Play,
  RotateCcw,
  Save,
  Search,
  Sparkles,
  XCircle,
} from 'lucide-react'
import type { ValidationResult } from '@/lib/config-api'

interface RawYamlTabProps {
  yamlContent: string
  originalYaml: string
  validation: ValidationResult | null
  isValidating: boolean
  isSaving: boolean
  onChange: (newContent: string) => void
  onValidate: () => void
  onSave: () => void
  onRevert: () => void
}

export function RawYamlTab({
  yamlContent,
  originalYaml,
  validation,
  isValidating,
  isSaving,
  onChange,
  onValidate,
  onSave,
  onRevert,
}: RawYamlTabProps) {
  const [copied, setCopied] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [activeErrorLine, setActiveErrorLine] = useState<number | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const lineNumbersRef = useRef<HTMLDivElement>(null)

  const lines = yamlContent.split('\n')
  const lineCount = lines.length
  const hasChanges = yamlContent !== originalYaml
  const isValid = validation?.valid ?? true
  const errors = validation?.errors || []

  // Sync scroll between textarea and line numbers gutter
  const handleScroll = (e: React.UIEvent<HTMLTextAreaElement>) => {
    if (lineNumbersRef.current) {
      lineNumbersRef.current.scrollTop = e.currentTarget.scrollTop
    }
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(yamlContent)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Handle Tab key inside textarea
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Tab') {
      e.preventDefault()
      const textarea = e.currentTarget
      const start = textarea.selectionStart
      const end = textarea.selectionEnd

      const newContent =
        yamlContent.substring(0, start) + '  ' + yamlContent.substring(end)
      onChange(newContent)

      setTimeout(() => {
        textarea.selectionStart = textarea.selectionEnd = start + 2
      }, 0)
    }
  }

  const errorLinesSet = new Set(errors.filter((e) => e.line != null).map((e) => e.line as number))

  return (
    <div className="space-y-4 animate-in fade-in duration-200">
      {/* Editor Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl border border-border bg-surface-1">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-md bg-accent/10 border border-accent/20 text-accent">
            <FileCode2 size={16} />
          </div>
          <div>
            <h4 className="text-xs font-mono font-bold text-foreground">
              Editor YAML Directo (`system.yaml`)
            </h4>
            <p className="text-[11px] text-muted-foreground">
              {lineCount} líneas · Comentarios y formato preservados en round-trip
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Unsaved changes indicator */}
          {hasChanges && (
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-mono bg-amber-500/10 border border-amber-500/30 text-amber-300">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
              Cambios sin guardar
            </span>
          )}

          {/* Revert Button */}
          <button
            type="button"
            onClick={onRevert}
            disabled={!hasChanges}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-mono border border-border bg-surface-2 text-muted-foreground hover:text-foreground hover:bg-surface-3 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            title="Descartar cambios y restaurar el YAML activo en disco"
          >
            <RotateCcw size={13} />
            <span>Descartar</span>
          </button>

          {/* Copy Button */}
          <button
            type="button"
            onClick={handleCopy}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-mono border border-border bg-surface-2 text-muted-foreground hover:text-foreground hover:bg-surface-3 transition-colors"
            title="Copiar YAML al portapapeles"
          >
            {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
            <span>{copied ? 'Copiado' : 'Copiar'}</span>
          </button>

          {/* Validate Button */}
          <button
            type="button"
            onClick={onValidate}
            disabled={isValidating}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono border border-border bg-surface-2 text-foreground hover:border-accent hover:text-accent transition-colors"
            title="Validar sintaxis y semántica"
          >
            <CheckCircle2 size={13} className="text-accent" />
            <span>{isValidating ? 'Validando…' : 'Validar'}</span>
          </button>

          {/* Save Button */}
          <button
            type="button"
            onClick={onSave}
            disabled={isSaving || !isValid}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-mono font-medium bg-accent text-accent-foreground hover:bg-accent/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
          >
            <Save size={13} />
            <span>Guardar YAML</span>
          </button>
        </div>
      </div>

      {/* Code Editor Container */}
      <div className="relative rounded-xl border border-border bg-[#0d1117] shadow-inner overflow-hidden flex flex-col min-h-[550px] max-h-[70vh]">
        {/* Editor Body with Line Numbers */}
        <div className="flex-1 flex overflow-hidden">
          {/* Gutter (Line Numbers) */}
          <div
            ref={lineNumbersRef}
            className="w-12 py-3 bg-[#090d13] border-r border-border/40 select-none overflow-hidden font-mono text-[11px] leading-[20px] text-right pr-2 text-muted-foreground/40 shrink-0"
          >
            {Array.from({ length: lineCount }).map((_, idx) => {
              const lineNum = idx + 1
              const isError = errorLinesSet.has(lineNum)
              return (
                <div
                  key={idx}
                  className={`h-[20px] ${
                    isError ? 'text-rose-400 font-bold bg-rose-950/40 rounded-xs' : ''
                  }`}
                >
                  {lineNum}
                </div>
              )
            })}
          </div>

          {/* Textarea */}
          <textarea
            ref={textareaRef}
            value={yamlContent}
            onChange={(e) => onChange(e.target.value)}
            onScroll={handleScroll}
            onKeyDown={handleKeyDown}
            spellCheck={false}
            className="flex-1 py-3 px-3 bg-transparent text-[#e6edf3] font-mono text-[11px] leading-[20px] resize-none outline-none overflow-auto whitespace-pre tab-2 selection:bg-accent/30 selection:text-white"
          />
        </div>

        {/* Validation Errors Drawer at bottom */}
        {errors.length > 0 && (
          <div className="border-t border-rose-500/40 bg-rose-950/30 p-3 max-h-36 overflow-auto text-xs font-mono space-y-1">
            <div className="flex items-center gap-1.5 text-rose-300 font-bold text-[11px] mb-1">
              <XCircle size={14} className="text-rose-400" />
              <span>Errores de Validación ({errors.length}):</span>
            </div>
            {errors.map((err, i) => (
              <div
                key={i}
                className="flex items-start gap-1.5 text-rose-200/90 text-[11px] hover:text-rose-100 cursor-pointer"
                onClick={() => {
                  if (err.line && textareaRef.current) {
                    const linePos = err.line - 1
                    const lineHeight = 20
                    textareaRef.current.scrollTop = linePos * lineHeight - 60
                  }
                }}
              >
                <span className="font-bold text-rose-400 shrink-0">
                  {err.line ? `[Línea ${err.line}]` : `[${err.field}]`}
                </span>
                <span>{err.message}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
