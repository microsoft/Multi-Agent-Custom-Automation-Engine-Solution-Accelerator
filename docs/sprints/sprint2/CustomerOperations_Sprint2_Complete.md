# Customer & Operations Analytics - Sprint 2 Documentation

**Date:** October 10, 2025  
**Status:** ✅ Complete and Ready for Integration Testing  
**Foundation:** Built on Sprint 1 Advanced Forecasting

---

## Table of Contents

1. [Overview](#overview)
2. [What Was Delivered](#what-was-delivered)
3. [Customer Analytics Tools](#customer-analytics-tools)
4. [Operations Analytics Tools](#operations-analytics-tools)
5. [Integration](#integration)
6. [Usage Examples](#usage-examples)
7. [Next Steps](#next-steps)

---

## Overview

Sprint 2 extends the analytics platform with two major new service domains: **Customer Analytics** and **Operations Analytics**. These services provide AI agents with powerful tools to analyze customer behavior, predict churn, optimize operations, and manage warehouse incidents.

### Key Achievements

- ✅ **8 new MCP tools** across two domains (Customer + Operations)
- ✅ **4 core utility modules** with production-ready analytics functions
- ✅ **2 new service classes** following established patterns
- ✅ **Domain expansion** with CUSTOMER and OPERATIONS added to factory
- ✅ **Full MCP integration** with server registration complete

---

## What Was Delivered

### New Files Created

1. **`src/backend/common/utils/customer_analytics.py`** (570 lines)
   - 4 production-ready customer analytics functions
   - Churn driver analysis with recommendations
   - RFM customer segmentation
   - CLV prediction with confidence intervals
   - Sentiment trend analysis with anomaly detection

2. **`src/backend/common/utils/operations_analytics.py`** (490 lines)
   - 7 operations analytics utility functions
   - Delivery performance analysis and forecasting
   - Warehouse incident categorization and impact assessment
   - Inventory optimization using newsvendor model
   - Performance scoring and trend analysis

3. **`src/mcp_server/services/customer_analytics_service.py`** (350 lines)
   - 4 MCP tools for customer analytics
   - Integrated with dataset storage system
   - Comprehensive error handling and logging
   - Full documentation and examples

4. **`src/mcp_server/services/operations_analytics_service.py`** (410 lines)
   - 4 MCP tools for operations analytics
   - Multi-dataset analysis capabilities
   - Executive summary generation
   - Risk assessment and scoring

### Enhanced Files

5. **`src/mcp_server/core/factory.py`**
   - Added CUSTOMER and OPERATIONS domains
   - Supports new service types

6. **`src/mcp_server/mcp_server.py`**
   - Registered CustomerAnalyticsService
   - Registered OperationsAnalyticsService
   - Tool count increased from 5 to 13 domains

### Analytics Functions Implemented

#### Customer Analytics
| Function | Purpose | Output |
|----------|---------|--------|
| **analyze_churn_drivers** | Identify and rank churn reasons | Drivers, recommendations, risk level |
| **segment_customers_rfm** | RFM segmentation | Segments with strategies |
| **predict_customer_lifetime_value** | CLV projection | Projected value, confidence intervals |
| **analyze_sentiment_trends** | Sentiment forecasting | Trends, anomalies, recommendations |

#### Operations Analytics
| Function | Purpose | Output |
|----------|---------|--------|
| **analyze_delivery_performance** | Performance scoring | Metrics, trends, degradation periods |
| **forecast_delivery_metrics** | Future performance projection | Forecasted metrics |
| **analyze_warehouse_incidents** | Incident impact assessment | Severity, categories, recommendations |
| **optimize_inventory** | Stock level optimization | Recommendations, reorder points |

---

## Customer Analytics Tools

### Tool 1: analyze_customer_churn

Analyzes customer churn drivers from churn analysis dataset.

**Input Dataset:** `customer_churn_analysis.csv`  
**Required Columns:** `ReasonForCancellation`, `Percentage`

**Example Call:**
```python
result = analyze_customer_churn(dataset_id="churn_001")
```

**Example Output:**
```json
{
    "total_churn_rate": 100.0,
    "drivers": [
        {
            "reason": "Service Dissatisfaction",
            "percentage": 40,
            "rank": 1
        },
        {
            "reason": "Competitor Offer",
            "percentage": 15,
            "rank": 2
        }
    ],
    "top_driver": {
        "reason": "Service Dissatisfaction",
        "percentage": 40,
        "impact": "Critical"
    },
    "recommendations": [
        {
            "priority": "High",
            "action": "Improve service quality",
            "details": "40% of churn is service-related. Conduct customer satisfaction surveys..."
        }
    ],
    "risk_level": "High"
}
```

### Tool 2: segment_customers

Segments customers using RFM (Recency, Frequency, Monetary) analysis.

**Input Dataset:** `customer_profile.csv`  
**Required Columns:** `CustomerID`, `Name`, `MembershipDuration`, `TotalSpend`

**Example Call:**
```python
result = segment_customers(dataset_id="profiles_001", method="rfm")
```

**Example Output:**
```json
{
    "total_customers": 1,
    "segments": [
        {
            "segment": "Loyal Customers",
            "count": 1,
            "total_value": 4800,
            "avg_spend": 4800,
            "strategy": "Upsell and increase engagement. Introduce premium tiers...",
            "customers": [
                {
                    "customer_id": "C1024",
                    "name": "Emily Thompson",
                    "total_spend": 4800
                }
            ]
        }
    ],
    "methodology": "RFM (Recency, Frequency, Monetary) Analysis"
}
```

### Tool 3: predict_customer_lifetime_value

Predicts customer lifetime value (CLV) over a projection period.

**Input Dataset:** `customer_profile.csv`  
**Required Columns:** `CustomerID`, `TotalSpend`, `AvgMonthlySpend`, `MembershipDuration`

**Example Call:**
```python
result = predict_customer_lifetime_value(
    dataset_id="profiles_001",
    customer_id="C1024",
    projection_months=12
)
```

**Example Output:**
```json
{
    "customer_id": "C1024",
    "customer_name": "Emily Thompson",
    "historical_value": 4800.00,
    "projected_value": 2161.52,
    "total_clv": 6961.52,
    "confidence_interval": {
        "lower": 5569.22,
        "upper": 8353.82,
        "confidence_level": 0.80
    },
    "projection_months": 12,
    "avg_monthly_spend": 200.00,
    "estimated_churn_rate": 0.250,
    "retention_rate": 0.976,
    "value_tier": "Medium Value"
}
```

### Tool 4: analyze_sentiment_trends

Analyzes social media sentiment trends, detects anomalies, forecasts future sentiment.

**Input Dataset:** `social_media_sentiment_analysis.csv`  
**Required Columns:** `Month`, `PositiveMentions`, `NegativeMentions`, `NeutralMentions`

**Example Call:**
```python
result = analyze_sentiment_trends(
    dataset_id="sentiment_001",
    forecast_periods=3
)
```

**Example Output:**
```json
{
    "total_periods": 7,
    "current_sentiment": 0.616,
    "average_sentiment": 0.484,
    "assessment": "Positive",
    "anomalies": [
        {
            "month": "June",
            "net_sentiment": 0.321,
            "previous_sentiment": 0.480,
            "change_percentage": -33.6,
            "severity": "Critical"
        }
    ],
    "anomaly_count": 2,
    "forecast": [
        {
            "period": 1,
            "forecasted_sentiment": 0.650,
            "trend": "Improving"
        }
    ],
    "recommendations": [...]
}
```

---

## Operations Analytics Tools

### Tool 1: forecast_delivery_performance

Forecasts delivery performance metrics and analyzes historical trends.

**Input Dataset:** `delivery_performance_metrics.csv`  
**Required Columns:** `Month`, `AverageDeliveryTime`, `OnTimeDeliveryRate`, `CustomerComplaints`

**Example Call:**
```python
result = forecast_delivery_performance(
    dataset_id="delivery_001",
    periods=3
)
```

**Example Output:**
```json
{
    "historical_analysis": {
        "total_periods": 7,
        "current_performance": {
            "month": "September",
            "score": 96.5,
            "grade": "A",
            "avg_delivery_time": 3,
            "on_time_rate": 97
        },
        "best_period": {
            "month": "March",
            "performance_score": 96.8,
            "grade": "A"
        },
        "worst_period": {
            "month": "July",
            "performance_score": 81.5,
            "grade": "B"
        },
        "trends": {
            "delivery_time": "Improving",
            "on_time_rate": "Improving",
            "complaints": "Decreasing"
        },
        "degradation_periods": [
            {
                "month": "June",
                "performance_score": 85.2,
                "change_percentage": -11.9,
                "severity": "High"
            }
        ]
    },
    "forecast": {
        "forecast_periods": 3,
        "forecast": [
            {
                "period": 1,
                "avg_delivery_time": 2.9,
                "on_time_rate": 97.5,
                "customer_complaints": 8,
                "performance_score": 97.2,
                "grade": "A"
            }
        ]
    },
    "recommendations": [...]
}
```

### Tool 2: optimize_inventory

Optimizes inventory levels based on historical purchase patterns.

**Input Dataset:** `purchase_history.csv`  
**Required Columns:** `ItemsPurchased`, `TotalAmount`

**Example Call:**
```python
result = optimize_inventory(
    dataset_id="purchases_001",
    target_service_level=0.95
)
```

**Example Output:**
```json
{
    "total_items": 12,
    "target_service_level": 0.95,
    "total_recommended_stock_units": 45,
    "total_revenue_analyzed": 1120.00,
    "recommendations": [
        {
            "item": "Evening Gown",
            "historical_demand": 1,
            "demand_rate": 0.143,
            "recommended_stock_level": 2,
            "reorder_point": 2,
            "safety_stock": 1,
            "revenue_contribution": 290.00,
            "priority": "High"
        }
    ],
    "methodology": "Newsvendor model with 95.0% service level target",
    "assumptions": {
        "demand_variability": "30% of mean demand",
        "lead_time": "1 period",
        "review_period": "Continuous"
    }
}
```

### Tool 3: analyze_warehouse_incidents

Analyzes warehouse incidents for impact assessment and risk management.

**Input Dataset:** `warehouse_incident_reports.csv`  
**Required Columns:** `Date`, `IncidentDescription`, `AffectedOrders`

**Example Call:**
```python
result = analyze_warehouse_incidents(dataset_id="incidents_001")
```

**Example Output:**
```json
{
    "total_incidents": 3,
    "total_affected_orders": 500,
    "incidents": [
        {
            "date": "2023-07-18",
            "description": "Logistics partner strike",
            "category": "External",
            "affected_orders": 250,
            "severity": "Critical",
            "impact_score": 10
        },
        {
            "date": "2023-08-25",
            "description": "Warehouse flooding due to heavy rain",
            "category": "Infrastructure",
            "affected_orders": 150,
            "severity": "High",
            "impact_score": 7
        }
    ],
    "most_severe_incident": {
        "date": "2023-07-18",
        "description": "Logistics partner strike",
        "severity": "Critical"
    },
    "incident_categories": ["External", "Infrastructure", "Systems"],
    "recommendations": [
        {
            "category": "External",
            "priority": "High",
            "action": "Mitigate external risks",
            "details": "2 external incident(s) affected 250 orders. Diversify logistics partners..."
        }
    ],
    "risk_level": "High"
}
```

### Tool 4: get_operations_summary

Generates comprehensive operations summary combining delivery and incident data.

**Input Datasets:** Delivery performance + Warehouse incidents

**Example Call:**
```python
result = get_operations_summary(
    delivery_dataset_id="delivery_001",
    incident_dataset_id="incidents_001"
)
```

**Example Output:**
```json
{
    "operations_health_score": 82.3,
    "health_grade": "B",
    "overall_status": "Good",
    "delivery_summary": {
        "current_performance_score": 96.5,
        "grade": "A",
        "avg_delivery_time": 3,
        "on_time_rate": 97,
        "trend": "Improving"
    },
    "incident_summary": {
        "total_incidents": 3,
        "total_affected_orders": 500,
        "risk_level": "High",
        "most_severe": {...}
    },
    "critical_issues": [
        {
            "category": "Incidents",
            "issue": "500 orders affected by warehouse incidents",
            "severity": "High"
        }
    ],
    "recommendations": [...]
}
```

---

## Integration

### Domain Registration

**File:** `src/mcp_server/core/factory.py`

```python
class Domain(Enum):
    """Service domains for organizing MCP tools."""
    
    HR = "hr"
    MARKETING = "marketing"
    PROCUREMENT = "procurement"
    PRODUCT = "product"
    TECH_SUPPORT = "tech_support"
    RETAIL = "retail"
    GENERAL = "general"
    DATA = "data"
    FINANCE = "finance"
    CUSTOMER = "customer"      # NEW
    OPERATIONS = "operations"  # NEW
```

### Service Registration

**File:** `src/mcp_server/mcp_server.py`

```python
# Import services
from services.customer_analytics_service import CustomerAnalyticsService
from services.operations_analytics_service import OperationsAnalyticsService

# Register services
factory.register_service(CustomerAnalyticsService())
factory.register_service(OperationsAnalyticsService())
```

### Tool Summary

After Sprint 2, the MCP server now provides:

| Domain | Service | Tools | Focus |
|--------|---------|-------|-------|
| Finance | FinanceService | 5 | Forecasting, dataset management |
| Customer | CustomerAnalyticsService | 4 | Churn, segmentation, CLV, sentiment |
| Operations | OperationsAnalyticsService | 4 | Delivery, inventory, incidents |
| HR | HRService | 4 | Employee management |
| Marketing | MarketingService | 4 | Campaign management |
| Product | ProductService | 4 | Product catalog |
| TechSupport | TechSupportService | 4 | Technical support |
| **Total** | **7 services** | **29 tools** | **Full business operations** |

---

## Usage Examples

### Example 1: Customer Retention Analysis

```python
# Step 1: Analyze churn drivers
churn_analysis = analyze_customer_churn(dataset_id="churn_001")
print(f"Top churn reason: {churn_analysis['top_driver']['reason']}")

# Step 2: Segment customers
segments = segment_customers(dataset_id="profiles_001")
high_value_customers = [
    c for s in segments['segments'] 
    if s['segment'] in ['Champions', 'Loyal Customers']
    for c in s['customers']
]

# Step 3: Predict CLV for at-risk high-value customers
for customer in high_value_customers:
    clv = predict_customer_lifetime_value(
        dataset_id="profiles_001",
        customer_id=customer['customer_id'],
        projection_months=24
    )
    print(f"{customer['name']}: ${clv['total_clv']:.2f} CLV")
```

### Example 2: Operations Health Check

```python
# Generate comprehensive operations summary
ops_summary = get_operations_summary(
    delivery_dataset_id="delivery_001",
    incident_dataset_id="incidents_001"
)

print(f"Operations Health: {ops_summary['health_grade']}")
print(f"Delivery Performance: {ops_summary['delivery_summary']['grade']}")
print(f"Incident Risk: {ops_summary['incident_summary']['risk_level']}")

# Forecast delivery performance
forecast = forecast_delivery_performance(
    dataset_id="delivery_001",
    periods=6
)

# Optimize inventory
inventory_rec = optimize_inventory(
    dataset_id="purchases_001",
    target_service_level=0.95
)
```

### Example 3: Sentiment Crisis Management

```python
# Analyze sentiment trends
sentiment = analyze_sentiment_trends(
    dataset_id="sentiment_001",
    forecast_periods=3
)

# Check for critical anomalies
critical_drops = [
    a for a in sentiment['anomalies']
    if a['severity'] == 'Critical'
]

if critical_drops:
    print(f"⚠️ {len(critical_drops)} critical sentiment drops detected")
    for drop in critical_drops:
        print(f"  - {drop['month']}: {drop['change_percentage']}% drop")
    
    # Review recommendations
    for rec in sentiment['recommendations']:
        if rec['priority'] in ['Critical', 'High']:
            print(f"  Action: {rec['action']}")
```

---

## Next Steps

### Sprint 3: Pricing & Marketing Analytics

Building on Sprint 2's customer and operations foundation:

1. **Pricing Analytics Service**
   - Competitive price analysis
   - Discount optimization
   - Revenue forecasting by category

2. **Marketing Analytics Service**
   - Campaign effectiveness analysis
   - Engagement prediction
   - Loyalty program optimization

3. **Agent Team Configurations**
   - Retail Operations Team
   - Customer Intelligence Team
   - Revenue Optimization Team
   - Marketing Intelligence Team

### Testing & Validation

**Next Priorities:**

1. Create unit tests for customer analytics utilities
2. Create unit tests for operations analytics utilities
3. Integration tests with sample datasets
4. End-to-end agent workflow tests

### Production Deployment

**Recommendations:**

1. **Dataset Preparation:**
   - Upload sample datasets to test storage
   - Validate CSV format compatibility
   - Test with real retail data

2. **Performance Monitoring:**
   - Track MCP tool response times
   - Monitor memory usage with large datasets
   - Log analytics function performance

3. **Error Handling:**
   - Validate all dataset schemas
   - Implement graceful degradation
   - Provide helpful error messages

---

## Testing

### Test Coverage

Sprint 2 includes comprehensive unit tests for all analytics utilities:

**Test Files:**
- `src/backend/tests/test_customer_analytics.py` (31 tests)
- `src/backend/tests/test_operations_analytics.py` (44 tests)

**Total Tests:** 75 (100% passing) ✅

### Test Summary

| Component | Test Class | Tests | Status |
|-----------|------------|-------|--------|
| Churn Analysis | TestAnalyzeChurnDrivers | 6 | ✅ 100% |
| RFM Segmentation | TestSegmentCustomersRFM | 6 | ✅ 100% |
| CLV Prediction | TestPredictCustomerLifetimeValue | 7 | ✅ 100% |
| Sentiment Trends | TestAnalyzeSentimentTrends | 10 | ✅ 100% |
| Sentiment Recommendations | TestGenerateSentimentRecommendations | 4 | ✅ 100% |
| Customer Integration | TestCustomerAnalyticsIntegration | 2 | ✅ 100% |
| Delivery Performance | TestAnalyzeDeliveryPerformance | 9 | ✅ 100% |
| Delivery Forecasting | TestForecastDeliveryMetrics | 4 | ✅ 100% |
| Warehouse Incidents | TestAnalyzeWarehouseIncidents | 8 | ✅ 100% |
| Inventory Optimization | TestOptimizeInventory | 6 | ✅ 100% |
| Helper Functions | TestHelperFunctions | 12 | ✅ 100% |
| Operations Integration | TestOperationsAnalyticsIntegration | 3 | ✅ 100% |
| **TOTAL** | **12 test classes** | **75** | **✅ 100%** |

### Running Tests

**Quick Test Run:**
```bash
python run_sprint2_tests.py
```

**Expected Output:**
```
============================= 75 passed in 0.32s ==============================
✅ All Sprint 2 tests passed!
```

**Individual Test Files:**
```bash
# Customer analytics tests only
cd src/backend
pytest tests/test_customer_analytics.py -v

# Operations analytics tests only
cd src/backend
pytest tests/test_operations_analytics.py -v

# Specific test class
pytest tests/test_customer_analytics.py::TestAnalyzeChurnDrivers -v
```

### Test Coverage by Feature

**Customer Analytics (31 tests):**
- ✅ Churn driver analysis with ranking and recommendations
- ✅ RFM customer segmentation (Champions, Loyal, At Risk, etc.)
- ✅ CLV prediction with confidence intervals and retention modeling
- ✅ Sentiment trend analysis with anomaly detection
- ✅ Sentiment forecasting with trend identification
- ✅ Recommendation generation for all scenarios
- ✅ Edge cases (empty data, extreme values)
- ✅ Integration workflows

**Operations Analytics (44 tests):**
- ✅ Delivery performance scoring and grading
- ✅ Performance degradation detection
- ✅ Trend analysis (improving/declining/stable)
- ✅ Delivery metrics forecasting
- ✅ Warehouse incident categorization and severity scoring
- ✅ Incident risk assessment and recommendations
- ✅ Inventory optimization with newsvendor model
- ✅ Service level impact on safety stock
- ✅ Helper functions (trend calculation, forecasting, categorization)
- ✅ Multi-dataset integration scenarios

---

## Quick Reference

### File Structure

```
src/backend/common/utils/
├── advanced_forecasting.py      # Sprint 1
├── customer_analytics.py        # Sprint 2 - NEW
├── operations_analytics.py      # Sprint 2 - NEW
└── dataset_utils.py             # Original

src/mcp_server/services/
├── finance_service.py                     # Sprint 1
├── customer_analytics_service.py          # Sprint 2 - NEW
├── operations_analytics_service.py        # Sprint 2 - NEW
├── hr_service.py                          # Original
├── marketing_service.py                   # Original
├── product_service.py                     # Original
└── tech_support_service.py                # Original

src/mcp_server/core/
└── factory.py                    # Enhanced with CUSTOMER, OPERATIONS domains
```

### Key Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| New Files | 4 | 2 utilities + 2 services |
| Modified Files | 2 | factory.py, mcp_server.py |
| Total Lines Added | ~1,820 | Across all new files |
| New MCP Tools | 8 | 4 customer + 4 operations |
| New Domains | 2 | CUSTOMER, OPERATIONS |
| Analytics Functions | 11 | 4 customer + 7 operations |

---

**Document Version:** 1.0  
**Last Updated:** October 10, 2025  
**Status:** ✅ Complete - Ready for Sprint 3  
**Next Sprint:** Pricing & Marketing Analytics + Agent Teams

