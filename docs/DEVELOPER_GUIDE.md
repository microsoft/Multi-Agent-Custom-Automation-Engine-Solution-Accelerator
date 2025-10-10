# Multi-Agent Custom Automation Engine - Developer Guide

**Version:** 1.0  
**Last Updated:** October 10, 2025  
**Audience:** Software Engineers, Data Scientists, Technical Contributors

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Development Environment Setup](#development-environment-setup)
3. [Adding New Analytics Tools](#adding-new-analytics-tools)
4. [Adding New Forecasting Methods](#adding-new-forecasting-methods)
5. [Frontend Component Development](#frontend-component-development)
6. [Testing Guidelines](#testing-guidelines)
7. [Deployment](#deployment)
8. [API Integration](#api-integration)
9. [Performance Optimization](#performance-optimization)
10. [Contributing](#contributing)

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                         Azure Cloud                          │
│  ┌────────────────┐  ┌──────────────┐  ┌─────────────┐     │
│  │  Azure AI      │  │  Cosmos DB   │  │  Storage    │     │
│  │  Services      │  │  (Data)      │  │  (Datasets) │     │
│  └────────────────┘  └──────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  v3 API      │  │  Auth        │  │  Middleware  │      │
│  │  /api/v3/*   │  │  Layer       │  │  (CORS)      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  ┌──────────────────────────────────────────────────┐       │
│  │           MCP Server (FastMCP)                    │       │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐    │       │
│  │  │Finance │ │Customer│ │Operations│ │Pricing│    │       │
│  │  │Service │ │Service │ │ Service  │ │Service│    │       │
│  │  └────────┘ └────────┘ └────────┘ └────────┘    │       │
│  └──────────────────────────────────────────────────┘       │
│                                                              │
│  ┌──────────────────────────────────────────────────┐       │
│  │           Utility Functions                       │       │
│  │  advanced_forecasting | customer_analytics |     │       │
│  │  operations_analytics | pricing_analytics  |     │       │
│  │  marketing_analytics  | dataset_utils      │     │       │
│  └──────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────┐
│              Frontend (React + TypeScript)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Pages       │  │  Components  │  │  Services    │      │
│  │  HomePage    │  │  ForecastChart│ │  APIClient   │      │
│  │  Analytics   │  │  KPI Cards   │  │  TeamService │      │
│  │  Dashboard   │  │  DataPanel   │  │  DataService │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  Tech Stack: Vite + React 18 + TypeScript + Fluent UI      │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

**Backend:**
- **Framework:** FastAPI (Python 3.11+)
- **MCP Server:** FastMCP (Model Context Protocol)
- **Database:** Azure Cosmos DB
- **Storage:** Azure Blob Storage
- **AI:** Azure OpenAI Service

**Frontend:**
- **Build Tool:** Vite
- **Framework:** React 18
- **Language:** TypeScript
- **UI Library:** Fluent UI React v9
- **Charts:** Recharts
- **HTTP Client:** Fetch API with custom wrapper

**Analytics:**
- **Forecasting:** statsmodels, Prophet, scikit-learn
- **Data Processing:** pandas, numpy
- **Testing:** pytest, pytest-asyncio

---

## Development Environment Setup

### Prerequisites

```bash
# Required
- Python 3.11+
- Node.js 18+
- npm or yarn
- Git

# Recommended
- VS Code with extensions:
  - Python
  - Pylance
  - ESLint
  - Prettier
```

### Local Setup

#### 1. Clone Repository

```bash
git clone <repository-url>
cd Multi-Agent-Custom-Automation-Engine-Solution-Accelerator
```

#### 2. Backend Setup

```bash
# Navigate to backend
cd src/backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -e .

# Or using requirements.txt:
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your Azure credentials
```

#### 3. MCP Server Setup

```bash
cd src/mcp_server

# Install dependencies
pip install -e .

# Copy environment template
cp .env.example .env
```

#### 4. Frontend Setup

```bash
cd src/frontend

# Install dependencies
npm install

# Copy environment template
cp .env.example .env
```

#### 5. Run Locally

**Terminal 1 - Backend:**
```bash
cd src/backend
uvicorn app_kernel:app --reload --port 8000
```

**Terminal 2 - MCP Server:**
```bash
cd src/mcp_server
python mcp_server.py
```

**Terminal 3 - Frontend:**
```bash
cd src/frontend
npm run dev
```

**Access:**
- Frontend: http://localhost:3001
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Adding New Analytics Tools

### Overview

Analytics tools are implemented as MCP (Model Context Protocol) tools within service classes. Each service represents a business domain (Finance, Customer, Operations, etc.).

### Step-by-Step Guide

#### Step 1: Create Utility Function

Create your analytics logic in `src/backend/common/utils/`:

```python
# src/backend/common/utils/my_analytics.py

import pandas as pd
from typing import List, Dict, Any

def analyze_my_metric(
    data: List[Dict[str, Any]],
    threshold: float = 0.5
) -> Dict[str, Any]:
    """
    Analyze a custom business metric.
    
    Args:
        data: List of data records
        threshold: Threshold for classification
        
    Returns:
        Dictionary with analysis results
    """
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Perform analysis
    total_records = len(df)
    above_threshold = len(df[df['value'] > threshold])
    
    # Calculate metrics
    percentage = (above_threshold / total_records) * 100 if total_records > 0 else 0
    
    # Generate insights
    insights = []
    if percentage > 75:
        insights.append("Strong performance - majority above threshold")
    elif percentage < 25:
        insights.append("Needs attention - majority below threshold")
    else:
        insights.append("Mixed performance - review individual cases")
    
    return {
        "total_records": total_records,
        "above_threshold": above_threshold,
        "percentage": round(percentage, 2),
        "insights": insights,
        "recommendation": _generate_recommendation(percentage)
    }

def _generate_recommendation(percentage: float) -> str:
    """Generate actionable recommendation."""
    if percentage > 75:
        return "Maintain current strategy"
    elif percentage > 50:
        return "Optimize underperforming segments"
    else:
        return "Implement improvement initiative"
```

#### Step 2: Create MCP Service (if new domain)

If adding to existing service, skip to Step 3. For new domain:

```python
# src/mcp_server/services/my_service.py

from typing import Any, Dict
from fastmcp import FastMCP
from core.factory import Domain, MCPToolBase
from common.utils.my_analytics import analyze_my_metric

class MyAnalyticsService(MCPToolBase):
    """Service for my custom analytics."""
    
    def __init__(self):
        """Initialize service."""
        super().__init__(domain=Domain.GENERAL, description="Custom analytics service")
    
    def register_tools(self, mcp: FastMCP) -> None:
        """Register MCP tools."""
        
        @mcp.tool()
        async def analyze_metric(
            dataset_name: str,
            threshold: float = 0.5
        ) -> Dict[str, Any]:
            """
            Analyze custom metric from dataset.
            
            Args:
                dataset_name: Name of uploaded dataset
                threshold: Classification threshold (0-1)
                
            Returns:
                Analysis results with insights and recommendations
            """
            try:
                # Load dataset
                data = await self._load_dataset(dataset_name)
                
                # Run analysis
                result = analyze_my_metric(
                    data=data,
                    threshold=threshold
                )
                
                # Add metadata
                result["dataset"] = dataset_name
                result["threshold_used"] = threshold
                
                return result
                
            except Exception as e:
                return {
                    "error": str(e),
                    "dataset": dataset_name
                }
    
    @property
    def tool_count(self) -> int:
        """Number of tools provided."""
        return 1
```

#### Step 3: Register Service

Add to `src/mcp_server/mcp_server.py`:

```python
# Import your service
from services.my_service import MyAnalyticsService

# In the initialization function
def initialize_services():
    """Register all services."""
    factory = MCPToolFactory(mcp)
    
    # Existing services...
    factory.register_service(FinanceService())
    factory.register_service(CustomerAnalyticsService())
    
    # Your new service
    factory.register_service(MyAnalyticsService())
    
    return factory
```

#### Step 4: Add Tests

```python
# src/backend/tests/test_my_analytics.py

import pytest
from common.utils.my_analytics import analyze_my_metric

class TestAnalyzeMyMetric:
    """Tests for my custom analytics."""
    
    def test_basic_analysis(self):
        """Test basic metric analysis."""
        data = [
            {"value": 0.8},
            {"value": 0.6},
            {"value": 0.3}
        ]
        
        result = analyze_my_metric(data, threshold=0.5)
        
        assert result["total_records"] == 3
        assert result["above_threshold"] == 2
        assert result["percentage"] == 66.67
        assert "insights" in result
        assert "recommendation" in result
    
    def test_edge_case_empty_data(self):
        """Test with empty dataset."""
        result = analyze_my_metric([], threshold=0.5)
        
        assert result["total_records"] == 0
        assert result["percentage"] == 0
    
    def test_all_above_threshold(self):
        """Test when all values exceed threshold."""
        data = [{"value": 0.9}, {"value": 0.8}, {"value": 0.7}]
        
        result = analyze_my_metric(data, threshold=0.5)
        
        assert result["percentage"] == 100.0
        assert "Strong performance" in result["insights"][0]
```

#### Step 5: Document Your Tool

Add to API reference and update relevant docs.

---

## Adding New Forecasting Methods

### Overview

Forecasting methods are implemented in `src/backend/common/utils/advanced_forecasting.py` and integrated with the auto-selection framework.

### Step-by-Step Guide

#### Step 1: Implement Forecast Function

```python
# src/backend/common/utils/advanced_forecasting.py

def my_custom_forecast(
    values: List[float],
    periods: int = 12,
    confidence_level: float = 0.95
) -> Dict[str, Any]:
    """
    Custom forecasting method.
    
    Args:
        values: Historical time series data
        periods: Number of periods to forecast
        confidence_level: Confidence level for intervals (0-1)
        
    Returns:
        Dictionary with forecast, bounds, and metadata
    """
    try:
        # Validate inputs
        if len(values) < 3:
            return {
                "error": "Insufficient data - need at least 3 points",
                "method": "my_custom_forecast"
            }
        
        # Implement your forecasting logic
        # Example: Simple moving average
        window = min(3, len(values))
        moving_avg = sum(values[-window:]) / window
        
        # Generate forecast
        forecast = [moving_avg] * periods
        
        # Calculate confidence intervals
        # (simplified example - use proper statistical methods)
        std_dev = np.std(values)
        z_score = 1.96  # for 95% confidence
        margin = z_score * std_dev
        
        lower_bound = [f - margin for f in forecast]
        upper_bound = [f + margin for f in forecast]
        
        return {
            "method": "my_custom_forecast",
            "forecast": forecast,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "confidence_level": confidence_level,
            "parameters": {
                "window_size": window
            }
        }
        
    except Exception as e:
        return {
            "error": f"Forecast failed: {str(e)}",
            "method": "my_custom_forecast"
        }
```

#### Step 2: Add to Auto-Selection

Update `auto_select_forecast_method()` to include your method:

```python
def auto_select_forecast_method(
    values: List[float],
    periods: int = 12,
    confidence_level: float = 0.95
) -> Dict[str, Any]:
    """Auto-select best forecasting method."""
    
    # Split data for validation
    train_size = int(len(values) * 0.8)
    train_data = values[:train_size]
    test_data = values[train_size:]
    
    # Test all methods
    methods = {
        "linear": linear_forecast_with_confidence,
        "sarima": sarima_forecast,
        "prophet": prophet_forecast,
        "exponential_smoothing": exponential_smoothing_forecast,
        "my_custom": my_custom_forecast  # Add your method
    }
    
    results = {}
    for method_name, method_func in methods.items():
        # Train on training data
        forecast_result = method_func(
            train_data,
            periods=len(test_data),
            confidence_level=confidence_level
        )
        
        if "error" not in forecast_result:
            # Evaluate accuracy
            accuracy = evaluate_forecast_accuracy(
                actual=test_data,
                forecast=forecast_result["forecast"]
            )
            results[method_name] = accuracy
    
    # Select best method (lowest MAPE)
    best_method = min(results, key=lambda x: results[x]["mape"])
    
    # Generate final forecast with best method
    final_forecast = methods[best_method](
        values,
        periods=periods,
        confidence_level=confidence_level
    )
    
    final_forecast["selected_method"] = best_method
    final_forecast["method_comparison"] = results
    
    return final_forecast
```

#### Step 3: Add Tests

```python
# src/backend/tests/test_advanced_forecasting.py

class TestMyCustomForecast:
    """Tests for custom forecast method."""
    
    def test_basic_forecast(self):
        """Test basic forecasting."""
        values = [100, 110, 105, 115, 120]
        result = my_custom_forecast(values, periods=3)
        
        assert "forecast" in result
        assert len(result["forecast"]) == 3
        assert "lower_bound" in result
        assert "upper_bound" in result
        assert result["method"] == "my_custom_forecast"
    
    def test_confidence_intervals(self):
        """Test confidence intervals are valid."""
        values = [100, 110, 120, 130]
        result = my_custom_forecast(values, periods=2, confidence_level=0.95)
        
        forecast = result["forecast"]
        lower = result["lower_bound"]
        upper = result["upper_bound"]
        
        for i in range(len(forecast)):
            assert lower[i] <= forecast[i] <= upper[i]
    
    def test_insufficient_data(self):
        """Test error handling with insufficient data."""
        values = [100, 110]
        result = my_custom_forecast(values, periods=3)
        
        assert "error" in result
```

---

## Frontend Component Development

### Creating a New Component

#### Step 1: Create Component File

```typescript
// src/frontend/src/components/content/MyComponent.tsx

import React, { useState, useEffect } from 'react';
import { Card } from '@fluentui/react-components';
import './MyComponent.css';

interface MyComponentProps {
  title: string;
  data?: any[];
  onAction?: () => void;
}

export const MyComponent: React.FC<MyComponentProps> = ({
  title,
  data = [],
  onAction
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Fetch data or perform initialization
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      // Fetch data from API
      const response = await fetch('/api/v3/my-endpoint');
      const result = await response.json();
      // Process result
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="my-component">
      <div className="my-component-header">
        <h2>{title}</h2>
      </div>
      
      <div className="my-component-content">
        {loading && <div>Loading...</div>}
        {error && <div className="error">{error}</div>}
        {!loading && !error && (
          <div className="data-display">
            {/* Render your data */}
          </div>
        )}
      </div>
    </Card>
  );
};

export default MyComponent;
```

#### Step 2: Create Styles

```css
/* src/frontend/src/styles/MyComponent.css */

.my-component {
  padding: 20px;
  margin: 16px 0;
  background: var(--colorNeutralBackground1);
  border-radius: 8px;
}

.my-component-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.my-component-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--colorNeutralForeground1);
}

.my-component-content {
  min-height: 200px;
}

.error {
  color: var(--colorPaletteRedForeground1);
  padding: 12px;
  background: var(--colorPaletteRedBackground1);
  border-radius: 4px;
}
```

#### Step 3: Add to Page

```typescript
// src/frontend/src/pages/MyPage.tsx

import React from 'react';
import { MyComponent } from '../components/content/MyComponent';

export const MyPage: React.FC = () => {
  return (
    <div className="my-page">
      <MyComponent title="My Analytics" />
    </div>
  );
};

export default MyPage;
```

### Using Recharts for Visualization

```typescript
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const MyChart = ({ data }) => {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="value" stroke="#8884d8" />
      </LineChart>
    </ResponsiveContainer>
  );
};
```

---

## Testing Guidelines

### Backend Unit Tests

**File Structure:**
```
src/backend/tests/
├── conftest.py          # Shared fixtures
├── test_*.py            # Test modules
└── README.md
```

**Example Test:**
```python
import pytest
from common.utils.my_analytics import analyze_my_metric

@pytest.fixture
def sample_data():
    """Provide sample data for tests."""
    return [
        {"id": 1, "value": 0.8},
        {"id": 2, "value": 0.6},
        {"id": 3, "value": 0.3}
    ]

class TestMyAnalytics:
    def test_basic_functionality(self, sample_data):
        """Test basic analysis."""
        result = analyze_my_metric(sample_data)
        assert result["total_records"] == 3
        assert "insights" in result
    
    def test_edge_cases(self):
        """Test edge cases."""
        # Empty data
        result = analyze_my_metric([])
        assert result["total_records"] == 0
        
        # Single record
        result = analyze_my_metric([{"value": 0.5}])
        assert result["total_records"] == 1
```

**Run Tests:**
```bash
# All tests
pytest

# Specific file
pytest src/backend/tests/test_my_analytics.py

# With coverage
pytest --cov=src/backend/common/utils
```

### Frontend Tests

```typescript
// src/frontend/src/__tests__/MyComponent.test.tsx

import { render, screen } from '@testing-library/react';
import { MyComponent } from '../components/content/MyComponent';

describe('MyComponent', () => {
  it('renders title correctly', () => {
    render(<MyComponent title="Test Title" />);
    expect(screen.getByText('Test Title')).toBeInTheDocument();
  });

  it('handles loading state', () => {
    render(<MyComponent title="Test" />);
    // Add assertions for loading state
  });
});
```

---

## Deployment

See [Production Deployment Guide](PRODUCTION_DEPLOYMENT.md) for detailed instructions.

**Quick Reference:**

```bash
# Azure deployment
azd up

# Docker build
docker build -t macae-backend -f src/backend/Dockerfile .
docker build -t macae-frontend -f src/frontend/Dockerfile .

# Frontend production build
cd src/frontend
npm run build
```

---

## API Integration

### Creating New Endpoints

```python
# src/backend/v3/api/my_endpoints.py

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

router = APIRouter(prefix="/my-analytics", tags=["My Analytics"])

@router.get("/analyze")
async def analyze_data(
    dataset_id: str,
    threshold: float = 0.5
) -> Dict[str, Any]:
    """
    Analyze dataset with custom logic.
    
    Args:
        dataset_id: Dataset identifier
        threshold: Analysis threshold
        
    Returns:
        Analysis results
    """
    try:
        # Load data
        data = await load_dataset(dataset_id)
        
        # Perform analysis
        result = analyze_my_metric(data, threshold)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Register Router

```python
# src/backend/v3/api/router.py

from v3.api.my_endpoints import router as my_router

# Add to main router
app.include_router(my_router, prefix="/api/v3")
```

---

## Performance Optimization

### Backend

**Async Operations:**
```python
async def process_large_dataset(data):
    # Use async for I/O operations
    result = await async_processing(data)
    return result
```

**Caching:**
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_computation(param):
    # Cached result
    return result
```

### Frontend

**Code Splitting:**
```typescript
const MyComponent = React.lazy(() => import('./MyComponent'));

<Suspense fallback={<Loading />}>
  <MyComponent />
</Suspense>
```

**Memoization:**
```typescript
const MemoizedComponent = React.memo(MyComponent);

const expensiveValue = useMemo(() => {
  return computeExpensiveValue(data);
}, [data]);
```

---

## Contributing

### Code Style

**Python:**
- Follow PEP 8
- Use type hints
- Document all functions
- Max line length: 100 characters

**TypeScript:**
- Use ES6+ features
- Prefer interfaces over types
- Document complex logic
- Use Prettier for formatting

### Pull Request Process

1. Create feature branch from `main`
2. Make changes with tests
3. Run linters and tests
4. Submit PR with description
5. Address review feedback
6. Merge after approval

---

**Developer Guide Version:** 1.0  
**Last Updated:** October 10, 2025  
**Maintainer:** Development Team

For questions: development@yourcompany.com



