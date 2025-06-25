import MainLayout from "@/layouts/MainLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useAuth } from "@/hooks/use-auth";
import { 
  Settings,
  User,
  Bell,
  Shield,
  Database,
  Save
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";

export default function SettingsPage() {
  const { user, logoutMutation } = useAuth();
  const { toast } = useToast();

  const handleSaveChanges = () => {
    toast({
      title: "Settings Saved",
      description: "Your preferences have been updated successfully"
    });
  };

  const handleNotificationSettings = () => {
    toast({
      title: "Notifications",
      description: "Opening notification preferences"
    });
  };

  const handleSecuritySettings = () => {
    toast({
      title: "Security",
      description: "Opening security configuration"
    });
  };

  const handleDataManagement = () => {
    toast({
      title: "Data Management",
      description: "Opening data export and backup options"
    });
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Settings
            </h1>
            <p className="text-slate-600 dark:text-slate-400 mt-1">
              Configure your account and application preferences
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Account Settings */}
          <Card className="shadow-lg border-0 lg:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <User className="w-5 h-5" />
                <span>Account Settings</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="username">Username</Label>
                  <Input id="username" value={user?.username || ""} disabled />
                </div>
                <div>
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" value={user?.email || ""} placeholder="Enter email" />
                </div>
              </div>
              
              <div>
                <Label htmlFor="role">Account Type</Label>
                <Input id="role" value={user?.role || "user"} disabled />
              </div>

              <div className="flex items-center justify-between pt-4 border-t">
                <div>
                  <h4 className="font-medium">Notifications</h4>
                  <p className="text-sm text-slate-600">Receive alerts for important events</p>
                </div>
                <Switch defaultChecked />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium">Auto Trading</h4>
                  <p className="text-sm text-slate-600">Enable automatic trade execution</p>
                </div>
                <Switch defaultChecked />
              </div>

              <div className="flex justify-between pt-4">
                <Button variant="outline" onClick={() => logoutMutation.mutate()}>
                  Logout
                </Button>
                <Button onClick={handleSaveChanges}>
                  <Save className="w-4 h-4 mr-2" />
                  Save Changes
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <div className="space-y-6">
            <Card className="shadow-lg border-0">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Settings className="w-5 h-5" />
                  <span>Quick Actions</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button variant="outline" className="w-full justify-start" onClick={handleNotificationSettings}>
                  <Bell className="w-4 h-4 mr-2" />
                  Notification Settings
                </Button>
                <Button variant="outline" className="w-full justify-start" onClick={handleSecuritySettings}>
                  <Shield className="w-4 h-4 mr-2" />
                  Security Settings
                </Button>
                <Button variant="outline" className="w-full justify-start" onClick={handleDataManagement}>
                  <Database className="w-4 h-4 mr-2" />
                  Data Management
                </Button>
              </CardContent>
            </Card>

            <Card className="shadow-lg border-0">
              <CardHeader>
                <CardTitle>System Status</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Database</span>
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-emerald-500 rounded-full"></div>
                      <span className="text-xs text-emerald-600">Connected</span>
                    </div>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm">API Server</span>
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-emerald-500 rounded-full"></div>
                      <span className="text-xs text-emerald-600">Online</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}