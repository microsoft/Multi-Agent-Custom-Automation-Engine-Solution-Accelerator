from typing import List

from autogen_core.base import AgentId
from autogen_core.components import default_subscription
from autogen_core.components.models import AzureOpenAIChatCompletionClient
from autogen_core.components.tools import FunctionTool, Tool

from src.backend.agents.base_agent import BaseAgent
from src.backend.context.cosmos_memory import CosmosBufferedChatCompletionContext


# Define new Marketing tools (functions)
async def create_marketing_campaign(
    campaign_name: str, target_audience: str, budget: float
) -> str:
    return f"Marketing campaign '{campaign_name}' created targeting '{target_audience}' with a budget of ${budget:.2f}."


async def analyze_market_trends(industry: str) -> str:
    return f"Market trends analyzed for the '{industry}' industry."


async def generate_social_media_posts(campaign_name: str, platforms: List[str]) -> str:
    platforms_str = ", ".join(platforms)
    return f"Social media posts for campaign '{campaign_name}' generated for platforms: {platforms_str}."


async def plan_advertising_budget(campaign_name: str, total_budget: float) -> str:
    return f"Advertising budget planned for campaign '{campaign_name}' with a total budget of ${total_budget:.2f}."


async def conduct_customer_survey(survey_topic: str, target_group: str) -> str:
    return f"Customer survey on '{survey_topic}' conducted targeting '{target_group}'."


async def perform_competitor_analysis(competitor_name: str) -> str:
    return f"Competitor analysis performed on '{competitor_name}'."


async def optimize_seo_strategy(keywords: List[str]) -> str:
    keywords_str = ", ".join(keywords)
    return f"SEO strategy optimized with keywords: {keywords_str}."


async def schedule_marketing_event(event_name: str, date: str, location: str) -> str:
    return f"Marketing event '{event_name}' scheduled on {date} at {location}."


async def design_promotional_material(campaign_name: str, material_type: str) -> str:
    return f"{material_type.capitalize()} for campaign '{campaign_name}' designed."


async def manage_email_marketing(campaign_name: str, email_list_size: int) -> str:
    return f"Email marketing managed for campaign '{campaign_name}' targeting {email_list_size} recipients."


async def track_campaign_performance(campaign_name: str) -> str:
    return f"Performance of campaign '{campaign_name}' tracked."


async def coordinate_with_sales_team(campaign_name: str) -> str:
    return f"Campaign '{campaign_name}' coordinated with the sales team."


async def develop_brand_strategy(brand_name: str) -> str:
    return f"Brand strategy developed for '{brand_name}'."


async def create_content_calendar(month: str) -> str:
    return f"Content calendar for '{month}' created."


async def update_website_content(page_name: str) -> str:
    return f"Website content on page '{page_name}' updated."


async def plan_product_launch(product_name: str, launch_date: str) -> str:
    return f"Product launch for '{product_name}' planned on {launch_date}."


# TODO: we need to remove the product info, and instead pass it through from the earlier conversation history / earlier context of the prior steps
async def generate_press_release(key_information_for_press_release: str) -> str:
    return f"Look through the conversation history. Identify the content. Now you must generate a press release based on this content {key_information_for_press_release}. Make it approximately 2 paragraphs."


# async def generate_press_release() -> str:
#     product_info="""

#     # Simulated Phone Plans

#     ## Plan A: Basic Saver
#     - **Monthly Cost**: $25
#     - **Data**: 5GB
#     - **Calls**: Unlimited local calls
#     - **Texts**: Unlimited local texts

#     ## Plan B: Standard Plus
#     - **Monthly Cost**: $45
#     - **Data**: 15GB
#     - **Calls**: Unlimited local and national calls
#     - **Texts**: Unlimited local and national texts

#     ## Plan C: Premium Unlimited
#     - **Monthly Cost**: $70
#     - **Data**: Unlimited
#     - **Calls**: Unlimited local, national, and international calls
#     - **Texts**: Unlimited local, national, and international texts

#     # Roaming Extras Add-On Pack
#     - **Cost**: $15/month
#     - **Data**: 1GB
#     - **Calls**: 200 minutes
#     - **Texts**: 200 texts

#     """
#     return f"Here is the product info {product_info}. Based on the information in the conversation history, you should generate a short, 3 paragraph press release. Use markdown. Return the press release to the user."


async def conduct_market_research(research_topic: str) -> str:
    return f"Market research conducted on '{research_topic}'."


async def handle_customer_feedback(feedback_details: str) -> str:
    return f"Customer feedback handled: {feedback_details}"


async def generate_marketing_report(campaign_name: str) -> str:
    return f"Marketing report generated for campaign '{campaign_name}'."


async def manage_social_media_account(platform: str, account_name: str) -> str:
    return f"Social media account '{account_name}' on platform '{platform}' managed."


async def create_video_ad(content_title: str, platform: str) -> str:
    return f"Video advertisement '{content_title}' created for platform '{platform}'."


async def conduct_focus_group(study_topic: str, participants: int) -> str:
    return f"Focus group study on '{study_topic}' conducted with {participants} participants."


async def update_brand_guidelines(brand_name: str, guidelines: str) -> str:
    return f"Brand guidelines for '{brand_name}' updated."


async def handle_influencer_collaboration(
    influencer_name: str, campaign_name: str
) -> str:
    return f"Collaboration with influencer '{influencer_name}' for campaign '{campaign_name}' handled."


async def analyze_customer_behavior(segment: str) -> str:
    return f"Customer behavior in segment '{segment}' analyzed."


async def manage_loyalty_program(program_name: str, members: int) -> str:
    return f"Loyalty program '{program_name}' managed with {members} members."


async def develop_content_strategy(strategy_name: str) -> str:
    return f"Content strategy '{strategy_name}' developed."


async def create_infographic(content_title: str) -> str:
    return f"Infographic '{content_title}' created."


async def schedule_webinar(webinar_title: str, date: str, platform: str) -> str:
    return f"Webinar '{webinar_title}' scheduled on {date} via {platform}."


async def manage_online_reputation(brand_name: str) -> str:
    return f"Online reputation for '{brand_name}' managed."


async def run_email_ab_testing(campaign_name: str) -> str:
    return f"A/B testing for email campaign '{campaign_name}' run."


async def create_podcast_episode(series_name: str, episode_title: str) -> str:
    return f"Podcast episode '{episode_title}' for series '{series_name}' created."


async def manage_affiliate_program(program_name: str, affiliates: int) -> str:
    return f"Affiliate program '{program_name}' managed with {affiliates} affiliates."


async def generate_lead_magnets(content_title: str) -> str:
    return f"Lead magnet '{content_title}' generated."


async def organize_trade_show(booth_number: str, event_name: str) -> str:
    return f"Trade show '{event_name}' organized at booth number '{booth_number}'."


async def manage_customer_retention_program(program_name: str) -> str:
    return f"Customer retention program '{program_name}' managed."


async def run_ppc_campaign(campaign_name: str, budget: float) -> str:
    return f"PPC campaign '{campaign_name}' run with a budget of ${budget:.2f}."


async def create_case_study(case_title: str, client_name: str) -> str:
    return f"Case study '{case_title}' for client '{client_name}' created."


async def generate_lead_nurturing_emails(sequence_name: str, steps: int) -> str:
    return (
        f"Lead nurturing email sequence '{sequence_name}' generated with {steps} steps."
    )


async def manage_crisis_communication(crisis_situation: str) -> str:
    return f"Crisis communication managed for situation '{crisis_situation}'."


async def create_interactive_content(content_title: str) -> str:
    return f"Interactive content '{content_title}' created."


async def handle_media_relations(media_outlet: str) -> str:
    return f"Media relations handled with '{media_outlet}'."


async def create_testimonial_video(client_name: str) -> str:
    return f"Testimonial video created for client '{client_name}'."


async def manage_event_sponsorship(event_name: str, sponsor_name: str) -> str:
    return (
        f"Sponsorship for event '{event_name}' managed with sponsor '{sponsor_name}'."
    )


async def optimize_conversion_funnel(stage: str) -> str:
    return f"Conversion funnel stage '{stage}' optimized."


async def run_influencer_marketing_campaign(
    campaign_name: str, influencers: List[str]
) -> str:
    influencers_str = ", ".join(influencers)
    return f"Influencer marketing campaign '{campaign_name}' run with influencers: {influencers_str}."


async def analyze_website_traffic(source: str) -> str:
    return f"Website traffic analyzed from source '{source}'."


async def develop_customer_personas(segment_name: str) -> str:
    return f"Customer personas developed for segment '{segment_name}'."


# Create the MarketingTools list
def get_marketing_tools() -> List[Tool]:
    MarketingTools: List[Tool] = [
        FunctionTool(
            create_marketing_campaign,
            description="Create a new marketing campaign.",
            name="create_marketing_campaign",
        ),
        FunctionTool(
            analyze_market_trends,
            description="Analyze market trends in a specific industry.",
            name="analyze_market_trends",
        ),
        FunctionTool(
            generate_social_media_posts,
            description="Generate social media posts for a campaign.",
            name="generate_social_media_posts",
        ),
        FunctionTool(
            plan_advertising_budget,
            description="Plan the advertising budget for a campaign.",
            name="plan_advertising_budget",
        ),
        FunctionTool(
            conduct_customer_survey,
            description="Conduct a customer survey on a specific topic.",
            name="conduct_customer_survey",
        ),
        FunctionTool(
            perform_competitor_analysis,
            description="Perform a competitor analysis.",
            name="perform_competitor_analysis",
        ),
        FunctionTool(
            optimize_seo_strategy,
            description="Optimize SEO strategy using specified keywords.",
            name="optimize_seo_strategy",
        ),
        FunctionTool(
            schedule_marketing_event,
            description="Schedule a marketing event.",
            name="schedule_marketing_event",
        ),
        FunctionTool(
            design_promotional_material,
            description="Design promotional material for a campaign.",
            name="design_promotional_material",
        ),
        FunctionTool(
            manage_email_marketing,
            description="Manage email marketing for a campaign.",
            name="manage_email_marketing",
        ),
        FunctionTool(
            track_campaign_performance,
            description="Track the performance of a campaign.",
            name="track_campaign_performance",
        ),
        FunctionTool(
            coordinate_with_sales_team,
            description="Coordinate a campaign with the sales team.",
            name="coordinate_with_sales_team",
        ),
        FunctionTool(
            develop_brand_strategy,
            description="Develop a brand strategy.",
            name="develop_brand_strategy",
        ),
        FunctionTool(
            create_content_calendar,
            description="Create a content calendar for a specific month.",
            name="create_content_calendar",
        ),
        FunctionTool(
            update_website_content,
            description="Update content on a specific website page.",
            name="update_website_content",
        ),
        FunctionTool(
            plan_product_launch,
            description="Plan a product launch.",
            name="plan_product_launch",
        ),
        FunctionTool(
            generate_press_release,
            description="This is a function to draft / write a press release. You must call the function by passing the key information that you want to be included in the press release.",
            name="generate_press_release",
        ),
        FunctionTool(
            conduct_market_research,
            description="Conduct market research on a specific topic.",
            name="conduct_market_research",
        ),
        FunctionTool(
            handle_customer_feedback,
            description="Handle customer feedback.",
            name="handle_customer_feedback",
        ),
        FunctionTool(
            generate_marketing_report,
            description="Generate a marketing report for a campaign.",
            name="generate_marketing_report",
        ),
        FunctionTool(
            manage_social_media_account,
            description="Manage a social media account.",
            name="manage_social_media_account",
        ),
        FunctionTool(
            create_video_ad,
            description="Create a video advertisement.",
            name="create_video_ad",
        ),
        FunctionTool(
            conduct_focus_group,
            description="Conduct a focus group study.",
            name="conduct_focus_group",
        ),
        FunctionTool(
            update_brand_guidelines,
            description="Update brand guidelines.",
            name="update_brand_guidelines",
        ),
        FunctionTool(
            handle_influencer_collaboration,
            description="Handle collaboration with an influencer.",
            name="handle_influencer_collaboration",
        ),
        FunctionTool(
            analyze_customer_behavior,
            description="Analyze customer behavior in a specific segment.",
            name="analyze_customer_behavior",
        ),
        FunctionTool(
            manage_loyalty_program,
            description="Manage a customer loyalty program.",
            name="manage_loyalty_program",
        ),
        FunctionTool(
            develop_content_strategy,
            description="Develop a content strategy.",
            name="develop_content_strategy",
        ),
        FunctionTool(
            create_infographic,
            description="Create an infographic.",
            name="create_infographic",
        ),
        FunctionTool(
            schedule_webinar,
            description="Schedule a webinar.",
            name="schedule_webinar",
        ),
        FunctionTool(
            manage_online_reputation,
            description="Manage online reputation for a brand.",
            name="manage_online_reputation",
        ),
        FunctionTool(
            run_email_ab_testing,
            description="Run A/B testing for an email campaign.",
            name="run_email_ab_testing",
        ),
        FunctionTool(
            create_podcast_episode,
            description="Create a podcast episode.",
            name="create_podcast_episode",
        ),
        FunctionTool(
            manage_affiliate_program,
            description="Manage an affiliate marketing program.",
            name="manage_affiliate_program",
        ),
        FunctionTool(
            generate_lead_magnets,
            description="Generate lead magnets.",
            name="generate_lead_magnets",
        ),
        FunctionTool(
            organize_trade_show,
            description="Organize participation in a trade show.",
            name="organize_trade_show",
        ),
        FunctionTool(
            manage_customer_retention_program,
            description="Manage a customer retention program.",
            name="manage_customer_retention_program",
        ),
        FunctionTool(
            run_ppc_campaign,
            description="Run a pay-per-click (PPC) campaign.",
            name="run_ppc_campaign",
        ),
        FunctionTool(
            create_case_study,
            description="Create a case study.",
            name="create_case_study",
        ),
        FunctionTool(
            generate_lead_nurturing_emails,
            description="Generate lead nurturing emails.",
            name="generate_lead_nurturing_emails",
        ),
        FunctionTool(
            manage_crisis_communication,
            description="Manage crisis communication.",
            name="manage_crisis_communication",
        ),
        FunctionTool(
            create_interactive_content,
            description="Create interactive content.",
            name="create_interactive_content",
        ),
        FunctionTool(
            handle_media_relations,
            description="Handle media relations.",
            name="handle_media_relations",
        ),
        FunctionTool(
            create_testimonial_video,
            description="Create a testimonial video.",
            name="create_testimonial_video",
        ),
        FunctionTool(
            manage_event_sponsorship,
            description="Manage event sponsorship.",
            name="manage_event_sponsorship",
        ),
        FunctionTool(
            optimize_conversion_funnel,
            description="Optimize a specific stage of the conversion funnel.",
            name="optimize_conversion_funnel",
        ),
        FunctionTool(
            run_influencer_marketing_campaign,
            description="Run an influencer marketing campaign.",
            name="run_influencer_marketing_campaign",
        ),
        FunctionTool(
            analyze_website_traffic,
            description="Analyze website traffic from a specific source.",
            name="analyze_website_traffic",
        ),
        FunctionTool(
            develop_customer_personas,
            description="Develop customer personas for a specific segment.",
            name="develop_customer_personas",
        ),
    ]
    return MarketingTools


@default_subscription
class MarketingAgent(BaseAgent):
    def __init__(
        self,
        model_client: AzureOpenAIChatCompletionClient,
        session_id: str,
        user_id: str,
        model_context: CosmosBufferedChatCompletionContext,
        marketing_tools: List[Tool],
        marketing_tool_agent_id: AgentId,
    ):
        super().__init__(
            "MarketingAgent",
            model_client,
            session_id,
            user_id,
            model_context,
            marketing_tools,
            marketing_tool_agent_id,
            "You are an AI Agent. You have knowledge about marketing, including campaigns, market research, and promotional activities.",
        )
