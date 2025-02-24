import os
import sys
import pytest
from unittest.mock import MagicMock

# --- Fake missing Azure modules ---
sys.modules["azure.monitor.events.extension"] = MagicMock()

# Adjust sys.path so that the project root is found.
# Assuming this test file is at: src/backend/tests/agents/test_procurement.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Set required environment variables (needed by Config and other modules)
os.environ["COSMOSDB_ENDPOINT"] = "https://mock-endpoint"
os.environ["COSMOSDB_KEY"] = "mock-key"
os.environ["COSMOSDB_DATABASE"] = "mock-database"
os.environ["COSMOSDB_CONTAINER"] = "mock-container"
os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "mock-deployment-name"
os.environ["AZURE_OPENAI_API_VERSION"] = "2023-01-01"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock-openai-endpoint"

# Import procurement functions and classes from procurement.py
from src.backend.agents.procurement import (
    order_hardware,
    order_software_license,
    check_inventory,
    process_purchase_order,
    initiate_contract_negotiation,
    approve_invoice,
    track_order,
    manage_vendor_relationship,
    update_procurement_policy,
    generate_procurement_report,
    evaluate_supplier_performance,
    handle_return,
    process_payment,
    request_quote,
    recommend_sourcing_options,
    update_asset_register,
    conduct_market_research,
    get_procurement_information,
    schedule_maintenance,
    audit_inventory,
    approve_budget,
    manage_warranty,
    handle_customs_clearance,
    negotiate_discount,
    register_new_vendor,
    decommission_asset,
    schedule_training,
    update_vendor_rating,
    handle_recall,
    request_samples,
    manage_subscription,
    verify_supplier_certification,
    conduct_supplier_audit,
    manage_import_licenses,
    conduct_cost_analysis,
    evaluate_risk_factors,
    manage_green_procurement_policy,
    update_supplier_database,
    handle_dispute_resolution,
    assess_compliance,
    manage_reverse_logistics,
    verify_delivery,
    handle_procurement_risk_assessment,
    manage_supplier_contract,
    allocate_budget,
    track_procurement_metrics,
    manage_inventory_levels,
    conduct_supplier_survey,
    get_procurement_tools,
)


# --- Parameterized tests for Procurement functions ---
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "func, args, expected",
    [
        (order_hardware, ("Laptop", 3), "Ordered 3 units of Laptop."),
        (order_software_license, ("OfficeSuite", "Enterprise", 5), "Ordered 5 Enterprise licenses of OfficeSuite."),
        (check_inventory, ("Monitor",), "Inventory status of Monitor: In Stock."),
        (process_purchase_order, ("PO123",), "Purchase Order PO123 has been processed."),
        (initiate_contract_negotiation, ("VendorX", "Exclusive deal"), "Contract negotiation initiated with VendorX: Exclusive deal"),
        (approve_invoice, ("INV001",), "Invoice INV001 approved for payment."),
        (track_order, ("ORDER001",), "Order ORDER001 is currently in transit."),
        (manage_vendor_relationship, ("VendorY", "improved"), "Vendor relationship with VendorY has been improved."),
        (update_procurement_policy, ("Policy1", "New Terms"), "Procurement policy 'Policy1' updated."),
        (generate_procurement_report, ("Summary",), "Generated Summary procurement report."),
        (evaluate_supplier_performance, ("SupplierA",), "Performance evaluation for supplier SupplierA completed."),
        (handle_return, ("Printer", 2, "Defective"), "Processed return of 2 units of Printer due to Defective."),
        (process_payment, ("VendorZ", 999.99), "Processed payment of $999.99 to VendorZ."),
        (request_quote, ("Server", 4), "Requested quote for 4 units of Server."),
        (recommend_sourcing_options, ("Router",), "Sourcing options for Router have been provided."),
        (update_asset_register, ("Asset1", "Details"), "Asset register updated for Asset1: Details"),
        (conduct_market_research, ("Electronics",), "Market research conducted for category: Electronics"),
        # For get_procurement_information, we now expect the returned text to contain a known substring.
        (get_procurement_information, ("Any query",), "Contoso's Procurement Policies and Procedures"),
        (schedule_maintenance, ("Printer", "2023-07-01"), "Scheduled maintenance for Printer on 2023-07-01."),
        (audit_inventory, (), "Inventory audit has been conducted."),
        (approve_budget, ("BUD001", 2000.0), "Approved budget ID BUD001 for amount $2000.00."),
        (manage_warranty, ("Laptop", "1 year"), "Warranty for Laptop managed for period 1 year."),
        (handle_customs_clearance, ("SHIP001",), "Customs clearance for shipment ID SHIP001 handled."),
        (negotiate_discount, ("VendorQ", 10.0), "Negotiated a 10.0% discount with vendor VendorQ."),
        (register_new_vendor, ("VendorNew", "Details"), "New vendor VendorNew registered with details: Details."),
        (decommission_asset, ("Old Printer",), "Asset Old Printer has been decommissioned."),
        (schedule_training, ("Procurement Basics", "2023-08-15"), "Training session 'Procurement Basics' scheduled on 2023-08-15."),
        (update_vendor_rating, ("VendorR", 4.5), "Vendor VendorR rating updated to 4.5."),
        (handle_recall, ("Monitor", "Faulty display"), "Recall of Monitor due to Faulty display handled."),
        (request_samples, ("Keyboard", 3), "Requested 3 samples of Keyboard."),
        (manage_subscription, ("CloudService", "activated"), "Subscription to CloudService has been activated."),
        (verify_supplier_certification, ("SupplierZ",), "Certification status of supplier SupplierZ verified."),
        (conduct_supplier_audit, ("SupplierZ",), "Audit of supplier SupplierZ conducted."),
        (manage_import_licenses, ("ItemX", "License Info"), "Import license for ItemX managed: License Info."),
        (conduct_cost_analysis, ("ItemY",), "Cost analysis for ItemY conducted."),
        (evaluate_risk_factors, ("ItemZ",), "Risk factors for ItemZ evaluated."),
        (manage_green_procurement_policy, ("Eco Policy",), "Green procurement policy managed: Eco Policy."),
        (update_supplier_database, ("SupplierM", "New Info"), "Supplier database updated for SupplierM: New Info."),
        (handle_dispute_resolution, ("VendorP", "Late delivery"), "Dispute with vendor VendorP over issue 'Late delivery' resolved."),
        (assess_compliance, ("ItemQ", "ISO standards"), "Compliance of ItemQ with standards 'ISO standards' assessed."),
        (manage_reverse_logistics, ("ItemR", 5), "Reverse logistics managed for 5 units of ItemR."),
        (verify_delivery, ("ItemS", "Delivered"), "Delivery status of ItemS verified as Delivered."),
        (handle_procurement_risk_assessment, ("Risk details",), "Procurement risk assessment handled: Risk details."),
        (manage_supplier_contract, ("VendorT", "renewed"), "Supplier contract with VendorT has been renewed."),
        (allocate_budget, ("DeptX", 1500.0), "Allocated budget of $1500.00 to DeptX."),
        (track_procurement_metrics, ("Metric1",), "Procurement metric 'Metric1' tracked."),
        (manage_inventory_levels, ("ItemU", "increased"), "Inventory levels for ItemU have been increased."),
        (conduct_supplier_survey, ("SupplierV",), "Survey of supplier SupplierV conducted."),
    ],
)
async def test_procurement_functions(func, args, expected):
    result = await func(*args)
    # For get_procurement_information, check for substring instead of full equality.
    if func.__name__ == "get_procurement_information":
        assert expected in result
    else:
        assert result == expected


# --- Test get_procurement_tools ---
def test_get_procurement_tools():
    tools = get_procurement_tools()
    from autogen_core.components.tools import FunctionTool
    assert isinstance(tools, list)
    assert len(tools) > 0
    assert any(isinstance(tool, FunctionTool) for tool in tools)
    names = [tool.name for tool in tools]
    # Check that one of the expected tool names is present.
    assert "order_hardware" in names
