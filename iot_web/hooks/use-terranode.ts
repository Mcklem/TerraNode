'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  apiFetch,
  fetchDevices,
  fetchHealth,
  fetchNodes,
  fetchOverrides,
  type Device,
  type Health,
  type Mode,
  type Override,
  type TerraNode,
} from '@/lib/terranode-api'

export function useTerraNode(pollIntervalMs = 4000) {
  const [health, setHealth] = useState<Health | null>(null)
  const [nodes, setNodes] = useState<TerraNode[]>([])
  const [devices, setDevices] = useState<Device[]>([])
  const [overrides, setOverrides] = useState<Override[]>([])

  const [loading, setLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [error, setError] = useState('')
  const [toast, setToast] = useState('')
  const [busyId, setBusyId] = useState('')

  const activeAbortController = useRef<AbortController | null>(null)

  const notify = useCallback((message: string) => {
    setToast(message)
    const timer = setTimeout(() => setToast(''), 3200)
    return () => clearTimeout(timer)
  }, [])

  const refresh = useCallback(async (isManual = false) => {
    if (isManual) setIsRefreshing(true)

    if (activeAbortController.current) {
      activeAbortController.current.abort()
    }

    const abortController = new AbortController()
    activeAbortController.current = abortController

    try {
      const [h, n, d, o] = await Promise.all([
        fetchHealth(abortController.signal),
        fetchNodes(abortController.signal),
        fetchDevices(abortController.signal),
        fetchOverrides(abortController.signal),
      ])

      setHealth(h)
      setNodes(n)
      setDevices(d)
      setOverrides(o)
      setError('')
    } catch (e: any) {
      if (e?.name !== 'AbortError') {
        setError(e instanceof Error ? e.message : 'No se pudo comunicar con el controlador TerraNode')
      }
    } finally {
      setLoading(false)
      if (isManual) setIsRefreshing(false)
    }
  }, [])

  // Auto-polling con pausa en pérdida de foco (tab hidden)
  useEffect(() => {
    refresh()

    let intervalId: number | null = null

    const startPolling = () => {
      if (!intervalId) {
        intervalId = window.setInterval(() => {
          if (document.visibilityState === 'visible') {
            refresh()
          }
        }, pollIntervalMs)
      }
    }

    const stopPolling = () => {
      if (intervalId) {
        window.clearInterval(intervalId)
        intervalId = null
      }
    }

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        refresh()
        startPolling()
      } else {
        stopPolling()
      }
    }

    startPolling()
    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      stopPolling()
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      if (activeAbortController.current) {
        activeAbortController.current.abort()
      }
    }
  }, [refresh, pollIntervalMs])

  const executeDeviceCommand = async (
    device: Device,
    action: string,
    params: Record<string, any> = {},
    targetMode?: Mode,
    ttlSeconds: number | null = 300
  ) => {
    setBusyId(device.id)
    try {
      const computedTargetMode =
        targetMode ||
        (device.type === 'relay'
          ? action === 'turn_on'
            ? 'MANUAL_ON'
            : 'MANUAL_OFF'
          : 'MANUAL_VALUE')

      await apiFetch(`/devices/${encodeURIComponent(device.id)}/command`, undefined, {
        method: 'POST',
        body: JSON.stringify({
          action,
          params,
          target_mode: computedTargetMode,
          user_id: 'dashboard_web',
          ttl_seconds: ttlSeconds,
        }),
      })

      notify(`Comando '${action}' aplicado a ${device.id}`)
      await refresh()
    } catch (e: any) {
      notify(e instanceof Error ? e.message : 'Error al enviar el comando al dispositivo')
    } finally {
      setBusyId('')
    }
  }

  const restoreDeviceControl = async (deviceId: string) => {
    setBusyId(deviceId)
    try {
      await apiFetch(`/devices/${encodeURIComponent(deviceId)}/restore-control`, undefined, {
        method: 'POST',
      })
      notify(`Control automático (AUTO) restaurado para ${deviceId}`)
      await refresh()
    } catch (e: any) {
      notify(e instanceof Error ? e.message : 'Error al restaurar el control')
    } finally {
      setBusyId('')
    }
  }

  const executeRawPinCommand = async (
    nodeId: string,
    commandType: 'digital_write' | 'analog_write',
    pin: string,
    value: number
  ) => {
    setBusyId(`node-${nodeId}`)
    try {
      await apiFetch(`/nodes/${encodeURIComponent(nodeId)}/pin`, undefined, {
        method: 'POST',
        body: JSON.stringify({ command_type: commandType, pin, value }),
      })
      notify(`Comando de Pin (${pin} = ${value}) enviado a nodo ${nodeId}`)
      await refresh()
    } catch (e: any) {
      notify(e instanceof Error ? e.message : 'Fallo en la ejecución de pin crudo')
    } finally {
      setBusyId('')
    }
  }

  const restoreAllOverrides = async () => {
    if (!overrides.length) return
    setBusyId('global-restore')
    try {
      await Promise.all(overrides.map((o) => restoreDeviceControl(o.device_id)))
      notify('Todos los dispositivos fueron restaurados al modo AUTO')
      await refresh()
    } catch (e: any) {
      notify(e instanceof Error ? e.message : 'Error al restaurar overrides')
    } finally {
      setBusyId('')
    }
  }

  return {
    health,
    nodes,
    devices,
    overrides,
    loading,
    isRefreshing,
    error,
    toast,
    busyId,
    notify,
    setToast,
    refresh: () => refresh(true),
    executeDeviceCommand,
    restoreDeviceControl,
    executeRawPinCommand,
    restoreAllOverrides,
  }
}
