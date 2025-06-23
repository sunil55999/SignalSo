import { useAuth } from "@/hooks/use-auth";
import { useLocation } from "wouter";

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export default function Sidebar({ activeTab, onTabChange }: SidebarProps) {
  const { user, logoutMutation } = useAuth();
  const [, navigate] = useLocation();

  const menuItems = [
    { id: "dashboard", label: "Dashboard", icon: "fas fa-tachometer-alt", path: "/" },
    { id: "signals", label: "Signals", icon: "fas fa-signal" },
    { id: "strategy", label: "Strategy Builder", icon: "fas fa-project-diagram" },
    { id: "trades", label: "Live Trades", icon: "fas fa-exchange-alt" },
    { id: "admin", label: "Admin Panel", icon: "fas fa-users-cog", path: "/admin" },
    { id: "logs", label: "Logs & Reports", icon: "fas fa-file-alt" },
  ];

  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
      {/* Logo/Brand */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
            <i className="fas fa-chart-line text-white text-sm"></i>
          </div>
          <span className="text-xl font-bold text-dark">SignalOS</span>
        </div>
      </div>

      {/* Navigation Menu */}
      <nav className="flex-1 p-4 space-y-2">
        {menuItems.map((item) => (
          <button
            key={item.id}
            onClick={() => {
              if (item.path) {
                navigate(item.path);
              } else {
                onTabChange(item.id);
              }
            }}
            className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg font-medium transition-colors ${
              activeTab === item.id
                ? "bg-primary/10 text-primary"
                : "text-gray-700 hover:bg-gray-100"
            }`}
          >
            <i className={`${item.icon} w-5`}></i>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      {/* User Profile */}
      <div className="p-4 border-t border-gray-200">
        <div className="flex items-center space-x-3">
          <img 
            src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=100&h=100" 
            alt="User profile" 
            className="w-10 h-10 rounded-full"
          />
          <div className="flex-1">
            <p className="text-sm font-medium text-dark">{user?.username || "User"}</p>
            <p className="text-xs text-muted">Premium Account</p>
          </div>
          <button 
            onClick={() => logoutMutation.mutate()}
            className="text-gray-400 hover:text-gray-600"
            disabled={logoutMutation.isPending}
          >
            <i className="fas fa-sign-out-alt"></i>
          </button>
        </div>
      </div>
    </aside>
  );
}
