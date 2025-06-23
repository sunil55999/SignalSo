import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Clock, Calendar, AlertCircle, Settings } from 'lucide-react';
import { format } from 'date-fns';

export interface TimeWindow {
  id: string;
  startTime: string; // HH:MM format
  endTime: string; // HH:MM format
  timezone: string;
  daysOfWeek: number[]; // 0-6, Sunday = 0
  enabled: boolean;
}

export interface TimeWindowBlockProps {
  id: string;
  title?: string;
  timeWindows: TimeWindow[];
  excludeWeekends?: boolean;
  excludeHolidays?: boolean;
  onUpdate: (config: TimeWindowBlockConfig) => void;
  onDelete?: () => void;
  className?: string;
}

export interface TimeWindowBlockConfig {
  timeWindows: TimeWindow[];
  excludeWeekends: boolean;
  excludeHolidays: boolean;
  timezone: string;
}

const TIMEZONES = [
  { value: 'UTC', label: 'UTC' },
  { value: 'America/New_York', label: 'New York (EST/EDT)' },
  { value: 'Europe/London', label: 'London (GMT/BST)' },
  { value: 'Europe/Frankfurt', label: 'Frankfurt (CET/CEST)' },
  { value: 'Asia/Tokyo', label: 'Tokyo (JST)' },
  { value: 'Asia/Singapore', label: 'Singapore (SGT)' },
  { value: 'Australia/Sydney', label: 'Sydney (AEST/AEDT)' },
];

const DAYS_OF_WEEK = [
  { value: 0, label: 'Sunday', short: 'Sun' },
  { value: 1, label: 'Monday', short: 'Mon' },
  { value: 2, label: 'Tuesday', short: 'Tue' },
  { value: 3, label: 'Wednesday', short: 'Wed' },
  { value: 4, label: 'Thursday', short: 'Thu' },
  { value: 5, label: 'Friday', short: 'Fri' },
  { value: 6, label: 'Saturday', short: 'Sat' },
];

export function TimeWindowBlock({
  id,
  title = "Time Window Filter",
  timeWindows: initialTimeWindows = [],
  excludeWeekends = true,
  excludeHolidays = false,
  onUpdate,
  onDelete,
  className = ""
}: TimeWindowBlockProps) {
  const [timeWindows, setTimeWindows] = useState<TimeWindow[]>(initialTimeWindows);
  const [excludeWeekendsState, setExcludeWeekends] = useState(excludeWeekends);
  const [excludeHolidaysState, setExcludeHolidays] = useState(excludeHolidays);
  const [defaultTimezone, setDefaultTimezone] = useState('UTC');
  const [currentTime, setCurrentTime] = useState(new Date());
  const [isWithinWindow, setIsWithinWindow] = useState(false);

  // Update current time every second
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // Check if current time is within any active window
  useEffect(() => {
    const checkTimeWindow = () => {
      if (timeWindows.length === 0) {
        setIsWithinWindow(true);
        return;
      }

      const now = new Date();
      const currentDay = now.getDay();
      const currentHour = now.getHours();
      const currentMinute = now.getMinutes();
      const currentTimeMinutes = currentHour * 60 + currentMinute;

      // Check weekend exclusion
      if (excludeWeekendsState && (currentDay === 0 || currentDay === 6)) {
        setIsWithinWindow(false);
        return;
      }

      // Check active time windows
      const inWindow = timeWindows.some(window => {
        if (!window.enabled) return false;
        if (!window.daysOfWeek.includes(currentDay)) return false;

        const [startHour, startMin] = window.startTime.split(':').map(Number);
        const [endHour, endMin] = window.endTime.split(':').map(Number);
        const startMinutes = startHour * 60 + startMin;
        const endMinutes = endHour * 60 + endMin;

        // Handle overnight windows (e.g., 22:00-06:00)
        if (startMinutes > endMinutes) {
          return currentTimeMinutes >= startMinutes || currentTimeMinutes <= endMinutes;
        } else {
          return currentTimeMinutes >= startMinutes && currentTimeMinutes <= endMinutes;
        }
      });

      setIsWithinWindow(inWindow);
    };

    checkTimeWindow();
  }, [timeWindows, excludeWeekendsState, currentTime]);

  // Notify parent of config changes
  useEffect(() => {
    onUpdate({
      timeWindows,
      excludeWeekends: excludeWeekendsState,
      excludeHolidays: excludeHolidaysState,
      timezone: defaultTimezone
    });
  }, [timeWindows, excludeWeekendsState, excludeHolidaysState, defaultTimezone, onUpdate]);

  const addTimeWindow = () => {
    const newWindow: TimeWindow = {
      id: `window_${Date.now()}`,
      startTime: '09:00',
      endTime: '17:00',
      timezone: defaultTimezone,
      daysOfWeek: [1, 2, 3, 4, 5], // Monday to Friday
      enabled: true
    };
    setTimeWindows([...timeWindows, newWindow]);
  };

  const updateTimeWindow = (windowId: string, updates: Partial<TimeWindow>) => {
    setTimeWindows(windows =>
      windows.map(window =>
        window.id === windowId ? { ...window, ...updates } : window
      )
    );
  };

  const removeTimeWindow = (windowId: string) => {
    setTimeWindows(windows => windows.filter(window => window.id !== windowId));
  };

  const toggleDay = (windowId: string, day: number) => {
    const window = timeWindows.find(w => w.id === windowId);
    if (!window) return;

    const newDays = window.daysOfWeek.includes(day)
      ? window.daysOfWeek.filter(d => d !== day)
      : [...window.daysOfWeek, day].sort();

    updateTimeWindow(windowId, { daysOfWeek: newDays });
  };

  const formatTimeRange = (startTime: string, endTime: string) => {
    return `${startTime} - ${endTime}`;
  };

  const getActiveWindowsCount = () => {
    return timeWindows.filter(w => w.enabled).length;
  };

  return (
    <Card className={`strategy-block time-window-block ${className}`}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="flex items-center space-x-2">
          <Clock className="h-4 w-4" />
          <CardTitle className="text-sm font-medium">{title}</CardTitle>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant={isWithinWindow ? "default" : "secondary"}>
            {isWithinWindow ? "Active" : "Inactive"}
          </Badge>
          {onDelete && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onDelete}
              className="h-6 w-6 p-0"
            >
              ×
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Current Status */}
        <div className="flex items-center justify-between p-2 bg-muted rounded-lg">
          <div className="flex items-center space-x-2">
            <AlertCircle className="h-4 w-4" />
            <span className="text-sm">Current Time</span>
          </div>
          <span className="text-sm font-mono">
            {format(currentTime, 'HH:mm:ss')} {defaultTimezone}
          </span>
        </div>

        {/* Global Settings */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label htmlFor="default-timezone">Default Timezone</Label>
            <Select value={defaultTimezone} onValueChange={setDefaultTimezone}>
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TIMEZONES.map(tz => (
                  <SelectItem key={tz.value} value={tz.value}>
                    {tz.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center justify-between">
            <Label htmlFor="exclude-weekends">Exclude Weekends</Label>
            <Switch
              id="exclude-weekends"
              checked={excludeWeekendsState}
              onCheckedChange={setExcludeWeekends}
            />
          </div>

          <div className="flex items-center justify-between">
            <Label htmlFor="exclude-holidays">Exclude Holidays</Label>
            <Switch
              id="exclude-holidays"
              checked={excludeHolidaysState}
              onCheckedChange={setExcludeHolidays}
            />
          </div>
        </div>

        {/* Time Windows */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label>Time Windows ({getActiveWindowsCount()} active)</Label>
            <Button size="sm" onClick={addTimeWindow}>
              Add Window
            </Button>
          </div>

          {timeWindows.map(window => (
            <Card key={window.id} className="p-3">
              <div className="space-y-3">
                {/* Window Header */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Switch
                      checked={window.enabled}
                      onCheckedChange={(enabled) => updateTimeWindow(window.id, { enabled })}
                    />
                    <span className="text-sm font-medium">
                      {formatTimeRange(window.startTime, window.endTime)}
                    </span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeTimeWindow(window.id)}
                    className="h-6 w-6 p-0"
                  >
                    ×
                  </Button>
                </div>

                {/* Time Inputs */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="text-xs">Start Time</Label>
                    <Input
                      type="time"
                      value={window.startTime}
                      onChange={(e) => updateTimeWindow(window.id, { startTime: e.target.value })}
                      className="h-8"
                    />
                  </div>
                  <div>
                    <Label className="text-xs">End Time</Label>
                    <Input
                      type="time"
                      value={window.endTime}
                      onChange={(e) => updateTimeWindow(window.id, { endTime: e.target.value })}
                      className="h-8"
                    />
                  </div>
                </div>

                {/* Days of Week */}
                <div>
                  <Label className="text-xs">Active Days</Label>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {DAYS_OF_WEEK.map(day => (
                      <Button
                        key={day.value}
                        variant={window.daysOfWeek.includes(day.value) ? "default" : "outline"}
                        size="sm"
                        className="h-6 px-2 text-xs"
                        onClick={() => toggleDay(window.id, day.value)}
                      >
                        {day.short}
                      </Button>
                    ))}
                  </div>
                </div>

                {/* Timezone Override */}
                <div>
                  <Label className="text-xs">Timezone</Label>
                  <Select
                    value={window.timezone}
                    onValueChange={(timezone) => updateTimeWindow(window.id, { timezone })}
                  >
                    <SelectTrigger className="h-8">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {TIMEZONES.map(tz => (
                        <SelectItem key={tz.value} value={tz.value}>
                          {tz.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </Card>
          ))}

          {timeWindows.length === 0 && (
            <div className="text-center py-4 text-muted-foreground">
              <Calendar className="h-8 w-8 mx-auto mb-2" />
              <p className="text-sm">No time windows configured</p>
              <p className="text-xs">Signals will be allowed at all times</p>
            </div>
          )}
        </div>

        {/* Connection Points */}
        <div className="flex justify-between pt-2 border-t">
          <div className="flex items-center space-x-1">
            <div className="w-3 h-3 rounded-full bg-blue-500"></div>
            <span className="text-xs text-muted-foreground">Input</span>
          </div>
          <div className="flex items-center space-x-1">
            <span className="text-xs text-muted-foreground">Output</span>
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default TimeWindowBlock;