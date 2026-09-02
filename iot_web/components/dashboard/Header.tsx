'use client'

import { Radio, RefreshCw, Server, Settings2 } from 'lucide-react'
import type { Health, TerraNode } from '@/lib/terranode-api'

interface HeaderProps {
  health: Health | null
  nodes: TerraNode[]
  devicesCount: number
  overridesCount: number
  hasError: boolean
  isRefreshing: boolean
  onRefresh: () => void
}

export function Header({
  health,
  nodes,
  devicesCount,
  overridesCount,
  hasError,
  isRefreshing,
  onRefresh,
}: HeaderProps) {
  const connectedNodesCount =
    health?.connected_nodes ?? nodes.filter((n) => n.connected).length
  const totalNodesCount = health?.total_nodes ?? nodes.length

  return (
    <header className="topbar">
      <div className="brand">
        <div className="brand-mark" aria-hidden="true">
          <Radio size={18} />
        </div>
        <div>
          <p className="eyebrow">FIELD OPERATIONS / LIVE</p>
          <h1>
            TerraNode <span>IoT Control Center</span>
          </h1>
        </div>
      </div>

      <div className="header-actions">
        <div className="server-status">
          <i className={hasError ? 'bg-destructive shadow-none' : ''} />
          SERVER <strong>{hasError ? 'ERROR' : 'OK'}</strong>
        </div>

        <div className="quick-stat">
          <span>NODES</span>
          <b>
            {connectedNodesCount}
            <span>/{totalNodesCount}</span>
          </b>
        </div>

        <div className="quick-stat">
          <span>DEVICES</span>
          <b>{health?.total_devices ?? devicesCount}</b>
        </div>

        <div className="quick-stat">
          <span>OVERRIDES</span>
          <b className="accent-amber">{overridesCount}</b>
        </div>

        <button
          type="button"
          className="icon-button"
          onClick={onRefresh}
          disabled={isRefreshing}
          title="Refrescar datos en vivo"
          aria-label="Refrescar datos"
        >
          <RefreshCw size={18} className={isRefreshing ? 'animate-spin' : ''} />
        </button>

        <button
          type="button"
          className="icon-button"
          title="Configuración de interfaz"
          aria-label="Configuración"
        >
          <Settings2 size={18} />
        </button>
      </div>
    </header>
  )
}
