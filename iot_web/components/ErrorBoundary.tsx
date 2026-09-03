'use client'

import React, { Component, ReactNode } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

interface Props {
  children: ReactNode
  fallbackTitle?: string
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('[TerraNode ErrorBoundary] Uncaught UI error:', error, errorInfo)
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="bg-[#190d0b] border border-[#61241a] rounded-lg p-6 text-center my-4 font-mono text-[12px]">
          <AlertTriangle size={28} className="mx-auto mb-2 text-[#ff806b]" />
          <h4 className="text-[#ff806b] font-bold mb-1">
            {this.props.fallbackTitle || 'Error al renderizar el componente'}
          </h4>
          <p className="text-[var(--muted-foreground)] mb-4 text-[11px]">
            {this.state.error?.message || 'Ocurrió un error inesperado en la interfaz.'}
          </p>
          <button
            type="button"
            className="quiet-button mx-auto border-[#ff806b]/40 text-[#ff806b] hover:bg-[#ff806b]/10"
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            <RefreshCw size={13} /> Reintentar Carga
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
