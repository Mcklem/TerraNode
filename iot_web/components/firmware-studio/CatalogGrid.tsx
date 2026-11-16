'use client'

import { useState } from 'react'
import { Cpu, ShieldCheck, Wifi, Sparkles, ArrowRight, Search, FileCode } from 'lucide-react'
import type { FirmwareManifest } from '@/lib/terranode-api'

interface CatalogGridProps {
  templates: FirmwareManifest[]
  loading: boolean
  onSelectTemplate: (template: FirmwareManifest) => void
}

export function CatalogGrid({ templates, loading, onSelectTemplate }: CatalogGridProps) {
  const [search, setSearch] = useState('')

  const filtered = templates.filter((t) => {
    const q = search.toLowerCase()
    return (
      t.name.toLowerCase().includes(q) ||
      t.description.toLowerCase().includes(q) ||
      t.board.fqbn.toLowerCase().includes(q) ||
      t.id.toLowerCase().includes(q)
    )
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <Cpu className="text-primary" size={20} />
            Catálogo de Firmwares Oficiales
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Selecciona una plantilla predefinida para configurar parámetros de red, claves de autenticación y compilar directamente sin usar Arduino IDE.
          </p>
        </div>

        <div className="relative w-full sm:w-72">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Buscar por placa o función..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-card border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-accent"
          />
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2].map((i) => (
            <div key={i} className="p-6 rounded-xl border border-border bg-card animate-pulse h-48" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 border border-dashed border-border rounded-xl">
          <FileCode size={36} className="mx-auto text-muted-foreground mb-3 opacity-60" />
          <p className="text-sm font-medium text-muted-foreground">
            No se encontraron plantillas que coincidan con la búsqueda.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {filtered.map((tmpl) => {
            const isSecure = tmpl.id.includes('secure')

            return (
              <div
                key={tmpl.id}
                className="group relative flex flex-col justify-between p-6 rounded-xl border border-border bg-card hover:border-accent transition-all duration-200"
              >
                <div>
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="flex items-center gap-2.5">
                      <div className="p-2 rounded-lg bg-surface-2 border border-border text-primary group-hover:text-accent transition-colors">
                        {isSecure ? <ShieldCheck size={20} /> : <Wifi size={20} />}
                      </div>
                      <div>
                        <h3 className="text-base font-semibold text-foreground group-hover:text-accent transition-colors">
                          {tmpl.name}
                        </h3>
                        <p className="text-xs font-mono text-muted-foreground">
                          v{tmpl.version} • {tmpl.category.toUpperCase()}
                        </p>
                      </div>
                    </div>

                    <span className="px-2 py-0.5 rounded text-[11px] font-mono font-medium border border-border bg-surface-2 text-muted-foreground">
                      {tmpl.board.architecture?.toUpperCase() || 'ESP8266'}
                    </span>
                  </div>

                  <p className="text-xs text-muted-foreground leading-relaxed mb-4 line-clamp-3">
                    {tmpl.description}
                  </p>

                  <div className="flex flex-wrap gap-1.5 mb-5 text-[11px] font-mono">
                    <span className="px-2 py-0.5 rounded bg-surface-2 border border-border text-foreground">
                      FQBN: {tmpl.board.fqbn}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-surface-2 border border-border text-foreground">
                      {tmpl.parameters?.length || 0} parámetros
                    </span>
                    {isSecure && (
                      <span className="px-2 py-0.5 rounded bg-primary/10 border border-primary/20 text-primary flex items-center gap-1">
                        <ShieldCheck size={11} /> Sysex Auth
                      </span>
                    )}
                  </div>
                </div>

                <div className="pt-4 border-t border-border flex items-center justify-between">
                  <div className="text-[11px] text-muted-foreground font-mono">
                    Por: {tmpl.author || 'TerraNode Core'}
                  </div>

                  <button
                    type="button"
                    onClick={() => onSelectTemplate(tmpl)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium font-mono bg-primary text-primary-foreground hover:opacity-90 transition-opacity"
                  >
                    <span>Configurar</span>
                    <ArrowRight size={14} />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
