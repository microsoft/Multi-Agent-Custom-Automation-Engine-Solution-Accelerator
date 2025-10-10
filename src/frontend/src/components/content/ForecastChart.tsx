import React, { useState } from 'react';
import {
  LineChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import {
  Card,
  Text,
  ToggleButton,
  Spinner,
  Caption1,
} from '@fluentui/react-components';

import '../../styles/ForecastChart.css';

export interface ForecastDataPoint {
  period: string | number;
  actual?: number;
  forecast?: number;
  lower_bound?: number;
  upper_bound?: number;
}

export interface ForecastChartProps {
  data: ForecastDataPoint[];
  title?: string;
  loading?: boolean;
  showConfidenceInterval?: boolean;
  height?: number;
  yAxisLabel?: string;
  xAxisLabel?: string;
}

export const ForecastChart: React.FC<ForecastChartProps> = ({
  data,
  title = 'Forecast Visualization',
  loading = false,
  showConfidenceInterval = true,
  height = 400,
  yAxisLabel = 'Value',
  xAxisLabel = 'Period',
}) => {
  const [showActual, setShowActual] = useState(true);
  const [showForecast, setShowForecast] = useState(true);

  if (loading) {
    return (
      <Card className="forecast-chart">
        <div className="forecast-chart__loading">
          <Spinner size="large" label="Loading forecast data..." />
        </div>
      </Card>
    );
  }

  // Find the point where forecast starts
  const forecastStartIndex = data.findIndex((d) => d.forecast && !d.actual);
  const forecastStartPeriod = forecastStartIndex >= 0 ? data[forecastStartIndex].period : null;

  return (
    <Card className="forecast-chart">
      <div className="forecast-chart__header">
        <Text weight="semibold" size={500}>
          {title}
        </Text>

        <div className="forecast-chart__controls">
          <ToggleButton
            checked={showActual}
            onClick={() => setShowActual(!showActual)}
            size="small"
          >
            Actual
          </ToggleButton>
          <ToggleButton
            checked={showForecast}
            onClick={() => setShowForecast(!showForecast)}
            size="small"
          >
            Forecast
          </ToggleButton>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e1dfdd" />
          <XAxis
            dataKey="period"
            label={{ value: xAxisLabel, position: 'insideBottom', offset: -5 }}
            style={{ fontSize: '12px' }}
          />
          <YAxis
            label={{ value: yAxisLabel, angle: -90, position: 'insideLeft' }}
            style={{ fontSize: '12px' }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#fff',
              border: '1px solid #e1dfdd',
              borderRadius: '4px',
            }}
          />
          <Legend wrapperStyle={{ fontSize: '12px' }} />

          {/* Confidence interval area */}
          {showConfidenceInterval && showForecast && (
            <>
              <Area
                type="monotone"
                dataKey="upper_bound"
                stroke="none"
                fill="#107c10"
                fillOpacity={0.1}
                name="Upper Bound"
              />
              <Area
                type="monotone"
                dataKey="lower_bound"
                stroke="none"
                fill="#107c10"
                fillOpacity={0.1}
                name="Lower Bound"
              />
            </>
          )}

          {/* Actual data line */}
          {showActual && (
            <Line
              type="monotone"
              dataKey="actual"
              stroke="#0078d4"
              strokeWidth={2}
              dot={{ r: 4, fill: '#0078d4' }}
              name="Actual"
              connectNulls={false}
            />
          )}

          {/* Forecast line */}
          {showForecast && (
            <Line
              type="monotone"
              dataKey="forecast"
              stroke="#107c10"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={{ r: 3, fill: '#107c10' }}
              name="Forecast"
              connectNulls={false}
            />
          )}

          {/* Reference line at forecast start */}
          {forecastStartPeriod && (
            <ReferenceLine
              x={forecastStartPeriod}
              stroke="#666"
              strokeDasharray="3 3"
              label={{ value: 'Forecast Start', position: 'top', fontSize: 10 }}
            />
          )}
        </LineChart>
      </ResponsiveContainer>

      {/* Summary stats */}
      {data.some((d) => d.forecast) && (
        <div className="forecast-chart__summary">
          <Caption1>
            Forecast Range: {data.find((d) => d.forecast)?.period} -{' '}
            {data[data.length - 1]?.period}
          </Caption1>
          {showConfidenceInterval && (
            <Caption1>Confidence Level: 85%</Caption1>
          )}
        </div>
      )}
    </Card>
  );
};

export default ForecastChart;



