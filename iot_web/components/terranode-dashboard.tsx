'use client'

import { Activity } from 'lucide-react'
import { useTerraNode } from '@/hooks/use-terranode'
import { ErrorBoundary } from './ErrorBoundary'
import { DeviceGrid } from './dashboard/DeviceGrid'
import { Header } from './dashboard/Header'
import { HealthGrid } from './dashboard/HealthGrid'
import { NodeGrid } from './dashboard/NodeGrid'
import { OverrideList } from './dashboard/OverrideList'
import { ScheduleGrid } from './dashboard/ScheduleGrid'
import { RuleGrid } from './dashboard/RuleGrid'
import { HistorySection } from './dashboard/history/HistorySection'
import { ToastNotification } from './dashboard/ToastNotification'

export default function TerraNodeDashboard() {
  const {
    health,
    nodes,
    devices,
    overrides,
    schedules,
    rules,
    loading,
    isRefreshing,
    error,
    toast,
    busyId,
    setToast,
    refresh,
    executeDeviceCommand,
    restoreDeviceControl,
    triggerScheduleAction,
    toggleScheduleAction,
    toggleRuleAction,
    executeRawPinCommand,
    restoreAllOverrides,
  } = useTerraNode(2000)

  return (
    <main className="min-h-screen bg-background text-foreground font-sans">
      <Header
        health={health}
        nodes={nodes}
        devicesCount={devices.length}
        overridesCount={overrides.length}
        hasError={!!error}
        isRefreshing={isRefreshing}
        onRefresh={refresh}
      />

      <div className="shell">
        <section className="hero-row">
          <div>
            <p className="eyebrow">
              SYSTEM OVERVIEW <span className="live-dot">•</span> LIVE TELEMETRY
            </p>
            <h2>Good morning, operator.</h2>
            <p className="muted">
              {error || 'Your greenhouse network is healthy and responding normally.'}
            </p>
          </div>

          <div className="last-sync">
            <span>LAST SYNC</span>
            <b>{loading ? 'Connecting…' : isRefreshing ? 'Updating…' : 'Just now'}</b>
            <Activity size={15} className={isRefreshing ? 'animate-pulse' : ''} />
          </div>
        </section>

        <ErrorBoundary fallbackTitle="Error en Métricas del Sistema">
          <HealthGrid
            health={health}
            nodes={nodes}
            devicesCount={devices.length}
            overridesCount={overrides.length}
            loading={loading}
            error={error}
          />
        </ErrorBoundary>

        <ErrorBoundary fallbackTitle="Error en Nodos Hardware">
          <NodeGrid
            nodes={nodes}
            onRefresh={refresh}
            onExecuteRawPin={executeRawPinCommand}
            busyId={busyId}
          />
        </ErrorBoundary>

        <ErrorBoundary fallbackTitle="Error en Dispositivos y Actuadores">
          <DeviceGrid
            devices={devices}
            nodes={nodes}
            busyId={busyId}
            onCommand={executeDeviceCommand}
            onRestore={restoreDeviceControl}
          />
        </ErrorBoundary>

        <ErrorBoundary fallbackTitle="Error en Tareas Programadas">
          <ScheduleGrid
            schedules={schedules}
            busyId={busyId}
            onTrigger={triggerScheduleAction}
            onToggle={toggleScheduleAction}
            onRefresh={refresh}
          />
        </ErrorBoundary>

        <ErrorBoundary fallbackTitle="Error en Reglas de Automatización">
          <RuleGrid
            rules={rules}
            busyId={busyId}
            onToggle={toggleRuleAction}
            onRefresh={refresh}
          />
        </ErrorBoundary>

        <ErrorBoundary fallbackTitle="Error en Lista de Overrides">
          <OverrideList
            overrides={overrides}
            onRestore={restoreDeviceControl}
            onRestoreAll={restoreAllOverrides}
            busyId={busyId}
          />
        </ErrorBoundary>

        <ErrorBoundary fallbackTitle="Error en Sección de Historial">
          <HistorySection />
        </ErrorBoundary>
      </div>

      <ToastNotification message={toast} onClose={() => setToast('')} />
    </main>
  )
}
