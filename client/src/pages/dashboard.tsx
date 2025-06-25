import { useState } from "react";
import MainLayout from "@/layouts/MainLayout";
import ModernStatsGrid from "@/components/dashboard/ModernStatsGrid";
import SignalTable from "@/components/tables/SignalTable";
import PerformanceChart from "@/components/charts/PerformanceChart";
import ModernLiveTrades from "@/components/dashboard/ModernLiveTrades";
import DesktopAppStatus from "@/components/desktop/DesktopAppStatus";
import QuickActions from "@/components/dashboard/quick-actions";
import ModernStrategyBuilder from "@/components/modals/ModernStrategyBuilder";

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
          <div className="space-y-8">
            <ModernStatsGrid />
            
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
              <div className="xl:col-span-2">
                <PerformanceChart />
              </div>
              <div className="space-y-6">
                <ModernLiveTrades />
                <DesktopAppStatus />
              </div>
            </div>

            <SignalTable />
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
    <MainLayout>
      <div className="max-w-7xl mx-auto">
        {renderContent()}
      </div>

      <ModernStrategyBuilder 
        isOpen={isStrategyModalOpen} 
        onClose={() => setIsStrategyModalOpen(false)} 
      />
    </MainLayout>
  );
}
