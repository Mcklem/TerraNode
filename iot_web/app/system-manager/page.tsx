import { SystemManager } from '@/components/system-manager/SystemManager'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'TerraNode | System Configuration Manager',
  description: 'Administración, edición visual y YAML, validación y respaldo de la configuración de TerraNode.',
}

export default function SystemManagerPage() {
  return <SystemManager />
}
