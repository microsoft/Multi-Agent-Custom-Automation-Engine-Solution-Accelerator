"""MarketingTools class provides various marketing functions for a marketing agent."""

import inspect
import json
from typing import Callable, List, get_type_hints

from semantic_kernel.functions import kernel_function
from common.models.messages_kernel import AgentType


class MarketingTools:
    """A class that provides various marketing tools and functions."""

    agent_name = AgentType.MARKETING.value

    @staticmethod
    @kernel_function(description="Create a new marketing campaign.")
    async def create_marketing_campaign(
        campaign_name: str, target_audience: str, budget: float
    ) -> str:
        return f"Marketing campaign '{campaign_name}' created targeting '{target_audience}' with a budget of ${budget:.2f}."

    @staticmethod
    @kernel_function(description="Analyze market trends in a specific industry.")
    async def analyze_market_trends(industry: str) -> str:
        return f"Market trends analyzed for the '{industry}' industry."

    # ToDo: Seems to be a bug in SK when processing functions with list parameters
    @staticmethod
    @kernel_function(description="Generate social media posts for a campaign.")
    async def generate_social_posts(campaign_name: str, platforms: List[str]) -> str:
        platforms_str = ", ".join(platforms)
        return f"Social media posts for campaign '{campaign_name}' generated for platforms: {platforms_str}."

    @staticmethod
    @kernel_function(description="Plan the advertising budget for a campaign.")
    async def plan_advertising_budget(campaign_name: str, total_budget: float) -> str:
        return f"Advertising budget planned for campaign '{campaign_name}' with a total budget of ${total_budget:.2f}."

    @staticmethod
    @kernel_function(description="Conduct a customer survey on a specific topic.")
    async def conduct_customer_survey(survey_topic: str, target_group: str) -> str:
        return (
            f"Customer survey on '{survey_topic}' conducted targeting '{target_group}'."
        )

    @staticmethod
    @kernel_function(description="Perform a competitor analysis.")
    async def perform_competitor_analysis(competitor_name: str) -> str:
        return f"Competitor analysis performed on '{competitor_name}'."

    @staticmethod
    @kernel_function(description="Schedule a marketing event.")
    async def schedule_marketing_event(
        event_name: str, date: str, location: str
    ) -> str:
        return f"Marketing event '{event_name}' scheduled on {date} at {location}."

    @staticmethod
    @kernel_function(description="Design promotional material for a campaign.")
    async def design_promotional_material(
        campaign_name: str, material_type: str
    ) -> str:
        return f"{material_type.capitalize()} for campaign '{campaign_name}' designed."

    @staticmethod
    @kernel_function(description="Manage email marketing for a campaign.")
    async def manage_email_marketing(campaign_name: str, email_list_size: int) -> str:
        return f"Email marketing managed for campaign '{campaign_name}' targeting {email_list_size} recipients."

    @staticmethod
    @kernel_function(description="Track the performance of a campaign.")
    async def track_campaign_performance(campaign_name: str) -> str:
        return f"Performance of campaign '{campaign_name}' tracked."

    @staticmethod
    @kernel_function(description="Coordinate a campaign with the sales team.")
    async def coordinate_with_sales_team(campaign_name: str) -> str:
        return f"Campaign '{campaign_name}' coordinated with the sales team."

    @staticmethod
    @kernel_function(description="Develop a brand strategy.")
    async def develop_brand_strategy(brand_name: str) -> str:
        return f"Brand strategy developed for '{brand_name}'."

    @staticmethod
    @kernel_function(description="Create a content calendar for a specific month.")
    async def create_content_calendar(month: str) -> str:
        return f"Content calendar for '{month}' created."

    @staticmethod
    @kernel_function(description="Update content on a specific website page.")
    async def update_website_content(page_name: str) -> str:
        return f"Website content on page '{page_name}' updated."

    @staticmethod
    @kernel_function(description="Plan a product launch.")
    async def plan_product_launch(product_name: str, launch_date: str) -> str:
        return f"Product launch for '{product_name}' planned on {launch_date}."

    @staticmethod
    @kernel_function(
        description="This is a function to draft / write a press release. You must call the function by passing the key information that you want to be included in the press release."
    )
    async def generate_press_release(key_information_for_press_release: str) -> str:
        return f"Look through the conversation history. Identify the content. Now you must generate a press release based on this content {key_information_for_press_release}. Make it approximately 2 paragraphs."

    @staticmethod
    @kernel_function(description="Conduct market research on a specific topic.")
    async def conduct_market_research(research_topic: str) -> str:
        return f"Market research conducted on '{research_topic}'."

    @staticmethod
    @kernel_function(description="Handle customer feedback.")
    async def handle_customer_feedback(feedback_details: str) -> str:
        return f"Customer feedback handled: {feedback_details}."

    @staticmethod
    @kernel_function(description="Generate a marketing report for a campaign.")
    async def generate_marketing_report(campaign_name: str) -> str:
        return f"Marketing report generated for campaign '{campaign_name}'."

    @staticmethod
    @kernel_function(description="Manage a social media account.")
    async def manage_social_media_account(platform: str, account_name: str) -> str:
        return (
            f"Social media account '{account_name}' on platform '{platform}' managed."
        )

    @staticmethod
    @kernel_function(description="Create a video advertisement.")
    async def create_video_ad(content_title: str, platform: str) -> str:
        return (
            f"Video advertisement '{content_title}' created for platform '{platform}'."
        )

    @staticmethod
    @kernel_function(description="Conduct a focus group study.")
    async def conduct_focus_group(study_topic: str, participants: int) -> str:
        return f"Focus group study on '{study_topic}' conducted with {participants} participants."

    @staticmethod
    @kernel_function(description="Update brand guidelines.")
    async def update_brand_guidelines(brand_name: str, guidelines: str) -> str:
        return f"Brand guidelines for '{brand_name}' updated."

    @staticmethod
    @kernel_function(description="Handle collaboration with an influencer.")
    async def handle_influencer_collaboration(
        influencer_name: str, campaign_name: str
    ) -> str:
        return f"Collaboration with influencer '{influencer_name}' for campaign '{campaign_name}' handled."

    @staticmethod
    @kernel_function(description="Analyze customer behavior in a specific segment.")
    async def analyze_customer_behavior(segment: str) -> str:
        return f"Customer behavior in segment '{segment}' analyzed."

    @staticmethod
    @kernel_function(description="Manage a customer loyalty program.")
    async def manage_loyalty_program(program_name: str, members: int) -> str:
        return f"Loyalty program '{program_name}' managed with {members} members."

    @staticmethod
    @kernel_function(description="Develop a content strategy.")
    async def develop_content_strategy(strategy_name: str) -> str:
        return f"Content strategy '{strategy_name}' developed."

    @staticmethod
    @kernel_function(description="Create an infographic.")
    async def create_infographic(content_title: str) -> str:
        return f"Infographic '{content_title}' created."

    @staticmethod
    @kernel_function(description="Schedule a webinar.")
    async def schedule_webinar(webinar_title: str, date: str, platform: str) -> str:
        return f"Webinar '{webinar_title}' scheduled on {date} via {platform}."

    @staticmethod
    @kernel_function(description="Manage online reputation for a brand.")
    async def manage_online_reputation(brand_name: str) -> str:
        return f"Online reputation for '{brand_name}' managed."

    @staticmethod
    @kernel_function(description="Run A/B testing for an email campaign.")
    async def run_email_ab_testing(campaign_name: str) -> str:
        return f"A/B testing for email campaign '{campaign_name}' run."

    @staticmethod
    @kernel_function(description="Create a podcast episode.")
    async def create_podcast_episode(series_name: str, episode_title: str) -> str:
        return f"Podcast episode '{episode_title}' for series '{series_name}' created."

    @staticmethod
    @kernel_function(description="Manage an affiliate marketing program.")
    async def manage_affiliate_program(program_name: str, affiliates: int) -> str:
        return (
            f"Affiliate program '{program_name}' managed with {affiliates} affiliates."
        )

    @staticmethod
    @kernel_function(description="Generate lead magnets.")
    async def generate_lead_magnets(content_title: str) -> str:
        return f"Lead magnet '{content_title}' generated."

    @staticmethod
    @kernel_function(description="Organize participation in a trade show.")
    async def organize_trade_show(booth_number: str, event_name: str) -> str:
        return f"Trade show '{event_name}' organized at booth number '{booth_number}'."

    @staticmethod
    @kernel_function(description="Manage a customer retention program.")
    async def manage_retention_program(program_name: str) -> str:
        return f"Customer retention program '{program_name}' managed."

    @staticmethod
    @kernel_function(description="Run a pay-per-click (PPC) campaign.")
    async def run_ppc_campaign(campaign_name: str, budget: float) -> str:
        return f"PPC campaign '{campaign_name}' run with a budget of ${budget:.2f}."

    @staticmethod
    @kernel_function(description="Create a case study.")
    async def create_case_study(case_title: str, client_name: str) -> str:
        return f"Case study '{case_title}' for client '{client_name}' created."

    @staticmethod
    @kernel_function(description="Generate lead nurturing emails.")
    async def generate_lead_nurturing_emails(sequence_name: str, steps: int) -> str:
        return f"Lead nurturing email sequence '{sequence_name}' generated with {steps} steps."

    @staticmethod
    @kernel_function(description="Manage crisis communication.")
    async def manage_crisis_communication(crisis_situation: str) -> str:
        return f"Crisis communication managed for situation '{crisis_situation}'."

    @staticmethod
    @kernel_function(description="Create interactive content.")
    async def create_interactive_content(content_title: str) -> str:
        return f"Interactive content '{content_title}' created."

    @staticmethod
    @kernel_function(description="Handle media relations.")
    async def handle_media_relations(media_outlet: str) -> str:
        return f"Media relations handled with '{media_outlet}'."

    @staticmethod
    @kernel_function(description="Create a testimonial video.")
    async def create_testimonial_video(client_name: str) -> str:
        return f"Testimonial video created for client '{client_name}'."

    @staticmethod
    @kernel_function(description="Manage event sponsorship.")
    async def manage_event_sponsorship(event_name: str, sponsor_name: str) -> str:
        return f"Event sponsorship for '{event_name}' managed with sponsor '{sponsor_name}'."

    @staticmethod
    @kernel_function(description="Optimize a specific stage of the conversion funnel.")
    async def optimize_conversion_funnel(stage: str) -> str:
        return f"Conversion funnel stage '{stage}' optimized."

    # ToDo: Seems to be a bug in SK when processing functions with list parameters
    @staticmethod
    @kernel_function(description="Run an influencer marketing campaign.")
    async def run_influencer_campaign(
        campaign_name: str, influencers: List[str]
    ) -> str:
        influencers_str = ", ".join(influencers)
        return f"Influencer marketing campaign '{campaign_name}' run with influencers: {influencers_str}."

    @staticmethod
    @kernel_function(description="Analyze website traffic from a specific source.")
    async def analyze_website_traffic(source: str) -> str:
        return f"Website traffic analyzed from source '{source}'."

    @staticmethod
    @kernel_function(description="Develop customer personas for a specific segment.")
    async def develop_customer_personas(segment_name: str) -> str:
        return f"Customer personas developed for segment '{segment_name}'."

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
