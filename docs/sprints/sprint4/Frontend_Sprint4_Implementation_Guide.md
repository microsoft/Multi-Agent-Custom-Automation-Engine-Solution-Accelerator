# Sprint 4: Frontend Enhancements - Implementation Guide

**Sprint Focus:** Analytics dashboards, forecast visualizations, and enhanced dataset management UI

**Status:** 📋 **READY FOR IMPLEMENTATION**

---

## 📋 Executive Summary

Sprint 4 brings all the backend analytics from Sprints 1-3 to life with beautiful, interactive frontend components. This guide provides complete specifications for implementing:

1. **Enhanced Dataset Panel** - Multi-upload, filtering, quick actions
2. **Forecast Visualization** - Interactive charts with confidence intervals
3. **Model Comparison** - Side-by-side forecast model analysis
4. **Analytics Dashboards** - Comprehensive KPI dashboards for all analytics domains

---

## 🎯 Prerequisites

### Required Dependencies

Add to `src/frontend/package.json`:

```json
{
  "dependencies": {
    "recharts": "^2.12.0",
    "@fluentui/react-charting": "^5.21.0"
  },
  "devDependencies": {
    "@types/recharts": "^1.8.29"
  }
}
```

Install:
```bash
cd src/frontend
npm install recharts @fluentui/react-charting
npm install --save-dev @types/recharts
```

---

## 📦 Component 1: Enhanced ForecastDatasetPanel

### Purpose
Upgrade the existing dataset panel with:
- Multi-file upload
- Search/filter datasets
- Quick actions (preview, summarize, link)
- Dataset tagging
- Usage statistics

### File Location
`src/frontend/src/components/content/EnhancedForecastDatasetPanel.tsx`

### Key Features

#### 1. Multi-Upload
```typescript
// Allow multiple file selection
<input
  ref={fileInputRef}
  type="file"
  accept={ACCEPTED_TYPES}
  onChange={handleFileChange}
  multiple  // Enable multi-select
  hidden
/>
```

#### 2. Search & Filter
```typescript
const [searchTerm, setSearchTerm] = useState<string>('');
const [filterType, setFilterType] = useState<'all' | 'csv' | 'xlsx'>('all');

const filteredDatasets = useMemo(() => {
  return datasets.filter(dataset => {
    const matchesSearch = dataset.original_filename
      .toLowerCase()
      .includes(searchTerm.toLowerCase());
    const matchesType = filterType === 'all' || 
      dataset.content_type.includes(filterType);
    return matchesSearch && matchesType;
  });
}, [datasets, searchTerm, filterType]);
```

#### 3. Quick Actions
```typescript
interface DatasetAction {
  icon: JSX.Element;
  label: string;
  onClick: (datasetId: string) => void;
}

const quickActions: DatasetAction[] = [
  {
    icon: <ChartMultiple20Regular />,
    label: "Visualize",
    onClick: (id) => navigate(`/analytics/visualize/${id}`)
  },
  {
    icon: <DataUsage20Regular />,
    label: "Summarize",
    onClick: async (id) => {
      const summary = await DatasetService.summarizeDataset(id);
      setActiveDatasetSummary(summary);
    }
  },
  {
    icon: <Link20Regular />,
    label: "Link datasets",
    onClick: (id) => setLinkingDataset(id)
  }
];
```

#### 4. Dataset Cards Enhancement
```typescript
<Card className="dataset-card">
  <div className="dataset-card__header">
    <div className="dataset-card__info">
      <Text weight="semibold">{dataset.original_filename}</Text>
      <Caption1>{formatSize(dataset.size_bytes)} • {dataset.columns.length} columns</Caption1>
    </div>
    
    {/* Tags */}
    <div className="dataset-card__tags">
      {dataset.tags?.map(tag => (
        <Badge key={tag} appearance="outline">{tag}</Badge>
      ))}
    </div>
  </div>

  {/* Quick stats */}
  <div className="dataset-card__stats">
    <Tooltip content="Row count" relationship="label">
      <div className="stat-item">
        <DataTable20Regular />
        <Caption1>{dataset.row_count?.toLocaleString()}</Caption1>
      </div>
    </Tooltip>
    <Tooltip content="Numeric columns" relationship="label">
      <div className="stat-item">
        <NumberSymbol20Regular />
        <Caption1>{dataset.numeric_columns?.length || 0}</Caption1>
      </div>
    </Tooltip>
  </div>

  {/* Actions */}
  <div className="dataset-card__actions">
    {quickActions.map(action => (
      <Tooltip key={action.label} content={action.label} relationship="label">
        <Button
          appearance="subtle"
          icon={action.icon}
          onClick={() => action.onClick(dataset.dataset_id)}
        />
      </Tooltip>
    ))}
  </div>
</Card>
```

### API Extensions Needed

Add to `DatasetService.tsx`:

```typescript
static async summarizeDataset(datasetId: string): Promise<DatasetSummary> {
  const response = await apiClient.get(`/v3/datasets/${datasetId}/summarize`);
  return response as DatasetSummary;
}

static async linkDatasets(
  primaryId: string,
  secondaryId: string,
  joinColumn: string
): Promise<DatasetLinkResponse> {
  const response = await apiClient.post(`/v3/datasets/link`, {
    primary_dataset_id: primaryId,
    secondary_dataset_id: secondaryId,
    join_column: joinColumn
  });
  return response as DatasetLinkResponse;
}
```

### Model Extensions

Add to `models/dataset.tsx`:

```typescript
export interface DatasetSummary {
  dataset_id: string;
  row_count: number;
  column_stats: {
    [column: string]: {
      type: 'numeric' | 'categorical' | 'datetime';
      unique_count: number;
      null_count: number;
      min?: number;
      max?: number;
      mean?: number;
      median?: number;
    };
  };
  correlations?: { [pair: string]: number };
}

export interface DatasetLinkResponse {
  linked_dataset_id: string;
  join_column: string;
  matched_rows: number;
}
```

---

## 📊 Component 2: ForecastChart

### Purpose
Interactive chart component for visualizing forecasts with:
- Historical data points
- Forecast line
- Confidence interval bands
- Multiple series comparison
- Zoom/pan capabilities

### File Location
`src/frontend/src/components/content/ForecastChart.tsx`

### Component Structure

```typescript
import React from 'react';
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
  ReferenceLine
} from 'recharts';
import { Card, Text, ToggleButton, Spinner } from '@fluentui/react-components';

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
  title = "Forecast Visualization",
  loading = false,
  showConfidenceInterval = true,
  height = 400,
  yAxisLabel = "Value",
  xAxisLabel = "Period"
}) => {
  const [showActual, setShowActual] = React.useState(true);
  const [showForecast, setShowForecast] = React.useState(true);

  if (loading) {
    return (
      <Card>
        <div style={{ display: 'flex', justifyContent: 'center', padding: '2rem' }}>
          <Spinner label="Loading forecast data..." />
        </div>
      </Card>
    );
  }

  return (
    <Card className="forecast-chart">
      <div className="forecast-chart__header">
        <Text weight="semibold" size={500}>{title}</Text>
        
        <div className="forecast-chart__controls">
          <ToggleButton
            checked={showActual}
            onClick={() => setShowActual(!showActual)}
          >
            Actual
          </ToggleButton>
          <ToggleButton
            checked={showForecast}
            onClick={() => setShowForecast(!showForecast)}
          >
            Forecast
          </ToggleButton>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={height}>
        <LineChart
          data={data}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="period"
            label={{ value: xAxisLabel, position: 'insideBottom', offset: -5 }}
          />
          <YAxis
            label={{ value: yAxisLabel, angle: -90, position: 'insideLeft' }}
          />
          <Tooltip />
          <Legend />

          {/* Confidence interval */}
          {showConfidenceInterval && showForecast && (
            <Area
              type="monotone"
              dataKey="upper_bound"
              stroke="none"
              fill="#8884d8"
              fillOpacity={0.1}
              name="Confidence Range"
            />
          )}
          {showConfidenceInterval && showForecast && (
            <Area
              type="monotone"
              dataKey="lower_bound"
              stroke="none"
              fill="#8884d8"
              fillOpacity={0.1}
            />
          )}

          {/* Actual data */}
          {showActual && (
            <Line
              type="monotone"
              dataKey="actual"
              stroke="#0078d4"
              strokeWidth={2}
              dot={{ r: 4 }}
              name="Actual"
            />
          )}

          {/* Forecast */}
          {showForecast && (
            <Line
              type="monotone"
              dataKey="forecast"
              stroke="#107c10"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={{ r: 3 }}
              name="Forecast"
            />
          )}

          {/* Reference line at forecast start */}
          {data.some(d => d.actual) && data.some(d => d.forecast) && (
            <ReferenceLine
              x={data.find(d => d.forecast && !d.actual)?.period}
              stroke="#666"
              strokeDasharray="3 3"
              label="Forecast Start"
            />
          )}
        </LineChart>
      </ResponsiveContainer>

      {/* Summary stats */}
      <div className="forecast-chart__summary">
        {data.some(d => d.forecast) && (
          <>
            <Text size={200}>
              Forecast Range: {data.find(d => d.forecast)?.period} - {data[data.length - 1]?.period}
            </Text>
            <Text size={200}>
              Confidence Level: 85%
            </Text>
          </>
        )}
      </div>
    </Card>
  );
};
```

### CSS Styles

Create `src/frontend/src/styles/ForecastChart.css`:

```css
.forecast-chart {
  padding: 1.5rem;
}

.forecast-chart__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.forecast-chart__controls {
  display: flex;
  gap: 0.5rem;
}

.forecast-chart__summary {
  display: flex;
  gap: 2rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--colorNeutralStroke1);
}
```

---

## 🔄 Component 3: ModelComparisonPanel

### Purpose
Side-by-side comparison of different forecasting models with:
- Model accuracy metrics (MAE, RMSE, MAPE)
- Visual comparison of forecasts
- Best model recommendation
- Performance rankings

### File Location
`src/frontend/src/components/content/ModelComparisonPanel.tsx`

### Component Structure

```typescript
import React from 'react';
import {
  Card,
  Text,
  Button,
  Spinner,
  Badge,
  DataGrid,
  DataGridHeader,
  DataGridRow,
  DataGridHeaderCell,
  DataGridBody,
  DataGridCell
} from '@fluentui/react-components';
import { ForecastChart } from './ForecastChart';

export interface ModelMetrics {
  model_name: string;
  mae: number;
  rmse: number;
  mape: number;
  forecast: number[];
  lower_bound?: number[];
  upper_bound?: number[];
}

export interface ModelComparisonProps {
  models: ModelMetrics[];
  historical: number[];
  periods: (string | number)[];
  loading?: boolean;
  onSelectModel?: (modelName: string) => void;
}

export const ModelComparisonPanel: React.FC<ModelComparisonProps> = ({
  models,
  historical,
  periods,
  loading = false,
  onSelectModel
}) => {
  const [selectedModel, setSelectedModel] = React.useState<string | null>(null);

  if (loading) {
    return (
      <Card>
        <Spinner label="Evaluating forecast models..." />
      </Card>
    );
  }

  // Find best model (lowest MAPE)
  const bestModel = models.reduce((best, current) =>
    current.mape < best.mape ? current : best
  , models[0]);

  const handleSelectModel = (modelName: string) => {
    setSelectedModel(modelName);
    onSelectModel?.(modelName);
  };

  return (
    <div className="model-comparison">
      {/* Summary Card */}
      <Card className="model-comparison__summary">
        <Text weight="semibold" size={500}>Model Performance Comparison</Text>
        <Text>
          Evaluated {models.length} forecasting models. 
          Best performer: <strong>{bestModel.model_name}</strong> (MAPE: {bestModel.mape.toFixed(2)}%)
        </Text>
      </Card>

      {/* Metrics Table */}
      <Card className="model-comparison__table">
        <Text weight="semibold" size={400}>Accuracy Metrics</Text>
        
        <DataGrid>
          <DataGridHeader>
            <DataGridRow>
              <DataGridHeaderCell>Model</DataGridHeaderCell>
              <DataGridHeaderCell>MAE</DataGridHeaderCell>
              <DataGridHeaderCell>RMSE</DataGridHeaderCell>
              <DataGridHeaderCell>MAPE</DataGridHeaderCell>
              <DataGridHeaderCell>Rank</DataGridHeaderCell>
              <DataGridHeaderCell>Action</DataGridHeaderCell>
            </DataGridRow>
          </DataGridHeader>
          <DataGridBody>
            {models
              .sort((a, b) => a.mape - b.mape)
              .map((model, index) => (
                <DataGridRow key={model.model_name}>
                  <DataGridCell>
                    {model.model_name}
                    {model.model_name === bestModel.model_name && (
                      <Badge appearance="filled" color="success" style={{ marginLeft: '0.5rem' }}>
                        Best
                      </Badge>
                    )}
                  </DataGridCell>
                  <DataGridCell>{model.mae.toFixed(2)}</DataGridCell>
                  <DataGridCell>{model.rmse.toFixed(2)}</DataGridCell>
                  <DataGridCell>{model.mape.toFixed(2)}%</DataGridCell>
                  <DataGridCell>#{index + 1}</DataGridCell>
                  <DataGridCell>
                    <Button
                      size="small"
                      appearance={selectedModel === model.model_name ? 'primary' : 'secondary'}
                      onClick={() => handleSelectModel(model.model_name)}
                    >
                      {selectedModel === model.model_name ? 'Selected' : 'Select'}
                    </Button>
                  </DataGridCell>
                </DataGridRow>
              ))}
          </DataGridBody>
        </DataGrid>
      </Card>

      {/* Visual Comparison */}
      {selectedModel && (
        <ForecastChart
          data={periods.map((period, i) => ({
            period,
            actual: i < historical.length ? historical[i] : undefined,
            forecast: models.find(m => m.model_name === selectedModel)?.forecast[i],
            lower_bound: models.find(m => m.model_name === selectedModel)?.lower_bound?.[i],
            upper_bound: models.find(m => m.model_name === selectedModel)?.upper_bound?.[i]
          }))}
          title={`${selectedModel} Forecast`}
          showConfidenceInterval={true}
        />
      )}
    </div>
  );
};
```

---

## 📱 Component 4: AnalyticsDashboard Page

### Purpose
Main analytics dashboard with:
- KPI summary cards
- Recent forecasts
- Quick access to all analytics domains
- Trend indicators

### File Location
`src/frontend/src/pages/AnalyticsDashboard.tsx`

### Component Structure

```typescript
import React, { useEffect, useState } from 'react';
import {
  Card,
  Text,
  Button,
  Spinner,
  Badge
} from '@fluentui/react-components';
import {
  ArrowTrendingUp24Regular,
  ArrowTrendingDown24Regular,
  PeopleTeam24Regular,
  ShoppingBag24Regular,
  Money24Regular
} from '@fluentui/react-icons';
import { ForecastChart } from '@/components/content/ForecastChart';
import { useNavigate } from 'react-router-dom';

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
    // Load KPI data
    const loadKPIs = async () => {
      try {
        setLoading(true);
        // Fetch KPIs from API
        const data: KPICard[] = [
          {
            title: "Revenue Forecast",
            value: "$1.2M",
            change: 8.5,
            changeLabel: "vs last month",
            icon: <Money24Regular />,
            color: "#107c10",
            route: "/analytics/revenue"
          },
          {
            title: "Customer Retention",
            value: "92.3%",
            change: 2.1,
            changeLabel: "vs last quarter",
            icon: <PeopleTeam24Regular />,
            color: "#0078d4",
            route: "/analytics/customers"
          },
          {
            title: "Avg Order Value",
            value: "$142",
            change: -3.2,
            changeLabel: "vs last week",
            icon: <ShoppingBag24Regular />,
            color: "#d83b01",
            route: "/analytics/orders"
          }
        ];
        setKpis(data);
      } catch (error) {
        console.error('Failed to load KPIs', error);
      } finally {
        setLoading(false);
      }
    };

    loadKPIs();
  }, []);

  if (loading) {
    return (
      <div className="dashboard-loading">
        <Spinner size="large" label="Loading dashboard..." />
      </div>
    );
  }

  return (
    <div className="analytics-dashboard">
      <div className="analytics-dashboard__header">
        <div>
          <Text size={700} weight="bold">Analytics Dashboard</Text>
          <Text>Real-time insights across all business metrics</Text>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="analytics-dashboard__kpis">
        {kpis.map(kpi => (
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
              <Text size={300} weight="semibold">{kpi.title}</Text>
            </div>

            <Text size={800} weight="bold" className="kpi-card__value">
              {kpi.value}
            </Text>

            <div className="kpi-card__change">
              {kpi.change > 0 ? (
                <>
                  <ArrowTrendingUp24Regular style={{ color: '#107c10' }} />
                  <Badge appearance="filled" color="success">
                    +{kpi.change}%
                  </Badge>
                </>
              ) : (
                <>
                  <ArrowTrendingDown24Regular style={{ color: '#d83b01' }} />
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
        <Card className="dashboard-section">
          <Text size={500} weight="semibold">Revenue Forecasting</Text>
          <ForecastChart
            data={[
              { period: 'Jan', actual: 100, forecast: undefined },
              { period: 'Feb', actual: 120, forecast: undefined },
              { period: 'Mar', actual: 115, forecast: 118, lower_bound: 110, upper_bound: 126 },
              { period: 'Apr', forecast: 125, lower_bound: 115, upper_bound: 135 },
              { period: 'May', forecast: 132, lower_bound: 120, upper_bound: 144 }
            ]}
            height={300}
            yAxisLabel="Revenue ($K)"
          />
          <Button appearance="primary" onClick={() => navigate('/analytics/revenue')}>
            View Details
          </Button>
        </Card>

        <Card className="dashboard-section">
          <Text size={500} weight="semibold">Quick Actions</Text>
          <div className="quick-actions">
            <Button onClick={() => navigate('/analytics/pricing')}>
              Pricing Analysis
            </Button>
            <Button onClick={() => navigate('/analytics/customers')}>
              Customer Insights
            </Button>
            <Button onClick={() => navigate('/analytics/operations')}>
              Operations Dashboard
            </Button>
            <Button onClick={() => navigate('/analytics/marketing')}>
              Marketing ROI
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
};
```

### CSS Styles

Create `src/frontend/src/styles/AnalyticsDashboard.css`:

```css
.analytics-dashboard {
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

.analytics-dashboard__header {
  margin-bottom: 2rem;
}

.analytics-dashboard__kpis {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.kpi-card {
  padding: 1.5rem;
  transition: transform 0.2s, box-shadow 0.2s;
}

.kpi-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
}

.kpi-card__header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.kpi-card__icon {
  font-size: 24px;
}

.kpi-card__value {
  display: block;
  margin: 1rem 0;
}

.kpi-card__change {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.analytics-dashboard__sections {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1.5rem;
}

.dashboard-section {
  padding: 1.5rem;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 1rem;
}

.dashboard-loading {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}
```

---

## 🗺️ Routing Updates

Add to `src/frontend/src/App.tsx` or routing configuration:

```typescript
import { AnalyticsDashboard } from './pages/AnalyticsDashboard';

// In your routes:
<Route path="/analytics" element={<AnalyticsDashboard />} />
<Route path="/analytics/revenue" element={<RevenueDashboard />} />
<Route path="/analytics/customers" element={<CustomerDashboard />} />
<Route path="/analytics/operations" element={<OperationsDashboard />} />
<Route path="/analytics/pricing" element={<PricingDashboard />} />
<Route path="/analytics/marketing" element={<MarketingDashboard />} />
```

---

## 🧪 Testing

### Unit Tests

Create `src/frontend/src/components/content/__tests__/ForecastChart.test.tsx`:

```typescript
import { render, screen } from '@testing-library/react';
import { ForecastChart } from '../ForecastChart';

describe('ForecastChart', () => {
  const mockData = [
    { period: 1, actual: 100, forecast: undefined },
    { period: 2, actual: 120, forecast: 125, lower_bound: 110, upper_bound: 140 }
  ];

  it('renders chart with data', () => {
    render(<ForecastChart data={mockData} />);
    expect(screen.getByText(/Forecast Visualization/i)).toBeInTheDocument();
  });

  it('shows loading state', () => {
    render(<ForecastChart data={[]} loading={true} />);
    expect(screen.getByText(/Loading forecast data/i)).toBeInTheDocument();
  });

  it('toggles forecast visibility', async () => {
    const { getByText } = render(<ForecastChart data={mockData} />);
    const forecastToggle = getByText('Forecast');
    // Add toggle interaction test
  });
});
```

---

## 📋 Implementation Checklist

### Phase 1: Setup (Day 1)
- [ ] Install dependencies (recharts, @fluentui/react-charting)
- [ ] Create base component files
- [ ] Set up routing for analytics pages
- [ ] Create CSS files

### Phase 2: Dataset Panel (Day 1-2)
- [ ] Implement multi-upload functionality
- [ ] Add search and filter
- [ ] Create quick action buttons
- [ ] Add dataset summary modal
- [ ] Implement linking UI

### Phase 3: Visualization (Day 2-3)
- [ ] Build ForecastChart component
- [ ] Implement confidence intervals
- [ ] Add interactive controls
- [ ] Create ModelComparisonPanel
- [ ] Build metrics table

### Phase 4: Dashboards (Day 3-4)
- [ ] Create AnalyticsDashboard page
- [ ] Build KPI cards
- [ ] Integrate ForecastChart
- [ ] Add navigation links
- [ ] Implement data fetching

### Phase 5: Testing & Polish (Day 4)
- [ ] Write unit tests
- [ ] Test responsive design
- [ ] Add error handling
- [ ] Performance optimization
- [ ] Accessibility review

---

## 🎨 Design Guidelines

### Color Palette
- **Primary**: #0078d4 (Blue)
- **Success**: #107c10 (Green)  
- **Warning**: #faa700 (Amber)
- **Danger**: #d83b01 (Red)
- **Neutral**: #605e5c (Gray)

### Typography
- **Headers**: Segoe UI Bold, 24-32px
- **Body**: Segoe UI Regular, 14px
- **Captions**: Segoe UI Regular, 12px

### Spacing
- **Section Gap**: 24px
- **Card Padding**: 24px
- **Element Gap**: 12px

---

## 🚀 Next Steps

After implementing Sprint 4 components:

1. **Integration Testing** - Test with real backend data
2. **User Acceptance** - Gather feedback from business users
3. **Performance Tuning** - Optimize chart rendering
4. **Sprint 5** - Use cases, documentation, E2E tests

---

## 📚 Additional Resources

- [Recharts Documentation](https://recharts.org/en-US/)
- [Fluent UI React](https://react.fluentui.dev/)
- [React TypeScript Cheatsheet](https://react-typescript-cheatsheet.netlify.app/)

---

**Sprint 4 Status:** 📋 **READY FOR IMPLEMENTATION**

**Estimated Effort:** 3-4 days for experienced React developer

**Dependencies:** Sprints 1-3 backend APIs must be deployed

