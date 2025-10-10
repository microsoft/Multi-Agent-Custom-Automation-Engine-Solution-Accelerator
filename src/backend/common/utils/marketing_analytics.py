"""
Marketing Analytics Utilities

Provides functions for campaign effectiveness analysis, engagement prediction,
and loyalty program optimization for retail marketing strategy.

Built for Sprint 3 - Pricing & Marketing Analytics
"""

import logging
from typing import Dict, List, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


def analyze_campaign_effectiveness(
    campaign_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Analyze marketing campaign effectiveness based on engagement metrics.
    
    Args:
        campaign_data: List of dicts with Campaign, Opened, Clicked, Unsubscribed
        
    Returns:
        Dictionary with campaign performance metrics and recommendations
    """
    try:
        if not campaign_data:
            return {
                "error": "No campaign data provided",
                "campaigns": []
            }
        
        campaigns = []
        total_campaigns = len(campaign_data)
        total_opened = 0
        total_clicked = 0
        total_unsubscribed = 0
        
        for entry in campaign_data:
            campaign_name = entry.get('Campaign', 'Unknown Campaign')
            opened = entry.get('Opened', '').lower() == 'yes'
            clicked = entry.get('Clicked', '').lower() == 'yes'
            unsubscribed = entry.get('Unsubscribed', '').lower() == 'yes'
            
            # Track totals
            if opened:
                total_opened += 1
            if clicked:
                total_clicked += 1
            if unsubscribed:
                total_unsubscribed += 1
            
            # Calculate engagement score
            engagement_score = 0
            if opened:
                engagement_score += 40
            if clicked:
                engagement_score += 50
            if unsubscribed:
                engagement_score -= 100  # Negative impact
            
            # Determine performance tier
            if engagement_score >= 80:
                performance = "Excellent"
            elif engagement_score >= 40:
                performance = "Good"
            elif engagement_score >= 0:
                performance = "Fair"
            else:
                performance = "Poor"
            
            # Generate recommendation
            recommendation = generate_campaign_recommendation(
                campaign_name, opened, clicked, unsubscribed
            )
            
            campaigns.append({
                "campaign": campaign_name,
                "opened": opened,
                "clicked": clicked,
                "unsubscribed": unsubscribed,
                "engagement_score": engagement_score,
                "performance": performance,
                "recommendation": recommendation
            })
        
        # Calculate overall metrics
        open_rate = (total_opened / total_campaigns * 100) if total_campaigns > 0 else 0
        click_rate = (total_clicked / total_campaigns * 100) if total_campaigns > 0 else 0
        click_through_rate = (total_clicked / total_opened * 100) if total_opened > 0 else 0
        unsubscribe_rate = (total_unsubscribed / total_campaigns * 100) if total_campaigns > 0 else 0
        
        # Identify best and worst performers
        if campaigns:
            best_campaign = max(campaigns, key=lambda x: x['engagement_score'])
            worst_campaigns = [c for c in campaigns if not c['opened']]
            
            # Generate overall recommendations
            overall_recommendations = []
            
            if unsubscribe_rate > 0:
                overall_recommendations.append({
                    "priority": "Critical",
                    "finding": f"{unsubscribe_rate:.0f}% unsubscribe rate detected",
                    "action": "Review email frequency, content relevance, and segmentation strategy"
                })
            
            if worst_campaigns:
                overall_recommendations.append({
                    "priority": "High",
                    "finding": f"{len(worst_campaigns)} campaigns had 0% open rate",
                    "action": f"A/B test subject lines for: {', '.join(c['campaign'] for c in worst_campaigns[:2])}"
                })
            
            if open_rate < 50:
                overall_recommendations.append({
                    "priority": "High",
                    "finding": f"Overall open rate is {open_rate:.0f}%",
                    "action": "Improve subject line relevance, sender name recognition, and send timing"
                })
            
            if click_through_rate < 20 and total_opened > 0:
                overall_recommendations.append({
                    "priority": "Medium",
                    "finding": f"Click-through rate is only {click_through_rate:.0f}%",
                    "action": "Enhance email content, CTA clarity, and offer personalization"
                })
            
            # Best practices from top performer
            if best_campaign['engagement_score'] > 50:
                overall_recommendations.append({
                    "priority": "Low",
                    "finding": f"'{best_campaign['campaign']}' performed excellently",
                    "action": "Replicate successful elements (subject line style, offer type, timing) in future campaigns"
                })
            
            return {
                "total_campaigns": total_campaigns,
                "overall_metrics": {
                    "open_rate": round(open_rate, 1),
                    "click_rate": round(click_rate, 1),
                    "click_through_rate": round(click_through_rate, 1),
                    "unsubscribe_rate": round(unsubscribe_rate, 1)
                },
                "best_campaign": {
                    "name": best_campaign['campaign'],
                    "engagement_score": best_campaign['engagement_score'],
                    "performance": best_campaign['performance']
                },
                "campaigns": campaigns,
                "recommendations": overall_recommendations,
                "summary": f"Analyzed {total_campaigns} campaigns. Open rate: {open_rate:.0f}%, CTR: {click_through_rate:.0f}%"
            }
        else:
            return {
                "error": "No valid campaign data to analyze",
                "campaigns": []
            }
        
    except Exception as e:
        logger.error(f"Error analyzing campaign effectiveness: {e}")
        return {
            "error": str(e),
            "campaigns": []
        }


def generate_campaign_recommendation(
    campaign_name: str,
    opened: bool,
    clicked: bool,
    unsubscribed: bool
) -> str:
    """Generate specific recommendation for campaign based on performance."""
    
    if unsubscribed:
        return "CRITICAL: Recipient unsubscribed. Review content relevance, frequency, and targeting for this campaign type."
    
    elif not opened:
        return f"Not opened. Test alternative subject lines, sender names, or send times. Consider re-engagement campaign."
    
    elif opened and clicked:
        return "Excellent engagement! Analyze what worked (subject line, offer, content) and replicate in future campaigns."
    
    elif opened and not clicked:
        return "Opened but no click. Strengthen call-to-action, improve offer clarity, or enhance email design/content."
    
    else:
        return "Monitor performance. Consider additional engagement tactics."


def predict_engagement(
    customer_profile: Dict[str, Any],
    historical_campaigns: List[Dict[str, Any]],
    campaign_type: str
) -> Dict[str, Any]:
    """
    Predict customer engagement for a campaign type.
    
    Args:
        customer_profile: Customer data with purchase history, preferences
        historical_campaigns: Past campaign performance
        campaign_type: Type of campaign to predict (e.g., "sale", "new_arrivals")
        
    Returns:
        Dictionary with engagement predictions and optimal timing
    """
    try:
        # Calculate historical engagement rate
        if not historical_campaigns:
            base_open_prob = 0.5  # Default
            base_click_prob = 0.3
        else:
            opened_count = sum(1 for c in historical_campaigns if c.get('Opened', '').lower() == 'yes')
            clicked_count = sum(1 for c in historical_campaigns if c.get('Clicked', '').lower() == 'yes')
            
            base_open_prob = opened_count / len(historical_campaigns) if historical_campaigns else 0.5
            base_click_prob = clicked_count / len(historical_campaigns) if historical_campaigns else 0.3
        
        # Adjust based on customer profile
        # High spenders are more engaged
        total_spend = float(customer_profile.get('TotalSpend', 0))
        if total_spend > 5000:
            engagement_multiplier = 1.3
        elif total_spend > 2000:
            engagement_multiplier = 1.1
        else:
            engagement_multiplier = 0.9
        
        # Adjust based on campaign type
        campaign_multiplier = {
            "sale": 1.2,
            "exclusive_offers": 1.1,
            "new_arrivals": 1.0,
            "styling": 0.8
        }.get(campaign_type.lower().replace(" ", "_"), 1.0)
        
        # Calculate final probabilities
        open_probability = min(0.95, base_open_prob * engagement_multiplier * campaign_multiplier)
        click_probability = min(0.90, base_click_prob * engagement_multiplier * campaign_multiplier)
        
        # Determine optimal send time based on customer behavior
        membership_duration = int(customer_profile.get('MembershipDuration', 0))
        if membership_duration > 18:
            optimal_time = "Tuesday 10 AM"  # Established customers
            timing_confidence = "High"
        elif membership_duration > 6:
            optimal_time = "Wednesday 2 PM"  # Growing customers
            timing_confidence = "Medium"
        else:
            optimal_time = "Thursday 11 AM"  # New customers
            timing_confidence = "Low"
        
        # Generate recommendation
        if open_probability > 0.7:
            recommendation = f"High engagement expected. Prioritize this customer for {campaign_type} campaigns."
        elif open_probability > 0.4:
            recommendation = f"Moderate engagement expected. Include in {campaign_type} campaigns with personalized content."
        else:
            recommendation = f"Low engagement expected. Consider alternative campaign types or re-engagement sequence first."
        
        return {
            "customer_id": customer_profile.get('CustomerID', 'Unknown'),
            "customer_name": customer_profile.get('Name', 'Unknown'),
            "campaign_type": campaign_type,
            "open_probability": round(open_probability, 3),
            "click_probability": round(click_probability, 3),
            "engagement_level": "High" if open_probability > 0.6 else "Medium" if open_probability > 0.3 else "Low",
            "optimal_send_time": optimal_time,
            "timing_confidence": timing_confidence,
            "recommendation": recommendation
        }
        
    except Exception as e:
        logger.error(f"Error predicting engagement: {e}")
        return {
            "error": str(e),
            "open_probability": 0,
            "click_probability": 0
        }


def optimize_loyalty_program(
    loyalty_data: Dict[str, Any],
    benefits_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Optimize loyalty program based on points usage and benefits utilization.
    
    Args:
        loyalty_data: Dict with TotalPointsEarned, PointsRedeemed, CurrentPointBalance, PointsExpiringNextMonth
        benefits_data: List of dicts with Benefit, UsageFrequency
        
    Returns:
        Dictionary with loyalty program analysis and optimization recommendations
    """
    try:
        if not loyalty_data:
            return {
                "error": "No loyalty data provided",
                "recommendations": []
            }
        
        # Extract loyalty metrics
        total_earned = int(loyalty_data.get('TotalPointsEarned', 0))
        redeemed = int(loyalty_data.get('PointsRedeemed', 0))
        current_balance = int(loyalty_data.get('CurrentPointBalance', 0))
        expiring = int(loyalty_data.get('PointsExpiringNextMonth', 0))
        
        # Calculate metrics
        redemption_rate = (redeemed / total_earned * 100) if total_earned > 0 else 0
        points_at_risk = (expiring / current_balance * 100) if current_balance > 0 else 0
        
        # Analyze benefits utilization
        benefits_analysis = []
        total_usage = 0
        unused_benefits = []
        
        for benefit in benefits_data:
            benefit_name = benefit.get('Benefit', 'Unknown')
            usage = int(benefit.get('UsageFrequency', 0))
            total_usage += usage
            
            if usage == 0:
                unused_benefits.append(benefit_name)
                utilization = "Not Used"
                priority = "High"
            elif usage <= 2:
                utilization = "Low"
                priority = "Medium"
            else:
                utilization = "Good"
                priority = "Low"
            
            benefits_analysis.append({
                "benefit": benefit_name,
                "usage_frequency": usage,
                "utilization": utilization,
                "improvement_priority": priority
            })
        
        # Sort by usage (ascending) - least used first
        benefits_analysis.sort(key=lambda x: x['usage_frequency'])
        
        # Generate recommendations
        recommendations = []
        
        # Expiring points
        if expiring > 0 and points_at_risk >= 40:
            recommendations.append({
                "priority": "Critical",
                "category": "Points Expiration",
                "finding": f"{expiring} points ({points_at_risk:.0f}% of balance) expiring next month",
                "action": "Send urgent expiration reminder with curated redemption options",
                "expected_impact": f"Prevent loss of {expiring} points"
            })
        
        # Low redemption rate
        if redemption_rate < 50 and total_earned > 1000:
            recommendations.append({
                "priority": "High",
                "category": "Redemption Rate",
                "finding": f"Only {redemption_rate:.0f}% of earned points have been redeemed",
                "action": "Simplify redemption process, highlight point value, offer bonus redemption periods",
                "expected_impact": f"Increase engagement with {total_earned - redeemed} unredeemed points"
            })
        
        # Unused benefits
        if unused_benefits:
            recommendations.append({
                "priority": "High",
                "category": "Benefit Utilization",
                "finding": f"{len(unused_benefits)} benefits have 0% utilization: {', '.join(unused_benefits)}",
                "action": f"Investigate barriers, improve awareness, or replace with more valued benefits",
                "expected_impact": "Improve perceived program value"
            })
        
        # Specific benefit recommendations
        for benefit in benefits_analysis[:2]:  # Top 2 underutilized
            if benefit['utilization'] in ["Not Used", "Low"]:
                action = generate_benefit_improvement_action(benefit['benefit'], benefit['usage_frequency'])
                recommendations.append({
                    "priority": benefit['improvement_priority'],
                    "category": "Specific Benefit",
                    "finding": f"'{benefit['benefit']}' has {benefit['utilization'].lower()} utilization",
                    "action": action,
                    "expected_impact": "Increase benefit awareness and usage"
                })
        
        # High performer recognition
        top_benefit = benefits_analysis[-1] if benefits_analysis else None
        if top_benefit and top_benefit['usage_frequency'] > 5:
            recommendations.append({
                "priority": "Low",
                "category": "Success Pattern",
                "finding": f"'{top_benefit['benefit']}' is highly utilized ({top_benefit['usage_frequency']} times)",
                "action": "Promote similar benefits or expand this popular offering",
                "expected_impact": "Replicate successful engagement pattern"
            })
        
        return {
            "points_metrics": {
                "total_earned": total_earned,
                "points_redeemed": redeemed,
                "current_balance": current_balance,
                "redemption_rate": round(redemption_rate, 1),
                "points_expiring_soon": expiring,
                "expiration_risk": round(points_at_risk, 1)
            },
            "benefits_utilization": benefits_analysis,
            "unused_benefits_count": len(unused_benefits),
            "recommendations": recommendations,
            "program_health": "Good" if redemption_rate > 60 and len(unused_benefits) <= 1 else "Fair" if redemption_rate > 30 else "Needs Improvement",
            "summary": f"Redemption rate: {redemption_rate:.0f}%. {len(unused_benefits)} unused benefits. {expiring} points expiring soon."
        }
        
    except Exception as e:
        logger.error(f"Error optimizing loyalty program: {e}")
        return {
            "error": str(e),
            "recommendations": []
        }


def generate_benefit_improvement_action(benefit_name: str, usage: int) -> str:
    """Generate specific action to improve benefit utilization."""
    
    benefit_lower = benefit_name.lower()
    
    if "styling" in benefit_lower:
        return "Proactively offer styling session via email/SMS with easy booking link. Highlight how it enhances shopping experience."
    
    elif "early access" in benefit_lower:
        return "Send personalized preview emails with exclusive early access codes 48 hours before collections launch."
    
    elif "discount" in benefit_lower:
        return "Auto-apply exclusive discounts at checkout rather than requiring code entry. Send monthly discount usage summaries."
    
    elif "shipping" in benefit_lower:
        return "Prominently display free shipping badge throughout site. No further action needed if already highly used."
    
    else:
        if usage == 0:
            return f"Survey members about awareness and interest in '{benefit_name}'. Consider replacing if no interest."
        else:
            return f"Increase promotion frequency and clarify value proposition for '{benefit_name}'."

