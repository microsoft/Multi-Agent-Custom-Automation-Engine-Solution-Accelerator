import React, { useEffect, useState } from 'react';
import {
  Card,
  Text,
  Button,
  Spinner,
  Badge,
  Title3,
} from '@fluentui/react-components';
import {
  DataTrending20Regular,
  ArrowUp20Regular,
  ArrowDown20Regular,
  People20Regular,
  ShoppingBag20Regular,
  Money20Regular,
  ChartMultiple20Regular,
} from '@fluentui/react-icons';
import { ForecastChart } from '../components/content/ForecastChart';
import { useNavigate } from 'react-router-dom';
import { AnalyticsService } from '../services/AnalyticsService';

import '../styles/AnalyticsDashboard.css';

interface KPICard {
  title: string;
  value: string;
  change: number;
  changeLabel: string;
  icon: JSX.Element;
  color: string;
  route: string;
}

export const AnalyticsDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [kpis, setKpis] = useState<KPICard[]>([]);

  useEffect(() => {
    // Load KPI data from backend API with fallback to mock data
    const loadKPIs = async () => {
      try {
        setLoading(true);
        
        // Try to fetch from backend API
        try {
          const kpiData = await AnalyticsService.getKPIs();
          
          // Transform API response to KPI cards
          const data: KPICard[] = [
            {
              title: 'Revenue Forecast',
              value: kpiData.revenue_forecast.value,
              change: kpiData.revenue_forecast.change,
              changeLabel: kpiData.revenue_forecast.change_label,
              icon: <Money20Regular />,
              color: '#107c10',
              route: '/plan',
            },
            {
              title: 'Customer Retention',
              value: kpiData.customer_retention.value,
              change: kpiData.customer_retention.change,
              changeLabel: kpiData.customer_retention.change_label,
              icon: <People20Regular />,
              color: '#0078d4',
              route: '/plan',
            },
            {
              title: 'Avg Order Value',
              value: kpiData.avg_order_value.value,
              change: kpiData.avg_order_value.change,
              changeLabel: kpiData.avg_order_value.change_label,
              icon: <ShoppingBag20Regular />,
              color: '#d83b01',
              route: '/plan',
            },
            {
              title: 'Forecast Accuracy',
              value: kpiData.forecast_accuracy.value,
              change: kpiData.forecast_accuracy.change,
              changeLabel: kpiData.forecast_accuracy.change_label,
              icon: <ChartMultiple20Regular />,
              color: '#5c2d91',
              route: '/plan',
            },
          ];
          
          setKpis(data);
        } catch (apiError) {
          console.warn('Backend API not available, using mock data', apiError);
          
          // Fallback to mock KPI data
          const mockData: KPICard[] = [
            {
              title: 'Revenue Forecast',
              value: '$1.2M',
              change: 8.5,
              changeLabel: 'vs last month',
              icon: <Money20Regular />,
              color: '#107c10',
              route: '/plan',
            },
            {
              title: 'Customer Retention',
              value: '92.3%',
              change: 2.1,
              changeLabel: 'vs last quarter',
              icon: <People20Regular />,
              color: '#0078d4',
              route: '/plan',
            },
            {
              title: 'Avg Order Value',
              value: '$142',
              change: -3.2,
              changeLabel: 'vs last week',
              icon: <ShoppingBag20Regular />,
              color: '#d83b01',
              route: '/plan',
            },
            {
              title: 'Forecast Accuracy',
              value: '94.8%',
              change: 1.5,
              changeLabel: 'MAPE improvement',
              icon: <ChartMultiple20Regular />,
              color: '#5c2d91',
              route: '/plan',
            },
          ];
          
          setKpis(mockData);
        }
      } catch (error) {
        console.error('Failed to load KPIs', error);
      } finally {
        setLoading(false);
      }
    };

    void loadKPIs();
  }, []);

  if (loading) {
    return (
      <div className="dashboard-loading">
        <Spinner size="huge" label="Loading dashboard..." />
      </div>
    );
  }

  // Mock forecast data
  const mockForecastData = [
    { period: 'Jan', actual: 100, forecast: undefined },
    { period: 'Feb', actual: 120, forecast: undefined },
    { period: 'Mar', actual: 115, forecast: 118, lower_bound: 110, upper_bound: 126 },
    { period: 'Apr', forecast: 125, lower_bound: 115, upper_bound: 135 },
    { period: 'May', forecast: 132, lower_bound: 120, upper_bound: 144 },
    { period: 'Jun', forecast: 140, lower_bound: 125, upper_bound: 155 },
  ];

  return (
    <div className="analytics-dashboard">
      <div className="analytics-dashboard__header">
        <div>
          <Title3>Analytics Dashboard</Title3>
          <Text>Real-time insights across all business metrics</Text>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="analytics-dashboard__kpis">
        {kpis.map((kpi) => (
          <Card
            key={kpi.title}
            className="kpi-card"
            onClick={() => navigate(kpi.route)}
            style={{ cursor: 'pointer' }}
          >
            <div className="kpi-card__header">
              <div className="kpi-card__icon" style={{ color: kpi.color }}>
                {kpi.icon}
              </div>
              <Text size={300} weight="semibold">
                {kpi.title}
              </Text>
            </div>

            <Text size={800} weight="bold" className="kpi-card__value">
              {kpi.value}
            </Text>

            <div className="kpi-card__change">
              {kpi.change > 0 ? (
                <>
                  <ArrowUp20Regular style={{ color: '#107c10' }} />
                  <Badge appearance="filled" color="success">
                    +{kpi.change}%
                  </Badge>
                </>
              ) : (
                <>
                  <ArrowDown20Regular style={{ color: '#d83b01' }} />
                  <Badge appearance="filled" color="danger">
                    {kpi.change}%
                  </Badge>
                </>
              )}
              <Text size={200}>{kpi.changeLabel}</Text>
            </div>
          </Card>
        ))}
      </div>

      {/* Analytics Sections */}
      <div className="analytics-dashboard__sections">
        <Card className="dashboard-section dashboard-section--large">
          <Text size={500} weight="semibold" style={{ marginBottom: '1rem' }}>
            Revenue Forecasting
          </Text>
          <ForecastChart
            data={mockForecastData}
            height={300}
            yAxisLabel="Revenue ($K)"
            xAxisLabel="Month"
          />
          <div style={{ marginTop: '1rem' }}>
            <Button appearance="primary" onClick={() => navigate('/plan')}>
              View Detailed Analytics
            </Button>
          </div>
        </Card>

        <Card className="dashboard-section">
          <Text size={500} weight="semibold" style={{ marginBottom: '1rem' }}>
            Quick Actions
          </Text>
          <div className="quick-actions">
            <Button
              appearance="outline"
              icon={<Money20Regular />}
              onClick={() => navigate('/plan')}
            >
              Pricing Analysis
            </Button>
            <Button
              appearance="outline"
              icon={<People20Regular />}
              onClick={() => navigate('/plan')}
            >
              Customer Insights
            </Button>
            <Button
              appearance="outline"
              icon={<DataTrending20Regular />}
              onClick={() => navigate('/plan')}
            >
              Operations Dashboard
            </Button>
            <Button
              appearance="outline"
              icon={<ShoppingBag20Regular />}
              onClick={() => navigate('/plan')}
            >
              Marketing ROI
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default AnalyticsDashboard;

