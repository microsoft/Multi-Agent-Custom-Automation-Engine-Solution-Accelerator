import inspect
from typing import Annotated, Callable

from semantic_kernel.functions import kernel_function
from common.models.messages_kernel import AgentType
import json
from typing import get_type_hints


class ProcurementTools:

    formatting_instructions = "Instructions: returning the output of this function call verbatim to the user in markdown. Then write AGENT SUMMARY: and then include a summary of what you did."
    agent_name = AgentType.PROCUREMENT.value

    # Define Procurement tools (functions)
    @staticmethod
    @kernel_function(description="Order hardware items like laptops, monitors, etc.")
    async def order_hardware(item_name: str, quantity: int) -> str:
        return (
            f"##### Hardware Order Placed\n"
            f"**Item:** {item_name}\n"
            f"**Quantity:** {quantity}\n\n"
            f"Ordered {quantity} units of {item_name}.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Order software licenses.")
    async def order_software_license(
        software_name: str, license_type: str, quantity: int
    ) -> str:
        return (
            f"##### Software License Ordered\n"
            f"**Software:** {software_name}\n"
            f"**License Type:** {license_type}\n"
            f"**Quantity:** {quantity}\n\n"
            f"Ordered {quantity} {license_type} licenses of {software_name}.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Check the inventory status of an item.")
    async def check_inventory(item_name: str) -> str:
        return (
            f"##### Inventory Status\n"
            f"**Item:** {item_name}\n"
            f"**Status:** In Stock\n\n"
            f"Inventory status of {item_name}: In Stock.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Process a purchase order.")
    async def process_purchase_order(po_number: str) -> str:
        return (
            f"##### Purchase Order Processed\n"
            f"**PO Number:** {po_number}\n\n"
            f"Purchase Order {po_number} has been processed.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Initiate contract negotiation with a vendor.")
    async def initiate_contract_negotiation(
        vendor_name: str, contract_details: str
    ) -> str:
        return (
            f"##### Contract Negotiation Initiated\n"
            f"**Vendor:** {vendor_name}\n"
            f"**Contract Details:** {contract_details}\n\n"
            f"Contract negotiation initiated with {vendor_name}: {contract_details}\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Approve an invoice for payment.")
    async def approve_invoice(invoice_number: str) -> str:
        return (
            f"##### Invoice Approved\n"
            f"**Invoice Number:** {invoice_number}\n\n"
            f"Invoice {invoice_number} approved for payment.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Track the status of an order.")
    async def track_order(order_number: str) -> str:
        return (
            f"##### Order Tracking\n"
            f"**Order Number:** {order_number}\n"
            f"**Status:** In Transit\n\n"
            f"Order {order_number} is currently in transit.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Manage relationships with vendors.")
    async def manage_vendor_relationship(vendor_name: str, action: str) -> str:
        return (
            f"##### Vendor Relationship Update\n"
            f"**Vendor:** {vendor_name}\n"
            f"**Action:** {action}\n\n"
            f"Vendor relationship with {vendor_name} has been {action}.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Update a procurement policy.")
    async def update_procurement_policy(policy_name: str, policy_content: str) -> str:
        return (
            f"##### Procurement Policy Updated\n"
            f"**Policy:** {policy_name}\n\n"
            f"Procurement policy '{policy_name}' updated.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Generate a procurement report.")
    async def generate_procurement_report(report_type: str) -> str:
        return (
            f"##### Procurement Report Generated\n"
            f"**Report Type:** {report_type}\n\n"
            f"Generated {report_type} procurement report.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Evaluate the performance of a supplier.")
    async def evaluate_supplier_performance(supplier_name: str) -> str:
        return (
            f"##### Supplier Performance Evaluation\n"
            f"**Supplier:** {supplier_name}\n\n"
            f"Performance evaluation for supplier {supplier_name} completed.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Handle the return of procured items.")
    async def handle_return(item_name: str, quantity: int, reason: str) -> str:
        return (
            f"##### Return Handled\n"
            f"**Item:** {item_name}\n"
            f"**Quantity:** {quantity}\n"
            f"**Reason:** {reason}\n\n"
            f"Processed return of {quantity} units of {item_name} due to {reason}.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Process payment to a vendor.")
    async def process_payment(vendor_name: str, amount: float) -> str:
        return (
            f"##### Payment Processed\n"
            f"**Vendor:** {vendor_name}\n"
            f"**Amount:** ${amount:.2f}\n\n"
            f"Processed payment of ${amount:.2f} to {vendor_name}.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Request a quote for items.")
    async def request_quote(item_name: str, quantity: int) -> str:
        return (
            f"##### Quote Requested\n"
            f"**Item:** {item_name}\n"
            f"**Quantity:** {quantity}\n\n"
            f"Requested quote for {quantity} units of {item_name}.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Recommend sourcing options for an item.")
    async def recommend_sourcing_options(item_name: str) -> str:
        return (
            f"##### Sourcing Options\n"
            f"**Item:** {item_name}\n\n"
            f"Sourcing options for {item_name} have been provided.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(
        description="Update the asset register with new or disposed assets."
    )
    async def update_asset_register(asset_name: str, asset_details: str) -> str:
        return (
            f"##### Asset Register Updated\n"
            f"**Asset:** {asset_name}\n"
            f"**Details:** {asset_details}\n\n"
            f"Asset register updated for {asset_name}: {asset_details}\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Manage leasing agreements for assets.")
    async def manage_leasing_agreements(agreement_details: str) -> str:
        return (
            f"##### Leasing Agreement Managed\n"
            f"**Agreement Details:** {agreement_details}\n\n"
            f"Leasing agreement processed: {agreement_details}\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Conduct market research for procurement purposes.")
    async def conduct_market_research(category: str) -> str:
        return (
            f"##### Market Research Conducted\n"
            f"**Category:** {category}\n\n"
            f"Market research conducted for category: {category}\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Schedule maintenance for equipment.")
    async def schedule_maintenance(equipment_name: str, maintenance_date: str) -> str:
        return (
            f"##### Maintenance Scheduled\n"
            f"**Equipment:** {equipment_name}\n"
            f"**Date:** {maintenance_date}\n\n"
            f"Scheduled maintenance for {equipment_name} on {maintenance_date}.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Conduct an inventory audit.")
    async def audit_inventory() -> str:
        return (
            f"##### Inventory Audit\n\n"
            f"Inventory audit has been conducted.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Approve a procurement budget.")
    async def approve_budget(budget_id: str, amount: float) -> str:
        return (
            f"##### Budget Approved\n"
            f"**Budget ID:** {budget_id}\n"
            f"**Amount:** ${amount:.2f}\n\n"
            f"Approved budget ID {budget_id} for amount ${amount:.2f}.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Manage warranties for procured items.")
    async def manage_warranty(item_name: str, warranty_period: str) -> str:
        return (
            f"##### Warranty Management\n"
            f"**Item:** {item_name}\n"
            f"**Warranty Period:** {warranty_period}\n\n"
            f"Warranty for {item_name} managed for period {warranty_period}.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(
        description="Handle customs clearance for international shipments."
    )
    async def handle_customs_clearance(shipment_id: str) -> str:
        return (
            f"##### Customs Clearance\n"
            f"**Shipment ID:** {shipment_id}\n\n"
            f"Customs clearance for shipment ID {shipment_id} handled.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Negotiate a discount with a vendor.")
    async def negotiate_discount(vendor_name: str, discount_percentage: float) -> str:
        return (
            f"##### Discount Negotiated\n"
            f"**Vendor:** {vendor_name}\n"
            f"**Discount:** {discount_percentage}%\n\n"
            f"Negotiated a {discount_percentage}% discount with vendor {vendor_name}.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Register a new vendor.")
    async def register_new_vendor(vendor_name: str, vendor_details: str) -> str:
        return (
            f"##### New Vendor Registered\n"
            f"**Vendor:** {vendor_name}\n"
            f"**Details:** {vendor_details}\n\n"
            f"New vendor {vendor_name} registered with details: {vendor_details}.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Decommission an asset.")
    async def decommission_asset(asset_name: str) -> str:
        return (
            f"##### Asset Decommissioned\n"
            f"**Asset:** {asset_name}\n\n"
            f"Asset {asset_name} has been decommissioned.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Schedule a training session for procurement staff.")
    async def schedule_training(session_name: str, date: str) -> str:
        return (
            f"##### Training Session Scheduled\n"
            f"**Session:** {session_name}\n"
            f"**Date:** {date}\n\n"
            f"Training session '{session_name}' scheduled on {date}.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Update the rating of a vendor.")
    async def update_vendor_rating(vendor_name: str, rating: float) -> str:
        return (
            f"##### Vendor Rating Updated\n"
            f"**Vendor:** {vendor_name}\n"
            f"**Rating:** {rating}\n\n"
            f"Vendor {vendor_name} rating updated to {rating}.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Handle the recall of a procured item.")
    async def handle_recall(item_name: str, recall_reason: str) -> str:
        return (
            f"##### Item Recall Handled\n"
            f"**Item:** {item_name}\n"
            f"**Reason:** {recall_reason}\n\n"
            f"Recall of {item_name} due to {recall_reason} handled.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Request samples of an item.")
    async def request_samples(item_name: str, quantity: int) -> str:
        return (
            f"##### Samples Requested\n"
            f"**Item:** {item_name}\n"
            f"**Quantity:** {quantity}\n\n"
            f"Requested {quantity} samples of {item_name}.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Manage subscriptions to services.")
    async def manage_subscription(service_name: str, action: str) -> str:
        return (
            f"##### Subscription Management\n"
            f"**Service:** {service_name}\n"
            f"**Action:** {action}\n\n"
            f"Subscription to {service_name} has been {action}.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Verify the certification status of a supplier.")
    async def verify_supplier_certification(supplier_name: str) -> str:
        return (
            f"##### Supplier Certification Verified\n"
            f"**Supplier:** {supplier_name}\n\n"
            f"Certification status of supplier {supplier_name} verified.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Conduct an audit of a supplier.")
    async def conduct_supplier_audit(supplier_name: str) -> str:
        return (
            f"##### Supplier Audit Conducted\n"
            f"**Supplier:** {supplier_name}\n\n"
            f"Audit of supplier {supplier_name} conducted.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Manage import licenses for items.")
    async def manage_import_licenses(item_name: str, license_details: str) -> str:
        return (
            f"##### Import License Management\n"
            f"**Item:** {item_name}\n"
            f"**License Details:** {license_details}\n\n"
            f"Import license for {item_name} managed: {license_details}.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Conduct a cost analysis for an item.")
    async def conduct_cost_analysis(item_name: str) -> str:
        return (
            f"##### Cost Analysis Conducted\n"
            f"**Item:** {item_name}\n\n"
            f"Cost analysis for {item_name} conducted.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(
        description="Evaluate risk factors associated with procuring an item."
    )
    async def evaluate_risk_factors(item_name: str) -> str:
        return (
            f"##### Risk Factors Evaluated\n"
            f"**Item:** {item_name}\n\n"
            f"Risk factors for {item_name} evaluated.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Manage green procurement policy.")
    async def manage_green_procurement_policy(policy_details: str) -> str:
        return (
            f"##### Green Procurement Policy Management\n"
            f"**Details:** {policy_details}\n\n"
            f"Green procurement policy managed: {policy_details}.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Update the supplier database with new information.")
    async def update_supplier_database(supplier_name: str, supplier_info: str) -> str:
        return (
            f"##### Supplier Database Updated\n"
            f"**Supplier:** {supplier_name}\n"
            f"**Information:** {supplier_info}\n\n"
            f"Supplier database updated for {supplier_name}: {supplier_info}.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Handle dispute resolution with a vendor.")
    async def handle_dispute_resolution(vendor_name: str, issue: str) -> str:
        return (
            f"##### Dispute Resolution\n"
            f"**Vendor:** {vendor_name}\n"
            f"**Issue:** {issue}\n\n"
            f"Dispute with vendor {vendor_name} over issue '{issue}' resolved.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Assess compliance of an item with standards.")
    async def assess_compliance(item_name: str, compliance_standards: str) -> str:
        return (
            f"##### Compliance Assessment\n"
            f"**Item:** {item_name}\n"
            f"**Standards:** {compliance_standards}\n\n"
            f"Compliance of {item_name} with standards '{compliance_standards}' assessed.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Manage reverse logistics for returning items.")
    async def manage_reverse_logistics(item_name: str, quantity: int) -> str:
        return (
            f"##### Reverse Logistics Management\n"
            f"**Item:** {item_name}\n"
            f"**Quantity:** {quantity}\n\n"
            f"Reverse logistics managed for {quantity} units of {item_name}.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Verify delivery status of an item.")
    async def verify_delivery(item_name: str, delivery_status: str) -> str:
        return (
            f"##### Delivery Status Verification\n"
            f"**Item:** {item_name}\n"
            f"**Status:** {delivery_status}\n\n"
            f"Delivery status of {item_name} verified as {delivery_status}.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="assess procurement risk assessment.")
    async def assess_procurement_risk(risk_details: str) -> str:
        return (
            f"##### Procurement Risk Assessment\n"
            f"**Details:** {risk_details}\n\n"
            f"Procurement risk assessment handled: {risk_details}.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Manage supplier contract actions.")
    async def manage_supplier_contract(supplier_name: str, contract_action: str) -> str:
        return (
            f"##### Supplier Contract Management\n"
            f"**Supplier:** {supplier_name}\n"
            f"**Action:** {contract_action}\n\n"
            f"Supplier contract with {supplier_name} has been {contract_action}.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Allocate budget to a department.")
    async def allocate_budget(department_name: str, budget_amount: float) -> str:
        return (
            f"##### Budget Allocation\n"
            f"**Department:** {department_name}\n"
            f"**Amount:** ${budget_amount:.2f}\n\n"
            f"Allocated budget of ${budget_amount:.2f} to {department_name}.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Track procurement metrics.")
    async def track_procurement_metrics(metric_name: str) -> str:
        return (
            f"##### Procurement Metrics Tracking\n"
            f"**Metric:** {metric_name}\n\n"
            f"Procurement metric '{metric_name}' tracked.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Manage inventory levels for an item.")
    async def manage_inventory_levels(item_name: str, action: str) -> str:
        return (
            f"##### Inventory Level Management\n"
            f"**Item:** {item_name}\n"
            f"**Action:** {action}\n\n"
            f"Inventory levels for {item_name} have been {action}.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(description="Conduct a survey of a supplier.")
    async def conduct_supplier_survey(supplier_name: str) -> str:
        return (
            f"##### Supplier Survey Conducted\n"
            f"**Supplier:** {supplier_name}\n\n"
            f"Survey of supplier {supplier_name} conducted.\n"
            f"{ProcurementTools.formatting_instructions}"
        )

    @staticmethod
    @kernel_function(
        description="Get procurement information, such as policies, procedures, and guidelines."
    )
    async def get_procurement_information(
        query: Annotated[str, "The query for the procurement knowledgebase"],
    ) -> str:
        information = (
            f"##### Procurement Information\n\n"
            f"**Document Name:** Contoso's Procurement Policies and Procedures\n"
            f"**Domain:** Procurement Policy\n"
            f"**Description:** Guidelines outlining the procurement processes for Contoso, including vendor selection, purchase orders, and asset management.\n\n"
            f"**Key points:**\n"
            f"- All hardware and software purchases must be approved by the procurement department.\n"
            f"- For new employees, hardware requests (like laptops) and ID badges should be ordered through the procurement agent.\n"
            f"- Software licenses should be managed to ensure compliance with vendor agreements.\n"
            f"- Regular inventory checks should be conducted to maintain optimal stock levels.\n"
            f"- Vendor relationships should be managed to achieve cost savings and ensure quality.\n"
            f"{ProcurementTools.formatting_instructions}"
        )
        return information

    @classmethod
    def generate_tools_json_doc(cls) -> str:
        """
        Generate a JSON document containing information about all methods in the class.

        Returns:
            str: JSON string containing the methods' information
        """

        tools_list = []

        # Get all methods from the class that have the kernel_function annotation
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            # Skip this method itself and any private methods
            if name.startswith("_") or name == "generate_tools_json_doc":
                continue

            # Check if the method has the kernel_function annotation
            if hasattr(method, "__kernel_function__"):
                # Get method description from docstring or kernel_function description
                description = ""
                if hasattr(method, "__doc__") and method.__doc__:
                    description = method.__doc__.strip()

                # Get kernel_function description if available
                if hasattr(method, "__kernel_function__") and getattr(
                    method.__kernel_function__, "description", None
                ):
                    description = method.__kernel_function__.description

                # Get argument information by introspection
                sig = inspect.signature(method)
                args_dict = {}

                # Get type hints if available
                type_hints = get_type_hints(method)

                # Process parameters
                for param_name, param in sig.parameters.items():
                    # Skip first parameter 'cls' for class methods (though we're using staticmethod now)
                    if param_name in ["cls", "self"]:
                        continue

                    # Get parameter type
                    param_type = "string"  # Default type
                    if param_name in type_hints:
                        type_obj = type_hints[param_name]
                        # Convert type to string representation
                        if hasattr(type_obj, "__name__"):
                            param_type = type_obj.__name__.lower()
                        else:
                            # Handle complex types like List, Dict, etc.
                            param_type = str(type_obj).lower()
                            if "int" in param_type:
                                param_type = "int"
                            elif "float" in param_type:
                                param_type = "float"
                            elif "bool" in param_type:
                                param_type = "boolean"
                            else:
                                param_type = "string"

                    # Create parameter description
                    # param_desc = param_name.replace("_", " ")
                    args_dict[param_name] = {
                        "description": param_name,
                        "title": param_name.replace("_", " ").title(),
                        "type": param_type,
                    }

                # Add the tool information to the list
                tool_entry = {
                    "agent": cls.agent_name,  # Use HR agent type
                    "function": name,
                    "description": description,
                    "arguments": json.dumps(args_dict).replace('"', "'"),
                }

                tools_list.append(tool_entry)

        # Return the JSON string representation
        return json.dumps(tools_list, ensure_ascii=False, indent=2)

    # This function does NOT have the kernel_function annotation
    # because it's meant for introspection rather than being exposed as a tool
    @classmethod
    def get_all_kernel_functions(cls) -> dict[str, Callable]:
        """
        Returns a dictionary of all methods in this class that have the @kernel_function annotation.
        This function itself is not annotated with @kernel_function.

        Returns:
            Dict[str, Callable]: Dictionary with function names as keys and function objects as values
        """
        kernel_functions = {}

        # Get all class methods
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            # Skip this method itself and any private/special methods
            if name.startswith("_") or name == "get_all_kernel_functions":
                continue

            # Check if the method has the kernel_function annotation
            # by looking at its __annotations__ attribute
            method_attrs = getattr(method, "__annotations__", {})
            if hasattr(method, "__kernel_function__") or "kernel_function" in str(
                method_attrs
            ):
                kernel_functions[name] = method

        return kernel_functions
