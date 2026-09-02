'use client'

import { Info, RotateCcw, Timer, Zap } from 'lucide-react'
import type { Override } from '@/lib/terranode-api'

interface OverrideListProps {
  overrides: Override[]
  onRestore: (deviceId: string) => void
  onRestoreAll: () => void
  busyId: string
}

export function OverrideList({ overrides, onRestore, onRestoreAll, busyId }: OverrideListProps) {
  return (
    <section className="section-block overrides" aria-label="Overrides Manuales Activos">
      <div className="section-heading">
        <div>
          <p className="eyebrow">MANUAL CONTROL</p>
          <h3>
            Active overrides{' '}
            <span className="count-badge amber">{overrides.length}</span>
          </h3>
        </div>

        <button
          type="button"
          className="danger-button"
          disabled={!overrides.length || busyId === 'global-restore'}
          onClick={onRestoreAll}
        >
          <RotateCcw size={14} /> Restore all to AUTO
        </button>
      </div>

      <div className="override-list">
        {overrides.map((o) => {
          const isExpiring = o.expires_at != null
          const expiryTimeStr = isExpiring
            ? new Date(o.expires_at! * 1000).toLocaleTimeString()
            : 'Sin expiración (Indefinido)'

          return (
            <div className="override-row" key={o.device_id}>
              <div className="override-device">
                <div className="mini-icon amber-bg" aria-hidden="true">
                  <Zap size={15} />
                </div>
                <div>
                  <b>{o.device_id}</b>
                  <span>ORIGEN: {o.override_source || 'dashboard_web'}</span>
                </div>
              </div>

              <div className="override-mode">
                <span className="mode manual">
                  {o.mode.replaceAll('_', ' ')}
                </span>
                <span className="source">
                  ACCIÓN: {o.last_action ? o.last_action.replaceAll('_', ' ') : 'manual'}
                </span>
              </div>

              <div className="expiry">
                <Timer size={14} />
                <span>
                  {isExpiring ? `Expira a las ${expiryTimeStr}` : expiryTimeStr}
                </span>
              </div>

              <button
                type="button"
                className="restore-button"
                disabled={busyId === o.device_id}
                onClick={() => onRestore(o.device_id)}
              >
                Restore
              </button>
            </div>
          )
        })}

        {!overrides.length && (
          <p className="empty-state">No hay overrides manuales activos en el sistema.</p>
        )}

        <div className="override-footer">
          <Info size={14} />
          Los comandos manuales bloquean la automatización (`RuleEngine`) hasta que expira el TTL o se restaura el control a `AUTO`.
        </div>
      </div>
    </section>
  )
}
