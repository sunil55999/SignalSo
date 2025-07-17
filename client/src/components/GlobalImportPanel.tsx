import React, { useState } from 'react';
import { Upload, Plus, X, FileText, Settings, Users, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';

export const GlobalImportPanel = ({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) => {
  const [activeTab, setActiveTab] = useState<'import' | 'test' | 'manage'>('import');
  const { toast } = useToast();

  if (!isOpen) return null;

  const handleQuickImport = (type: 'signals' | 'strategies' | 'providers') => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.csv,.json,.pdf';
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        toast({
          title: "Import Started",
          description: `Importing ${type} from ${file.name}`,
        });
        // Handle file import
      }
    };
    input.click();
  };

  const handleQuickTest = (type: 'strategy' | 'connection' | 'parser') => {
    toast({
      title: "Test Started",
      description: `Testing ${type}...`,
    });
    // Handle test
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <Card className="w-full max-w-4xl max-h-[80vh] overflow-y-auto">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Plus className="h-5 w-5" />
            Quick Actions
          </CardTitle>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        
        <CardContent>
          {/* Tab Navigation */}
          <div className="flex gap-2 mb-6">
            <Button
              variant={activeTab === 'import' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setActiveTab('import')}
            >
              <Upload className="h-4 w-4 mr-2" />
              Import
            </Button>
            <Button
              variant={activeTab === 'test' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setActiveTab('test')}
            >
              <Zap className="h-4 w-4 mr-2" />
              Test
            </Button>
            <Button
              variant={activeTab === 'manage' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setActiveTab('manage')}
            >
              <Settings className="h-4 w-4 mr-2" />
              Manage
            </Button>
          </div>

          {/* Import Tab */}
          {activeTab === 'import' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                      onClick={() => handleQuickImport('signals')}>
                  <CardContent className="p-4 text-center">
                    <FileText className="h-8 w-8 mx-auto mb-2 text-blue-600" />
                    <h3 className="font-medium mb-1">Import Signals</h3>
                    <p className="text-sm text-gray-600">CSV, JSON, or PDF files</p>
                    <Badge variant="secondary" className="mt-2">Drag & Drop</Badge>
                  </CardContent>
                </Card>
                
                <Card className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                      onClick={() => handleQuickImport('strategies')}>
                  <CardContent className="p-4 text-center">
                    <Settings className="h-8 w-8 mx-auto mb-2 text-green-600" />
                    <h3 className="font-medium mb-1">Import Strategies</h3>
                    <p className="text-sm text-gray-600">Configuration files</p>
                    <Badge variant="secondary" className="mt-2">Auto-detect</Badge>
                  </CardContent>
                </Card>
                
                <Card className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                      onClick={() => handleQuickImport('providers')}>
                  <CardContent className="p-4 text-center">
                    <Users className="h-8 w-8 mx-auto mb-2 text-purple-600" />
                    <h3 className="font-medium mb-1">Import Providers</h3>
                    <p className="text-sm text-gray-600">Provider configurations</p>
                    <Badge variant="secondary" className="mt-2">Bulk import</Badge>
                  </CardContent>
                </Card>
              </div>
              
              <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
                <h4 className="font-medium mb-2">Quick Import Tips:</h4>
                <ul className="text-sm space-y-1">
                  <li>• Drag files directly onto the cards above</li>
                  <li>• Supported formats: CSV, JSON, PDF</li>
                  <li>• Files are validated before import</li>
                  <li>• Errors and warnings are shown immediately</li>
                </ul>
              </div>
            </div>
          )}

          {/* Test Tab */}
          {activeTab === 'test' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                      onClick={() => handleQuickTest('strategy')}>
                  <CardContent className="p-4 text-center">
                    <Zap className="h-8 w-8 mx-auto mb-2 text-orange-600" />
                    <h3 className="font-medium mb-1">Test Strategy</h3>
                    <p className="text-sm text-gray-600">Backtest with demo data</p>
                    <Badge variant="secondary" className="mt-2">Quick test</Badge>
                  </CardContent>
                </Card>
                
                <Card className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                      onClick={() => handleQuickTest('connection')}>
                  <CardContent className="p-4 text-center">
                    <Users className="h-8 w-8 mx-auto mb-2 text-green-600" />
                    <h3 className="font-medium mb-1">Test Connection</h3>
                    <p className="text-sm text-gray-600">Verify Telegram & MT5</p>
                    <Badge variant="secondary" className="mt-2">Health check</Badge>
                  </CardContent>
                </Card>
                
                <Card className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                      onClick={() => handleQuickTest('parser')}>
                  <CardContent className="p-4 text-center">
                    <FileText className="h-8 w-8 mx-auto mb-2 text-blue-600" />
                    <h3 className="font-medium mb-1">Test Parser</h3>
                    <p className="text-sm text-gray-600">Parse sample signals</p>
                    <Badge variant="secondary" className="mt-2">AI test</Badge>
                  </CardContent>
                </Card>
              </div>
              
              <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg">
                <h4 className="font-medium mb-2">Test Environment:</h4>
                <ul className="text-sm space-y-1">
                  <li>• All tests use safe demo data</li>
                  <li>• No real trades are executed</li>
                  <li>• Results show detailed analysis</li>
                  <li>• Performance metrics included</li>
                </ul>
              </div>
            </div>
          )}

          {/* Manage Tab */}
          {activeTab === 'manage' && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <Button variant="outline" className="h-20 flex-col">
                  <Settings className="h-6 w-6 mb-2" />
                  <span>Manage Strategies</span>
                </Button>
                <Button variant="outline" className="h-20 flex-col">
                  <Users className="h-6 w-6 mb-2" />
                  <span>Manage Providers</span>
                </Button>
                <Button variant="outline" className="h-20 flex-col">
                  <FileText className="h-6 w-6 mb-2" />
                  <span>Signal History</span>
                </Button>
                <Button variant="outline" className="h-20 flex-col">
                  <Zap className="h-6 w-6 mb-2" />
                  <span>System Settings</span>
                </Button>
              </div>
              
              <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
                <h4 className="font-medium mb-2">Recent Activity:</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span>Imported 15 signals</span>
                    <span className="text-gray-500">2 minutes ago</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Updated EUR/USD strategy</span>
                    <span className="text-gray-500">5 minutes ago</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Connected new provider</span>
                    <span className="text-gray-500">1 hour ago</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};