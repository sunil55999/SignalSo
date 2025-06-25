import { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ThemeProvider } from "next-themes";
import { useLocation } from "wouter";
import { useAuth } from "@/hooks/use-auth";
import LoginButton from "@/components/auth/LoginButton";
import ConnectionStatus from "@/components/dashboard/ConnectionStatus";
import {
  Activity,
  BarChart3,
  Bot,
  DollarSign,
  Layers,
  Settings,
  Shield,
  Signal,
  TrendingUp,
  Users,
  Zap,
  Menu,
  X
} from "lucide-react";
import { useState } from "react";

interface MainLayoutProps {
  children: ReactNode;
  className?: string;
}

const sidebarItems = [
  {
    id: "dashboard",
    label: "Dashboard",
    icon: BarChart3,
    description: "Overview & Analytics",
    path: "/"
  },
  {
    id: "signals",
    label: "Signal Manager",
    icon: Signal,
    description: "Live Signals & History",
    path: "/signals"
  },
  {
    id: "trades",
    label: "Trade Manager",
    icon: TrendingUp,
    description: "Active Positions",
    path: "/trades"
  },
  {
    id: "providers",
    label: "Providers",
    icon: Users,
    description: "Signal Sources",
    path: "/providers"
  },
  {
    id: "strategy",
    label: "Strategy Builder",
    icon: Layers,
    description: "Automation Rules",
    path: "/strategy"
  },
  {
    id: "analytics",
    label: "Analytics",
    icon: Activity,
    description: "Performance Reports",
    path: "/analytics"
  },
  {
    id: "copilot",
    label: "AI Copilot",
    icon: Bot,
    description: "Smart Assistant",
    path: "/copilot"
  },
  {
    id: "risk",
    label: "Risk Control",
    icon: Shield,
    description: "Safety & Limits",
    path: "/risk"
  },
  {
    id: "settings",
    label: "Settings",
    icon: Settings,
    description: "Configuration",
    path: "/settings"
  }
];

export default function MainLayout({ children, className }: MainLayoutProps) {
  const [location, navigate] = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const { user, isLoading } = useAuth();
  
  const getCurrentTab = () => {
    const currentItem = sidebarItems.find(item => item.path === location);
    return currentItem?.id || "dashboard";
  };
  
  const activeTab = getCurrentTab();

  // Show login if not authenticated
  if (!user && !isLoading) {
    return (
      <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
        <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 flex items-center justify-center">
          <div className="text-center">
            <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl flex items-center justify-center mx-auto mb-6">
              <Zap className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-2">
              SignalOS
            </h1>
            <p className="text-slate-600 dark:text-slate-400 mb-8">
              Professional Trading Automation Platform
            </p>
          </div>
          <LoginButton />
        </div>
      </ThemeProvider>
    );
  }

  if (isLoading) {
    return (
      <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
        <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 flex items-center justify-center">
          <div className="text-center">
            <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl flex items-center justify-center mx-auto mb-6 animate-pulse">
              <Zap className="w-8 h-8 text-white" />
            </div>
            <p className="text-slate-600 dark:text-slate-400">Loading SignalOS...</p>
          </div>
        </div>
      </ThemeProvider>
    );
  }

  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
      <div className="flex h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
        {/* Modern Sidebar */}
        <aside
          className={cn(
            "bg-white/95 dark:bg-slate-900/95 backdrop-blur-sm border-r border-slate-200 dark:border-slate-700 transition-all duration-300 flex flex-col shadow-xl",
            sidebarOpen ? "w-72" : "w-16"
          )}
        >
          {/* Logo & Toggle */}
          <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-700">
            {sidebarOpen && (
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                  <Zap className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="text-lg font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                    SignalOS
                  </h1>
                  <p className="text-xs text-slate-500 dark:text-slate-400">Trading Platform</p>
                </div>
              </div>
            )}
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="h-8 w-8"
            >
              {sidebarOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </Button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-2">
            {sidebarItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              
              return (
                <button
                  key={item.id}
                  onClick={() => navigate(item.path)}
                  className={cn(
                    "w-full flex items-center space-x-3 px-3 py-2.5 rounded-xl text-left transition-all duration-200 group",
                    isActive
                      ? "bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg shadow-blue-500/25"
                      : "hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300"
                  )}
                >
                  <Icon
                    className={cn(
                      "w-5 h-5 flex-shrink-0",
                      isActive ? "text-white" : "text-slate-500 group-hover:text-slate-700 dark:group-hover:text-slate-200"
                    )}
                  />
                  {sidebarOpen && (
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm">{item.label}</div>
                      <div className={cn(
                        "text-xs opacity-75",
                        isActive ? "text-blue-100" : "text-slate-500 dark:text-slate-400"
                      )}>
                        {item.description}
                      </div>
                    </div>
                  )}
                </button>
              );
            })}
          </nav>

          {/* User Info */}
          <div className="p-4 border-t border-slate-200 dark:border-slate-700">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-r from-green-400 to-blue-500 rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-medium">T</span>
              </div>
              {sidebarOpen && (
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-slate-900 dark:text-slate-100">
                    {user?.username || "Trader"}
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">
                    {user?.role === "admin" ? "Admin Account" : "Pro Account"}
                  </div>
                </div>
              )}
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Top Header */}
          <header className="bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm border-b border-slate-200 dark:border-slate-700 px-6 py-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100 capitalize">
                  {sidebarItems.find(item => item.id === activeTab)?.label || "Dashboard"}
                </h2>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  {sidebarItems.find(item => item.id === activeTab)?.description}
                </p>
              </div>
              
              <div className="flex items-center space-x-4">
                {/* Status Indicators */}
                <div className="flex items-center space-x-2">
                  <div className="flex items-center space-x-1">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                    <span className="text-xs text-slate-600 dark:text-slate-400">MT5 Connected</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                    <span className="text-xs text-slate-600 dark:text-slate-400">Signals Active</span>
                  </div>
                </div>

                {/* Quick Stats */}
                <div className="flex items-center space-x-4 text-sm">
                  <div className="flex items-center space-x-1">
                    <DollarSign className="w-4 h-4 text-green-500" />
                    <span className="font-medium text-slate-900 dark:text-slate-100">$12,450</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <TrendingUp className="w-4 h-4 text-blue-500" />
                    <span className="font-medium text-green-600">+2.4%</span>
                  </div>
                </div>
              </div>
            </div>
          </header>

          {/* Content Area */}
          <div className={cn("flex-1 overflow-auto p-6", className)}>
            {children}
          </div>
        </main>
      </div>
    </ThemeProvider>
  );
}