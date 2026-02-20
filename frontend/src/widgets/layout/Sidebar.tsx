import { NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Wallet,
  Receipt,
  Calendar,
  Newspaper,
  Bot,
  ArrowLeftRight,
  CreditCard,
  TrendingUp,
  Settings,
  ChevronLeft,
  ChevronRight,
  LogOut,
} from "lucide-react";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { Separator } from "@/shared/ui/separator";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/shared/ui/tooltip";
import { useAuthStore } from "@/features/auth/model/auth-store";

const NAV_ITEMS = [
  { to: "/", icon: LayoutDashboard, label: "대시보드" },
  { to: "/assets", icon: Wallet, label: "자산 관리" },
  { to: "/budget", icon: Receipt, label: "예산 관리" },
  { to: "/calendar", icon: Calendar, label: "캘린더" },
  { to: "/expenses", icon: CreditCard, label: "지출 내역" },
  { to: "/transactions", icon: ArrowLeftRight, label: "거래 내역" },
  { to: "/income", icon: TrendingUp, label: "수입 내역" },
  { to: "/news", icon: Newspaper, label: "뉴스" },
  { to: "/chatbot", icon: Bot, label: "AI 챗봇" },
] as const;

const navLinkClass = (isActive: boolean, collapsed?: boolean) =>
  cn(
    "flex items-center rounded-lg text-sm font-medium transition-colors",
    collapsed ? "justify-center p-3" : "gap-3 px-3 py-2.5",
    isActive
      ? "bg-sidebar-accent text-sidebar-accent-foreground"
      : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground",
  );

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  onNavigate?: () => void;
}

export function Sidebar({ collapsed, onToggle, onNavigate }: SidebarProps) {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-30 flex h-screen flex-col border-r border-sidebar-border bg-sidebar transition-[width] duration-300",
        collapsed ? "w-20" : "w-60",
      )}
    >
      {/* Logo */}
      <div
        className={cn("flex h-14 items-center gap-2", collapsed ? "justify-center px-2" : "px-4")}
      >
        <img src="/logo.svg" alt="MyFinance" className="h-8 w-8 shrink-0 rounded-lg" />
        {!collapsed && (
          <span className="text-lg font-semibold text-sidebar-foreground whitespace-nowrap">
            MyFinance
          </span>
        )}
      </div>

      <Separator className="bg-sidebar-border" />

      {/* Navigation */}
      <nav
        className={cn(
          "flex flex-1 flex-col overflow-y-auto overflow-x-hidden py-3",
          collapsed ? "items-center gap-2 px-3" : "gap-1.5 px-2",
        )}
      >
        {NAV_ITEMS.map(({ to, icon: Icon, label }) =>
          collapsed ? (
            <Tooltip key={to} delayDuration={0}>
              <TooltipTrigger asChild>
                <NavLink
                  to={to}
                  end={to === "/"}
                  className={({ isActive }) => navLinkClass(isActive, true)}
                  onClick={onNavigate}
                >
                  <Icon className="h-6 w-6 shrink-0" aria-hidden="true" />
                </NavLink>
              </TooltipTrigger>
              <TooltipContent side="right">{label}</TooltipContent>
            </Tooltip>
          ) : (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) => navLinkClass(isActive)}
              onClick={onNavigate}
            >
              <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
              <span className="truncate">{label}</span>
            </NavLink>
          ),
        )}
      </nav>

      <Separator className="bg-sidebar-border" />

      {/* Bottom */}
      <div
        className={cn("flex flex-col py-3", collapsed ? "items-center gap-2 px-3" : "gap-1.5 px-2")}
      >
        {collapsed ? (
          <Tooltip delayDuration={0}>
            <TooltipTrigger asChild>
              <NavLink to="/settings" className={({ isActive }) => navLinkClass(isActive, true)} onClick={onNavigate}>
                <Settings className="h-6 w-6 shrink-0" aria-hidden="true" />
              </NavLink>
            </TooltipTrigger>
            <TooltipContent side="right">설정</TooltipContent>
          </Tooltip>
        ) : (
          <NavLink to="/settings" className={({ isActive }) => navLinkClass(isActive)} onClick={onNavigate}>
            <Settings className="h-5 w-5 shrink-0" aria-hidden="true" />
            <span className="truncate">설정</span>
          </NavLink>
        )}

        {user &&
          (collapsed ? (
            <Tooltip delayDuration={0}>
              <TooltipTrigger asChild>
                <button
                  onClick={handleLogout}
                  className="flex w-full items-center justify-center rounded-lg p-3 text-sm font-medium text-sidebar-foreground/70 transition-colors hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
                >
                  <LogOut className="h-6 w-6 shrink-0" aria-hidden="true" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="right">로그아웃</TooltipContent>
            </Tooltip>
          ) : (
            <button
              onClick={handleLogout}
              className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-sidebar-foreground/70 transition-colors hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
            >
              <LogOut className="h-5 w-5 shrink-0" aria-hidden="true" />
              <span className="truncate">로그아웃</span>
            </button>
          ))}
      </div>

      {/* Collapse toggle */}
      <div className={cn("border-t border-sidebar-border p-2", collapsed && "flex justify-center")}>
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggle}
          className="h-9 w-9 text-sidebar-foreground/50 hover:text-sidebar-foreground"
          aria-label={collapsed ? "사이드바 펼치기" : "사이드바 접기"}
        >
          {collapsed ? <ChevronRight className="h-5 w-5" /> : <ChevronLeft className="h-5 w-5" />}
        </Button>
      </div>
    </aside>
  );
}
