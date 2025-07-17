import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { useTheme } from '@/components/theme-provider';
import { 
  Settings, 
  Save, 
  RotateCcw, 
  Database, 
  Shield, 
  Palette, 
  Bell,
  Globe,
  Key,
  Server,
  Eye,
  EyeOff
} from 'lucide-react';

export function SettingsPanel() {
  const { theme, setTheme } = useTheme();
  const { toast } = useToast();
  const [showApiKeys, setShowApiKeys] = useState(false);
  const [settings, setSettings] = useState({
    general: {
      autoStart: true,
      language: 'en',
      theme: theme,
      notifications: true,
      soundAlerts: false,
    },
    trading: {
      riskLevel: 'medium',
      maxPositions: 5,
      autoTrade: false,
      confirmTrades: true,
      defaultLotSize: 0.1,
    },
    api: {
      mt5Server: '192.168.1.100:443',
      mt5Login: '12345678',
      mt5Password: '**********',
      telegramApiId: '**********',
      telegramApiHash: '**********',
    },
    advanced: {
      logLevel: 'info',
      backupEnabled: true,
      backupInterval: 24,
      enableDebug: false,
    },
  });

  const handleSaveSettings = async () => {
    try {
      const response = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });

      const result = await response.json();

      if (result.success) {
        toast({
          title: 'Settings saved',
          description: 'Your settings have been saved successfully',
        });
      } else {
        toast({
          title: 'Save failed',
          description: result.error || 'Failed to save settings',
          variant: 'destructive',
        });
      }
    } catch (error) {
      toast({
        title: 'Save error',
        description: 'An error occurred while saving settings',
        variant: 'destructive',
      });
    }
  };

  const handleResetSettings = () => {
    setSettings({
      general: {
        autoStart: true,
        language: 'en',
        theme: 'light',
        notifications: true,
        soundAlerts: false,
      },
      trading: {
        riskLevel: 'medium',
        maxPositions: 5,
        autoTrade: false,
        confirmTrades: true,
        defaultLotSize: 0.1,
      },
      api: {
        mt5Server: '192.168.1.100:443',
        mt5Login: '12345678',
        mt5Password: '**********',
        telegramApiId: '**********',
        telegramApiHash: '**********',
      },
      advanced: {
        logLevel: 'info',
        backupEnabled: true,
        backupInterval: 24,
        enableDebug: false,
      },
    });

    toast({
      title: 'Settings reset',
      description: 'All settings have been reset to defaults',
    });
  };

  const updateSetting = (category: string, key: string, value: any) => {
    setSettings(prev => ({
      ...prev,
      [category]: {
        ...prev[category as keyof typeof prev],
        [key]: value,
      },
    }));
  };

  const handleThemeChange = (newTheme: 'light' | 'dark') => {
    setTheme(newTheme);
    updateSetting('general', 'theme', newTheme);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Settings</h1>
        <p className="text-gray-600 dark:text-gray-300">
          Configure your SignalOS trading system
        </p>
      </div>

      {/* General Settings */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2 mb-4">
          <Settings className="h-5 w-5 text-gray-600 dark:text-gray-400" />
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">General</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Auto-start on boot
            </label>
            <div className="flex items-center">
              <input
                type="checkbox"
                checked={settings.general.autoStart}
                onChange={(e) => updateSetting('general', 'autoStart', e.target.checked)}
                className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
              />
              <span className="ml-2 text-sm text-gray-600 dark:text-gray-400">
                Start SignalOS automatically when system boots
              </span>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Language
            </label>
            <select
              value={settings.general.language}
              onChange={(e) => updateSetting('general', 'language', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
            >
              <option value="en">English</option>
              <option value="es">Spanish</option>
              <option value="fr">French</option>
              <option value="de">German</option>
              <option value="zh">Chinese</option>
              <option value="ja">Japanese</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Theme
            </label>
            <div className="flex gap-2">
              <Button
                variant={theme === 'light' ? 'default' : 'outline'}
                size="sm"
                onClick={() => handleThemeChange('light')}
              >
                Light
              </Button>
              <Button
                variant={theme === 'dark' ? 'default' : 'outline'}
                size="sm"
                onClick={() => handleThemeChange('dark')}
              >
                Dark
              </Button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Notifications
            </label>
            <div className="space-y-2">
              <div className="flex items-center">
                <input
                  type="checkbox"
                  checked={settings.general.notifications}
                  onChange={(e) => updateSetting('general', 'notifications', e.target.checked)}
                  className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
                />
                <span className="ml-2 text-sm text-gray-600 dark:text-gray-400">
                  Enable notifications
                </span>
              </div>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  checked={settings.general.soundAlerts}
                  onChange={(e) => updateSetting('general', 'soundAlerts', e.target.checked)}
                  className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
                />
                <span className="ml-2 text-sm text-gray-600 dark:text-gray-400">
                  Sound alerts
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Trading Settings */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2 mb-4">
          <Shield className="h-5 w-5 text-gray-600 dark:text-gray-400" />
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Trading</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Risk Level
            </label>
            <select
              value={settings.trading.riskLevel}
              onChange={(e) => updateSetting('trading', 'riskLevel', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Max Positions
            </label>
            <input
              type="number"
              value={settings.trading.maxPositions}
              onChange={(e) => updateSetting('trading', 'maxPositions', parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
              min="1"
              max="20"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Default Lot Size
            </label>
            <input
              type="number"
              value={settings.trading.defaultLotSize}
              onChange={(e) => updateSetting('trading', 'defaultLotSize', parseFloat(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
              min="0.01"
              max="10"
              step="0.01"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Trading Options
            </label>
            <div className="space-y-2">
              <div className="flex items-center">
                <input
                  type="checkbox"
                  checked={settings.trading.autoTrade}
                  onChange={(e) => updateSetting('trading', 'autoTrade', e.target.checked)}
                  className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
                />
                <span className="ml-2 text-sm text-gray-600 dark:text-gray-400">
                  Auto-trade signals
                </span>
              </div>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  checked={settings.trading.confirmTrades}
                  onChange={(e) => updateSetting('trading', 'confirmTrades', e.target.checked)}
                  className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
                />
                <span className="ml-2 text-sm text-gray-600 dark:text-gray-400">
                  Confirm trades before execution
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* API Settings */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Key className="h-5 w-5 text-gray-600 dark:text-gray-400" />
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">API Configuration</h2>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowApiKeys(!showApiKeys)}
          >
            {showApiKeys ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              MT5 Server
            </label>
            <input
              type="text"
              value={settings.api.mt5Server}
              onChange={(e) => updateSetting('api', 'mt5Server', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
              placeholder="192.168.1.100:443"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              MT5 Login
            </label>
            <input
              type="text"
              value={settings.api.mt5Login}
              onChange={(e) => updateSetting('api', 'mt5Login', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
              placeholder="12345678"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              MT5 Password
            </label>
            <input
              type={showApiKeys ? 'text' : 'password'}
              value={settings.api.mt5Password}
              onChange={(e) => updateSetting('api', 'mt5Password', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
              placeholder="Enter MT5 password"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Telegram API ID
            </label>
            <input
              type={showApiKeys ? 'text' : 'password'}
              value={settings.api.telegramApiId}
              onChange={(e) => updateSetting('api', 'telegramApiId', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
              placeholder="Enter Telegram API ID"
            />
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Telegram API Hash
            </label>
            <input
              type={showApiKeys ? 'text' : 'password'}
              value={settings.api.telegramApiHash}
              onChange={(e) => updateSetting('api', 'telegramApiHash', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
              placeholder="Enter Telegram API Hash"
            />
          </div>
        </div>
      </div>

      {/* Advanced Settings */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2 mb-4">
          <Server className="h-5 w-5 text-gray-600 dark:text-gray-400" />
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Advanced</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Log Level
            </label>
            <select
              value={settings.advanced.logLevel}
              onChange={(e) => updateSetting('advanced', 'logLevel', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
            >
              <option value="debug">Debug</option>
              <option value="info">Info</option>
              <option value="warning">Warning</option>
              <option value="error">Error</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Backup Interval (hours)
            </label>
            <input
              type="number"
              value={settings.advanced.backupInterval}
              onChange={(e) => updateSetting('advanced', 'backupInterval', parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
              min="1"
              max="168"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              System Options
            </label>
            <div className="space-y-2">
              <div className="flex items-center">
                <input
                  type="checkbox"
                  checked={settings.advanced.backupEnabled}
                  onChange={(e) => updateSetting('advanced', 'backupEnabled', e.target.checked)}
                  className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
                />
                <span className="ml-2 text-sm text-gray-600 dark:text-gray-400">
                  Enable automatic backups
                </span>
              </div>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  checked={settings.advanced.enableDebug}
                  onChange={(e) => updateSetting('advanced', 'enableDebug', e.target.checked)}
                  className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
                />
                <span className="ml-2 text-sm text-gray-600 dark:text-gray-400">
                  Enable debug mode
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex justify-end gap-4">
        <Button variant="outline" onClick={handleResetSettings}>
          <RotateCcw className="h-4 w-4 mr-2" />
          Reset to Defaults
        </Button>
        <Button onClick={handleSaveSettings}>
          <Save className="h-4 w-4 mr-2" />
          Save Settings
        </Button>
      </div>
    </div>
  );
}