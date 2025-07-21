import { ReactNode } from 'react'
import { SidebarNav } from './SidebarNav'
import { DashboardHeader } from './DashboardHeader'

interface LayoutProps {
  children: ReactNode
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="desktop-grid">
      <div className="desktop-sidebar">
        <SidebarNav />
      </div>
      <main className="flex flex-col min-h-screen">
        <DashboardHeader />
        <div className="flex-1 desktop-content custom-scrollbar overflow-auto">
          {children}
        </div>
      </main>
    </div>
  )
}