import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Download, TrendingUp, TrendingDown, Activity, Clock, Target, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

interface ProviderStats {
  id: number;
  providerId: string;
  providerName: string;
  totalSignals: number;
  successfulSignals: number;
  winRate: string;
  avgRrRatio: string;
  avgExecutionDelay: number;
  maxDrawdown: string;
  totalProfit: string;
  totalLoss: string;
  avgConfidence: string;
  isActive: boolean;
  lastSignalAt: string | null;
  createdAt: string;
  updatedAt: string;
}

type SortField = 'providerName' | 'winRate' | 'avgRrRatio' | 'totalSignals' | 'avgExecutionDelay' | 'maxDrawdown';
type SortDirection = 'asc' | 'desc';
type ViewMode = 'table' | 'cards';

export default function ProviderCompare() {
  const [sortField, setSortField] = useState<SortField>('winRate');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedProviders, setSelectedProviders] = useState<string[]>([]);
  const [viewMode, setViewMode] = useState<ViewMode>('table');
  const [showActiveOnly, setShowActiveOnly] = useState(true);

  const { data: providers = [], isLoading, error } = useQuery<ProviderStats[]>({
    queryKey: ['/api/provider-stats'],
  });

  const filteredAndSortedProviders = useMemo(() => {
    let filtered = providers;

    // Filter by search term
    if (searchTerm) {
      filtered = filtered.filter(provider =>
        provider.providerName.toLowerCase().includes(searchTerm.toLowerCase()) ||
        provider.providerId.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Filter by active status
    if (showActiveOnly) {
      filtered = filtered.filter(provider => provider.isActive);
    }

    // Sort
    filtered.sort((a, b) => {
      let aValue: any = a[sortField];
      let bValue: any = b[sortField];

      // Convert string numbers to actual numbers for proper sorting
      if (sortField === 'winRate' || sortField === 'avgRrRatio' || sortField === 'maxDrawdown') {
        aValue = parseFloat(aValue) || 0;
        bValue = parseFloat(bValue) || 0;
      }

      if (sortDirection === 'asc') {
        return aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
      } else {
        return aValue > bValue ? -1 : aValue < bValue ? 1 : 0;
      }
    });

    return filtered;
  }, [providers, searchTerm, sortField, sortDirection, showActiveOnly]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const toggleProviderSelection = (providerId: string) => {
    setSelectedProviders(prev =>
      prev.includes(providerId)
        ? prev.filter(id => id !== providerId)
        : [...prev, providerId]
    );
  };

  const getPerformanceColor = (value: number, type: 'winRate' | 'drawdown' | 'ratio') => {
    if (type === 'winRate') {
      if (value >= 70) return 'text-green-600';
      if (value >= 50) return 'text-yellow-600';
      return 'text-red-600';
    }
    if (type === 'drawdown') {
      if (value <= 5) return 'text-green-600';
      if (value <= 15) return 'text-yellow-600';
      return 'text-red-600';
    }
    if (type === 'ratio') {
      if (value >= 2) return 'text-green-600';
      if (value >= 1.5) return 'text-yellow-600';
      return 'text-red-600';
    }
    return '';
  };

  const formatExecutionDelay = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const exportToCSV = () => {
    const csvData = [
      ['Provider Name', 'Win Rate %', 'Avg R:R', 'Total Signals', 'Execution Delay', 'Max Drawdown %', 'Total Profit', 'Active'],
      ...filteredAndSortedProviders.map(provider => [
        provider.providerName,
        provider.winRate,
        provider.avgRrRatio,
        provider.totalSignals.toString(),
        formatExecutionDelay(provider.avgExecutionDelay),
        provider.maxDrawdown,
        provider.totalProfit,
        provider.isActive ? 'Yes' : 'No'
      ])
    ];

    const csvContent = csvData.map(row => row.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'provider-comparison.csv';
    link.click();
    window.URL.revokeObjectURL(url);
  };

  if (isLoading) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto p-6">
        <Card className="border-red-200">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2 text-red-600">
              <AlertTriangle className="h-5 w-5" />
              <span>Failed to load provider statistics</span>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex flex-col space-y-4 sm:flex-row sm:items-center sm:justify-between sm:space-y-0">
        <div>
          <h1 className="text-3xl font-bold">Provider Comparison</h1>
          <p className="text-muted-foreground">
            Compare signal provider performance metrics and statistics
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button onClick={exportToCSV} variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Export CSV
          </Button>
          <Select value={viewMode} onValueChange={(value: ViewMode) => setViewMode(value)}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="table">Table</SelectItem>
              <SelectItem value="cards">Cards</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filters & Search</CardTitle>
          <CardDescription>
            Filter and search providers to find the best performers
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col space-y-4 sm:flex-row sm:items-center sm:space-y-0 sm:space-x-4">
            <div className="flex-1">
              <Input
                placeholder="Search providers..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="max-w-sm"
              />
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox
                id="activeOnly"
                checked={showActiveOnly}
                onCheckedChange={(checked) => setShowActiveOnly(checked as boolean)}
              />
              <label htmlFor="activeOnly" className="text-sm font-medium">
                Active providers only
              </label>
            </div>
            <div className="text-sm text-muted-foreground">
              {filteredAndSortedProviders.length} providers found
            </div>
          </div>
        </CardContent>
      </Card>

      {selectedProviders.length > 0 && (
        <Card className="border-blue-200 bg-blue-50/50">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold">Selected Providers</h3>
                <p className="text-sm text-muted-foreground">
                  {selectedProviders.length} provider(s) selected for comparison
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelectedProviders([])}
              >
                Clear Selection
              </Button>
            </div>
            <div className="flex flex-wrap gap-2 mt-3">
              {selectedProviders.map(providerId => {
                const provider = providers.find(p => p.providerId === providerId);
                return provider ? (
                  <Badge key={providerId} variant="secondary">
                    {provider.providerName}
                  </Badge>
                ) : null;
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {viewMode === 'table' ? (
        <Card>
          <CardHeader>
            <CardTitle>Provider Performance Table</CardTitle>
            <CardDescription>
              Detailed comparison of all provider metrics
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">
                      <Checkbox
                        checked={selectedProviders.length === filteredAndSortedProviders.length}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            setSelectedProviders(filteredAndSortedProviders.map(p => p.providerId));
                          } else {
                            setSelectedProviders([]);
                          }
                        }}
                      />
                    </TableHead>
                    <TableHead>
                      <Button
                        variant="ghost"
                        onClick={() => handleSort('providerName')}
                        className="h-auto p-0 font-semibold"
                      >
                        Provider
                        {sortField === 'providerName' && (
                          sortDirection === 'desc' ? <TrendingDown className="ml-1 h-4 w-4" /> : <TrendingUp className="ml-1 h-4 w-4" />
                        )}
                      </Button>
                    </TableHead>
                    <TableHead>
                      <Button
                        variant="ghost"
                        onClick={() => handleSort('winRate')}
                        className="h-auto p-0 font-semibold"
                      >
                        Win Rate
                        {sortField === 'winRate' && (
                          sortDirection === 'desc' ? <TrendingDown className="ml-1 h-4 w-4" /> : <TrendingUp className="ml-1 h-4 w-4" />
                        )}
                      </Button>
                    </TableHead>
                    <TableHead>
                      <Button
                        variant="ghost"
                        onClick={() => handleSort('avgRrRatio')}
                        className="h-auto p-0 font-semibold"
                      >
                        Avg R:R
                        {sortField === 'avgRrRatio' && (
                          sortDirection === 'desc' ? <TrendingDown className="ml-1 h-4 w-4" /> : <TrendingUp className="ml-1 h-4 w-4" />
                        )}
                      </Button>
                    </TableHead>
                    <TableHead>
                      <Button
                        variant="ghost"
                        onClick={() => handleSort('totalSignals')}
                        className="h-auto p-0 font-semibold"
                      >
                        Signals
                        {sortField === 'totalSignals' && (
                          sortDirection === 'desc' ? <TrendingDown className="ml-1 h-4 w-4" /> : <TrendingUp className="ml-1 h-4 w-4" />
                        )}
                      </Button>
                    </TableHead>
                    <TableHead>
                      <Button
                        variant="ghost"
                        onClick={() => handleSort('avgExecutionDelay')}
                        className="h-auto p-0 font-semibold"
                      >
                        Exec. Speed
                        {sortField === 'avgExecutionDelay' && (
                          sortDirection === 'desc' ? <TrendingDown className="ml-1 h-4 w-4" /> : <TrendingUp className="ml-1 h-4 w-4" />
                        )}
                      </Button>
                    </TableHead>
                    <TableHead>
                      <Button
                        variant="ghost"
                        onClick={() => handleSort('maxDrawdown')}
                        className="h-auto p-0 font-semibold"
                      >
                        Max DD
                        {sortField === 'maxDrawdown' && (
                          sortDirection === 'desc' ? <TrendingDown className="ml-1 h-4 w-4" /> : <TrendingUp className="ml-1 h-4 w-4" />
                        )}
                      </Button>
                    </TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredAndSortedProviders.map((provider) => (
                    <TableRow key={provider.providerId} className="cursor-pointer hover:bg-muted/50">
                      <TableCell>
                        <Checkbox
                          checked={selectedProviders.includes(provider.providerId)}
                          onCheckedChange={() => toggleProviderSelection(provider.providerId)}
                        />
                      </TableCell>
                      <TableCell>
                        <div>
                          <div className="font-medium">{provider.providerName}</div>
                          <div className="text-sm text-muted-foreground">{provider.providerId}</div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className={cn("font-medium", getPerformanceColor(parseFloat(provider.winRate), 'winRate'))}>
                          {parseFloat(provider.winRate).toFixed(1)}%
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className={cn("font-medium", getPerformanceColor(parseFloat(provider.avgRrRatio), 'ratio'))}>
                          {parseFloat(provider.avgRrRatio).toFixed(2)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center space-x-1">
                          <Activity className="h-4 w-4 text-muted-foreground" />
                          <span>{provider.totalSignals}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center space-x-1">
                          <Clock className="h-4 w-4 text-muted-foreground" />
                          <span>{formatExecutionDelay(provider.avgExecutionDelay)}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className={cn("font-medium", getPerformanceColor(parseFloat(provider.maxDrawdown), 'drawdown'))}>
                          {parseFloat(provider.maxDrawdown).toFixed(1)}%
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge variant={provider.isActive ? "default" : "secondary"}>
                          {provider.isActive ? "Active" : "Inactive"}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredAndSortedProviders.map((provider) => (
            <Card key={provider.providerId} className="cursor-pointer hover:shadow-md transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      checked={selectedProviders.includes(provider.providerId)}
                      onCheckedChange={() => toggleProviderSelection(provider.providerId)}
                    />
                    <div>
                      <CardTitle className="text-lg">{provider.providerName}</CardTitle>
                      <CardDescription>{provider.providerId}</CardDescription>
                    </div>
                  </div>
                  <Badge variant={provider.isActive ? "default" : "secondary"}>
                    {provider.isActive ? "Active" : "Inactive"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center">
                    <div className={cn("text-2xl font-bold", getPerformanceColor(parseFloat(provider.winRate), 'winRate'))}>
                      {parseFloat(provider.winRate).toFixed(1)}%
                    </div>
                    <div className="text-sm text-muted-foreground">Win Rate</div>
                  </div>
                  <div className="text-center">
                    <div className={cn("text-2xl font-bold", getPerformanceColor(parseFloat(provider.avgRrRatio), 'ratio'))}>
                      {parseFloat(provider.avgRrRatio).toFixed(2)}
                    </div>
                    <div className="text-sm text-muted-foreground">Avg R:R</div>
                  </div>
                </div>
                
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Total Signals</span>
                    <div className="flex items-center space-x-1">
                      <Activity className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium">{provider.totalSignals}</span>
                    </div>
                  </div>
                  
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Execution Speed</span>
                    <div className="flex items-center space-x-1">
                      <Clock className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium">{formatExecutionDelay(provider.avgExecutionDelay)}</span>
                    </div>
                  </div>
                  
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Max Drawdown</span>
                    <div className="flex items-center space-x-1">
                      <Target className="h-4 w-4 text-muted-foreground" />
                      <span className={cn("font-medium", getPerformanceColor(parseFloat(provider.maxDrawdown), 'drawdown'))}>
                        {parseFloat(provider.maxDrawdown).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                  
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Total Profit</span>
                    <span className="font-medium text-green-600">
                      ${parseFloat(provider.totalProfit).toFixed(2)}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {filteredAndSortedProviders.length === 0 && (
        <Card>
          <CardContent className="pt-6">
            <div className="text-center text-muted-foreground">
              <Activity className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <h3 className="text-lg font-semibold mb-2">No providers found</h3>
              <p>Try adjusting your search terms or filters.</p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}