import { useState } from "react";
import Sidebar from "@/components/layout/sidebar";
import TopHeader from "@/components/layout/top-header";
import StatsGrid from "@/components/dashboard/stats-grid";
import LiveTrades from "@/components/dashboard/live-trades";
import RecentSignals from "@/components/dashboard/recent-signals";
import QuickActions from "@/components/dashboard/quick-actions";
import StrategyBuilderModal from "@/components/modals/strategy-builder-modal";

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [isStrategyModalOpen, setIsStrategyModalOpen] = useState(false);

  const handleTabChange = (tab: string) => {
    if (tab === "strategy") {
      setIsStrategyModalOpen(true);
    } else {
      setActiveTab(tab);
    }
  };

  const renderContent = () => {
    switch (activeTab) {
      case "dashboard":
        return (
          <div className="fade-in">
            <StatsGrid />
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-8">
              <LiveTrades />
              <RecentSignals />
            </div>

            <div className="mt-8">
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
                <div className="p-6 border-b border-gray-200">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-dark">Strategy Performance</h3>
                    <div className="flex items-center space-x-2">
                      <select className="text-sm border border-gray-300 rounded-lg px-3 py-1 focus:outline-none focus:ring-2 focus:ring-primary/20">
                        <option>Last 7 Days</option>
                        <option>Last 30 Days</option>
                        <option>Last 3 Months</option>
                      </select>
                    </div>
                  </div>
                </div>
                <div className="p-6">
                  <div className="h-64 bg-gray-50 rounded-lg flex items-center justify-center border-2 border-dashed border-gray-300">
                    <div className="text-center">
                      <i className="fas fa-chart-area text-4xl text-gray-400 mb-4"></i>
                      <p className="text-gray-500 font-medium">Performance Chart</p>
                      <p className="text-sm text-gray-400">Real-time P&L and signal success metrics</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <QuickActions />
          </div>
        );
      case "signals":
        return (
          <div className="fade-in">
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
              <div className="p-6 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-dark">Signal History</h3>
              </div>
              <div className="p-6">
                <div className="text-center py-8">
                  <i className="fas fa-signal text-4xl text-gray-400 mb-4"></i>
                  <p className="text-gray-500 font-medium">Signal History View</p>
                  <p className="text-sm text-gray-400">Detailed signal processing and execution logs</p>
                </div>
              </div>
            </div>
          </div>
        );
      case "trades":
        return (
          <div className="fade-in">
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
              <div className="p-6 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-dark">Live Trades Management</h3>
              </div>
              <div className="p-6">
                <div className="text-center py-8">
                  <i className="fas fa-exchange-alt text-4xl text-gray-400 mb-4"></i>
                  <p className="text-gray-500 font-medium">Trade Management Interface</p>
                  <p className="text-sm text-gray-400">Monitor and manage all active trading positions</p>
                </div>
              </div>
            </div>
          </div>
        );
      case "admin":
        return (
          <div className="fade-in">
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
              <div className="p-6 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-dark">Admin Panel</h3>
              </div>
              <div className="p-6">
                <div className="text-center py-8">
                  <i className="fas fa-users-cog text-4xl text-gray-400 mb-4"></i>
                  <p className="text-gray-500 font-medium">User & Channel Management</p>
                  <p className="text-sm text-gray-400">Manage users, channels, and system configuration</p>
                </div>
              </div>
            </div>
          </div>
        );
      case "logs":
        return (
          <div className="fade-in">
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
              <div className="p-6 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-dark">Logs & Reports</h3>
              </div>
              <div className="p-6">
                <div className="text-center py-8">
                  <i className="fas fa-file-alt text-4xl text-gray-400 mb-4"></i>
                  <p className="text-gray-500 font-medium">System Logs & Analytics</p>
                  <p className="text-sm text-gray-400">Comprehensive logging and performance reports</p>
                </div>
              </div>
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      <Sidebar activeTab={activeTab} onTabChange={handleTabChange} />
      
      <main className="flex-1 overflow-hidden flex flex-col">
        <TopHeader />
        
        <div className="flex-1 overflow-y-auto p-6">
          {renderContent()}
        </div>
      </main>

      <StrategyBuilderModal 
        isOpen={isStrategyModalOpen} 
        onClose={() => setIsStrategyModalOpen(false)} 
      />
    </div>
  );
}
