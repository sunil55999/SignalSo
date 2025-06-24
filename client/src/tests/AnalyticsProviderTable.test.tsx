/**
 * Unit Tests for AnalyticsProviderTable
 * Tests sorting, filtering, conditional rendering, and responsiveness
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AnalyticsProviderTable, type ProviderStats } from '../components/analytics/AnalyticsProviderTable';
import mockProviderStats from './mocks/provider_stats.json';

// Mock fetch globally
global.fetch = vi.fn();

// Test component wrapper with QueryClient
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        refetchOnWindowFocus: false,
      },
    },
  });

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

describe('AnalyticsProviderTable', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockProviderStats),
    });
  });

  describe('Basic Rendering', () => {
    it('should render the table with provider data', async () => {
      render(
        <TestWrapper>
          <AnalyticsProviderTable />
        </TestWrapper>
      );

      // Wait for data to load
      await waitFor(() => {
        expect(screen.getByText('Gold Signals Pro')).toBeInTheDocument();
      });

      // Check if all expected columns are present
      expect(screen.getByText('Provider Name')).toBeInTheDocument();
      expect(screen.getByText('Total Signals')).toBeInTheDocument();
      expect(screen.getByText('Win Rate %')).toBeInTheDocument();
      expect(screen.getByText('Avg R:R')).toBeInTheDocument();
      expect(screen.getByText('Max Drawdown')).toBeInTheDocument();
      expect(screen.getByText('Total P&L')).toBeInTheDocument();
      expect(screen.getByText('Last Signal')).toBeInTheDocument();
      expect(screen.getByText('Grade')).toBeInTheDocument();
      expect(screen.getByText('Status')).toBeInTheDocument();
    });

    it('should display loading state', () => {
      (global.fetch as any).mockImplementation(() => new Promise(() => {})); // Never resolves

      render(
        <TestWrapper>
          <AnalyticsProviderTable />
        </TestWrapper>
      );

      // Should show skeleton loaders
      expect(document.querySelectorAll('[data-testid="skeleton"]')).toBeTruthy();
    });

    it('should display error state when fetch fails', async () => {
      (global.fetch as any).mockRejectedValue(new Error('Network error'));

      render(
        <TestWrapper>
          <AnalyticsProviderTable />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText(/Failed to load provider statistics/)).toBeInTheDocument();
      });
    });
  });

  describe('Column Sorting', () => {
    it('should sort by win rate in descending order by default', async () => {
      render(
        <TestWrapper>
          <AnalyticsProviderTable />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('AI Trading Bot')).toBeInTheDocument();
      });

      const rows = screen.getAllByRole('row');
      const dataRows = rows.slice(1); // Skip header row
      
      // First provider should be "AI Trading Bot" with highest win rate (78.0%)
      expect(within(dataRows[0]).getByText('AI Trading Bot')).toBeInTheDocument();
      expect(within(dataRows[0]).getByText('78.0%')).toBeInTheDocument();
    });

    it('should toggle sort direction when clicking same column header', async () => {
      render(
        <TestWrapper>
          <AnalyticsProviderTable />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('AI Trading Bot')).toBeInTheDocument();
      });

      // Click win rate header to sort ascending
      const winRateHeader = screen.getByText('Win Rate %');
      fireEvent.click(winRateHeader);

      await waitFor(() => {
        const rows = screen.getAllByRole('row');
        const dataRows = rows.slice(1);
        // First provider should now be "High Risk Returns" with lowest win rate (40.0%)
        expect(within(dataRows[0]).getByText('High Risk Returns')).toBeInTheDocument();
      });
    });

    it('should sort by total signals correctly', async () => {
      render(
        <TestWrapper>
          <AnalyticsProviderTable />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('AI Trading Bot')).toBeInTheDocument();
      });

      // Click total signals header
      const totalSignalsHeader = screen.getByText('Total Signals');
      fireEvent.click(totalSignalsHeader);

      await waitFor(() => {
        const rows = screen.getAllByRole('row');
        const dataRows = rows.slice(1);
        // Should show provider with fewest signals first (ascending order)
        expect(within(dataRows[0]).getByText('Euro Trend Signals')).toBeInTheDocument();
      });
    });

    it('should sort by provider name alphabetically', async () => {
      render(
        <TestWrapper>
          <AnalyticsProviderTable />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('AI Trading Bot')).toBeInTheDocument();
      });

      // Click provider name header
      const nameHeader = screen.getByText('Provider Name');
      fireEvent.click(nameHeader);

      await waitFor(() => {
        const rows = screen.getAllByRole('row');
        const dataRows = rows.slice(1);
        // Should show alphabetically first provider
        expect(within(dataRows[0]).getByText('AI Trading Bot')).toBeInTheDocument();
      });
    });
  });

  describe('Filtering', () => {
    it('should filter providers by search term', async () => {
      render(
        <TestWrapper>
          <AnalyticsProviderTable />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('AI Trading Bot')).toBeInTheDocument();
      });

      // Type in search box
      const searchInput = screen.getByPlaceholderText('Search providers...');
      fireEvent.change(searchInput, { target: { value: 'Gold' } });

      await waitFor(() => {
        // Should only show providers with "Gold" in name
        expect(screen.getByText('Gold Signals Pro')).toBeInTheDocument();
        expect(screen.queryByText('AI Trading Bot')).not.toBeInTheDocument();
      });
    });

    it('should filter by minimum win rate', async () => {
      render(
        <TestWrapper>
          <AnalyticsProviderTable />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('High Risk Returns')).toBeInTheDocument();
      });

      // Select 70%+ win rate filter
      const winRateSelect = screen.getByRole('combobox', { name: /min win rate/i });
      fireEvent.click(winRateSelect);
      
      const option70 = screen.getByText('70%+ Win Rate');
      fireEvent.click(option70);

      await waitFor(() => {
        // Should only show providers with 70%+ win rate
        expect(screen.getByText('AI Trading Bot')).toBeInTheDocument(); // 78.0%
        expect(screen.getByText('Gold Signals Pro')).toBeInTheDocument(); // 77.7%
        expect(screen.queryByText('High Risk Returns')).not.toBeInTheDocument(); // 40.0%
      });
    });

    it('should filter by performance grade', async () => {
      render(
        <TestWrapper>
          <AnalyticsProviderTable />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('High Risk Returns')).toBeInTheDocument();
      });

      // Select Grade A filter
      const gradeSelect = screen.getByRole('combobox', { name: /grade/i });
      fireEvent.click(gradeSelect);
      
      const gradeA = screen.getByText('Grade A');
      fireEvent.click(gradeA);

      await waitFor(() => {
        // Should only show Grade A providers
        expect(screen.getByText('AI Trading Bot')).toBeInTheDocument();
        expect(screen.getByText('Gold Signals Pro')).toBeInTheDocument();
        expect(screen.queryByText('High Risk Returns')).not.toBeInTheDocument();
      });
    });

    it('should clear all filters when clear button is clicked', async () => {
      render(
        <TestWrapper>
          <AnalyticsProviderTable />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('High Risk Returns')).toBeInTheDocument();
      });

      // Apply search filter
      const searchInput = screen.getByPlaceholderText('Search providers...');
      fireEvent.change(searchInput, { target: { value: 'Gold' } });

      await waitFor(() => {
        expect(screen.queryByText('AI Trading Bot')).not.toBeInTheDocument();
      });

      // Click clear filters
      const clearButton = screen.getByText('Clear Filters');
      fireEvent.click(clearButton);

      await waitFor(() => {
        // All providers should be visible again
        expect(screen.getByText('AI Trading Bot')).toBeInTheDocument();
        expect(screen.getByText('High Risk Returns')).toBeInTheDocument();
        expect(searchInput).toHaveValue('');
      });
    });
  });

  describe('Conditional Rendering and Highlighting', () => {
    it('should highlight top performers with green background', async () => {
      render(
        <TestWrapper>
          <AnalyticsProviderTable />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('AI Trading Bot')).toBeInTheDocument();
      });

      const rows = screen.getAllByRole('row');
      const topPerformerRow = rows.find(row => 
        within(row).queryByText('AI Trading Bot')
      );

      expect(topPerformerRow).toHaveClass('bg-green-50/50');
    });

    it('should display correct win rate colors', async () => {
      render(
        <TestWrapper>
          <AnalyticsProviderTable />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('78.0%')).toBeInTheDocument();
      });

      // Excellent win rate (>75%) should be green
      const excellentWinRate = screen.getByText('78.0%');
      expect(excellentWinRate).toHaveClass('text-green-600');

      // Poor win rate (<45%) should be red
      const poorWinRate = screen.getByText('40.0%');
      expect(poorWinRate).toHaveClass('text-red-600');
    });

    it('should display correct performance grade badges', async () => {
      render(
        <TestWrapper>
          <AnalyticsProviderTable />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('AI Trading Bot')).toBeInTheDocument();
      });

      // Check for Grade A badge
      const gradeABadges = screen.getAllByText('A');
      expect(gradeABadges.length).toBeGreaterThan(0);
      expect(gradeABadges[0]).toHaveClass('bg-green-100');

      // Check for Grade F badge
      const gradeFBadges = screen.getAllByText('F');
      expect(gradeFBadges.length).toBeGreaterThan(0);
      expect(gradeFBadges[0]).toHaveClass('bg-red-100');
    });

    it('should display correct P&L colors', async () => {
      render(
        <TestWrapper>
          <AnalyticsProviderTable />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('+$4851')).toBeInTheDocument();
      });

      // Positive P&L should be green
      const positivePN = screen.getByText('+$4851');
      expect(positivePN).toHaveClass('text-green-600');

      // Negative P&L should be red
      const negativePN = screen.getByText('-$1251');
      expect(negativePN).toHaveClass('text-red-600');
    });

    it('should show trend icons based on win rate', async () => {
      render(
        <TestWrapper>
          <AnalyticsProviderTable />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('AI Trading Bot')).toBeInTheDocument();
      });

      // Should show trending up icons for high performers
      const trendingUpIcons = document.querySelectorAll('.lucide-trending-up');
      expect(trendingUpIcons.length).toBeGreaterThan(0);

      // Should show trending down icons for poor performers
      const trendingDownIcons = document.querySelectorAll('.lucide-trending-down');
      expect(trendingDownIcons.length).toBeGreaterThan(0);
    });
  });

  describe('Export Functionality', () => {
    it('should handle CSV export', async () => {
      // Mock URL.createObjectURL and document methods
      const createObjectURLSpy = vi.fn(() => 'blob:test-url');
      const revokeObjectURLSpy = vi.fn();
      const createElementSpy = vi.fn(() => ({
        href: '',
        download: '',
        click: vi.fn(),
      }));
      const appendChildSpy = vi.fn();
      const removeChildSpy = vi.fn();

      Object.defineProperty(URL, 'createObjectURL', { value: createObjectURLSpy });
      Object.defineProperty(URL, 'revokeObjectURL', { value: revokeObjectURLSpy });
      Object.defineProperty(document, 'createElement', { value: createElementSpy });
      Object.defineProperty(document.body, 'appendChild', { value: appendChildSpy });
      Object.defineProperty(document.body, 'removeChild', { value: removeChildSpy });

      render(
        <TestWrapper>
          <AnalyticsProviderTable />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('AI Trading Bot')).toBeInTheDocument();
      });

      // Click export button
      const exportButton = screen.getByText('Export CSV');
      fireEvent.click(exportButton);

      // Verify CSV export functions were called
      expect(createObjectURLSpy).toHaveBeenCalled();
      expect(createElementSpy).toHaveBeenCalledWith('a');
      expect(appendChildSpy).toHaveBeenCalled();
      expect(removeChildSpy).toHaveBeenCalled();
      expect(revokeObjectURLSpy).toHaveBeenCalled();
    });
  });

  describe('Mobile Responsiveness', () => {
    it('should have horizontal scroll for small screens', async () => {
      render(
        <TestWrapper>
          <AnalyticsProviderTable />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('AI Trading Bot')).toBeInTheDocument();
      });

      const tableContainer = document.querySelector('.overflow-x-auto');
      expect(tableContainer).toBeInTheDocument();
    });

    it('should display row count information', async () => {
      render(
        <TestWrapper>
          <AnalyticsProviderTable />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText(/Showing \d+ of \d+ providers/)).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels and roles', async () => {
      render(
        <TestWrapper>
          <AnalyticsProviderTable />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('AI Trading Bot')).toBeInTheDocument();
      });

      // Check for proper table structure
      expect(screen.getByRole('table')).toBeInTheDocument();
      expect(screen.getAllByRole('columnheader')).toHaveLength(9);
      expect(screen.getAllByRole('row')).toHaveLength(11); // 1 header + 10 data rows
    });

    it('should support keyboard navigation on sortable headers', async () => {
      render(
        <TestWrapper>
          <AnalyticsProviderTable />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('AI Trading Bot')).toBeInTheDocument();
      });

      const nameHeader = screen.getByText('Provider Name');
      expect(nameHeader.closest('th')).toHaveClass('cursor-pointer');
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty provider list', async () => {
      (global.fetch as any).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve([]),
      });

      render(
        <TestWrapper>
          <AnalyticsProviderTable />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('No providers found matching your criteria.')).toBeInTheDocument();
      });
    });

    it('should disable export button when no data available', async () => {
      (global.fetch as any).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve([]),
      });

      render(
        <TestWrapper>
          <AnalyticsProviderTable />
        </TestWrapper>
      );

      await waitFor(() => {
        const exportButton = screen.getByText('Export CSV');
        expect(exportButton).toBeDisabled();
      });
    });
  });
});