import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi } from 'vitest';
import ProviderCompare from '@/pages/ProviderCompare';

// Mock data
const mockProviderData = [
  {
    id: 1,
    providerId: 'gold-signals',
    providerName: 'Gold Signals Pro',
    totalSignals: 150,
    successfulSignals: 105,
    winRate: '70.00',
    avgRrRatio: '2.50',
    avgExecutionDelay: 850,
    maxDrawdown: '8.50',
    totalProfit: '15420.50',
    totalLoss: '-3250.00',
    avgConfidence: '0.75',
    isActive: true,
    lastSignalAt: '2023-12-20T10:30:00Z',
    createdAt: '2023-01-01T00:00:00Z',
    updatedAt: '2023-12-20T10:30:00Z'
  },
  {
    id: 2,
    providerId: 'forex-master',
    providerName: 'Forex Master',
    totalSignals: 200,
    successfulSignals: 120,
    winRate: '60.00',
    avgRrRatio: '1.80',
    avgExecutionDelay: 1200,
    maxDrawdown: '12.30',
    totalProfit: '8500.00',
    totalLoss: '-5200.00',
    avgConfidence: '0.68',
    isActive: true,
    lastSignalAt: '2023-12-19T15:45:00Z',
    createdAt: '2023-02-01T00:00:00Z',
    updatedAt: '2023-12-19T15:45:00Z'
  },
  {
    id: 3,
    providerId: 'premium-trader',
    providerName: 'Premium Trader',
    totalSignals: 80,
    successfulSignals: 32,
    winRate: '40.00',
    avgRrRatio: '1.20',
    avgExecutionDelay: 2500,
    maxDrawdown: '25.60',
    totalProfit: '2100.00',
    totalLoss: '-8900.00',
    avgConfidence: '0.45',
    isActive: false,
    lastSignalAt: '2023-11-15T08:20:00Z',
    createdAt: '2023-03-01T00:00:00Z',
    updatedAt: '2023-11-15T08:20:00Z'
  }
];

// Mock the API call
const mockFetch = vi.fn();
global.fetch = mockFetch;

const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

const renderWithQueryClient = (component: React.ReactElement) => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  );
};

describe('ProviderCompare Component', () => {
  beforeEach(() => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockProviderData,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders provider comparison page with correct title', async () => {
    renderWithQueryClient(<ProviderCompare />);
    
    expect(screen.getByText('Provider Comparison')).toBeInTheDocument();
    expect(screen.getByText('Compare signal provider performance metrics and statistics')).toBeInTheDocument();
  });

  it('displays provider data in table view', async () => {
    renderWithQueryClient(<ProviderCompare />);

    await waitFor(() => {
      expect(screen.getByText('Gold Signals Pro')).toBeInTheDocument();
      expect(screen.getByText('Forex Master')).toBeInTheDocument();
    });

    // Check if win rates are displayed
    expect(screen.getByText('70.0%')).toBeInTheDocument();
    expect(screen.getByText('60.0%')).toBeInTheDocument();
  });

  it('filters providers by search term', async () => {
    renderWithQueryClient(<ProviderCompare />);

    await waitFor(() => {
      expect(screen.getByText('Gold Signals Pro')).toBeInTheDocument();
    });

    // Search for "Gold"
    const searchInput = screen.getByPlaceholderText('Search providers...');
    fireEvent.change(searchInput, { target: { value: 'Gold' } });

    await waitFor(() => {
      expect(screen.getByText('Gold Signals Pro')).toBeInTheDocument();
      expect(screen.queryByText('Forex Master')).not.toBeInTheDocument();
    });
  });

  it('filters active providers only', async () => {
    renderWithQueryClient(<ProviderCompare />);

    await waitFor(() => {
      expect(screen.getByText('Gold Signals Pro')).toBeInTheDocument();
      expect(screen.getByText('Forex Master')).toBeInTheDocument();
    });

    // Initially, "Active providers only" should be checked and Premium Trader (inactive) should not be visible
    const activeCheckbox = screen.getByLabelText('Active providers only');
    expect(activeCheckbox).toBeChecked();
    expect(screen.queryByText('Premium Trader')).not.toBeInTheDocument();

    // Uncheck to show all providers
    fireEvent.click(activeCheckbox);

    await waitFor(() => {
      expect(screen.getByText('Premium Trader')).toBeInTheDocument();
    });
  });

  it('sorts providers by different metrics', async () => {
    renderWithQueryClient(<ProviderCompare />);

    await waitFor(() => {
      expect(screen.getByText('Gold Signals Pro')).toBeInTheDocument();
    });

    // Click on Total Signals column to sort
    const signalsHeader = screen.getByRole('button', { name: /Signals/i });
    fireEvent.click(signalsHeader);

    // Should be sorted by total signals in descending order
    const providerRows = screen.getAllByText(/Gold Signals Pro|Forex Master/);
    // Forex Master has more signals (200 vs 150), so it should be first when sorted by signals desc
    expect(providerRows[0]).toHaveTextContent('Forex Master');
  });

  it('switches between table and card view modes', async () => {
    renderWithQueryClient(<ProviderCompare />);

    await waitFor(() => {
      expect(screen.getByText('Gold Signals Pro')).toBeInTheDocument();
    });

    // Initially in table view
    expect(screen.getByRole('table')).toBeInTheDocument();

    // Switch to cards view
    const viewSelect = screen.getByRole('combobox');
    fireEvent.click(viewSelect);
    fireEvent.click(screen.getByText('Cards'));

    await waitFor(() => {
      expect(screen.queryByRole('table')).not.toBeInTheDocument();
      // Should still show provider data but in card format
      expect(screen.getByText('Gold Signals Pro')).toBeInTheDocument();
    });
  });

  it('selects and deselects providers for comparison', async () => {
    renderWithQueryClient(<ProviderCompare />);

    await waitFor(() => {
      expect(screen.getByText('Gold Signals Pro')).toBeInTheDocument();
    });

    // Get checkboxes (there should be individual checkboxes for each provider plus a select-all)
    const checkboxes = screen.getAllByRole('checkbox');
    const providerCheckbox = checkboxes.find(cb => 
      cb.closest('tr')?.textContent?.includes('Gold Signals Pro')
    );

    expect(providerCheckbox).toBeDefined();
    
    // Select a provider
    fireEvent.click(providerCheckbox!);

    await waitFor(() => {
      expect(screen.getByText('Selected Providers')).toBeInTheDocument();
      expect(screen.getByText('1 provider(s) selected for comparison')).toBeInTheDocument();
    });
  });

  it('displays performance metrics with correct color coding', async () => {
    renderWithQueryClient(<ProviderCompare />);

    await waitFor(() => {
      expect(screen.getByText('70.0%')).toBeInTheDocument();
    });

    // Check that high win rate (70%) has green color class
    const highWinRate = screen.getByText('70.0%');
    expect(highWinRate).toHaveClass('text-green-600');

    // Check that medium win rate (60%) has yellow color class
    const mediumWinRate = screen.getByText('60.0%');
    expect(mediumWinRate).toHaveClass('text-yellow-600');
  });

  it('formats execution delay correctly', async () => {
    renderWithQueryClient(<ProviderCompare />);

    await waitFor(() => {
      expect(screen.getByText('0.9s')).toBeInTheDocument(); // 850ms formatted as 0.9s
      expect(screen.getByText('1.2s')).toBeInTheDocument(); // 1200ms formatted as 1.2s
    });
  });

  it('handles loading state', () => {
    // Mock loading state
    mockFetch.mockImplementation(() => new Promise(() => {})); // Never resolves

    renderWithQueryClient(<ProviderCompare />);

    expect(screen.getByRole('status')).toBeInTheDocument(); // Loading spinner
  });

  it('handles error state', async () => {
    // Mock error
    mockFetch.mockRejectedValue(new Error('API Error'));

    renderWithQueryClient(<ProviderCompare />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load provider statistics')).toBeInTheDocument();
    });
  });

  it('exports data to CSV when export button is clicked', async () => {
    // Mock URL.createObjectURL and related methods
    const mockCreateObjectURL = vi.fn(() => 'mock-url');
    const mockRevokeObjectURL = vi.fn();
    const mockClick = vi.fn();
    
    global.URL.createObjectURL = mockCreateObjectURL;
    global.URL.revokeObjectURL = mockRevokeObjectURL;
    
    // Mock createElement to return an element with click method
    const originalCreateElement = document.createElement;
    document.createElement = vi.fn((tagName) => {
      if (tagName === 'a') {
        return {
          href: '',
          download: '',
          click: mockClick,
        } as any;
      }
      return originalCreateElement.call(document, tagName);
    });

    renderWithQueryClient(<ProviderCompare />);

    await waitFor(() => {
      expect(screen.getByText('Gold Signals Pro')).toBeInTheDocument();
    });

    // Click export button
    const exportButton = screen.getByRole('button', { name: /Export CSV/i });
    fireEvent.click(exportButton);

    expect(mockCreateObjectURL).toHaveBeenCalled();
    expect(mockClick).toHaveBeenCalled();
    expect(mockRevokeObjectURL).toHaveBeenCalled();

    // Restore original method
    document.createElement = originalCreateElement;
  });
});