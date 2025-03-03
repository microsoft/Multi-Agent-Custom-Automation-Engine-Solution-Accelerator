from typing import List

from autogen_core.base import AgentId
from autogen_core.components import default_subscription
from autogen_core.components.models import AzureOpenAIChatCompletionClient
from autogen_core.components.tools import FunctionTool, Tool
from typing_extensions import Annotated

from src.backend.agents.base_agent import BaseAgent
from src.backend.context.cosmos_memory import CosmosBufferedChatCompletionContext


# Define new Procurement tools (functions)
async def order_hardware(item_name: str, quantity: int) -> str:
    """Order hardware items like laptops, monitors, etc."""
    return f"Ordered {quantity} units of {item_name}."


async def order_software_license(
    software_name: str, license_type: str, quantity: int
) -> str:
    """Order software licenses."""
    return f"Ordered {quantity} {license_type} licenses of {software_name}."


async def check_inventory(item_name: str) -> str:
    """Check the inventory status of an item."""
    return f"Inventory status of {item_name}: In Stock."


async def process_purchase_order(po_number: str) -> str:
    """Process a purchase order."""
    return f"Purchase Order {po_number} has been processed."


async def initiate_contract_negotiation(vendor_name: str, contract_details: str) -> str:
    """Initiate contract negotiation with a vendor."""
    return f"Contract negotiation initiated with {vendor_name}: {contract_details}"


async def approve_invoice(invoice_number: str) -> str:
    """Approve an invoice for payment."""
    return f"Invoice {invoice_number} approved for payment."


async def track_order(order_number: str) -> str:
    """Track the status of an order."""
    return f"Order {order_number} is currently in transit."


async def manage_vendor_relationship(vendor_name: str, action: str) -> str:
    """Manage relationships with vendors."""
    return f"Vendor relationship with {vendor_name} has been {action}."


async def update_procurement_policy(policy_name: str, policy_content: str) -> str:
    """Update a procurement policy."""
    return f"Procurement policy '{policy_name}' updated."


async def generate_procurement_report(report_type: str) -> str:
    """Generate a procurement report."""
    return f"Generated {report_type} procurement report."


async def evaluate_supplier_performance(supplier_name: str) -> str:
    """Evaluate the performance of a supplier."""
    return f"Performance evaluation for supplier {supplier_name} completed."


async def handle_return(item_name: str, quantity: int, reason: str) -> str:
    """Handle the return of procured items."""
    return f"Processed return of {quantity} units of {item_name} due to {reason}."


async def process_payment(vendor_name: str, amount: float) -> str:
    """Process payment to a vendor."""
    return f"Processed payment of ${amount:.2f} to {vendor_name}."


async def request_quote(item_name: str, quantity: int) -> str:
    """Request a quote for items."""
    return f"Requested quote for {quantity} units of {item_name}."


async def recommend_sourcing_options(item_name: str) -> str:
    """Recommend sourcing options for an item."""
    return f"Sourcing options for {item_name} have been provided."


async def update_asset_register(asset_name: str, asset_details: str) -> str:
    """Update the asset register with new or disposed assets."""
    return f"Asset register updated for {asset_name}: {asset_details}"


async def manage_leasing_agreements(agreement_details: str) -> str:
    """Manage leasing agreements for assets."""
    return f"Leasing agreement processed: {agreement_details}"


async def conduct_market_research(category: str) -> str:
    """Conduct market research for procurement purposes."""
    return f"Market research conducted for category: {category}"


async def schedule_maintenance(equipment_name: str, maintenance_date: str) -> str:
    """Schedule maintenance for equipment."""
    return f"Scheduled maintenance for {equipment_name} on {maintenance_date}."


async def audit_inventory() -> str:
    """Conduct an inventory audit."""
    return "Inventory audit has been conducted."


async def approve_budget(budget_id: str, amount: float) -> str:
    """Approve a procurement budget."""
    return f"Approved budget ID {budget_id} for amount ${amount:.2f}."


async def manage_warranty(item_name: str, warranty_period: str) -> str:
    """Manage warranties for procured items."""
    return f"Warranty for {item_name} managed for period {warranty_period}."


async def handle_customs_clearance(shipment_id: str) -> str:
    """Handle customs clearance for international shipments."""
    return f"Customs clearance for shipment ID {shipment_id} handled."


async def negotiate_discount(vendor_name: str, discount_percentage: float) -> str:
    """Negotiate a discount with a vendor."""
    return f"Negotiated a {discount_percentage}% discount with vendor {vendor_name}."


async def register_new_vendor(vendor_name: str, vendor_details: str) -> str:
    """Register a new vendor."""
    return f"New vendor {vendor_name} registered with details: {vendor_details}."


async def decommission_asset(asset_name: str) -> str:
    """Decommission an asset."""
    return f"Asset {asset_name} has been decommissioned."


async def schedule_training(session_name: str, date: str) -> str:
    """Schedule a training session for procurement staff."""
    return f"Training session '{session_name}' scheduled on {date}."


async def update_vendor_rating(vendor_name: str, rating: float) -> str:
    """Update the rating of a vendor."""
    return f"Vendor {vendor_name} rating updated to {rating}."


async def handle_recall(item_name: str, recall_reason: str) -> str:
    """Handle the recall of a procured item."""
    return f"Recall of {item_name} due to {recall_reason} handled."


async def request_samples(item_name: str, quantity: int) -> str:
    """Request samples of an item."""
    return f"Requested {quantity} samples of {item_name}."


async def manage_subscription(service_name: str, action: str) -> str:
    """Manage subscriptions to services."""
    return f"Subscription to {service_name} has been {action}."


async def verify_supplier_certification(supplier_name: str) -> str:
    """Verify the certification status of a supplier."""
    return f"Certification status of supplier {supplier_name} verified."


async def conduct_supplier_audit(supplier_name: str) -> str:
    """Conduct an audit of a supplier."""
    return f"Audit of supplier {supplier_name} conducted."


async def manage_import_licenses(item_name: str, license_details: str) -> str:
    """Manage import licenses for items."""
    return f"Import license for {item_name} managed: {license_details}."


async def conduct_cost_analysis(item_name: str) -> str:
    """Conduct a cost analysis for an item."""
    return f"Cost analysis for {item_name} conducted."


async def evaluate_risk_factors(item_name: str) -> str:
    """Evaluate risk factors associated with procuring an item."""
    return f"Risk factors for {item_name} evaluated."


async def manage_green_procurement_policy(policy_details: str) -> str:
    """Manage green procurement policy."""
    return f"Green procurement policy managed: {policy_details}."


async def update_supplier_database(supplier_name: str, supplier_info: str) -> str:
    """Update the supplier database with new information."""
    return f"Supplier database updated for {supplier_name}: {supplier_info}."


async def handle_dispute_resolution(vendor_name: str, issue: str) -> str:
    """Handle dispute resolution with a vendor."""
    return f"Dispute with vendor {vendor_name} over issue '{issue}' resolved."


async def assess_compliance(item_name: str, compliance_standards: str) -> str:
    """Assess compliance of an item with standards."""
    return (
        f"Compliance of {item_name} with standards '{compliance_standards}' assessed."
    )


async def manage_reverse_logistics(item_name: str, quantity: int) -> str:
    """Manage reverse logistics for returning items."""
    return f"Reverse logistics managed for {quantity} units of {item_name}."


async def verify_delivery(item_name: str, delivery_status: str) -> str:
    """Verify delivery status of an item."""
    return f"Delivery status of {item_name} verified as {delivery_status}."


async def handle_procurement_risk_assessment(risk_details: str) -> str:
    """Handle procurement risk assessment."""
    return f"Procurement risk assessment handled: {risk_details}."


async def manage_supplier_contract(supplier_name: str, contract_action: str) -> str:
    """Manage supplier contract actions."""
    return f"Supplier contract with {supplier_name} has been {contract_action}."


async def allocate_budget(department_name: str, budget_amount: float) -> str:
    """Allocate budget to a department."""
    return f"Allocated budget of ${budget_amount:.2f} to {department_name}."


async def track_procurement_metrics(metric_name: str) -> str:
    """Track procurement metrics."""
    return f"Procurement metric '{metric_name}' tracked."


async def manage_inventory_levels(item_name: str, action: str) -> str:
    """Manage inventory levels for an item."""
    return f"Inventory levels for {item_name} have been {action}."


async def conduct_supplier_survey(supplier_name: str) -> str:
    """Conduct a survey of a supplier."""
    return f"Survey of supplier {supplier_name} conducted."


async def get_procurement_information(
    query: Annotated[str, "The query for the procurement knowledgebase"]
) -> str:
    """Get procurement information, such as policies, procedures, and guidelines."""
    information = """
    Document Name: Contoso's Procurement Policies and Procedures
    Domain: Procurement Policy
    Description: Guidelines outlining the procurement processes for Contoso, including vendor selection, purchase orders, and asset management.

    Key points:
    - All hardware and software purchases must be approved by the procurement department.
    - For new employees, hardware requests (like laptops) and ID badges should be ordered through the procurement agent.
    - Software licenses should be managed to ensure compliance with vendor agreements.
    - Regular inventory checks should be conducted to maintain optimal stock levels.
    - Vendor relationships should be managed to achieve cost savings and ensure quality.
    """
    return information


# Create the ProcurementTools list
def get_procurement_tools() -> List[Tool]:
    ProcurementTools: List[Tool] = [
        FunctionTool(
            order_hardware,
            description="Order hardware items like laptops, monitors, etc.",
            name="order_hardware",
        ),
        FunctionTool(
            order_software_license,
            description="Order software licenses.",
            name="order_software_license",
        ),
        FunctionTool(
            check_inventory,
            description="Check the inventory status of an item.",
            name="check_inventory",
        ),
        FunctionTool(
            process_purchase_order,
            description="Process a purchase order.",
            name="process_purchase_order",
        ),
        FunctionTool(
            initiate_contract_negotiation,
            description="Initiate contract negotiation with a vendor.",
            name="initiate_contract_negotiation",
        ),
        FunctionTool(
            approve_invoice,
            description="Approve an invoice for payment.",
            name="approve_invoice",
        ),
        FunctionTool(
            track_order,
            description="Track the status of an order.",
            name="track_order",
        ),
        FunctionTool(
            manage_vendor_relationship,
            description="Manage relationships with vendors.",
            name="manage_vendor_relationship",
        ),
        FunctionTool(
            update_procurement_policy,
            description="Update a procurement policy.",
            name="update_procurement_policy",
        ),
        FunctionTool(
            generate_procurement_report,
            description="Generate a procurement report.",
            name="generate_procurement_report",
        ),
        FunctionTool(
            evaluate_supplier_performance,
            description="Evaluate the performance of a supplier.",
            name="evaluate_supplier_performance",
        ),
        FunctionTool(
            handle_return,
            description="Handle the return of procured items.",
            name="handle_return",
        ),
        FunctionTool(
            process_payment,
            description="Process payment to a vendor.",
            name="process_payment",
        ),
        FunctionTool(
            request_quote,
            description="Request a quote for items.",
            name="request_quote",
        ),
        FunctionTool(
            recommend_sourcing_options,
            description="Recommend sourcing options for an item.",
            name="recommend_sourcing_options",
        ),
        FunctionTool(
            update_asset_register,
            description="Update the asset register with new or disposed assets.",
            name="update_asset_register",
        ),
        FunctionTool(
            manage_leasing_agreements,
            description="Manage leasing agreements for assets.",
            name="manage_leasing_agreements",
        ),
        FunctionTool(
            conduct_market_research,
            description="Conduct market research for procurement purposes.",
            name="conduct_market_research",
        ),
        FunctionTool(
            get_procurement_information,
            description="Get procurement information, such as policies, procedures, and guidelines.",
            name="get_procurement_information",
        ),
        FunctionTool(
            schedule_maintenance,
            description="Schedule maintenance for equipment.",
            name="schedule_maintenance",
        ),
        FunctionTool(
            audit_inventory,
            description="Conduct an inventory audit.",
            name="audit_inventory",
        ),
        FunctionTool(
            approve_budget,
            description="Approve a procurement budget.",
            name="approve_budget",
        ),
        FunctionTool(
            manage_warranty,
            description="Manage warranties for procured items.",
            name="manage_warranty",
        ),
        FunctionTool(
            handle_customs_clearance,
            description="Handle customs clearance for international shipments.",
            name="handle_customs_clearance",
        ),
        FunctionTool(
            negotiate_discount,
            description="Negotiate a discount with a vendor.",
            name="negotiate_discount",
        ),
        FunctionTool(
            register_new_vendor,
            description="Register a new vendor.",
            name="register_new_vendor",
        ),
        FunctionTool(
            decommission_asset,
            description="Decommission an asset.",
            name="decommission_asset",
        ),
        FunctionTool(
            schedule_training,
            description="Schedule a training session for procurement staff.",
            name="schedule_training",
        ),
        FunctionTool(
            update_vendor_rating,
            description="Update the rating of a vendor.",
            name="update_vendor_rating",
        ),
        FunctionTool(
            handle_recall,
            description="Handle the recall of a procured item.",
            name="handle_recall",
        ),
        FunctionTool(
            request_samples,
            description="Request samples of an item.",
            name="request_samples",
        ),
        FunctionTool(
            manage_subscription,
            description="Manage subscriptions to services.",
            name="manage_subscription",
        ),
        FunctionTool(
            verify_supplier_certification,
            description="Verify the certification status of a supplier.",
            name="verify_supplier_certification",
        ),
        FunctionTool(
            conduct_supplier_audit,
            description="Conduct an audit of a supplier.",
            name="conduct_supplier_audit",
        ),
        FunctionTool(
            manage_import_licenses,
            description="Manage import licenses for items.",
            name="manage_import_licenses",
        ),
        FunctionTool(
            conduct_cost_analysis,
            description="Conduct a cost analysis for an item.",
            name="conduct_cost_analysis",
        ),
        FunctionTool(
            evaluate_risk_factors,
            description="Evaluate risk factors associated with procuring an item.",
            name="evaluate_risk_factors",
        ),
        FunctionTool(
            manage_green_procurement_policy,
            description="Manage green procurement policy.",
            name="manage_green_procurement_policy",
        ),
        FunctionTool(
            update_supplier_database,
            description="Update the supplier database with new information.",
            name="update_supplier_database",
        ),
        FunctionTool(
            handle_dispute_resolution,
            description="Handle dispute resolution with a vendor.",
            name="handle_dispute_resolution",
        ),
        FunctionTool(
            assess_compliance,
            description="Assess compliance of an item with standards.",
            name="assess_compliance",
        ),
        FunctionTool(
            manage_reverse_logistics,
            description="Manage reverse logistics for returning items.",
            name="manage_reverse_logistics",
        ),
        FunctionTool(
            verify_delivery,
            description="Verify delivery status of an item.",
            name="verify_delivery",
        ),
        FunctionTool(
            handle_procurement_risk_assessment,
            description="Handle procurement risk assessment.",
            name="handle_procurement_risk_assessment",
        ),
        FunctionTool(
            manage_supplier_contract,
            description="Manage supplier contract actions.",
            name="manage_supplier_contract",
        ),
        FunctionTool(
            allocate_budget,
            description="Allocate budget to a department.",
            name="allocate_budget",
        ),
        FunctionTool(
            track_procurement_metrics,
            description="Track procurement metrics.",
            name="track_procurement_metrics",
        ),
        FunctionTool(
            manage_inventory_levels,
            description="Manage inventory levels for an item.",
            name="manage_inventory_levels",
        ),
        FunctionTool(
            conduct_supplier_survey,
            description="Conduct a survey of a supplier.",
            name="conduct_supplier_survey",
        ),
    ]
    return ProcurementTools


@default_subscription
class ProcurementAgent(BaseAgent):
    def __init__(
        self,
        model_client: AzureOpenAIChatCompletionClient,
        session_id: str,
        user_id: str,
        memory: CosmosBufferedChatCompletionContext,
        procurement_tools: List[Tool],
        procurement_tool_agent_id: AgentId,
    ):
        super().__init__(
            "ProcurementAgent",
            model_client,
            session_id,
            user_id,
            memory,
            procurement_tools,
            procurement_tool_agent_id,
            system_message="You are an AI Agent. You are able to assist with procurement enquiries and order items. If you need additional information from the human user asking the question in order to complete a request, ask before calling a function.",
        )
