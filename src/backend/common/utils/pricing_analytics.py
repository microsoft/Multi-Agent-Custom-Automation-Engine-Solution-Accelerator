"""
Pricing Analytics Utilities

Provides functions for competitive price analysis, discount optimization,
and revenue forecasting by category for retail pricing strategy.

Built for Sprint 3 - Pricing & Marketing Analytics
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import math

logger = logging.getLogger(__name__)


def analyze_competitive_pricing(
    pricing_data: List[Dict[str, Any]],
    product_data: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Analyze competitive pricing gaps and provide pricing recommendations.
    
    Args:
        pricing_data: List of dicts with ProductCategory, ContosoAveragePrice, CompetitorAveragePrice
        product_data: Optional list with ReturnRate data
        
    Returns:
        Dictionary with price gaps, recommendations, and competitive positioning
    """
    try:
        if not pricing_data:
            return {
                "error": "No pricing data provided",
                "analysis": []
            }
        
        # Merge product data if provided
        return_rates = {}
        if product_data:
            for product in product_data:
                category = product.get('ProductCategory', '')
                return_rate = product.get('ReturnRate', 0)
                if return_rate:
                    try:
                        return_rates[category] = float(return_rate)
                    except (ValueError, TypeError):
                        pass
        
        analysis = []
        total_gap = 0
        overpriced_count = 0
        underpriced_count = 0
        
        for entry in pricing_data:
            category = entry.get('ProductCategory', 'Unknown')
            
            try:
                our_price = float(entry.get('ContosoAveragePrice', 0))
                comp_price = float(entry.get('CompetitorAveragePrice', 0))
            except (ValueError, TypeError):
                continue
            
            if our_price == 0 or comp_price == 0:
                continue
            
            # Calculate price gap
            price_gap = our_price - comp_price
            price_gap_percent = (price_gap / comp_price) * 100
            
            # Determine positioning
            if price_gap_percent > 10:
                positioning = "Overpriced"
                overpriced_count += 1
            elif price_gap_percent > 0:
                positioning = "Premium"
            elif price_gap_percent > -10:
                positioning = "Competitive"
            else:
                positioning = "Underpriced"
                underpriced_count += 1
            
            total_gap += abs(price_gap_percent)
            
            # Get return rate if available
            return_rate = return_rates.get(category, None)
            
            # Generate recommendation
            recommendation = generate_pricing_recommendation(
                category, price_gap_percent, return_rate, our_price, comp_price
            )
            
            # Calculate suggested price
            if price_gap_percent > 15:
                # Significantly overpriced - reduce to be competitive
                suggested_price = comp_price * 1.05  # 5% premium
            elif price_gap_percent < -10:
                # Underpriced - can increase
                suggested_price = comp_price * 0.95  # 5% discount
            else:
                # Already competitive
                suggested_price = our_price
            
            # Estimate revenue impact
            if price_gap_percent > 10:
                # Overpriced -> reduce price should increase volume
                volume_change = price_gap_percent * -0.5  # Price elasticity assumption
                revenue_impact = (suggested_price / our_price - 1) * 100 + volume_change
            elif price_gap_percent < -5:
                # Underpriced -> increase price
                volume_change = (suggested_price / our_price - 1) * -0.3
                revenue_impact = (suggested_price / our_price - 1) * 100 + volume_change
            else:
                revenue_impact = 0
            
            analysis.append({
                "category": category,
                "our_price": round(our_price, 2),
                "competitor_price": round(comp_price, 2),
                "price_gap": round(price_gap, 2),
                "price_gap_percent": round(price_gap_percent, 1),
                "positioning": positioning,
                "return_rate": return_rate,
                "suggested_price": round(suggested_price, 2),
                "potential_revenue_impact": round(revenue_impact, 1),
                "recommendation": recommendation
            })
        
        # Sort by price gap (descending) - most overpriced first
        analysis.sort(key=lambda x: x['price_gap_percent'], reverse=True)
        
        # Calculate summary
        avg_price_gap = total_gap / len(analysis) if analysis else 0
        
        # Overall strategy
        if overpriced_count > underpriced_count:
            strategy = "Price Reduction Focus"
            strategy_detail = f"{overpriced_count} categories are overpriced. Consider selective price reductions to improve competitiveness."
        elif underpriced_count > overpriced_count:
            strategy = "Price Increase Opportunity"
            strategy_detail = f"{underpriced_count} categories are underpriced. Consider strategic price increases to improve margins."
        else:
            strategy = "Maintain Current Strategy"
            strategy_detail = "Pricing is generally competitive across categories."
        
        return {
            "total_categories": len(analysis),
            "avg_price_gap_percent": round(avg_price_gap, 1),
            "overpriced_categories": overpriced_count,
            "underpriced_categories": underpriced_count,
            "competitive_categories": len(analysis) - overpriced_count - underpriced_count,
            "overall_strategy": strategy,
            "strategy_detail": strategy_detail,
            "category_analysis": analysis,
            "top_priority_actions": get_top_pricing_actions(analysis)
        }
        
    except Exception as e:
        logger.error(f"Error analyzing competitive pricing: {e}")
        return {
            "error": str(e),
            "analysis": []
        }


def generate_pricing_recommendation(
    category: str,
    price_gap_percent: float,
    return_rate: Optional[float],
    our_price: float,
    comp_price: float
) -> str:
    """Generate specific pricing recommendation based on gap and return rate."""
    
    if price_gap_percent > 20:
        return f"URGENT: Reduce price by ~{abs(price_gap_percent - 5):.0f}% to regain competitiveness. Currently {price_gap_percent:.0f}% above market."
    
    elif price_gap_percent > 10:
        rec = f"Consider reducing price to ${comp_price * 1.05:.2f} (5% premium) to improve competitiveness"
        if return_rate and return_rate > 12:
            rec += f". High return rate ({return_rate}%) suggests quality/fit issues may compound price resistance."
        return rec
    
    elif price_gap_percent > 5:
        return f"Maintain current premium positioning. Monitor closely for competitive changes."
    
    elif price_gap_percent > -5:
        return f"Pricing is competitive. Focus on value differentiation and customer experience."
    
    elif price_gap_percent > -15:
        return f"Opportunity to increase price to ${comp_price * 0.95:.2f} while maintaining competitive discount."
    
    else:
        return f"Significantly underpriced. Consider {abs(price_gap_percent) / 2:.0f}% price increase to improve margins."


def get_top_pricing_actions(analysis: List[Dict[str, Any]], limit: int = 3) -> List[Dict[str, str]]:
    """Get top priority pricing actions."""
    actions = []
    
    # Most overpriced categories
    overpriced = [a for a in analysis if a['price_gap_percent'] > 10]
    for item in overpriced[:min(2, len(overpriced))]:
        actions.append({
            "priority": "High",
            "category": item['category'],
            "action": f"Reduce price from ${item['our_price']} to ${item['suggested_price']}",
            "expected_impact": f"+{abs(item['potential_revenue_impact']):.1f}% revenue potential"
        })
    
    # High return rate + overpriced
    high_return = [a for a in analysis if a.get('return_rate') is not None and a.get('return_rate') > 12 and a['price_gap_percent'] > 5]
    if high_return:
        item = high_return[0]
        actions.append({
            "priority": "Critical",
            "category": item['category'],
            "action": "Address quality issues AND reduce price",
            "expected_impact": f"Reduce {item['return_rate']:.0f}% return rate"
        })
    
    return actions[:limit]


def optimize_discount_strategy(
    purchase_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Optimize discount strategy based on historical purchase patterns.
    
    Args:
        purchase_data: List of dicts with TotalAmount, DiscountApplied
        
    Returns:
        Dictionary with discount effectiveness analysis and recommendations
    """
    try:
        if not purchase_data:
            return {
                "error": "No purchase data provided",
                "recommendations": []
            }
        
        # Categorize purchases by discount level
        discount_buckets = {
            "No Discount (0%)": [],
            "Small (1-10%)": [],
            "Medium (11-20%)": [],
            "Large (21%+)": []
        }
        
        for purchase in purchase_data:
            try:
                amount = float(purchase.get('TotalAmount', 0))
                discount = float(purchase.get('DiscountApplied', 0))
            except (ValueError, TypeError):
                continue
            
            if amount == 0:
                continue
            
            discount_percent = (discount / (amount + discount)) * 100 if (amount + discount) > 0 else 0
            
            if discount_percent == 0:
                discount_buckets["No Discount (0%)"].append(amount)
            elif discount_percent <= 10:
                discount_buckets["Small (1-10%)"].append(amount)
            elif discount_percent <= 20:
                discount_buckets["Medium (11-20%)"].append(amount)
            else:
                discount_buckets["Large (21%+)"].append(amount)
        
        # Calculate metrics for each bucket
        bucket_analysis = []
        for bucket_name, amounts in discount_buckets.items():
            if amounts:
                avg_order_value = sum(amounts) / len(amounts)
                total_revenue = sum(amounts)
                order_count = len(amounts)
                
                bucket_analysis.append({
                    "discount_level": bucket_name,
                    "order_count": order_count,
                    "avg_order_value": round(avg_order_value, 2),
                    "total_revenue": round(total_revenue, 2),
                    "revenue_share": 0  # Will calculate after
                })
        
        # Calculate revenue share
        total_revenue = sum(b['total_revenue'] for b in bucket_analysis)
        for bucket in bucket_analysis:
            bucket['revenue_share'] = round((bucket['total_revenue'] / total_revenue * 100), 1) if total_revenue > 0 else 0
        
        # Calculate optimal discount level
        # Find bucket with highest revenue per order
        if bucket_analysis:
            best_bucket = max(bucket_analysis, key=lambda x: x['avg_order_value'])
            
            # Generate recommendations
            recommendations = []
            
            # Check if no-discount performs well
            no_discount = next((b for b in bucket_analysis if "No Discount" in b['discount_level']), None)
            if no_discount and no_discount['order_count'] > 0:
                recommendations.append({
                    "priority": "Medium",
                    "finding": f"{no_discount['order_count']} orders had no discount with avg value ${no_discount['avg_order_value']:.2f}",
                    "recommendation": "Strong baseline demand exists. Reserve discounts for strategic conversion opportunities."
                })
            
            # Check for over-discounting
            large_discount = next((b for b in bucket_analysis if "Large" in b['discount_level']), None)
            if large_discount and large_discount['revenue_share'] < 20 and large_discount['order_count'] > 0:
                recommendations.append({
                    "priority": "High",
                    "finding": f"Large discounts (21%+) only drove {large_discount['revenue_share']:.1f}% of revenue",
                    "recommendation": f"Reduce reliance on deep discounts. Cap discounts at 15-20% to protect margins."
                })
            
            # Optimal recommendation
            optimal_range = best_bucket['discount_level']
            recommendations.append({
                "priority": "High",
                "finding": f"'{optimal_range}' discount range has highest ROI",
                "recommendation": f"Focus promotions in this range - avg order value: ${best_bucket['avg_order_value']:.2f}"
            })
            
            # Calculate discount efficiency
            discounted_orders = sum(b['order_count'] for b in bucket_analysis if "No Discount" not in b['discount_level'])
            total_orders = sum(b['order_count'] for b in bucket_analysis)
            discount_penetration = (discounted_orders / total_orders * 100) if total_orders > 0 else 0
            
            return {
                "total_orders": total_orders,
                "orders_with_discount": discounted_orders,
                "discount_penetration": round(discount_penetration, 1),
                "optimal_discount_range": optimal_range,
                "bucket_analysis": bucket_analysis,
                "recommendations": recommendations,
                "summary": f"Analyzed {total_orders} orders across {len(bucket_analysis)} discount tiers. {optimal_range} shows best performance."
            }
        else:
            return {
                "error": "No valid purchase data to analyze",
                "recommendations": []
            }
        
    except Exception as e:
        logger.error(f"Error optimizing discount strategy: {e}")
        return {
            "error": str(e),
            "recommendations": []
        }


def forecast_revenue_by_category(
    purchase_data: List[Dict[str, Any]],
    periods: int = 6
) -> Dict[str, Any]:
    """
    Forecast revenue by product category.
    
    Args:
        purchase_data: List of purchase records with ItemsPurchased, TotalAmount
        periods: Number of periods to forecast
        
    Returns:
        Dictionary with category-level revenue forecasts
    """
    try:
        if not purchase_data:
            return {
                "error": "No purchase data provided",
                "forecasts": []
            }
        
        # Extract category revenue (simplified - assumes categories in ItemsPurchased)
        category_revenue = defaultdict(list)
        
        for purchase in purchase_data:
            items = purchase.get('ItemsPurchased', '')
            try:
                amount = float(purchase.get('TotalAmount', 0))
            except (ValueError, TypeError):
                continue
            
            # Parse categories from items (simplified)
            items_list = [item.strip() for item in items.split(',') if item.strip()]
            
            # Distribute revenue across items equally
            if items_list and amount > 0:
                revenue_per_item = amount / len(items_list)
                
                for item in items_list:
                    # Categorize items (simplified heuristics)
                    category = categorize_item(item)
                    category_revenue[category].append(revenue_per_item)
        
        # Generate forecasts for each category
        forecasts = []
        total_historical_revenue = 0
        
        for category, revenues in category_revenue.items():
            if not revenues:
                continue
            
            # Calculate historical metrics
            total_revenue = sum(revenues)
            avg_revenue = total_revenue / len(revenues)
            total_historical_revenue += total_revenue
            
            # Simple growth projection (assume 5% growth for demo)
            growth_rate = 0.05
            
            # Generate forecast
            forecast_values = []
            for period in range(1, periods + 1):
                forecast_value = avg_revenue * (1 + growth_rate) ** period
                forecast_values.append(round(forecast_value, 2))
            
            # Confidence intervals (±15%)
            lower_bound = [round(v * 0.85, 2) for v in forecast_values]
            upper_bound = [round(v * 1.15, 2) for v in forecast_values]
            
            forecasts.append({
                "category": category,
                "historical_orders": len(revenues),
                "historical_total_revenue": round(total_revenue, 2),
                "historical_avg_revenue_per_order": round(avg_revenue, 2),
                "forecast_periods": periods,
                "forecast": forecast_values,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "projected_growth_rate": growth_rate
            })
        
        # Sort by historical revenue (descending)
        forecasts.sort(key=lambda x: x['historical_total_revenue'], reverse=True)
        
        return {
            "total_categories": len(forecasts),
            "total_historical_revenue": round(total_historical_revenue, 2),
            "forecast_periods": periods,
            "category_forecasts": forecasts,
            "methodology": "Simple growth projection with 5% assumed growth rate",
            "confidence_level": 0.85
        }
        
    except Exception as e:
        logger.error(f"Error forecasting revenue by category: {e}")
        return {
            "error": str(e),
            "forecasts": []
        }


def categorize_item(item: str) -> str:
    """Categorize an item based on keywords."""
    item_lower = item.lower()
    
    if any(word in item_lower for word in ['dress', 'gown']):
        return "Dresses"
    elif any(word in item_lower for word in ['shoe', 'boot', 'sneaker']):
        return "Shoes"
    elif any(word in item_lower for word in ['jacket', 'coat', 'outerwear']):
        return "Outerwear"
    elif any(word in item_lower for word in ['legging', 'sportswear', 'fitness', 'sports', 'athletic']):
        return "Sportswear"
    elif any(word in item_lower for word in ['bag', 'clutch', 'scarf', 'hat', 'accessory', 'accessories']):
        return "Accessories"
    else:
        return "Other"

