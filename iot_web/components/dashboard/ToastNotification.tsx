'use client'

import { Sparkles, X } from 'lucide-react'

interface ToastNotificationProps {
  message: string
  onClose: () => void
}

export function ToastNotification({ message, onClose }: ToastNotificationProps) {
  if (!message) return null

  return (
    <div className="toast" role="status" aria-live="polite">
      <Sparkles size={16} />
      <span>{message}</span>
      <button type="button" onClick={onClose} aria-label="Descartar notificación">
        <X size={14} />
      </button>
    </div>
  )
}
