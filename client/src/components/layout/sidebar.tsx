import { Link, useLocation } from 'wouter';
import { 
  Home, 
  Settings, 
  Activity, 
  TrendingUp, 
  Users, 
  MessageCircle,
  FileText,
  CheckSquare
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

const navItems = [
  { path: '/', icon: Home, label: 'Dashboard' },
  { path: '/channels/setup', icon: MessageCircle, label: 'Channels' },
  { path: '/signals/validator', icon: CheckSquare, label: 'Validator' },
  { path: '/logs', icon: FileText, label: 'Logs' },
  { path: '/strategy/backtest', icon: TrendingUp, label: 'Backtest' },
  { path: '/settings', icon: Settings, label: 'Settings' },
];

export function Sidebar() {
  const [location] = useLocation();

  return (
    <div className="w-64 bg-card border-r border-border">
      <div className="p-6">
        <div className="flex items-center gap-2 mb-8">
          <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
            <Activity className="h-4 w-4 text-primary-foreground" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">SignalOS</h2>
            <p className="text-xs text-muted-foreground">Desktop Trading</p>
          </div>
        </div>
        
        <nav className="space-y-2">
          {navItems.map((item) => (
            <Link key={item.path} href={item.path}>
              <Button
                variant={location === item.path ? 'default' : 'ghost'}
                className={cn(
                  "w-full justify-start",
                  location === item.path && "bg-primary text-primary-foreground"
                )}
              >
                <item.icon className="h-4 w-4 mr-2" />
                {item.label}
              </Button>
            </Link>
          ))}
        </nav>
      </div>
    </div>
  );
}