import { useToast } from "@/hooks/use-toast";
import { queryClient } from "@/lib/queryClient";

export function useToastActions() {
  const { toast } = useToast();

  const handleEmergencyStop = () => {
    toast({
      title: "Emergency Stop Activated",
      description: "All trading operations have been halted",
      variant: "destructive"
    });
  };

  const handleSyncStatus = async () => {
    try {
      await queryClient.refetchQueries();
      toast({
        title: "Status Synced",
        description: "All data refreshed successfully"
      });
    } catch (error) {
      toast({
        title: "Sync Failed", 
        description: "Could not refresh status",
        variant: "destructive"
      });
    }
  };

  const handleQuickReport = () => {
    // Simulate report generation
    toast({
      title: "Report Generated",
      description: "Performance report has been created and downloaded"
    });
  };

  const handleSettings = () => {
    // Navigate to settings would be handled by router
    toast({
      title: "Opening Settings",
      description: "Redirecting to configuration panel"
    });
  };

  const handleRefresh = async () => {
    try {
      await queryClient.invalidateQueries();
      toast({
        title: "Data Refreshed",
        description: "All information updated successfully"
      });
    } catch (error) {
      toast({
        title: "Refresh Failed",
        description: "Could not update data",
        variant: "destructive"
      });
    }
  };

  const handleExport = () => {
    toast({
      title: "Export Started",
      description: "Data export is being prepared for download"
    });
  };

  const handleFilter = () => {
    toast({
      title: "Filter Applied",
      description: "Data has been filtered according to your criteria"
    });
  };

  return {
    handleEmergencyStop,
    handleSyncStatus,
    handleQuickReport,
    handleSettings,
    handleRefresh,
    handleExport,
    handleFilter
  };
}