'use client'

import { useState } from 'react'
import { SlidersHorizontal, X } from 'lucide-react'
import type { TerraNode } from '@/lib/terranode-api'

interface PinModalProps {
  node: TerraNode
  isOpen: boolean
  onClose: () => void
  onExecute: (
    nodeId: string,
    commandType: 'digital_write' | 'analog_write',
    pin: string,
    value: number
  ) => Promise<void>
  busy: boolean
}

const AVAILABLE_PINS = ['D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'A0']

export function PinModal({ node, isOpen, onClose, onExecute, busy }: PinModalProps) {
  const [commandType, setCommandType] = useState<'digital_write' | 'analog_write'>('digital_write')
  const [pin, setPin] = useState('D5')
  const [digitalVal, setDigitalVal] = useState<number>(1)
  const [analogVal, setAnalogVal] = useState<number>(128)

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const value = commandType === 'digital_write' ? digitalVal : analogVal
    await onExecute(node.id, commandType, pin, value)
    onClose()
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="pin-modal-title">
      <div className="modal">
        <div className="modal-head">
          <div>
            <h3 id="pin-modal-title">Control de Pin Crudo</h3>
            <span>NODO: {node.id} ({node.host})</span>
          </div>
          <button type="button" onClick={onClose} aria-label="Cerrar modal">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <label>
            <span>TIPO DE COMANDO</span>
            <select
              value={commandType}
              onChange={(e) => setCommandType(e.target.value as 'digital_write' | 'analog_write')}
            >
              <option value="digital_write">Digital Write (HIGH / LOW)</option>
              <option value="analog_write">Analog Write (PWM 0-255)</option>
            </select>
          </label>

          <label>
            <span>PIN FÍSICO NODEMCU</span>
            <select value={pin} onChange={(e) => setPin(e.target.value)}>
              {AVAILABLE_PINS.map((p) => (
                <option key={p} value={p}>
                  Pin {p}
                </option>
              ))}
            </select>
          </label>

          {commandType === 'digital_write' ? (
            <label>
              <span>ESTADO DIGITAL</span>
              <select
                value={digitalVal}
                onChange={(e) => setDigitalVal(Number(e.target.value))}
              >
                <option value={1}>HIGH (1 - Voltaje 3.3V)</option>
                <option value={0}>LOW (0 - Voltaje 0V / GND)</option>
              </select>
              <span className="text-xs text-muted-foreground mt-1 block">
                Nota: En hardware Active-LOW (ej. LED interno NodeMCU o módulos de relé active-low), LOW (0V) enciende el circuito.
              </span>
            </label>
          ) : (
            <label>
              <span>CICLO ÚTIL PWM (0 - 255): <strong>{analogVal}</strong></span>
              <input
                type="range"
                min="0"
                max="255"
                value={analogVal}
                onChange={(e) => setAnalogVal(Number(e.target.value))}
              />
            </label>
          )}

          <button
            type="submit"
            className="send-button"
            disabled={busy || !node.connected}
          >
            <SlidersHorizontal size={14} />
            {busy ? 'Enviando...' : 'Enviar Orden al Microcontrolador'}
          </button>
        </form>
      </div>
    </div>
  )
}
