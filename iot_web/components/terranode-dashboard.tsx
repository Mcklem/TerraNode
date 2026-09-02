'use client'

import { Activity } from 'lucide-react'
import { useTerraNode } from '@/hooks/use-terranode'
import { DeviceGrid } from './dashboard/DeviceGrid'
import { Header } from './dashboard/Header'
import { HealthGrid } from './dashboard/HealthGrid'
import { NodeGrid } from './dashboard/NodeGrid'
import { OverrideList } from './dashboard/OverrideList'
import { ToastNotification } from './dashboard/ToastNotification'

export default function TerraNodeDashboard() {
  const {
    health,
    nodes,
    devices,
    overrides,
    loading,
    isRefreshing,
    error,
    toast,
    busyId,
    setToast,
    refresh,
    executeDeviceCommand,
    restoreDeviceControl,
    executeRawPinCommand,
    restoreAllOverrides,
  } = useTerraNode(4000)

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

        <HealthGrid
          health={health}
          nodes={nodes}
          devicesCount={devices.length}
          overridesCount={overrides.length}
          loading={loading}
          error={error}
        />

        <NodeGrid
          nodes={nodes}
          onRefresh={refresh}
          onExecuteRawPin={executeRawPinCommand}
          busyId={busyId}
        />

        <DeviceGrid
          devices={devices}
          busyId={busyId}
          onCommand={executeDeviceCommand}
          onRestore={restoreDeviceControl}
        />

        <OverrideList
          overrides={overrides}
          onRestore={restoreDeviceControl}
          onRestoreAll={restoreAllOverrides}
          busyId={busyId}
        />
      </div>

      <ToastNotification message={toast} onClose={() => setToast('')} />
    </main>
  )
}
