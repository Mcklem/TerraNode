import { NextRequest, NextResponse } from 'next/server'

const baseUrl = process.env.TERRANODE_API_URL || 'http://localhost:8000'
const allowedMethods = new Set(['GET', 'POST', 'DELETE', 'PUT', 'PATCH', 'OPTIONS'])

export async function GET(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return forward(request, (await params).path)
}

export async function POST(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return forward(request, (await params).path)
}

export async function DELETE(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return forward(request, (await params).path)
}

export async function PUT(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return forward(request, (await params).path)
}

export async function PATCH(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return forward(request, (await params).path)
}

export async function OPTIONS() {
  return new NextResponse(null, { status: 204 })
}

async function forward(request: NextRequest, pathParts: string[]) {
  if (!allowedMethods.has(request.method) || pathParts.some((part) => part.includes('..'))) {
    return NextResponse.json({ detail: 'Ruta no permitida o método no soportado' }, { status: 400 })
  }

  const pathStr = pathParts.map(encodeURIComponent).join('/')
  const targetUrl = new URL(`/api/v1/${pathStr}`, baseUrl)

  // Preservar parámetros de búsqueda de la URL original
  request.nextUrl.searchParams.forEach((value, key) => {
    targetUrl.searchParams.append(key, value)
  })

  const body = request.method === 'POST' ? await request.text() : undefined

  // Mayor tiempo de espera para operaciones de compilación de firmware
  const isFirmwareBuild = pathParts.includes('firmware') && pathParts.includes('compile')
  const timeoutMs = isFirmwareBuild ? 120000 : 15000

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const response = await fetch(targetUrl.toString(), {
      method: request.method,
      headers: {
        Accept: '*/*',
        ...(body ? { 'Content-Type': 'application/json' } : {}),
      },
      body,
      cache: 'no-store',
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    const contentType = response.headers.get('content-type') || ''

    // Si es un archivo binario o zip descargable, pasar el stream con sus cabeceras
    if (
      contentType.includes('application/octet-stream') ||
      contentType.includes('application/zip') ||
      contentType.includes('application/x-zip')
    ) {
      const headers = new Headers()
      headers.set('Content-Type', contentType)
      const disposition = response.headers.get('content-disposition')
      if (disposition) headers.set('Content-Disposition', disposition)
      const len = response.headers.get('content-length')
      if (len) headers.set('Content-Length', len)

      return new NextResponse(response.body, {
        status: response.status,
        headers,
      })
    }

    const data = await response.json().catch(() => ({ detail: 'Respuesta con formato no válido del controlador' }))
    return NextResponse.json(data, { status: response.status })
  } catch (error: any) {
    clearTimeout(timeoutId)
    const isTimeout = error?.name === 'AbortError'
    return NextResponse.json(
      {
        detail: isTimeout
          ? `Tiempo de espera agotado al conectar con TerraNode API en ${baseUrl}`
          : `No se pudo conectar con el controlador TerraNode en ${baseUrl}`,
      },
      { status: 503 }
    )
  }

}
