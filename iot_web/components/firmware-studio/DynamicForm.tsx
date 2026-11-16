'use client'

import { useState } from 'react'
import {
  ShieldAlert,
  Eye,
  EyeOff,
  Cpu,
  CheckCircle2,
  AlertCircle,
  FileCode2,
  ArrowLeft,
  Loader2,
} from 'lucide-react'
import type { FirmwareManifest, FirmwareParameter } from '@/lib/terranode-api'

interface DynamicFormProps {
  template: FirmwareManifest
  onBack: () => void
  onGenerate: (params: Record<string, unknown>) => Promise<void>
  busy: boolean
  error?: string
}

export function DynamicForm({
  template,
  onBack,
  onGenerate,
  busy,
  error,
}: DynamicFormProps) {
  // Initialize form with defaults
  const [formValues, setFormValues] = useState<Record<string, any>>(() => {
    const initial: Record<string, any> = {}
    template.parameters?.forEach((p) => {
      initial[p.id] = p.default !== undefined && p.default !== null ? p.default : ''
    })
    return initial
  })

  const [visibleSecrets, setVisibleSecrets] = useState<Record<string, boolean>>({})
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({})

  const handleChange = (paramId: string, val: any) => {
    setFormValues((prev) => ({ ...prev, [paramId]: val }))
    if (validationErrors[paramId]) {
      setValidationErrors((prev) => {
        const copy = { ...prev }
        delete copy[paramId]
        return copy
      })
    }
  }

  const toggleSecretVisibility = (paramId: string) => {
    setVisibleSecrets((prev) => ({ ...prev, [paramId]: !prev[paramId] }))
  }

  const validateLocal = (): boolean => {
    const errs: Record<string, string> = {}
    template.parameters?.forEach((param) => {
      const val = formValues[param.id]
      if (param.required && (val === '' || val === null || val === undefined)) {
        errs[param.id] = `El campo '${param.label}' es obligatorio.`
        return
      }

      if (param.type === 'port' && val) {
        const port = Number(val)
        if (isNaN(port) || port < 1 || port > 65535) {
          errs[param.id] = 'Debe ser un puerto válido entre 1 y 65535.'
        }
      }

      if (param.type === 'ip' && val) {
        const ipRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/
        if (!ipRegex.test(String(val))) {
          errs[param.id] = 'Debe ser una dirección IPv4 válida (ej. 192.168.1.50).'
        }
      }

      if (param.min_length && String(val).length < param.min_length) {
        errs[param.id] = `Debe tener al menos ${param.min_length} caracteres.`
      }
    })

    setValidationErrors(errs)
    return Object.keys(errs).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validateLocal()) return
    await onGenerate(formValues)
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-border">
        <button
          type="button"
          onClick={onBack}
          disabled={busy}
          className="flex items-center gap-1.5 text-xs font-mono text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft size={14} />
          <span>Volver al catálogo</span>
        </button>

        <div className="flex items-center gap-2">
          <span className="px-2.5 py-0.5 rounded text-xs font-mono bg-surface-2 border border-border text-foreground">
            {template.board.name || template.board.fqbn}
          </span>
          <span className="px-2 py-0.5 rounded text-xs font-mono bg-primary/10 text-primary border border-primary/20">
            v{template.version}
          </span>
        </div>
      </div>

      <div>
        <h2 className="text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
          <FileCode2 className="text-accent" size={20} />
          Configuración: {template.name}
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          Rellena los valores requeridos. El sistema generará el código fuente en C++ sustituyendo automáticamente los marcadores sin modificar los archivos originales.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-xl border border-destructive/40 bg-destructive/10 text-destructive text-sm flex items-start gap-3">
          <AlertCircle size={18} className="shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Error al validar o generar firmware</p>
            <p className="text-xs mt-0.5 opacity-90">{error}</p>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-6 rounded-xl border border-border bg-card">
          {template.parameters?.map((param: FirmwareParameter) => {
            const isPassword = param.type === 'password' || param.type === 'secret'
            const isVisible = visibleSecrets[param.id]
            const fieldError = validationErrors[param.id]
            const value = formValues[param.id] ?? ''

            return (
              <div
                key={param.id}
                className={param.type === 'boolean' ? 'col-span-1' : 'col-span-1'}
              >
                <label className="block text-xs font-mono font-medium text-foreground mb-1.5">
                  {param.label}
                  {param.required && <span className="text-destructive ml-1">*</span>}
                </label>

                {param.type === 'select' ? (
                  <select
                    value={value}
                    onChange={(e) => handleChange(param.id, e.target.value)}
                    disabled={busy}
                    className="w-full px-3 py-2 rounded-lg bg-surface-2 border border-border text-sm text-foreground focus:outline-none focus:border-accent"
                  >
                    {param.options?.map((opt) => (
                      <option key={String(opt.value)} value={String(opt.value)}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                ) : param.type === 'boolean' ? (
                  <label className="flex items-center gap-2 mt-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={Boolean(value)}
                      onChange={(e) => handleChange(param.id, e.target.checked)}
                      disabled={busy}
                      className="rounded border-border text-primary focus:ring-accent w-4 h-4 bg-surface-2"
                    />
                    <span className="text-xs text-muted-foreground">{param.description || 'Habilitar'}</span>
                  </label>
                ) : (
                  <div className="relative">
                    <input
                      type={isPassword ? (isVisible ? 'text' : 'password') : 'text'}
                      value={value}
                      placeholder={param.default !== undefined ? String(param.default) : ''}
                      onChange={(e) => handleChange(param.id, e.target.value)}
                      disabled={busy}
                      className={`w-full px-3 py-2 rounded-lg bg-surface-2 border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none ${
                        fieldError
                          ? 'border-destructive focus:border-destructive'
                          : 'border-border focus:border-accent'
                      } ${isPassword ? 'pr-10' : ''}`}
                    />

                    {isPassword && (
                      <button
                        type="button"
                        onClick={() => toggleSecretVisibility(param.id)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                        tabIndex={-1}
                      >
                        {isVisible ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    )}
                  </div>
                )}

                {param.description && param.type !== 'boolean' && (
                  <p className="text-[11px] text-muted-foreground mt-1 leading-normal">
                    {param.description}
                  </p>
                )}

                {fieldError && (
                  <p className="text-[11px] text-destructive mt-1 font-mono">
                    {fieldError}
                  </p>
                )}
              </div>
            )
          })}
        </div>

        <div className="flex items-center justify-between pt-4">
          <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono">
            <ShieldAlert size={14} className="text-primary" />
            <span>Los secretos se procesan en memoria y no se persisten en base de datos.</span>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onBack}
              disabled={busy}
              className="px-4 py-2 rounded-lg text-xs font-mono border border-border text-foreground hover:border-muted-foreground transition-colors"
            >
              Cancelar
            </button>

            <button
              type="submit"
              disabled={busy}
              className="flex items-center gap-2 px-5 py-2 rounded-lg text-xs font-mono font-medium bg-primary text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {busy ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  <span>Generando código...</span>
                </>
              ) : (
                <>
                  <CheckCircle2 size={14} />
                  <span>Validar y Generar Código</span>
                </>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
