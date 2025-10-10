# Multi-Agent Custom Automation Engine - User Guide

**Version:** 1.0  
**Last Updated:** October 10, 2025  
**Audience:** Business Users, Analysts, Managers

---

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Understanding the Dashboard](#understanding-the-dashboard)
4. [Working with Datasets](#working-with-datasets)
5. [Using Agent Teams](#using-agent-teams)
6. [Running Analytics](#running-analytics)
7. [Understanding Results](#understanding-results)
8. [Use Case Walkthroughs](#use-case-walkthroughs)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)
11. [Glossary](#glossary)
12. [Support & Resources](#support--resources)

---

## Introduction

### What is the Multi-Agent Custom Automation Engine?

The Multi-Agent Custom Automation Engine (MACAE) is an intelligent analytics platform that uses AI-powered agents to help you make data-driven business decisions. Whether you need to forecast revenue, identify at-risk customers, optimize operations, or improve pricing strategies, MACAE provides the tools and insights you need.

### Who Should Use This Guide?

This guide is designed for:
- **Business Analysts** - Running reports and analyzing trends
- **Department Managers** - Making data-driven decisions
- **Marketing Teams** - Optimizing campaigns and customer engagement
- **Operations Teams** - Improving efficiency and reducing costs
- **Finance Teams** - Forecasting and budget planning
- **Anyone** who needs actionable insights from business data

### What You Can Do with MACAE

✅ **Forecast Revenue** - Predict future sales with 95% confidence intervals  
✅ **Prevent Customer Churn** - Identify at-risk customers before they leave  
✅ **Optimize Operations** - Improve delivery times and reduce costs  
✅ **Analyze Pricing** - Understand competitive positioning and maximize revenue  
✅ **Evaluate Marketing** - Measure campaign ROI and optimize spend  
✅ **Segment Customers** - Identify high-value customer segments  

### No Technical Skills Required

You don't need to:
- Write code or SQL queries
- Understand complex statistics
- Be a data scientist
- Have technical training

**You just need:**
- Your business data (CSV or Excel files)
- A clear question or objective
- 15-30 minutes to run an analysis

---

## Getting Started

### Accessing the Platform

1. **Open your web browser** (Chrome, Edge, or Firefox recommended)
2. **Navigate to the platform URL**
   - Local development: `http://localhost:3001`
   - Production: Your organization's deployment URL
3. **Log in with your credentials**
   - Username: Your company email
   - Password: Provided by your administrator

### First Time Login

When you first log in, you'll see:
- **Home Page** - Quick access to agent teams and recent analyses
- **Navigation Menu** - Access to different sections (Datasets, Analytics, Teams)
- **Analytics Dashboard** - Real-time KPI metrics and visualizations

### Platform Overview

```
┌─────────────────────────────────────────────────────────┐
│  Multi-Agent Custom Automation Engine                   │
├─────────────────────────────────────────────────────────┤
│  Home  |  Analytics  |  Datasets  |  Teams  |  Help     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │  Revenue Forecast │  │  Customer Churn  │            │
│  │  $1.2M (+8.5%)   │  │  17.4% at risk   │            │
│  └──────────────────┘  └──────────────────┘            │
│                                                          │
│  ┌─────────────────────────────────────────┐            │
│  │       Forecast Visualization            │            │
│  │  [Chart showing actual vs. predicted]   │            │
│  └─────────────────────────────────────────┘            │
│                                                          │
│  Quick Actions:                                          │
│  [Upload Dataset] [Run Forecast] [View Reports]         │
└─────────────────────────────────────────────────────────┘
```

---

## Understanding the Dashboard

### Analytics Dashboard (`/analytics`)

The Analytics Dashboard is your mission control center, showing key metrics at a glance.

#### KPI Cards

**Revenue Forecast**
- Shows projected revenue for the next period
- Green/red arrow indicates trend (up/down)
- Click to see detailed forecast breakdown

**Customer Retention**
- Percentage of customers retained month-over-month
- Higher is better (target: 90%+)
- Links to churn analysis tools

**Average Order Value**
- Average amount customers spend per transaction
- Track over time to measure pricing/upsell effectiveness

**Forecast Accuracy**
- How accurate your forecasts have been historically
- Based on MAPE (Mean Absolute Percentage Error)
- Higher accuracy = more reliable predictions

#### Forecast Chart

Visual representation of:
- **Blue Line**: Historical actual data
- **Green Line**: Forecasted future values
- **Shaded Area**: Confidence interval (95% by default)
- **Reference Lines**: Trend indicators

**How to Read It:**
- If green line is above blue line → Growth projected
- Wider shaded area → More uncertainty in forecast
- Narrower shaded area → Higher confidence in prediction

#### Quick Actions

**Upload Dataset** - Add new data for analysis  
**Generate Forecast** - Create revenue/sales predictions  
**View Insights** - See AI-generated recommendations  
**Export Report** - Download results as PDF/Excel

---

## Working with Datasets

### What is a Dataset?

A dataset is a collection of business data (usually in CSV or Excel format) that the platform analyzes. Examples:
- Sales transactions
- Customer information
- Product catalog
- Marketing campaign results
- Delivery performance metrics

### Supported File Formats

✅ **CSV** (.csv) - Comma-separated values  
✅ **Excel** (.xlsx, .xls) - Microsoft Excel files  
✅ **JSON** (.json) - For advanced users  

**Maximum file size:** 50MB  
**Maximum rows:** 100,000 rows per file

### Uploading a Dataset

#### Method 1: Drag and Drop

1. Navigate to the **Datasets** section
2. Click **"Upload Dataset"** button
3. Drag your file from your computer into the upload area
4. Wait for the green checkmark (upload complete)
5. Your dataset appears in the list

#### Method 2: File Browser

1. Click **"Upload Dataset"** button
2. Click **"Browse Files"**
3. Select your file from your computer
4. Click **"Open"**
5. Wait for upload confirmation

### Dataset Requirements

For best results, your dataset should:

**Required:**
- Have column headers in the first row
- Use consistent date formats (YYYY-MM-DD or MM/DD/YYYY)
- Have numeric values for amounts (no currency symbols in data)
- Be free of completely blank rows

**Recommended:**
- At least 12 rows of data (more is better for forecasting)
- Clear, descriptive column names
- No special characters in column names (use underscores instead of spaces)
- Date columns named clearly (e.g., "TransactionDate", "OrderDate")

**Example - Good Dataset:**
```csv
TransactionDate,CustomerID,ProductName,Quantity,TotalAmount
2024-01-15,C1001,Blue Dress,1,89.99
2024-01-15,C1002,Red Shoes,2,149.98
2024-01-16,C1003,Handbag,1,199.99
```

**Example - Needs Improvement:**
```csv
Date,Cust,Item,Qty,$$$
1/15/24,1001,Item1,1,"$89.99"    ← Currency symbol in data
,1002,Item2,2,$149.98            ← Blank date cell
```

### Previewing a Dataset

After uploading, click on the dataset name to see:
- **First 10 rows** - Sample of your data
- **Column types** - Detected data types (text, number, date)
- **Row count** - Total number of records
- **File size** - Storage used

**Verify:**
- Column headers are correct
- Data types are detected properly
- No unexpected values or errors

### Managing Datasets

**Download** - Export dataset back to your computer  
**Delete** - Remove dataset (cannot be undone)  
**Refresh** - Re-upload updated version  

**Note:** Deleting a dataset does NOT delete analyses you've already run - those are saved separately.

---

## Using Agent Teams

### What are Agent Teams?

Agent Teams are groups of specialized AI agents that work together to analyze your data. Each team has expertise in a specific business area.

Think of it like having a team of expert consultants available 24/7:
- They never get tired
- They analyze data consistently
- They provide insights in seconds
- They're always improving

### Available Agent Teams

#### 1. Finance Forecasting Team

**Use this team when you need to:**
- Forecast future revenue or sales
- Predict budget requirements
- Identify financial trends
- Compare different forecasting methods

**Agents:**
- **Financial Analyst Agent** - Analyzes trends and patterns
- **Forecasting Specialist Agent** - Generates predictions

**Example Questions:**
- "What will our revenue be next quarter?"
- "Which forecasting method is most accurate for our data?"
- "How confident can we be in these predictions?"

**Required Data:** Historical sales/revenue with dates

---

#### 2. Customer Intelligence Team

**Use this team when you need to:**
- Identify customers at risk of churning
- Segment customers by value
- Predict customer lifetime value
- Understand customer sentiment

**Agents:**
- **Churn Prediction Agent** - Identifies at-risk customers
- **Sentiment Analyst Agent** - Monitors satisfaction trends

**Example Questions:**
- "Which customers are most likely to leave?"
- "What are my most valuable customer segments?"
- "Why are customers churning?"
- "Is customer sentiment improving or declining?"

**Required Data:** Customer profiles, purchase history, engagement metrics

---

#### 3. Retail Operations Team

**Use this team when you need to:**
- Improve delivery performance
- Optimize inventory levels
- Reduce warehouse incidents
- Identify cost-saving opportunities

**Agents:**
- **Operations Strategist Agent** - Finds improvement opportunities
- **Supply Chain Analyst Agent** - Optimizes logistics and inventory

**Example Questions:**
- "How can we improve on-time delivery rates?"
- "Are we holding too much inventory?"
- "What's causing warehouse incidents?"
- "Where can we cut operational costs?"

**Required Data:** Delivery metrics, inventory data, incident reports

---

#### 4. Revenue Optimization Team

**Use this team when you need to:**
- Analyze competitive pricing
- Optimize discount strategies
- Forecast revenue by category
- Maximize profit margins

**Agents:**
- **Pricing Strategist Agent** - Optimizes pricing decisions
- **Revenue Forecaster Agent** - Predicts revenue impact

**Example Questions:**
- "Are we priced competitively?"
- "Should we increase or decrease prices?"
- "Are our discounts profitable?"
- "Which products have the most revenue potential?"

**Required Data:** Pricing data, competitor prices, sales history

---

#### 5. Marketing Intelligence Team

**Use this team when you need to:**
- Measure campaign effectiveness
- Predict customer engagement
- Optimize loyalty programs
- Calculate marketing ROI

**Agents:**
- **Campaign Analyst Agent** - Evaluates marketing performance
- **Loyalty Optimization Agent** - Improves retention programs

**Example Questions:**
- "Which marketing campaigns are most effective?"
- "What's the ROI of our email campaigns?"
- "How can we improve our loyalty program?"
- "Which customers are most likely to engage?"

**Required Data:** Campaign performance, loyalty program data, customer engagement

---

### Activating an Agent Team

1. **Navigate to Teams** section
2. **Select the appropriate team** for your analysis goal
3. **Click "Activate Team"** or "Initialize"
4. **Wait for confirmation** (team status shows "Active")
5. **Team is ready** to analyze your data

You can have multiple teams active simultaneously.

---

## Running Analytics

### Step-by-Step: Running Your First Analysis

Let's walk through a complete example: **Forecasting Revenue**

#### Step 1: Prepare Your Data

✅ Gather your sales/revenue data  
✅ Export to CSV or Excel  
✅ Ensure it has columns for: Date and Amount  
✅ Have at least 12 months of historical data

#### Step 2: Upload Dataset

1. Go to **Datasets** → **Upload Dataset**
2. Select your `sales_history.csv` file
3. Wait for upload confirmation
4. Click on dataset name to preview

#### Step 3: Activate Finance Team

1. Go to **Teams** → **Finance Forecasting**
2. Click **"Activate Team"**
3. Team status changes to "Active" ✅

#### Step 4: Configure Analysis

1. Navigate to **Analytics** → **Forecasting**
2. Select your uploaded dataset
3. Configure parameters:
   - **Target Column:** `Revenue` (or your amount column)
   - **Date Column:** `Date` (or your date column)
   - **Forecast Method:** `Auto-Select` (recommended)
   - **Forecast Periods:** `12` (months ahead)
   - **Confidence Level:** `95%`

#### Step 5: Run Analysis

1. Click **"Generate Forecast"**
2. Wait 10-30 seconds for processing
3. Results appear automatically

#### Step 6: Review Results

You'll see:
- **Forecast table** with predicted values
- **Chart visualization** with confidence intervals
- **Model accuracy metrics** (MAE, RMSE, MAPE)
- **AI-generated insights** and recommendations

#### Step 7: Take Action

Based on results:
- Export forecast to Excel
- Share insights with stakeholders
- Adjust business plans
- Schedule follow-up analyses

---

### Understanding Forecasting Methods

The platform offers multiple forecasting methods. Here's when to use each:

#### Auto-Select (Recommended for Beginners)

**What it does:** Tests all methods and picks the most accurate  
**When to use:** When you're not sure which method is best  
**Pros:** Always gives you the best result  
**Cons:** Takes slightly longer to compute

#### Linear Regression

**What it does:** Fits a straight line through your data  
**When to use:** Stable, consistent trends without seasonality  
**Best for:** Simple revenue growth, headcount planning  
**Example:** Steady 5% monthly growth

#### SARIMA (Seasonal Auto-Regressive Integrated Moving Average)

**What it does:** Captures trends AND seasonal patterns  
**When to use:** Data with repeating patterns (holidays, seasons)  
**Best for:** Retail sales, tourism, seasonal businesses  
**Example:** Holiday sales spike every December

#### Prophet (Facebook's Algorithm)

**What it does:** Handles multiple seasonal patterns and outliers  
**When to use:** Complex data with holidays and special events  
**Best for:** E-commerce, subscriptions, web traffic  
**Example:** Sales affected by Black Friday, Valentine's Day, etc.

#### Exponential Smoothing

**What it does:** Weights recent data more heavily  
**When to use:** Short-term forecasts where recent trends matter most  
**Best for:** Inventory planning, short-term budgets  
**Example:** Next month's staffing needs

**Quick Decision Guide:**
- **Simple steady growth?** → Linear Regression
- **Seasonal patterns (Christmas rush, summer slowdown)?** → SARIMA
- **Complex with holidays/events?** → Prophet
- **Not sure?** → Auto-Select

---

## Understanding Results

### Reading Forecast Results

#### Forecast Table

| Month | Forecast | Lower Bound (95%) | Upper Bound (95%) |
|-------|----------|-------------------|-------------------|
| Jan 2025 | $120,000 | $115,000 | $125,000 |

**How to interpret:**
- **Forecast:** Most likely outcome
- **Lower Bound:** Worst-case scenario (95% confident it won't go below this)
- **Upper Bound:** Best-case scenario (95% confident it won't exceed this)

**Example interpretation:**
"We expect $120K in revenue for January. We're 95% confident it will be between $115K and $125K."

#### Accuracy Metrics

**MAE (Mean Absolute Error)**
- Average forecast error in actual dollars
- Example: MAE of $2,500 means forecasts are off by $2,500 on average
- **Lower is better**

**RMSE (Root Mean Squared Error)**
- Similar to MAE but penalizes large errors more heavily
- Use to identify if you have occasional big misses
- **Lower is better**

**MAPE (Mean Absolute Percentage Error)**
- Error as a percentage of actual values
- Example: MAPE of 2.5% means forecasts are 2.5% off on average
- **Lower is better** - Under 5% is excellent, under 10% is good

**What's a "good" MAPE?**
- **< 5%** - Excellent accuracy (trust these forecasts)
- **5-10%** - Good accuracy (useful for planning)
- **10-20%** - Fair accuracy (use as rough guide)
- **> 20%** - Poor accuracy (investigate data quality)

#### Confidence Intervals

**What does "95% confidence interval" mean?**

If you run 100 forecasts, 95 of them will fall within the predicted range.

**Wide interval vs. Narrow interval:**
- **Narrow (tight range):** High confidence, stable data
- **Wide (large range):** More uncertainty, volatile data

**Example:**
- Narrow: $100K-$105K (very predictable)
- Wide: $80K-$130K (high variability - plan conservatively)

---

### AI-Generated Insights

The platform provides plain-English insights such as:

✅ **"Strong upward trend detected with 8.5% projected growth"**
→ Revenue is increasing consistently

✅ **"Seasonal peak identified in Q4 (Nov-Dec)"**
→ Plan for increased demand in those months

✅ **"SARIMA method recommended due to seasonality"**
→ Platform auto-selected the best forecasting method

✅ **"Forecast accuracy: 98.2% (excellent)"**
→ High confidence in these predictions

⚠️ **"Limited historical data - confidence may be reduced"**
→ Upload more historical data for better results

---

## Use Case Walkthroughs

The platform includes four detailed scenario guides with step-by-step instructions:

### 1. [Retail Revenue Forecasting](../examples/scenarios/01_retail_revenue_forecasting.md)

**Time:** 15-20 minutes  
**What you'll learn:**
- Upload sales data
- Generate forecasts with multiple methods
- Compare model accuracy
- Create 12-month revenue projections

**Business value:** $80K-$120K in improved planning

---

### 2. [Customer Churn Prevention](../examples/scenarios/02_customer_churn_prevention.md)

**Time:** 20-25 minutes  
**What you'll learn:**
- Identify at-risk customers
- Segment customers by value (RFM)
- Predict customer lifetime value
- Create retention strategies

**Business value:** $258K in saved customer value

---

### 3. [Operations Optimization](../examples/scenarios/03_operations_optimization.md)

**Time:** 20-25 minutes  
**What you'll learn:**
- Forecast delivery performance
- Optimize inventory levels
- Analyze warehouse incidents
- Identify cost savings

**Business value:** $253K in annual savings

---

### 4. [Pricing & Marketing ROI](../examples/scenarios/04_pricing_marketing_roi.md)

**Time:** 25-30 minutes  
**What you'll learn:**
- Analyze competitive pricing
- Optimize discount strategies
- Measure campaign effectiveness
- Improve loyalty programs

**Business value:** $652K in revenue increase

---

## Best Practices

### Data Quality Tips

✅ **Clean your data first**
- Remove duplicate rows
- Fill in missing critical values
- Fix obvious errors (negative prices, future dates)

✅ **Use consistent formats**
- Dates: YYYY-MM-DD or MM/DD/YYYY (pick one)
- Numbers: No commas or currency symbols in data cells
- Text: Consistent capitalization

✅ **Include enough history**
- Forecasting: 12-24 months minimum
- Churn analysis: 6-12 months minimum
- Trend analysis: At least 3 months

✅ **Update regularly**
- Re-upload data monthly or quarterly
- Keep forecasts current
- Track accuracy over time

### Analysis Tips

✅ **Start simple**
- Begin with one dataset and one question
- Master basic forecasts before advanced analytics
- Build confidence gradually

✅ **Compare methods**
- Use "Auto-Select" initially
- Review which method performed best
- Use that method for similar data going forward

✅ **Validate results**
- Do the forecasts "make sense" based on your business knowledge?
- Compare to your gut feel or manual estimates
- Share with colleagues for sanity checks

✅ **Document your process**
- Note which datasets you used
- Record parameter settings
- Save insights and decisions made

### Interpretation Tips

✅ **Context matters**
- External factors affect forecasts (economy, competition, seasonality)
- Forecasts are predictions, not guarantees
- Use confidence intervals for planning buffers

✅ **Trust the data, but verify**
- If results seem wrong, check data quality first
- Outliers can skew forecasts
- Sometimes business changes make historical data less relevant

✅ **Act on insights**
- Forecasts are only valuable if you use them
- Share results with stakeholders
- Adjust plans based on predictions
- Measure actual vs. forecast regularly

---

## Troubleshooting

### Common Issues and Solutions

#### "Upload failed" or "File too large"

**Cause:** File exceeds 50MB or has > 100K rows  
**Solution:**
- Split large files into smaller chunks
- Aggregate data (daily → monthly)
- Remove unnecessary columns
- Contact admin to increase limits

#### "No forecast generated" or "Insufficient data"

**Cause:** Less than 12 data points  
**Solution:**
- Upload more historical data
- Use shorter forecast period
- Try Linear method (requires fewer data points)

#### "Low accuracy" or "MAPE > 20%"

**Cause:** Volatile data or poor data quality  
**Solution:**
- Check for data entry errors
- Remove outliers
- Try Prophet method (handles outliers better)
- Consider external factors not in your data

#### Forecast looks flat (no trend)

**Cause:** Data lacks clear trend  
**Solution:**
- Normal for stable businesses
- Check if dates are sorted correctly
- Verify you selected the right columns
- Try different forecast methods

#### Results take too long (> 60 seconds)

**Cause:** Large dataset or complex method (SARIMA)  
**Solution:**
- Use monthly aggregation instead of daily
- Reduce forecast periods (12 → 6)
- Try Exponential Smoothing (faster)
- Be patient - SARIMA is thorough but slow

#### Can't find uploaded dataset

**Cause:** Filter or search issue  
**Solution:**
- Clear any search filters
- Refresh the page
- Check if upload actually completed
- Try re-uploading

#### Charts not displaying

**Cause:** Browser compatibility or slow connection  
**Solution:**
- Use Chrome, Edge, or Firefox
- Refresh page
- Clear browser cache
- Check internet connection

---

## Glossary

**Agent Team** - Group of AI agents specialized in a business domain (Finance, Marketing, etc.)

**Confidence Interval** - Range where actual values are likely to fall (e.g., 95% CI = 95% confidence)

**Churn** - When a customer stops doing business with you

**CLV (Customer Lifetime Value)** - Total revenue expected from a customer over their entire relationship

**Dataset** - Collection of business data uploaded for analysis

**Forecast** - Prediction of future values based on historical patterns

**KPI (Key Performance Indicator)** - Measurable metric that shows business performance

**MAE (Mean Absolute Error)** - Average forecast error in actual units (dollars, units, etc.)

**MAPE (Mean Absolute Percentage Error)** - Forecast accuracy as a percentage

**RFM (Recency, Frequency, Monetary)** - Customer segmentation method based on purchase behavior

**RMSE (Root Mean Squared Error)** - Forecast error metric that penalizes large errors

**ROI (Return on Investment)** - Profit generated per dollar invested

**SARIMA** - Statistical forecasting method that captures seasonal patterns

**Seasonality** - Repeating patterns in data (monthly, quarterly, yearly)

**Trend** - Long-term direction of data (upward, downward, or flat)

---

## Support & Resources

### Getting Help

**Documentation**
- This User Guide (you're reading it!)
- [Developer Guide](DEVELOPER_GUIDE.md) - For technical users
- [API Reference](API_REFERENCE.md) - For integrations
- [Scenario Guides](../examples/scenarios/) - Step-by-step walkthroughs

**Interactive Learning**
- [Jupyter Notebooks](../examples/notebooks/) - Hands-on Python examples
- [Video Tutorials](#) - Coming soon

**Support Channels**
- **Help Desk:** support@yourcompany.com
- **Slack Channel:** #macae-support
- **Office Hours:** Tuesdays 2-4 PM (virtual)

### Additional Resources

**Sprint Documentation**
- [Sprint 1: Advanced Forecasting](./sprints/sprint1/FinanceForecasting_Sprint1_Complete.md)
- [Sprint 2: Customer & Operations Analytics](./sprints/sprint2/CustomerOperations_Sprint2_Complete.md)
- [Sprint 3: Pricing & Marketing Analytics](./sprints/sprint3/PricingMarketing_Sprint3_Complete.md)
- [Sprint 4: Frontend & Visualization](./sprints/sprint4/Frontend_Sprint4_Implementation_Guide.md)

**Technical Documentation**
- [Deployment Guide](DeploymentGuide.md)
- [Testing Guide](../TESTING.md)
- [Production Deployment](PRODUCTION_DEPLOYMENT.md)

### Feedback

We're constantly improving! Share your feedback:
- **Feature Requests:** Submit via Help Desk
- **Bug Reports:** Email with screenshots
- **Success Stories:** We'd love to hear how MACAE helped your business!

---

**Document Version:** 1.0  
**Last Updated:** October 10, 2025  
**Next Review:** January 2026

---

**Ready to get started?** Begin with [Scenario 1: Retail Revenue Forecasting](../examples/scenarios/01_retail_revenue_forecasting.md) for a hands-on walkthrough!

