import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import MarginFilterBlock, { 
  MarginFilterConfig, 
  MarginStatus, 
  MarginFilterBlockProps 
} from '../MarginFilterBlock';

// Mock the query client
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

// Mock margin status data
const mockMarginStatus: MarginStatus = {
  freeMargin: 5000,
  totalMargin: 10000,
  usedMargin: 5000,
  marginLevel: 200,
  equity: 15000,
  balance: 15000,
  lastUpdate: new Date(),
  isConnected: true,
};

const mockLowMarginStatus: MarginStatus = {
  freeMargin: 500,
  totalMargin: 10000,
  usedMargin: 9500,
  marginLevel: 15,
  equity: 15000,
  balance: 15000,
  lastUpdate: new Date(),
  isConnected: true,
};

const mockEmergencyMarginStatus: MarginStatus = {
  freeMargin: 100,
  totalMargin: 10000,
  usedMargin: 9900,
  marginLevel: 5,
  equity: 15000,
  balance: 15000,
  lastUpdate: new Date(),
  isConnected: true,
};

const mockDisconnectedStatus: MarginStatus = {
  freeMargin: 0,
  totalMargin: 0,
  usedMargin: 0,
  marginLevel: 0,
  equity: 0,
  balance: 0,
  lastUpdate: new Date(),
  isConnected: false,
};

const defaultConfig: MarginFilterConfig = {
  filterType: 'percentage',
  thresholdPercentage: 25,
  thresholdAbsolute: 1000,
  allowOverride: false,
  overrideSignalTypes: [],
  emergencyThreshold: 10,
  checkInterval: 30,
  enableRealTimeCheck: true,
};

const defaultProps: MarginFilterBlockProps = {
  id: 'margin-filter-1',
  config: defaultConfig,
  onUpdate: vi.fn(),
  onDelete: vi.fn(),
};

const renderWithQueryClient = (component: React.ReactElement, marginData?: MarginStatus) => {
  const queryClient = createTestQueryClient();
  
  // Mock the margin status query
  if (marginData) {
    queryClient.setQueryData(['/api/margin/status'], marginData);
  }
  
  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  );
};

describe('MarginFilterBlock', () => {
  const mockOnUpdate = vi.fn();
  const mockOnDelete = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders with default configuration', () => {
    renderWithQueryClient(
      <MarginFilterBlock {...defaultProps} onUpdate={mockOnUpdate} onDelete={mockOnDelete} />
    );

    expect(screen.getByText('Margin Filter')).toBeInTheDocument();
    expect(screen.getByText('Filter Type')).toBeInTheDocument();
    expect(screen.getByText('Minimum Margin Level (%)')).toBeInTheDocument();
  });

  it('displays current margin status when data is available', () => {
    renderWithQueryClient(
      <MarginFilterBlock {...defaultProps} />,
      mockMarginStatus
    );

    expect(screen.getByText('Current Margin Level')).toBeInTheDocument();
    expect(screen.getByText('200.0%')).toBeInTheDocument();
    expect(screen.getByText('Free Margin')).toBeInTheDocument();
    expect(screen.getByText('$5,000')).toBeInTheDocument();
  });

  it('shows "Active" status when margin is sufficient', () => {
    renderWithQueryClient(
      <MarginFilterBlock {...defaultProps} />,
      mockMarginStatus
    );

    expect(screen.getByText('Active')).toBeInTheDocument();
    expect(screen.getByText('Signal Allowed')).toBeInTheDocument();
  });

  it('shows "Blocked" status when margin is insufficient', () => {
    renderWithQueryClient(
      <MarginFilterBlock {...defaultProps} />,
      mockLowMarginStatus
    );

    expect(screen.getByText('Blocked')).toBeInTheDocument();
    expect(screen.getByText('Signal Blocked')).toBeInTheDocument();
    expect(screen.getByText(/Margin level too low/)).toBeInTheDocument();
  });

  it('shows "Emergency" status when margin is critically low', () => {
    renderWithQueryClient(
      <MarginFilterBlock {...defaultProps} />,
      mockEmergencyMarginStatus
    );

    expect(screen.getByText('Emergency')).toBeInTheDocument();
    expect(screen.getByText('Signal Blocked')).toBeInTheDocument();
    expect(screen.getByText(/Emergency threshold breached/)).toBeInTheDocument();
  });

  it('shows "Disconnected" status when MT5 is not connected', () => {
    renderWithQueryClient(
      <MarginFilterBlock {...defaultProps} />,
      mockDisconnectedStatus
    );

    expect(screen.getByText('Disconnected')).toBeInTheDocument();
    expect(screen.getByText('Margin data unavailable')).toBeInTheDocument();
  });

  it('switches between percentage and absolute filter types', () => {
    renderWithQueryClient(
      <MarginFilterBlock {...defaultProps} onUpdate={mockOnUpdate} />
    );

    const filterTypeSelect = screen.getByRole('combobox');
    fireEvent.click(filterTypeSelect);
    
    const absoluteOption = screen.getByText('Free Margin ($)');
    fireEvent.click(absoluteOption);

    expect(mockOnUpdate).toHaveBeenCalledWith(
      expect.objectContaining({ filterType: 'absolute' })
    );
  });

  it('updates threshold via slider', () => {
    renderWithQueryClient(
      <MarginFilterBlock {...defaultProps} onUpdate={mockOnUpdate} />
    );

    const slider = screen.getByRole('slider');
    fireEvent.change(slider, { target: { value: '50' } });

    expect(mockOnUpdate).toHaveBeenCalledWith(
      expect.objectContaining({ thresholdPercentage: 50 })
    );
  });

  it('shows advanced settings when toggled', () => {
    renderWithQueryClient(<MarginFilterBlock {...defaultProps} />);

    const advancedButton = screen.getByText('Advanced Settings');
    fireEvent.click(advancedButton);

    expect(screen.getByText('Emergency Threshold (%)')).toBeInTheDocument();
    expect(screen.getByText('Allow Signal Override')).toBeInTheDocument();
    expect(screen.getByText('Real-time Monitoring')).toBeInTheDocument();
  });

  it('enables override configuration when allow override is turned on', () => {
    renderWithQueryClient(
      <MarginFilterBlock 
        {...defaultProps} 
        config={{ ...defaultConfig, allowOverride: true }}
        onUpdate={mockOnUpdate}
      />
    );

    const advancedButton = screen.getByText('Advanced Settings');
    fireEvent.click(advancedButton);

    expect(screen.getByText('Override Signal Types')).toBeInTheDocument();
    expect(screen.getByText('High Confidence')).toBeInTheDocument();
    expect(screen.getByText('Breakout')).toBeInTheDocument();
  });

  it('applies override for specified signal types', () => {
    const configWithOverride: MarginFilterConfig = {
      ...defaultConfig,
      allowOverride: true,
      overrideSignalTypes: ['HIGH_CONFIDENCE'],
    };

    const testSignal = {
      symbol: 'EURUSD',
      action: 'BUY' as const,
      signalType: 'HIGH_CONFIDENCE',
    };

    renderWithQueryClient(
      <MarginFilterBlock 
        {...defaultProps} 
        config={configWithOverride}
        testSignal={testSignal}
      />,
      mockLowMarginStatus
    );

    expect(screen.getByText('Signal Allowed')).toBeInTheDocument();
    expect(screen.getByText('Override Applied')).toBeInTheDocument();
    expect(screen.getByText(/Override applied for HIGH_CONFIDENCE/)).toBeInTheDocument();
  });

  it('does not apply override for non-specified signal types', () => {
    const configWithOverride: MarginFilterConfig = {
      ...defaultConfig,
      allowOverride: true,
      overrideSignalTypes: ['HIGH_CONFIDENCE'],
    };

    const testSignal = {
      symbol: 'EURUSD',
      action: 'BUY' as const,
      signalType: 'SCALP',
    };

    renderWithQueryClient(
      <MarginFilterBlock 
        {...defaultProps} 
        config={configWithOverride}
        testSignal={testSignal}
      />,
      mockLowMarginStatus
    );

    expect(screen.getByText('Signal Blocked')).toBeInTheDocument();
    expect(screen.queryByText('Override Applied')).not.toBeInTheDocument();
  });

  it('never allows override in emergency mode', () => {
    const configWithOverride: MarginFilterConfig = {
      ...defaultConfig,
      allowOverride: true,
      overrideSignalTypes: ['HIGH_CONFIDENCE'],
    };

    const testSignal = {
      symbol: 'EURUSD',
      action: 'BUY' as const,
      signalType: 'HIGH_CONFIDENCE',
    };

    renderWithQueryClient(
      <MarginFilterBlock 
        {...defaultProps} 
        config={configWithOverride}
        testSignal={testSignal}
      />,
      mockEmergencyMarginStatus
    );

    expect(screen.getByText('Emergency')).toBeInTheDocument();
    expect(screen.getByText('Signal Blocked')).toBeInTheDocument();
    expect(screen.getByText(/Emergency threshold breached/)).toBeInTheDocument();
    expect(screen.queryByText('Override Applied')).not.toBeInTheDocument();
  });

  it('displays test signal information when provided', () => {
    const testSignal = {
      symbol: 'EURUSD',
      action: 'BUY' as const,
      signalType: 'HIGH_CONFIDENCE',
    };

    renderWithQueryClient(
      <MarginFilterBlock {...defaultProps} testSignal={testSignal} />
    );

    expect(screen.getByText('Test Signal')).toBeInTheDocument();
    expect(screen.getByText('Symbol: EURUSD')).toBeInTheDocument();
    expect(screen.getByText('Action: BUY')).toBeInTheDocument();
    expect(screen.getByText('Type: HIGH_CONFIDENCE')).toBeInTheDocument();
  });

  it('works with absolute threshold filtering', () => {
    const absoluteConfig: MarginFilterConfig = {
      ...defaultConfig,
      filterType: 'absolute',
      thresholdAbsolute: 2000,
    };

    renderWithQueryClient(
      <MarginFilterBlock {...defaultProps} config={absoluteConfig} />,
      mockMarginStatus
    );

    expect(screen.getByText('Signal Allowed')).toBeInTheDocument();
    expect(screen.getByText(/Free margin sufficient/)).toBeInTheDocument();
  });

  it('blocks signals when absolute threshold is not met', () => {
    const absoluteConfig: MarginFilterConfig = {
      ...defaultConfig,
      filterType: 'absolute',
      thresholdAbsolute: 6000,
    };

    renderWithQueryClient(
      <MarginFilterBlock {...defaultProps} config={absoluteConfig} />,
      mockMarginStatus
    );

    expect(screen.getByText('Signal Blocked')).toBeInTheDocument();
    expect(screen.getByText(/Free margin too low/)).toBeInTheDocument();
  });

  it('calls onDelete when delete button is clicked', () => {
    renderWithQueryClient(
      <MarginFilterBlock {...defaultProps} onDelete={mockOnDelete} />
    );
    
    const deleteButton = screen.getByText('×');
    fireEvent.click(deleteButton);

    expect(mockOnDelete).toHaveBeenCalledTimes(1);
  });

  it('updates emergency threshold configuration', () => {
    renderWithQueryClient(
      <MarginFilterBlock {...defaultProps} onUpdate={mockOnUpdate} />
    );

    const advancedButton = screen.getByText('Advanced Settings');
    fireEvent.click(advancedButton);

    const emergencyInput = screen.getByDisplayValue('10');
    fireEvent.change(emergencyInput, { target: { value: '15' } });

    expect(mockOnUpdate).toHaveBeenCalledWith(
      expect.objectContaining({ emergencyThreshold: 15 })
    );
  });

  it('toggles real-time monitoring', () => {
    renderWithQueryClient(
      <MarginFilterBlock {...defaultProps} onUpdate={mockOnUpdate} />
    );

    const advancedButton = screen.getByText('Advanced Settings');
    fireEvent.click(advancedButton);

    const realtimeToggle = screen.getByRole('switch', { name: /real-time monitoring/i });
    fireEvent.click(realtimeToggle);

    expect(mockOnUpdate).toHaveBeenCalledWith(
      expect.objectContaining({ enableRealTimeCheck: false })
    );
  });

  it('updates check interval when real-time is enabled', () => {
    renderWithQueryClient(
      <MarginFilterBlock {...defaultProps} onUpdate={mockOnUpdate} />
    );

    const advancedButton = screen.getByText('Advanced Settings');
    fireEvent.click(advancedButton);

    const intervalSelect = screen.getAllByRole('combobox')[1]; // Second combobox is interval
    fireEvent.click(intervalSelect);
    
    const oneMinuteOption = screen.getByText('1 minute');
    fireEvent.click(oneMinuteOption);

    expect(mockOnUpdate).toHaveBeenCalledWith(
      expect.objectContaining({ checkInterval: 60 })
    );
  });
});

// Integration tests for strategy builder connection
describe('MarginFilterBlock Integration', () => {
  const mockOnUpdate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('integrates with strategy builder workflow', async () => {
    const { rerender } = renderWithQueryClient(
      <MarginFilterBlock {...defaultProps} onUpdate={mockOnUpdate} />
    );

    // Simulate configuration changes
    const filterTypeSelect = screen.getByRole('combobox');
    fireEvent.click(filterTypeSelect);
    fireEvent.click(screen.getByText('Free Margin ($)'));

    expect(mockOnUpdate).toHaveBeenCalledWith(
      expect.objectContaining({ filterType: 'absolute' })
    );

    // Simulate props update from parent
    const updatedConfig = { ...defaultConfig, filterType: 'absolute' as const };
    rerender(
      <QueryClientProvider client={createTestQueryClient()}>
        <MarginFilterBlock {...defaultProps} config={updatedConfig} onUpdate={mockOnUpdate} />
      </QueryClientProvider>
    );

    expect(screen.getByText('Minimum Free Margin ($)')).toBeInTheDocument();
  });

  it('handles rapid configuration updates efficiently', () => {
    renderWithQueryClient(
      <MarginFilterBlock {...defaultProps} onUpdate={mockOnUpdate} />
    );

    const slider = screen.getByRole('slider');
    
    // Simulate rapid slider changes
    fireEvent.change(slider, { target: { value: '30' } });
    fireEvent.change(slider, { target: { value: '35' } });
    fireEvent.change(slider, { target: { value: '40' } });

    // Should call onUpdate for each change
    expect(mockOnUpdate).toHaveBeenCalledTimes(3);
    expect(mockOnUpdate).toHaveBeenLastCalledWith(
      expect.objectContaining({ thresholdPercentage: 40 })
    );
  });

  it('maintains state consistency across re-renders', () => {
    const { rerender } = renderWithQueryClient(
      <MarginFilterBlock {...defaultProps} />
    );

    // Open advanced settings
    fireEvent.click(screen.getByText('Advanced Settings'));
    expect(screen.getByText('Emergency Threshold (%)')).toBeInTheDocument();

    // Re-render with same props
    rerender(
      <QueryClientProvider client={createTestQueryClient()}>
        <MarginFilterBlock {...defaultProps} />
      </QueryClientProvider>
    );

    // Advanced settings should still be open
    expect(screen.getByText('Emergency Threshold (%)')).toBeInTheDocument();
  });
});