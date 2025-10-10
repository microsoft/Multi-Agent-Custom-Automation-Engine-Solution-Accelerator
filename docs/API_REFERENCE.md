# Multi-Agent Custom Automation Engine - API Reference

**Version:** 1.0  
**Last Updated:** October 10, 2025  
**Base URL:** `http://localhost:8000/api/v3` (development) or `https://your-domain.com/api/v3` (production)

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [MCP Tools](#mcp-tools)
4. [REST API Endpoints](#rest-api-endpoints)
5. [Data Models](#data-models)
6. [Error Handling](#error-handling)
7. [Rate Limits](#rate-limits)
8. [Examples](#examples)

---

## Overview

The Multi-Agent Custom Automation Engine provides two types of APIs:

**MCP (Model Context Protocol) Tools**
- AI-callable functions for analytics and forecasting
- Invoked by agent teams
- Return structured JSON responses

**REST API Endpoints**
- HTTP-based APIs for web/mobile clients
- Standard CRUD operations for datasets, plans, teams
- Authentication required

---

## Authentication

### API Key Authentication

```http
GET /api/v3/datasets
Authorization: Bearer YOUR_API_KEY
```

### Azure AD (Entra ID) Authentication

```http
GET /api/v3/datasets
Authorization: Bearer AZURE_AD_TOKEN
```

**Obtaining a Token:**
```python
import requests

# Get token from Azure AD
token_response = requests.post(
    f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
    data={
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "api://macae/.default",
        "grant_type": "client_credentials"
    }
)
access_token = token_response.json()["access_token"]

# Use token in API calls
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.get("http://localhost:8000/api/v3/datasets", headers=headers)
```

---

## MCP Tools

### Finance Service (5 tools)

#### 1. `upload_dataset`

Upload a dataset for analysis.

**Parameters:**
```json
{
  "file_name": "sales_data.csv",
  "file_content": "base64_encoded_content",
  "description": "Monthly sales data"
}
```

**Returns:**
```json
{
  "dataset_id": "ds_abc123",
  "name": "sales_data.csv",
  "rows": 1250,
  "columns": ["Date", "Revenue", "Units"],
  "status": "uploaded"
}
```

---

#### 2. `list_datasets`

List all uploaded datasets.

**Parameters:**
```json
{}
```

**Returns:**
```json
{
  "datasets": [
    {
      "id": "ds_abc123",
      "name": "sales_data.csv",
      "uploaded_at": "2025-10-10T14:30:00Z",
      "rows": 1250,
      "size_bytes": 45000
    }
  ],
  "total_count": 1
}
```

---

#### 3. `download_dataset`

Download a dataset.

**Parameters:**
```json
{
  "dataset_id": "ds_abc123"
}
```

**Returns:**
```json
{
  "dataset_id": "ds_abc123",
  "name": "sales_data.csv",
  "content": "base64_encoded_content",
  "content_type": "text/csv"
}
```

---

#### 4. `generate_financial_forecast`

Generate revenue/financial forecast with confidence intervals.

**Parameters:**
```json
{
  "dataset_id": "ds_abc123",
  "target_column": "Revenue",
  "date_column": "Date",
  "method": "auto",
  "periods": 12,
  "confidence_level": 0.95
}
```

**Method Options:**
- `"auto"` - Auto-select best method (recommended)
- `"linear"` - Linear regression
- `"sarima"` - Seasonal ARIMA
- `"prophet"` - Facebook Prophet
- `"exponential_smoothing"` - Holt-Winters

**Returns:**
```json
{
  "method": "sarima",
  "forecast": [120000, 125000, 121000, 127000, 123000, 129000, 126000, 132000, 128000, 140000, 145000, 150000],
  "lower_bound": [115000, 119000, 115000, 120000, 116000, 121000, 118000, 124000, 120000, 132000, 136000, 140000],
  "upper_bound": [125000, 131000, 127000, 134000, 130000, 137000, 134000, 140000, 136000, 148000, 154000, 160000],
  "confidence_level": 0.95,
  "forecast_periods": 12,
  "historical_mean": 115000,
  "trend": "upward",
  "seasonality_detected": true,
  "seasonal_period": 12,
  "summary": "SARIMA forecast indicates steady growth with Q4 seasonal peaks"
}
```

---

#### 5. `evaluate_forecast_models`

Compare multiple forecasting methods and select the best.

**Parameters:**
```json
{
  "dataset_id": "ds_abc123",
  "target_column": "Revenue",
  "date_column": "Date",
  "methods": ["linear", "sarima", "prophet", "exponential_smoothing"],
  "test_split": 0.2
}
```

**Returns:**
```json
{
  "comparison_results": [
    {
      "method": "sarima",
      "mae": 2150.30,
      "rmse": 2847.52,
      "mape": 1.82,
      "rank": 1,
      "recommendation": "Best model - lowest error metrics"
    },
    {
      "method": "prophet",
      "mae": 2380.45,
      "rmse": 3021.87,
      "mape": 2.01,
      "rank": 2,
      "recommendation": "Strong alternative"
    },
    {
      "method": "exponential_smoothing",
      "mae": 2890.12,
      "rmse": 3542.90,
      "mape": 2.45,
      "rank": 3
    },
    {
      "method": "linear",
      "mae": 3450.78,
      "rmse": 4123.45,
      "mape": 2.91,
      "rank": 4
    }
  ],
  "best_method": "sarima",
  "confidence": "high"
}
```

---

### Customer Analytics Service (4 tools)

#### 1. `analyze_customer_churn`

Identify at-risk customers and churn drivers.

**Parameters:**
```json
{
  "churn_dataset": "customer_churn_analysis.csv",
  "profile_dataset": "customer_profile.csv",
  "risk_threshold": 0.7
}
```

**Returns:**
```json
{
  "total_customers": 500,
  "at_risk_customers": 87,
  "churn_rate": 17.4,
  "churn_drivers": [
    {
      "driver": "Low Engagement Score",
      "affected_customers": 52,
      "impact_score": 8.7,
      "recommendation": "Launch re-engagement campaign"
    }
  ],
  "high_priority_customers": [
    {
      "customer_id": "C1023",
      "churn_risk": 0.92,
      "total_spend": 15420,
      "recommendation": "Immediate intervention required"
    }
  ]
}
```

---

#### 2. `segment_customers`

Perform RFM (Recency, Frequency, Monetary) customer segmentation.

**Parameters:**
```json
{
  "purchase_dataset": "purchase_history.csv",
  "profile_dataset": "customer_profile.csv",
  "segmentation_method": "rfm"
}
```

**Returns:**
```json
{
  "segments": [
    {
      "segment": "Champions",
      "customer_count": 75,
      "percentage": 15.0,
      "avg_recency_days": 8,
      "avg_frequency": 24,
      "avg_monetary": 8450,
      "strategy": "Reward loyalty, ask for reviews"
    },
    {
      "segment": "At Risk",
      "customer_count": 65,
      "percentage": 13.0,
      "avg_recency_days": 78,
      "strategy": "Win-back campaigns"
    }
  ]
}
```

---

#### 3. `predict_customer_lifetime_value`

Predict Customer Lifetime Value (CLV) with confidence intervals.

**Parameters:**
```json
{
  "purchase_dataset": "purchase_history.csv",
  "profile_dataset": "customer_profile.csv",
  "forecast_months": 12,
  "discount_rate": 0.10
}
```

**Returns:**
```json
{
  "top_clv_customers": [
    {
      "customer_id": "C0456",
      "predicted_clv": 24500,
      "confidence_interval": [22100, 26900],
      "current_spend": 18200,
      "growth_potential": 34.6,
      "retention_priority": "critical"
    }
  ],
  "segment_clv_summary": [
    {
      "segment": "Champions",
      "avg_clv": 15800,
      "total_value": 1185000
    }
  ]
}
```

---

#### 4. `analyze_sentiment_trends`

Analyze customer sentiment trends and forecast future sentiment.

**Parameters:**
```json
{
  "sentiment_dataset": "social_media_sentiment_analysis.csv",
  "forecast_periods": 3
}
```

**Returns:**
```json
{
  "current_sentiment": {
    "avg_score": 72.4,
    "positive_customers": 285,
    "neutral_customers": 178,
    "negative_customers": 37
  },
  "sentiment_forecast": {
    "next_3_months": [71.2, 70.8, 70.1],
    "trend": "declining",
    "alert_level": "warning"
  },
  "negative_sentiment_drivers": [
    {
      "topic": "Shipping Delays",
      "affected_customers": 18,
      "recommendation": "Improve shipping communication"
    }
  ]
}
```

---

### Operations Analytics Service (4 tools)

#### 1. `forecast_delivery_performance`

Forecast delivery metrics and identify improvement opportunities.

**Parameters:**
```json
{
  "metrics_dataset": "delivery_performance_metrics.csv",
  "forecast_periods": 12,
  "target_metric": "on_time_delivery_rate"
}
```

**Returns:**
```json
{
  "current_performance": {
    "on_time_delivery_rate": 82.5,
    "avg_delivery_time_hours": 28.3
  },
  "forecast": {
    "next_12_months_on_time_rate": [83.1, 83.8, 84.2, 84.5, 85.0, 85.3, 85.7, 86.0, 86.2, 86.5, 86.8, 87.0],
    "trend": "improving"
  },
  "improvement_opportunities": [
    {
      "opportunity": "Route Optimization",
      "potential_improvement": "+2.5% on-time rate",
      "annual_benefit": "$45,000"
    }
  ]
}
```

---

#### 2. `optimize_inventory`

Optimize inventory levels across locations.

**Parameters:**
```json
{
  "purchase_dataset": "purchase_history.csv",
  "current_inventory_days": 45,
  "target_service_level": 0.95
}
```

**Returns:**
```json
{
  "current_state": {
    "avg_inventory_days": 45,
    "carrying_cost_annual": 285000,
    "stockout_rate": 3.2
  },
  "optimized_state": {
    "recommended_inventory_days": 32,
    "projected_carrying_cost": 205000,
    "projected_stockout_rate": 2.8
  },
  "savings_analysis": {
    "annual_carrying_cost_savings": 80000,
    "roi": 1358.0
  }
}
```

---

#### 3. `analyze_warehouse_incidents`

Analyze warehouse incident patterns and prevention opportunities.

**Parameters:**
```json
{
  "incident_dataset": "warehouse_incident_reports.csv",
  "time_period_months": 12
}
```

**Returns:**
```json
{
  "incident_summary": {
    "total_incidents": 147,
    "high_severity": 12,
    "total_cost_impact": 234000
  },
  "incident_categories": [
    {
      "category": "Equipment Malfunction",
      "count": 42,
      "total_cost": 96600,
      "prevention_recommendation": "Predictive maintenance"
    }
  ],
  "cost_reduction_opportunities": [
    {
      "initiative": "Predictive Maintenance",
      "implementation_cost": 25000,
      "annual_savings": 58000,
      "roi": 232.0
    }
  ]
}
```

---

#### 4. `get_operations_summary`

Get comprehensive operations health summary.

**Parameters:**
```json
{}
```

**Returns:**
```json
{
  "operations_health_score": 73.5,
  "grade": "B-",
  "key_metrics": {
    "delivery_performance": {"score": 82.5, "trend": "improving"},
    "inventory_efficiency": {"score": 68.0, "trend": "needs_improvement"},
    "safety_compliance": {"score": 78.0, "trend": "stable"}
  },
  "overall_recommendations": [
    {
      "priority": 1,
      "recommendation": "Implement inventory optimization",
      "annual_benefit": "$175,000"
    }
  ]
}
```

---

### Pricing Analytics Service (3 tools)

#### 1. `analyze_competitive_pricing`

Analyze competitive pricing and identify opportunities.

**Parameters:**
```json
{
  "pricing_dataset": "competitor_pricing_analysis.csv",
  "purchase_dataset": "purchase_history.csv"
}
```

**Returns:**
```json
{
  "pricing_overview": {
    "total_products_analyzed": 48,
    "overpriced": 12,
    "underpriced": 8,
    "avg_price_gap": -2.3
  },
  "pricing_opportunities": [
    {
      "product": "Premium Dress Collection",
      "our_price": 89.99,
      "competitor_avg_price": 119.99,
      "recommendation": "Increase price to $109.99",
      "estimated_revenue_impact": "+$45,000 annually"
    }
  ],
  "total_revenue_opportunity": 215000
}
```

---

#### 2. `optimize_discount_strategy`

Optimize discount strategies for maximum ROI.

**Parameters:**
```json
{
  "purchase_dataset": "purchase_history.csv",
  "competitor_dataset": "competitor_pricing_analysis.csv"
}
```

**Returns:**
```json
{
  "current_discount_performance": {
    "avg_discount_rate": 18.5,
    "discount_roi": 329.0
  },
  "optimization_analysis": [
    {
      "current_discount": "30% off Clearance",
      "recommendation": "Reduce to 25%",
      "margin_improvement": "+$8,500"
    }
  ],
  "optimization_impact": {
    "revenue_increase": 112000,
    "total_benefit": 135500
  }
}
```

---

#### 3. `forecast_revenue_by_category`

Forecast revenue by product category.

**Parameters:**
```json
{
  "purchase_dataset": "purchase_history.csv",
  "forecast_periods": 12
}
```

**Returns:**
```json
{
  "category_forecasts": [
    {
      "category": "Dresses",
      "current_monthly_avg": 45000,
      "forecast_12_months": [46000, 47500, 49000, ...],
      "total_forecast": 661500,
      "growth_rate": 22.6,
      "trend": "strong_growth"
    }
  ],
  "overall_forecast": {
    "total_revenue_12_months": 1349000,
    "yoy_growth": 18.2
  }
}
```

---

### Marketing Analytics Service (3 tools)

#### 1. `analyze_campaign_effectiveness`

Analyze email campaign performance and ROI.

**Parameters:**
```json
{
  "campaign_dataset": "email_marketing_engagement.csv"
}
```

**Returns:**
```json
{
  "campaign_performance_summary": {
    "total_campaigns": 24,
    "avg_open_rate": 22.5,
    "avg_click_rate": 3.8,
    "overall_roi": 670.8
  },
  "top_performing_campaigns": [
    {
      "campaign": "VIP Early Access",
      "open_rate": 45.2,
      "conversion_rate": 5.8,
      "roi": 1580.0,
      "recommendation": "Run quarterly"
    }
  ],
  "total_optimization_impact": 167000
}
```

---

#### 2. `predict_engagement`

Predict customer engagement likelihood.

**Parameters:**
```json
{
  "customer_dataset": "customer_profile.csv",
  "engagement_history": "email_marketing_engagement.csv"
}
```

**Returns:**
```json
{
  "engagement_predictions": [
    {
      "customer_id": "C1001",
      "engagement_probability": 0.85,
      "recommended_action": "Send personalized offer",
      "optimal_send_time": "Tuesday 10:00 AM"
    }
  ],
  "segment_engagement": [
    {
      "segment": "Champions",
      "avg_engagement_rate": 78.5,
      "best_channel": "Email"
    }
  ]
}
```

---

#### 3. `optimize_loyalty_program`

Optimize loyalty program design and benefits.

**Parameters:**
```json
{
  "loyalty_dataset": "loyalty_program_overview.csv",
  "purchase_dataset": "purchase_history.csv"
}
```

**Returns:**
```json
{
  "program_health": {
    "active_members": 285,
    "engagement_rate": 68.5,
    "redemption_rate": 42.0
  },
  "optimization_recommendations": [
    {
      "recommendation": "Point expiration alerts",
      "estimated_impact": "+$35,000 sales"
    },
    {
      "recommendation": "Tiered point earning",
      "estimated_impact": "+$45,000 revenue"
    }
  ],
  "total_program_value": 175500
}
```

---

## REST API Endpoints

### Datasets

#### GET `/api/v3/datasets`

List all datasets.

**Response:**
```json
{
  "datasets": [
    {
      "id": "ds_abc123",
      "name": "sales_data.csv",
      "created_at": "2025-10-10T14:30:00Z",
      "row_count": 1250,
      "column_count": 5
    }
  ]
}
```

---

#### POST `/api/v3/datasets`

Upload a new dataset.

**Request:**
```json
{
  "name": "sales_data.csv",
  "content": "base64_encoded_content"
}
```

**Response:**
```json
{
  "id": "ds_abc123",
  "name": "sales_data.csv",
  "status": "uploaded"
}
```

---

#### DELETE `/api/v3/datasets/{dataset_id}`

Delete a dataset.

**Response:**
```json
{
  "message": "Dataset deleted successfully",
  "dataset_id": "ds_abc123"
}
```

---

### Plans (Agent Executions)

#### GET `/api/v3/plans`

List all execution plans.

**Response:**
```json
{
  "plans": [
    {
      "id": "plan_xyz789",
      "name": "Revenue Forecast Q4 2025",
      "status": "completed",
      "created_at": "2025-10-10T15:00:00Z"
    }
  ]
}
```

---

#### GET `/api/v3/plans/{plan_id}`

Get plan details.

**Response:**
```json
{
  "id": "plan_xyz789",
  "name": "Revenue Forecast Q4 2025",
  "status": "completed",
  "results": {
    "forecast": [...]
  }
}
```

---

### Teams

#### POST `/api/v3/init_team`

Initialize an agent team.

**Request:**
```json
{
  "team_name": "finance_forecasting"
}
```

**Response:**
```json
{
  "team_id": "team_123",
  "team_name": "finance_forecasting",
  "status": "active",
  "agents": ["Financial Analyst", "Forecasting Specialist"]
}
```

---

## Data Models

### Dataset

```typescript
interface Dataset {
  id: string;
  name: string;
  created_at: string;  // ISO 8601
  row_count: number;
  column_count: number;
  size_bytes: number;
  status: "uploaded" | "processing" | "ready" | "error";
}
```

### ForecastResult

```typescript
interface ForecastResult {
  method: "linear" | "sarima" | "prophet" | "exponential_smoothing";
  forecast: number[];
  lower_bound: number[];
  upper_bound: number[];
  confidence_level: number;
  accuracy_metrics?: {
    mae: number;
    rmse: number;
    mape: number;
  };
}
```

---

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "INVALID_DATASET",
    "message": "Dataset not found",
    "details": {
      "dataset_id": "ds_invalid123"
    }
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `AUTHENTICATION_FAILED` | 401 | Invalid or missing auth token |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `DATASET_NOT_FOUND` | 404 | Dataset doesn't exist |
| `INVALID_PARAMETERS` | 400 | Invalid request parameters |
| `INSUFFICIENT_DATA` | 400 | Not enough data for analysis |
| `PROCESSING_ERROR` | 500 | Internal processing error |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |

---

## Rate Limits

**Default Limits:**
- 100 requests per minute per API key
- 1000 requests per hour per API key

**Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1633024800
```

**Exceeding Limits:**
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Retry after 60 seconds."
  }
}
```

---

## Examples

### Python Example

```python
import requests
import base64

# Configuration
API_BASE = "http://localhost:8000/api/v3"
API_KEY = "your_api_key_here"
headers = {"Authorization": f"Bearer {API_KEY}"}

# Upload dataset
with open("sales_data.csv", "rb") as f:
    content = base64.b64encode(f.read()).decode()

response = requests.post(
    f"{API_BASE}/datasets",
    json={"name": "sales_data.csv", "content": content},
    headers=headers
)
dataset_id = response.json()["id"]

# Generate forecast (via MCP tool)
forecast_result = requests.post(
    f"{API_BASE}/mcp/generate_financial_forecast",
    json={
        "dataset_id": dataset_id,
        "target_column": "Revenue",
        "date_column": "Date",
        "method": "auto",
        "periods": 12
    },
    headers=headers
).json()

print(f"Forecast: {forecast_result['forecast']}")
print(f"Method: {forecast_result['method']}")
print(f"MAPE: {forecast_result['accuracy_metrics']['mape']}%")
```

### JavaScript Example

```javascript
const API_BASE = 'http://localhost:8000/api/v3';
const API_KEY = 'your_api_key_here';

// Fetch datasets
async function getDatasets() {
  const response = await fetch(`${API_BASE}/datasets`, {
    headers: {
      'Authorization': `Bearer ${API_KEY}`
    }
  });
  return response.json();
}

// Generate forecast
async function generateForecast(datasetId) {
  const response = await fetch(`${API_BASE}/mcp/generate_financial_forecast`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${API_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      dataset_id: datasetId,
      target_column: 'Revenue',
      date_column: 'Date',
      method: 'auto',
      periods: 12
    })
  });
  return response.json();
}

// Usage
const datasets = await getDatasets();
const forecast = await generateForecast(datasets.datasets[0].id);
console.log('Forecast:', forecast.forecast);
```

---

**API Reference Version:** 1.0  
**Last Updated:** October 10, 2025

For support: api-support@yourcompany.com  
For feature requests: Submit via GitHub Issues

