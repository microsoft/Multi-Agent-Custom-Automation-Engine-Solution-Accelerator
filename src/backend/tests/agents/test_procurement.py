import os
import sys
import pytest
from unittest.mock import MagicMock

# Mocking azure.monitor.events.extension globally
sys.modules["azure.monitor.events.extension"] = MagicMock()

# Setting up environment variables to mock Config dependencies
os.environ["COSMOSDB_ENDPOINT"] = "https://mock-endpoint"
os.environ["COSMOSDB_KEY"] = "mock-key"
os.environ["COSMOSDB_DATABASE"] = "mock-database"
os.environ["COSMOSDB_CONTAINER"] = "mock-container"
os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "mock-deployment-name"
os.environ["AZURE_OPENAI_API_VERSION"] = "2023-01-01"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock-openai-endpoint"

# Import the procurement tools for testing
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
    audit_inventory,
    approve_budget,
    manage_import_licenses,
    allocate_budget,
    track_procurement_metrics,
)

# Mocking `track_event_if_configured` for tests
sys.modules["src.backend.event_utils"] = MagicMock()


@pytest.mark.asyncio
async def test_order_hardware():
    result = await order_hardware("laptop", 10)
    assert "Ordered 10 units of laptop." in result


@pytest.mark.asyncio
async def test_order_software_license():
    result = await order_software_license("Photoshop", "team", 5)
    assert "Ordered 5 team licenses of Photoshop." in result


@pytest.mark.asyncio
async def test_check_inventory():
    result = await check_inventory("printer")
    assert "Inventory status of printer: In Stock." in result


@pytest.mark.asyncio
async def test_process_purchase_order():
    result = await process_purchase_order("PO12345")
    assert "Purchase Order PO12345 has been processed." in result


@pytest.mark.asyncio
async def test_initiate_contract_negotiation():
    result = await initiate_contract_negotiation("VendorX", "Exclusive deal for 2025")
    assert (
        "Contract negotiation initiated with VendorX: Exclusive deal for 2025" in result
    )


@pytest.mark.asyncio
async def test_approve_invoice():
    result = await approve_invoice("INV001")
    assert "Invoice INV001 approved for payment." in result


@pytest.mark.asyncio
async def test_track_order():
    result = await track_order("ORDER123")
    assert "Order ORDER123 is currently in transit." in result


@pytest.mark.asyncio
async def test_manage_vendor_relationship():
    result = await manage_vendor_relationship("VendorY", "renewed")
    assert "Vendor relationship with VendorY has been renewed." in result


@pytest.mark.asyncio
async def test_update_procurement_policy():
    result = await update_procurement_policy(
        "Policy2025", "Updated terms and conditions"
    )
    assert "Procurement policy 'Policy2025' updated." in result


@pytest.mark.asyncio
async def test_generate_procurement_report():
    result = await generate_procurement_report("Annual")
    assert "Generated Annual procurement report." in result


@pytest.mark.asyncio
async def test_evaluate_supplier_performance():
    result = await evaluate_supplier_performance("SupplierZ")
    assert "Performance evaluation for supplier SupplierZ completed." in result


@pytest.mark.asyncio
async def test_handle_return():
    result = await handle_return("Laptop", 3, "Defective screens")
    assert "Processed return of 3 units of Laptop due to Defective screens." in result


@pytest.mark.asyncio
async def test_process_payment():
    result = await process_payment("VendorA", 5000.00)
    assert "Processed payment of $5000.00 to VendorA." in result


@pytest.mark.asyncio
async def test_request_quote():
    result = await request_quote("Tablet", 20)
    assert "Requested quote for 20 units of Tablet." in result


@pytest.mark.asyncio
async def test_recommend_sourcing_options():
    result = await recommend_sourcing_options("Projector")
    assert "Sourcing options for Projector have been provided." in result


@pytest.mark.asyncio
async def test_update_asset_register():
    result = await update_asset_register("ServerX", "Deployed in Data Center")
    assert "Asset register updated for ServerX: Deployed in Data Center" in result


@pytest.mark.asyncio
async def test_conduct_market_research():
    result = await conduct_market_research("Electronics")
    assert "Market research conducted for category: Electronics" in result


@pytest.mark.asyncio
async def test_audit_inventory():
    result = await audit_inventory()
    assert "Inventory audit has been conducted." in result


@pytest.mark.asyncio
async def test_approve_budget():
    result = await approve_budget("BUD001", 25000.00)
    assert "Approved budget ID BUD001 for amount $25000.00." in result


@pytest.mark.asyncio
async def test_manage_import_licenses():
    result = await manage_import_licenses("Smartphones", "License12345")
    assert "Import license for Smartphones managed: License12345." in result


@pytest.mark.asyncio
async def test_allocate_budget():
    result = await allocate_budget("IT Department", 150000.00)
    assert "Allocated budget of $150000.00 to IT Department." in result


@pytest.mark.asyncio
async def test_track_procurement_metrics():
    result = await track_procurement_metrics("Cost Savings")
    assert "Procurement metric 'Cost Savings' tracked." in result


@pytest.mark.asyncio
async def test_order_hardware_invalid_quantity():
    result = await order_hardware("printer", 0)
    assert "Ordered 0 units of printer." in result


@pytest.mark.asyncio
async def test_order_software_license_invalid_type():
    result = await order_software_license("Photoshop", "", 5)
    assert "Ordered 5  licenses of Photoshop." in result


@pytest.mark.asyncio
async def test_check_inventory_empty_item():
    result = await check_inventory("")
    assert "Inventory status of : In Stock." in result


@pytest.mark.asyncio
async def test_process_purchase_order_empty():
    result = await process_purchase_order("")
    assert "Purchase Order  has been processed." in result


@pytest.mark.asyncio
async def test_initiate_contract_negotiation_empty_details():
    result = await initiate_contract_negotiation("", "")
    assert "Contract negotiation initiated with : " in result


@pytest.mark.asyncio
async def test_approve_invoice_empty():
    result = await approve_invoice("")
    assert "Invoice  approved for payment." in result


@pytest.mark.asyncio
async def test_track_order_empty_order():
    result = await track_order("")
    assert "Order  is currently in transit." in result


@pytest.mark.asyncio
async def test_manage_vendor_relationship_empty_action():
    result = await manage_vendor_relationship("VendorA", "")
    assert "Vendor relationship with VendorA has been ." in result


@pytest.mark.asyncio
async def test_update_procurement_policy_no_content():
    result = await update_procurement_policy("Policy2025", "")
    assert "Procurement policy 'Policy2025' updated." in result


@pytest.mark.asyncio
async def test_generate_procurement_report_empty_type():
    result = await generate_procurement_report("")
    assert "Generated  procurement report." in result


@pytest.mark.asyncio
async def test_evaluate_supplier_performance_empty_name():
    result = await evaluate_supplier_performance("")
    assert "Performance evaluation for supplier  completed." in result


@pytest.mark.asyncio
async def test_handle_return_negative_quantity():
    result = await handle_return("Monitor", -5, "Damaged")
    assert "Processed return of -5 units of Monitor due to Damaged." in result


@pytest.mark.asyncio
async def test_process_payment_zero_amount():
    result = await process_payment("VendorB", 0.00)
    assert "Processed payment of $0.00 to VendorB." in result


@pytest.mark.asyncio
async def test_request_quote_empty_item():
    result = await request_quote("", 10)
    assert "Requested quote for 10 units of ." in result


@pytest.mark.asyncio
async def test_recommend_sourcing_options_empty_item():
    result = await recommend_sourcing_options("")
    assert "Sourcing options for  have been provided." in result


@pytest.mark.asyncio
async def test_update_asset_register_empty_details():
    result = await update_asset_register("AssetX", "")
    assert "Asset register updated for AssetX: " in result


@pytest.mark.asyncio
async def test_conduct_market_research_empty_category():
    result = await conduct_market_research("")
    assert "Market research conducted for category: " in result


@pytest.mark.asyncio
async def test_audit_inventory_double_call():
    result1 = await audit_inventory()
    result2 = await audit_inventory()
    assert result1 == "Inventory audit has been conducted."
    assert result2 == "Inventory audit has been conducted."


@pytest.mark.asyncio
async def test_approve_budget_negative_amount():
    result = await approve_budget("BUD002", -1000.00)
    assert "Approved budget ID BUD002 for amount $-1000.00." in result


@pytest.mark.asyncio
async def test_manage_import_licenses_empty_license():
    result = await manage_import_licenses("Electronics", "")
    assert "Import license for Electronics managed: ." in result


@pytest.mark.asyncio
async def test_allocate_budget_negative_value():
    result = await allocate_budget("HR Department", -50000.00)
    assert "Allocated budget of $-50000.00 to HR Department." in result


@pytest.mark.asyncio
async def test_track_procurement_metrics_empty_metric():
    result = await track_procurement_metrics("")
    assert "Procurement metric '' tracked." in result


@pytest.mark.asyncio
async def test_handle_return_zero_quantity():
    result = await handle_return("Monitor", 0, "Packaging error")
    assert "Processed return of 0 units of Monitor due to Packaging error." in result


@pytest.mark.asyncio
async def test_order_hardware_large_quantity():
    result = await order_hardware("Monitor", 1000000)
    assert "Ordered 1000000 units of Monitor." in result


@pytest.mark.asyncio
async def test_process_payment_large_amount():
    result = await process_payment("VendorX", 10000000.99)
    assert "Processed payment of $10000000.99 to VendorX." in result


@pytest.mark.asyncio
async def test_track_order_invalid_number():
    result = await track_order("INVALID123")
    assert "Order INVALID123 is currently in transit." in result


@pytest.mark.asyncio
async def test_initiate_contract_negotiation_long_details():
    long_details = (
        "This is a very long contract negotiation detail for testing purposes. " * 10
    )
    result = await initiate_contract_negotiation("VendorY", long_details)
    assert "Contract negotiation initiated with VendorY" in result
    assert long_details in result


@pytest.mark.asyncio
async def test_manage_vendor_relationship_invalid_action():
    result = await manage_vendor_relationship("VendorZ", "undefined")
    assert "Vendor relationship with VendorZ has been undefined." in result


@pytest.mark.asyncio
async def test_update_procurement_policy_no_policy_name():
    result = await update_procurement_policy("", "Updated policy details")
    assert "Procurement policy '' updated." in result


@pytest.mark.asyncio
async def test_generate_procurement_report_invalid_type():
    result = await generate_procurement_report("Nonexistent")
    assert "Generated Nonexistent procurement report." in result


@pytest.mark.asyncio
async def test_evaluate_supplier_performance_no_supplier_name():
    result = await evaluate_supplier_performance("")
    assert "Performance evaluation for supplier  completed." in result


@pytest.mark.asyncio
async def test_manage_import_licenses_no_item_name():
    result = await manage_import_licenses("", "License123")
    assert "Import license for  managed: License123." in result


@pytest.mark.asyncio
async def test_allocate_budget_zero_value():
    result = await allocate_budget("Operations", 0)
    assert "Allocated budget of $0.00 to Operations." in result


@pytest.mark.asyncio
async def test_audit_inventory_multiple_calls():
    result1 = await audit_inventory()
    result2 = await audit_inventory()
    assert result1 == "Inventory audit has been conducted."
    assert result2 == "Inventory audit has been conducted."


@pytest.mark.asyncio
async def test_approve_budget_large_amount():
    result = await approve_budget("BUD123", 1e9)
    assert "Approved budget ID BUD123 for amount $1000000000.00." in result


@pytest.mark.asyncio
async def test_request_quote_no_quantity():
    result = await request_quote("Laptop", 0)
    assert "Requested quote for 0 units of Laptop." in result


@pytest.mark.asyncio
async def test_conduct_market_research_no_category():
    result = await conduct_market_research("")
    assert "Market research conducted for category: " in result


@pytest.mark.asyncio
async def test_track_procurement_metrics_no_metric_name():
    result = await track_procurement_metrics("")
    assert "Procurement metric '' tracked." in result


@pytest.mark.asyncio
async def test_order_hardware_no_item_name():
    """Test line 98: Edge case where item name is empty."""
    result = await order_hardware("", 5)
    assert "Ordered 5 units of ." in result


@pytest.mark.asyncio
async def test_order_hardware_negative_quantity():
    """Test line 108: Handle negative quantities."""
    result = await order_hardware("Keyboard", -5)
    assert "Ordered -5 units of Keyboard." in result


@pytest.mark.asyncio
async def test_order_software_license_no_license_type():
    """Test line 123: License type missing."""
    result = await order_software_license("Photoshop", "", 10)
    assert "Ordered 10  licenses of Photoshop." in result


@pytest.mark.asyncio
async def test_order_software_license_no_quantity():
    """Test line 128: Quantity missing."""
    result = await order_software_license("Photoshop", "team", 0)
    assert "Ordered 0 team licenses of Photoshop." in result


@pytest.mark.asyncio
async def test_process_purchase_order_invalid_number():
    """Test line 133: Invalid purchase order number."""
    result = await process_purchase_order("")
    assert "Purchase Order  has been processed." in result


@pytest.mark.asyncio
async def test_check_inventory_empty_item_name():
    """Test line 138: Inventory check for an empty item."""
    result = await check_inventory("")
    assert "Inventory status of : In Stock." in result


@pytest.mark.asyncio
async def test_initiate_contract_negotiation_empty_vendor():
    """Test line 143: Contract negotiation with empty vendor name."""
    result = await initiate_contract_negotiation("", "Sample contract")
    assert "Contract negotiation initiated with : Sample contract" in result


@pytest.mark.asyncio
async def test_update_procurement_policy_empty_policy_name():
    """Test line 158: Empty policy name."""
    result = await update_procurement_policy("", "New terms")
    assert "Procurement policy '' updated." in result


@pytest.mark.asyncio
async def test_evaluate_supplier_performance_no_name():
    """Test line 168: Empty supplier name."""
    result = await evaluate_supplier_performance("")
    assert "Performance evaluation for supplier  completed." in result


@pytest.mark.asyncio
async def test_handle_return_empty_reason():
    """Test line 173: Handle return with no reason provided."""
    result = await handle_return("Laptop", 2, "")
    assert "Processed return of 2 units of Laptop due to ." in result


@pytest.mark.asyncio
async def test_process_payment_no_vendor_name():
    """Test line 178: Payment processing with no vendor name."""
    result = await process_payment("", 500.00)
    assert "Processed payment of $500.00 to ." in result


@pytest.mark.asyncio
async def test_manage_import_licenses_no_details():
    """Test line 220: Import licenses with empty details."""
    result = await manage_import_licenses("Smartphones", "")
    assert "Import license for Smartphones managed: ." in result


@pytest.mark.asyncio
async def test_allocate_budget_no_department_name():
    """Test line 255: Allocate budget with empty department name."""
    result = await allocate_budget("", 1000.00)
    assert "Allocated budget of $1000.00 to ." in result


@pytest.mark.asyncio
async def test_track_procurement_metrics_no_metric():
    """Test line 540: Track metrics with empty metric name."""
    result = await track_procurement_metrics("")
    assert "Procurement metric '' tracked." in result


@pytest.mark.asyncio
async def test_handle_return_negative_and_zero_quantity():
    """Covers lines 173, 178."""
    result_negative = await handle_return("Laptop", -5, "Damaged")
    result_zero = await handle_return("Laptop", 0, "Packaging Issue")
    assert "Processed return of -5 units of Laptop due to Damaged." in result_negative
    assert (
        "Processed return of 0 units of Laptop due to Packaging Issue." in result_zero
    )


@pytest.mark.asyncio
async def test_process_payment_no_vendor_name_large_amount():
    """Covers line 188."""
    result_empty_vendor = await process_payment("", 1000000.00)
    assert "Processed payment of $1000000.00 to ." in result_empty_vendor


@pytest.mark.asyncio
async def test_request_quote_edge_cases():
    """Covers lines 193, 198."""
    result_no_quantity = await request_quote("Tablet", 0)
    result_negative_quantity = await request_quote("Tablet", -10)
    assert "Requested quote for 0 units of Tablet." in result_no_quantity
    assert "Requested quote for -10 units of Tablet." in result_negative_quantity


@pytest.mark.asyncio
async def test_update_asset_register_no_details():
    """Covers line 203."""
    result = await update_asset_register("ServerX", "")
    assert "Asset register updated for ServerX: " in result


@pytest.mark.asyncio
async def test_audit_inventory_multiple_runs():
    """Covers lines 213."""
    result1 = await audit_inventory()
    result2 = await audit_inventory()
    assert result1 == "Inventory audit has been conducted."
    assert result2 == "Inventory audit has been conducted."


@pytest.mark.asyncio
async def test_approve_budget_negative_and_zero_amount():
    """Covers lines 220, 225."""
    result_zero = await approve_budget("BUD123", 0.00)
    result_negative = await approve_budget("BUD124", -500.00)
    assert "Approved budget ID BUD123 for amount $0.00." in result_zero
    assert "Approved budget ID BUD124 for amount $-500.00." in result_negative


@pytest.mark.asyncio
async def test_manage_import_licenses_no_license_details():
    """Covers lines 230, 235."""
    result_empty_license = await manage_import_licenses("Smartphones", "")
    result_no_item = await manage_import_licenses("", "License12345")
    assert "Import license for Smartphones managed: ." in result_empty_license
    assert "Import license for  managed: License12345." in result_no_item


@pytest.mark.asyncio
async def test_allocate_budget_no_department_and_large_values():
    """Covers lines 250, 255."""
    result_no_department = await allocate_budget("", 10000.00)
    result_large_amount = await allocate_budget("Operations", 1e9)
    assert "Allocated budget of $10000.00 to ." in result_no_department
    assert "Allocated budget of $1000000000.00 to Operations." in result_large_amount


@pytest.mark.asyncio
async def test_track_procurement_metrics_empty_name():
    """Covers line 540."""
    result = await track_procurement_metrics("")
    assert "Procurement metric '' tracked." in result


@pytest.mark.asyncio
async def test_order_hardware_missing_name_and_zero_quantity():
    """Covers lines 98 and 108."""
    result_missing_name = await order_hardware("", 10)
    result_zero_quantity = await order_hardware("Keyboard", 0)
    assert "Ordered 10 units of ." in result_missing_name
    assert "Ordered 0 units of Keyboard." in result_zero_quantity


@pytest.mark.asyncio
async def test_process_purchase_order_empty_number():
    """Covers line 133."""
    result = await process_purchase_order("")
    assert "Purchase Order  has been processed." in result


@pytest.mark.asyncio
async def test_initiate_contract_negotiation_empty_vendor_and_details():
    """Covers lines 143, 148."""
    result_empty_vendor = await initiate_contract_negotiation("", "Details")
    result_empty_details = await initiate_contract_negotiation("VendorX", "")
    assert "Contract negotiation initiated with : Details" in result_empty_vendor
    assert "Contract negotiation initiated with VendorX: " in result_empty_details


@pytest.mark.asyncio
async def test_manage_vendor_relationship_unexpected_action():
    """Covers line 153."""
    result = await manage_vendor_relationship("VendorZ", "undefined")
    assert "Vendor relationship with VendorZ has been undefined." in result


@pytest.mark.asyncio
async def test_handle_return_zero_and_negative_quantity():
    """Covers lines 173, 178."""
    result_zero = await handle_return("Monitor", 0, "No issue")
    result_negative = await handle_return("Monitor", -5, "Damaged")
    assert "Processed return of 0 units of Monitor due to No issue." in result_zero
    assert "Processed return of -5 units of Monitor due to Damaged." in result_negative


@pytest.mark.asyncio
async def test_process_payment_large_amount_and_no_vendor_name():
    """Covers line 188."""
    result_large_amount = await process_payment("VendorX", 1e7)
    result_no_vendor = await process_payment("", 500.00)
    assert "Processed payment of $10000000.00 to VendorX." in result_large_amount
    assert "Processed payment of $500.00 to ." in result_no_vendor


@pytest.mark.asyncio
async def test_request_quote_zero_and_negative_quantity():
    """Covers lines 193, 198."""
    result_zero = await request_quote("Tablet", 0)
    result_negative = await request_quote("Tablet", -10)
    assert "Requested quote for 0 units of Tablet." in result_zero
    assert "Requested quote for -10 units of Tablet." in result_negative


@pytest.mark.asyncio
async def test_track_procurement_metrics_with_invalid_input():
    """Covers edge cases for tracking metrics."""
    result_empty = await track_procurement_metrics("")
    result_invalid = await track_procurement_metrics("InvalidMetricName")
    assert "Procurement metric '' tracked." in result_empty
    assert "Procurement metric 'InvalidMetricName' tracked." in result_invalid


@pytest.mark.asyncio
async def test_order_hardware_invalid_cases():
    """Covers invalid inputs for order_hardware."""
    result_no_name = await order_hardware("", 5)
    result_negative_quantity = await order_hardware("Laptop", -10)
    assert "Ordered 5 units of ." in result_no_name
    assert "Ordered -10 units of Laptop." in result_negative_quantity


@pytest.mark.asyncio
async def test_order_software_license_invalid_cases():
    """Covers invalid inputs for order_software_license."""
    result_empty_type = await order_software_license("Photoshop", "", 5)
    result_zero_quantity = await order_software_license("Photoshop", "Single User", 0)
    assert "Ordered 5  licenses of Photoshop." in result_empty_type
    assert "Ordered 0 Single User licenses of Photoshop." in result_zero_quantity
