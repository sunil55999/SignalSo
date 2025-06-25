import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Database, Loader2, CheckCircle } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { queryClient } from "@/lib/queryClient";

export default function SampleDataButton() {
  const [isLoading, setIsLoading] = useState(false);
  const [isCreated, setIsCreated] = useState(false);
  const { toast } = useToast();

  const createSampleData = async () => {
    setIsLoading(true);
    try {
      const response = await fetch("/api/sample-data", {
        method: "POST",
        credentials: "include"
      });

      if (response.ok) {
        const result = await response.json();
        setIsCreated(true);
        
        // Invalidate queries to refresh data
        queryClient.invalidateQueries({ queryKey: ["/api/dashboard/stats"] });
        queryClient.invalidateQueries({ queryKey: ["/api/signals"] });
        queryClient.invalidateQueries({ queryKey: ["/api/trades/live"] });
        queryClient.invalidateQueries({ queryKey: ["/api/providers/stats"] });
        
        toast({
          title: "Sample Data Created",
          description: `Created ${result.data.signals} signals and ${result.data.trades} trades`,
        });
        
        // Reset button state after 3 seconds
        setTimeout(() => setIsCreated(false), 3000);
      } else {
        throw new Error("Failed to create sample data");
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to create sample data",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  if (isCreated) {
    return (
      <Button variant="outline" disabled className="w-full">
        <CheckCircle className="w-4 h-4 mr-2 text-green-600" />
        Sample Data Created
      </Button>
    );
  }

  return (
    <Button 
      onClick={createSampleData} 
      disabled={isLoading}
      variant="outline"
      className="w-full"
    >
      {isLoading ? (
        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
      ) : (
        <Database className="w-4 h-4 mr-2" />
      )}
      {isLoading ? "Creating..." : "Load Sample Data"}
    </Button>
  );
}