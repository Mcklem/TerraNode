'use client'

import {
  Activity,
  ChevronLeft,
  ChevronRight,
  Cpu,
  Power,
  RefreshCw,
  Zap,
} from 'lucide-react'
import { useHistory } from '@/hooks/use-history'
import { ActuatorsTable } from './ActuatorsTable'
import { EventsHistoryTable } from './EventsHistoryTable'
import { MeasurementsTable } from './MeasurementsTable'
import { NodesHistoryTable } from './NodesHistoryTable'

export function HistorySection() {
  const {
    activeTab,
    setActiveTab,
    page,
    setPage,
    limit,
    setLimit,
    deviceIdFilter,
    setDeviceIdFilter,
    nodeIdFilter,
    setNodeIdFilter,
    sourceFilter,
    setSourceFilter,
    topicFilter,
    setTopicFilter,
    loading,
    error,
    totals,
    measurementsData,
    actuatorsData,
    nodesData,
    eventsData,
    refresh,
  } = useHistory()

  const currentTotal =
    activeTab === 'measurements'
      ? measurementsData.total
      : activeTab === 'actuators'
      ? actuatorsData.total
      : activeTab === 'nodes'
      ? nodesData.total
      : eventsData.total

  const totalPages = Math.max(1, Math.ceil(currentTotal / limit))

  return (
    <section className="section-block history-section" aria-label="Histórico y Auditoría">
      <div className="section-heading">
        <div>
          <p className="eyebrow">PERSISTENT STORAGE / LOGS</p>
          <h3>
            Historical Audit Logs <span className="count-badge">{currentTotal}</span>
          </h3>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            className="quiet-button"
            onClick={() => refresh()}
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refrescar Histórico
          </button>
        </div>
      </div>

      <div className="history-container bg-[var(--card)] border border-[var(--border)] rounded overflow-hidden">
        {/* Navigation Tabs */}
        <div className="history-tabs flex flex-wrap border-b border-[var(--border)] bg-[#071318]">
          <button
            type="button"
            className={`tab-item ${activeTab === 'measurements' ? 'active' : ''}`}
            onClick={() => setActiveTab('measurements')}
          >
            <Activity size={15} /> Sensores ({totals.measurements})
          </button>

          <button
            type="button"
            className={`tab-item ${activeTab === 'actuators' ? 'active' : ''}`}
            onClick={() => setActiveTab('actuators')}
          >
            <Power size={15} /> Actuadores ({totals.actuators})
          </button>

          <button
            type="button"
            className={`tab-item ${activeTab === 'nodes' ? 'active' : ''}`}
            onClick={() => setActiveTab('nodes')}
          >
            <Cpu size={15} /> Nodos Hardware ({totals.nodes})
          </button>

          <button
            type="button"
            className={`tab-item ${activeTab === 'events' ? 'active' : ''}`}
            onClick={() => setActiveTab('events')}
          >
            <Zap size={15} /> Bus de Eventos ({totals.events})
          </button>
        </div>

        {error && (
          <div className="p-4 bg-destructive/10 text-destructive text-[12px] border-b border-[var(--border)] font-mono">
            ⚠️ {error}
          </div>
        )}

        {/* Tab Content Tables */}
        <div className="history-content">
          {activeTab === 'measurements' && (
            <MeasurementsTable
              records={measurementsData.records}
              deviceIdFilter={deviceIdFilter}
              onDeviceIdChange={setDeviceIdFilter}
              loading={loading}
            />
          )}

          {activeTab === 'actuators' && (
            <ActuatorsTable
              records={actuatorsData.records}
              deviceIdFilter={deviceIdFilter}
              sourceFilter={sourceFilter}
              onDeviceIdChange={setDeviceIdFilter}
              onSourceChange={setSourceFilter}
              loading={loading}
            />
          )}

          {activeTab === 'nodes' && (
            <NodesHistoryTable
              records={nodesData.records}
              nodeIdFilter={nodeIdFilter}
              onNodeIdChange={setNodeIdFilter}
              loading={loading}
            />
          )}

          {activeTab === 'events' && (
            <EventsHistoryTable
              records={eventsData.records}
              topicFilter={topicFilter}
              onTopicChange={setTopicFilter}
              loading={loading}
            />
          )}
        </div>

        {/* Footer Pagination Controls */}
        <div className="pagination-bar flex flex-wrap items-center justify-between gap-4 p-3 bg-[#081318] border-t border-[var(--border)] text-[11px] font-mono">
          <div className="flex items-center gap-3">
            <span>REGISTROS POR PÁGINA:</span>
            <select
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="bg-[#050e12] border border-[var(--border)] rounded px-2 py-1 text-[11px] text-[var(--foreground)]"
            >
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>

          <div className="flex items-center gap-3">
            <span>
              PÁGINA <strong>{page}</strong> DE <strong>{totalPages}</strong> ({currentTotal} TOTALES)
            </span>

            <div className="flex gap-1">
              <button
                type="button"
                className="quiet-button px-2 py-1"
                disabled={page <= 1 || loading}
                onClick={() => setPage(page - 1)}
                title="Página Anterior"
              >
                <ChevronLeft size={14} />
              </button>

              <button
                type="button"
                className="quiet-button px-2 py-1"
                disabled={page >= totalPages || loading}
                onClick={() => setPage(page + 1)}
                title="Página Siguiente"
              >
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
