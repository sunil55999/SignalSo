import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { 
  MessageSquare, 
  Plus, 
  Trash2, 
  CheckCircle, 
  AlertCircle,
  Settings,
  Eye,
  EyeOff,
  Hash
} from 'lucide-react';

export function ChannelSetup() {
  const [telegramConfig, setTelegramConfig] = useState({
    apiId: '',
    apiHash: '',
    phoneNumber: '',
  });
  const [channels, setChannels] = useState([
    { id: '1', name: 'Premium Signals', telegramId: '@premium_signals', isActive: true },
    { id: '2', name: 'Forex Alpha', telegramId: '@forex_alpha', isActive: false },
  ]);
  const [showApiHash, setShowApiHash] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [newChannelId, setNewChannelId] = useState('');
  const { toast } = useToast();

  const handleTelegramLogin = async () => {
    setIsConnecting(true);
    try {
      const response = await fetch('/api/telegram/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(telegramConfig),
      });
      
      const result = await response.json();
      
      if (result.success) {
        toast({
          title: 'Telegram connected successfully',
          description: 'You can now add channels to monitor',
        });
      } else {
        toast({
          title: 'Connection failed',
          description: result.error || 'Failed to connect to Telegram',
          variant: 'destructive',
        });
      }
    } catch (error) {
      toast({
        title: 'Connection error',
        description: 'An error occurred while connecting to Telegram',
        variant: 'destructive',
      });
    } finally {
      setIsConnecting(false);
    }
  };

  const handleAddChannel = () => {
    if (!newChannelId.trim()) return;
    
    const newChannel = {
      id: Date.now().toString(),
      name: newChannelId.replace('@', ''),
      telegramId: newChannelId.startsWith('@') ? newChannelId : `@${newChannelId}`,
      isActive: true,
    };
    
    setChannels([...channels, newChannel]);
    setNewChannelId('');
    
    toast({
      title: 'Channel added',
      description: `Channel ${newChannel.telegramId} has been added to monitoring`,
    });
  };

  const handleRemoveChannel = (channelId: string) => {
    setChannels(channels.filter(channel => channel.id !== channelId));
    toast({
      title: 'Channel removed',
      description: 'Channel has been removed from monitoring',
    });
  };

  const toggleChannelStatus = (channelId: string) => {
    setChannels(channels.map(channel => 
      channel.id === channelId 
        ? { ...channel, isActive: !channel.isActive }
        : channel
    ));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Channel Setup</h1>
        <p className="text-gray-600 dark:text-gray-300">
          Configure Telegram channels for signal monitoring
        </p>
      </div>

      {/* Telegram Configuration */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Telegram Configuration
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              API ID
            </label>
            <input
              type="text"
              value={telegramConfig.apiId}
              onChange={(e) => setTelegramConfig({ ...telegramConfig, apiId: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
              placeholder="Enter your Telegram API ID"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              API Hash
            </label>
            <div className="relative">
              <input
                type={showApiHash ? 'text' : 'password'}
                value={telegramConfig.apiHash}
                onChange={(e) => setTelegramConfig({ ...telegramConfig, apiHash: e.target.value })}
                className="w-full px-3 py-2 pr-10 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                placeholder="Enter your Telegram API Hash"
              />
              <button
                type="button"
                onClick={() => setShowApiHash(!showApiHash)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                {showApiHash ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Phone Number
          </label>
          <input
            type="text"
            value={telegramConfig.phoneNumber}
            onChange={(e) => setTelegramConfig({ ...telegramConfig, phoneNumber: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
            placeholder="+1234567890"
          />
        </div>

        <Button 
          onClick={handleTelegramLogin}
          disabled={isConnecting || !telegramConfig.apiId || !telegramConfig.apiHash || !telegramConfig.phoneNumber}
          className="w-full md:w-auto"
        >
          {isConnecting ? 'Connecting...' : 'Connect to Telegram'}
        </Button>
      </div>

      {/* Channel Management */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Monitored Channels
        </h2>

        {/* Add Channel */}
        <div className="flex gap-2 mb-6">
          <div className="flex-1">
            <input
              type="text"
              value={newChannelId}
              onChange={(e) => setNewChannelId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
              placeholder="@channel_username or channel ID"
            />
          </div>
          <Button 
            onClick={handleAddChannel}
            disabled={!newChannelId.trim()}
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Channel
          </Button>
        </div>

        {/* Channel List */}
        <div className="space-y-3">
          {channels.map((channel) => (
            <div 
              key={channel.id}
              className="flex items-center justify-between p-4 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700"
            >
              <div className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${channel.isActive ? 'bg-green-500' : 'bg-gray-400'}`} />
                <div>
                  <h3 className="font-medium text-gray-900 dark:text-white">{channel.name}</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">{channel.telegramId}</p>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => toggleChannelStatus(channel.id)}
                >
                  {channel.isActive ? (
                    <CheckCircle className="h-4 w-4 text-green-600" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-gray-400" />
                  )}
                </Button>
                
                <Button
                  variant="ghost"
                  size="sm"
                >
                  <Settings className="h-4 w-4" />
                </Button>
                
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleRemoveChannel(channel.id)}
                >
                  <Trash2 className="h-4 w-4 text-red-600" />
                </Button>
              </div>
            </div>
          ))}
        </div>

        {channels.length === 0 && (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            <MessageSquare className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No channels configured yet</p>
            <p className="text-sm">Add your first Telegram channel to start monitoring signals</p>
          </div>
        )}
      </div>

      {/* Channel Configuration Help */}
      <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-6 border border-blue-200 dark:border-blue-800">
        <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">
          Setting up Telegram API
        </h3>
        <div className="text-sm text-blue-800 dark:text-blue-200 space-y-2">
          <p>1. Visit <a href="https://my.telegram.org" className="underline" target="_blank" rel="noopener noreferrer">my.telegram.org</a> and log in</p>
          <p>2. Go to "API Development Tools" and create a new application</p>
          <p>3. Copy your API ID and API Hash from the application settings</p>
          <p>4. Enter your phone number in international format (+1234567890)</p>
        </div>
      </div>
    </div>
  );
}