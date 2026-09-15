'use client'

import { useState } from 'react'
import { ArrowUpRight, Cpu, Lock, ShieldAlert, SlidersHorizontal } from 'lucide-react'
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

  const lastErr = node.last_error || ''
  const isAuthFailed = lastErr.includes('SECURITY_AUTH_FAILED')
  const isMissingKey = lastErr.includes('MISSING_AUTH_KEY')
  const isTlsError = lastErr.includes('TLS_ERROR')
  const isSecurityIssue = isAuthFailed || isMissingKey || isTlsError

  let securityMessage = ''
  if (isAuthFailed) {
    securityMessage = 'Clave única rechazada por el microcontrolador. Verifica "auth_key" en system.yaml.'
  } else if (isMissingKey) {
    securityMessage = 'Nodo seguro requiere definir el parámetro "auth_key" en system.yaml.'
  } else if (isTlsError) {
    securityMessage = 'No se pudo negociar el túnel cifrado TLS/SSL con el nodo.'
  }

  return (
    <div className={`node-card ${isDisconnected ? 'is-disconnected' : ''} ${isSecurityIssue ? 'border-amber-500/60 bg-[#1c140a]' : ''}`}>
      <div className="node-card-top">
        <div
          className={`node-icon ${
            isSecurityIssue
              ? 'text-amber-400 border-amber-500/50 bg-[#2b1c0c]'
              : isDisconnected
              ? 'text-destructive border-destructive/50 bg-[#241010]'
              : ''
          }`}
          aria-hidden="true"
        >
          {isSecurityIssue ? <Lock size={20} /> : <Cpu size={20} />}
        </div>
        <div>
          <b className={isSecurityIssue ? 'text-amber-400' : isDisconnected ? 'text-destructive' : ''}>{node.id}</b>
          <span className="node-id">
            {driverLabel} · {node.enabled ? 'ENABLED' : 'DISABLED'}
          </span>
        </div>
        <span
          className={`status-pill ${
            isSecurityIssue
              ? 'text-amber-400 border-amber-500/50 bg-amber-500/10 font-bold'
              : isDisconnected
              ? 'text-destructive border-destructive/40 bg-destructive/10 font-bold'
              : ''
          }`}
        >
          <i className={isSecurityIssue ? 'bg-amber-400 shadow-[0_0_8px_var(--amber-400,#f59e0b)]' : isDisconnected ? 'bg-destructive shadow-[0_0_8px_var(--destructive)]' : ''} />
          {isSecurityIssue ? 'AUTH ERROR' : node.status}
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
          <b className={isSecurityIssue ? 'text-amber-400 font-bold' : isDisconnected ? 'text-destructive font-bold' : ''}>
            {isSecurityIssue ? 'AUTH ERROR' : isDisconnected ? 'OFFLINE' : 'ONLINE'}
          </b>
        </div>
      </div>

      {isSecurityIssue && (
        <div className="mt-3 p-2.5 rounded border border-amber-500/40 bg-amber-500/10 text-amber-300 text-xs flex items-start gap-2">
          <ShieldAlert size={16} className="shrink-0 mt-0.5 text-amber-400" />
          <div>
            <strong className="block font-semibold text-amber-200">Fallo de Seguridad IoT:</strong>
            <span>{securityMessage}</span>
          </div>
        </div>
      )}

      <div className="loadbar" aria-hidden="true">
        <i
          className={isSecurityIssue ? 'bg-amber-400 shadow-[0_0_8px_var(--amber-400,#f59e0b)]' : isDisconnected ? 'bg-destructive shadow-[0_0_8px_var(--destructive)]' : ''}
          style={{ width: '100%' }}
        />
      </div>

      <button
        type="button"
        className="pin-button"
        disabled={isDisconnected || isSecurityIssue}
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
