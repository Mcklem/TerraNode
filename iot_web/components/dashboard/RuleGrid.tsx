'use client'

import { RefreshCw, Zap } from 'lucide-react'
import type { RuleState } from '@/lib/schemas'
import { RuleCard } from './RuleCard'

interface RuleGridProps {
  rules: RuleState[]
  busyId: string
  onToggle: (ruleId: string) => void
  onRefresh?: () => void
}

export function RuleGrid({
  rules,
  busyId,
  onToggle,
  onRefresh,
}: RuleGridProps) {
  return (
    <section className="section-block mt-10" aria-label="Reglas de Automatización por Sensores">
      <div className="section-heading">
        <div>
          <p className="eyebrow">AUTOMATION ENGINE / SENSOR RULES</p>
          <h3>
            Sensor Automation Rules <span className="count-badge">{rules.length}</span>
          </h3>
        </div>

        {onRefresh && (
          <button
            type="button"
            className="quiet-button"
            onClick={onRefresh}
          >
            <RefreshCw size={14} />
            Actualizar Reglas
          </button>
        )}
      </div>

      {rules.length === 0 ? (
        <div className="bg-[var(--card)] border border-[var(--border)] rounded p-8 text-center text-[var(--muted-foreground)] font-mono text-[12px]">
          <Zap size={24} className="mx-auto mb-2 opacity-50 text-amber-400" />
          No hay reglas de automatización por sensores configuradas en la API (`/api/v1/rules`).
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {rules.map((rule) => (
            <RuleCard
              key={rule.id}
              rule={rule}
              busyId={busyId}
              onToggle={onToggle}
            />
          ))}
        </div>
      )}
    </section>
  )
}
