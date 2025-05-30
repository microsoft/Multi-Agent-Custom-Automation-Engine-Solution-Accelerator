# src/tests/backend/kernel_tools/test_product_tools.py

import sys
import os
import types
import pytest
import json
from datetime import datetime

# --- Stub out semantic_kernel.functions ---
sk_pkg = types.ModuleType("semantic_kernel")
sk_pkg.__path__ = []
sk_funcs = types.ModuleType("semantic_kernel.functions")
def kernel_function(name=None, description=None):
    def decorator(func):
        # attach a __kernel_function__ marker
        setattr(func, "__kernel_function__", types.SimpleNamespace(name=name or func.__name__, description=description))
        return func
    return decorator
sk_funcs.kernel_function = kernel_function
sys.modules["semantic_kernel"] = sk_pkg
sys.modules["semantic_kernel.functions"] = sk_funcs

# --- Stub out models.messages_kernel.AgentType ---
models_pkg = types.ModuleType("models")
msgs_mod = types.ModuleType("models.messages_kernel")
from enum import Enum
class AgentType(Enum):
    PRODUCT = "product_agent"
msgs_mod.AgentType = AgentType
models_pkg.messages_kernel = msgs_mod
sys.modules["models"] = models_pkg
sys.modules["models.messages_kernel"] = msgs_mod

# --- Ensure src is on PYTHONPATH ---
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from backend.kernel_tools.product_tools import ProductTools


@pytest.mark.asyncio
async def test_add_mobile_extras_pack():
    result = await ProductTools.add_mobile_extras_pack("Roaming Plus", "2025-07-01")
    assert "## New Plan" in result
    assert "Roaming Plus" in result
    assert "2025-07-01" in result


def test_generate_tools_json_doc():
    doc = ProductTools.generate_tools_json_doc()
    tools = json.loads(doc)
    assert isinstance(tools, list)
    inv = next((t for t in tools if t["function"] == "check_inventory"), None)
    assert inv is not None
    assert inv["agent"] == ProductTools.agent_name
    assert "product_name" in inv["arguments"]


@pytest.mark.asyncio
async def test_update_and_check_inventory_prints(capsys):
    chk = await ProductTools.check_inventory("GadgetZ")
    upd = await ProductTools.update_inventory("GadgetZ", 10)
    assert chk == "## Inventory Status\nInventory status for **'GadgetZ'** checked."
    assert upd == "## Inventory Update\nInventory for **'GadgetZ'** updated by **10** units."
    captured = capsys.readouterr()
    assert "Inventory status for **'GadgetZ'** checked." in captured.out
    assert "Inventory for **'GadgetZ'** updated by **10** units." in captured.out


def test_get_all_kernel_functions_filters_only_decorated():
    funcs = ProductTools.get_all_kernel_functions()
    # Decorated methods should appear
    assert "add_mobile_extras_pack" in funcs
    assert "get_billing_date" in funcs
    # Introspection helpers should not
    assert "generate_tools_json_doc" not in funcs
    assert "get_all_kernel_functions" not in funcs


# -----------------------------------------------------------------------------
# Parametrized test to cover all other async methods in ProductTools
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,args,expected_substr",
    [
        ("get_product_info", [], "Here is information to relay"),
        ("add_new_product", ["NewWidget details"], "## New Product Added"),
        ("update_product_price", ["WidgetX", 19.99], "## Price Update"),
        ("schedule_product_launch", ["WidgetX", "2025-09-01"], "## Product Launch Scheduled"),
        ("analyze_sales_data", ["WidgetX", "Q1"], "## Sales Data Analysis"),
        ("get_customer_feedback", ["WidgetX"], "## Customer Feedback"),
        ("manage_promotions", ["WidgetX", "Promo"], "## Promotion Managed"),
        ("coordinate_with_marketing", ["WidgetX", "Campaign"], "## Marketing Coordination"),
        ("review_product_quality", ["WidgetX"], "## Quality Review"),
        ("handle_product_recall", ["WidgetX", "Defect"], "## Product Recall"),
        ("provide_product_recommendations", ["pref"], "## Product Recommendations"),
        ("generate_product_report", ["WidgetX", "Summary"], "## Summary Report"),
        ("manage_supply_chain", ["WidgetX", "SupCo"], "## Supply Chain Management"),
        ("track_product_shipment", ["WidgetX", "TRACK123"], "## Shipment Tracking"),
        ("set_reorder_level", ["WidgetX", 50], "## Reorder Level Set"),
        ("monitor_market_trends", [], "## Market Trends"),
        ("develop_new_product_ideas", ["Cool idea"], "## New Product Idea"),
        ("collaborate_with_tech_team", ["WidgetX", "Spec"], "## Tech Team Collaboration"),
        ("update_product_description", ["WidgetX", "New desc"], "## Product Description Updated"),
        ("set_product_discount", ["WidgetX", 15.0], "## Discount Set"),
        ("manage_product_returns", ["WidgetX", "Broken"], "## Product Return Managed"),
        ("conduct_product_survey", ["WidgetX", "SurveyQ"], "## Product Survey Conducted"),
        ("handle_product_complaints", ["WidgetX", "Late"], "## Product Complaint Handled"),
        ("update_product_specifications", ["WidgetX", "Specs"], "## Product Specifications Updated"),
        ("organize_product_photoshoot", ["WidgetX", "2025-10-10"], "## Product Photoshoot Organized"),
        ("manage_product_listing", ["WidgetX", "Details"], "## Product Listing Managed"),
        ("set_product_availability", ["WidgetX", True], "now **available**"),
        ("coordinate_with_logistics", ["WidgetX", "Logistics"], "## Logistics Coordination"),
        ("calculate_product_margin", ["WidgetX", 10.0, 20.0], "## Profit Margin Calculated"),
        ("update_product_category", ["WidgetX", "Gadgets"], "## Product Category Updated"),
        ("manage_product_bundles", ["Bundle1", ["A", "B"]], "## Product Bundle Managed"),
        ("optimize_product_page", ["WidgetX", "Speed"], "## Product Page Optimized"),
        ("monitor_product_performance", ["WidgetX"], "## Product Performance Monitored"),
        ("handle_product_pricing", ["WidgetX", "Premium"], "## Pricing Strategy Set"),
        ("create_training_material", ["WidgetX", "Material"], "## Training Material Developed"),
        ("update_product_labels", ["WidgetX", "Labels"], "## Product Labels Updated"),
        ("manage_product_warranty", ["WidgetX", "1 year"], "## Product Warranty Managed"),
        ("forecast_product_demand", ["WidgetX", "NextMonth"], "## Demand Forecast"),
        ("handle_product_licensing", ["WidgetX", "License"], "## Product Licensing Handled"),
        ("manage_product_packaging", ["WidgetX", "Box"], "## Product Packaging Managed"),
        ("set_product_safety_standards", ["WidgetX", "Standards"], "## Safety Standards Set"),
        ("develop_product_features", ["WidgetX", "NewFeat"], "## New Features Developed"),
        ("evaluate_product_performance", ["WidgetX", "KPIs"], "## Product Performance Evaluated"),
        ("manage_custom_product_orders", ["OrderDetails"], "## Custom Product Order Managed"),
        ("update_product_images", ["WidgetX", ["url1","url2"]], "## Product Images Updated"),
        ("handle_product_obsolescence", ["WidgetX"], "## Product Obsolescence Handled"),
        ("manage_product_sku", ["WidgetX", "SKU123"], "## SKU Managed"),
        ("provide_product_training", ["WidgetX", "Session"], "## Product Training Provided"),
    ],
)
async def test_all_other_tools(method, args, expected_substr):
    fn = getattr(ProductTools, method)
    result = await fn(*args)
    assert expected_substr in result


def test_check_inventory_and_update_prints(capsys):
    # ensure the print side-effects still occur
    import asyncio
    chk = asyncio.get_event_loop().run_until_complete(ProductTools.check_inventory("X"))
    upd = asyncio.get_event_loop().run_until_complete(ProductTools.update_inventory("X", 5))
    out = capsys.readouterr().out
    assert "Inventory status for **'X'** checked." in out
    assert "Inventory for **'X'** updated by **5** units." in out
