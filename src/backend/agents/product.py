import time
from datetime import datetime
from typing import List

from autogen_core.base import AgentId
from autogen_core.components import default_subscription
from autogen_core.components.models import AzureOpenAIChatCompletionClient
from autogen_core.components.tools import FunctionTool, Tool
from typing_extensions import Annotated

from agents.base_agent import BaseAgent
from context.cosmos_memory import CosmosBufferedChatCompletionContext

formatting_instructions = "Instructions: returning the output of this function call verbatim to the user in markdown. Then write AGENT SUMMARY: and then include a summary of what you did."


# Define Product Agent functions (tools)
async def add_mobile_extras_pack(new_extras_pack_name: str, start_date: str) -> str:
    """Add an extras pack/new product to the mobile plan for the customer. For example, adding a roaming plan to their service. The arguments should include the new_extras_pack_name and the start_date as strings. You must provide the exact plan name, as found using the get_product_info() function."""
    analysis = (
        f"# Request to Add Extras Pack to Mobile Plan\n"
        f"## New Plan:\n{new_extras_pack_name}\n"
        f"## Start Date:\n{start_date}\n\n"
        f"These changes have been completed and should be reflected in your app in 5-10 minutes."
        f"\n\n{formatting_instructions}"
    )
    time.sleep(2)
    return analysis


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


async def get_billing_date() -> str:
    """Get information about the recurring billing date."""
    now = datetime.now()
    start_of_month = datetime(now.year, now.month, 1)
    start_of_month_string = start_of_month.strftime("%Y-%m-%d")
    return f"## Billing Date\nYour most recent billing date was **{start_of_month_string}**."


async def check_inventory(product_name: str) -> str:
    """Check the inventory level for a specific product."""
    inventory_status = (
        f"## Inventory Status\nInventory status for **'{product_name}'** checked."
    )
    print(inventory_status)
    return inventory_status


async def update_inventory(product_name: str, quantity: int) -> str:
    """Update the inventory quantity for a specific product."""
    message = f"## Inventory Update\nInventory for **'{product_name}'** updated by **{quantity}** units."
    print(message)
    return message


async def add_new_product(
    product_details: Annotated[str, "Details of the new product"]
) -> str:
    """Add a new product to the inventory."""
    message = (
        f"## New Product Added\nNew product added with details:\n\n{product_details}"
    )
    print(message)
    return message


async def update_product_price(product_name: str, price: float) -> str:
    """Update the price of a specific product."""
    message = (
        f"## Price Update\nPrice for **'{product_name}'** updated to **${price:.2f}**."
    )
    print(message)
    return message


async def schedule_product_launch(product_name: str, launch_date: str) -> str:
    """Schedule a product launch on a specific date."""
    message = f"## Product Launch Scheduled\nProduct **'{product_name}'** launch scheduled on **{launch_date}**."
    print(message)
    return message


async def analyze_sales_data(product_name: str, time_period: str) -> str:
    """Analyze sales data for a product over a given time period."""
    analysis = f"## Sales Data Analysis\nSales data for **'{product_name}'** over **{time_period}** analyzed."
    print(analysis)
    return analysis


async def get_customer_feedback(product_name: str) -> str:
    """Retrieve customer feedback for a specific product."""
    feedback = (
        f"## Customer Feedback\nCustomer feedback for **'{product_name}'** retrieved."
    )
    print(feedback)
    return feedback


async def manage_promotions(
    product_name: str, promotion_details: Annotated[str, "Details of the promotion"]
) -> str:
    """Manage promotions for a specific product."""
    message = f"## Promotion Managed\nPromotion for **'{product_name}'** managed with details:\n\n{promotion_details}"
    print(message)
    return message


async def coordinate_with_marketing(
    product_name: str,
    campaign_details: Annotated[str, "Details of the marketing campaign"],
) -> str:
    """Coordinate with the marketing team for a product."""
    message = f"## Marketing Coordination\nCoordinated with marketing for **'{product_name}'** campaign:\n\n{campaign_details}"
    print(message)
    return message


async def review_product_quality(product_name: str) -> str:
    """Review the quality of a specific product."""
    review = f"## Quality Review\nQuality review for **'{product_name}'** completed."
    print(review)
    return review


async def handle_product_recall(product_name: str, recall_reason: str) -> str:
    """Handle a product recall for a specific product."""
    message = f"## Product Recall\nProduct recall for **'{product_name}'** initiated due to:\n\n{recall_reason}"
    print(message)
    return message


async def provide_product_recommendations(
    customer_preferences: Annotated[str, "Customer preferences or requirements"]
) -> str:
    """Provide product recommendations based on customer preferences."""
    recommendations = f"## Product Recommendations\nProduct recommendations based on preferences **'{customer_preferences}'** provided."
    print(recommendations)
    return recommendations


async def generate_product_report(product_name: str, report_type: str) -> str:
    """Generate a report for a specific product."""
    report = f"## {report_type} Report\n{report_type} report for **'{product_name}'** generated."
    print(report)
    return report


async def manage_supply_chain(product_name: str, supplier_name: str) -> str:
    """Manage supply chain activities for a specific product."""
    message = f"## Supply Chain Management\nSupply chain for **'{product_name}'** managed with supplier **'{supplier_name}'**."
    print(message)
    return message


async def track_product_shipment(product_name: str, tracking_number: str) -> str:
    """Track the shipment of a specific product."""
    status = f"## Shipment Tracking\nShipment for **'{product_name}'** with tracking number **'{tracking_number}'** tracked."
    print(status)
    return status


async def set_reorder_level(product_name: str, reorder_level: int) -> str:
    """Set the reorder level for a specific product."""
    message = f"## Reorder Level Set\nReorder level for **'{product_name}'** set to **{reorder_level}** units."
    print(message)
    return message


async def monitor_market_trends() -> str:
    """Monitor market trends relevant to products."""
    trends = "## Market Trends\nMarket trends monitored and data updated."
    print(trends)
    return trends


async def develop_new_product_ideas(
    idea_details: Annotated[str, "Details of the new product idea"]
) -> str:
    """Develop new product ideas."""
    message = f"## New Product Idea\nNew product idea developed:\n\n{idea_details}"
    print(message)
    return message


async def collaborate_with_tech_team(
    product_name: str,
    collaboration_details: Annotated[str, "Details of the technical requirements"],
) -> str:
    """Collaborate with the tech team for product development."""
    message = f"## Tech Team Collaboration\nCollaborated with tech team on **'{product_name}'**:\n\n{collaboration_details}"
    print(message)
    return message


async def update_product_description(product_name: str, description: str) -> str:
    """Update the description of a specific product."""
    message = f"## Product Description Updated\nDescription for **'{product_name}'** updated to:\n\n{description}"
    print(message)
    return message


async def set_product_discount(product_name: str, discount_percentage: float) -> str:
    """Set a discount for a specific product."""
    message = f"## Discount Set\nDiscount for **'{product_name}'** set to **{discount_percentage}%**."
    print(message)
    return message


async def manage_product_returns(product_name: str, return_reason: str) -> str:
    """Manage returns for a specific product."""
    message = f"## Product Return Managed\nReturn for **'{product_name}'** managed due to:\n\n{return_reason}"
    print(message)
    return message


async def conduct_product_survey(product_name: str, survey_details: str) -> str:
    """Conduct a survey for a specific product."""
    message = f"## Product Survey Conducted\nSurvey for **'{product_name}'** conducted with details:\n\n{survey_details}"
    print(message)
    return message


async def handle_product_complaints(product_name: str, complaint_details: str) -> str:
    """Handle complaints for a specific product."""
    message = f"## Product Complaint Handled\nComplaint for **'{product_name}'** handled with details:\n\n{complaint_details}"
    print(message)
    return message


async def update_product_specifications(product_name: str, specifications: str) -> str:
    """Update the specifications for a specific product."""
    message = f"## Product Specifications Updated\nSpecifications for **'{product_name}'** updated to:\n\n{specifications}"
    print(message)
    return message


async def organize_product_photoshoot(product_name: str, photoshoot_date: str) -> str:
    """Organize a photoshoot for a specific product."""
    message = f"## Product Photoshoot Organized\nPhotoshoot for **'{product_name}'** organized on **{photoshoot_date}**."
    print(message)
    return message


async def manage_product_listing(product_name: str, listing_details: str) -> str:
    """Manage the listing of a specific product on e-commerce platforms."""
    message = f"## Product Listing Managed\nListing for **'{product_name}'** managed with details:\n\n{listing_details}"
    print(message)
    return message


async def set_product_availability(product_name: str, availability: bool) -> str:
    """Set the availability status of a specific product."""
    status = "available" if availability else "unavailable"
    message = f"## Product Availability Set\nProduct **'{product_name}'** is now **{status}**."
    print(message)
    return message


async def coordinate_with_logistics(product_name: str, logistics_details: str) -> str:
    """Coordinate with the logistics team for a specific product."""
    message = f"## Logistics Coordination\nCoordinated with logistics for **'{product_name}'** with details:\n\n{logistics_details}"
    print(message)
    return message


async def calculate_product_margin(
    product_name: str, cost_price: float, selling_price: float
) -> str:
    """Calculate the profit margin for a specific product."""
    margin = ((selling_price - cost_price) / selling_price) * 100
    message = f"## Profit Margin Calculated\nProfit margin for **'{product_name}'** calculated at **{margin:.2f}%**."
    print(message)
    return message


async def update_product_category(product_name: str, category: str) -> str:
    """Update the category of a specific product."""
    message = f"## Product Category Updated\nCategory for **'{product_name}'** updated to:\n\n{category}"
    print(message)
    return message


async def manage_product_bundles(bundle_name: str, product_list: List[str]) -> str:
    """Manage product bundles."""
    products = ", ".join(product_list)
    message = f"## Product Bundle Managed\nProduct bundle **'{bundle_name}'** managed with products:\n\n{products}"
    print(message)
    return message


async def optimize_product_page(product_name: str, optimization_details: str) -> str:
    """Optimize the product page for better performance."""
    message = f"## Product Page Optimized\nProduct page for **'{product_name}'** optimized with details:\n\n{optimization_details}"
    print(message)
    return message


async def monitor_product_performance(product_name: str) -> str:
    """Monitor the performance of a specific product."""
    message = f"## Product Performance Monitored\nPerformance for **'{product_name}'** monitored."
    print(message)
    return message


async def handle_product_pricing(product_name: str, pricing_strategy: str) -> str:
    """Handle pricing strategy for a specific product."""
    message = f"## Pricing Strategy Set\nPricing strategy for **'{product_name}'** set to:\n\n{pricing_strategy}"
    print(message)
    return message


async def develop_product_training_material(
    product_name: str, training_material: str
) -> str:
    """Develop training material for a specific product."""
    message = f"## Training Material Developed\nTraining material for **'{product_name}'** developed:\n\n{training_material}"
    print(message)
    return message


async def update_product_labels(product_name: str, label_details: str) -> str:
    """Update labels for a specific product."""
    message = f"## Product Labels Updated\nLabels for **'{product_name}'** updated with details:\n\n{label_details}"
    print(message)
    return message


async def manage_product_warranty(product_name: str, warranty_details: str) -> str:
    """Manage the warranty for a specific product."""
    message = f"## Product Warranty Managed\nWarranty for **'{product_name}'** managed with details:\n\n{warranty_details}"
    print(message)
    return message


async def forecast_product_demand(product_name: str, forecast_period: str) -> str:
    """Forecast demand for a specific product."""
    message = f"## Demand Forecast\nDemand for **'{product_name}'** forecasted for **{forecast_period}**."
    print(message)
    return message


async def handle_product_licensing(product_name: str, licensing_details: str) -> str:
    """Handle licensing for a specific product."""
    message = f"## Product Licensing Handled\nLicensing for **'{product_name}'** handled with details:\n\n{licensing_details}"
    print(message)
    return message


async def manage_product_packaging(product_name: str, packaging_details: str) -> str:
    """Manage packaging for a specific product."""
    message = f"## Product Packaging Managed\nPackaging for **'{product_name}'** managed with details:\n\n{packaging_details}"
    print(message)
    return message


async def set_product_safety_standards(product_name: str, safety_standards: str) -> str:
    """Set safety standards for a specific product."""
    message = f"## Safety Standards Set\nSafety standards for **'{product_name}'** set to:\n\n{safety_standards}"
    print(message)
    return message


async def develop_product_features(product_name: str, features_details: str) -> str:
    """Develop new features for a specific product."""
    message = f"## New Features Developed\nNew features for **'{product_name}'** developed with details:\n\n{features_details}"
    print(message)
    return message


async def evaluate_product_performance(
    product_name: str, evaluation_criteria: str
) -> str:
    """Evaluate the performance of a specific product."""
    message = f"## Product Performance Evaluated\nPerformance of **'{product_name}'** evaluated based on:\n\n{evaluation_criteria}"
    print(message)
    return message


async def manage_custom_product_orders(order_details: str) -> str:
    """Manage custom orders for a specific product."""
    message = f"## Custom Product Order Managed\nCustom product order managed with details:\n\n{order_details}"
    print(message)
    return message


async def update_product_images(product_name: str, image_urls: List[str]) -> str:
    """Update images for a specific product."""
    images = ", ".join(image_urls)
    message = f"## Product Images Updated\nImages for **'{product_name}'** updated:\n\n{images}"
    print(message)
    return message


async def handle_product_obsolescence(product_name: str) -> str:
    """Handle the obsolescence of a specific product."""
    message = f"## Product Obsolescence Handled\nObsolescence for **'{product_name}'** handled."
    print(message)
    return message


async def manage_product_sku(product_name: str, sku: str) -> str:
    """Manage SKU for a specific product."""
    message = f"## SKU Managed\nSKU for **'{product_name}'** managed:\n\n{sku}"
    print(message)
    return message


async def provide_product_training(
    product_name: str, training_session_details: str
) -> str:
    """Provide training for a specific product."""
    message = f"## Product Training Provided\nTraining for **'{product_name}'** provided with details:\n\n{training_session_details}"
    print(message)
    return message


# Create the ProductTools list
def get_product_tools() -> List[Tool]:
    ProductTools: List[Tool] = [
        FunctionTool(
            add_mobile_extras_pack,
            description="Add an extras pack/new product to the mobile plan for the customer. For example, adding a roaming plan to their service. The arguments should include the new_extras_pack_name and the start_date as strings. You must provide the exact plan name, as found using the get_product_info() function.",
            name="add_mobile_extras_pack",
        ),
        FunctionTool(
            get_product_info,
            description="Get information about the different products and phone plans available, including roaming services.",
            name="get_product_info",
        ),
        FunctionTool(
            get_billing_date,
            description="Get the billing date for the customer",
            name="get_billing_date",
        ),
        FunctionTool(
            check_inventory,
            description="Check the inventory level for a specific product.",
            name="check_inventory",
        ),
        FunctionTool(
            update_inventory,
            description="Update the inventory quantity for a specific product.",
            name="update_inventory",
        ),
        FunctionTool(
            add_new_product,
            description="Add a new product to the inventory.",
            name="add_new_product",
        ),
        FunctionTool(
            update_product_price,
            description="Update the price of a specific product.",
            name="update_product_price",
        ),
        FunctionTool(
            schedule_product_launch,
            description="Schedule a product launch on a specific date.",
            name="schedule_product_launch",
        ),
        FunctionTool(
            analyze_sales_data,
            description="Analyze sales data for a product over a given time period.",
            name="analyze_sales_data",
        ),
        FunctionTool(
            get_customer_feedback,
            description="Retrieve customer feedback for a specific product.",
            name="get_customer_feedback",
        ),
        FunctionTool(
            manage_promotions,
            description="Manage promotions for a specific product.",
            name="manage_promotions",
        ),
        FunctionTool(
            coordinate_with_marketing,
            description="Coordinate with the marketing team for a product.",
            name="coordinate_with_marketing",
        ),
        FunctionTool(
            review_product_quality,
            description="Review the quality of a specific product.",
            name="review_product_quality",
        ),
        FunctionTool(
            handle_product_recall,
            description="Handle a product recall for a specific product.",
            name="handle_product_recall",
        ),
        FunctionTool(
            provide_product_recommendations,
            description="Provide product recommendations based on customer preferences.",
            name="provide_product_recommendations",
        ),
        FunctionTool(
            generate_product_report,
            description="Generate a report for a specific product.",
            name="generate_product_report",
        ),
        FunctionTool(
            manage_supply_chain,
            description="Manage supply chain activities for a specific product.",
            name="manage_supply_chain",
        ),
        FunctionTool(
            track_product_shipment,
            description="Track the shipment of a specific product.",
            name="track_product_shipment",
        ),
        FunctionTool(
            set_reorder_level,
            description="Set the reorder level for a specific product.",
            name="set_reorder_level",
        ),
        FunctionTool(
            monitor_market_trends,
            description="Monitor market trends relevant to products.",
            name="monitor_market_trends",
        ),
        FunctionTool(
            develop_new_product_ideas,
            description="Develop new product ideas.",
            name="develop_new_product_ideas",
        ),
        FunctionTool(
            collaborate_with_tech_team,
            description="Collaborate with the tech team for product development.",
            name="collaborate_with_tech_team",
        ),
        FunctionTool(
            get_product_info,
            description="Get detailed information about a specific product.",
            name="get_product_info",
        ),
        FunctionTool(
            check_inventory,
            description="Check the inventory level for a specific product.",
            name="check_inventory",
        ),
        FunctionTool(
            update_inventory,
            description="Update the inventory quantity for a specific product.",
            name="update_inventory",
        ),
        FunctionTool(
            add_new_product,
            description="Add a new product to the inventory.",
            name="add_new_product",
        ),
        FunctionTool(
            update_product_price,
            description="Update the price of a specific product.",
            name="update_product_price",
        ),
        FunctionTool(
            schedule_product_launch,
            description="Schedule a product launch on a specific date.",
            name="schedule_product_launch",
        ),
        FunctionTool(
            analyze_sales_data,
            description="Analyze sales data for a product over a given time period.",
            name="analyze_sales_data",
        ),
        FunctionTool(
            get_customer_feedback,
            description="Retrieve customer feedback for a specific product.",
            name="get_customer_feedback",
        ),
        FunctionTool(
            manage_promotions,
            description="Manage promotions for a specific product.",
            name="manage_promotions",
        ),
        FunctionTool(
            coordinate_with_marketing,
            description="Coordinate with the marketing team for a product.",
            name="coordinate_with_marketing",
        ),
        FunctionTool(
            review_product_quality,
            description="Review the quality of a specific product.",
            name="review_product_quality",
        ),
        FunctionTool(
            handle_product_recall,
            description="Handle a product recall for a specific product.",
            name="handle_product_recall",
        ),
        FunctionTool(
            provide_product_recommendations,
            description="Provide product recommendations based on customer preferences.",
            name="provide_product_recommendations",
        ),
        FunctionTool(
            generate_product_report,
            description="Generate a report for a specific product.",
            name="generate_product_report",
        ),
        FunctionTool(
            manage_supply_chain,
            description="Manage supply chain activities for a specific product.",
            name="manage_supply_chain",
        ),
        FunctionTool(
            track_product_shipment,
            description="Track the shipment of a specific product.",
            name="track_product_shipment",
        ),
        FunctionTool(
            set_reorder_level,
            description="Set the reorder level for a specific product.",
            name="set_reorder_level",
        ),
        FunctionTool(
            monitor_market_trends,
            description="Monitor market trends relevant to products.",
            name="monitor_market_trends",
        ),
        FunctionTool(
            develop_new_product_ideas,
            description="Develop new product ideas.",
            name="develop_new_product_ideas",
        ),
        FunctionTool(
            collaborate_with_tech_team,
            description="Collaborate with the tech team for product development.",
            name="collaborate_with_tech_team",
        ),
        # New tools
        FunctionTool(
            update_product_description,
            description="Update the description of a specific product.",
            name="update_product_description",
        ),
        FunctionTool(
            set_product_discount,
            description="Set a discount for a specific product.",
            name="set_product_discount",
        ),
        FunctionTool(
            manage_product_returns,
            description="Manage returns for a specific product.",
            name="manage_product_returns",
        ),
        FunctionTool(
            conduct_product_survey,
            description="Conduct a survey for a specific product.",
            name="conduct_product_survey",
        ),
        FunctionTool(
            handle_product_complaints,
            description="Handle complaints for a specific product.",
            name="handle_product_complaints",
        ),
        FunctionTool(
            update_product_specifications,
            description="Update the specifications for a specific product.",
            name="update_product_specifications",
        ),
        FunctionTool(
            organize_product_photoshoot,
            description="Organize a photoshoot for a specific product.",
            name="organize_product_photoshoot",
        ),
        FunctionTool(
            manage_product_listing,
            description="Manage the listing of a specific product on e-commerce platforms.",
            name="manage_product_listing",
        ),
        FunctionTool(
            set_product_availability,
            description="Set the availability status of a specific product.",
            name="set_product_availability",
        ),
        FunctionTool(
            coordinate_with_logistics,
            description="Coordinate with the logistics team for a specific product.",
            name="coordinate_with_logistics",
        ),
        FunctionTool(
            calculate_product_margin,
            description="Calculate the profit margin for a specific product.",
            name="calculate_product_margin",
        ),
        FunctionTool(
            update_product_category,
            description="Update the category of a specific product.",
            name="update_product_category",
        ),
        FunctionTool(
            manage_product_bundles,
            description="Manage product bundles.",
            name="manage_product_bundles",
        ),
        FunctionTool(
            optimize_product_page,
            description="Optimize the product page for better performance.",
            name="optimize_product_page",
        ),
        FunctionTool(
            monitor_product_performance,
            description="Monitor the performance of a specific product.",
            name="monitor_product_performance",
        ),
        FunctionTool(
            handle_product_pricing,
            description="Handle pricing strategy for a specific product.",
            name="handle_product_pricing",
        ),
        FunctionTool(
            develop_product_training_material,
            description="Develop training material for a specific product.",
            name="develop_product_training_material",
        ),
        FunctionTool(
            update_product_labels,
            description="Update labels for a specific product.",
            name="update_product_labels",
        ),
        FunctionTool(
            manage_product_warranty,
            description="Manage the warranty for a specific product.",
            name="manage_product_warranty",
        ),
        FunctionTool(
            forecast_product_demand,
            description="Forecast demand for a specific product.",
            name="forecast_product_demand",
        ),
        FunctionTool(
            handle_product_licensing,
            description="Handle licensing for a specific product.",
            name="handle_product_licensing",
        ),
        FunctionTool(
            manage_product_packaging,
            description="Manage packaging for a specific product.",
            name="manage_product_packaging",
        ),
        FunctionTool(
            set_product_safety_standards,
            description="Set safety standards for a specific product.",
            name="set_product_safety_standards",
        ),
        FunctionTool(
            develop_product_features,
            description="Develop new features for a specific product.",
            name="develop_product_features",
        ),
        FunctionTool(
            evaluate_product_performance,
            description="Evaluate the performance of a specific product.",
            name="evaluate_product_performance",
        ),
        FunctionTool(
            manage_custom_product_orders,
            description="Manage custom orders for a specific product.",
            name="manage_custom_product_orders",
        ),
        FunctionTool(
            update_product_images,
            description="Update images for a specific product.",
            name="update_product_images",
        ),
        FunctionTool(
            handle_product_obsolescence,
            description="Handle the obsolescence of a specific product.",
            name="handle_product_obsolescence",
        ),
        FunctionTool(
            manage_product_sku,
            description="Manage SKU for a specific product.",
            name="manage_product_sku",
        ),
        FunctionTool(
            provide_product_training,
            description="Provide training for a specific product.",
            name="provide_product_training",
        ),
    ]
    return ProductTools


@default_subscription
class ProductAgent(BaseAgent):
    def __init__(
        self,
        model_client: AzureOpenAIChatCompletionClient,
        session_id: str,
        user_id: str,
        memory: CosmosBufferedChatCompletionContext,
        product_tools: List[Tool],
        product_tool_agent_id: AgentId,
    ) -> None:
        super().__init__(
            "ProductAgent",
            model_client,
            session_id,
            user_id,
            memory,
            product_tools,
            product_tool_agent_id,
            "You are a Product agent. You have knowledge about product management, development, and compliance guidelines. When asked to call a function, you should summarise back what was done.",
        )
