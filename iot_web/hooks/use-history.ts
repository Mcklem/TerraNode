'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  fetchActuatorsHistory,
  fetchEventsHistory,
  fetchMeasurementsHistory,
  fetchNodesHistory,
  fetchSchedulesHistory,
  type ActuatorHistoryRecord,
  type EventRecord,
  type MeasurementRecord,
  type NodeHistoryRecord,
  type ScheduleHistoryRecord,
} from '@/lib/terranode-api'

export type HistoryTab = 'measurements' | 'actuators' | 'nodes' | 'schedules' | 'events'

export function useHistory() {
  const [activeTab, setActiveTab] = useState<HistoryTab>('measurements')

  const [page, setPage] = useState(1)
  const [limit, setLimit] = useState(25)

  const [deviceIdFilter, setDeviceIdFilter] = useState('')
  const [nodeIdFilter, setNodeIdFilter] = useState('')
  const [scheduleIdFilter, setScheduleIdFilter] = useState('')
  const [sourceFilter, setSourceFilter] = useState('')
  const [topicFilter, setTopicFilter] = useState('')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Totales para los badges de las pestañas
  const [totals, setTotals] = useState({
    measurements: 0,
    actuators: 0,
    nodes: 0,
    schedules: 0,
    events: 0,
  })

  const [measurementsData, setMeasurementsData] = useState<{ total: number; records: MeasurementRecord[] }>({
    total: 0,
    records: [],
  })

  const [actuatorsData, setActuatorsData] = useState<{ total: number; records: ActuatorHistoryRecord[] }>({
    total: 0,
    records: [],
  })

  const [nodesData, setNodesData] = useState<{ total: number; records: NodeHistoryRecord[] }>({
    total: 0,
    records: [],
  })

  const [schedulesData, setSchedulesData] = useState<{ total: number; records: ScheduleHistoryRecord[] }>({
    total: 0,
    records: [],
  })

  const [eventsData, setEventsData] = useState<{ total: number; records: EventRecord[] }>({
    total: 0,
    records: [],
  })

  const activeAbortRef = useRef<AbortController | null>(null)

  // Carga inicial de totales de las 5 categorías para actualizar las pestañas
  const loadTotals = useCallback(async (signal?: AbortSignal) => {
    try {
      const [m, a, n, s, e] = await Promise.all([
        fetchMeasurementsHistory(undefined, 1, 0, signal),
        fetchActuatorsHistory(undefined, undefined, 1, 0, signal),
        fetchNodesHistory(undefined, 1, 0, signal),
        fetchSchedulesHistory(undefined, undefined, 1, 0, signal),
        fetchEventsHistory(undefined, 1, 0, signal),
      ])
      setTotals({
        measurements: m?.total ?? 0,
        actuators: a?.total ?? 0,
        nodes: n?.total ?? 0,
        schedules: s?.total ?? 0,
        events: e?.total ?? 0,
      })
    } catch {
      // Ignorar errores silenciosos en la precarga de contadores
    }
  }, [])

  const loadData = useCallback(async () => {
    if (activeAbortRef.current) {
      activeAbortRef.current.abort()
    }
    const controller = new AbortController()
    activeAbortRef.current = controller

    setLoading(true)
    setError('')

    const offset = (page - 1) * limit

    try {
      // Cargar totales generales en segundo plano
      loadTotals(controller.signal)

      if (activeTab === 'measurements') {
        const res = await fetchMeasurementsHistory(deviceIdFilter || undefined, limit, offset, controller.signal)
        const records = Array.isArray(res?.data) ? res.data : []
        const total = typeof res?.total === 'number' ? res.total : records.length
        setMeasurementsData({ total, records })
        setTotals((prev) => ({ ...prev, measurements: total }))
      } else if (activeTab === 'actuators') {
        const res = await fetchActuatorsHistory(
          deviceIdFilter || undefined,
          sourceFilter || undefined,
          limit,
          offset,
          controller.signal
        )
        const records = Array.isArray(res?.data) ? res.data : []
        const total = typeof res?.total === 'number' ? res.total : records.length
        setActuatorsData({ total, records })
        setTotals((prev) => ({ ...prev, actuators: total }))
      } else if (activeTab === 'nodes') {
        const res = await fetchNodesHistory(nodeIdFilter || undefined, limit, offset, controller.signal)
        const records = Array.isArray(res?.data) ? res.data : []
        const total = typeof res?.total === 'number' ? res.total : records.length
        setNodesData({ total, records })
        setTotals((prev) => ({ ...prev, nodes: total }))
      } else if (activeTab === 'schedules') {
        const res = await fetchSchedulesHistory(
          scheduleIdFilter || undefined,
          deviceIdFilter || undefined,
          limit,
          offset,
          controller.signal
        )
        const records = Array.isArray(res?.data) ? res.data : []
        const total = typeof res?.total === 'number' ? res.total : records.length
        setSchedulesData({ total, records })
        setTotals((prev) => ({ ...prev, schedules: total }))
      } else if (activeTab === 'events') {
        const res = await fetchEventsHistory(topicFilter || undefined, limit, offset, controller.signal)
        const records = Array.isArray(res?.data) ? res.data : []
        const total = typeof res?.total === 'number' ? res.total : records.length
        setEventsData({ total, records })
        setTotals((prev) => ({ ...prev, events: total }))
      }
    } catch (e: any) {
      if (e?.name !== 'AbortError') {
        setError(e instanceof Error ? e.message : 'No se pudieron cargar los registros de histórico')
      }
    } finally {
      setLoading(false)
    }
  }, [activeTab, page, limit, deviceIdFilter, nodeIdFilter, scheduleIdFilter, sourceFilter, topicFilter, loadTotals])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleTabChange = (tab: HistoryTab) => {
    setActiveTab(tab)
    setPage(1)
  }

  const handleLimitChange = (newLimit: number) => {
    setLimit(newLimit)
    setPage(1)
  }

  return {
    activeTab,
    setActiveTab: handleTabChange,
    page,
    setPage,
    limit,
    setLimit: handleLimitChange,
    deviceIdFilter,
    setDeviceIdFilter: (val: string) => { setDeviceIdFilter(val); setPage(1); },
    nodeIdFilter,
    setNodeIdFilter: (val: string) => { setNodeIdFilter(val); setPage(1); },
    scheduleIdFilter,
    setScheduleIdFilter: (val: string) => { setScheduleIdFilter(val); setPage(1); },
    sourceFilter,
    setSourceFilter: (val: string) => { setSourceFilter(val); setPage(1); },
    topicFilter,
    setTopicFilter: (val: string) => { setTopicFilter(val); setPage(1); },
    loading,
    error,
    totals,
    measurementsData,
    actuatorsData,
    nodesData,
    schedulesData,
    eventsData,
    refresh: loadData,
  }
}
