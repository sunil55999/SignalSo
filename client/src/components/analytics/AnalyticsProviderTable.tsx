/**
 * AnalyticsProviderTable Component
 * Displays performance statistics for all signal providers in a sortable and filterable table
 */

import React, { useState, useMemo, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Download,
  Filter,
  Search,
  TrendingUp,
  TrendingDown,
  Minus,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ProviderStats {
  id: string;
  name: string;
  totalSignals: number;
  executedSignals: number;
  winCount: number;
  lossCount: number;
  winRate: number;
  averageRR: number;
  maxDrawdown: number;
  totalPnL: number;
  lastSignalDate: string;
  performanceGrade: 'A' | 'B' | 'C' | 'D' | 'F';
  isActive: boolean;
  avgExecutionTime?: number;
  avgHoldTime?: number;
}

type SortField = keyof ProviderStats;
type SortDirection = 'asc' | 'desc';

interface SortConfig {
  field: SortField;
  direction: SortDirection;
}

interface FilterConfig {
  search: string;
  minWinRate: number;
  minSignals: number;
  performanceGrade: string;
  activeOnly: boolean;
}

const DEFAULT_FILTERS: FilterConfig = {
  search: '',
  minWinRate: 0,
  minSignals: 0,
  performanceGrade: 'all',
  activeOnly: false,
};

const PERFORMANCE_COLORS = {
  A: 'bg-green-100 text-green-800 border-green-300',
  B: 'bg-blue-100 text-blue-800 border-blue-300',
  C: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  D: 'bg-orange-100 text-orange-800 border-orange-300',
  F: 'bg-red-100 text-red-800 border-red-300',
};

const WIN_RATE_COLORS = {
  excellent: 'text-green-600 font-semibold', // > 75%
  good: 'text-blue-600', // 60-75%
  average: 'text-yellow-600', // 45-60%
  poor: 'text-red-600', // < 45%
};

export function AnalyticsProviderTable() {
  const [sortConfig, setSortConfig] = useState<SortConfig>({
    field: 'winRate',
    direction: 'desc',
  });
  const [filters, setFilters] = useState<FilterConfig>(DEFAULT_FILTERS);

  // Fetch provider statistics from API
  const {
    data: providers,
    isLoading,
    error,
    refetch,
  } = useQuery<ProviderStats[]>({
    queryKey: ['providerStats'],
    queryFn: async () => {
      const response = await fetch('/api/providers/stats');
      if (!response.ok) {
        throw new Error('Failed to fetch provider statistics');
      }
      return response.json();
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 30 * 1000, // Refresh every 30 seconds
  });

  // Sort and filter providers
  const filteredAndSortedProviders = useMemo(() => {
    if (!providers) return [];

    let filtered = providers.filter((provider) => {
      // Search filter
      if (filters.search) {
        const searchLower = filters.search.toLowerCase();
        const matchesSearch = provider.name.toLowerCase().includes(searchLower) ||
          provider.id.toLowerCase().includes(searchLower);
        if (!matchesSearch) return false;
      }

      // Win rate filter
      if (provider.winRate < filters.minWinRate) return false;

      // Minimum signals filter
      if (provider.totalSignals < filters.minSignals) return false;

      // Performance grade filter
      if (filters.performanceGrade !== 'all' && 
          provider.performanceGrade !== filters.performanceGrade) return false;

      // Active only filter
      if (filters.activeOnly && !provider.isActive) return false;

      return true;
    });

    // Sort the filtered results
    filtered.sort((a, b) => {
      const aValue = a[sortConfig.field];
      const bValue = b[sortConfig.field];

      if (aValue === null || aValue === undefined) return 1;
      if (bValue === null || bValue === undefined) return -1;

      let comparison = 0;
      if (typeof aValue === 'string' && typeof bValue === 'string') {
        comparison = aValue.localeCompare(bValue);
      } else if (typeof aValue === 'number' && typeof bValue === 'number') {
        comparison = aValue - bValue;
      } else if (aValue instanceof Date && bValue instanceof Date) {
        comparison = aValue.getTime() - bValue.getTime();
      }

      return sortConfig.direction === 'asc' ? comparison : -comparison;
    });

    return filtered;
  }, [providers, sortConfig, filters]);

  // Handle sorting
  const handleSort = useCallback((field: SortField) => {
    setSortConfig((prev) => ({
      field,
      direction: prev.field === field && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  }, []);

  // Handle filter changes
  const updateFilter = useCallback((key: keyof FilterConfig, value: any) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }, []);

  // Clear all filters
  const clearFilters = useCallback(() => {
    setFilters(DEFAULT_FILTERS);
  }, []);

  // Export to CSV
  const exportToCSV = useCallback(() => {
    if (!filteredAndSortedProviders.length) return;

    const headers = [
      'Provider Name',
      'Total Signals',
      'Executed Signals',
      'Win Rate (%)',
      'Average R:R',
      'Max Drawdown',
      'Total P&L',
      'Last Signal Date',
      'Performance Grade',
      'Status',
    ];

    const csvData = filteredAndSortedProviders.map((provider) => [
      provider.name,
      provider.totalSignals,
      provider.executedSignals,
      provider.winRate.toFixed(2),
      provider.averageRR.toFixed(2),
      provider.maxDrawdown.toFixed(2),
      provider.totalPnL.toFixed(2),
      new Date(provider.lastSignalDate).toLocaleDateString(),
      provider.performanceGrade,
      provider.isActive ? 'Active' : 'Inactive',
    ]);

    const csv = [headers, ...csvData].map((row) => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `provider-analytics-${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [filteredAndSortedProviders]);

  // Get win rate color class
  const getWinRateColor = (winRate: number): string => {
    if (winRate > 75) return WIN_RATE_COLORS.excellent;
    if (winRate >= 60) return WIN_RATE_COLORS.good;
    if (winRate >= 45) return WIN_RATE_COLORS.average;
    return WIN_RATE_COLORS.poor;
  };

  // Get trend icon based on win rate
  const getTrendIcon = (winRate: number) => {
    if (winRate > 75) return <TrendingUp className="h-4 w-4 text-green-500" />;
    if (winRate >= 45) return <Minus className="h-4 w-4 text-yellow-500" />;
    return <TrendingDown className="h-4 w-4 text-red-500" />;
  };

  // Render sort icon
  const renderSortIcon = (field: SortField) => {
    if (sortConfig.field !== field) {
      return <ArrowUpDown className="h-4 w-4" />;
    }
    return sortConfig.direction === 'asc' ? 
      <ArrowUp className="h-4 w-4" /> : 
      <ArrowDown className="h-4 w-4" />;
  };

  if (error) {
    return (
      <Alert className="border-red-200 bg-red-50">
        <AlertDescription>
          Failed to load provider statistics. Please try again later.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Provider Analytics</CardTitle>
            <CardDescription>
              Performance statistics for all signal providers
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={exportToCSV}
              disabled={!filteredAndSortedProviders.length}
            >
              <Download className="h-4 w-4 mr-2" />
              Export CSV
            </Button>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              Refresh
            </Button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-4 pt-4">
          <div className="flex items-center gap-2">
            <Search className="h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search providers..."
              value={filters.search}
              onChange={(e) => updateFilter('search', e.target.value)}
              className="w-48"
            />
          </div>

          <Select
            value={filters.minWinRate.toString()}
            onValueChange={(value) => updateFilter('minWinRate', parseInt(value))}
          >
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Min Win Rate" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="0">All Win Rates</SelectItem>
              <SelectItem value="50">50%+ Win Rate</SelectItem>
              <SelectItem value="60">60%+ Win Rate</SelectItem>
              <SelectItem value="70">70%+ Win Rate</SelectItem>
              <SelectItem value="80">80%+ Win Rate</SelectItem>
            </SelectContent>
          </Select>

          <Select
            value={filters.performanceGrade}
            onValueChange={(value) => updateFilter('performanceGrade', value)}
          >
            <SelectTrigger className="w-32">
              <SelectValue placeholder="Grade" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Grades</SelectItem>
              <SelectItem value="A">Grade A</SelectItem>
              <SelectItem value="B">Grade B</SelectItem>
              <SelectItem value="C">Grade C</SelectItem>
              <SelectItem value="D">Grade D</SelectItem>
              <SelectItem value="F">Grade F</SelectItem>
            </SelectContent>
          </Select>

          <Button
            variant="outline"
            size="sm"
            onClick={clearFilters}
            disabled={JSON.stringify(filters) === JSON.stringify(DEFAULT_FILTERS)}
          >
            <Filter className="h-4 w-4 mr-2" />
            Clear Filters
          </Button>
        </div>

        {filteredAndSortedProviders.length > 0 && (
          <div className="text-sm text-muted-foreground">
            Showing {filteredAndSortedProviders.length} of {providers?.length || 0} providers
          </div>
        )}
      </CardHeader>

      <CardContent>
        {isLoading ? (
          <div className="space-y-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center space-x-4">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-4 w-16" />
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-4 w-16" />
              </div>
            ))}
          </div>
        ) : filteredAndSortedProviders.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            No providers found matching your criteria.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="cursor-pointer" onClick={() => handleSort('name')}>
                    <div className="flex items-center gap-1">
                      Provider Name
                      {renderSortIcon('name')}
                    </div>
                  </TableHead>
                  <TableHead className="cursor-pointer text-center" onClick={() => handleSort('totalSignals')}>
                    <div className="flex items-center justify-center gap-1">
                      Total Signals
                      {renderSortIcon('totalSignals')}
                    </div>
                  </TableHead>
                  <TableHead className="cursor-pointer text-center" onClick={() => handleSort('winRate')}>
                    <div className="flex items-center justify-center gap-1">
                      Win Rate %
                      {renderSortIcon('winRate')}
                    </div>
                  </TableHead>
                  <TableHead className="cursor-pointer text-center" onClick={() => handleSort('averageRR')}>
                    <div className="flex items-center justify-center gap-1">
                      Avg R:R
                      {renderSortIcon('averageRR')}
                    </div>
                  </TableHead>
                  <TableHead className="cursor-pointer text-center" onClick={() => handleSort('maxDrawdown')}>
                    <div className="flex items-center justify-center gap-1">
                      Max Drawdown
                      {renderSortIcon('maxDrawdown')}
                    </div>
                  </TableHead>
                  <TableHead className="cursor-pointer text-center" onClick={() => handleSort('totalPnL')}>
                    <div className="flex items-center justify-center gap-1">
                      Total P&L
                      {renderSortIcon('totalPnL')}
                    </div>
                  </TableHead>
                  <TableHead className="cursor-pointer text-center" onClick={() => handleSort('lastSignalDate')}>
                    <div className="flex items-center justify-center gap-1">
                      Last Signal
                      {renderSortIcon('lastSignalDate')}
                    </div>
                  </TableHead>
                  <TableHead className="text-center">Grade</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredAndSortedProviders.map((provider) => (
                  <TableRow
                    key={provider.id}
                    className={cn(
                      'hover:bg-muted/50 transition-colors',
                      provider.winRate > 75 && 'bg-green-50/50 hover:bg-green-50/75'
                    )}
                  >
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        {getTrendIcon(provider.winRate)}
                        <span>{provider.name}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-center">
                      <div className="flex flex-col items-center">
                        <span className="font-medium">{provider.totalSignals}</span>
                        <span className="text-xs text-muted-foreground">
                          ({provider.executedSignals} executed)
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="text-center">
                      <div className={cn('font-medium', getWinRateColor(provider.winRate))}>
                        {provider.winRate.toFixed(1)}%
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {provider.winCount}W / {provider.lossCount}L
                      </div>
                    </TableCell>
                    <TableCell className="text-center font-medium">
                      {provider.averageRR.toFixed(2)}
                    </TableCell>
                    <TableCell className="text-center">
                      <span className="text-red-600 font-medium">
                        ${provider.maxDrawdown.toFixed(0)}
                      </span>
                    </TableCell>
                    <TableCell className="text-center">
                      <span className={cn(
                        'font-medium',
                        provider.totalPnL >= 0 ? 'text-green-600' : 'text-red-600'
                      )}>
                        {provider.totalPnL >= 0 ? '+' : ''}${provider.totalPnL.toFixed(0)}
                      </span>
                    </TableCell>
                    <TableCell className="text-center text-sm">
                      {new Date(provider.lastSignalDate).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-center">
                      <Badge className={cn('border', PERFORMANCE_COLORS[provider.performanceGrade])}>
                        {provider.performanceGrade}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-center">
                      <Badge variant={provider.isActive ? 'default' : 'secondary'}>
                        {provider.isActive ? 'Active' : 'Inactive'}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default AnalyticsProviderTable;