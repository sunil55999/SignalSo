import { useState, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { useToast } from '@/hooks/use-toast';
import { apiRequest } from '@/lib/queryClient';
import { 
  Upload, 
  Download, 
  FileText, 
  CheckCircle, 
  XCircle, 
  AlertTriangle,
  Eye,
  Trash2,
  Database,
  FileSpreadsheet,
  Settings
} from 'lucide-react';

export function ImportExportHub() {
  const [activeTab, setActiveTab] = useState<'import' | 'export'>('import');
  const [dragActive, setDragActive] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [previewData, setPreviewData] = useState<any>(null);
  const [importResults, setImportResults] = useState<any>(null);
  const { toast } = useToast();

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      await handleFileUpload(files[0]);
    }
  }, []);

  const handleFileUpload = async (file: File) => {
    setIsUploading(true);
    setUploadProgress(0);
    
    try {
      // Simulate file upload progress
      for (let i = 0; i <= 100; i += 10) {
        setUploadProgress(i);
        await new Promise(resolve => setTimeout(resolve, 100));
      }
      
      // Mock preview data
      const mockPreview = {
        fileName: file.name,
        fileSize: file.size,
        entries: [
          { symbol: 'EURUSD', action: 'BUY', price: 1.0850, tp: 1.0900, sl: 1.0800, valid: true },
          { symbol: 'GBPUSD', action: 'SELL', price: 1.2650, tp: 1.2600, sl: 1.2700, valid: true },
          { symbol: 'INVALID', action: 'BUY', price: 0, tp: 0, sl: 0, valid: false }
        ],
        stats: {
          total: 50,
          valid: 47,
          invalid: 3,
          duplicates: 2
        }
      };
      
      setPreviewData(mockPreview);
      
      toast({
        title: 'File uploaded successfully',
        description: `${mockPreview.stats.valid} valid entries found`,
      });
      
    } catch (error) {
      toast({
        title: 'Upload failed',
        description: 'Failed to process the uploaded file',
        variant: 'destructive',
      });
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const handleImport = async () => {
    if (!previewData) return;
    
    try {
      const response = await apiRequest('/api/import', {
        method: 'POST',
        body: JSON.stringify({
          data: previewData.entries,
          options: {
            skipInvalid: true,
            skipDuplicates: true
          }
        })
      });
      
      setImportResults(response);
      setPreviewData(null);
      
      toast({
        title: 'Import completed',
        description: `${response.items} items imported successfully`,
      });
      
    } catch (error) {
      toast({
        title: 'Import failed',
        description: 'Failed to import data',
        variant: 'destructive',
      });
    }
  };

  const handleExport = async (type: string) => {
    try {
      const response = await apiRequest(`/api/export/${type}`, { method: 'GET' });
      
      // Create downloadable file
      const blob = new Blob([JSON.stringify(response, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${type}-export-${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
      
      toast({
        title: 'Export completed',
        description: `${type} data exported successfully`,
      });
      
    } catch (error) {
      toast({
        title: 'Export failed',
        description: `Failed to export ${type} data`,
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      <div className="flex space-x-2">
        <Button
          variant={activeTab === 'import' ? 'default' : 'outline'}
          onClick={() => setActiveTab('import')}
          className="flex items-center gap-2"
        >
          <Upload className="h-4 w-4" />
          Import Data
        </Button>
        <Button
          variant={activeTab === 'export' ? 'default' : 'outline'}
          onClick={() => setActiveTab('export')}
          className="flex items-center gap-2"
        >
          <Download className="h-4 w-4" />
          Export Data
        </Button>
      </div>

      {/* Import Tab */}
      {activeTab === 'import' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="h-5 w-5" />
                Import Signals & Data
              </CardTitle>
              <CardDescription>
                Drag and drop files or click to upload CSV, JSON, or PDF files
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                  dragActive 
                    ? 'border-primary bg-primary/10' 
                    : 'border-muted-foreground/25 hover:border-muted-foreground/50'
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                {isUploading ? (
                  <div className="space-y-4">
                    <Upload className="h-12 w-12 mx-auto text-muted-foreground animate-bounce" />
                    <div>
                      <p className="text-lg font-medium">Uploading...</p>
                      <Progress value={uploadProgress} className="mt-2" />
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <Upload className="h-12 w-12 mx-auto text-muted-foreground" />
                    <div>
                      <p className="text-lg font-medium">Drop files here or click to browse</p>
                      <p className="text-sm text-muted-foreground">
                        Supported formats: CSV, JSON, PDF
                      </p>
                    </div>
                    <Button variant="outline">
                      <FileText className="h-4 w-4 mr-2" />
                      Select Files
                    </Button>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Preview Panel */}
          {previewData && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Eye className="h-5 w-5" />
                  File Preview
                </CardTitle>
                <CardDescription>
                  Review entries before importing
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">{previewData.fileName}</p>
                      <p className="text-sm text-muted-foreground">
                        {(previewData.fileSize / 1024).toFixed(1)} KB
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Badge variant="outline">
                        {previewData.stats.valid} valid
                      </Badge>
                      <Badge variant="destructive">
                        {previewData.stats.invalid} invalid
                      </Badge>
                      <Badge variant="secondary">
                        {previewData.stats.duplicates} duplicates
                      </Badge>
                    </div>
                  </div>
                  
                  <div className="border rounded-lg overflow-hidden">
                    <div className="bg-muted p-2 text-sm font-medium">
                      Preview ({previewData.entries.length} of {previewData.stats.total} entries)
                    </div>
                    <div className="max-h-64 overflow-y-auto">
                      {previewData.entries.map((entry: any, index: number) => (
                        <div key={index} className={`p-2 border-b flex items-center gap-2 ${
                          !entry.valid ? 'bg-red-50 dark:bg-red-900/20' : ''
                        }`}>
                          {entry.valid ? (
                            <CheckCircle className="h-4 w-4 text-green-600" />
                          ) : (
                            <XCircle className="h-4 w-4 text-red-600" />
                          )}
                          <span className="text-sm">
                            {entry.symbol} {entry.action} @ {entry.price} 
                            (TP: {entry.tp}, SL: {entry.sl})
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                  
                  <div className="flex gap-2">
                    <Button onClick={handleImport} className="flex-1">
                      <Database className="h-4 w-4 mr-2" />
                      Import {previewData.stats.valid} Valid Entries
                    </Button>
                    <Button variant="outline" onClick={() => setPreviewData(null)}>
                      <Trash2 className="h-4 w-4 mr-2" />
                      Cancel
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Import Results */}
          {importResults && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CheckCircle className="h-5 w-5 text-green-600" />
                  Import Results
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <p className="text-sm">
                    <span className="font-medium">Items imported:</span> {importResults.items}
                  </p>
                  {importResults.warnings && importResults.warnings.length > 0 && (
                    <div className="flex items-center gap-2 text-yellow-600">
                      <AlertTriangle className="h-4 w-4" />
                      <span className="text-sm">{importResults.warnings.join(', ')}</span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Export Tab */}
      {activeTab === 'export' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Download className="h-5 w-5" />
                Export Data
              </CardTitle>
              <CardDescription>
                Download your data in various formats
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Button
                  variant="outline"
                  className="h-24 flex flex-col items-center justify-center gap-2"
                  onClick={() => handleExport('signals')}
                >
                  <FileSpreadsheet className="h-8 w-8" />
                  <div className="text-center">
                    <div className="font-medium">Export Signals</div>
                    <div className="text-xs text-muted-foreground">All parsed signals</div>
                  </div>
                </Button>

                <Button
                  variant="outline"
                  className="h-24 flex flex-col items-center justify-center gap-2"
                  onClick={() => handleExport('strategies')}
                >
                  <Settings className="h-8 w-8" />
                  <div className="text-center">
                    <div className="font-medium">Export Strategies</div>
                    <div className="text-xs text-muted-foreground">Trading strategies</div>
                  </div>
                </Button>

                <Button
                  variant="outline"
                  className="h-24 flex flex-col items-center justify-center gap-2"
                  onClick={() => handleExport('providers')}
                >
                  <Database className="h-8 w-8" />
                  <div className="text-center">
                    <div className="font-medium">Export Providers</div>
                    <div className="text-xs text-muted-foreground">Signal providers</div>
                  </div>
                </Button>

                <Button
                  variant="outline"
                  className="h-24 flex flex-col items-center justify-center gap-2"
                  onClick={() => handleExport('logs')}
                >
                  <FileText className="h-8 w-8" />
                  <div className="text-center">
                    <div className="font-medium">Export Logs</div>
                    <div className="text-xs text-muted-foreground">System activity logs</div>
                  </div>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}