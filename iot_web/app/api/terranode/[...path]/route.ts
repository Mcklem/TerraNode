import { NextRequest, NextResponse } from 'next/server'

const baseUrl = process.env.TERRANODE_API_URL || 'http://localhost:8000'
const allowedMethods = new Set(['GET', 'POST'])

export async function GET(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return forward(request, (await params).path)
}

export async function POST(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return forward(request, (await params).path)
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

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 6000)

  try {
    const response = await fetch(targetUrl.toString(), {
      method: request.method,
      headers: {
        Accept: 'application/json',
        ...(body ? { 'Content-Type': 'application/json' } : {}),
      },
      body,
      cache: 'no-store',
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

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
