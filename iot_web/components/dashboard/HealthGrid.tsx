'use client'

import { AlertTriangle, Cpu, Power, Server, type LucideIcon } from 'lucide-react'
import type { Device, Health, TerraNode } from '@/lib/terranode-api'

interface HealthGridProps {
  health: Health | null
  nodes: TerraNode[]
  devicesCount: number
  devices?: Device[]
  overridesCount: number
  loading: boolean
  error: string
}

interface HealthCardProps {
  icon: LucideIcon
  title: string
  value: string
  detail: string
  tone: 'lime' | 'cyan' | 'amber' | 'rose'
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
  devices,
  overridesCount,
  loading,
  error,
}: HealthGridProps) {
  const connectedCount =
    health?.connected_nodes ?? nodes.filter((n) => n.connected).length
  const totalNodesCount = health?.total_nodes ?? nodes.length
  const totalDevicesCount = health?.total_devices ?? devicesCount
  const devicesInError = devices?.filter((d) => d.status === 'ERROR').length ?? 0

  // 1. SYSTEM HEALTH CARD
  const getHealthCardState = (): {
    value: string
    detail: string
    tone: 'lime' | 'cyan' | 'amber' | 'rose'
  } => {
    if (error) {
      return {
        value: health?.status || 'Unavailable',
        detail: 'Verifica el controlador local API',
        tone: 'rose',
      }
    }
    if (loading && !health) {
      return {
        value: 'Connecting',
        detail: 'Sincronizando estado general…',
        tone: 'cyan',
      }
    }

    const status = (health?.status || 'OK').toUpperCase()

    if (status === 'ERROR') {
      return {
        value: 'ERROR',
        detail:
          health?.message ||
          (totalNodesCount > 0 && connectedCount === 0
            ? 'Sin comunicación con nodos hardware'
            : 'Fallo crítico en servicios'),
        tone: 'rose',
      }
    }

    if (status === 'WARNING') {
      return {
        value: 'WARNING',
        detail:
          health?.message ||
          (totalNodesCount > 0 && connectedCount < totalNodesCount
            ? `${totalNodesCount - connectedCount} de ${totalNodesCount} nodo(s) desconectado(s)`
            : devicesInError > 0
              ? `${devicesInError} dispositivo(s) con errores`
              : 'Operación degradada o atención requerida'),
        tone: 'amber',
      }
    }

    return {
      value: 'OK',
      detail: health?.message || 'Todos los servicios respondiendo',
      tone: 'lime',
    }
  }

  // 2. CONNECTED NODES CARD
  const getConnectedNodesState = (): {
    detail: string
    tone: 'lime' | 'cyan' | 'amber' | 'rose'
  } => {
    if (totalNodesCount === 0) {
      return {
        detail: 'Sin nodos en catálogo',
        tone: 'cyan',
      }
    }
    if (connectedCount === 0) {
      return {
        detail: 'Todos los nodos desconectados (OFFLINE)',
        tone: 'rose',
      }
    }
    if (connectedCount < totalNodesCount) {
      return {
        detail: `${totalNodesCount - connectedCount} de ${totalNodesCount} nodo(s) fuera de línea`,
        tone: 'amber',
      }
    }
    return {
      detail: 'Nodos activos en LAN/Firmata',
      tone: 'lime',
    }
  }

  // 3. ACTIVE DEVICES CARD
  const getDevicesState = (): {
    detail: string
    tone: 'lime' | 'cyan' | 'amber' | 'rose'
  } => {
    if (totalNodesCount > 0 && connectedCount === 0) {
      return {
        detail: 'Dispositivos inalcanzables (nodos OFFLINE)',
        tone: 'rose',
      }
    }
    if (devicesInError > 0) {
      return {
        detail: `${devicesInError} dispositivo(s) con fallos de hardware`,
        tone: 'amber',
      }
    }
    if (connectedCount < totalNodesCount) {
      return {
        detail: 'Dispositivos parcialmente alcanzables',
        tone: 'amber',
      }
    }
    return {
      detail: 'Catálogo de sensores/actuadores',
      tone: 'cyan',
    }
  }

  const healthState = getHealthCardState()
  const nodesState = getConnectedNodesState()
  const devicesState = getDevicesState()

  return (
    <section className="health-grid" aria-label="Métricas del sistema">
      <HealthCard
        icon={Server}
        title="SYSTEM HEALTH"
        value={healthState.value}
        detail={healthState.detail}
        tone={healthState.tone}
      />
      <HealthCard
        icon={Cpu}
        title="CONNECTED NODES"
        value={`${connectedCount} / ${totalNodesCount}`}
        detail={nodesState.detail}
        tone={nodesState.tone}
      />
      <HealthCard
        icon={Power}
        title="ACTIVE DEVICES"
        value={String(totalDevicesCount)}
        detail={devicesState.detail}
        tone={devicesState.tone}
      />
      <HealthCard
        icon={AlertTriangle}
        title="ATTENTION"
        value={String(overridesCount)}
        detail={
          overridesCount > 0
            ? 'Overrides manuales bloqueando AUTO'
            : 'Modo automático sin bloqueos'
        }
        tone={overridesCount > 0 ? 'amber' : 'lime'}
      />
    </section>
  )
}
