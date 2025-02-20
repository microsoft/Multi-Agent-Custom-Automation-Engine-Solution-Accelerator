import os
import sys
from unittest.mock import MagicMock
import pytest

# Mock Azure SDK dependencies
sys.modules["azure.monitor.events.extension"] = MagicMock()

# Set up environment variables
os.environ["COSMOSDB_ENDPOINT"] = "https://mock-endpoint"
os.environ["COSMOSDB_KEY"] = "mock-key"
os.environ["COSMOSDB_DATABASE"] = "mock-database"
os.environ["COSMOSDB_CONTAINER"] = "mock-container"
os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "mock-deployment-name"
os.environ["AZURE_OPENAI_API_VERSION"] = "2023-01-01"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock-openai-endpoint"


# Import the required functions for testing
from src.backend.agents.product import (
    add_mobile_extras_pack,
    get_product_info,
    update_inventory,
    schedule_product_launch,
    analyze_sales_data,
    get_customer_feedback,
    manage_promotions,
    check_inventory,
    update_product_price,
    provide_product_recommendations,
    handle_product_recall,
    set_product_discount,
    manage_supply_chain,
    forecast_product_demand,
    handle_product_complaints,
    monitor_market_trends,
    generate_product_report,
    develop_new_product_ideas,
    optimize_product_page,
    track_product_shipment,
    evaluate_product_performance,
)


# Parameterized tests for repetitive cases
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "function, args, expected_substrings",
    [
        (add_mobile_extras_pack, ("Roaming Pack", "2025-01-01"), ["Roaming Pack", "2025-01-01"]),
        (get_product_info, (), ["Simulated Phone Plans", "Plan A"]),
        (update_inventory, ("Product A", 50), ["Inventory for", "Product A"]),
        (schedule_product_launch, ("New Product", "2025-02-01"), ["New Product", "2025-02-01"]),
        (analyze_sales_data, ("Product B", "Last Quarter"), ["Sales data for", "Product B"]),
        (get_customer_feedback, ("Product C",), ["Customer feedback for", "Product C"]),
        (manage_promotions, ("Product A", "10% off for summer"), ["Promotion for", "Product A"]),
        (handle_product_recall, ("Product A", "Defective batch"), ["Product recall for", "Defective batch"]),
        (set_product_discount, ("Product A", 15.0), ["Discount for", "15.0%"]),
        (manage_supply_chain, ("Product A", "Supplier X"), ["Supply chain for", "Supplier X"]),
        (check_inventory, ("Product A",), ["Inventory status for", "Product A"]),
        (update_product_price, ("Product A", 99.99), ["Price for", "$99.99"]),
        (provide_product_recommendations, ("High Performance",), ["Product recommendations", "High Performance"]),
        (forecast_product_demand, ("Product A", "Next Month"), ["Demand for", "Next Month"]),
        (handle_product_complaints, ("Product A", "Complaint about quality"), ["Complaint for", "Product A"]),
        (generate_product_report, ("Product A", "Sales"), ["Sales report for", "Product A"]),
        (develop_new_product_ideas, ("Smartphone X with AI Camera",), ["New product idea", "Smartphone X"]),
        (optimize_product_page, ("Product A", "SEO optimization"), ["Product page for", "optimized"]),
        (track_product_shipment, ("Product A", "1234567890"), ["Shipment for", "1234567890"]),
        (evaluate_product_performance, ("Product A", "Customer reviews"), ["Performance of", "evaluated"]),
    ],
)
async def test_product_functions(function, args, expected_substrings):
    result = await function(*args)
    for substring in expected_substrings:
        assert substring in result


# Specific test for monitoring market trends
@pytest.mark.asyncio
async def test_monitor_market_trends():
    result = await monitor_market_trends()
    assert "Market trends monitored" in result
