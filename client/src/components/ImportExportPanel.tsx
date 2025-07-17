import React, { useState, useRef } from 'react';
import { Upload, Download, FileText, Users, Settings, AlertCircle, CheckCircle, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { useToast } from '@/hooks/use-toast';
import { apiRequest } from '@/lib/queryClient';

interface ImportResult {
  success: boolean;
  message: string;
  items?: number;
  errors?: string[];
  warnings?: string[];
}

export const ImportExportPanel = () => {
  const [isImporting, setIsImporting] = useState(false);
  const [importProgress, setImportProgress] = useState(0);
  const [importResults, setImportResults] = useState<ImportResult[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  const handleFileUpload = async (files: FileList) => {
    setIsImporting(true);
    setImportProgress(0);
    setImportResults([]);

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        setImportProgress((i / files.length) * 100);

        const formData = new FormData();
        formData.append('file', file);

        const response = await apiRequest('/api/import', {
          method: 'POST',
          body: formData,
        });

        const result: ImportResult = {
          success: response.success,
          message: response.message || `Imported ${file.name}`,
          items: response.items || 0,
          errors: response.errors || [],
          warnings: response.warnings || []
        };

        setImportResults(prev => [...prev, result]);
      }

      setImportProgress(100);
      
      toast({
        title: "Import Complete",
        description: `Successfully processed ${files.length} file(s)`,
      });
    } catch (error) {
      toast({
        title: "Import Failed",
        description: error instanceof Error ? error.message : "Failed to import files",
        variant: "destructive",
      });
    } finally {
      setIsImporting(false);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileUpload(e.target.files);
    }
  };

  const handleExport = async (type: 'signals' | 'strategies' | 'providers') => {
    try {
      const response = await apiRequest(`/api/export/${type}`, {
        method: 'GET',
      });

      // Create and download file
      const blob = new Blob([JSON.stringify(response, null, 2)], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${type}_export_${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      toast({
        title: "Export Complete",
        description: `${type} exported successfully`,
      });
    } catch (error) {
      toast({
        title: "Export Failed",
        description: error instanceof Error ? error.message : "Failed to export data",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6">
      {/* Import Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5" />
            Import Data
          </CardTitle>
          <CardDescription>
            Import signals, strategies, and providers from CSV, JSON, or PDF files
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              dragActive
                ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                : 'border-gray-300 hover:border-gray-400'
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
            <p className="text-lg font-medium mb-2">
              Drag and drop files here, or click to select
            </p>
            <p className="text-sm text-gray-500 mb-4">
              Supports CSV, JSON, and PDF files up to 10MB each
            </p>
            <Button
              onClick={() => fileInputRef.current?.click()}
              disabled={isImporting}
              className="mb-4"
            >
              {isImporting ? 'Importing...' : 'Select Files'}
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".csv,.json,.pdf"
              onChange={handleFileSelect}
              className="hidden"
            />
          </div>

          {/* Import Progress */}
          {isImporting && (
            <div className="mt-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Importing files...</span>
                <span className="text-sm text-gray-500">{Math.round(importProgress)}%</span>
              </div>
              <Progress value={importProgress} className="w-full" />
            </div>
          )}

          {/* Import Results */}
          {importResults.length > 0 && (
            <div className="mt-4 space-y-2">
              <h4 className="font-medium">Import Results:</h4>
              {importResults.map((result, index) => (
                <div
                  key={index}
                  className={`p-3 rounded-md border ${
                    result.success
                      ? 'border-green-200 bg-green-50 dark:bg-green-900/20'
                      : 'border-red-200 bg-red-50 dark:bg-red-900/20'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {result.success ? (
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    ) : (
                      <AlertCircle className="h-4 w-4 text-red-600" />
                    )}
                    <span className="text-sm font-medium">{result.message}</span>
                    {result.items && (
                      <Badge variant="secondary">{result.items} items</Badge>
                    )}
                  </div>
                  {result.errors && result.errors.length > 0 && (
                    <div className="mt-2">
                      <p className="text-xs text-red-600 font-medium">Errors:</p>
                      <ul className="text-xs text-red-600 list-disc list-inside">
                        {result.errors.map((error, i) => (
                          <li key={i}>{error}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {result.warnings && result.warnings.length > 0 && (
                    <div className="mt-2">
                      <p className="text-xs text-yellow-600 font-medium">Warnings:</p>
                      <ul className="text-xs text-yellow-600 list-disc list-inside">
                        {result.warnings.map((warning, i) => (
                          <li key={i}>{warning}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Export Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Download className="h-5 w-5" />
            Export Data
          </CardTitle>
          <CardDescription>
            Export your data for backup or migration
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Button
              variant="outline"
              onClick={() => handleExport('signals')}
              className="flex items-center gap-2"
            >
              <FileText className="h-4 w-4" />
              Export Signals
            </Button>
            <Button
              variant="outline"
              onClick={() => handleExport('strategies')}
              className="flex items-center gap-2"
            >
              <Settings className="h-4 w-4" />
              Export Strategies
            </Button>
            <Button
              variant="outline"
              onClick={() => handleExport('providers')}
              className="flex items-center gap-2"
            >
              <Users className="h-4 w-4" />
              Export Providers
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>
            Common tasks after importing data
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Button variant="outline" size="sm">
              Backtest Strategy
            </Button>
            <Button variant="outline" size="sm">
              Assign Provider
            </Button>
            <Button variant="outline" size="sm">
              Test Connection
            </Button>
            <Button variant="outline" size="sm">
              View Reports
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};