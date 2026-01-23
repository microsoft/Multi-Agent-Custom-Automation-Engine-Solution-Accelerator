'use client';

import React from 'react';

/**
 * Stats data structure for dashboard overview
 */
export interface StatsData {
  /** Number of scheduled appointments */
  scheduled: number;
  /** Number of confirmed appointments */
  confirmed: number;
  /** Number of pending appointments */
  pending: number;
  /** Total revenue (in dollars) */
  revenue: number;
}

/**
 * Props for the StatsCards component
 */
export interface StatsCardsProps {
  /** Statistics data to display */
  stats: StatsData;
  /** Whether the component is in a loading state */
  loading?: boolean;
  /** Optional className for custom styling */
  className?: string;
}

/**
 * Individual stat card configuration
 */
interface StatCardConfig {
  /** Display label for the stat */
  label: string;
  /** Key in StatsData */
  key: keyof StatsData;
  /** Icon component */
  icon: React.ReactNode;
  /** CSS class for the icon background */
  iconBgClass: string;
  /** Format function for the value */
  format: (value: number) => string;
  /** Trend indicator (optional) */
  trend?: 'up' | 'down' | 'neutral';
}

/**
 * Calendar icon for scheduled appointments
 */
const CalendarIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    className="h-6 w-6"
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
 * Check circle icon for confirmed appointments
 */
const CheckCircleIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    className="h-6 w-6"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
    <polyline points="22 4 12 14.01 9 11.01" />
  </svg>
);

/**
 * Clock icon for pending appointments
 */
const ClockIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    className="h-6 w-6"
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
 * Dollar sign icon for revenue
 */
const DollarIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    className="h-6 w-6"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <line x1="12" x2="12" y1="2" y2="22" />
    <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
  </svg>
);

/**
 * Skeleton component for loading state
 */
const StatCardSkeleton: React.FC = () => (
  <div className="card p-6 animate-pulse">
    <div className="flex items-center justify-between">
      <div className="flex-1">
        <div className="h-4 w-24 bg-muted rounded mb-2" />
        <div className="h-8 w-16 bg-muted rounded" />
      </div>
      <div className="h-12 w-12 bg-muted rounded-lg" />
    </div>
  </div>
);

/**
 * Format a number as currency (USD)
 */
function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

/**
 * Format a number with comma separators
 */
function formatNumber(value: number): string {
  return new Intl.NumberFormat('en-US').format(value);
}

/**
 * Card configurations for each statistic
 */
const STAT_CARDS: StatCardConfig[] = [
  {
    label: 'Scheduled',
    key: 'scheduled',
    icon: <CalendarIcon />,
    iconBgClass: 'bg-blue-100 text-blue-600',
    format: formatNumber,
  },
  {
    label: 'Confirmed',
    key: 'confirmed',
    icon: <CheckCircleIcon />,
    iconBgClass: 'bg-green-100 text-green-600',
    format: formatNumber,
  },
  {
    label: 'Pending',
    key: 'pending',
    icon: <ClockIcon />,
    iconBgClass: 'bg-amber-100 text-amber-600',
    format: formatNumber,
  },
  {
    label: 'Revenue',
    key: 'revenue',
    icon: <DollarIcon />,
    iconBgClass: 'bg-purple-100 text-purple-600',
    format: formatCurrency,
  },
];

/**
 * StatsCards component for dashboard overview
 *
 * Displays key metrics in a responsive grid of cards:
 * - Scheduled appointments
 * - Confirmed appointments
 * - Pending appointments
 * - Total revenue
 *
 * @example
 * ```tsx
 * <StatsCards
 *   stats={{
 *     scheduled: 45,
 *     confirmed: 32,
 *     pending: 13,
 *     revenue: 15600,
 *   }}
 * />
 * ```
 */
const StatsCards: React.FC<StatsCardsProps> = ({
  stats,
  loading = false,
  className = '',
}) => {
  if (loading) {
    return (
      <div
        className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 ${className}`}
        role="region"
        aria-label="Dashboard statistics loading"
      >
        {Array.from({ length: 4 }, (_, i) => (
          <StatCardSkeleton key={`skeleton-${i}`} />
        ))}
      </div>
    );
  }

  return (
    <div
      className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 ${className}`}
      role="region"
      aria-label="Dashboard statistics"
    >
      {STAT_CARDS.map((config) => {
        const value = stats[config.key];
        const formattedValue = config.format(value);

        return (
          <div
            key={config.key}
            className="card p-6 hover:shadow-md transition-shadow duration-200"
          >
            <div className="flex items-center justify-between">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-muted-foreground truncate">
                  {config.label}
                </p>
                <p
                  className="mt-1 text-2xl font-semibold text-foreground truncate"
                  title={formattedValue}
                >
                  {formattedValue}
                </p>
              </div>
              <div
                className={`flex-shrink-0 ml-4 p-3 rounded-lg ${config.iconBgClass}`}
                aria-hidden="true"
              >
                {config.icon}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default StatsCards;
