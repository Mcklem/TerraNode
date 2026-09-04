'use client'

import { useMemo, useState } from 'react'
import { isActuator, type Device, type Mode, type TerraNode } from '@/lib/terranode-api'
import { DeviceCard } from './DeviceCard'

export type FilterType = 'ALL' | 'ACTUATORS' | 'SENSORS'

interface DeviceGridProps {
  devices: Device[]
  nodes?: TerraNode[]
  busyId: string
  onCommand: (
    device: Device,
    action: string,
    params?: Record<string, any>,
    targetMode?: Mode,
    ttlSeconds?: number | null
  ) => void
  onRestore: (id: string) => void
}

export function DeviceGrid({ devices, nodes = [], busyId, onCommand, onRestore }: DeviceGridProps) {
  const [filter, setFilter] = useState<FilterType>('ALL')

  const visibleDevices = useMemo(() => {
    return devices.filter((d) => {
      if (filter === 'ALL') return true
      const actuator = isActuator(d)
      return filter === 'ACTUATORS' ? actuator : !actuator
    })
  }, [devices, filter])

  return (
    <section className="section-block" aria-label="Superficie de Control de Dispositivos">
      <div className="section-heading">
        <div>
          <p className="eyebrow">CONTROL SURFACE</p>
          <h3>
            Devices <span className="count-badge">{visibleDevices.length}</span>
          </h3>
        </div>

        <div className="filter-row">
          {(['ALL', 'ACTUATORS', 'SENSORS'] as FilterType[]).map((f) => (
            <button
              key={f}
              type="button"
              className={filter === f ? 'filter active' : 'filter'}
              onClick={() => setFilter(f)}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="device-grid">
        {visibleDevices.map((device) => {
          const matchingNode = nodes.find((n) => n.id === device.node_id)
          const nodeConnected = matchingNode ? matchingNode.connected && matchingNode.enabled : true
          return (
            <DeviceCard
              key={device.id}
              device={device}
              nodeConnected={nodeConnected}
              busy={busyId === device.id}
              onCommand={onCommand}
              onRestore={onRestore}
            />
          )
        })}
      </div>
    </section>
  )
}
