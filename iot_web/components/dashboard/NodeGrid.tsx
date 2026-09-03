'use client'

import { useState } from 'react'
import { ArrowUpRight, Cpu, SlidersHorizontal } from 'lucide-react'
import type { TerraNode } from '@/lib/terranode-api'
import { formatDriverName } from '@/lib/constants'
import { PinModal } from './PinModal'

interface NodeCardProps {
  node: TerraNode
  onOpenPinModal: (node: TerraNode) => void
}

function NodeCard({ node, onOpenPinModal }: NodeCardProps) {
  const driverLabel = formatDriverName(node.driver)
  const isDisconnected = !node.connected || node.status === 'DISCONNECTED'

  return (
    <div className={`node-card ${isDisconnected ? 'is-disconnected' : ''}`}>
      <div className="node-card-top">
        <div
          className={`node-icon ${
            isDisconnected
              ? 'text-destructive border-destructive/50 bg-[#241010]'
              : ''
          }`}
          aria-hidden="true"
        >
          <Cpu size={20} />
        </div>
        <div>
          <b className={isDisconnected ? 'text-destructive' : ''}>{node.id}</b>
          <span className="node-id">
            {driverLabel} · {node.enabled ? 'ENABLED' : 'DISABLED'}
          </span>
        </div>
        <span
          className={`status-pill ${
            isDisconnected ? 'text-destructive border-destructive/40 bg-destructive/10 font-bold' : ''
          }`}
        >
          <i className={isDisconnected ? 'bg-destructive shadow-[0_0_8px_var(--destructive)]' : ''} />
          {node.status}
        </span>
      </div>

      <div className="node-details">
        <div>
          <span>HOST / IP</span>
          <b>
            {node.host}:{node.port}
          </b>
        </div>
        <div>
          <span>DRIVER</span>
          <b>{driverLabel}</b>
        </div>
        <div>
          <span>ESTADO</span>
          <b className={isDisconnected ? 'text-destructive font-bold' : ''}>
            {isDisconnected ? 'OFFLINE' : 'ONLINE'}
          </b>
        </div>
      </div>

      <div className="loadbar" aria-hidden="true">
        <i
          className={isDisconnected ? 'bg-destructive shadow-[0_0_8px_var(--destructive)]' : ''}
          style={{ width: isDisconnected ? '100%' : '100%' }}
        />
      </div>

      <button
        type="button"
        className="pin-button"
        disabled={isDisconnected}
        onClick={() => onOpenPinModal(node)}
      >
        <SlidersHorizontal size={14} /> Pin directo <ArrowUpRight size={13} />
      </button>
    </div>
  )
}

interface NodeGridProps {
  nodes: TerraNode[]
  onRefresh: () => void
  onExecuteRawPin: (
    nodeId: string,
    commandType: 'digital_write' | 'analog_write',
    pin: string,
    value: number
  ) => Promise<void>
  busyId: string
}

export function NodeGrid({ nodes, onRefresh, onExecuteRawPin, busyId }: NodeGridProps) {
  const [selectedNode, setSelectedNode] = useState<TerraNode | null>(null)

  return (
    <section className="section-block" aria-label="Nodos Hardware">
      <div className="section-heading">
        <div>
          <p className="eyebrow">INFRASTRUCTURE</p>
          <h3>Hardware nodes</h3>
        </div>
        <button type="button" className="quiet-button" onClick={onRefresh}>
          Refresh diagnostics <ArrowUpRight size={14} />
        </button>
      </div>

      <div className="node-grid">
        {nodes.map((node) => (
          <NodeCard
            key={node.id}
            node={node}
            onOpenPinModal={(n) => setSelectedNode(n)}
          />
        ))}
      </div>

      {selectedNode && (
        <PinModal
          node={selectedNode}
          isOpen={!!selectedNode}
          onClose={() => setSelectedNode(null)}
          onExecute={onExecuteRawPin}
          busy={busyId === `node-${selectedNode.id}`}
        />
      )}
    </section>
  )
}
