# Scenario 2: Customer Churn Prevention

**Business Objective:** Identify at-risk customers and implement targeted retention strategies to reduce churn and maximize Customer Lifetime Value (CLV).

**Estimated Time:** 20-25 minutes  
**Difficulty:** Intermediate  
**Agent Team:** Customer Intelligence

---

## Overview

This scenario demonstrates how to analyze customer behavior patterns, identify churn drivers, segment customers by value, and generate data-driven retention strategies. You'll learn to prioritize retention efforts on high-value customers who are most likely to churn.

### What You'll Learn

- How to identify key churn indicators
- How to perform RFM (Recency, Frequency, Monetary) segmentation
- How to predict Customer Lifetime Value (CLV)
- How to analyze sentiment trends
- How to create targeted retention campaigns
- How to calculate retention ROI

---

## Datasets Required

| Dataset | Purpose | Rows | Key Columns |
|---------|---------|------|-------------|
| `customer_churn_analysis.csv` | Churn indicators and behavior | ~500 | `CustomerID`, `ChurnRisk`, `DaysSinceLastPurchase`, `EngagementScore` |
| `customer_profile.csv` | Customer demographics | ~500 | `CustomerID`, `JoinDate`, `Segment`, `TotalSpend` |
| `purchase_history.csv` | Transaction history | ~1,000 | `CustomerID`, `TransactionDate`, `TotalAmount` |
| `social_media_sentiment_analysis.csv` | Customer sentiment data | ~300 | `CustomerID`, `SentimentScore`, `Date` |

---

## Step-by-Step Walkthrough

### Step 1: Upload Customer Datasets

Upload all four datasets to the platform:

```
1. customer_churn_analysis.csv
2. customer_profile.csv
3. purchase_history.csv
4. social_media_sentiment_analysis.csv
```

**Verify:** All datasets appear in the dataset list with correct row counts.

---

### Step 2: Initialize Customer Intelligence Team

**Team:** `customer_intelligence`  
**Agents:**
- **Churn Prediction Agent**: Analyzes churn patterns and drivers
- **Sentiment Analyst Agent**: Monitors customer satisfaction trends

**Action:** Activate the Customer Intelligence team

---

### Step 3: Analyze Customer Churn Patterns

**MCP Tool:** `analyze_customer_churn`

**Parameters:**
```json
{
  "churn_dataset": "customer_churn_analysis.csv",
  "profile_dataset": "customer_profile.csv",
  "risk_threshold": 0.7
}
```

**Expected Output:**
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
      "recommendation": "Launch re-engagement campaign with personalized offers"
    },
    {
      "driver": "Days Since Last Purchase > 90",
      "affected_customers": 41,
      "impact_score": 8.2,
      "recommendation": "Send \"We miss you\" email with 20% discount code"
    },
    {
      "driver": "Declining Purchase Frequency",
      "affected_customers": 35,
      "impact_score": 7.5,
      "recommendation": "Offer subscription model or loyalty rewards"
    },
    {
      "driver": "Negative Sentiment Trend",
      "affected_customers": 28,
      "impact_score": 7.1,
      "recommendation": "Proactive customer service outreach"
    }
  ],
  "high_priority_customers": [
    {
      "customer_id": "C1023",
      "churn_risk": 0.92,
      "total_spend": 15420,
      "days_inactive": 67,
      "recommendation": "Immediate intervention - assign account manager"
    },
    {
      "customer_id": "C2341",
      "churn_risk": 0.88,
      "total_spend": 12890,
      "days_inactive": 52,
      "recommendation": "VIP re-engagement offer"
    }
    // ... more customers
  ]
}
```

**Key Insights:**
- 17.4% of customers are at high risk of churning
- Low engagement is the #1 driver (affects 52 customers)
- 87 customers require immediate retention efforts

---

### Step 4: Segment Customers (RFM Analysis)

**MCP Tool:** `segment_customers`

**Parameters:**
```json
{
  "purchase_dataset": "purchase_history.csv",
  "profile_dataset": "customer_profile.csv",
  "segmentation_method": "rfm"
}
```

**Expected Output:**
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
      "characteristics": "Recent, frequent, high-value buyers",
      "strategy": "Reward loyalty, ask for reviews, upsell premium products"
    },
    {
      "segment": "Loyal Customers",
      "customer_count": 95,
      "percentage": 19.0,
      "avg_recency_days": 22,
      "avg_frequency": 18,
      "avg_monetary": 5200,
      "characteristics": "Regular buyers with good frequency",
      "strategy": "Engage with exclusive offers, build community"
    },
    {
      "segment": "At Risk",
      "customer_count": 65,
      "percentage": 13.0,
      "avg_recency_days": 78,
      "avg_frequency": 12,
      "avg_monetary": 4100,
      "characteristics": "Used to be good customers, now inactive",
      "strategy": "Win-back campaigns, understand why they left"
    },
    {
      "segment": "Hibernating",
      "customer_count": 85,
      "percentage": 17.0,
      "avg_recency_days": 142,
      "avg_frequency": 4,
      "avg_monetary": 1850,
      "characteristics": "Long time since last purchase, low engagement",
      "strategy": "Reactivation campaign with deep discounts"
    },
    {
      "segment": "Lost",
      "customer_count": 45,
      "percentage": 9.0,
      "avg_recency_days": 210,
      "avg_frequency": 2,
      "avg_monetary": 950,
      "characteristics": "Minimal engagement, likely churned",
      "strategy": "Revive interest or remove from active marketing"
    }
    // ... other segments
  ],
  "segment_distribution_chart": "data:image/png;base64,..."
}
```

**Key Insights:**
- 15% are "Champions" - protect and grow these relationships
- 13% "At Risk" + 17% "Hibernating" = 30% need retention focus
- Different segments require different strategies

---

### Step 5: Predict Customer Lifetime Value (CLV)

**MCP Tool:** `predict_customer_lifetime_value`

**Parameters:**
```json
{
  "purchase_dataset": "purchase_history.csv",
  "profile_dataset": "customer_profile.csv",
  "forecast_months": 12,
  "discount_rate": 0.10
}
```

**Expected Output:**
```json
{
  "top_clv_customers": [
    {
      "customer_id": "C0456",
      "predicted_clv": 24500,
      "confidence_interval": [22100, 26900],
      "current_spend": 18200,
      "growth_potential": 34.6,
      "segment": "Champions",
      "retention_priority": "critical",
      "recommendation": "Assign dedicated account manager, offer premium tier"
    },
    {
      "customer_id": "C1234",
      "predicted_clv": 18750,
      "confidence_interval": [16200, 21300],
      "current_spend": 12400,
      "growth_potential": 51.2,
      "segment": "Loyal Customers",
      "retention_priority": "high",
      "recommendation": "Upsell to subscription model"
    }
    // ... top 50 customers
  ],
  "segment_clv_summary": [
    {
      "segment": "Champions",
      "avg_clv": 15800,
      "total_value": 1185000,
      "percentage_of_total": 42.5
    },
    {
      "segment": "Loyal Customers",
      "avg_clv": 8200,
      "total_value": 779000,
      "percentage_of_total": 27.9
    }
    // ... other segments
  ],
  "retention_roi_analysis": {
    "if_retain_at_risk_customers": {
      "customers": 65,
      "avg_clv": 4100,
      "total_potential_value": 266500,
      "retention_campaign_cost": 13000,
      "roi": 1950.0
    }
  }
}
```

**Key Insights:**
- Top 75 Champions represent 42.5% of total customer value
- Retaining "At Risk" customers has 1,950% ROI
- Invest retention budget in high-CLV, high-risk customers

---

### Step 6: Analyze Sentiment Trends

**MCP Tool:** `analyze_sentiment_trends`

**Parameters:**
```json
{
  "sentiment_dataset": "social_media_sentiment_analysis.csv",
  "forecast_periods": 3
}
```

**Expected Output:**
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
      "avg_sentiment": -45.2,
      "recommendation": "Improve shipping communication, offer compensation"
    },
    {
      "topic": "Product Quality Issues",
      "affected_customers": 12,
      "avg_sentiment": -38.7,
      "recommendation": "Quality control review, proactive replacements"
    }
  ],
  "at_risk_from_sentiment": [
    {
      "customer_id": "C2456",
      "sentiment_score": -62,
      "recent_feedback": "Disappointed with recent order quality",
      "clv": 8200,
      "recommendation": "Immediate customer service call, offer replacement + discount"
    }
  ]
}
```

**Key Insights:**
- Sentiment declining (72.4 → 70.1 projected)
- Shipping delays are primary complaint
- 37 customers with negative sentiment need proactive outreach

---

## Expected Outputs & Business Actions

### Retention Campaign Plan

| Segment | Customers | Strategy | Estimated Cost | Expected Retention | ROI |
|---------|-----------|----------|----------------|-------------------|-----|
| At Risk Champions | 15 | VIP phone calls + 30% discount | $3,000 | 80% (12 retained) | 3,200% |
| At Risk Loyal | 50 | Personalized email + 20% off | $5,000 | 60% (30 retained) | 1,480% |
| Hibernating | 85 | Generic reactivation email + 15% off | $2,500 | 25% (21 retained) | 345% |
| **Total** | **150** | **Multi-tiered approach** | **$10,500** | **63 customers** | **~2,000%** |

**Total Value Saved:** $258,300 (63 customers × $4,100 avg CLV)  
**Campaign Cost:** $10,500  
**Net Benefit:** $247,800  
**ROI:** 2,360%

### Recommended Actions (Next 30 Days)

**Week 1: High-Priority Interventions**
1. ✅ Assign account managers to top 15 at-risk Champions
2. ✅ Call customers with negative sentiment scores
3. ✅ Send VIP win-back offers to high-CLV at-risk customers

**Week 2: Targeted Email Campaigns**
4. ✅ "We miss you" campaign to At-Risk segment (65 customers)
5. ✅ Re-engagement offers to Hibernating segment (85 customers)
6. ✅ Loyalty rewards announcement to Champions (75 customers)

**Week 3: Product/Service Improvements**
7. ✅ Address shipping delay issues (implement faster shipping option)
8. ✅ Quality control review for reported product issues
9. ✅ Launch customer feedback survey

**Week 4: Monitoring & Optimization**
10. ✅ Track campaign response rates
11. ✅ Measure sentiment score changes
12. ✅ Calculate actual retention vs. forecast

---

## Business Impact

### Immediate Benefits (Month 1)
- **Customers Retained:** 63 (out of 150 at risk)
- **Revenue Saved:** $258,300 in CLV
- **Campaign ROI:** 2,360%

### 12-Month Projection
- **Churn Reduction:** From 17.4% to 10.2% (-7.2 percentage points)
- **Revenue Impact:** $500K+ in retained customer value
- **Customer Satisfaction:** Sentiment score increase from 72.4 to 78.5

### Long-Term Strategic Value
- Data-driven retention playbook
- Proactive churn prevention system
- Improved customer lifetime value management
- Enhanced brand loyalty and advocacy

---

## Troubleshooting

**Issue:** "No churn patterns detected"  
**Solution:** Ensure dataset has historical data (6+ months) and churn indicator columns

**Issue:** CLV predictions seem too high/low  
**Solution:** Adjust discount rate (0.05-0.15 typical range) or forecast period

**Issue:** RFM segments are unbalanced  
**Solution:** Normal - most businesses have few Champions and many occasional buyers

---

## Next Steps

- **[Scenario 3: Operations Optimization →](03_operations_optimization.md)**
- **[Jupyter Notebook](../notebooks/02_customer_segmentation.ipynb)** - Interactive analysis
- **[Customer Analytics Docs](../../docs/sprints/sprint2/CustomerOperations_Sprint2_Complete.md)**

---

**Scenario Completion Time:** ~25 minutes  
**Difficulty:** ⭐⭐⭐☆☆ (Intermediate)  
**Business Impact:** ⭐⭐⭐⭐⭐ (Very High - $250K+ value)



