import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Home, 
  Upload, 
  Download, 
  Settings, 
  Activity, 
  TrendingUp, 
  Users, 
  MessageCircle,
  FileText,
  Target,
  BarChart3,
  Zap,
  Database,
  TestTube,
  Eye,
  ChevronRight,
  ChevronDown,
  Play
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface SidebarProps {
  activeSection: string;
  onSectionChange: (section: string) => void;
}

export function RedesignedSidebar({ activeSection, onSectionChange }: SidebarProps) {
  const [expandedGroups, setExpandedGroups] = useState<string[]>(['core', 'management']);

  const toggleGroup = (groupId: string) => {
    setExpandedGroups(prev => 
      prev.includes(groupId) 
        ? prev.filter(id => id !== groupId)
        : [...prev, groupId]
    );
  };

  const menuGroups = [
    {
      id: 'core',
      title: 'Core Functions',
      items: [
        { id: 'dashboard', icon: Home, label: 'Dashboard', badge: null },
        { id: 'import', icon: Upload, label: 'Import/Export', badge: null },
        { id: 'signals', icon: MessageCircle, label: 'Signal Parser', badge: '2' },
        { id: 'trades', icon: TrendingUp, label: 'Active Trades', badge: '5' },
      ]
    },
    {
      id: 'management',
      title: 'Management',
      items: [
        { id: 'providers', icon: Users, label: 'Signal Providers', badge: null },
        { id: 'strategies', icon: Target, label: 'Strategy Builder', badge: null },
        { id: 'backtest', icon: BarChart3, label: 'Backtesting', badge: null },
      ]
    },
    {
      id: 'monitoring',
      title: 'Monitoring & Logs',
      items: [
        { id: 'logs', icon: FileText, label: 'System Logs', badge: null },
        { id: 'activity', icon: Activity, label: 'Activity Center', badge: '12' },
        { id: 'health', icon: Zap, label: 'System Health', badge: null },
      ]
    },
    {
      id: 'tools',
      title: 'Tools & Testing',
      items: [
        { id: 'validator', icon: Eye, label: 'Signal Validator', badge: null },
        { id: 'tester', icon: TestTube, label: 'Signal Tester', badge: null },
        { id: 'database', icon: Database, label: 'Data Manager', badge: null },
      ]
    },
    {
      id: 'settings',
      title: 'Configuration',
      items: [
        { id: 'settings', icon: Settings, label: 'Settings', badge: null },
      ]
    }
  ];

  return (
    <div className="w-64 bg-card border-r border-border h-full overflow-y-auto">
      <div className="p-4">
        {/* Quick Stats */}
        <div className="mb-6 p-4 rounded-lg bg-gradient-to-br from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20">
          <div className="text-sm font-medium text-foreground mb-2">System Status</div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <div className="text-green-600 font-medium">Router</div>
              <div className="text-muted-foreground">Online</div>
            </div>
            <div>
              <div className="text-blue-600 font-medium">MT5</div>
              <div className="text-muted-foreground">Connected</div>
            </div>
            <div>
              <div className="text-purple-600 font-medium">Telegram</div>
              <div className="text-muted-foreground">Active</div>
            </div>
            <div>
              <div className="text-orange-600 font-medium">Signals</div>
              <div className="text-muted-foreground">Running</div>
            </div>
          </div>
        </div>

        {/* Navigation Menu */}
        <nav className="space-y-2">
          {menuGroups.map((group) => (
            <div key={group.id} className="space-y-1">
              <Button
                variant="ghost"
                className="w-full justify-start p-2 h-auto text-xs font-medium text-muted-foreground hover:text-foreground"
                onClick={() => toggleGroup(group.id)}
              >
                <div className="flex items-center justify-between w-full">
                  <span className="uppercase tracking-wider">{group.title}</span>
                  {expandedGroups.includes(group.id) ? (
                    <ChevronDown className="h-3 w-3" />
                  ) : (
                    <ChevronRight className="h-3 w-3" />
                  )}
                </div>
              </Button>
              
              {expandedGroups.includes(group.id) && (
                <div className="pl-2 space-y-1">
                  {group.items.map((item) => (
                    <Button
                      key={item.id}
                      variant={activeSection === item.id ? 'default' : 'ghost'}
                      className={cn(
                        "w-full justify-start gap-3 h-10",
                        activeSection === item.id && "bg-primary text-primary-foreground"
                      )}
                      onClick={() => onSectionChange(item.id)}
                    >
                      <item.icon className="h-4 w-4" />
                      <span className="flex-1 text-left">{item.label}</span>
                      {item.badge && (
                        <Badge variant="secondary" className="h-5 px-2 text-xs">
                          {item.badge}
                        </Badge>
                      )}
                    </Button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </nav>

        {/* Quick Actions */}
        <div className="mt-6 p-4 rounded-lg bg-muted/50">
          <div className="text-sm font-medium mb-3">Quick Actions</div>
          <div className="space-y-2">
            <Button size="sm" className="w-full justify-start gap-2">
              <Play className="h-3 w-3" />
              Start Router
            </Button>
            <Button size="sm" variant="outline" className="w-full justify-start gap-2">
              <Upload className="h-3 w-3" />
              Import Data
            </Button>
            <Button size="sm" variant="outline" className="w-full justify-start gap-2">
              <TestTube className="h-3 w-3" />
              Test Signal
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}