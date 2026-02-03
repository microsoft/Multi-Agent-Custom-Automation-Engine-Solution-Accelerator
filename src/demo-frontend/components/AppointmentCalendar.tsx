'use client';

import React, { useState, useMemo } from 'react';

/**
 * Appointment status enum
 */
export type AppointmentStatus = 'confirmed' | 'pending' | 'cancelled';

/**
 * Appointment data structure
 */
export interface Appointment {
  /** Unique appointment ID */
  id: string;
  /** Client/Customer name */
  clientName: string;
  /** Service type */
  service: string;
  /** Appointment date (ISO string) */
  date: string;
  /** Start time (HH:MM format) */
  startTime: string;
  /** End time (HH:MM format) */
  endTime: string;
  /** Appointment status */
  status: AppointmentStatus;
  /** Optional phone number */
  phone?: string;
  /** Optional notes */
  notes?: string;
}

/**
 * Calendar view mode
 */
export type CalendarView = 'week' | 'month';

/**
 * Props for the AppointmentCalendar component
 */
export interface AppointmentCalendarProps {
  /** List of appointments to display */
  appointments?: Appointment[];
  /** Initial view mode */
  initialView?: CalendarView;
  /** Whether the component is in a loading state */
  loading?: boolean;
  /** Callback when an appointment is clicked */
  onAppointmentClick?: (appointment: Appointment) => void;
  /** Optional className for custom styling */
  className?: string;
}

/**
 * Mock appointment data for demo purposes
 */
const MOCK_APPOINTMENTS: Appointment[] = [
  {
    id: '1',
    clientName: 'John Smith',
    service: 'Consultation',
    date: getDateString(0),
    startTime: '09:00',
    endTime: '09:30',
    status: 'confirmed',
    phone: '(555) 123-4567',
  },
  {
    id: '2',
    clientName: 'Sarah Johnson',
    service: 'Follow-up',
    date: getDateString(0),
    startTime: '10:30',
    endTime: '11:00',
    status: 'confirmed',
  },
  {
    id: '3',
    clientName: 'Mike Davis',
    service: 'Initial Visit',
    date: getDateString(0),
    startTime: '14:00',
    endTime: '15:00',
    status: 'pending',
    phone: '(555) 987-6543',
  },
  {
    id: '4',
    clientName: 'Emily Brown',
    service: 'Checkup',
    date: getDateString(1),
    startTime: '11:00',
    endTime: '11:30',
    status: 'confirmed',
  },
  {
    id: '5',
    clientName: 'David Wilson',
    service: 'Emergency',
    date: getDateString(1),
    startTime: '15:30',
    endTime: '16:30',
    status: 'pending',
    notes: 'Urgent appointment',
  },
  {
    id: '6',
    clientName: 'Lisa Anderson',
    service: 'Consultation',
    date: getDateString(2),
    startTime: '09:30',
    endTime: '10:00',
    status: 'confirmed',
  },
  {
    id: '7',
    clientName: 'Robert Taylor',
    service: 'Service A',
    date: getDateString(2),
    startTime: '13:00',
    endTime: '14:00',
    status: 'cancelled',
  },
  {
    id: '8',
    clientName: 'Jennifer Martinez',
    service: 'Follow-up',
    date: getDateString(3),
    startTime: '10:00',
    endTime: '10:30',
    status: 'confirmed',
  },
  {
    id: '9',
    clientName: 'Chris Lee',
    service: 'Initial Visit',
    date: getDateString(4),
    startTime: '14:30',
    endTime: '15:30',
    status: 'pending',
  },
  {
    id: '10',
    clientName: 'Amanda White',
    service: 'Consultation',
    date: getDateString(5),
    startTime: '11:30',
    endTime: '12:00',
    status: 'confirmed',
  },
];

/**
 * Format a local date as YYYY-MM-DD
 */
function toLocalDateString(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/**
 * Get date string relative to today
 */
function getDateString(daysFromToday: number): string {
  const date = new Date();
  date.setDate(date.getDate() + daysFromToday);
  return toLocalDateString(date);
}

/**
 * Parse YYYY-MM-DD as a local date
 */
function parseLocalDate(dateString: string): Date {
  const [yearStr, monthStr, dayStr] = dateString.split('-');
  const year = Number(yearStr);
  const month = Number(monthStr);
  const day = Number(dayStr);
  if (!year || !month || !day) {
    return new Date(dateString);
  }
  return new Date(year, month - 1, day);
}

/**
 * Get start of week (Sunday)
 */
function getStartOfWeek(date: Date): Date {
  const d = new Date(date);
  const day = d.getDay();
  d.setDate(d.getDate() - day);
  d.setHours(0, 0, 0, 0);
  return d;
}

/**
 * Get start of month
 */
function getStartOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

/**
 * Format date for display
 */
function formatDate(date: Date, format: 'short' | 'long' = 'short'): string {
  if (format === 'long') {
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    });
  }
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Format time for display
 */
function formatTime(time: string): string {
  const [hours, minutes] = time.split(':').map(Number);
  const period = hours >= 12 ? 'PM' : 'AM';
  const displayHours = hours % 12 || 12;
  return `${displayHours}:${minutes.toString().padStart(2, '0')} ${period}`;
}

/**
 * Get day of week abbreviation
 */
function getDayAbbreviation(date: Date): string {
  return date.toLocaleDateString('en-US', { weekday: 'short' });
}

/**
 * Check if two dates are the same day
 */
function isSameDay(date1: Date, date2: Date): boolean {
  return (
    date1.getFullYear() === date2.getFullYear() &&
    date1.getMonth() === date2.getMonth() &&
    date1.getDate() === date2.getDate()
  );
}

/**
 * Check if date is today
 */
function isToday(date: Date): boolean {
  return isSameDay(date, new Date());
}

/**
 * Status badge colors
 */
const STATUS_COLORS: Record<AppointmentStatus, { bg: string; text: string; dot: string }> = {
  confirmed: {
    bg: 'bg-green-50',
    text: 'text-green-700',
    dot: 'bg-green-500',
  },
  pending: {
    bg: 'bg-amber-50',
    text: 'text-amber-700',
    dot: 'bg-amber-500',
  },
  cancelled: {
    bg: 'bg-red-50',
    text: 'text-red-700 line-through',
    dot: 'bg-red-500',
  },
};

/**
 * Left arrow icon
 */
const ChevronLeftIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    className="h-5 w-5"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <polyline points="15 18 9 12 15 6" />
  </svg>
);

/**
 * Right arrow icon
 */
const ChevronRightIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    className="h-5 w-5"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <polyline points="9 18 15 12 9 6" />
  </svg>
);

/**
 * Calendar icon
 */
const CalendarIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    className="h-5 w-5"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <rect width="18" height="18" x="3" y="4" rx="2" ry="2" />
    <line x1="16" x2="16" y1="2" y2="6" />
    <line x1="8" x2="8" y1="2" y2="6" />
    <line x1="3" x2="21" y1="10" y2="10" />
  </svg>
);

/**
 * Clock icon
 */
const ClockIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    className="h-4 w-4"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <circle cx="12" cy="12" r="10" />
    <polyline points="12 6 12 12 16 14" />
  </svg>
);

/**
 * Skeleton loader for calendar
 */
const CalendarSkeleton: React.FC = () => (
  <div className="card p-6 animate-pulse">
    {/* Header skeleton */}
    <div className="flex items-center justify-between mb-6">
      <div className="h-8 w-40 bg-muted rounded" />
      <div className="flex gap-2">
        <div className="h-10 w-20 bg-muted rounded" />
        <div className="h-10 w-20 bg-muted rounded" />
      </div>
    </div>
    {/* Calendar grid skeleton */}
    <div className="grid grid-cols-7 gap-2 mb-4">
      {Array.from({ length: 7 }, (_, i) => (
        <div key={`header-${i}`} className="h-8 bg-muted rounded" />
      ))}
    </div>
    <div className="grid grid-cols-7 gap-2">
      {Array.from({ length: 14 }, (_, i) => (
        <div key={`cell-${i}`} className="h-24 bg-muted rounded" />
      ))}
    </div>
  </div>
);

/**
 * Individual appointment card
 */
const AppointmentCard: React.FC<{
  appointment: Appointment;
  compact?: boolean;
  onClick?: (appointment: Appointment) => void;
}> = ({ appointment, compact = false, onClick }) => {
  const statusStyle = STATUS_COLORS[appointment.status];

  return (
    <button
      type="button"
      onClick={() => onClick?.(appointment)}
      className={`
        w-full text-left rounded-md transition-all duration-150
        hover:shadow-sm focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-1
        ${statusStyle.bg} ${compact ? 'p-1.5' : 'p-2'}
      `}
      aria-label={`${appointment.clientName}, ${appointment.service} at ${formatTime(appointment.startTime)}, ${appointment.status}`}
    >
      <div className="flex items-start gap-1.5">
        <span
          className={`flex-shrink-0 w-2 h-2 rounded-full mt-1.5 ${statusStyle.dot}`}
          aria-hidden="true"
        />
        <div className="min-w-0 flex-1">
          <p className={`font-medium truncate ${statusStyle.text} ${compact ? 'text-xs' : 'text-sm'}`}>
            {appointment.clientName}
          </p>
          {!compact && (
            <>
              <p className="text-xs text-muted-foreground truncate">
                {appointment.service}
              </p>
              <div className="flex items-center gap-1 mt-1 text-xs text-muted-foreground">
                <ClockIcon />
                <span>{formatTime(appointment.startTime)}</span>
              </div>
            </>
          )}
          {compact && (
            <p className="text-xs text-muted-foreground">
              {formatTime(appointment.startTime)}
            </p>
          )}
        </div>
      </div>
    </button>
  );
};

/**
 * Week view component
 */
const WeekView: React.FC<{
  weekStart: Date;
  appointments: Appointment[];
  onAppointmentClick?: (appointment: Appointment) => void;
}> = ({ weekStart, appointments, onAppointmentClick }) => {
  const weekDays = useMemo(() => {
    const days: Date[] = [];
    for (let i = 0; i < 7; i++) {
      const day = new Date(weekStart);
      day.setDate(weekStart.getDate() + i);
      days.push(day);
    }
    return days;
  }, [weekStart]);

  const appointmentsByDay = useMemo(() => {
    const byDay: Map<string, Appointment[]> = new Map();
    weekDays.forEach((day) => {
      const dateStr = toLocalDateString(day);
      byDay.set(dateStr, []);
    });
    appointments.forEach((apt) => {
      const existing = byDay.get(apt.date) || [];
      existing.push(apt);
      byDay.set(apt.date, existing);
    });
    // Sort appointments by start time
    byDay.forEach((apts, key) => {
      byDay.set(
        key,
        apts.sort((a, b) => a.startTime.localeCompare(b.startTime))
      );
    });
    return byDay;
  }, [weekDays, appointments]);

  return (
    <div className="grid grid-cols-7 gap-2">
      {/* Day headers */}
      {weekDays.map((day) => (
        <div
          key={day.toISOString()}
          className={`
            text-center py-2 rounded-t-lg
            ${isToday(day) ? 'bg-brand/10' : 'bg-muted'}
          `}
        >
          <p className="text-xs font-medium text-muted-foreground">
            {getDayAbbreviation(day)}
          </p>
          <p
            className={`
              text-lg font-semibold
              ${isToday(day) ? 'text-brand' : 'text-foreground'}
            `}
          >
            {day.getDate()}
          </p>
        </div>
      ))}
      {/* Day columns */}
      {weekDays.map((day) => {
        const dateStr = toLocalDateString(day);
        const dayAppointments = appointmentsByDay.get(dateStr) || [];

        return (
          <div
            key={`col-${day.toISOString()}`}
            className={`
              min-h-[120px] p-1 rounded-b-lg border
              ${isToday(day) ? 'border-brand/30 bg-brand/5' : 'border-border'}
            `}
          >
            <div className="space-y-1">
              {dayAppointments.slice(0, 3).map((apt) => (
                <AppointmentCard
                  key={apt.id}
                  appointment={apt}
                  compact
                  onClick={onAppointmentClick}
                />
              ))}
              {dayAppointments.length > 3 && (
                <p className="text-xs text-center text-muted-foreground py-1">
                  +{dayAppointments.length - 3} more
                </p>
              )}
              {dayAppointments.length === 0 && (
                <p className="text-xs text-center text-muted-foreground py-4">
                  No appointments
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};

/**
 * Month view component
 */
const MonthView: React.FC<{
  monthStart: Date;
  appointments: Appointment[];
  onAppointmentClick?: (appointment: Appointment) => void;
}> = ({ monthStart, appointments, onAppointmentClick }) => {
  const { weeks, monthDays } = useMemo(() => {
    const days: (Date | null)[] = [];
    const firstDay = new Date(monthStart.getFullYear(), monthStart.getMonth(), 1);
    const lastDay = new Date(monthStart.getFullYear(), monthStart.getMonth() + 1, 0);

    // Add empty slots for days before first of month
    const startDayOfWeek = firstDay.getDay();
    for (let i = 0; i < startDayOfWeek; i++) {
      days.push(null);
    }

    // Add all days of month
    for (let d = 1; d <= lastDay.getDate(); d++) {
      days.push(new Date(monthStart.getFullYear(), monthStart.getMonth(), d));
    }

    // Split into weeks
    const weekRows: (Date | null)[][] = [];
    for (let i = 0; i < days.length; i += 7) {
      weekRows.push(days.slice(i, i + 7));
    }

    return { weeks: weekRows, monthDays: days };
  }, [monthStart]);

  const appointmentsByDay = useMemo(() => {
    const byDay: Map<string, Appointment[]> = new Map();
    appointments.forEach((apt) => {
      const existing = byDay.get(apt.date) || [];
      existing.push(apt);
      byDay.set(apt.date, existing);
    });
    return byDay;
  }, [appointments]);

  const dayHeaders = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  return (
    <div>
      {/* Day headers */}
      <div className="grid grid-cols-7 gap-1 mb-2">
        {dayHeaders.map((day) => (
          <div
            key={day}
            className="text-center py-2 text-xs font-medium text-muted-foreground"
          >
            {day}
          </div>
        ))}
      </div>
      {/* Calendar grid */}
      <div className="space-y-1">
        {weeks.map((week, weekIdx) => (
          <div key={`week-${weekIdx}`} className="grid grid-cols-7 gap-1">
            {week.map((day, dayIdx) => {
              if (!day) {
                return (
                  <div
                    key={`empty-${weekIdx}-${dayIdx}`}
                    className="min-h-[80px] rounded-lg bg-muted/30"
                  />
                );
              }

              const dateStr = toLocalDateString(day);
              const dayAppointments = appointmentsByDay.get(dateStr) || [];
              const today = isToday(day);

              return (
                <div
                  key={day.toISOString()}
                  className={`
                    min-h-[80px] p-1 rounded-lg border
                    ${today ? 'border-brand bg-brand/5' : 'border-border'}
                  `}
                >
                  <p
                    className={`
                      text-sm font-medium mb-1
                      ${today ? 'text-brand' : 'text-foreground'}
                    `}
                  >
                    {day.getDate()}
                  </p>
                  <div className="space-y-0.5">
                    {dayAppointments.slice(0, 2).map((apt) => (
                      <button
                        key={apt.id}
                        onClick={() => onAppointmentClick?.(apt)}
                        className={`
                          w-full text-left text-xs truncate px-1 py-0.5 rounded
                          ${STATUS_COLORS[apt.status].bg}
                          ${STATUS_COLORS[apt.status].text}
                          hover:opacity-80 transition-opacity
                        `}
                        title={`${apt.clientName} - ${apt.service} at ${formatTime(apt.startTime)}`}
                      >
                        {apt.clientName}
                      </button>
                    ))}
                    {dayAppointments.length > 2 && (
                      <p className="text-xs text-muted-foreground text-center">
                        +{dayAppointments.length - 2}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
            {/* Pad the last week if needed */}
            {week.length < 7 &&
              Array.from({ length: 7 - week.length }, (_, i) => (
                <div
                  key={`pad-${weekIdx}-${i}`}
                  className="min-h-[80px] rounded-lg bg-muted/30"
                />
              ))}
          </div>
        ))}
      </div>
    </div>
  );
};

/**
 * AppointmentCalendar component for displaying appointments in weekly/monthly views
 *
 * Displays appointments in an interactive calendar with:
 * - Weekly and monthly view options
 * - Navigation controls for changing periods
 * - Color-coded appointment status
 * - Click handlers for appointment details
 *
 * @example
 * ```tsx
 * <AppointmentCalendar
 *   appointments={appointments}
 *   initialView="week"
 *   onAppointmentClick={(apt) => console.log('Clicked:', apt)}
 * />
 * ```
 */
const AppointmentCalendar: React.FC<AppointmentCalendarProps> = ({
  appointments = MOCK_APPOINTMENTS,
  initialView = 'week',
  loading = false,
  onAppointmentClick,
  className = '',
}) => {
  const [view, setView] = useState<CalendarView>(initialView);
  const [currentDate, setCurrentDate] = useState<Date>(new Date());

  // Calculate view-specific start date
  const viewStartDate = useMemo(() => {
    return view === 'week' ? getStartOfWeek(currentDate) : getStartOfMonth(currentDate);
  }, [view, currentDate]);

  // Filter appointments for current view range
  const filteredAppointments = useMemo(() => {
    const start = viewStartDate;
    const end = new Date(start);
    if (view === 'week') {
      end.setDate(end.getDate() + 7);
    } else {
      end.setMonth(end.getMonth() + 1);
    }

    return appointments.filter((apt) => {
      const aptDate = parseLocalDate(apt.date);
      return aptDate >= start && aptDate < end;
    });
  }, [appointments, viewStartDate, view]);

  // Navigation handlers
  const goToPrevious = () => {
    setCurrentDate((prev) => {
      const next = new Date(prev);
      if (view === 'week') {
        next.setDate(next.getDate() - 7);
      } else {
        next.setMonth(next.getMonth() - 1);
      }
      return next;
    });
  };

  const goToNext = () => {
    setCurrentDate((prev) => {
      const next = new Date(prev);
      if (view === 'week') {
        next.setDate(next.getDate() + 7);
      } else {
        next.setMonth(next.getMonth() + 1);
      }
      return next;
    });
  };

  const goToToday = () => {
    setCurrentDate(new Date());
  };

  // Get header title based on view
  const headerTitle = useMemo(() => {
    if (view === 'week') {
      const weekEnd = new Date(viewStartDate);
      weekEnd.setDate(weekEnd.getDate() + 6);
      return `${formatDate(viewStartDate)} - ${formatDate(weekEnd)}`;
    }
    return currentDate.toLocaleDateString('en-US', {
      month: 'long',
      year: 'numeric',
    });
  }, [view, viewStartDate, currentDate]);

  if (loading) {
    return <CalendarSkeleton />;
  }

  return (
    <div
      className={`card p-6 ${className}`}
      role="region"
      aria-label="Appointment calendar"
    >
      {/* Header with navigation and view toggles */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        {/* Title and navigation */}
        <div className="flex items-center gap-3">
          <div className="p-2 bg-brand/10 rounded-lg text-brand" aria-hidden="true">
            <CalendarIcon />
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={goToPrevious}
              className="p-1.5 rounded-md hover:bg-muted transition-colors"
              aria-label={`Go to previous ${view}`}
            >
              <ChevronLeftIcon />
            </button>
            <h2 className="text-lg font-semibold text-foreground min-w-[180px] text-center">
              {headerTitle}
            </h2>
            <button
              type="button"
              onClick={goToNext}
              className="p-1.5 rounded-md hover:bg-muted transition-colors"
              aria-label={`Go to next ${view}`}
            >
              <ChevronRightIcon />
            </button>
          </div>
        </div>

        {/* View toggles and today button */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={goToToday}
            className="px-3 py-1.5 text-sm font-medium text-brand hover:bg-brand/10 rounded-md transition-colors"
          >
            Today
          </button>
          <div className="flex rounded-lg border border-border overflow-hidden">
            <button
              type="button"
              onClick={() => setView('week')}
              className={`
                px-3 py-1.5 text-sm font-medium transition-colors
                ${view === 'week'
                  ? 'bg-brand text-white'
                  : 'bg-white text-foreground hover:bg-muted'
                }
              `}
              aria-pressed={view === 'week'}
            >
              Week
            </button>
            <button
              type="button"
              onClick={() => setView('month')}
              className={`
                px-3 py-1.5 text-sm font-medium transition-colors
                ${view === 'month'
                  ? 'bg-brand text-white'
                  : 'bg-white text-foreground hover:bg-muted'
                }
              `}
              aria-pressed={view === 'month'}
            >
              Month
            </button>
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 mb-4 text-sm">
        {Object.entries(STATUS_COLORS).map(([status, colors]) => (
          <div key={status} className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${colors.dot}`} aria-hidden="true" />
            <span className="text-muted-foreground capitalize">{status}</span>
          </div>
        ))}
      </div>

      {/* Calendar view */}
      {view === 'week' ? (
        <WeekView
          weekStart={viewStartDate}
          appointments={filteredAppointments}
          onAppointmentClick={onAppointmentClick}
        />
      ) : (
        <MonthView
          monthStart={viewStartDate}
          appointments={filteredAppointments}
          onAppointmentClick={onAppointmentClick}
        />
      )}

      {/* Summary */}
      <div className="mt-4 pt-4 border-t border-border">
        <p className="text-sm text-muted-foreground">
          Showing {filteredAppointments.length} appointment{filteredAppointments.length !== 1 ? 's' : ''}{' '}
          for this {view}
        </p>
      </div>
    </div>
  );
};

export default AppointmentCalendar;
