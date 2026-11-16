'use client'

import { useState, useEffect } from 'react'
import { FirmwareHeader } from './FirmwareHeader'
import { CatalogGrid } from './CatalogGrid'
import { DynamicForm } from './DynamicForm'
import { BuildTerminal } from './BuildTerminal'
import { WebSerialFlasher } from './WebSerialFlasher'
import { BuildHistoryTable } from './BuildHistoryTable'
import {
  fetchFirmwareTemplates,
  generateFirmware,
  compileFirmware,
  fetchBuildStatus,
  type FirmwareManifest,
  type BuildRecord,
} from '@/lib/terranode-api'

export default function FirmwareStudio() {
  const [activeTab, setActiveTab] = useState<'catalog' | 'configure' | 'build' | 'history'>('catalog')
  const [isFlashingMode, setIsFlashingMode] = useState(false)
  const [templates, setTemplates] = useState<FirmwareManifest[]>([])
  const [loadingTemplates, setLoadingTemplates] = useState(true)
  const [selectedTemplate, setSelectedTemplate] = useState<FirmwareManifest | null>(null)
  const [currentBuild, setCurrentBuild] = useState<BuildRecord | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | undefined>()

  // Load templates on mount
  useEffect(() => {
    let ignore = false
    const load = async () => {
      try {
        setLoadingTemplates(true)
        const data = await fetchFirmwareTemplates()
        if (!ignore) {
          setTemplates(data || [])
          if (data && data.length > 0 && !selectedTemplate) {
            setSelectedTemplate(data[0])
          }
        }
      } catch (err: any) {
        if (!ignore) {
          setError(err.message || 'Error al conectar con el catálogo de firmware.')
        }
      } finally {
        if (!ignore) setLoadingTemplates(false)
      }
    }
    load()
    return () => {
      ignore = true
    }
  }, [])

  const handleSelectTemplate = (template: FirmwareManifest) => {
    setSelectedTemplate(template)
    setError(undefined)
    setActiveTab('configure')
  }

  const handleGenerate = async (params: Record<string, unknown>) => {
    if (!selectedTemplate) return
    try {
      setBusy(true)
      setError(undefined)
      const record = await generateFirmware(selectedTemplate.id, params)
      setCurrentBuild(record)
      setIsFlashingMode(false)
      setActiveTab('build')
    } catch (err: any) {
      setError(err.message || 'No se pudo generar el código configurado.')
    } finally {
      setBusy(false)
    }
  }

  const handleCompile = async (forceMock: boolean = false) => {
    if (!currentBuild) return
    try {
      setBusy(true)
      setError(undefined)
      const updated = await compileFirmware(currentBuild.id, forceMock)
      setCurrentBuild(updated)
    } catch (err: any) {
      setError(err.message || 'Error al ejecutar la compilación.')
      if (currentBuild) {
        // Refresh build status
        const refreshed = await fetchBuildStatus(currentBuild.id).catch(() => null)
        if (refreshed) setCurrentBuild(refreshed)
      }
    } finally {
      setBusy(false)
    }
  }

  const handleSelectFromHistory = (build: BuildRecord) => {
    setCurrentBuild(build)
    setIsFlashingMode(false)
    setActiveTab('build')
  }

  return (
    <main className="min-h-screen bg-background text-foreground font-sans pb-16">
      <FirmwareHeader
        activeTab={activeTab}
        onSelectTab={(tab) => {
          setActiveTab(tab)
          setIsFlashingMode(false)
        }}
        hasActiveBuild={Boolean(currentBuild)}
      />

      <div className="shell pt-8">
        {activeTab === 'catalog' && (
          <CatalogGrid
            templates={templates}
            loading={loadingTemplates}
            onSelectTemplate={handleSelectTemplate}
          />
        )}

        {activeTab === 'configure' && selectedTemplate && (
          <DynamicForm
            template={selectedTemplate}
            onBack={() => setActiveTab('catalog')}
            onGenerate={handleGenerate}
            busy={busy}
            error={error}
          />
        )}

        {activeTab === 'build' && currentBuild && (
          <>
            {isFlashingMode ? (
              <WebSerialFlasher
                build={currentBuild}
                onBackToBuild={() => setIsFlashingMode(false)}
              />
            ) : (
              <BuildTerminal
                build={currentBuild}
                onCompile={handleCompile}
                onSwitchToFlash={() => setIsFlashingMode(true)}
                busy={busy}
              />
            )}
          </>
        )}

        {activeTab === 'build' && !currentBuild && (
          <div className="max-w-md mx-auto text-center py-16 border border-dashed border-border rounded-xl space-y-4">
            <p className="text-sm text-muted-foreground font-mono">
              No hay ninguna compilación activa en este momento.
            </p>
            <button
              type="button"
              onClick={() => setActiveTab('catalog')}
              className="px-4 py-2 rounded-lg text-xs font-mono font-medium bg-primary text-primary-foreground hover:opacity-90"
            >
              Seleccionar plantilla del catálogo
            </button>
          </div>
        )}

        {activeTab === 'history' && (
          <BuildHistoryTable onSelectBuild={handleSelectFromHistory} />
        )}
      </div>
    </main>
  )
}
