'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  apiFetch,
  fetchDevices,
  fetchHealth,
  fetchNodes,
  fetchOverrides,
  fetchSchedules,
  toggleSchedule,
  triggerSchedule,
  type Device,
  type Health,
  type Mode,
  type Override,
  type ScheduleState,
  type TerraNode,
} from '@/lib/terranode-api'

export function useTerraNode(pollIntervalMs = 2000) {
  const [health, setHealth] = useState<Health | null>(null)
  const [nodes, setNodes] = useState<TerraNode[]>([])
  const [devices, setDevices] = useState<Device[]>([])
  const [overrides, setOverrides] = useState<Override[]>([])
  const [schedules, setSchedules] = useState<ScheduleState[]>([])

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
      const [h, n, d, o, s] = await Promise.all([
        fetchHealth(abortController.signal),
        fetchNodes(abortController.signal),
        fetchDevices(abortController.signal),
        fetchOverrides(abortController.signal),
        fetchSchedules(abortController.signal).catch(() => []),
      ])

      setHealth(h)
      setNodes(n)
      setDevices(d)
      setOverrides(o)
      setSchedules(Array.isArray(s) ? s : [])
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

    const computedTargetMode =
      targetMode ||
      (device.type === 'relay'
        ? action === 'turn_on'
          ? 'MANUAL_ON'
          : 'MANUAL_OFF'
        : 'MANUAL_VALUE')

    // 1. Instant Optimistic Local UI Update (0ms latency for button state)
    setDevices((prev) =>
      prev.map((d) => {
        if (d.id === device.id) {
          const nextState = { ...d.current_state }
          if (action === 'turn_on') nextState.state = 'ON'
          if (action === 'turn_off') nextState.state = 'OFF'
          if (action === 'set_position' && typeof params.angle === 'number') {
            nextState.angle = params.angle
          }
          return {
            ...d,
            control_mode: computedTargetMode as Mode,
            override_active: true,
            current_state: nextState,
          }
        }
        return d
      })
    )

    try {
      const res = await apiFetch<any>(`/devices/${encodeURIComponent(device.id)}/command`, undefined, {
        method: 'POST',
        body: JSON.stringify({
          action,
          params,
          target_mode: computedTargetMode,
          user_id: 'dashboard_web',
          ttl_seconds: ttlSeconds,
        }),
      })

      // 2. Authoritative update from server response payload
      if (res && res.state_payload) {
        setDevices((prev) =>
          prev.map((d) => {
            if (d.id === device.id) {
              return {
                ...d,
                control_mode: (res.current_mode || computedTargetMode) as Mode,
                override_active: true,
                current_state: res.state_payload,
              }
            }
            return d
          })
        )
      }

      notify(`Comando '${action}' aplicado a ${device.id}`)
      // 3. Trigger non-blocking background refresh to sync other components
      refresh()
    } catch (e: any) {
      notify(e instanceof Error ? e.message : 'Error al enviar el comando al dispositivo')
      // Rollback on error
      refresh()
    } finally {
      setBusyId('')
    }
  }

  const restoreDeviceControl = async (deviceId: string) => {
    setBusyId(deviceId)

    // Instant Optimistic UI Update
    setDevices((prev) =>
      prev.map((d) => {
        if (d.id === deviceId) {
          return {
            ...d,
            control_mode: 'AUTO' as Mode,
            override_active: false,
          }
        }
        return d
      })
    )

    try {
      const res = await apiFetch<any>(`/devices/${encodeURIComponent(deviceId)}/restore-control`, undefined, {
        method: 'POST',
      })

      if (res && res.state_payload) {
        setDevices((prev) =>
          prev.map((d) => {
            if (d.id === deviceId) {
              return {
                ...d,
                control_mode: 'AUTO' as Mode,
                override_active: false,
                current_state: res.state_payload,
              }
            }
            return d
          })
        )
      }

      notify(`Control automático (AUTO) restaurado para ${deviceId}`)
      refresh()
    } catch (e: any) {
      notify(e instanceof Error ? e.message : 'Error al restaurar el control')
      refresh()
    } finally {
      setBusyId('')
    }
  }

  const triggerScheduleAction = async (scheduleId: string) => {
    setBusyId(`sched-${scheduleId}`)
    try {
      const res = await triggerSchedule(scheduleId)
      notify(res.message || `Tarea programada '${scheduleId}' disparada manualmente`)
      refresh()
    } catch (e: any) {
      notify(e instanceof Error ? e.message : 'Error al disparar la tarea programada')
    } finally {
      setBusyId('')
    }
  }

  const toggleScheduleAction = async (scheduleId: string) => {
    setBusyId(`sched-${scheduleId}`)
    try {
      const res = await toggleSchedule(scheduleId)
      notify(res.message || `Estado de '${scheduleId}' actualizado`)
      refresh()
    } catch (e: any) {
      notify(e instanceof Error ? e.message : 'Error al alternar la tarea programada')
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
      refresh()
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
      refresh()
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
    schedules,
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
    triggerScheduleAction,
    toggleScheduleAction,
    executeRawPinCommand,
    restoreAllOverrides,
  }
}
