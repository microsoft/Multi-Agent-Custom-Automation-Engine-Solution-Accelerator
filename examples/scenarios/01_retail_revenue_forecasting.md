# Scenario 1: Retail Revenue Forecasting

**Business Objective:** Predict future revenue to optimize inventory planning, staffing decisions, and budget projections.

**Estimated Time:** 15-20 minutes  
**Difficulty:** Beginner  
**Agent Team:** Finance Forecasting

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Datasets Required](#datasets-required)
4. [Step-by-Step Walkthrough](#step-by-step-walkthrough)
5. [Expected Outputs](#expected-outputs)
6. [Business Impact](#business-impact)
7. [Troubleshooting](#troubleshooting)
8. [Next Steps](#next-steps)

---

## Overview

This scenario demonstrates how to generate accurate revenue forecasts using multiple advanced forecasting methods. The platform automatically evaluates different algorithms (SARIMA, Prophet, Exponential Smoothing, Linear Regression) and selects the best-performing model based on historical data.

### What You'll Learn

- How to upload and prepare sales data for forecasting
- How to generate forecasts using multiple methods
- How to interpret confidence intervals
- How to evaluate model accuracy (MAE, RMSE, MAPE)
- How to select the best forecasting method for your data
- How to action forecast insights

---

## Prerequisites

### System Requirements
- Access to the Multi-Agent Custom Automation Engine platform
- Backend server running (see [Deployment Guide](../../docs/DeploymentGuide.md))
- Frontend accessible at `http://localhost:3001` (or your deployed URL)

### Knowledge Prerequisites
- Basic understanding of time series data
- Familiarity with uploading CSV files
- No advanced statistical knowledge required

---

## Datasets Required

This scenario uses the following sample datasets (located in `data/datasets/`):

| Dataset | Purpose | Rows | Key Columns |
|---------|---------|------|-------------|
| `purchase_history.csv` | Historical sales transactions | ~1,000 | `CustomerID`, `TransactionDate`, `TotalAmount`, `ItemsPurchased` |
| `product_table.csv` | Product catalog (optional) | ~50 | `ProductID`, `ProductName`, `Category`, `Price` |

### Data Requirements

**`purchase_history.csv`** must contain:
- **Date column**: Transaction dates (YYYY-MM-DD format)
- **Revenue column**: Numeric values representing sales amounts
- **Minimum history**: At least 12 data points (preferably 24+ for seasonality detection)

---

## Step-by-Step Walkthrough

### Step 1: Upload Purchase History Dataset

1. **Navigate to the application**
   - Open your browser to `http://localhost:3001` (or your deployed URL)
   - Log in with your credentials

2. **Access the Dataset Panel**
   - Look for the "Forecast Dataset Panel" on the left side
   - Or navigate to the dataset management section

3. **Upload the dataset**
   ```
   Click "Upload Dataset" button
   → Select file: data/datasets/purchase_history.csv
   → Wait for upload confirmation
   → Dataset appears in the list
   ```

4. **Verify dataset preview**
   - Click on the uploaded dataset name
   - Confirm you see columns: `TransactionDate`, `TotalAmount`
   - Check data quality (no missing values in key columns)

**Expected Result:** ✅ Dataset "purchase_history.csv" visible in dataset list

---

### Step 2: Initialize Finance Forecasting Team

1. **Access Agent Teams**
   - Navigate to "Teams" or "Agent Configuration"
   - Look for available agent teams

2. **Select Finance Forecasting Team**
   - Team name: `finance_forecasting`
   - Agents included:
     - **Financial Analyst Agent**: Data analysis and trend identification
     - **Forecasting Specialist Agent**: Advanced forecasting execution

3. **Initialize the team**
   ```
   Click "Initialize Team" or "Activate"
   → Wait for confirmation
   → Team status shows "Active"
   ```

**Expected Result:** ✅ Finance Forecasting team is active and ready

---

### Step 3: Generate Revenue Forecast (Simple Linear)

Let's start with a basic linear forecast to understand the trend.

1. **Open the forecasting interface**
   - Navigate to "Forecasting" or "Analytics"
   - Select the uploaded `purchase_history.csv` dataset

2. **Configure forecast parameters**
   ```
   Dataset: purchase_history.csv
   Target Column: TotalAmount
   Date Column: TransactionDate
   Method: Linear (with Confidence Intervals)
   Forecast Periods: 6 (months ahead)
   Confidence Level: 95%
   ```

3. **Execute forecast**
   - Click "Generate Forecast" or use the MCP tool directly
   - Wait for processing (5-10 seconds)

**Expected Output:**
```json
{
  "method": "linear",
  "forecast_periods": 6,
  "forecast_values": [120000, 122000, 124000, 126000, 128000, 130000],
  "lower_bound": [115000, 116000, 117000, 118000, 119000, 120000],
  "upper_bound": [125000, 128000, 131000, 134000, 137000, 140000],
  "confidence_level": 0.95,
  "trend": "upward",
  "summary": "Linear forecast indicates steady growth of ~$2,000/month"
}
```

**Chart Visualization:**
- Blue line: Historical actual revenue
- Green line: Forecasted revenue
- Shaded area: 95% confidence interval

---

### Step 4: Generate Advanced Forecasts (SARIMA)

Now let's use SARIMA to capture seasonality in the data.

1. **Change forecast method**
   ```
   Method: SARIMA (Seasonal Auto-Regressive Integrated Moving Average)
   All other parameters: Same as Step 3
   ```

2. **Execute SARIMA forecast**
   - Click "Generate Forecast"
   - Wait for processing (15-20 seconds - SARIMA is more compute-intensive)

**Expected Output:**
```json
{
  "method": "sarima",
  "model_order": "(1,1,1)x(1,1,1,12)",
  "seasonality_detected": true,
  "seasonal_period": 12,
  "forecast_periods": 6,
  "forecast_values": [118000, 125000, 121000, 127000, 123000, 129000],
  "lower_bound": [113000, 119000, 115000, 120000, 116000, 121000],
  "upper_bound": [123000, 131000, 127000, 134000, 130000, 137000],
  "confidence_level": 0.95,
  "summary": "SARIMA detected monthly seasonality with peak in Q4"
}
```

**Key Insight:** Notice the forecast values fluctuate - this captures seasonal patterns!

---

### Step 5: Generate Prophet Forecast

Prophet is excellent for data with strong trends and multiple seasonalities.

1. **Change forecast method**
   ```
   Method: Prophet (Facebook's forecasting algorithm)
   All other parameters: Same as above
   ```

2. **Execute Prophet forecast**
   - Click "Generate Forecast"
   - Wait for processing (10-15 seconds)

**Expected Output:**
```json
{
  "method": "prophet",
  "forecast_periods": 6,
  "forecast_values": [119500, 124000, 120500, 128000, 122000, 130500],
  "lower_bound": [112000, 116000, 113000, 119000, 114000, 121000],
  "upper_bound": [127000, 132000, 128000, 137000, 130000, 140000],
  "confidence_level": 0.95,
  "trend_components": {
    "overall_trend": "increasing",
    "weekly_seasonality": false,
    "yearly_seasonality": true
  },
  "summary": "Prophet identified yearly seasonality with Q4 peak"
}
```

---

### Step 6: Compare and Select Best Model

Use the model evaluation tool to compare all methods.

1. **Call the "Evaluate Forecast Models" MCP tool**
   ```
   Dataset: purchase_history.csv
   Target Column: TotalAmount
   Date Column: TransactionDate
   Methods to Compare: ["linear", "sarima", "prophet", "exponential_smoothing"]
   Test Split: 0.2 (use last 20% of data for validation)
   ```

2. **Review model comparison results**

**Expected Output:**
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
      "recommendation": "Strong alternative with good trend capture"
    },
    {
      "method": "exponential_smoothing",
      "mae": 2890.12,
      "rmse": 3542.90,
      "mape": 2.45,
      "rank": 3,
      "recommendation": "Good for short-term forecasts"
    },
    {
      "method": "linear",
      "mae": 3450.78,
      "rmse": 4123.45,
      "mape": 2.91,
      "rank": 4,
      "recommendation": "Baseline - use for simple trends only"
    }
  ],
  "best_method": "sarima",
  "confidence": "high",
  "reasoning": "SARIMA captures both trend and seasonality with lowest MAPE of 1.82%"
}
```

**Key Metrics Explained:**
- **MAE (Mean Absolute Error)**: Average forecast error in dollars - lower is better
- **RMSE (Root Mean Squared Error)**: Penalizes large errors more - lower is better
- **MAPE (Mean Absolute Percentage Error)**: Error as a percentage - lower is better
- **Rank**: Overall ranking (1 = best)

**Decision:** ✅ Use **SARIMA** for final forecast (lowest MAPE: 1.82%)

---

### Step 7: Generate Final Production Forecast

1. **Use the best method (SARIMA) for your official forecast**
   ```
   Method: SARIMA
   Forecast Periods: 12 (next 12 months for budget planning)
   Confidence Level: 95%
   ```

2. **Export forecast results**
   - Download forecast data as CSV
   - Save chart visualization as PNG
   - Document key insights

---

## Expected Outputs

### 1. Forecast Data Table

| Month | Historical (Actual) | Forecast | Lower Bound (95%) | Upper Bound (95%) |
|-------|---------------------|----------|-------------------|-------------------|
| Jan 2025 | - | $118,000 | $113,000 | $123,000 |
| Feb 2025 | - | $125,000 | $119,000 | $131,000 |
| Mar 2025 | - | $121,000 | $115,000 | $127,000 |
| Apr 2025 | - | $127,000 | $120,000 | $134,000 |
| May 2025 | - | $123,000 | $116,000 | $130,000 |
| Jun 2025 | - | $129,000 | $121,000 | $137,000 |
| Jul 2025 | - | $126,000 | $117,000 | $135,000 |
| Aug 2025 | - | $132,000 | $122,000 | $142,000 |
| Sep 2025 | - | $128,000 | $117,000 | $139,000 |
| Oct 2025 | - | $140,000 | $128,000 | $152,000 |
| Nov 2025 | - | $145,000 | $132,000 | $158,000 |
| Dec 2025 | - | $150,000 | $136,000 | $164,000 |

**Total Projected Revenue (12 months):** $1,564,000  
**Confidence Range:** $1,426,000 - $1,702,000

### 2. Key Insights

✅ **Trend:** Steady upward trajectory with ~8.5% YoY growth  
✅ **Seasonality:** Strong Q4 peak (Nov-Dec), Q1 dip (Jan-Mar)  
✅ **Forecast Accuracy:** MAPE of 1.82% indicates high reliability  
✅ **Confidence:** 95% CI provides reasonable planning buffer

### 3. Visual Dashboard

The Analytics Dashboard (`/analytics`) displays:
- KPI Card: "Revenue Forecast: $1.56M (+8.5%)"
- Forecast Chart: Historical + predicted with confidence bands
- Model Comparison: SARIMA ranked #1

---

## Business Impact

### Immediate Actions

1. **Inventory Planning**
   - **Q4 Preparation:** Increase inventory by 20% for Nov-Dec peak
   - **Q1 Adjustment:** Reduce orders by 10% to avoid overstock in Jan-Mar
   - **Estimated Savings:** $50K-$80K in carrying costs

2. **Staffing Optimization**
   - **Hiring Plan:** Add 5 seasonal staff in Q4 (Oct-Dec)
   - **Schedule Optimization:** Reduce hours in Q1 by 15%
   - **Estimated Savings:** $30K-$40K in labor costs

3. **Budget Allocation**
   - **Marketing Budget:** Allocate 30% more in Q3 to drive Q4 sales
   - **Cash Flow Management:** Reserve $150K for Q4 inventory purchases
   - **Capital Projects:** Schedule major expenses in Q1 (lower revenue period)

### Long-Term Benefits

- **Improved Cash Flow:** 15-20% better cash flow management
- **Reduced Waste:** 12-18% reduction in inventory obsolescence
- **Customer Satisfaction:** 95%+ product availability during peak season
- **Financial Planning:** Accurate budget projections for board/investors

### ROI Calculation

**Investment:** 2 hours of analyst time (~$150)  
**Annual Benefit:** $80K-$120K in cost savings + improved planning  
**ROI:** 53,333% - 80,000%  
**Payback Period:** Immediate (first forecast)

---

## Troubleshooting

### Issue 1: "Insufficient data points" error

**Cause:** Dataset has fewer than 12 historical records  
**Solution:**
- Use at least 12 data points for basic forecasting
- Use 24+ data points for seasonality detection (SARIMA, Prophet)
- If limited data, stick with Linear or Exponential Smoothing methods

### Issue 2: Forecast shows flat line (no trend)

**Cause:** Data lacks clear trend or has too much noise  
**Solution:**
- Check data quality (outliers, missing values)
- Try Prophet method (more robust to noise)
- Consider aggregating data (daily → weekly → monthly)

### Issue 3: Confidence intervals are very wide

**Cause:** High variability in historical data  
**Solution:**
- Normal for volatile business data
- Use median forecast for planning
- Focus on trend direction rather than exact values
- Consider adding external factors (marketing spend, seasonality)

### Issue 4: SARIMA takes too long (>60 seconds)

**Cause:** Large dataset or complex seasonality  
**Solution:**
- Use aggregated data (monthly instead of daily)
- Reduce forecast periods (12 → 6)
- Try Exponential Smoothing as faster alternative

### Issue 5: Models disagree significantly

**Cause:** Complex patterns in data  
**Solution:**
- Check for data quality issues
- Review MAPE scores - trust the lowest
- Consider ensemble averaging of top 2-3 models
- Consult domain expert for validation

---

## Next Steps

### Expand Your Forecasting

1. **Try Other Datasets**
   - Product-level forecasting
   - Regional revenue forecasts
   - Customer segment forecasts

2. **Advanced Techniques**
   - Add external variables (marketing spend, holidays)
   - Forecast by product category
   - Build ensemble models

3. **Automate Workflows**
   - Schedule monthly forecast regeneration
   - Set up alerts for forecast vs. actual variance
   - Create automated reports for stakeholders

### Related Scenarios

- **[Scenario 2: Customer Churn Prevention](02_customer_churn_prevention.md)** - Identify at-risk customers
- **[Scenario 3: Operations Optimization](03_operations_optimization.md)** - Improve delivery & inventory
- **[Scenario 4: Pricing & Marketing ROI](04_pricing_marketing_roi.md)** - Optimize pricing & campaigns

### Additional Resources

- **[User Guide](../../docs/USER_GUIDE.md)** - Complete platform documentation
- **[API Reference](../../docs/API_REFERENCE.md)** - MCP tools documentation
- **[Jupyter Notebook](../notebooks/01_revenue_forecasting.ipynb)** - Interactive Python version
- **[Advanced Forecasting Docs](../../docs/sprints/sprint1/FinanceForecasting_Sprint1_Complete.md)** - Technical details

---

## Summary

✅ **What We Accomplished:**
- Uploaded sales data to the platform
- Generated forecasts using 4 different methods
- Compared models and selected the best (SARIMA)
- Created actionable 12-month revenue forecast
- Identified $80K-$120K in cost savings opportunities

✅ **Key Learnings:**
- SARIMA is best for seasonal data with clear patterns
- Prophet is robust for noisy data with strong trends
- Linear regression works for simple, stable trends
- Model evaluation (MAPE) helps select the best method
- Confidence intervals provide planning flexibility

✅ **Business Value:**
- Accurate revenue projections for budgeting
- Optimized inventory and staffing decisions
- Improved cash flow management
- ROI: 53,000%+

---

**Scenario Completion Time:** ~20 minutes  
**Difficulty:** ⭐⭐☆☆☆ (Beginner)  
**Business Impact:** ⭐⭐⭐⭐⭐ (Very High)

**Ready for the next scenario?** Continue to [Customer Churn Prevention →](02_customer_churn_prevention.md)

