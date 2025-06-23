import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import RiskRewardBlock, { RiskRewardConfig, SignalData } from '../RiskRewardBlock';

describe('RiskRewardBlock', () => {
  const mockOnUpdate = vi.fn();
  const mockOnDelete = vi.fn();

  const defaultConfig: RiskRewardConfig = {
    minimumRatio: 1.5,
    calculationMethod: 'weighted',
    considerMultipleTP: true,
    tpWeights: [0.5, 0.3, 0.2, 0.0, 0.0],
    riskToleranceMode: 'moderate',
    dynamicAdjustment: false
  };

  const testSignal: SignalData = {
    symbol: 'EURUSD',
    action: 'BUY',
    entry: 1.1000,
    stopLoss: 1.0950,
    takeProfit1: 1.1075,
    takeProfit2: 1.1150,
    takeProfit3: 1.1200,
    lotSize: 0.1
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const defaultProps = {
    id: 'test-rr-block',
    config: defaultConfig,
    onUpdate: mockOnUpdate,
    onDelete: mockOnDelete
  };

  it('renders with default configuration', () => {
    render(<RiskRewardBlock {...defaultProps} />);
    
    expect(screen.getByText('Risk-Reward Filter')).toBeInTheDocument();
    expect(screen.getByText('Minimum R:R')).toBeInTheDocument();
    expect(screen.getByText('1:1.50')).toBeInTheDocument();
  });

  it('calculates R:R ratio correctly for simple method', async () => {
    const simpleConfig = { ...defaultConfig, calculationMethod: 'simple' as const };
    
    render(
      <RiskRewardBlock 
        {...defaultProps} 
        config={simpleConfig}
        testSignal={testSignal}
      />
    );

    // Risk: 1.1000 - 1.0950 = 50 pips
    // Reward: 1.1075 - 1.1000 = 75 pips
    // Ratio: 75/50 = 1.5
    expect(screen.getByText('1:1.50')).toBeInTheDocument();
  });

  it('calculates weighted R:R ratio correctly', async () => {
    render(
      <RiskRewardBlock 
        {...defaultProps} 
        testSignal={testSignal}
      />
    );

    // Risk: 50 pips
    // TP1: 75 pips * 0.5 = 37.5
    // TP2: 150 pips * 0.3 = 45
    // TP3: 200 pips * 0.2 = 40
    // Total weighted reward: 122.5 pips
    // Ratio: 122.5/50 = 2.45
    expect(screen.getByText('1:2.45')).toBeInTheDocument();
  });

  it('handles conservative calculation method', async () => {
    const conservativeConfig = { ...defaultConfig, calculationMethod: 'conservative' as const };
    
    render(
      <RiskRewardBlock 
        {...defaultProps} 
        config={conservativeConfig}
        testSignal={testSignal}
      />
    );

    // Conservative should use closest TP (TP1: 75 pips)
    // Ratio: 75/50 = 1.5
    expect(screen.getByText('1:1.50')).toBeInTheDocument();
  });

  it('shows pass/fail status based on minimum ratio', () => {
    const passingSignal = { ...testSignal, takeProfit1: 1.1100 }; // Higher TP
    
    render(
      <RiskRewardBlock 
        {...defaultProps} 
        testSignal={passingSignal}
      />
    );

    // Should pass with higher TP
    const badges = screen.getAllByRole('status');
    expect(badges.some(badge => badge.textContent?.includes('1:'))).toBe(true);
  });

  it('expands and collapses configuration panel', async () => {
    render(<RiskRewardBlock {...defaultProps} />);
    
    const expandButton = screen.getByText('+');
    expect(screen.queryByText('Calculation Method')).not.toBeInTheDocument();
    
    fireEvent.click(expandButton);
    
    await waitFor(() => {
      expect(screen.getByText('Calculation Method')).toBeInTheDocument();
    });
    
    const collapseButton = screen.getByText('−');
    fireEvent.click(collapseButton);
    
    await waitFor(() => {
      expect(screen.queryByText('Calculation Method')).not.toBeInTheDocument();
    });
  });

  it('updates minimum ratio configuration', async () => {
    render(<RiskRewardBlock {...defaultProps} />);
    
    // Expand panel
    fireEvent.click(screen.getByText('+'));
    
    await waitFor(() => {
      expect(screen.getByText('Calculation Method')).toBeInTheDocument();
    });

    // Find and interact with slider (this is a simplified test)
    const sliders = screen.getAllByRole('slider');
    const ratioSlider = sliders[0]; // First slider should be minimum ratio
    
    fireEvent.change(ratioSlider, { target: { value: '2.0' } });

    await waitFor(() => {
      expect(mockOnUpdate).toHaveBeenCalledWith(
        expect.objectContaining({
          minimumRatio: expect.any(Number)
        })
      );
    });
  });

  it('changes calculation method', async () => {
    render(<RiskRewardBlock {...defaultProps} />);
    
    fireEvent.click(screen.getByText('+'));
    
    await waitFor(() => {
      const methodSelect = screen.getByDisplayValue('Weighted Average');
      fireEvent.click(methodSelect);
    });

    const simpleOption = screen.getByText('Simple (First TP only)');
    fireEvent.click(simpleOption);

    await waitFor(() => {
      expect(mockOnUpdate).toHaveBeenCalledWith(
        expect.objectContaining({
          calculationMethod: 'simple'
        })
      );
    });
  });

  it('toggles multiple TP consideration', async () => {
    render(<RiskRewardBlock {...defaultProps} />);
    
    fireEvent.click(screen.getByText('+'));
    
    await waitFor(() => {
      const multipleTPSwitch = screen.getByRole('switch', { name: /consider multiple tps/i });
      fireEvent.click(multipleTPSwitch);
    });

    await waitFor(() => {
      expect(mockOnUpdate).toHaveBeenCalledWith(
        expect.objectContaining({
          considerMultipleTP: false
        })
      );
    });
  });

  it('shows TP weights when weighted method is selected', async () => {
    render(<RiskRewardBlock {...defaultProps} />);
    
    fireEvent.click(screen.getByText('+'));
    
    await waitFor(() => {
      expect(screen.getByText('Take Profit Weights')).toBeInTheDocument();
      expect(screen.getByText('TP1')).toBeInTheDocument();
      expect(screen.getByText('TP2')).toBeInTheDocument();
      expect(screen.getByText('TP3')).toBeInTheDocument();
    });
  });

  it('updates TP weights correctly', async () => {
    render(<RiskRewardBlock {...defaultProps} />);
    
    fireEvent.click(screen.getByText('+'));
    
    await waitFor(() => {
      const weightSliders = screen.getAllByRole('slider');
      // Find TP1 weight slider (after minimum ratio slider)
      const tp1Slider = weightSliders[1];
      
      fireEvent.change(tp1Slider, { target: { value: '60' } });
    });

    await waitFor(() => {
      expect(mockOnUpdate).toHaveBeenCalledWith(
        expect.objectContaining({
          tpWeights: expect.arrayContaining([0.6, expect.any(Number), expect.any(Number)])
        })
      );
    });
  });

  it('changes risk tolerance mode', async () => {
    render(<RiskRewardBlock {...defaultProps} />);
    
    fireEvent.click(screen.getByText('+'));
    
    await waitFor(() => {
      const toleranceSelect = screen.getByDisplayValue('Moderate (Small deviation allowed)');
      fireEvent.click(toleranceSelect);
    });

    const strictOption = screen.getByText('Strict (Exact ratio required)');
    fireEvent.click(strictOption);

    await waitFor(() => {
      expect(mockOnUpdate).toHaveBeenCalledWith(
        expect.objectContaining({
          riskToleranceMode: 'strict'
        })
      );
    });
  });

  it('toggles dynamic adjustment', async () => {
    render(<RiskRewardBlock {...defaultProps} />);
    
    fireEvent.click(screen.getByText('+'));
    
    await waitFor(() => {
      const dynamicSwitch = screen.getByRole('switch', { name: /dynamic adjustment/i });
      fireEvent.click(dynamicSwitch);
    });

    await waitFor(() => {
      expect(mockOnUpdate).toHaveBeenCalledWith(
        expect.objectContaining({
          dynamicAdjustment: true
        })
      );
    });
  });

  it('handles signals with missing take profit levels', () => {
    const incompleteSignal: SignalData = {
      symbol: 'EURUSD',
      action: 'BUY',
      entry: 1.1000,
      stopLoss: 1.0950
      // No take profit levels
    };

    render(
      <RiskRewardBlock 
        {...defaultProps} 
        testSignal={incompleteSignal}
      />
    );

    // Should show 0 ratio for incomplete signals
    expect(screen.getByText('1:0.00')).toBeInTheDocument();
  });

  it('handles SELL signals correctly', () => {
    const sellSignal: SignalData = {
      symbol: 'EURUSD',
      action: 'SELL',
      entry: 1.1000,
      stopLoss: 1.1050,
      takeProfit1: 1.0925,
      takeProfit2: 1.0850
    };

    render(
      <RiskRewardBlock 
        {...defaultProps} 
        testSignal={sellSignal}
      />
    );

    // Risk: 1.1050 - 1.1000 = 50 pips
    // TP1: 1.1000 - 1.0925 = 75 pips
    // Should calculate correctly for SELL
    expect(screen.getByText(/1:1\./)).toBeInTheDocument();
  });

  it('shows calculation breakdown when expanded', async () => {
    render(
      <RiskRewardBlock 
        {...defaultProps} 
        testSignal={testSignal}
      />
    );
    
    fireEvent.click(screen.getByText('+'));
    
    await waitFor(() => {
      expect(screen.getByText('Calculation Breakdown')).toBeInTheDocument();
      expect(screen.getByText('TP1')).toBeInTheDocument();
      expect(screen.getByText('TP2')).toBeInTheDocument();
    });
  });

  it('shows warning for signals below minimum ratio', () => {
    const poorSignal: SignalData = {
      symbol: 'EURUSD',
      action: 'BUY',
      entry: 1.1000,
      stopLoss: 1.0950,
      takeProfit1: 1.1025 // Very low TP, poor R:R
    };

    render(
      <RiskRewardBlock 
        {...defaultProps} 
        testSignal={poorSignal}
      />
    );

    expect(screen.getByText('Signal does not meet minimum R:R requirements')).toBeInTheDocument();
  });

  it('calls onDelete when delete button is clicked', () => {
    render(<RiskRewardBlock {...defaultProps} />);
    
    const deleteButton = screen.getByText('×');
    fireEvent.click(deleteButton);

    expect(mockOnDelete).toHaveBeenCalledTimes(1);
  });

  it('handles different symbol pip values', () => {
    const jpySignal: SignalData = {
      symbol: 'USDJPY',
      action: 'BUY',
      entry: 150.00,
      stopLoss: 149.50,
      takeProfit1: 150.75
    };

    render(
      <RiskRewardBlock 
        {...defaultProps} 
        testSignal={jpySignal}
      />
    );

    // JPY pairs use 0.01 pip value instead of 0.0001
    // Should calculate correctly with different pip values
    expect(screen.getByText(/1:1\./)).toBeInTheDocument();
  });

  it('shows confidence level in results', () => {
    render(
      <RiskRewardBlock 
        {...defaultProps} 
        testSignal={testSignal}
      />
    );

    expect(screen.getByText('Confidence')).toBeInTheDocument();
    expect(screen.getByText(/\d+%/)).toBeInTheDocument();
  });
});

// Integration tests for strategy builder connection
describe('RiskRewardBlock Integration', () => {
  const mockOnUpdate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('provides correct configuration for strategy flow', () => {
    const config: RiskRewardConfig = {
      minimumRatio: 2.0,
      calculationMethod: 'simple',
      considerMultipleTP: false,
      tpWeights: [1.0, 0.0, 0.0, 0.0, 0.0],
      riskToleranceMode: 'strict',
      dynamicAdjustment: true
    };

    render(
      <RiskRewardBlock
        id="test-block"
        config={config}
        onUpdate={mockOnUpdate}
      />
    );

    expect(mockOnUpdate).toHaveBeenCalledWith(config);
  });

  it('shows connection points for strategy builder', () => {
    render(
      <RiskRewardBlock
        id="test-block"
        config={{
          minimumRatio: 1.5,
          calculationMethod: 'weighted',
          considerMultipleTP: true,
          tpWeights: [0.5, 0.3, 0.2, 0.0, 0.0],
          riskToleranceMode: 'moderate',
          dynamicAdjustment: false
        }}
        onUpdate={vi.fn()}
      />
    );

    expect(screen.getByText('Signal In')).toBeInTheDocument();
    expect(screen.getByText('Filtered Out')).toBeInTheDocument();
  });

  it('updates connection status based on signal filtering', () => {
    const passingSignal: SignalData = {
      symbol: 'EURUSD',
      action: 'BUY',
      entry: 1.1000,
      stopLoss: 1.0950,
      takeProfit1: 1.1125 // High TP for good R:R
    };

    render(
      <RiskRewardBlock
        id="test-block"
        config={{
          minimumRatio: 1.5,
          calculationMethod: 'simple',
          considerMultipleTP: false,
          tpWeights: [1.0, 0.0, 0.0, 0.0, 0.0],
          riskToleranceMode: 'moderate',
          dynamicAdjustment: false
        }}
        testSignal={passingSignal}
        onUpdate={vi.fn()}
      />
    );

    // Connection point should show green for passing signal
    const connectionPoints = screen.getAllByRole('generic');
    const outputConnection = connectionPoints.find(el => 
      el.className?.includes('bg-green-500')
    );
    expect(outputConnection).toBeInTheDocument();
  });
});