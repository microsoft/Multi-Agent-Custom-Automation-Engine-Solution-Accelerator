import os
import sys
from unittest.mock import MagicMock

sys.modules["azure.monitor.events"] = MagicMock()
sys.modules["azure.monitor.events.extension"] = MagicMock()


import pytest


# Adjust sys.path so that the project root is found.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Set required environment variables before importing modules that depend on them.
os.environ["COSMOSDB_ENDPOINT"] = "https://mock-endpoint"
os.environ["COSMOSDB_KEY"] = "mock-key"
os.environ["COSMOSDB_DATABASE"] = "mock-database"
os.environ["COSMOSDB_CONTAINER"] = "mock-container"
os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "mock-deployment-name"
os.environ["AZURE_OPENAI_API_VERSION"] = "2023-01-01"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock-openai-endpoint"

# Import product functions and classes.
from src.backend.agents.product import (
    add_mobile_extras_pack,
    get_product_info,
    get_billing_date,
    update_inventory,
    add_new_product,
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
    generate_product_report,
    develop_new_product_ideas,
    optimize_product_page,
    track_product_shipment,
    coordinate_with_marketing,
    review_product_quality,
    collaborate_with_tech_team,
    update_product_description,
    manage_product_returns,
    conduct_product_survey,
    update_product_specifications,
    organize_product_photoshoot,
    manage_product_listing,
    set_product_availability,
    coordinate_with_logistics,
    calculate_product_margin,
    update_product_category,
    manage_product_bundles,
    monitor_product_performance,
    handle_product_pricing,
    develop_product_training_material,
    update_product_labels,
    manage_product_warranty,
    handle_product_licensing,
    manage_product_packaging,
    set_product_safety_standards,
    develop_product_features,
    evaluate_product_performance,
    manage_custom_product_orders,
    update_product_images,
    handle_product_obsolescence,
    manage_product_sku,
    provide_product_training,
    get_product_tools,
)

from autogen_core.components.tools import FunctionTool


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "function, args, expected_substrings",
    [
        (add_mobile_extras_pack, ("Roaming Pack", "2025-01-01"), ["Roaming Pack", "2025-01-01", "AGENT SUMMARY:"]),
        (get_product_info, (), ["Simulated Phone Plans", "Plan A"]),
        (update_inventory, ("Product A", 50), ["Inventory for", "Product A"]),
        (schedule_product_launch, ("New Product", "2025-02-01"), ["New Product", "2025-02-01"]),
        (analyze_sales_data, ("Product B", "Last Quarter"), ["Sales data for", "Product B"]),
        (get_customer_feedback, ("Product C",), ["Customer feedback for", "Product C"]),
        (manage_promotions, ("Product A", "10% off for summer"), ["Promotion for", "Product A"]),
        (check_inventory, ("Product A",), ["Inventory status for", "Product A"]),
        (update_product_price, ("Product A", 99.99), ["Price for", "$99.99"]),
        (provide_product_recommendations, ("High Performance",), ["Product recommendations", "High Performance"]),
        (handle_product_recall, ("Product A", "Defective batch"), ["Product recall for", "Defective batch"]),
        (set_product_discount, ("Product A", 15.0), ["Discount for", "15.0%"]),
        (manage_supply_chain, ("Product A", "Supplier X"), ["Supply chain for", "Supplier X"]),
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


# --- Extra parameterized tests for remaining functions ---
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "function, args, expected_substrings",
    [
        (get_billing_date, (), ["Billing Date"]),
        (add_new_product, ("New smartwatch with health tracking.",), ["New Product Added", "New smartwatch"]),
        (coordinate_with_marketing, ("Smartphone", "Campaign XYZ"), ["Marketing Coordination", "Campaign XYZ"]),
        (review_product_quality, ("Monitor",), ["Quality review", "Monitor"]),
        (collaborate_with_tech_team, ("Drone", "Improve battery efficiency"), ["Tech Team Collaboration", "Improve battery"]),
        (update_product_description, ("Smartwatch", "Sleek design"), ["Product Description Updated", "Sleek design"]),
        (manage_product_returns, ("Printer", "Paper jam"), ["Product Return Managed", "Paper jam"]),
        (conduct_product_survey, ("Monitor", "Online survey"), ["Product Survey Conducted", "Online survey"]),
        (update_product_specifications, ("TV", "1080p, 60Hz"), ["Product Specifications Updated", "1080p, 60Hz"]),
        (organize_product_photoshoot, ("Camera", "2023-06-01"), ["Photoshoot Organized", "2023-06-01"]),
        (manage_product_listing, ("Tablet", "Listed on Amazon"), ["Product Listing Managed", "Amazon"]),
        (set_product_availability, ("Laptop", True), ["available"]),
        (set_product_availability, ("Laptop", False), ["unavailable"]),
        (coordinate_with_logistics, ("Speaker", "Pickup scheduled"), ["Logistics Coordination", "Pickup scheduled"]),
        (calculate_product_margin, ("Laptop", 500, 1000), ["Profit margin", "50.00%"]),
        (update_product_category, ("Phone", "Electronics"), ["Product Category Updated", "Electronics"]),
        (manage_product_bundles, ("Bundle1", ["Phone", "Charger"]), ["Product Bundle Managed", "Phone", "Charger"]),
        (monitor_product_performance, ("Camera",), ["Product Performance Monitored", "Camera"]),
        (handle_product_pricing, ("TV", "Dynamic pricing"), ["Pricing Strategy Set", "Dynamic pricing"]),
        (develop_product_training_material, ("Router", "Video tutorial"), ["Training Material Developed", "Video tutorial"]),
        (update_product_labels, ("Smartphone", "New, Hot"), ["Product Labels Updated", "New, Hot"]),
        (manage_product_warranty, ("Laptop", "2-year warranty"), ["Product Warranty Managed", "2-year warranty"]),
        (handle_product_licensing, ("Software", "GPL License"), ["Product Licensing Handled", "GPL License"]),
        (manage_product_packaging, ("Laptop", "Eco-friendly packaging"), ["Product Packaging Managed", "Eco-friendly packaging"]),
        (set_product_safety_standards, ("Refrigerator", "ISO 9001"), ["Safety standards", "ISO 9001"]),
        (develop_product_features, ("Smart TV", "Voice control, facial recognition"), ["New Features Developed", "Voice control"]),
        (manage_custom_product_orders, ("Custom engraving required",), ["Custom Product Order Managed", "Custom engraving"]),
        (update_product_images, ("Camera", ["http://example.com/img1.jpg", "http://example.com/img2.jpg"]), ["Product Images Updated", "img1.jpg", "img2.jpg"]),
        (handle_product_obsolescence, ("DVD Player",), ["Product Obsolescence Handled", "DVD Player"]),
        (manage_product_sku, ("Phone", "SKU12345"), ["SKU Managed", "SKU12345"]),
        (provide_product_training, ("Tablet", "In-person training session"), ["Product Training Provided", "In-person training session"]),
    ],
)
async def test_product_functions_extra(function, args, expected_substrings):
    result = await function(*args)
    for substring in expected_substrings:
        assert substring in result


# --- Test get_product_tools ---
def test_get_product_tools():
    tools = get_product_tools()
    assert isinstance(tools, list)
    assert any(isinstance(tool, FunctionTool) for tool in tools)
    names = [tool.name for tool in tools]
    assert "add_mobile_extras_pack" in names or "get_product_info" in names
