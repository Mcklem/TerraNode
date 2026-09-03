'use client'

import { AlertTriangle, Cpu, Power, Server, type LucideIcon } from 'lucide-react'
import type { Health, TerraNode } from '@/lib/terranode-api'

interface HealthGridProps {
  health: Health | null
  nodes: TerraNode[]
  devicesCount: number
  overridesCount: number
  loading: boolean
  error: string
}

interface HealthCardProps {
  icon: LucideIcon
  title: string
  value: string
  detail: string
  tone: 'lime' | 'cyan' | 'amber'
}

function HealthCard({ icon: Icon, title, value, detail, tone }: HealthCardProps) {
  return (
    <div className="health-card">
      <div className={`health-icon ${tone}`}>
        <Icon size={18} />
      </div>
      <div>
        <p>{title}</p>
        <b>{value}</b>
        <span>{detail}</span>
      </div>
    </div>
  )
}

export function HealthGrid({
  health,
  nodes,
  devicesCount,
  overridesCount,
  loading,
  error,
}: HealthGridProps) {
  const connectedCount =
    health?.connected_nodes ?? nodes.filter((n) => n.connected).length
  const totalNodesCount = health?.total_nodes ?? nodes.length
  const totalDevicesCount = health?.total_devices ?? devicesCount

  return (
    <section className="health-grid" aria-label="Métricas del sistema">
      <HealthCard
        icon={Server}
        title="SYSTEM HEALTH"
        value={health?.status || (loading ? 'Connecting' : 'Unavailable')}
        detail={error ? 'Verifica el controlador local API' : 'Todos los servicios respondiendo'}
        tone={error ? 'amber' : 'lime'}
      />
      <HealthCard
        icon={Cpu}
        title="CONNECTED NODES"
        value={`${connectedCount} / ${totalNodesCount}`}
        detail="Nodos activos en LAN/Firmata"
        tone="cyan"
      />
      <HealthCard
        icon={Power}
        title="ACTIVE DEVICES"
        value={String(totalDevicesCount)}
        detail="Catálogo de sensores/actuadores"
        tone="cyan"
      />
      <HealthCard
        icon={AlertTriangle}
        title="ATTENTION"
        value={String(overridesCount)}
        detail={overridesCount > 0 ? 'Overrides manuales bloqueando AUTO' : 'Modo automático sin bloqueos'}
        tone={overridesCount > 0 ? 'amber' : 'lime'}
      />
    </section>
  )
}
