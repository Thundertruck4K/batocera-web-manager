import { motion } from 'motion/react'
import {
  FolderCog,
  Info,
  Power,
  RefreshCw,
  Save,
  Server,
  Terminal,
  Trophy,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { PageContainer, useShell } from '@/components/layout/AppShell'
import { Topbar } from '@/components/layout/Topbar'
import { Button } from '@/components/ui/Button'
import { Field, Input, Toggle } from '@/components/ui/Field'
import { PanelCard, StatRow } from '@/components/ui/Card'
import { PillBar, Pill } from '@/components/ui/Pill'
import { useApi } from '@/hooks/useApi'
import { useTheme } from '@/hooks/useTheme'
import { useToast } from '@/hooks/useToast'
import { triggerHaptic } from '@/hooks/useWebHaptics'
import { api } from '@/lib/api'
import type { ServiceStatus, Settings, UiTheme } from '@/lib/types'

const EASE = [0.16, 1, 0.3, 1] as const

const THEME_OPTIONS: { label: string; value: UiTheme }[] = [
  { label: 'Oscuro', value: 'dark' },
  { label: 'Claro', value: 'light' },
  { label: 'Automático', value: 'auto' },
]

const PATH_FIELDS: { key: keyof Settings; label: string; hint?: string }[] = [
  { key: 'es_cfg_dir', label: 'Configuraciones de EmulationStation' },
  { key: 'roms_base', label: 'Base de ROMs' },
  { key: 'themes_user', label: 'Temas del usuario' },
  { key: 'themes_sys', label: 'Temas del sistema' },
  { key: 'bios_dir', label: 'Directorio de BIOS' },
  { key: 'batocera_conf', label: 'Fichero batocera.conf' },
  { key: 'python_path', label: 'Ruta de configgen (emulatorlauncher.py)' },
  { key: 'app_path', label: 'Ruta de app.py' },
]

export function SettingsPage() {
  const { openMenu } = useShell()
  const { showToast } = useToast()
  const { mode, setMode } = useTheme()

  const settings = useApi(() => api.getSettings(), [])
  const service = useApi(() => api.serviceStatus(), [])
  const info = useApi(() => api.systemInfo(), [])

  const [draft, setDraft] = useState<Partial<Settings>>({})
  const [raKey, setRaKey] = useState('')
  const [saving, setSaving] = useState(false)
  const [busy, setBusy] = useState<string | null>(null)

  useEffect(() => {
    if (settings.data) setDraft(settings.data)
  }, [settings.data])

  const value = <K extends keyof Settings>(key: K): string => {
    const v = draft[key]
    return v === undefined || v === null ? '' : String(v)
  }

  const save = async () => {
    setSaving(true)
    try {
      const payload: Partial<Settings> & { ra_api_key?: string } = { ...draft }
      // La clave real nunca se devuelve al cliente: sólo se envía si el
      // usuario escribe una nueva.
      if (raKey.trim()) payload.ra_api_key = raKey.trim()
      else delete payload.ra_api_key

      await api.saveSettings(payload)
      triggerHaptic('success')
      showToast('Ajustes guardados.', 'success')
      setRaKey('')
      settings.refresh()
    } catch {
      triggerHaptic('error')
      showToast('No se pudieron guardar los ajustes.', 'error')
    } finally {
      setSaving(false)
    }
  }

  const serviceAction = async (action: 'install' | 'remove' | 'restart') => {
    setBusy(action)
    triggerHaptic('medium')
    try {
      if (action === 'install') await api.serviceInstall()
      else if (action === 'remove') await api.serviceRemove()
      else await api.serviceRestart()
      showToast(
        action === 'install'
          ? 'Arranque automático instalado.'
          : action === 'remove'
            ? 'Arranque automático retirado.'
            : 'Servicio reiniciado.',
        'success',
      )
      service.refresh()
    } catch {
      showToast('La operación no se pudo completar.', 'error')
    } finally {
      setBusy(null)
    }
  }

  const status: ServiceStatus | null = service.data
  // Carpeta de instalación: la ruta de app.py sin el nombre del fichero.
  const installDir = (info.data?.app_path || '/userdata/system/batocera_web/app.py').replace(
    /\/app\.py$/,
    '',
  )

  return (
    <>
      <Topbar
        title="Configuración"
        subtitle="Rutas, tema de la interfaz y arranque automático"
        onMenu={openMenu}
        actions={
          <Button size="sm" variant="primary" onClick={save} disabled={saving}>
            <Save className="size-3.5" />
            {saving ? 'Guardando…' : 'Guardar'}
          </Button>
        }
      />

      <PageContainer>
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          {/* Tema */}
          <PanelCard
            title="Tema de la interfaz"
            subtitle="Se aplica al instante y se guarda en el manager"
            icon={<RefreshCw className="size-4" />}
          >
            <PillBar>
              {THEME_OPTIONS.map((opt) => (
                <Pill
                  key={opt.value}
                  active={mode === opt.value}
                  onClick={() => {
                    triggerHaptic('light')
                    setMode(opt.value)
                  }}
                >
                  {opt.label}
                </Pill>
              ))}
            </PillBar>
            <p className="mt-3 text-xs text-muted-foreground">
              «Automático» sigue la preferencia del sistema (claro u oscuro).
            </p>
          </PanelCard>

          {/* Servicio */}
          <PanelCard
            title="Arranque automático"
            subtitle={status?.autostart.installed ? 'Instalado en custom.sh' : 'No instalado'}
            icon={<Power className="size-4" />}
            actions={
              status?.autostart.installed ? (
                <>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => serviceAction('restart')}
                    disabled={busy !== null}
                  >
                    Reiniciar
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => serviceAction('remove')}
                    disabled={busy !== null}
                  >
                    Quitar
                  </Button>
                </>
              ) : (
                <Button
                  size="sm"
                  variant="primary"
                  onClick={() => serviceAction('install')}
                  disabled={busy !== null}
                >
                  Instalar
                </Button>
              )
            }
          >
            <div className="space-y-1">
              <StatRow
                label="Estado"
                value={status?.autostart.installed ? 'Instalado' : 'No instalado'}
              />
              <StatRow
                label="Proceso"
                value={
                  status?.process.running
                    ? `Activo · PID ${status.process.pid ?? '—'}`
                    : 'Detenido'
                }
              />
              <StatRow
                label="Puerto en marcha"
                value={status?.process.port ? String(status.process.port) : '—'}
              />
              <StatRow label="Fichero" value={status?.custom_sh ?? '—'} />
            </div>
            {status?.autostart.manual_mode && (
              <p className="mt-3 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-[11px] font-medium text-amber-600 dark:text-amber-400">
                El manager se está ejecutando en modo manual: no arrancó con el sistema.
              </p>
            )}
            <div className="mt-3">
              <p className="text-xs font-medium text-foreground">Bloque en custom.sh</p>
              <pre className="mt-1 overflow-auto rounded-xl border border-border bg-stage p-3 font-mono text-[10px] leading-relaxed text-muted-foreground">
                {status?.autostart.block?.trim() || '(sin bloque)'}
              </pre>
            </div>
          </PanelCard>

          {/* Información del sistema */}
          <PanelCard
            title="Información del sistema"
            subtitle="Qué está sirviendo ahora mismo el manager"
            icon={<Info className="size-4" />}
          >
            <div className="space-y-1">
              <StatRow label="Versión del manager" value={info.data ? `v${info.data.version}` : '—'} />
              <StatRow
                label="Interfaz"
                value={
                  !info.data
                    ? '—'
                    : info.data.frontend === 'react'
                      ? 'SPA de React + Tailwind'
                      : 'Interfaz clásica (un fichero)'
                }
              />
              <StatRow label="Python" value={info.data?.python_version ?? '—'} />
              <StatRow
                label="Node"
                value={
                  !info.data
                    ? '—'
                    : info.data.node_version
                      ? `${info.data.node_version} · instalado`
                      : 'no instalado · no hace falta'
                }
              />
              <StatRow
                label="Pillow (logos)"
                value={
                  !info.data ? '—' : info.data.has_pil ? 'disponible' : 'no disponible'
                }
              />
              <StatRow label="Puerto" value={info.data ? String(info.data.port) : '—'} />
              <StatRow label="Bundle del frontend" value={info.data?.dist_dir ?? '—'} />
              <StatRow label="Script de arranque" value={info.data?.custom_sh ?? '—'} />
            </div>
            <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
              {info.data?.frontend === 'react'
                ? 'El frontend se sirve ya compilado desde frontend/dist: la consola no necesita Node para funcionar.'
                : 'No hay bundle compilado en frontend/dist, así que se sirve la interfaz clásica de un solo fichero. Compila el frontend para usar la versión React.'}
            </p>
          </PanelCard>

          {/* Instrucciones */}
          <PanelCard
            title="Instrucciones"
            subtitle="Instalar, actualizar y recompilar"
            icon={<Terminal className="size-4" />}
          >
            <div className="space-y-3">
              <div>
                <p className="text-xs font-medium text-foreground">Acceso</p>
                <pre className="mt-1 overflow-auto rounded-xl border border-border bg-stage p-3 font-mono text-[10px] leading-relaxed text-muted-foreground">
                  {`http://<IP-DE-LA-CONSOLA>:${info.data?.port ?? 5000}`}
                </pre>
              </div>
              <div>
                <p className="text-xs font-medium text-foreground">Instalar o actualizar (por SSH)</p>
                <pre className="mt-1 overflow-auto rounded-xl border border-border bg-stage p-3 font-mono text-[10px] leading-relaxed text-muted-foreground">
                  {`cd ${installDir}
git pull
bash install.sh`}
                </pre>
              </div>
              <div>
                <p className="text-xs font-medium text-foreground">
                  Recompilar el frontend en la consola (opcional, requiere Node)
                </p>
                <pre className="mt-1 overflow-auto rounded-xl border border-border bg-stage p-3 font-mono text-[10px] leading-relaxed text-muted-foreground">
                  {`cd ${installDir}/frontend
npm ci
npm run build`}
                </pre>
              </div>
              <p className="text-xs leading-relaxed text-muted-foreground">
                La consola no trae Node de serie: <code className="font-mono text-foreground">bash install.sh</code>{' '}
                lo puede instalar por ti (tarball oficial de nodejs.org, con el sha256 verificado) y
                dejar los enlaces listos para cada arranque. El bundle se despliega compilado, así que
                el manager funciona igual sin Node.
              </p>
            </div>
          </PanelCard>

          {/* Rutas */}
          <PanelCard
            title="Rutas del sistema"
            subtitle="Dónde busca y escribe el manager"
            icon={<FolderCog className="size-4" />}
          >
            <div className="grid grid-cols-1 gap-4">
              {PATH_FIELDS.map((field) => (
                <Field key={String(field.key)} label={field.label} hint={field.hint}>
                  <Input
                    value={value(field.key)}
                    onChange={(e) => setDraft((prev) => ({ ...prev, [field.key]: e.target.value }))}
                    spellCheck={false}
                  />
                </Field>
              ))}
              <Field label="Puerto del servidor" hint="Se aplica al reiniciar el manager.">
                <Input
                  type="number"
                  value={value('server_port')}
                  onChange={(e) =>
                    setDraft((prev) => ({ ...prev, server_port: Number(e.target.value) || 5000 }))
                  }
                />
              </Field>
            </div>
          </PanelCard>

          {/* RetroAchievements */}
          <PanelCard
            title="RetroAchievements"
            subtitle="Progreso y logros dentro del panel"
            icon={<Trophy className="size-4" />}
          >
            <Toggle
              checked={draft.ra_enabled ?? false}
              onChange={(v) => setDraft((prev) => ({ ...prev, ra_enabled: v }))}
              label="Activar RetroAchievements"
              description="Al desactivarlo el panel deja de consultar la API."
            />

            <div className="mt-4 grid grid-cols-1 gap-4">
              <Field label="Usuario" htmlFor="ra_user">
                <Input
                  id="ra_user"
                  value={value('ra_user')}
                  onChange={(e) => setDraft((prev) => ({ ...prev, ra_user: e.target.value }))}
                  spellCheck={false}
                />
              </Field>
              <Field
                label="Web API Key"
                htmlFor="ra_key"
                hint={
                  settings.data?.ra_api_key_set
                    ? 'Ya hay una clave guardada. Escríbela para sustituirla.'
                    : 'Todavía no hay ninguna clave guardada.'
                }
              >
                <Input
                  id="ra_key"
                  type="password"
                  value={raKey}
                  onChange={(e) => setRaKey(e.target.value)}
                  placeholder={settings.data?.ra_api_key_set ? '••••••••••••' : ''}
                  spellCheck={false}
                  autoComplete="off"
                />
              </Field>
            </div>
          </PanelCard>

          {/* Servidor */}
          <PanelCard
            title="Servidor"
            subtitle="Proceso del manager en ejecución"
            icon={<Server className="size-4" />}
          >
            <div className="space-y-1">
              <StatRow label="Estado del servicio" value={status?.process.running ? 'Activo' : 'Detenido'} />
              <StatRow
                label="Modo"
                value={status?.autostart.manual_mode ? 'Manual' : 'Arranque automático'}
              />
              <StatRow
                label="PID"
                value={status?.process.pid ? String(status.process.pid) : '—'}
              />
              <StatRow
                label="Puerto en marcha"
                value={status?.process.port ? String(status.process.port) : '—'}
              />
              <StatRow
                label="Puerto configurado"
                value={value('server_port') || '—'}
              />
            </div>
            {status?.process.cmd && (
              <pre className="mt-3 overflow-auto rounded-xl border border-border bg-stage p-3 font-mono text-[10px] leading-relaxed text-muted-foreground">
                {status.process.cmd}
              </pre>
            )}
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.25, ease: EASE }}
              className="mt-3 text-xs leading-relaxed text-muted-foreground"
            >
              La interfaz se sirve desde el mismo proceso que expone la API: no hay ningún otro
              servicio implicado.
            </motion.p>
          </PanelCard>
        </div>
      </PageContainer>
    </>
  )
}
