'use client'

import { Activity, Cpu, Pause, Power, Zap } from 'lucide-react'
import type { RuleState } from '@/lib/schemas'

interface RuleCardProps {
  rule: RuleState
  busyId: string
  onToggle: (ruleId: string) => void
}

export function RuleCard({ rule, busyId, onToggle }: RuleCardProps) {
  const isBusy = busyId === `rule-${rule.id}`

  const formatValue = (val: unknown) => {
    if (val == null) return 'Sin lectura'
    if (typeof val === 'number') return val.toFixed(1)
    return String(val)
  }

  return (
    <article
      className={`device-card bg-[var(--card)] border rounded p-4 relative flex flex-col justify-between space-y-3 transition-all ${
        rule.is_triggered
          ? 'border-amber-500/70 shadow-[0_0_15px_rgba(245,158,11,0.25)] bg-[#120e08]/90'
          : 'border-[var(--border)] hover:border-[var(--accent)]/40'
      }`}
    >
      <div className="space-y-3">
        {/* Card Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap size={18} className="text-amber-400 shrink-0" />
            <h4
              className="font-mono font-bold text-[14px] text-[var(--foreground)] truncate max-w-[180px]"
              title={rule.id}
            >
              {rule.id}
            </h4>
          </div>

          <span
            className={`status-pill font-mono font-bold shrink-0 ${
              rule.is_triggered
                ? 'text-amber-400 border-amber-500/50 bg-amber-950/40'
                : rule.enabled
                ? 'text-emerald-400 border-emerald-500/50 bg-emerald-950/40'
                : 'text-destructive border-red-500/50 bg-red-950/40'
            }`}
          >
            <i
              className={
                rule.is_triggered
                  ? 'bg-amber-400 animate-ping'
                  : rule.enabled
                  ? 'bg-emerald-400'
                  : 'bg-destructive shadow-none'
              }
            />
            {rule.is_triggered
              ? 'DISPARADA (MATCH)'
              : rule.enabled
              ? 'ACTIVA'
              : 'PAUSADA'}
          </span>
        </div>

        {/* Sensor Condition Box */}
        <div className="text-[11px] font-mono text-[var(--muted-foreground)] bg-[#050e12] p-2.5 rounded border border-[var(--border)] space-y-1.5">
          <div className="flex items-center justify-between text-[var(--accent)] font-semibold pb-1 border-b border-[var(--border)]/60">
            <span className="flex items-center gap-1.5">
              <Activity size={12} /> SENSOR Y CONDICIÓN:
            </span>
            <span className="text-[10px] text-[var(--foreground)] bg-[#091d24] px-1.5 py-0.5 rounded border border-[var(--border)] font-bold">
              {rule.condition.device}.{rule.condition.property}
            </span>
          </div>

          <div className="flex justify-between items-center pt-0.5">
            <span>REGLA UMBRAL:</span>
            <strong className="text-[var(--primary)] font-mono font-bold">
              {rule.condition.property} {rule.condition.operator} {String(rule.condition.value)}
            </strong>
          </div>

          <div className="flex justify-between items-center pt-1 border-t border-[var(--border)]/40">
            <span>LECTURA EN TIEMPO REAL:</span>
            <strong
              className={`font-mono font-bold ${
                rule.is_triggered ? 'text-amber-400 animate-pulse' : 'text-[var(--foreground)]'
              }`}
            >
              {formatValue(rule.last_sensor_value)}
            </strong>
          </div>
        </div>

        {/* Associated Actions Box */}
        <div className="text-[11px] font-mono text-[var(--muted-foreground)] bg-[#07151a] p-2.5 rounded border border-[var(--border)] space-y-1.5">
          <div className="flex items-center gap-1.5 text-emerald-400 font-semibold pb-1 border-b border-[var(--border)]/60">
            <Cpu size={12} /> ACCIONES DISPARADAS:
          </div>

          {rule.actions.length === 0 ? (
            <p className="text-[10px] text-[var(--muted-foreground)]">Sin acciones asociadas</p>
          ) : (
            <div className="space-y-1 pt-0.5">
              {rule.actions.map((act, idx) => (
                <div key={idx} className="flex justify-between items-center text-[10px]">
                  <span className="text-[var(--foreground)] font-semibold">{act.device}</span>
                  <span className="text-emerald-400 font-mono font-bold">
                    {act.command} {act.args && Object.keys(act.args).length > 0 ? JSON.stringify(act.args) : ''}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Action Button */}
      <div className="pt-2">
        <button
          type="button"
          className={`w-full h-9 flex items-center justify-center gap-1.5 text-[11px] font-mono font-bold px-2 whitespace-nowrap rounded transition-all shadow-md ${
            rule.enabled
              ? 'bg-amber-500/20 border border-amber-500/80 text-amber-400 hover:bg-amber-500/35 hover:border-amber-400 shadow-[0_0_12px_rgba(245,158,11,0.2)]'
              : 'bg-emerald-500/20 border border-emerald-500 text-emerald-400 hover:bg-emerald-500/35 hover:border-emerald-400 shadow-[0_0_14px_rgba(16,185,129,0.3)]'
          }`}
          disabled={isBusy}
          onClick={() => onToggle(rule.id)}
          title={rule.enabled ? 'Pausar esta regla de automatización' : 'Activar esta regla de automatización'}
        >
          {rule.enabled ? (
            <>
              <Pause size={13} className="text-amber-400 fill-amber-400/40 shrink-0" />
              <span>Pausar Regla</span>
            </>
          ) : (
            <>
              <Power size={13} className="text-emerald-400 shrink-0" />
              <span>Activar Regla</span>
            </>
          )}
        </button>
      </div>
    </article>
  )
}
