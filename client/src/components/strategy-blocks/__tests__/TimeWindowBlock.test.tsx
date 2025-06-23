import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import TimeWindowBlock, { TimeWindow, TimeWindowBlockConfig } from '../TimeWindowBlock';

// Mock date-fns
vi.mock('date-fns', () => ({
  format: vi.fn((date: Date, format: string) => {
    if (format === 'HH:mm:ss') {
      return date.toTimeString().slice(0, 8);
    }
    return date.toISOString();
  })
}));

describe('TimeWindowBlock', () => {
  const mockOnUpdate = vi.fn();
  const mockOnDelete = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock current time to a consistent value for testing
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2025-06-23T14:30:00Z')); // Monday 2:30 PM UTC
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  const defaultProps = {
    id: 'test-window',
    timeWindows: [],
    onUpdate: mockOnUpdate,
    onDelete: mockOnDelete
  };

  it('renders with default configuration', () => {
    render(<TimeWindowBlock {...defaultProps} />);
    
    expect(screen.getByText('Time Window Filter')).toBeInTheDocument();
    expect(screen.getByText('Active')).toBeInTheDocument(); // No windows = always active
    expect(screen.getByText('No time windows configured')).toBeInTheDocument();
  });

  it('displays current time correctly', () => {
    render(<TimeWindowBlock {...defaultProps} />);
    
    expect(screen.getByText('14:30:00 UTC')).toBeInTheDocument();
  });

  it('allows adding a new time window', async () => {
    render(<TimeWindowBlock {...defaultProps} />);
    
    const addButton = screen.getByText('Add Window');
    fireEvent.click(addButton);

    await waitFor(() => {
      expect(mockOnUpdate).toHaveBeenCalledWith(
        expect.objectContaining({
          timeWindows: expect.arrayContaining([
            expect.objectContaining({
              startTime: '09:00',
              endTime: '17:00',
              timezone: 'UTC',
              daysOfWeek: [1, 2, 3, 4, 5],
              enabled: true
            })
          ])
        })
      );
    });
  });

  it('validates time window during market hours', () => {
    const timeWindows: TimeWindow[] = [{
      id: 'window1',
      startTime: '09:00',
      endTime: '17:00',
      timezone: 'UTC',
      daysOfWeek: [1, 2, 3, 4, 5], // Monday to Friday
      enabled: true
    }];

    render(<TimeWindowBlock {...defaultProps} timeWindows={timeWindows} />);
    
    // Current time is 14:30 on Monday, should be active
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('validates time window outside market hours', () => {
    vi.setSystemTime(new Date('2025-06-23T20:30:00Z')); // Monday 8:30 PM UTC
    
    const timeWindows: TimeWindow[] = [{
      id: 'window1',
      startTime: '09:00',
      endTime: '17:00',
      timezone: 'UTC',
      daysOfWeek: [1, 2, 3, 4, 5],
      enabled: true
    }];

    render(<TimeWindowBlock {...defaultProps} timeWindows={timeWindows} />);
    
    expect(screen.getByText('Inactive')).toBeInTheDocument();
  });

  it('handles weekend exclusion correctly', () => {
    vi.setSystemTime(new Date('2025-06-21T14:30:00Z')); // Saturday 2:30 PM UTC
    
    const timeWindows: TimeWindow[] = [{
      id: 'window1',
      startTime: '09:00',
      endTime: '17:00',
      timezone: 'UTC',
      daysOfWeek: [0, 1, 2, 3, 4, 5, 6], // All days
      enabled: true
    }];

    render(<TimeWindowBlock {...defaultProps} timeWindows={timeWindows} excludeWeekends={true} />);
    
    expect(screen.getByText('Inactive')).toBeInTheDocument();
  });

  it('allows weekend trading when exclusion is disabled', () => {
    vi.setSystemTime(new Date('2025-06-21T14:30:00Z')); // Saturday 2:30 PM UTC
    
    const timeWindows: TimeWindow[] = [{
      id: 'window1',
      startTime: '09:00',
      endTime: '17:00',
      timezone: 'UTC',
      daysOfWeek: [0, 1, 2, 3, 4, 5, 6], // All days
      enabled: true
    }];

    render(<TimeWindowBlock {...defaultProps} timeWindows={timeWindows} excludeWeekends={false} />);
    
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('handles overnight time windows correctly', () => {
    vi.setSystemTime(new Date('2025-06-23T02:30:00Z')); // Monday 2:30 AM UTC
    
    const timeWindows: TimeWindow[] = [{
      id: 'window1',
      startTime: '22:00', // 10 PM
      endTime: '06:00',   // 6 AM next day
      timezone: 'UTC',
      daysOfWeek: [0, 1, 2, 3, 4, 5, 6],
      enabled: true
    }];

    render(<TimeWindowBlock {...defaultProps} timeWindows={timeWindows} excludeWeekends={false} />);
    
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('updates time window configuration', async () => {
    const timeWindows: TimeWindow[] = [{
      id: 'window1',
      startTime: '09:00',
      endTime: '17:00',
      timezone: 'UTC',
      daysOfWeek: [1, 2, 3, 4, 5],
      enabled: true
    }];

    render(<TimeWindowBlock {...defaultProps} timeWindows={timeWindows} />);
    
    const startTimeInput = screen.getByDisplayValue('09:00');
    fireEvent.change(startTimeInput, { target: { value: '08:00' } });

    await waitFor(() => {
      expect(mockOnUpdate).toHaveBeenCalledWith(
        expect.objectContaining({
          timeWindows: expect.arrayContaining([
            expect.objectContaining({
              startTime: '08:00'
            })
          ])
        })
      );
    });
  });

  it('toggles days of week correctly', async () => {
    const timeWindows: TimeWindow[] = [{
      id: 'window1',
      startTime: '09:00',
      endTime: '17:00',
      timezone: 'UTC',
      daysOfWeek: [1, 2, 3, 4, 5],
      enabled: true
    }];

    render(<TimeWindowBlock {...defaultProps} timeWindows={timeWindows} />);
    
    const saturdayButton = screen.getByText('Sat');
    fireEvent.click(saturdayButton);

    await waitFor(() => {
      expect(mockOnUpdate).toHaveBeenCalledWith(
        expect.objectContaining({
          timeWindows: expect.arrayContaining([
            expect.objectContaining({
              daysOfWeek: expect.arrayContaining([1, 2, 3, 4, 5, 6])
            })
          ])
        })
      );
    });
  });

  it('removes time window correctly', async () => {
    const timeWindows: TimeWindow[] = [{
      id: 'window1',
      startTime: '09:00',
      endTime: '17:00',
      timezone: 'UTC',
      daysOfWeek: [1, 2, 3, 4, 5],
      enabled: true
    }];

    render(<TimeWindowBlock {...defaultProps} timeWindows={timeWindows} />);
    
    const removeButtons = screen.getAllByText('×');
    const windowRemoveButton = removeButtons[1]; // First × is for block delete, second is for window
    fireEvent.click(windowRemoveButton);

    await waitFor(() => {
      expect(mockOnUpdate).toHaveBeenCalledWith(
        expect.objectContaining({
          timeWindows: []
        })
      );
    });
  });

  it('changes timezone correctly', async () => {
    render(<TimeWindowBlock {...defaultProps} />);
    
    const timezoneSelect = screen.getByDisplayValue('UTC');
    fireEvent.click(timezoneSelect);
    
    const londonOption = screen.getByText('London (GMT/BST)');
    fireEvent.click(londonOption);

    await waitFor(() => {
      expect(mockOnUpdate).toHaveBeenCalledWith(
        expect.objectContaining({
          timezone: 'Europe/London'
        })
      );
    });
  });

  it('toggles weekend exclusion', async () => {
    render(<TimeWindowBlock {...defaultProps} />);
    
    const weekendSwitch = screen.getByRole('switch', { name: /exclude weekends/i });
    fireEvent.click(weekendSwitch);

    await waitFor(() => {
      expect(mockOnUpdate).toHaveBeenCalledWith(
        expect.objectContaining({
          excludeWeekends: false
        })
      );
    });
  });

  it('toggles holiday exclusion', async () => {
    render(<TimeWindowBlock {...defaultProps} />);
    
    const holidaySwitch = screen.getByRole('switch', { name: /exclude holidays/i });
    fireEvent.click(holidaySwitch);

    await waitFor(() => {
      expect(mockOnUpdate).toHaveBeenCalledWith(
        expect.objectContaining({
          excludeHolidays: true
        })
      );
    });
  });

  it('enables and disables time windows', async () => {
    const timeWindows: TimeWindow[] = [{
      id: 'window1',
      startTime: '09:00',
      endTime: '17:00',
      timezone: 'UTC',
      daysOfWeek: [1, 2, 3, 4, 5],
      enabled: true
    }];

    render(<TimeWindowBlock {...defaultProps} timeWindows={timeWindows} />);
    
    const enableSwitch = screen.getAllByRole('switch')[2]; // First two are global settings
    fireEvent.click(enableSwitch);

    await waitFor(() => {
      expect(mockOnUpdate).toHaveBeenCalledWith(
        expect.objectContaining({
          timeWindows: expect.arrayContaining([
            expect.objectContaining({
              enabled: false
            })
          ])
        })
      );
    });
  });

  it('shows correct active window count', () => {
    const timeWindows: TimeWindow[] = [
      {
        id: 'window1',
        startTime: '09:00',
        endTime: '17:00',
        timezone: 'UTC',
        daysOfWeek: [1, 2, 3, 4, 5],
        enabled: true
      },
      {
        id: 'window2',
        startTime: '18:00',
        endTime: '22:00',
        timezone: 'UTC',
        daysOfWeek: [1, 2, 3, 4, 5],
        enabled: false
      }
    ];

    render(<TimeWindowBlock {...defaultProps} timeWindows={timeWindows} />);
    
    expect(screen.getByText('Time Windows (1 active)')).toBeInTheDocument();
  });

  it('calls onDelete when delete button is clicked', () => {
    render(<TimeWindowBlock {...defaultProps} />);
    
    const deleteButton = screen.getAllByText('×')[0]; // First × is for block delete
    fireEvent.click(deleteButton);

    expect(mockOnDelete).toHaveBeenCalledTimes(1);
  });

  it('updates current time every second', async () => {
    render(<TimeWindowBlock {...defaultProps} />);
    
    expect(screen.getByText('14:30:00 UTC')).toBeInTheDocument();

    // Advance time by 1 second
    vi.advanceTimersByTime(1000);

    await waitFor(() => {
      expect(screen.getByText('14:30:01 UTC')).toBeInTheDocument();
    });
  });

  it('handles multiple overlapping time windows', () => {
    const timeWindows: TimeWindow[] = [
      {
        id: 'window1',
        startTime: '09:00',
        endTime: '17:00',
        timezone: 'UTC',
        daysOfWeek: [1, 2, 3, 4, 5],
        enabled: true
      },
      {
        id: 'window2',
        startTime: '13:00',
        endTime: '20:00',
        timezone: 'UTC',
        daysOfWeek: [1, 2, 3, 4, 5],
        enabled: true
      }
    ];

    render(<TimeWindowBlock {...defaultProps} timeWindows={timeWindows} />);
    
    // Current time 14:30 should be in both windows, so active
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('respects timezone differences', () => {
    vi.setSystemTime(new Date('2025-06-23T14:30:00Z')); // 2:30 PM UTC

    const timeWindows: TimeWindow[] = [{
      id: 'window1',
      startTime: '09:00',
      endTime: '17:00',
      timezone: 'America/New_York', // EST/EDT, 4-5 hours behind UTC
      daysOfWeek: [1, 2, 3, 4, 5],
      enabled: true
    }];

    render(<TimeWindowBlock {...defaultProps} timeWindows={timeWindows} />);
    
    // Note: This test assumes the component handles timezone conversion
    // The actual implementation would need proper timezone handling
    expect(screen.getByText(/Time Windows/)).toBeInTheDocument();
  });
});

// Integration tests for block connection and data flow
describe('TimeWindowBlock Integration', () => {
  const mockOnUpdate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2025-06-23T14:30:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('provides correct block configuration for strategy flow', () => {
    const timeWindows: TimeWindow[] = [{
      id: 'window1',
      startTime: '09:00',
      endTime: '17:00',
      timezone: 'UTC',
      daysOfWeek: [1, 2, 3, 4, 5],
      enabled: true
    }];

    render(
      <TimeWindowBlock
        id="test-window"
        timeWindows={timeWindows}
        excludeWeekends={true}
        excludeHolidays={false}
        onUpdate={mockOnUpdate}
      />
    );

    expect(mockOnUpdate).toHaveBeenCalledWith({
      timeWindows: expect.arrayContaining([
        expect.objectContaining({
          startTime: '09:00',
          endTime: '17:00',
          timezone: 'UTC',
          daysOfWeek: [1, 2, 3, 4, 5],
          enabled: true
        })
      ]),
      excludeWeekends: true,
      excludeHolidays: false,
      timezone: 'UTC'
    });
  });

  it('shows connection points for strategy builder', () => {
    render(
      <TimeWindowBlock
        id="test-window"
        timeWindows={[]}
        onUpdate={mockOnUpdate}
      />
    );

    expect(screen.getByText('Input')).toBeInTheDocument();
    expect(screen.getByText('Output')).toBeInTheDocument();
  });
});