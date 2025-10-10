"""
Customer Analytics Utilities

Provides functions for customer churn analysis, segmentation, CLV prediction,
and sentiment trend analysis for retail datasets.

Built for Sprint 2 - Customer & Operations Analytics
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import math

logger = logging.getLogger(__name__)


def analyze_churn_drivers(churn_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze customer churn drivers from churn analysis dataset.
    
    Args:
        churn_data: List of dicts with 'ReasonForCancellation' and 'Percentage'
        
    Returns:
        Dictionary with ranked drivers, recommendations, and risk assessment
    """
    try:
        if not churn_data:
            return {
                "error": "No churn data provided",
                "drivers": [],
                "recommendations": []
            }
        
        # Sort drivers by percentage (descending)
        sorted_drivers = sorted(
            churn_data,
            key=lambda x: float(x.get('Percentage', 0)),
            reverse=True
        )
        
        # Calculate total churn rate
        total_churn = sum(float(d.get('Percentage', 0)) for d in sorted_drivers)
        
        # Generate recommendations based on top drivers
        recommendations = []
        top_reason = sorted_drivers[0]['ReasonForCancellation']
        top_percentage = float(sorted_drivers[0]['Percentage'])
        
        if 'Service Dissatisfaction' in top_reason and top_percentage > 30:
            recommendations.append({
                "priority": "High",
                "action": "Improve service quality",
                "details": "40% of churn is service-related. Conduct customer satisfaction surveys, enhance support response times, and implement service quality monitoring."
            })
        
        if 'Competitor Offer' in top_reason:
            pct = float(sorted_drivers[1]['Percentage']) if len(sorted_drivers) > 1 else 0
            recommendations.append({
                "priority": "Medium" if pct < 20 else "High",
                "action": "Competitive pricing analysis",
                "details": f"{pct}% churn to competitors. Review pricing strategy, add unique value propositions, and consider loyalty incentives."
            })
        
        # Add retention strategies
        recommendations.append({
            "priority": "Medium",
            "action": "Proactive retention program",
            "details": "Implement early warning system to identify at-risk customers before cancellation requests."
        })
        
        return {
            "total_churn_rate": round(total_churn, 2),
            "drivers": [
                {
                    "reason": d['ReasonForCancellation'],
                    "percentage": float(d['Percentage']),
                    "rank": i + 1
                }
                for i, d in enumerate(sorted_drivers)
            ],
            "top_driver": {
                "reason": top_reason,
                "percentage": top_percentage,
                "impact": "Critical" if top_percentage > 35 else "High" if top_percentage > 20 else "Medium"
            },
            "recommendations": recommendations,
            "risk_level": "High" if total_churn > 80 else "Medium" if total_churn > 50 else "Low"
        }
        
    except Exception as e:
        logger.error(f"Error analyzing churn drivers: {e}")
        return {
            "error": str(e),
            "drivers": [],
            "recommendations": []
        }


def segment_customers_rfm(
    customers: List[Dict[str, Any]],
    reference_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Segment customers using RFM (Recency, Frequency, Monetary) analysis.
    
    Args:
        customers: List of customer dicts with MembershipDuration, TotalSpend
        reference_date: Reference date for recency calculation (default: now)
        
    Returns:
        Dictionary with customer segments and characteristics
    """
    try:
        if not customers:
            return {
                "error": "No customer data provided",
                "segments": []
            }
        
        if reference_date is None:
            reference_date = datetime.now()
        
        # Calculate RFM scores
        customers_with_scores = []
        for customer in customers:
            # Recency: membership duration (longer = less recent)
            duration_months = int(customer.get('MembershipDuration', 0))
            recency_score = 5 if duration_months < 6 else 4 if duration_months < 12 else 3 if duration_months < 24 else 2
            
            # Frequency: estimate from membership duration (more months = more purchases)
            frequency_score = 5 if duration_months >= 24 else 4 if duration_months >= 12 else 3 if duration_months >= 6 else 2
            
            # Monetary: total spend
            total_spend = float(customer.get('TotalSpend', 0))
            monetary_score = 5 if total_spend >= 5000 else 4 if total_spend >= 3000 else 3 if total_spend >= 1500 else 2 if total_spend >= 500 else 1
            
            # Calculate RFM combined score
            rfm_score = (recency_score + frequency_score + monetary_score) / 3
            
            # Assign segment
            if rfm_score >= 4.5:
                segment = "Champions"
            elif rfm_score >= 4.0:
                segment = "Loyal Customers"
            elif rfm_score >= 3.5:
                segment = "Potential Loyalists"
            elif rfm_score >= 3.0:
                segment = "At Risk"
            else:
                segment = "Needs Attention"
            
            customers_with_scores.append({
                "customer_id": customer.get('CustomerID', 'Unknown'),
                "name": customer.get('Name', 'Unknown'),
                "total_spend": total_spend,
                "membership_duration": duration_months,
                "rfm_score": round(rfm_score, 2),
                "segment": segment,
                "recency_score": recency_score,
                "frequency_score": frequency_score,
                "monetary_score": monetary_score
            })
        
        # Group by segment
        segments_summary = {}
        for customer in customers_with_scores:
            segment = customer['segment']
            if segment not in segments_summary:
                segments_summary[segment] = {
                    "segment": segment,
                    "count": 0,
                    "total_value": 0,
                    "avg_spend": 0,
                    "customers": []
                }
            segments_summary[segment]["count"] += 1
            segments_summary[segment]["total_value"] += customer['total_spend']
            segments_summary[segment]["customers"].append({
                "customer_id": customer['customer_id'],
                "name": customer['name'],
                "total_spend": customer['total_spend']
            })
        
        # Calculate averages
        for segment in segments_summary.values():
            if segment["count"] > 0:
                segment["avg_spend"] = round(segment["total_value"] / segment["count"], 2)
        
        # Add segment recommendations
        segment_strategies = {
            "Champions": "Reward and retain. Offer VIP benefits, early access to new products, exclusive events.",
            "Loyal Customers": "Upsell and increase engagement. Introduce premium tiers, personalized recommendations.",
            "Potential Loyalists": "Nurture with targeted campaigns. Offer incentives for increased purchases.",
            "At Risk": "Win back with special offers. Identify pain points, provide discounts, improve service.",
            "Needs Attention": "Re-engage aggressively. Send win-back campaigns, surveys to understand issues."
        }
        
        for segment in segments_summary.values():
            segment["strategy"] = segment_strategies.get(segment["segment"], "Monitor and engage")
        
        return {
            "total_customers": len(customers),
            "segments": list(segments_summary.values()),
            "customers_with_scores": customers_with_scores,
            "methodology": "RFM (Recency, Frequency, Monetary) Analysis"
        }
        
    except Exception as e:
        logger.error(f"Error in RFM segmentation: {e}")
        return {
            "error": str(e),
            "segments": []
        }


def predict_customer_lifetime_value(
    customer_data: Dict[str, Any],
    projection_months: int = 12
) -> Dict[str, Any]:
    """
    Predict customer lifetime value (CLV) based on historical spending.
    
    Args:
        customer_data: Customer dict with TotalSpend, AvgMonthlySpend, MembershipDuration
        projection_months: Number of months to project (default: 12)
        
    Returns:
        Dictionary with CLV projection and breakdown
    """
    try:
        total_spend = float(customer_data.get('TotalSpend', 0))
        avg_monthly_spend = float(customer_data.get('AvgMonthlySpend', 0))
        membership_duration = int(customer_data.get('MembershipDuration', 1))
        
        if membership_duration == 0:
            membership_duration = 1  # Avoid division by zero
        
        # Calculate historical monthly average (fallback if AvgMonthlySpend not provided)
        if avg_monthly_spend == 0 and total_spend > 0:
            avg_monthly_spend = total_spend / membership_duration
        
        # Estimate churn probability (simple heuristic)
        # Longer membership = lower churn risk
        churn_rate_annual = 0.15 if membership_duration >= 24 else 0.25 if membership_duration >= 12 else 0.35
        churn_rate_monthly = churn_rate_annual / 12
        
        # Calculate retention rate
        retention_rate = 1 - churn_rate_monthly
        
        # Project CLV using retention-adjusted spend
        projected_values = []
        cumulative_clv = total_spend  # Start with historical value
        
        for month in range(1, projection_months + 1):
            # Retention-adjusted value for this month
            month_probability = retention_rate ** month
            month_value = avg_monthly_spend * month_probability
            cumulative_clv += month_value
            
            projected_values.append({
                "month": month,
                "expected_spend": round(month_value, 2),
                "retention_probability": round(month_probability, 3),
                "cumulative_clv": round(cumulative_clv, 2)
            })
        
        # Calculate final metrics
        total_projected_value = sum(pv['expected_spend'] for pv in projected_values)
        final_clv = total_spend + total_projected_value
        
        # Confidence intervals (simple: ±20% based on spend variability)
        clv_lower = final_clv * 0.8
        clv_upper = final_clv * 1.2
        
        return {
            "customer_id": customer_data.get('CustomerID', 'Unknown'),
            "customer_name": customer_data.get('Name', 'Unknown'),
            "historical_value": round(total_spend, 2),
            "projected_value": round(total_projected_value, 2),
            "total_clv": round(final_clv, 2),
            "confidence_interval": {
                "lower": round(clv_lower, 2),
                "upper": round(clv_upper, 2),
                "confidence_level": 0.80
            },
            "projection_months": projection_months,
            "avg_monthly_spend": round(avg_monthly_spend, 2),
            "estimated_churn_rate": round(churn_rate_annual, 3),
            "retention_rate": round(retention_rate ** projection_months, 3),
            "monthly_breakdown": projected_values,
            "value_tier": "High Value" if final_clv >= 8000 else "Medium Value" if final_clv >= 4000 else "Standard"
        }
        
    except Exception as e:
        logger.error(f"Error predicting CLV: {e}")
        return {
            "error": str(e),
            "total_clv": 0
        }


def analyze_sentiment_trends(
    sentiment_data: List[Dict[str, Any]],
    forecast_periods: int = 3
) -> Dict[str, Any]:
    """
    Analyze sentiment trends and detect anomalies.
    
    Args:
        sentiment_data: List of dicts with Month, PositiveMentions, NegativeMentions, NeutralMentions
        forecast_periods: Number of periods to forecast
        
    Returns:
        Dictionary with sentiment analysis, trends, anomalies, and forecast
    """
    try:
        if not sentiment_data:
            return {
                "error": "No sentiment data provided",
                "trends": []
            }
        
        # Calculate net sentiment score for each period
        sentiment_scores = []
        for entry in sentiment_data:
            positive = int(entry.get('PositiveMentions', 0))
            negative = int(entry.get('NegativeMentions', 0))
            neutral = int(entry.get('NeutralMentions', 0))
            total = positive + negative + neutral
            
            if total == 0:
                net_sentiment = 0
            else:
                # Net sentiment: (positive - negative) / total
                net_sentiment = (positive - negative) / total
            
            sentiment_scores.append({
                "month": entry.get('Month', 'Unknown'),
                "positive": positive,
                "negative": negative,
                "neutral": neutral,
                "total_mentions": total,
                "net_sentiment": round(net_sentiment, 3),
                "positive_rate": round(positive / total, 3) if total > 0 else 0,
                "negative_rate": round(negative / total, 3) if total > 0 else 0
            })
        
        # Detect anomalies (sentiment drops > 20% from previous period)
        anomalies = []
        for i in range(1, len(sentiment_scores)):
            current = sentiment_scores[i]['net_sentiment']
            previous = sentiment_scores[i - 1]['net_sentiment']
            
            if previous != 0:
                change = (current - previous) / abs(previous)
                
                if change < -0.2:  # 20% drop
                    anomalies.append({
                        "month": sentiment_scores[i]['month'],
                        "net_sentiment": current,
                        "previous_sentiment": previous,
                        "change_percentage": round(change * 100, 1),
                        "severity": "Critical" if change < -0.4 else "High" if change < -0.3 else "Medium"
                    })
        
        # Simple trend forecast (linear extrapolation)
        if len(sentiment_scores) >= 2:
            # Calculate trend from last 3 periods (or all if less)
            recent_scores = sentiment_scores[-min(3, len(sentiment_scores)):]
            recent_values = [s['net_sentiment'] for s in recent_scores]
            
            # Simple linear trend
            n = len(recent_values)
            x_mean = (n - 1) / 2
            y_mean = sum(recent_values) / n
            
            numerator = sum((i - x_mean) * (recent_values[i] - y_mean) for i in range(n))
            denominator = sum((i - x_mean) ** 2 for i in range(n))
            
            if denominator != 0:
                slope = numerator / denominator
                intercept = y_mean - slope * x_mean
                
                forecast = []
                last_value = sentiment_scores[-1]['net_sentiment']
                
                for period in range(1, forecast_periods + 1):
                    forecast_value = intercept + slope * (n - 1 + period)
                    # Clamp to realistic bounds [-1, 1]
                    forecast_value = max(-1, min(1, forecast_value))
                    
                    forecast.append({
                        "period": period,
                        "forecasted_sentiment": round(forecast_value, 3),
                        "trend": "Improving" if slope > 0.02 else "Declining" if slope < -0.02 else "Stable"
                    })
            else:
                # Flat forecast if no trend
                last_value = sentiment_scores[-1]['net_sentiment']
                forecast = [
                    {
                        "period": i + 1,
                        "forecasted_sentiment": round(last_value, 3),
                        "trend": "Stable"
                    }
                    for i in range(forecast_periods)
                ]
        else:
            forecast = []
        
        # Overall assessment
        avg_sentiment = sum(s['net_sentiment'] for s in sentiment_scores) / len(sentiment_scores)
        current_sentiment = sentiment_scores[-1]['net_sentiment'] if sentiment_scores else 0
        
        assessment = "Positive" if current_sentiment > 0.3 else "Neutral" if current_sentiment > 0 else "Concerning" if current_sentiment > -0.2 else "Critical"
        
        return {
            "total_periods": len(sentiment_scores),
            "sentiment_scores": sentiment_scores,
            "current_sentiment": round(current_sentiment, 3),
            "average_sentiment": round(avg_sentiment, 3),
            "assessment": assessment,
            "anomalies": anomalies,
            "anomaly_count": len(anomalies),
            "forecast": forecast,
            "recommendations": generate_sentiment_recommendations(current_sentiment, anomalies, forecast)
        }
        
    except Exception as e:
        logger.error(f"Error analyzing sentiment trends: {e}")
        return {
            "error": str(e),
            "trends": []
        }


def generate_sentiment_recommendations(
    current_sentiment: float,
    anomalies: List[Dict],
    forecast: List[Dict]
) -> List[Dict[str, str]]:
    """Generate actionable recommendations based on sentiment analysis."""
    recommendations = []
    
    if current_sentiment < 0:
        recommendations.append({
            "priority": "High",
            "action": "Address negative sentiment urgently",
            "details": "Net sentiment is negative. Investigate root causes, improve customer service, and launch reputation recovery campaign."
        })
    
    if anomalies:
        critical_anomalies = [a for a in anomalies if a['severity'] == 'Critical']
        if critical_anomalies:
            recommendations.append({
                "priority": "Critical",
                "action": "Investigate sentiment drops",
                "details": f"Detected {len(critical_anomalies)} critical sentiment drops. Review customer feedback, identify issues, and implement corrective actions."
            })
    
    if forecast:
        declining_forecast = any(f['trend'] == 'Declining' for f in forecast)
        if declining_forecast:
            recommendations.append({
                "priority": "Medium",
                "action": "Proactive sentiment management",
                "details": "Forecast shows declining trend. Launch positive PR campaigns, improve product quality, and enhance customer experience."
            })
    
    if current_sentiment > 0.3 and not anomalies:
        recommendations.append({
            "priority": "Low",
            "action": "Maintain positive momentum",
            "details": "Sentiment is strong. Continue current strategies, leverage positive reviews in marketing, and reward loyal advocates."
        })
    
    return recommendations if recommendations else [
        {
            "priority": "Low",
            "action": "Monitor sentiment regularly",
            "details": "Continue tracking sentiment trends and respond promptly to changes."
        }
    ]

