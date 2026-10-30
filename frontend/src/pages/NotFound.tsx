import { Compass } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { PageContainer, useShell } from '@/components/layout/AppShell'
import { Topbar } from '@/components/layout/Topbar'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'

export function NotFound() {
  const { openMenu } = useShell()
  const navigate = useNavigate()

  return (
    <>
      <Topbar title="Página no encontrada" subtitle="404" onMenu={openMenu} />
      <PageContainer>
        <EmptyState
          icon={<Compass className="size-5" />}
          title="Esta sección no existe"
          description="El enlace que has seguido no apunta a ninguna pantalla del manager."
          action={
            <Button variant="primary" onClick={() => navigate('/')}>
              Volver al panel
            </Button>
          }
        />
      </PageContainer>
    </>
  )
}
