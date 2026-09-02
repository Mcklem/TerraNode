import { NextRequest, NextResponse } from 'next/server'

const baseUrl = process.env.TERRANODE_API_URL || 'http://localhost:8000'
const allowedMethods = new Set(['GET', 'POST'])

export async function GET(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return forward(request, (await params).path)
}

export async function POST(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return forward(request, (await params).path)
}

async function forward(request: NextRequest, path: string[]) {
  if (!allowedMethods.has(request.method) || path.some((part) => part.includes('..'))) {
    return NextResponse.json({ detail: 'Ruta no permitida' }, { status: 400 })
  }
  const target = new URL(`/api/v1/${path.map(encodeURIComponent).join('/')}`, baseUrl)
  const body = request.method === 'POST' ? await request.text() : undefined
  try {
    const response = await fetch(target, { method: request.method, headers: { Accept: 'application/json', ...(body ? { 'Content-Type': 'application/json' } : {}) }, body, cache: 'no-store' })
    const data = await response.json().catch(() => ({ detail: 'Respuesta inválida del controlador' }))
    return NextResponse.json(data, { status: response.status })
  } catch {
    return NextResponse.json({ detail: `No se pudo conectar con TerraNode en ${baseUrl}` }, { status: 503 })
  }
}
