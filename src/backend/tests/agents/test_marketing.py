# src/backend/tests/agents/test_marketing.py
import os
import sys
import pytest
from unittest.mock import MagicMock

# Adjust sys.path so that the project root is found.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Set required environment variables for tests.
os.environ["COSMOSDB_ENDPOINT"] = "https://mock-endpoint"
os.environ["COSMOSDB_KEY"] = "mock-key"
os.environ["COSMOSDB_DATABASE"] = "mock-database"
os.environ["COSMOSDB_CONTAINER"] = "mock-container"
os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "mock-deployment-name"
os.environ["AZURE_OPENAI_API_VERSION"] = "2023-01-01"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock-openai-endpoint"

# Patch azure module so that event_utils imports without error.
sys.modules["azure.monitor.events.extension"] = MagicMock()

# Import the marketing functions and MarketingAgent from the module.
from src.backend.agents.marketing import (
    create_marketing_campaign,
    analyze_market_trends,
    generate_social_media_posts,
    plan_advertising_budget,
    conduct_customer_survey,
    perform_competitor_analysis,
    optimize_seo_strategy,
    schedule_marketing_event,
    design_promotional_material,
    manage_email_marketing,
    track_campaign_performance,
    coordinate_with_sales_team,
    develop_brand_strategy,
    create_content_calendar,
    update_website_content,
    plan_product_launch,
    generate_press_release,
    conduct_market_research,
    handle_customer_feedback,
    generate_marketing_report,
    manage_social_media_account,
    create_video_ad,
    conduct_focus_group,
    update_brand_guidelines,
    handle_influencer_collaboration,
    analyze_customer_behavior,
    manage_loyalty_program,
    develop_content_strategy,
    create_infographic,
    schedule_webinar,
    manage_online_reputation,
    run_email_ab_testing,
    create_podcast_episode,
    manage_affiliate_program,
    generate_lead_magnets,
    organize_trade_show,
    manage_customer_retention_program,
    run_ppc_campaign,
    create_case_study,
    generate_lead_nurturing_emails,
    manage_crisis_communication,
    create_interactive_content,
    handle_media_relations,
    create_testimonial_video,
    manage_event_sponsorship,
    optimize_conversion_funnel,
    run_influencer_marketing_campaign,
    analyze_website_traffic,
    develop_customer_personas,
    get_marketing_tools,
)


# ------------------ Tests for marketing functions ------------------

@pytest.mark.asyncio
async def test_create_marketing_campaign():
    result = await create_marketing_campaign("Holiday Sale", "Millennials", 10000)
    assert "Marketing campaign 'Holiday Sale' created targeting 'Millennials' with a budget of $10000.00." in result


@pytest.mark.asyncio
async def test_analyze_market_trends():
    result = await analyze_market_trends("Technology")
    assert "Market trends analyzed for the 'Technology' industry." in result


@pytest.mark.asyncio
async def test_generate_social_media_posts():
    result = await generate_social_media_posts("Black Friday", ["Facebook", "Instagram"])
    assert "Social media posts for campaign 'Black Friday' generated for platforms: Facebook, Instagram." in result


@pytest.mark.asyncio
async def test_plan_advertising_budget():
    result = await plan_advertising_budget("New Year Sale", 20000)
    assert "Advertising budget planned for campaign 'New Year Sale' with a total budget of $20000.00." in result


@pytest.mark.asyncio
async def test_conduct_customer_survey():
    result = await conduct_customer_survey("Customer Satisfaction", "Frequent Buyers")
    assert "Customer survey on 'Customer Satisfaction' conducted targeting 'Frequent Buyers'." in result


@pytest.mark.asyncio
async def test_perform_competitor_analysis():
    result = await perform_competitor_analysis("Competitor A")
    assert "Competitor analysis performed on 'Competitor A'." in result


@pytest.mark.asyncio
async def test_optimize_seo_strategy():
    result = await optimize_seo_strategy(["keyword1", "keyword2"])
    assert "SEO strategy optimized with keywords: keyword1, keyword2." in result


@pytest.mark.asyncio
async def test_schedule_marketing_event():
    result = await schedule_marketing_event("Product Launch", "2025-01-30", "Main Hall")
    assert "Marketing event 'Product Launch' scheduled on 2025-01-30 at Main Hall." in result


@pytest.mark.asyncio
async def test_design_promotional_material():
    result = await design_promotional_material("Spring Sale", "poster")
    # Note: The function capitalizes the material_type using .capitalize()
    assert "Poster for campaign 'Spring Sale' designed." in result


@pytest.mark.asyncio
async def test_manage_email_marketing():
    result = await manage_email_marketing("Holiday Offers", 5000)
    assert "Email marketing managed for campaign 'Holiday Offers' targeting 5000 recipients." in result


@pytest.mark.asyncio
async def test_track_campaign_performance():
    result = await track_campaign_performance("Fall Promo")
    assert "Performance of campaign 'Fall Promo' tracked." in result


@pytest.mark.asyncio
async def test_coordinate_with_sales_team():
    result = await coordinate_with_sales_team("Spring Campaign")
    assert "Campaign 'Spring Campaign' coordinated with the sales team." in result


@pytest.mark.asyncio
async def test_develop_brand_strategy():
    result = await develop_brand_strategy("MyBrand")
    assert "Brand strategy developed for 'MyBrand'." in result


@pytest.mark.asyncio
async def test_create_content_calendar():
    result = await create_content_calendar("March")
    assert "Content calendar for 'March' created." in result


@pytest.mark.asyncio
async def test_update_website_content():
    result = await update_website_content("Homepage")
    assert "Website content on page 'Homepage' updated." in result


@pytest.mark.asyncio
async def test_plan_product_launch():
    result = await plan_product_launch("Smartwatch", "2025-02-15")
    assert "Product launch for 'Smartwatch' planned on 2025-02-15." in result


@pytest.mark.asyncio
async def test_generate_press_release():
    result = await generate_press_release("Key updates for press release.")
    # Check for a substring that indicates the press release is generated.
    assert "generate a press release based on this content Key updates for press release." in result


@pytest.mark.asyncio
async def test_conduct_market_research():
    result = await conduct_market_research("Automotive")
    assert "Market research conducted on 'Automotive'." in result


@pytest.mark.asyncio
async def test_handle_customer_feedback():
    result = await handle_customer_feedback("Excellent service!")
    assert "Customer feedback handled: Excellent service!" in result


@pytest.mark.asyncio
async def test_generate_marketing_report():
    result = await generate_marketing_report("Winter Campaign")
    assert "Marketing report generated for campaign 'Winter Campaign'." in result


@pytest.mark.asyncio
async def test_manage_social_media_account():
    result = await manage_social_media_account("Twitter", "BrandX")
    assert "Social media account 'BrandX' on platform 'Twitter' managed." in result


@pytest.mark.asyncio
async def test_create_video_ad():
    result = await create_video_ad("Ad Title", "YouTube")
    assert "Video advertisement 'Ad Title' created for platform 'YouTube'." in result


@pytest.mark.asyncio
async def test_conduct_focus_group():
    result = await conduct_focus_group("Product Feedback", 10)
    assert "Focus group study on 'Product Feedback' conducted with 10 participants." in result


@pytest.mark.asyncio
async def test_update_brand_guidelines():
    result = await update_brand_guidelines("BrandX", "New guidelines")
    assert "Brand guidelines for 'BrandX' updated." in result


@pytest.mark.asyncio
async def test_handle_influencer_collaboration():
    result = await handle_influencer_collaboration("InfluencerY", "CampaignZ")
    assert "Collaboration with influencer 'InfluencerY' for campaign 'CampaignZ' handled." in result


@pytest.mark.asyncio
async def test_analyze_customer_behavior():
    result = await analyze_customer_behavior("SegmentA")
    assert "Customer behavior in segment 'SegmentA' analyzed." in result


@pytest.mark.asyncio
async def test_manage_loyalty_program():
    result = await manage_loyalty_program("Rewards", 300)
    assert "Loyalty program 'Rewards' managed with 300 members." in result


@pytest.mark.asyncio
async def test_develop_content_strategy():
    result = await develop_content_strategy("ContentPlan")
    assert "Content strategy 'ContentPlan' developed." in result


@pytest.mark.asyncio
async def test_create_infographic():
    result = await create_infographic("Top 10 Tips")
    assert "Infographic 'Top 10 Tips' created." in result


@pytest.mark.asyncio
async def test_schedule_webinar():
    result = await schedule_webinar("Webinar X", "2025-03-20", "Zoom")
    assert "Webinar 'Webinar X' scheduled on 2025-03-20 via Zoom." in result


@pytest.mark.asyncio
async def test_manage_online_reputation():
    result = await manage_online_reputation("BrandX")
    assert "Online reputation for 'BrandX' managed." in result


@pytest.mark.asyncio
async def test_run_email_ab_testing():
    result = await run_email_ab_testing("Campaign Test")
    assert "A/B testing for email campaign 'Campaign Test' run." in result


@pytest.mark.asyncio
async def test_create_podcast_episode():
    result = await create_podcast_episode("Series1", "Episode 1")
    assert "Podcast episode 'Episode 1' for series 'Series1' created." in result


@pytest.mark.asyncio
async def test_manage_affiliate_program():
    result = await manage_affiliate_program("AffiliateX", 25)
    assert "Affiliate program 'AffiliateX' managed with 25 affiliates." in result


@pytest.mark.asyncio
async def test_generate_lead_magnets():
    result = await generate_lead_magnets("Free Ebook")
    assert "Lead magnet 'Free Ebook' generated." in result


@pytest.mark.asyncio
async def test_organize_trade_show():
    result = await organize_trade_show("B12", "Tech Expo")
    assert "Trade show 'Tech Expo' organized at booth number 'B12'." in result


@pytest.mark.asyncio
async def test_manage_customer_retention_program():
    result = await manage_customer_retention_program("Retention2025")
    assert "Customer retention program 'Retention2025' managed." in result


@pytest.mark.asyncio
async def test_run_ppc_campaign():
    result = await run_ppc_campaign("PPC Test", 5000.00)
    assert "PPC campaign 'PPC Test' run with a budget of $5000.00." in result


@pytest.mark.asyncio
async def test_create_case_study():
    result = await create_case_study("Case Study 1", "ClientA")
    assert "Case study 'Case Study 1' for client 'ClientA' created." in result


@pytest.mark.asyncio
async def test_generate_lead_nurturing_emails():
    result = await generate_lead_nurturing_emails("NurtureSeq", 5)
    assert "Lead nurturing email sequence 'NurtureSeq' generated with 5 steps." in result


@pytest.mark.asyncio
async def test_manage_crisis_communication():
    result = await manage_crisis_communication("CrisisX")
    assert "Crisis communication managed for situation 'CrisisX'." in result


@pytest.mark.asyncio
async def test_create_interactive_content():
    result = await create_interactive_content("Interactive Quiz")
    assert "Interactive content 'Interactive Quiz' created." in result


@pytest.mark.asyncio
async def test_handle_media_relations():
    result = await handle_media_relations("MediaCorp")
    assert "Media relations handled with 'MediaCorp'." in result


@pytest.mark.asyncio
async def test_create_testimonial_video():
    result = await create_testimonial_video("ClientB")
    assert "Testimonial video created for client 'ClientB'." in result


@pytest.mark.asyncio
async def test_manage_event_sponsorship():
    result = await manage_event_sponsorship("Expo2025", "SponsorX")
    assert "Sponsorship for event 'Expo2025' managed with sponsor 'SponsorX'." in result


@pytest.mark.asyncio
async def test_optimize_conversion_funnel():
    result = await optimize_conversion_funnel("Checkout")
    assert "Conversion funnel stage 'Checkout' optimized." in result


@pytest.mark.asyncio
async def test_run_influencer_marketing_campaign():
    result = await run_influencer_marketing_campaign("InfluenceNow", ["Influencer1", "Influencer2"])
    assert "Influencer marketing campaign 'InfluenceNow' run with influencers: Influencer1, Influencer2." in result


@pytest.mark.asyncio
async def test_analyze_website_traffic():
    result = await analyze_website_traffic("Google")
    assert "Website traffic analyzed from source 'Google'." in result


@pytest.mark.asyncio
async def test_develop_customer_personas():
    result = await develop_customer_personas("Millennials")
    assert "Customer personas developed for segment 'Millennials'." in result


# ------------------ Tests for the MarketingAgent class ------------------
@pytest.fixture
def marketing_agent_dependencies():
    from autogen_core.components.models import AzureOpenAIChatCompletionClient
    return {
        "model_client": MagicMock(spec=AzureOpenAIChatCompletionClient),
        "session_id": "sess_marketing",
        "user_id": "user_marketing",
        "model_context": MagicMock(),  # This would be an instance of CosmosBufferedChatCompletionContext in production
        "marketing_tools": get_marketing_tools(),
        "marketing_tool_agent_id": ("marketing_agent", "sess_marketing"),
    }


def test_get_marketing_tools_complete():
    tools = get_marketing_tools()
    # Check that there are many tools (for example, more than 40)
    assert len(tools) > 40
    # Check that specific tool names are included.
    tool_names = [tool.name for tool in tools]
    for name in [
        "create_marketing_campaign",
        "analyze_market_trends",
        "generate_social_media_posts",
        "plan_advertising_budget",
        "conduct_customer_survey",
    ]:
        assert name in tool_names
