'use client'

import React, { useState } from 'react'
import {
  Bell,
  CheckCircle2,
  Copy,
  Eye,
  EyeOff,
  Globe,
  HelpCircle,
  Lock,
  Mail,
  Plus,
  RefreshCw,
  Send,
  ShieldCheck,
  Trash2,
  X,
  AlertTriangle,
} from 'lucide-react'
import {
  EmailNotificationConfig,
  NotificationsConfig,
  TelegramNotificationConfig,
  WebhookConfig,
  fetchConfig,
  testNotificationChannel,
} from '@/lib/config-api'

interface NotificationsTabProps {
  notifications?: NotificationsConfig
  onChange: (updated: NotificationsConfig) => void
}

type NotificationSubTab = 'telegram' | 'email' | 'webhooks'

export function NotificationsTab({ notifications, onChange }: NotificationsTabProps) {
  const [activeSubTab, setActiveSubTab] = useState<NotificationSubTab>('telegram')
  const [showTokens, setShowTokens] = useState<Record<string, boolean>>({})
  const [revealedSecrets, setRevealedSecrets] = useState<Record<string, string>>({})
  const [loadingSecret, setLoadingSecret] = useState<Record<string, boolean>>({})

  // Testing feedback states
  const [testingChannel, setTestingChannel] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<{
    channel: string
    success: boolean
    message?: string
    error?: string
  } | null>(null)

  // Webhook Modal state
  const [editingWebhookId, setEditingWebhookId] = useState<string | null>(null)
  const [isWebhookModalOpen, setIsWebhookModalOpen] = useState(false)
  const [webhookForm, setWebhookForm] = useState<{
    id: string
    name: string
    enabled: boolean
    url: string
    method: 'GET' | 'POST' | 'PUT'
    headers: Array<{ key: string; value: string }>
    payload_template: string
  }>({
    id: '',
    name: '',
    enabled: true,
    url: '',
    method: 'POST',
    headers: [{ key: 'Content-Type', value: 'application/json' }],
    payload_template: '{"event": "{rule_id}", "device": "{device}", "value": {value}, "timestamp": "{timestamp}"}',
  })

  // Ensure safe config defaults
  const currentNotif: NotificationsConfig = notifications || {
    email: {
      enabled: false,
      smtp_host: '',
      smtp_port: 587,
      use_tls: true,
      username: '',
      password: '',
      from_address: '',
      to_addresses: [],
    },
    telegram: {
      enabled: false,
      bot_token: '',
      chat_id: '',
    },
    webhooks: {},
  }

  const telegramCfg: TelegramNotificationConfig = currentNotif.telegram || {
    enabled: false,
    bot_token: '',
    chat_id: '',
  }

  const emailCfg: EmailNotificationConfig = currentNotif.email || {
    enabled: false,
    smtp_host: '',
    smtp_port: 587,
    use_tls: true,
    username: '',
    password: '',
    from_address: '',
    to_addresses: [],
  }

  const webhooks = currentNotif.webhooks || {}

  const updateTelegram = (patch: Partial<TelegramNotificationConfig>) => {
    onChange({
      ...currentNotif,
      telegram: {
        ...telegramCfg,
        ...patch,
      },
    })
  }

  const updateEmail = (patch: Partial<EmailNotificationConfig>) => {
    onChange({
      ...currentNotif,
      email: {
        ...emailCfg,
        ...patch,
      },
    })
  }

  const updateWebhooks = (newWebhooks: Record<string, WebhookConfig>) => {
    onChange({
      ...currentNotif,
      webhooks: newWebhooks,
    })
  }

  const toggleShowSecret = async (field: 'telegram_bot' | 'email_pass') => {
    // If currently visible, hide it
    if (showTokens[field]) {
      setShowTokens((prev) => ({ ...prev, [field]: false }))
      return
    }

    // Check if we already have the unmasked value cached in state
    if (revealedSecrets[field] !== undefined) {
      setShowTokens((prev) => ({ ...prev, [field]: true }))
      return
    }

    const currentVal = field === 'telegram_bot' ? telegramCfg.bot_token : emailCfg.password
    const isMasked = !currentVal || currentVal.includes('•') || currentVal.includes('*')

    // If the user already typed a plaintext value that is not masked, use it directly
    if (!isMasked && currentVal) {
      setRevealedSecrets((prev) => ({ ...prev, [field]: currentVal }))
      setShowTokens((prev) => ({ ...prev, [field]: true }))
      return
    }

    // Otherwise, fetch the unmasked secret from the server
    try {
      setLoadingSecret((prev) => ({ ...prev, [field]: true }))
      const res = await fetchConfig(false)
      let secret = ''
      if (field === 'telegram_bot') {
        secret = res.config.notifications?.telegram?.bot_token || ''
      } else if (field === 'email_pass') {
        secret = res.config.notifications?.email?.password || ''
      }
      setRevealedSecrets((prev) => ({ ...prev, [field]: secret }))
      setShowTokens((prev) => ({ ...prev, [field]: true }))
    } catch (err) {
      console.error('Error fetching unmasked secret:', err)
      setShowTokens((prev) => ({ ...prev, [field]: true }))
    } finally {
      setLoadingSecret((prev) => ({ ...prev, [field]: false }))
    }
  }

  // Live test dispatcher
  const handleTest = async (channel: 'telegram' | 'email' | 'webhook', webhookId?: string) => {
    setTestingChannel(webhookId ? `webhook-${webhookId}` : channel)
    setTestResult(null)

    try {
      let override: any = undefined
      if (channel === 'telegram') {
        const isMasked =
          !telegramCfg.bot_token ||
          telegramCfg.bot_token.includes('•') ||
          telegramCfg.bot_token.includes('*')
        override = {
          chat_id: telegramCfg.chat_id,
          ...(isMasked ? {} : { bot_token: telegramCfg.bot_token }),
        }
      } else if (channel === 'email') {
        const isMasked =
          !emailCfg.password ||
          emailCfg.password.includes('•') ||
          emailCfg.password.includes('*')
        override = {
          smtp_host: emailCfg.smtp_host,
          smtp_port: emailCfg.smtp_port,
          use_tls: emailCfg.use_tls,
          username: emailCfg.username,
          ...(isMasked ? {} : { password: emailCfg.password }),
          from_address: emailCfg.from_address,
          to_addresses: emailCfg.to_addresses,
        }
      } else if (channel === 'webhook' && webhookId) {
        override = webhooks[webhookId]
      }

      const res = await testNotificationChannel({
        channel,
        webhook_id: webhookId,
        config_override: override,
        message: '🔔 Mensaje de prueba enviado desde el Gestor de Configuración de TerraNode.',
      })

      setTestResult({
        channel: webhookId ? `webhook:${webhookId}` : channel,
        success: res.success,
        message: res.message,
        error: res.error,
      })
    } catch (err: any) {
      setTestResult({
        channel: webhookId ? `webhook:${webhookId}` : channel,
        success: false,
        error: err.message || 'Error de conexión con el servicio de notificaciones.',
      })
    } finally {
      setTestingChannel(null)
    }
  }

  // Webhook Modal Open
  const handleOpenWebhookModal = (id?: string) => {
    if (id && webhooks[id]) {
      const wh = webhooks[id]
      const headersArray = Object.entries(wh.headers || {}).map(([key, value]) => ({ key, value }))
      setEditingWebhookId(id)
      setWebhookForm({
        id,
        name: wh.name || id,
        enabled: wh.enabled !== false,
        url: wh.url || '',
        method: wh.method || 'POST',
        headers: headersArray.length > 0 ? headersArray : [{ key: 'Content-Type', value: 'application/json' }],
        payload_template:
          wh.payload_template ||
          '{"event": "{rule_id}", "device": "{device}", "value": {value}, "timestamp": "{timestamp}"}',
      })
    } else {
      setEditingWebhookId(null)
      const count = Object.keys(webhooks).length + 1
      setWebhookForm({
        id: `webhook_${count}`,
        name: `Webhook ${count}`,
        enabled: true,
        url: '',
        method: 'POST',
        headers: [{ key: 'Content-Type', value: 'application/json' }],
        payload_template:
          '{"event": "{rule_id}", "device": "{device}", "value": {value}, "timestamp": "{timestamp}"}',
      })
    }
    setIsWebhookModalOpen(true)
  }

  const handleSaveWebhook = () => {
    const rawId = webhookForm.id.trim() || `webhook_${Date.now()}`
    const safeId = rawId.toLowerCase().replace(/[^a-z0-9_-]/g, '_')

    const headersObj: Record<string, string> = {}
    for (const h of webhookForm.headers) {
      if (h.key.trim()) {
        headersObj[h.key.trim()] = h.value
      }
    }

    const updatedMap = { ...webhooks }
    if (editingWebhookId && editingWebhookId !== safeId) {
      delete updatedMap[editingWebhookId]
    }

    updatedMap[safeId] = {
      name: webhookForm.name.trim() || safeId,
      enabled: webhookForm.enabled,
      url: webhookForm.url.trim(),
      method: webhookForm.method,
      headers: headersObj,
      payload_template: webhookForm.payload_template.trim() || undefined,
    }

    updateWebhooks(updatedMap)
    setIsWebhookModalOpen(false)
  }

  const handleDeleteWebhook = (id: string) => {
    if (!confirm(`¿Eliminar el webhook '${webhooks[id]?.name || id}'?`)) return
    const updated = { ...webhooks }
    delete updated[id]
    updateWebhooks(updated)
  }

  const insertPlaceholder = (placeholder: string) => {
    setWebhookForm((prev) => ({
      ...prev,
      payload_template: prev.payload_template + placeholder,
    }))
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header Info */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-xl border border-border bg-surface-1">
        <div>
          <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
            <Bell size={18} className="text-accent" />
            Canales de Notificación y Webhooks
          </h3>
          <p className="text-xs text-muted-foreground mt-1">
            Configura el envío de alertas automáticas para reglas de automatización críticas mediante Telegram Bot,
            correo SMTP o Webhooks HTTP hacia plataformas externas (Home Assistant, Node-RED, Discord, etc.).
          </p>
        </div>

        {/* Quick status counters */}
        <div className="flex items-center gap-2 flex-wrap">
          <div
            className={`px-2.5 py-1 text-xs rounded-full border flex items-center gap-1.5 font-mono ${
              telegramCfg.enabled
                ? 'bg-blue-500/10 text-blue-400 border-blue-500/30'
                : 'bg-surface-2 text-muted-foreground border-border'
            }`}
          >
            <Send size={12} />
            Telegram: {telegramCfg.enabled ? 'ON' : 'OFF'}
          </div>
          <div
            className={`px-2.5 py-1 text-xs rounded-full border flex items-center gap-1.5 font-mono ${
              emailCfg.enabled
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                : 'bg-surface-2 text-muted-foreground border-border'
            }`}
          >
            <Mail size={12} />
            Email: {emailCfg.enabled ? 'ON' : 'OFF'}
          </div>
          <div
            className={`px-2.5 py-1 text-xs rounded-full border flex items-center gap-1.5 font-mono ${
              Object.values(webhooks).some((w) => w.enabled)
                ? 'bg-purple-500/10 text-purple-400 border-purple-500/30'
                : 'bg-surface-2 text-muted-foreground border-border'
            }`}
          >
            <Globe size={12} />
            Webhooks: {Object.values(webhooks).filter((w) => w.enabled).length}/{Object.keys(webhooks).length}
          </div>
        </div>
      </div>

      {/* Environment & Security Info Banner */}
      <div className="p-3.5 rounded-xl border border-blue-500/20 bg-blue-500/5 flex items-start gap-3 text-xs">
        <HelpCircle size={16} className="text-blue-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <span className="font-semibold text-foreground">Gestión Segura de Credenciales y Notificaciones</span>
          <p className="text-muted-foreground text-[11px] leading-relaxed">
            Puedes configurar y editar los parámetros directamente desde este formulario visual, o utilizar variables de entorno seguras en el archivo <code className="text-accent bg-surface-2 px-1 py-0.5 rounded font-mono">.env</code> (por ejemplo, <code className="text-accent font-mono">TELEGRAM_BOT_TOKEN</code>, <code className="text-accent font-mono">TELEGRAM_CHAT_ID</code>, <code className="text-accent font-mono">EMAIL_SMTP_HOST</code>, <code className="text-accent font-mono">EMAIL_PASSWORD</code>). Si no modificas un valor resuelto desde <code className="text-accent font-mono">.env</code>, su referencia se mantendrá intacta al guardar.
          </p>
        </div>
      </div>

      {/* Sub Tabs */}
      <div className="flex border-b border-border gap-2">
        <button
          onClick={() => {
            setActiveSubTab('telegram')
            setTestResult(null)
          }}
          className={`px-4 py-2 text-xs font-mono font-medium border-b-2 flex items-center gap-2 transition-colors ${
            activeSubTab === 'telegram'
              ? 'border-accent text-accent'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Send size={14} />
          Telegram Bot
        </button>
        <button
          onClick={() => {
            setActiveSubTab('email')
            setTestResult(null)
          }}
          className={`px-4 py-2 text-xs font-mono font-medium border-b-2 flex items-center gap-2 transition-colors ${
            activeSubTab === 'email'
              ? 'border-accent text-accent'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Mail size={14} />
          Correo Electrónico (SMTP)
        </button>
        <button
          onClick={() => {
            setActiveSubTab('webhooks')
            setTestResult(null)
          }}
          className={`px-4 py-2 text-xs font-mono font-medium border-b-2 flex items-center gap-2 transition-colors ${
            activeSubTab === 'webhooks'
              ? 'border-accent text-accent'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Globe size={14} />
          Webhooks HTTP ({Object.keys(webhooks).length})
        </button>
      </div>

      {/* Test feedback banner */}
      {testResult && (
        <div
          className={`p-4 rounded-xl border text-xs font-mono flex items-start gap-3 ${
            testResult.success
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
              : 'bg-red-500/10 border-red-500/30 text-red-400'
          }`}
        >
          {testResult.success ? (
            <CheckCircle2 size={16} className="shrink-0 mt-0.5" />
          ) : (
            <AlertTriangle size={16} className="shrink-0 mt-0.5" />
          )}
          <div className="flex-1">
            <div className="font-semibold">{testResult.success ? 'Prueba Exitosa' : 'Fallo en la Prueba'}</div>
            <div className="text-[11px] mt-0.5 opacity-90">
              {testResult.message || testResult.error}
            </div>
          </div>
          <button
            onClick={() => setTestResult(null)}
            className="text-muted-foreground hover:text-foreground"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* 1. TELEGRAM TAB */}
      {activeSubTab === 'telegram' && (
        <div className="p-6 rounded-xl border border-border bg-surface-1 space-y-6 max-w-4xl">
          <div className="flex items-center justify-between pb-4 border-b border-border">
            <div>
              <h4 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Send size={16} className="text-blue-400" />
                Notificaciones por Telegram Bot
              </h4>
              <p className="text-xs text-muted-foreground mt-0.5">
                Envía alertas inmediatas a tu canal o chat privado de Telegram.
              </p>
            </div>
            <label className="flex items-center gap-2 cursor-pointer">
              <span className="text-xs font-mono text-muted-foreground">Activo</span>
              <input
                type="checkbox"
                checked={telegramCfg.enabled}
                onChange={(e) => updateTelegram({ enabled: e.target.checked })}
                className="w-4 h-4 rounded border-border text-accent focus:ring-accent"
              />
            </label>
          </div>

          <div className="p-3 rounded-lg border border-blue-500/20 bg-blue-500/5 flex items-start gap-2.5 text-xs">
            <ShieldCheck size={16} className="text-blue-400 shrink-0 mt-0.5" />
            <p className="text-muted-foreground text-[11px] leading-relaxed">
              <strong className="text-foreground">Aislamiento de credenciales:</strong> Los valores de Bot Token y Chat ID se sincronizan automáticamente en tu archivo <code className="font-mono text-blue-300">.env</code> para evitar exponer claves en el archivo <code className="font-mono text-foreground">system.yaml</code>.
            </p>
          </div>

          <div className="space-y-4">
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-mono font-medium text-foreground">
                  Bot Token (`telegram.bot_token`)
                </label>
                <div className="flex items-center gap-1.5">
                  <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center gap-1">
                    <Lock size={10} />
                    .env: TELEGRAM_BOT_TOKEN
                  </span>
                  {(telegramCfg.bot_token?.includes('•') || telegramCfg.bot_token?.includes('*')) && (
                    <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      Protegido
                    </span>
                  )}
                </div>
              </div>
              <div className="relative">
                <input
                  type={showTokens['telegram_bot'] ? 'text' : 'password'}
                  value={
                    showTokens['telegram_bot']
                      ? revealedSecrets['telegram_bot'] !== undefined
                        ? revealedSecrets['telegram_bot']
                        : telegramCfg.bot_token?.includes('•')
                        ? ''
                        : telegramCfg.bot_token || ''
                      : telegramCfg.bot_token || ''
                  }
                  onChange={(e) => {
                    const newVal = e.target.value
                    updateTelegram({ bot_token: newVal })
                    setRevealedSecrets((prev) => ({ ...prev, telegram_bot: newVal }))
                  }}
                  placeholder="123456789:ABCDEF... o variable ${TELEGRAM_BOT_TOKEN}"
                  className="w-full px-3 py-2 pr-10 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
                />
                <button
                  type="button"
                  onClick={() => toggleShowSecret('telegram_bot')}
                  disabled={loadingSecret['telegram_bot']}
                  title={showTokens['telegram_bot'] ? 'Ocultar token' : 'Mostrar token'}
                  className="absolute right-3 top-2.5 text-muted-foreground hover:text-foreground disabled:opacity-50 transition-colors"
                >
                  {loadingSecret['telegram_bot'] ? (
                    <RefreshCw size={14} className="animate-spin text-accent" />
                  ) : showTokens['telegram_bot'] ? (
                    <EyeOff size={14} />
                  ) : (
                    <Eye size={14} />
                  )}
                </button>
              </div>
              <p className="text-[11px] text-muted-foreground">
                Token obtenido de @BotFather al crear el bot de Telegram. Al escribir un nuevo token, se externalizará automáticamente a .env.
              </p>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-mono font-medium text-foreground">
                  Chat ID (`telegram.chat_id`)
                </label>
                <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center gap-1">
                  <Lock size={10} />
                  .env: TELEGRAM_CHAT_ID
                </span>
              </div>
              <input
                type="text"
                value={telegramCfg.chat_id || ''}
                onChange={(e) => updateTelegram({ chat_id: e.target.value })}
                placeholder="123456789 o -100123456789 o ${TELEGRAM_CHAT_ID}"
                className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
              />
              <p className="text-[11px] text-muted-foreground">
                Identificador de usuario, grupo o canal donde enviar los avisos (se sincroniza con TELEGRAM_CHAT_ID en .env).
              </p>
            </div>
          </div>

          <div className="pt-4 border-t border-border flex items-center justify-between">
            <button
              type="button"
              disabled={testingChannel === 'telegram'}
              onClick={() => handleTest('telegram')}
              className="px-4 py-2 text-xs font-mono font-medium rounded-lg border border-blue-500/40 bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 disabled:opacity-50 flex items-center gap-2 transition-colors"
            >
              {testingChannel === 'telegram' ? (
                <RefreshCw size={14} className="animate-spin" />
              ) : (
                <Send size={14} />
              )}
              Probar Telegram Ahora
            </button>
            <span className="text-[11px] text-muted-foreground">
              Guarda la configuración para aplicar permanentemente.
            </span>
          </div>
        </div>
      )}

      {/* 2. EMAIL TAB */}
      {activeSubTab === 'email' && (
        <div className="p-6 rounded-xl border border-border bg-surface-1 space-y-6 max-w-4xl">
          <div className="flex items-center justify-between pb-4 border-b border-border">
            <div>
              <h4 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Mail size={16} className="text-emerald-400" />
                Notificaciones por Correo (SMTP)
              </h4>
              <p className="text-xs text-muted-foreground mt-0.5">
                Envía reportes y alertas a una o varias direcciones de correo electrónico.
              </p>
            </div>
            <label className="flex items-center gap-2 cursor-pointer">
              <span className="text-xs font-mono text-muted-foreground">Activo</span>
              <input
                type="checkbox"
                checked={emailCfg.enabled}
                onChange={(e) => updateEmail({ enabled: e.target.checked })}
                className="w-4 h-4 rounded border-border text-accent focus:ring-accent"
              />
            </label>
          </div>

          <div className="p-3 rounded-lg border border-emerald-500/20 bg-emerald-500/5 flex items-start gap-2.5 text-xs">
            <ShieldCheck size={16} className="text-emerald-400 shrink-0 mt-0.5" />
            <p className="text-muted-foreground text-[11px] leading-relaxed">
              <strong className="text-foreground">Aislamiento de credenciales SMTP:</strong> El servidor, puerto, usuario, contraseña y remitente se sincronizan automáticamente en el archivo <code className="font-mono text-emerald-300">.env</code> de TerraNode sin quedar expuestos en texto plano dentro de <code className="font-mono text-foreground">system.yaml</code>.
            </p>
          </div>

          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="sm:col-span-2 space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-mono font-medium text-foreground">
                    Servidor SMTP (`smtp_host`)
                  </label>
                  <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                    <Lock size={10} />
                    .env: EMAIL_SMTP_HOST
                  </span>
                </div>
                <input
                  type="text"
                  value={emailCfg.smtp_host || ''}
                  onChange={(e) => updateEmail({ smtp_host: e.target.value })}
                  placeholder="smtp.gmail.com"
                  className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
                />
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-mono font-medium text-foreground">
                    Puerto (`smtp_port`)
                  </label>
                  <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    .env: PORT
                  </span>
                </div>
                <input
                  type="number"
                  value={emailCfg.smtp_port || 587}
                  onChange={(e) => updateEmail({ smtp_port: parseInt(e.target.value) || 587 })}
                  placeholder="587"
                  className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
                />
              </div>
            </div>

            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 cursor-pointer text-xs font-mono text-foreground">
                <input
                  type="checkbox"
                  checked={emailCfg.use_tls !== false}
                  onChange={(e) => updateEmail({ use_tls: e.target.checked })}
                  className="w-4 h-4 rounded border-border text-accent focus:ring-accent"
                />
                Usar TLS / STARTTLS (Recomendado para puerto 587)
              </label>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-mono font-medium text-foreground">
                    Usuario SMTP (`username`)
                  </label>
                  <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                    <Lock size={10} />
                    .env: EMAIL_USERNAME
                  </span>
                </div>
                <input
                  type="text"
                  value={emailCfg.username || ''}
                  onChange={(e) => updateEmail({ username: e.target.value })}
                  placeholder="usuario@dominio.com"
                  className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
                />
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-mono font-medium text-foreground">
                    Contraseña (`password`)
                  </label>
                  <div className="flex items-center gap-1.5">
                    <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                      <Lock size={10} />
                      .env: EMAIL_PASSWORD
                    </span>
                    {(emailCfg.password?.includes('•') || emailCfg.password?.includes('*')) && (
                      <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        Protegida
                      </span>
                    )}
                  </div>
                </div>
                <div className="relative">
                  <input
                    type={showTokens['email_pass'] ? 'text' : 'password'}
                    value={
                      showTokens['email_pass']
                        ? revealedSecrets['email_pass'] !== undefined
                          ? revealedSecrets['email_pass']
                          : emailCfg.password?.includes('•')
                          ? ''
                          : emailCfg.password || ''
                        : emailCfg.password || ''
                    }
                    onChange={(e) => {
                      const newVal = e.target.value
                      updateEmail({ password: newVal })
                      setRevealedSecrets((prev) => ({ ...prev, email_pass: newVal }))
                    }}
                    placeholder="Contraseña de aplicación o variable ${EMAIL_PASSWORD}"
                    className="w-full px-3 py-2 pr-10 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
                  />
                  <button
                    type="button"
                    onClick={() => toggleShowSecret('email_pass')}
                    disabled={loadingSecret['email_pass']}
                    title={showTokens['email_pass'] ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                    className="absolute right-3 top-2.5 text-muted-foreground hover:text-foreground disabled:opacity-50 transition-colors"
                  >
                    {loadingSecret['email_pass'] ? (
                      <RefreshCw size={14} className="animate-spin text-accent" />
                    ) : showTokens['email_pass'] ? (
                      <EyeOff size={14} />
                    ) : (
                      <Eye size={14} />
                    )}
                  </button>
                </div>
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-mono font-medium text-foreground">
                  Remitente (`from_address`)
                </label>
                <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                  <Lock size={10} />
                  .env: EMAIL_FROM_ADDRESS
                </span>
              </div>
              <input
                type="text"
                value={emailCfg.from_address || ''}
                onChange={(e) => updateEmail({ from_address: e.target.value })}
                placeholder="terranode@mifinca.local o ${EMAIL_FROM_ADDRESS}"
                className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-mono font-medium text-foreground">
                Destinatarios (`to_addresses`, separados por coma)
              </label>
              <input
                type="text"
                value={Array.isArray(emailCfg.to_addresses) ? emailCfg.to_addresses.join(', ') : ''}
                onChange={(e) =>
                  updateEmail({
                    to_addresses: e.target.value
                      .split(',')
                      .map((s) => s.trim())
                      .filter(Boolean),
                  })
                }
                placeholder="admin@ejemplo.com, operador@ejemplo.com"
                className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
              />
              <p className="text-[11px] text-muted-foreground">
                Lista de direcciones de correo electrónico que recibirán los avisos de alerta.
              </p>
            </div>
          </div>

          <div className="pt-4 border-t border-border flex items-center justify-between">
            <button
              type="button"
              disabled={testingChannel === 'email'}
              onClick={() => handleTest('email')}
              className="px-4 py-2 text-xs font-mono font-medium rounded-lg border border-emerald-500/40 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 disabled:opacity-50 flex items-center gap-2 transition-colors"
            >
              {testingChannel === 'email' ? (
                <RefreshCw size={14} className="animate-spin" />
              ) : (
                <Mail size={14} />
              )}
              Probar Correo SMTP
            </button>
            <span className="text-[11px] text-muted-foreground">
              Guarda la configuración para aplicar permanentemente.
            </span>
          </div>
        </div>
      )}

      {/* 3. WEBHOOKS TAB */}
      {activeSubTab === 'webhooks' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Globe size={16} className="text-purple-400" />
                Endpoints Webhooks Personalizados
              </h4>
              <p className="text-xs text-muted-foreground mt-0.5">
                Endpoints HTTP configurables para integración con Home Assistant, dashboards externos o servicios en la nube.
              </p>
            </div>
            <button
              onClick={() => handleOpenWebhookModal()}
              className="px-3 py-1.5 text-xs font-mono font-medium rounded-lg bg-accent text-accent-foreground hover:bg-accent/90 flex items-center gap-1.5 transition-colors"
            >
              <Plus size={14} />
              Añadir Webhook
            </button>
          </div>

          {Object.keys(webhooks).length === 0 ? (
            <div className="p-8 text-center rounded-xl border border-dashed border-border bg-surface-1 space-y-3">
              <Globe size={32} className="mx-auto text-muted-foreground opacity-50" />
              <p className="text-xs text-muted-foreground font-mono">
                No hay webhooks configurados todavía.
              </p>
              <button
                onClick={() => handleOpenWebhookModal()}
                className="px-3 py-1.5 text-xs font-mono font-medium rounded-lg border border-border bg-surface-2 text-foreground hover:bg-surface-3 transition-colors"
              >
                Crear el primer Webhook
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(webhooks).map(([wId, wCfg]) => {
                const isTestingThis = testingChannel === `webhook-${wId}`
                return (
                  <div
                    key={wId}
                    className="p-5 rounded-xl border border-border bg-surface-1 flex flex-col justify-between space-y-4 hover:border-border/80 transition-colors"
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span
                            className={`w-2 h-2 rounded-full ${
                              wCfg.enabled ? 'bg-emerald-400' : 'bg-zinc-600'
                            }`}
                          />
                          <h5 className="text-xs font-mono font-semibold text-foreground">
                            {wCfg.name || wId}
                          </h5>
                          <span className="text-[10px] font-mono text-muted-foreground">({wId})</span>
                        </div>
                        <span
                          className={`px-2 py-0.5 text-[10px] font-mono font-semibold rounded uppercase ${
                            wCfg.method === 'POST'
                              ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                              : wCfg.method === 'PUT'
                              ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                              : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          }`}
                        >
                          {wCfg.method || 'POST'}
                        </span>
                      </div>

                      <div className="text-[11px] font-mono text-muted-foreground break-all bg-surface-2 px-2.5 py-1.5 rounded border border-border">
                        {wCfg.url || <span className="italic text-zinc-500">Sin URL configurada</span>}
                      </div>

                      {wCfg.headers && Object.keys(wCfg.headers).length > 0 && (
                        <div className="text-[10px] font-mono text-muted-foreground">
                          Cabeceras:{' '}
                          <span className="text-foreground">
                            {Object.keys(wCfg.headers).join(', ')}
                          </span>
                        </div>
                      )}
                    </div>

                    <div className="pt-3 border-t border-border flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          disabled={isTestingThis}
                          onClick={() => handleTest('webhook', wId)}
                          className="px-2.5 py-1 text-xs font-mono rounded border border-purple-500/30 bg-purple-500/10 text-purple-400 hover:bg-purple-500/20 disabled:opacity-50 flex items-center gap-1.5 transition-colors"
                        >
                          {isTestingThis ? (
                            <RefreshCw size={12} className="animate-spin" />
                          ) : (
                            <Send size={12} />
                          )}
                          Probar
                        </button>
                        <button
                          type="button"
                          onClick={() => handleOpenWebhookModal(wId)}
                          className="px-2.5 py-1 text-xs font-mono rounded border border-border bg-surface-2 text-foreground hover:bg-surface-3 transition-colors"
                        >
                          Editar
                        </button>
                      </div>

                      <button
                        type="button"
                        onClick={() => handleDeleteWebhook(wId)}
                        className="p-1 text-muted-foreground hover:text-red-400 transition-colors"
                        title="Eliminar webhook"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* WEBHOOK ADD / EDIT MODAL */}
      {isWebhookModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="w-full max-w-xl p-6 rounded-2xl border border-border bg-surface-1 shadow-2xl space-y-5 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-border">
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Globe size={16} className="text-purple-400" />
                {editingWebhookId ? 'Editar Webhook' : 'Nuevo Endpoint Webhook'}
              </h3>
              <button
                onClick={() => setIsWebhookModalOpen(false)}
                className="text-muted-foreground hover:text-foreground"
              >
                <X size={16} />
              </button>
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-mono font-medium text-foreground">
                    Identificador (`id`)
                  </label>
                  <input
                    type="text"
                    disabled={!!editingWebhookId}
                    value={webhookForm.id}
                    onChange={(e) => setWebhookForm((prev) => ({ ...prev, id: e.target.value }))}
                    placeholder="home_assistant"
                    className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent disabled:opacity-50"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-mono font-medium text-foreground">
                    Nombre Descriptivo
                  </label>
                  <input
                    type="text"
                    value={webhookForm.name}
                    onChange={(e) => setWebhookForm((prev) => ({ ...prev, name: e.target.value }))}
                    placeholder="Home Assistant Alerta"
                    className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                <div className="sm:col-span-1 space-y-1.5">
                  <label className="text-xs font-mono font-medium text-foreground">Método</label>
                  <select
                    value={webhookForm.method}
                    onChange={(e) =>
                      setWebhookForm((prev) => ({ ...prev, method: e.target.value as any }))
                    }
                    className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
                  >
                    <option value="POST">POST</option>
                    <option value="PUT">PUT</option>
                    <option value="GET">GET</option>
                  </select>
                </div>

                <div className="sm:col-span-3 space-y-1.5">
                  <label className="text-xs font-mono font-medium text-foreground">URL Destino</label>
                  <input
                    type="url"
                    value={webhookForm.url}
                    onChange={(e) => setWebhookForm((prev) => ({ ...prev, url: e.target.value }))}
                    placeholder="https://ha.mifinca.local/api/webhook/alert"
                    className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
                  />
                </div>
              </div>

              <div className="flex items-center gap-2">
                <label className="flex items-center gap-2 cursor-pointer text-xs font-mono text-foreground">
                  <input
                    type="checkbox"
                    checked={webhookForm.enabled}
                    onChange={(e) => setWebhookForm((prev) => ({ ...prev, enabled: e.target.checked }))}
                    className="w-4 h-4 rounded border-border text-accent focus:ring-accent"
                  />
                  Habilitar este webhook para envíos automáticos
                </label>
              </div>

              {/* Custom Headers */}
              <div className="space-y-2 pt-2 border-t border-border">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-mono font-medium text-foreground">
                    Cabeceras HTTP (`headers`)
                  </label>
                  <button
                    type="button"
                    onClick={() =>
                      setWebhookForm((prev) => ({
                        ...prev,
                        headers: [...prev.headers, { key: '', value: '' }],
                      }))
                    }
                    className="text-[11px] font-mono text-accent hover:underline flex items-center gap-1"
                  >
                    <Plus size={12} />
                    Añadir Cabecera
                  </button>
                </div>

                {webhookForm.headers.map((h, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <input
                      type="text"
                      placeholder="Header (e.g. Authorization)"
                      value={h.key}
                      onChange={(e) => {
                        const newH = [...webhookForm.headers]
                        newH[idx].key = e.target.value
                        setWebhookForm((prev) => ({ ...prev, headers: newH }))
                      }}
                      className="w-1/2 px-2.5 py-1.5 text-xs font-mono rounded border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
                    />
                    <input
                      type="text"
                      placeholder="Valor (e.g. Bearer token)"
                      value={h.value}
                      onChange={(e) => {
                        const newH = [...webhookForm.headers]
                        newH[idx].value = e.target.value
                        setWebhookForm((prev) => ({ ...prev, headers: newH }))
                      }}
                      className="w-1/2 px-2.5 py-1.5 text-xs font-mono rounded border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
                    />
                    <button
                      type="button"
                      onClick={() => {
                        const newH = webhookForm.headers.filter((_, i) => i !== idx)
                        setWebhookForm((prev) => ({ ...prev, headers: newH }))
                      }}
                      className="text-muted-foreground hover:text-red-400 p-1"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}

                <p className="text-[10px] text-muted-foreground">
                  Las cabeceras con tokens sensibles (Authorization, Token, Secret, Key) se aíslan automáticamente en el archivo <code className="font-mono text-purple-300">.env</code> al guardar la configuración.
                </p>
              </div>

              {/* Payload Template */}
              <div className="space-y-2 pt-2 border-t border-border">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-mono font-medium text-foreground">
                    Plantilla de Carga (`payload_template`)
                  </label>
                  <span className="text-[10px] text-muted-foreground">JSON o texto con variables</span>
                </div>

                <div className="flex flex-wrap gap-1 mb-1">
                  {[
                    '{device}',
                    '{property}',
                    '{value}',
                    '{threshold}',
                    '{operator}',
                    '{rule_id}',
                    '{timestamp}',
                  ].map((tok) => (
                    <button
                      key={tok}
                      type="button"
                      onClick={() => insertPlaceholder(tok)}
                      className="px-2 py-0.5 text-[10px] font-mono rounded border border-border bg-surface-2 text-foreground hover:bg-surface-3 hover:border-accent/40 transition-colors"
                      title={`Insertar ${tok}`}
                    >
                      + {tok}
                    </button>
                  ))}
                </div>

                <textarea
                  rows={4}
                  value={webhookForm.payload_template}
                  onChange={(e) =>
                    setWebhookForm((prev) => ({ ...prev, payload_template: e.target.value }))
                  }
                  placeholder='{"event": "{rule_id}", "device": "{device}", "value": {value}}'
                  className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-border bg-surface-2 text-foreground focus:outline-none focus:border-accent"
                />
              </div>
            </div>

            <div className="pt-4 border-t border-border flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setIsWebhookModalOpen(false)}
                className="px-4 py-2 text-xs font-mono rounded-lg border border-border bg-surface-2 text-muted-foreground hover:text-foreground transition-colors"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleSaveWebhook}
                disabled={!webhookForm.url.trim()}
                className="px-4 py-2 text-xs font-mono font-medium rounded-lg bg-accent text-accent-foreground hover:bg-accent/90 disabled:opacity-50 transition-colors"
              >
                {editingWebhookId ? 'Actualizar Webhook' : 'Guardar Webhook'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
