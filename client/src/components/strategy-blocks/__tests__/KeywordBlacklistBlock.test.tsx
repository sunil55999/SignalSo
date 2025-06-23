import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import KeywordBlacklistBlock, { 
  KeywordBlacklistConfig, 
  KeywordBlacklistBlockProps 
} from '../KeywordBlacklistBlock';

const defaultConfig: KeywordBlacklistConfig = {
  keywords: [],
  caseSensitive: false,
  wholeWordsOnly: true,
  enableSystemKeywords: true,
  matchMode: 'any',
  logBlockedSignals: true,
  notifyOnBlock: true,
};

const defaultProps: KeywordBlacklistBlockProps = {
  id: 'blacklist-1',
  config: defaultConfig,
  onUpdate: vi.fn(),
  onDelete: vi.fn(),
};

describe('KeywordBlacklistBlock', () => {
  const mockOnUpdate = vi.fn();
  const mockOnDelete = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders with default configuration', () => {
    render(<KeywordBlacklistBlock {...defaultProps} onUpdate={mockOnUpdate} onDelete={mockOnDelete} />);

    expect(screen.getByText('Keyword Blacklist')).toBeInTheDocument();
    expect(screen.getByText('Blacklisted Keywords')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Enter keyword to blacklist')).toBeInTheDocument();
  });

  it('adds new keywords when typing and pressing enter', () => {
    render(<KeywordBlacklistBlock {...defaultProps} onUpdate={mockOnUpdate} />);

    const input = screen.getByPlaceholderText('Enter keyword to blacklist');
    fireEvent.change(input, { target: { value: 'high risk' } });
    fireEvent.keyPress(input, { key: 'Enter' });

    expect(mockOnUpdate).toHaveBeenCalledWith(
      expect.objectContaining({
        keywords: ['high risk']
      })
    );
  });

  it('adds new keywords when clicking the plus button', () => {
    render(<KeywordBlacklistBlock {...defaultProps} onUpdate={mockOnUpdate} />);

    const input = screen.getByPlaceholderText('Enter keyword to blacklist');
    const addButton = screen.getByRole('button', { name: '' }); // Plus icon button

    fireEvent.change(input, { target: { value: 'manual only' } });
    fireEvent.click(addButton);

    expect(mockOnUpdate).toHaveBeenCalledWith(
      expect.objectContaining({
        keywords: ['manual only']
      })
    );
  });

  it('prevents adding duplicate keywords', () => {
    const configWithKeywords = {
      ...defaultConfig,
      keywords: ['high risk']
    };

    render(
      <KeywordBlacklistBlock 
        {...defaultProps} 
        config={configWithKeywords}
        onUpdate={mockOnUpdate}
      />
    );

    const input = screen.getByPlaceholderText('Enter keyword to blacklist');
    fireEvent.change(input, { target: { value: 'high risk' } });
    fireEvent.keyPress(input, { key: 'Enter' });

    // Should not call onUpdate since keyword already exists
    expect(mockOnUpdate).not.toHaveBeenCalled();
  });

  it('removes keywords when clicking the X button', () => {
    const configWithKeywords = {
      ...defaultConfig,
      keywords: ['high risk', 'manual only']
    };

    render(
      <KeywordBlacklistBlock 
        {...defaultProps} 
        config={configWithKeywords}
        onUpdate={mockOnUpdate}
      />
    );

    // Find the X button for the first keyword
    const removeButtons = screen.getAllByRole('button');
    const removeButton = removeButtons.find(button => 
      button.textContent === '' && button.className.includes('text-gray-500')
    );
    
    if (removeButton) {
      fireEvent.click(removeButton);
    }

    expect(mockOnUpdate).toHaveBeenCalledWith(
      expect.objectContaining({
        keywords: expect.arrayContaining(['manual only'])
      })
    );
  });

  it('shows system keywords when enabled', () => {
    render(<KeywordBlacklistBlock {...defaultProps} />);

    expect(screen.getByText('System Keywords:')).toBeInTheDocument();
    expect(screen.getByText('high risk')).toBeInTheDocument();
    expect(screen.getByText('no sl')).toBeInTheDocument();
  });

  it('hides system keywords when disabled', () => {
    const configWithoutSystem = {
      ...defaultConfig,
      enableSystemKeywords: false
    };

    render(<KeywordBlacklistBlock {...defaultProps} config={configWithoutSystem} />);

    expect(screen.queryByText('System Keywords:')).not.toBeInTheDocument();
  });

  it('blocks signal when keyword matches', () => {
    const configWithKeywords = {
      ...defaultConfig,
      keywords: ['dangerous'],
      enableSystemKeywords: false
    };

    const testSignal = {
      rawMessage: 'This is a dangerous trade with high risk',
      symbol: 'EURUSD',
      action: 'BUY'
    };

    render(
      <KeywordBlacklistBlock 
        {...defaultProps} 
        config={configWithKeywords}
        testSignal={testSignal}
      />
    );

    expect(screen.getByText('Signal Blocked')).toBeInTheDocument();
    expect(screen.getByText(/matched keywords: dangerous/)).toBeInTheDocument();
  });

  it('allows signal when no keywords match', () => {
    const configWithKeywords = {
      ...defaultConfig,
      keywords: ['dangerous'],
      enableSystemKeywords: false
    };

    const testSignal = {
      rawMessage: 'This is a safe trade with good setup',
      symbol: 'EURUSD',
      action: 'BUY'
    };

    render(
      <KeywordBlacklistBlock 
        {...defaultProps} 
        config={configWithKeywords}
        testSignal={testSignal}
      />
    );

    expect(screen.getByText('Signal Allowed')).toBeInTheDocument();
    expect(screen.getByText(/No keyword matches found/)).toBeInTheDocument();
  });

  it('respects case sensitivity setting', () => {
    const caseSensitiveConfig = {
      ...defaultConfig,
      keywords: ['RISK'],
      caseSensitive: true,
      enableSystemKeywords: false
    };

    const testSignal = {
      rawMessage: 'This trade has some risk',
      symbol: 'EURUSD'
    };

    render(
      <KeywordBlacklistBlock 
        {...defaultProps} 
        config={caseSensitiveConfig}
        testSignal={testSignal}
      />
    );

    // Should not match because 'risk' != 'RISK' when case sensitive
    expect(screen.getByText('Signal Allowed')).toBeInTheDocument();
  });

  it('respects whole words only setting', () => {
    const wholeWordsConfig = {
      ...defaultConfig,
      keywords: ['risk'],
      wholeWordsOnly: false,
      enableSystemKeywords: false
    };

    const testSignal = {
      rawMessage: 'This is a risky trade',
      symbol: 'EURUSD'
    };

    render(
      <KeywordBlacklistBlock 
        {...defaultProps} 
        config={wholeWordsConfig}
        testSignal={testSignal}
      />
    );

    // Should match because 'risk' is contained in 'risky' when wholeWordsOnly is false
    expect(screen.getByText('Signal Blocked')).toBeInTheDocument();
  });

  it('handles "all" match mode correctly', () => {
    const allMatchConfig = {
      ...defaultConfig,
      keywords: ['high', 'risk'],
      matchMode: 'all' as const,
      enableSystemKeywords: false
    };

    const testSignalPartial = {
      rawMessage: 'This is a high confidence trade',
      symbol: 'EURUSD'
    };

    const testSignalFull = {
      rawMessage: 'This is a high risk trade',
      symbol: 'EURUSD'
    };

    // Test partial match (should allow)
    const { rerender } = render(
      <KeywordBlacklistBlock 
        {...defaultProps} 
        config={allMatchConfig}
        testSignal={testSignalPartial}
      />
    );

    expect(screen.getByText('Signal Allowed')).toBeInTheDocument();

    // Test full match (should block)
    rerender(
      <KeywordBlacklistBlock 
        {...defaultProps} 
        config={allMatchConfig}
        testSignal={testSignalFull}
      />
    );

    expect(screen.getByText('Signal Blocked')).toBeInTheDocument();
  });

  it('opens advanced settings when clicked', () => {
    render(<KeywordBlacklistBlock {...defaultProps} />);

    fireEvent.click(screen.getByText('Advanced Settings'));

    expect(screen.getByText('Case Sensitive')).toBeInTheDocument();
    expect(screen.getByText('Whole Words Only')).toBeInTheDocument();
    expect(screen.getByText('Match Mode')).toBeInTheDocument();
  });

  it('toggles advanced settings correctly', () => {
    render(<KeywordBlacklistBlock {...defaultProps} onUpdate={mockOnUpdate} />);

    fireEvent.click(screen.getByText('Advanced Settings'));

    // Toggle case sensitivity
    const caseSensitiveSwitch = screen.getByRole('switch', { name: /case sensitive/i });
    fireEvent.click(caseSensitiveSwitch);

    expect(mockOnUpdate).toHaveBeenCalledWith(
      expect.objectContaining({
        caseSensitive: true
      })
    );
  });

  it('opens bulk add dialog when clicked', () => {
    render(<KeywordBlacklistBlock {...defaultProps} />);

    fireEvent.click(screen.getByText('Bulk Add'));

    expect(screen.getByText('Add multiple keywords (one per line or comma-separated)')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/high risk/)).toBeInTheDocument();
  });

  it('adds multiple keywords via bulk add', () => {
    render(<KeywordBlacklistBlock {...defaultProps} onUpdate={mockOnUpdate} />);

    fireEvent.click(screen.getByText('Bulk Add'));

    const textarea = screen.getByPlaceholderText(/high risk/);
    fireEvent.change(textarea, { 
      target: { value: 'keyword1\nkeyword2,keyword3' } 
    });

    fireEvent.click(screen.getByText('Add Keywords'));

    expect(mockOnUpdate).toHaveBeenCalledWith(
      expect.objectContaining({
        keywords: ['keyword1', 'keyword2', 'keyword3']
      })
    );
  });

  it('adds suggested keywords when clicked', () => {
    render(<KeywordBlacklistBlock {...defaultProps} onUpdate={mockOnUpdate} />);

    const suggestedButton = screen.getByText('+avoid');
    fireEvent.click(suggestedButton);

    expect(mockOnUpdate).toHaveBeenCalledWith(
      expect.objectContaining({
        keywords: ['avoid']
      })
    );
  });

  it('clears all keywords when clear all is clicked', () => {
    const configWithKeywords = {
      ...defaultConfig,
      keywords: ['keyword1', 'keyword2']
    };

    render(
      <KeywordBlacklistBlock 
        {...defaultProps} 
        config={configWithKeywords}
        onUpdate={mockOnUpdate}
      />
    );

    fireEvent.click(screen.getByText('Clear All'));

    expect(mockOnUpdate).toHaveBeenCalledWith(
      expect.objectContaining({
        keywords: []
      })
    );
  });

  it('displays test signal content correctly', () => {
    const testSignal = {
      rawMessage: 'This is a very long test signal message that should be truncated when displayed in the UI because it exceeds the maximum length',
      symbol: 'EURUSD',
      action: 'BUY'
    };

    render(<KeywordBlacklistBlock {...defaultProps} testSignal={testSignal} />);

    expect(screen.getByText('Test Signal')).toBeInTheDocument();
    expect(screen.getByText('Symbol: EURUSD')).toBeInTheDocument();
    expect(screen.getByText('Action: BUY')).toBeInTheDocument();
    
    // Should truncate long messages
    expect(screen.getByText(/This is a very long test signal message/)).toBeInTheDocument();
  });

  it('shows correct status indicators', () => {
    // Test inactive state (no keywords)
    const inactiveConfig = {
      ...defaultConfig,
      keywords: [],
      enableSystemKeywords: false
    };

    const { rerender } = render(
      <KeywordBlacklistBlock {...defaultProps} config={inactiveConfig} />
    );

    expect(screen.getByText('Inactive')).toBeInTheDocument();

    // Test active state (with keywords, signal allowed)
    const activeConfig = {
      ...defaultConfig,
      keywords: ['test'],
      enableSystemKeywords: false
    };

    const allowedSignal = {
      rawMessage: 'This is a good trade',
      symbol: 'EURUSD'
    };

    rerender(
      <KeywordBlacklistBlock 
        {...defaultProps} 
        config={activeConfig}
        testSignal={allowedSignal}
      />
    );

    expect(screen.getByText('Active')).toBeInTheDocument();

    // Test blocked state
    const blockedSignal = {
      rawMessage: 'This is a test trade',
      symbol: 'EURUSD'
    };

    rerender(
      <KeywordBlacklistBlock 
        {...defaultProps} 
        config={activeConfig}
        testSignal={blockedSignal}
      />
    );

    expect(screen.getByText('Blocked')).toBeInTheDocument();
  });

  it('calls onDelete when delete button is clicked', () => {
    render(<KeywordBlacklistBlock {...defaultProps} onDelete={mockOnDelete} />);
    
    const deleteButton = screen.getByText('×');
    fireEvent.click(deleteButton);

    expect(mockOnDelete).toHaveBeenCalledTimes(1);
  });

  it('handles empty and whitespace keywords correctly', () => {
    render(<KeywordBlacklistBlock {...defaultProps} onUpdate={mockOnUpdate} />);

    const input = screen.getByPlaceholderText('Enter keyword to blacklist');
    
    // Try adding empty keyword
    fireEvent.change(input, { target: { value: '' } });
    fireEvent.keyPress(input, { key: 'Enter' });

    expect(mockOnUpdate).not.toHaveBeenCalled();

    // Try adding whitespace-only keyword
    fireEvent.change(input, { target: { value: '   ' } });
    fireEvent.keyPress(input, { key: 'Enter' });

    expect(mockOnUpdate).not.toHaveBeenCalled();
  });

  it('shows confidence percentage in results', () => {
    const configWithKeywords = {
      ...defaultConfig,
      keywords: ['risk'],
      enableSystemKeywords: false
    };

    const testSignal = {
      rawMessage: 'This trade has risk',
      symbol: 'EURUSD'
    };

    render(
      <KeywordBlacklistBlock 
        {...defaultProps} 
        config={configWithKeywords}
        testSignal={testSignal}
      />
    );

    expect(screen.getByText(/\d+% confidence/)).toBeInTheDocument();
  });
});

// Integration tests for strategy builder connection
describe('KeywordBlacklistBlock Integration', () => {
  const mockOnUpdate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('integrates with strategy builder workflow', () => {
    const { rerender } = render(
      <KeywordBlacklistBlock {...defaultProps} onUpdate={mockOnUpdate} />
    );

    // Add a keyword
    const input = screen.getByPlaceholderText('Enter keyword to blacklist');
    fireEvent.change(input, { target: { value: 'dangerous' } });
    fireEvent.keyPress(input, { key: 'Enter' });

    expect(mockOnUpdate).toHaveBeenCalledWith(
      expect.objectContaining({ keywords: ['dangerous'] })
    );

    // Simulate props update from parent
    const updatedConfig = { ...defaultConfig, keywords: ['dangerous'] };
    rerender(
      <KeywordBlacklistBlock {...defaultProps} config={updatedConfig} onUpdate={mockOnUpdate} />
    );

    expect(screen.getByText('dangerous')).toBeInTheDocument();
  });

  it('handles rapid configuration updates efficiently', () => {
    render(<KeywordBlacklistBlock {...defaultProps} onUpdate={mockOnUpdate} />);

    const input = screen.getByPlaceholderText('Enter keyword to blacklist');
    
    // Simulate rapid keyword additions
    fireEvent.change(input, { target: { value: 'keyword1' } });
    fireEvent.keyPress(input, { key: 'Enter' });
    
    fireEvent.change(input, { target: { value: 'keyword2' } });
    fireEvent.keyPress(input, { key: 'Enter' });
    
    fireEvent.change(input, { target: { value: 'keyword3' } });
    fireEvent.keyPress(input, { key: 'Enter' });

    // Should call onUpdate for each addition
    expect(mockOnUpdate).toHaveBeenCalledTimes(3);
  });

  it('maintains state consistency across re-renders', () => {
    const { rerender } = render(<KeywordBlacklistBlock {...defaultProps} />);

    // Open advanced settings
    fireEvent.click(screen.getByText('Advanced Settings'));
    expect(screen.getByText('Case Sensitive')).toBeInTheDocument();

    // Re-render with same props
    rerender(<KeywordBlacklistBlock {...defaultProps} />);

    // Advanced settings should still be open
    expect(screen.getByText('Case Sensitive')).toBeInTheDocument();
  });
});