import { MotionConfig } from 'motion/react'
import { useEffect, useState } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { ThemeProvider } from '@/hooks/useTheme'
import { ToastProvider } from '@/hooks/useToast'
import { api } from '@/lib/api'
import { Dashboard } from '@/pages/Dashboard'
import { NotFound } from '@/pages/NotFound'
import { SettingsPage } from '@/pages/Settings'
import { SystemForm } from '@/pages/SystemForm'
import { Systems } from '@/pages/Systems'

function ManagerShell() {
  const [version, setVersion] = useState<string>()
  const [esRunning, setEsRunning] = useState(false)

  useEffect(() => {
    let cancelled = false

    const load = async () => {
      try {
        const dash = await api.dashboard()
        if (cancelled) return
        setVersion(dash.batocera_version)
        setEsRunning(dash.es?.running ?? false)
      } catch {
        /* El backend puede no estar listo: el shell funciona igual. */
      }
    }

    void load()
    const timer = window.setInterval(load, 15000)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [])

  return (
    <AppShell version={version} esRunning={esRunning}>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/sistemas" element={<Systems />} />
        <Route path="/sistemas/nuevo" element={<SystemForm />} />
        <Route path="/sistemas/:name/editar" element={<SystemForm />} />
        <Route path="/configuracion" element={<SettingsPage />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </AppShell>
  )
}

export default function App() {
  return (
    <MotionConfig reducedMotion="user">
      <ThemeProvider>
        <ToastProvider>
          <BrowserRouter>
            <ManagerShell />
          </BrowserRouter>
        </ToastProvider>
      </ThemeProvider>
    </MotionConfig>
  )
}
