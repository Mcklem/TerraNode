'use client'

import Link from 'next/link'
import { Cpu, ArrowLeft, Terminal, ShieldCheck } from 'lucide-react'

interface FirmwareHeaderProps {
  activeTab: 'catalog' | 'configure' | 'build' | 'history'
  onSelectTab: (tab: 'catalog' | 'configure' | 'build' | 'history') => void
  hasActiveBuild: boolean
}

export function FirmwareHeader({
  activeTab,
  onSelectTab,
  hasActiveBuild,
}: FirmwareHeaderProps) {
  return (
    <header className="topbar">
      <div className="brand">
        <Link
          href="/"
          className="brand-mark hover:border-accent transition-colors"
          title="Volver al Centro de Control TerraNode"
        >
          <ArrowLeft size={18} className="text-muted-foreground hover:text-foreground" />
        </Link>
        <div>
          <div className="flex items-center gap-2">
            <p className="eyebrow flex items-center gap-1.5 text-accent">
              <Cpu size={13} />
              HARDWARE TOOLCHAIN / FIRMWARE STUDIO
            </p>
          </div>
          <h1>
            TerraNode <span>Firmware Studio</span>
          </h1>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <nav className="flex items-center gap-1 bg-surface-2 p-1 rounded-lg border border-border">
          <button
            type="button"
            onClick={() => onSelectTab('catalog')}
            className={`px-3 py-1.5 rounded-md text-xs font-mono font-medium transition-colors ${
              activeTab === 'catalog'
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            1. Catálogo
          </button>

          <button
            type="button"
            onClick={() => onSelectTab('configure')}
            className={`px-3 py-1.5 rounded-md text-xs font-mono font-medium transition-colors ${
              activeTab === 'configure'
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            2. Configurar
          </button>

          <button
            type="button"
            onClick={() => onSelectTab('build')}
            className={`px-3 py-1.5 rounded-md text-xs font-mono font-medium transition-colors flex items-center gap-1.5 ${
              activeTab === 'build'
                ? 'bg-accent text-accent-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <Terminal size={12} />
            3. Build & Flasheo
            {hasActiveBuild && (
              <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
            )}
          </button>

          <button
            type="button"
            onClick={() => onSelectTab('history')}
            className={`px-3 py-1.5 rounded-md text-xs font-mono font-medium transition-colors ${
              activeTab === 'history'
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            4. Historial
          </button>
        </nav>

        <Link
          href="/"
          className="px-3 py-1.5 rounded-md text-xs font-mono text-muted-foreground hover:text-foreground border border-border hover:border-accent transition-colors flex items-center gap-1.5"
          title="Regresar al panel de control"
        >
          <span>Control Center</span>
        </Link>
      </div>
    </header>
  )
}
