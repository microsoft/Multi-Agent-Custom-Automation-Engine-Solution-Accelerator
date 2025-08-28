"""ProductTools class for managing product-related tasks in a mobile plan context."""

import inspect
import time
from typing import Annotated, Callable, List

from semantic_kernel.functions import kernel_function
from models.messages_kernel import AgentType
import json
from typing import get_type_hints
from utils_date import format_date_for_user
from app_config import config


class ProductTools:
    """Define Product Agent functions (tools)"""

    agent_name = AgentType.PRODUCT.value
    selecetd_language = config.get_user_local_browser_language()

    @staticmethod
    @kernel_function(
        description="Add an extras pack/new product to the mobile plan for the customer. For example, adding a roaming plan to their service. Convert all date strings in the following text to short date format with 3-letter month (MMM) in the {selecetd_language} locale (e.g., en-US, en-IN), remove time, and replace original dates with the formatted ones"
    )
    async def add_mobile_extras_pack(new_extras_pack_name: str, start_date: str) -> str:
        """Add an extras pack/new product to the mobile plan for the customer. For example, adding a roaming plan to their service. The arguments should include the new_extras_pack_name and the start_date as strings. You must provide the exact plan name, as found using the get_product_info() function."""
        formatting_instructions = "Instructions: returning the output of this function call verbatim to the user in markdown. Then write AGENT SUMMARY: and then include a summary of what you did."
        analysis = (
            f"# Request to Add Extras Pack to Mobile Plan\n"
            f"## New Plan:\n{new_extras_pack_name}\n"
            f"## Start Date:\n{start_date}\n\n"
            f"These changes have been completed and should be reflected in your app in 5-10 minutes."
            f"\n\n{formatting_instructions}"
        )
        time.sleep(2)
        return analysis

    @staticmethod
    @kernel_function(
        description="Get information about available products and phone plans, including roaming services."
    )
    async def get_product_info() -> str:
        # This is a placeholder function, for a proper Azure AI Search RAG process.

        """Get information about the different products and phone plans available, including roaming services."""
        product_info = """

        # Simulated Phone Plans

        ## Plan A: Basic Saver
        - **Monthly Cost**: $25
        - **Data**: 5GB
        - **Calls**: Unlimited local calls
        - **Texts**: Unlimited local texts

        ## Plan B: Standard Plus
        - **Monthly Cost**: $45
        - **Data**: 15GB
        - **Calls**: Unlimited local and national calls
        - **Texts**: Unlimited local and national texts

        ## Plan C: Premium Unlimited
        - **Monthly Cost**: $70
        - **Data**: Unlimited
        - **Calls**: Unlimited local, national, and international calls
        - **Texts**: Unlimited local, national, and international texts

        # Roaming Extras Add-On Pack
        - **Cost**: $15/month
        - **Data**: 1GB
        - **Calls**: 200 minutes
        - **Texts**: 200 texts

        """
        return f"Here is information to relay back to the user. Repeat back all the relevant sections that the user asked for: {product_info}."

    # @staticmethod
    # @kernel_function(
    #     description="Retrieve the customer's recurring billing date information."
    # )
    # async def get_billing_date() -> str:
    #     """Get information about the recurring billing date."""
    #     now = datetime.now()
    #     start_of_month = datetime(now.year, now.month, 1)
    #     start_of_month_string = start_of_month.strftime("%Y-%m-%d")
    #     formatted_date = format_date_for_user(start_of_month_string)
    #     return f"## Billing Date\nYour most recent billing date was **{formatted_date}**."

    @staticmethod
    @kernel_function(
        description="Check the current inventory level for a specified product."
    )
    async def check_inventory(product_name: str) -> str:
        """Check the inventory level for a specific product."""
        inventory_status = (
            f"## Inventory Status\nInventory status for **'{product_name}'** checked."
        )
        return inventory_status

    @staticmethod
    @kernel_function(
        description="Update the inventory quantity for a specified product."
    )
    async def update_inventory(product_name: str, quantity: int) -> str:
        """Update the inventory quantity for a specific product."""
        message = f"## Inventory Update\nInventory for **'{product_name}'** updated by **{quantity}** units."

        return message

    @staticmethod
    @kernel_function(
        description="Add a new product to the inventory system with detailed product information."
    )
    async def add_new_product(
        product_details: Annotated[str, "Details of the new product"],
    ) -> str:
        """Add a new product to the inventory."""
        message = f"## New Product Added\nNew product added with details:\n\n{product_details}"

        return message

    # @staticmethod
    # @kernel_function(
    #     description="Update the price of a specified product in the system."
    # )
    # async def update_product_price(product_name: str, price: float) -> str:
    #     """Update the price of a specific product."""
    #     message = f"## Price Update\nPrice for **'{product_name}'** updated to **${price:.2f}**."

    #     return message

    @staticmethod
    @kernel_function(description="Schedule a product launch event on a specific date.")
    async def schedule_product_launch(product_name: str, launch_date: str) -> str:
        """Schedule a product launch on a specific date."""
        formatted_date = format_date_for_user(launch_date)
        message = f"## Product Launch Scheduled\nProduct **'{product_name}'** launch scheduled on **{formatted_date}**."

        return message

    # @staticmethod
    # @kernel_function(
    #     description="Analyze sales data for a product over a specified time period."
    # )
    # async def analyze_sales_data(product_name: str, time_period: str) -> str:
    #     """Analyze sales data for a product over a given time period."""
    #     analysis = f"## Sales Data Analysis\nSales data for **'{product_name}'** over **{time_period}** analyzed."

    #     return analysis

    # @staticmethod
    # @kernel_function(description="Retrieve customer feedback for a specified product.")
    # async def get_customer_feedback(product_name: str) -> str:
    #     """Retrieve customer feedback for a specific product."""
    #     feedback = f"## Customer Feedback\nCustomer feedback for **'{product_name}'** retrieved."

    #     return feedback

    @staticmethod
    @kernel_function(
        description="Manage promotional activities for a specified product."
    )
    async def manage_promotions(
        product_name: str,
        promotion_details: Annotated[str, "Details of the promotion"],
    ) -> str:
        """Manage promotions for a specific product."""
        message = f"## Promotion Managed\nPromotion for **'{product_name}'** managed with details:\n\n{promotion_details}"

        return message

    @staticmethod
    @kernel_function(
        description="Coordinate with the marketing team for product campaign activities."
    )
    async def coordinate_with_marketing(
        product_name: str,
        campaign_details: Annotated[str, "Details of the marketing campaign"],
    ) -> str:
        """Coordinate with the marketing team for a product."""
        message = f"## Marketing Coordination\nCoordinated with marketing for **'{product_name}'** campaign:\n\n{campaign_details}"

        return message

    # @staticmethod
    # @kernel_function(
    #     description="Review and assess the quality of a specified product."
    # )
    # async def review_product_quality(product_name: str) -> str:
    #     """Review the quality of a specific product."""
    #     review = (
    #         f"## Quality Review\nQuality review for **'{product_name}'** completed."
    #     )

    #     return review

    @staticmethod
    @kernel_function(
        description="Initiate and manage a product recall for a specified product."
    )
    async def handle_product_recall(product_name: str, recall_reason: str) -> str:
        """Handle a product recall for a specific product."""
        message = f"## Product Recall\nProduct recall for **'{product_name}'** initiated due to:\n\n{recall_reason}"

        return message

    # @staticmethod
    # @kernel_function(
    #     description="Provide product recommendations based on customer preferences."
    # )
    # async def provide_product_recommendations(
    #     customer_preferences: Annotated[str, "Customer preferences or requirements"],
    # ) -> str:
    #     """Provide product recommendations based on customer preferences."""
    #     recommendations = f"## Product Recommendations\nProduct recommendations based on preferences **'{customer_preferences}'** provided."

    #     return recommendations

    @staticmethod
    @kernel_function(description="Generate a detailed report for a specified product.")
    async def generate_product_report(product_name: str, report_type: str) -> str:
        """Generate a report for a specific product."""
        report = f"## {report_type} Report\n{report_type} report for **'{product_name}'** generated."

        return report

    # @staticmethod
    # @kernel_function(
    #     description="Manage supply chain activities for a specified product with a particular supplier."
    # )
    # async def manage_supply_chain(product_name: str, supplier_name: str) -> str:
    #     """Manage supply chain activities for a specific product."""
    #     message = f"## Supply Chain Management\nSupply chain for **'{product_name}'** managed with supplier **'{supplier_name}'**."

    #     return message

    # @staticmethod
    # @kernel_function(
    #     description="Track the shipment status of a specified product using a tracking number."
    # )
    # async def track_product_shipment(product_name: str, tracking_number: str) -> str:
    #     """Track the shipment of a specific product."""
    #     status = f"## Shipment Tracking\nShipment for **'{product_name}'** with tracking number **'{tracking_number}'** tracked."

    #     return status

    # @staticmethod
    # @kernel_function(
    #     description="Set the reorder threshold level for a specified product."
    # )
    # async def set_reorder_level(product_name: str, reorder_level: int) -> str:
    #     """Set the reorder level for a specific product."""
    #     message = f"## Reorder Level Set\nReorder level for **'{product_name}'** set to **{reorder_level}** units."

    #     return message

    @staticmethod
    @kernel_function(
        description="Monitor and analyze current market trends relevant to product lines."
    )
    async def monitor_market_trends() -> str:
        """Monitor market trends relevant to products."""
        trends = "## Market Trends\nMarket trends monitored and data updated."

        return trends

    @staticmethod
    @kernel_function(description="Develop and document new product ideas and concepts.")
    async def develop_new_product_ideas(
        idea_details: Annotated[str, "Details of the new product idea"],
    ) -> str:
        """Develop new product ideas."""
        message = f"## New Product Idea\nNew product idea developed:\n\n{idea_details}"

        return message

    @staticmethod
    @kernel_function(
        description="Collaborate with the technical team for product development and specifications."
    )
    async def collaborate_with_tech_team(
        product_name: str,
        collaboration_details: Annotated[str, "Details of the technical requirements"],
    ) -> str:
        """Collaborate with the tech team for product development."""
        message = f"## Tech Team Collaboration\nCollaborated with tech team on **'{product_name}'**:\n\n{collaboration_details}"

        return message

    # @staticmethod
    # @kernel_function(
    #     description="Update the description information for a specified product."
    # )
    # async def update_product_description(product_name: str, description: str) -> str:
    #     """Update the description of a specific product."""
    #     message = f"## Product Description Updated\nDescription for **'{product_name}'** updated to:\n\n{description}"

    #     return message

    # @staticmethod
    # @kernel_function(description="Set a percentage discount for a specified product.")
    # async def set_product_discount(
    #     product_name: str, discount_percentage: float
    # ) -> str:
    #     """Set a discount for a specific product."""
    #     message = f"## Discount Set\nDiscount for **'{product_name}'** set to **{discount_percentage}%**."

    #     return message

    # @staticmethod
    # @kernel_function(
    #     description="Process and manage product returns with detailed reason tracking."
    # )
    # async def manage_product_returns(product_name: str, return_reason: str) -> str:
    #     """Manage returns for a specific product."""
    #     message = f"## Product Return Managed\nReturn for **'{product_name}'** managed due to:\n\n{return_reason}"

    #     return message

    # @staticmethod
    # @kernel_function(description="Conduct a customer survey about a specified product.")
    # async def conduct_product_survey(product_name: str, survey_details: str) -> str:
    #     """Conduct a survey for a specific product."""
    #     message = f"## Product Survey Conducted\nSurvey for **'{product_name}'** conducted with details:\n\n{survey_details}"

    #     return message

    # @staticmethod
    # @kernel_function(
    #     description="Handle and process customer complaints about a specified product."
    # )
    # async def handle_product_complaints(
    #     product_name: str, complaint_details: str
    # ) -> str:
    #     """Handle complaints for a specific product."""
    #     message = f"## Product Complaint Handled\nComplaint for **'{product_name}'** handled with details:\n\n{complaint_details}"

    #     return message

    # @staticmethod
    # @kernel_function(
    #     description="Update the technical specifications for a specified product."
    # )
    # async def update_product_specifications(
    #     product_name: str, specifications: str
    # ) -> str:
    #     """Update the specifications for a specific product."""
    #     message = f"## Product Specifications Updated\nSpecifications for **'{product_name}'** updated to:\n\n{specifications}"

    #     return message

    @staticmethod
    @kernel_function(
        description="Organize and schedule a photoshoot for a specified product."
    )
    async def organize_product_photoshoot(
        product_name: str, photoshoot_date: str
    ) -> str:
        """Organize a photoshoot for a specific product."""
        message = f"## Product Photoshoot Organized\nPhotoshoot for **'{product_name}'** organized on **{photoshoot_date}**."

        return message

    @staticmethod
    @kernel_function(
        description="Manage the e-commerce platform listings for a specified product."
    )
    async def manage_product_listing(product_name: str, listing_details: str) -> str:
        """Manage the listing of a specific product on e-commerce platforms."""
        message = f"## Product Listing Managed\nListing for **'{product_name}'** managed with details:\n\n{listing_details}"

        return message

    # @staticmethod
    # @kernel_function(description="Set the availability status of a specified product.")
    # async def set_product_availability(product_name: str, availability: bool) -> str:
    #     """Set the availability status of a specific product."""
    #     status = "available" if availability else "unavailable"
    #     message = f"## Product Availability Set\nProduct **'{product_name}'** is now **{status}**."

    #     return message

    @staticmethod
    @kernel_function(
        description="Coordinate logistics operations for a specified product."
    )
    async def coordinate_with_logistics(
        product_name: str, logistics_details: str
    ) -> str:
        """Coordinate with the logistics team for a specific product."""
        message = f"## Logistics Coordination\nCoordinated with logistics for **'{product_name}'** with details:\n\n{logistics_details}"

        return message

    # @staticmethod
    # @kernel_function(
    #     description="Calculate the profit margin for a specified product using cost and selling prices."
    # )
    # async def calculate_product_margin(
    #     product_name: str, cost_price: float, selling_price: float
    # ) -> str:
    #     """Calculate the profit margin for a specific product."""
    #     margin = ((selling_price - cost_price) / selling_price) * 100
    #     message = f"## Profit Margin Calculated\nProfit margin for **'{product_name}'** calculated at **{margin:.2f}%**."

    #     return message

    @staticmethod
    @kernel_function(
        description="Update the category classification for a specified product."
    )
    async def update_product_category(product_name: str, category: str) -> str:
        """Update the category of a specific product."""
        message = f"## Product Category Updated\nCategory for **'{product_name}'** updated to:\n\n{category}"

        return message

    # @staticmethod
    # @kernel_function(
    #     description="Create and manage product bundles with multiple products."
    # )
    # async def manage_product_bundles(bundle_name: str, product_list: List[str]) -> str:
    #     """Manage product bundles."""
    #     products = ", ".join(product_list)
    #     message = f"## Product Bundle Managed\nProduct bundle **'{bundle_name}'** managed with products:\n\n{products}"

    #     return message

    # @staticmethod
    # @kernel_function(
    #     description="Optimize the product page for better user experience and performance."
    # )
    # async def optimize_product_page(
    #     product_name: str, optimization_details: str
    # ) -> str:
    #     """Optimize the product page for better performance."""
    #     message = f"## Product Page Optimized\nProduct page for **'{product_name}'** optimized with details:\n\n{optimization_details}"

    #     return message

    # @staticmethod
    # @kernel_function(
    #     description="Monitor and track performance metrics for a specified product."
    # )
    # async def monitor_product_performance(product_name: str) -> str:
    #     """Monitor the performance of a specific product."""
    #     message = f"## Product Performance Monitored\nPerformance for **'{product_name}'** monitored."

    #     return message

    @staticmethod
    @kernel_function(
        description="Implement pricing strategies for a specified product."
    )
    async def handle_product_pricing(product_name: str, pricing_strategy: str) -> str:
        """Handle pricing strategy for a specific product."""
        message = f"## Pricing Strategy Set\nPricing strategy for **'{product_name}'** set to:\n\n{pricing_strategy}"

        return message

    @staticmethod
    @kernel_function(description="Develop training materials for a specified product.")
    async def create_training_material(
        product_name: str, training_material: str
    ) -> str:
        """Develop training material for a specific product."""
        message = f"## Training Material Developed\nTraining material for **'{product_name}'** developed:\n\n{training_material}"

        return message

    # @staticmethod
    # @kernel_function(
    #     description="Update the labeling information for a specified product."
    # )
    # async def update_product_labels(product_name: str, label_details: str) -> str:
    #     """Update labels for a specific product."""
    #     message = f"## Product Labels Updated\nLabels for **'{product_name}'** updated with details:\n\n{label_details}"

    #     return message

    # @staticmethod
    # @kernel_function(
    #     description="Manage warranty terms and conditions for a specified product."
    # )
    # async def manage_product_warranty(product_name: str, warranty_details: str) -> str:
    #     """Manage the warranty for a specific product."""
    #     message = f"## Product Warranty Managed\nWarranty for **'{product_name}'** managed with details:\n\n{warranty_details}"

    #     return message

    # @staticmethod
    # @kernel_function(
    #     description="Forecast future demand for a specified product over a time period."
    # )
    # async def forecast_product_demand(product_name: str, forecast_period: str) -> str:
    #     """Forecast demand for a specific product."""
    #     message = f"## Demand Forecast\nDemand for **'{product_name}'** forecasted for **{forecast_period}**."

    #     return message

    # @staticmethod
    # @kernel_function(
    #     description="Handle licensing agreements and requirements for a specified product."
    # )
    # async def handle_product_licensing(
    #     product_name: str, licensing_details: str
    # ) -> str:
    #     """Handle licensing for a specific product."""
    #     message = f"## Product Licensing Handled\nLicensing for **'{product_name}'** handled with details:\n\n{licensing_details}"

    #     return message

    @staticmethod
    @kernel_function(
        description="Manage packaging specifications and designs for a specified product."
    )
    async def manage_product_packaging(
        product_name: str, packaging_details: str
    ) -> str:
        """Manage packaging for a specific product."""
        message = f"## Product Packaging Managed\nPackaging for **'{product_name}'** managed with details:\n\n{packaging_details}"

        return message

    @staticmethod
    @kernel_function(
        description="Set safety standards and compliance requirements for a specified product."
    )
    async def set_product_safety_standards(
        product_name: str, safety_standards: str
    ) -> str:
        """Set safety standards for a specific product."""
        message = f"## Safety Standards Set\nSafety standards for **'{product_name}'** set to:\n\n{safety_standards}"

        return message

    @staticmethod
    @kernel_function(
        description="Develop and implement new features for a specified product."
    )
    async def develop_product_features(product_name: str, features_details: str) -> str:
        """Develop new features for a specific product."""
        message = f"## New Features Developed\nNew features for **'{product_name}'** developed with details:\n\n{features_details}"

        return message

    @staticmethod
    @kernel_function(
        description="Evaluate product performance based on specified criteria."
    )
    async def evaluate_product_performance(
        product_name: str, evaluation_criteria: str
    ) -> str:
        """Evaluate the performance of a specific product."""
        message = f"## Product Performance Evaluated\nPerformance of **'{product_name}'** evaluated based on:\n\n{evaluation_criteria}"

        return message

    @staticmethod
    @kernel_function(
        description="Manage custom product orders with specific customer requirements."
    )
    async def manage_custom_product_orders(order_details: str) -> str:
        """Manage custom orders for a specific product."""
        message = f"## Custom Product Order Managed\nCustom product order managed with details:\n\n{order_details}"

        return message

    @staticmethod
    @kernel_function(
        description="Update the product images for a specified product with new image URLs."
    )
    async def update_product_images(product_name: str, image_urls: List[str]) -> str:
        """Update images for a specific product."""
        images = ", ".join(image_urls)
        message = f"## Product Images Updated\nImages for **'{product_name}'** updated:\n\n{images}"

        return message

    @staticmethod
    @kernel_function(
        description="Handle product obsolescence and end-of-life procedures for a specified product."
    )
    async def handle_product_obsolescence(product_name: str) -> str:
        """Handle the obsolescence of a specific product."""
        message = f"## Product Obsolescence Handled\nObsolescence for **'{product_name}'** handled."

        return message

    @staticmethod
    @kernel_function(
        description="Manage stock keeping unit (SKU) information for a specified product."
    )
    async def manage_product_sku(product_name: str, sku: str) -> str:
        """Manage SKU for a specific product."""
        message = f"## SKU Managed\nSKU for **'{product_name}'** managed:\n\n{sku}"

        return message

    @staticmethod
    @kernel_function(
        description="Provide product training sessions with detailed training materials."
    )
    async def provide_product_training(
        product_name: str, training_session_details: str
    ) -> str:
        """Provide training for a specific product."""
        message = f"## Product Training Provided\nTraining for **'{product_name}'** provided with details:\n\n{training_session_details}"

        return message

    # This function does NOT have the kernel_function annotation
    # because it's meant for introspection rather than being exposed as a tool
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
        return json.dumps(tools_list, ensure_ascii=False)

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
