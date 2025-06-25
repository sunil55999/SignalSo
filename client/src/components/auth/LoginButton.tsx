import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import { Loader2, User, Lock } from "lucide-react";

export default function LoginButton() {
  const [isOpen, setIsOpen] = useState(false);
  const [credentials, setCredentials] = useState({ username: "", password: "" });
  const { loginMutation, registerMutation } = useAuth();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await loginMutation.mutateAsync(credentials);
      setIsOpen(false);
      setCredentials({ username: "", password: "" });
    } catch (error) {
      // Error handled by mutation
    }
  };

  const handleQuickLogin = async () => {
    try {
      // Try to login with admin account, or create it if it doesn't exist
      try {
        await loginMutation.mutateAsync({ username: "admin", password: "admin123" });
      } catch (error) {
        // If login fails, try to register admin account
        await registerMutation.mutateAsync({ 
          username: "admin", 
          password: "admin123",
          email: "admin@signalos.com" 
        });
      }
      setIsOpen(false);
    } catch (error) {
      // If both fail, show login form
      setIsOpen(true);
    }
  };

  if (!isOpen) {
    return (
      <div className="fixed top-4 right-4 z-50">
        <Button 
          onClick={handleQuickLogin}
          disabled={loginMutation.isPending || registerMutation.isPending}
          className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700"
        >
          {loginMutation.isPending || registerMutation.isPending ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <User className="w-4 h-4 mr-2" />
          )}
          Quick Login
        </Button>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <Card className="w-full max-w-md mx-4">
        <CardHeader>
          <CardTitle className="text-center">Login to SignalOS</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <Input
                type="text"
                placeholder="Username"
                value={credentials.username}
                onChange={(e) => setCredentials(prev => ({ ...prev, username: e.target.value }))}
                required
              />
            </div>
            <div>
              <Input
                type="password"
                placeholder="Password"
                value={credentials.password}
                onChange={(e) => setCredentials(prev => ({ ...prev, password: e.target.value }))}
                required
              />
            </div>
            <div className="flex space-x-2">
              <Button 
                type="submit" 
                disabled={loginMutation.isPending}
                className="flex-1"
              >
                {loginMutation.isPending ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Lock className="w-4 h-4 mr-2" />
                )}
                Login
              </Button>
              <Button 
                type="button" 
                variant="outline"
                onClick={() => setIsOpen(false)}
              >
                Cancel
              </Button>
            </div>
          </form>
          
          <div className="mt-4 pt-4 border-t">
            <p className="text-sm text-slate-600 text-center mb-2">Quick Demo Access:</p>
            <Button 
              onClick={handleQuickLogin}
              variant="outline"
              className="w-full"
              disabled={loginMutation.isPending || registerMutation.isPending}
            >
              Use Demo Account
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}