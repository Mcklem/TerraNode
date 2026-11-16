import FirmwareStudio from '@/components/firmware-studio/FirmwareStudio'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'TerraNode | Firmware Studio',
  description: 'Instalación, configuración y compilación de firmware Arduino para nodos IoT de TerraNode.',
}

export default function FirmwareStudioPage() {
  return <FirmwareStudio />
}
