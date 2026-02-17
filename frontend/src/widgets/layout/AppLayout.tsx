import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { Sheet, SheetContent } from '@/shared/ui/sheet';
import { cn } from '@/shared/lib/utils';

export function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-background">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground">
        본문으로 건너뛰기
      </a>
      {/* Desktop sidebar */}
      <div className="hidden md:block">
        <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />
      </div>

      {/* Mobile sidebar (Sheet) */}
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="w-60 p-0">
          <Sidebar collapsed={false} onToggle={() => setMobileOpen(false)} />
        </SheetContent>
      </Sheet>

      {/* Main content */}
      <div
        className={cn(
          'flex min-h-screen flex-col transition-[margin-left] duration-300',
          collapsed ? 'md:ml-20' : 'md:ml-60'
        )}
      >
        <Header onMenuClick={() => setMobileOpen(true)} />
        <main id="main-content" className="flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
