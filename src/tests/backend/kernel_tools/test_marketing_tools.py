"""Test cases for marketing tools."""
import json
import sys
import types

import pytest


mock_models = types.ModuleType("models")
mock_messages_kernel = types.ModuleType("messages_kernel")


class MockAgentType:
    """Mock class to simulate AgentType enum used in messages_kernel."""

    MARKETING = type("EnumValue", (), {"value": "marketing-agent"})


mock_messages_kernel.AgentType = MockAgentType
mock_models.messages_kernel = mock_messages_kernel

sys.modules["models"] = mock_models
sys.modules["models.messages_kernel"] = mock_messages_kernel
from src.backend.kernel_tools.marketing_tools import MarketingTools


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "campaign_name, target_audience, budget, expected",
    [
        (
            "Summer Sale", "Young Adults", 5000.0,
            "Marketing campaign 'Summer Sale' created targeting 'Young Adults' with a budget of $5000.00."
        )
    ]
)
async def test_create_marketing_campaign(campaign_name, target_audience, budget, expected):
    """Test creation of a marketing campaign."""
    result = await MarketingTools.create_marketing_campaign(campaign_name, target_audience, budget)
    assert result == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "industry, expected",
    [
        ("Retail", "Market trends analyzed for the 'Retail' industry.")
    ]
)
async def test_analyze_market_trends(industry, expected):
    """Test analysis of market trends for a given industry."""
    result = await MarketingTools.analyze_market_trends(industry)
    assert result == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "campaign_name, platforms, expected",
    [
        (
            "Holiday Push", ["Facebook", "Instagram"],
            "Social media posts for campaign 'Holiday Push' generated for platforms: Facebook, Instagram."
        )
    ]
)
async def test_generate_social_posts(campaign_name, platforms, expected):
    """Test generation of social media posts."""
    result = await MarketingTools.generate_social_posts(campaign_name, platforms)
    assert result == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "event_name, date, location, expected",
    [
        (
            "Product Launch", "2025-08-15", "New York",
            "Marketing event 'Product Launch' scheduled on 2025-08-15 at New York."
        )
    ]
)
async def test_schedule_marketing_event(event_name, date, location, expected):
    """Test scheduling of a marketing event."""
    result = await MarketingTools.schedule_marketing_event(event_name, date, location)
    assert result == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "campaign_name, material_type, expected",
    [
        (
            "Back to School", "flyer",
            "Flyer for campaign 'Back to School' designed."
        )
    ]
)
async def test_design_promotional_material(campaign_name, material_type, expected):
    """Test design of promotional material."""
    result = await MarketingTools.design_promotional_material(campaign_name, material_type)
    assert result == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "page_name, expected",
    [
        (
            "homepage", "Website content on page 'homepage' updated."
        )
    ]
)
async def test_update_website_content(page_name, expected):
    """Test update of website content."""
    result = await MarketingTools.update_website_content(page_name)
    assert result == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "campaign_name, email_list_size, expected",
    [
        (
            "Newsletter Blast", 2500,
            "Email marketing managed for campaign 'Newsletter Blast' targeting 2500 recipients."
        )
    ]
)
async def test_manage_email_marketing(campaign_name, email_list_size, expected):
    """Test managing an email marketing campaign."""
    result = await MarketingTools.manage_email_marketing(campaign_name, email_list_size)
    assert result == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "key_info, expected_substring",
    [
        (
            "Product XYZ release", "generate a press release based on this content Product XYZ release"
        )
    ]
)
async def test_generate_press_release(key_info, expected_substring):
    """Test generation of a press release."""
    result = await MarketingTools.generate_press_release(key_info)
    assert expected_substring in result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "platform, account_name, expected",
    [
        (
            "Twitter", "BrandHandle",
            "Social media account 'BrandHandle' on platform 'Twitter' managed."
        )
    ]
)
async def test_manage_social_media_account(platform, account_name, expected):
    """Test management of a social media account."""
    result = await MarketingTools.manage_social_media_account(platform, account_name)
    assert result == expected


@pytest.mark.asyncio
async def test_create_marketing_campaign_empty_name():
    """Test creation of a marketing campaign with an empty name."""
    result = await MarketingTools.create_marketing_campaign("", "Adults", 1000.0)
    assert "campaign" in result.lower()


def test_generate_tools_json_doc_contains_expected_keys():
    """Test that the generated JSON document contains expected keys."""
    tools_json = MarketingTools.generate_tools_json_doc()
    tools_list = json.loads(tools_json)
    assert isinstance(tools_list, list)
    assert all("agent" in tool for tool in tools_list)
    assert all("function" in tool for tool in tools_list)
    assert all("description" in tool for tool in tools_list)
    assert all("arguments" in tool for tool in tools_list)
    # Optional: check presence of a known function
    assert any(tool["function"] == "create_marketing_campaign" for tool in tools_list)


def test_get_all_kernel_functions_returns_expected_functions():
    """Test that get_all_kernel_functions returns expected functions."""
    kernel_funcs = MarketingTools.get_all_kernel_functions()
    assert isinstance(kernel_funcs, dict)
    assert "create_marketing_campaign" in kernel_funcs
    assert callable(kernel_funcs["create_marketing_campaign"])


@pytest.mark.asyncio
async def test_plan_advertising_budget():
    """Test planning of an advertising budget."""
    result = await MarketingTools.plan_advertising_budget("Winter Sale", 10000.0)
    assert result == "Advertising budget planned for campaign 'Winter Sale' with a total budget of $10000.00."


@pytest.mark.asyncio
async def test_conduct_customer_survey():
    """Test conducting a customer survey."""
    result = await MarketingTools.conduct_customer_survey("Product Feedback", "Adults")
    assert result == "Customer survey on 'Product Feedback' conducted targeting 'Adults'."


@pytest.mark.asyncio
async def test_perform_competitor_analysis():
    """Test competitor analysis."""
    result = await MarketingTools.perform_competitor_analysis("Competitor A")
    assert result == "Competitor analysis performed on 'Competitor A'."


@pytest.mark.asyncio
async def test_track_campaign_performance():
    """Test tracking of campaign performance."""
    result = await MarketingTools.track_campaign_performance("Spring Promo")
    assert result == "Performance of campaign 'Spring Promo' tracked."


@pytest.mark.asyncio
async def test_coordinate_with_sales_team():
    """Test coordination with the sales team."""
    result = await MarketingTools.coordinate_with_sales_team("Black Friday")
    assert result == "Campaign 'Black Friday' coordinated with the sales team."


@pytest.mark.asyncio
async def test_develop_brand_strategy():
    """Test development of a brand strategy."""
    result = await MarketingTools.develop_brand_strategy("BrandX")
    assert result == "Brand strategy developed for 'BrandX'."


@pytest.mark.asyncio
async def test_create_content_calendar():
    """Test creation of a content calendar."""
    result = await MarketingTools.create_content_calendar("August")
    assert result == "Content calendar for 'August' created."


@pytest.mark.asyncio
async def test_plan_product_launch():
    """Test planning of a product launch."""
    result = await MarketingTools.plan_product_launch("GadgetPro", "2025-12-01")
    assert result == "Product launch for 'GadgetPro' planned on 2025-12-01."


@pytest.mark.asyncio
async def test_conduct_market_research():
    """Test conducting market research."""
    result = await MarketingTools.conduct_market_research("Smartphones")
    assert result == "Market research conducted on 'Smartphones'."


@pytest.mark.asyncio
async def test_handle_customer_feedback():
    """Test handling of customer feedback."""
    result = await MarketingTools.handle_customer_feedback("Great service")
    assert result == "Customer feedback handled: Great service."


@pytest.mark.asyncio
async def test_generate_marketing_report():
    """Test generation of a marketing report."""
    result = await MarketingTools.generate_marketing_report("Holiday Campaign")
    assert result == "Marketing report generated for campaign 'Holiday Campaign'."


@pytest.mark.asyncio
async def test_create_video_ad():
    """Test creation of a video advertisement."""
    result = await MarketingTools.create_video_ad("New Product", "YouTube")
    assert result == "Video advertisement 'New Product' created for platform 'YouTube'."


@pytest.mark.asyncio
async def test_conduct_focus_group():
    """Test conducting a focus group study."""
    result = await MarketingTools.conduct_focus_group("Brand Awareness", 15)
    assert result == "Focus group study on 'Brand Awareness' conducted with 15 participants."


@pytest.mark.asyncio
async def test_update_brand_guidelines():
    """Test update of brand guidelines."""
    result = await MarketingTools.update_brand_guidelines("BrandY", "New colors and fonts")
    assert result == "Brand guidelines for 'BrandY' updated."


@pytest.mark.asyncio
async def test_handle_influencer_collaboration():
    """Test handling of influencer collaboration."""
    result = await MarketingTools.handle_influencer_collaboration("InfluencerX", "Summer Blast")
    assert result == "Collaboration with influencer 'InfluencerX' for campaign 'Summer Blast' handled."


@pytest.mark.asyncio
async def test_analyze_customer_behavior():
    """Test analysis of customer behavior in a specific segment."""
    result = await MarketingTools.analyze_customer_behavior("Teenagers")
    assert result == "Customer behavior in segment 'Teenagers' analyzed."


@pytest.mark.asyncio
async def test_manage_loyalty_program():
    """Test management of a loyalty program."""
    result = await MarketingTools.manage_loyalty_program("RewardsPlus", 1200)
    assert result == "Loyalty program 'RewardsPlus' managed with 1200 members."


@pytest.mark.asyncio
async def test_develop_content_strategy():
    """Test development of a content strategy."""
    result = await MarketingTools.develop_content_strategy("Video Focus")
    assert result == "Content strategy 'Video Focus' developed."


@pytest.mark.asyncio
async def test_create_infographic():
    """Test creation of an infographic."""
    result = await MarketingTools.create_infographic("Market Growth 2025")
    assert result == "Infographic 'Market Growth 2025' created."


@pytest.mark.asyncio
async def test_schedule_webinar():
    """Test scheduling of a webinar."""
    result = await MarketingTools.schedule_webinar("Q3 Update", "2025-07-10", "Zoom")
    assert result == "Webinar 'Q3 Update' scheduled on 2025-07-10 via Zoom."


@pytest.mark.asyncio
async def test_manage_online_reputation():
    """Test management of online reputation."""
    result = await MarketingTools.manage_online_reputation("BrandZ")
    assert result == "Online reputation for 'BrandZ' managed."


@pytest.mark.asyncio
async def test_run_email_ab_testing():
    """Test running A/B testing for email campaigns."""
    result = await MarketingTools.run_email_ab_testing("Email Campaign 1")
    assert result == "A/B testing for email campaign 'Email Campaign 1' run."


@pytest.mark.asyncio
async def test_create_podcast_episode():
    """Test creation of a podcast episode."""
    result = await MarketingTools.create_podcast_episode("Tech Talk", "AI Trends")
    assert result == "Podcast episode 'AI Trends' for series 'Tech Talk' created."


@pytest.mark.asyncio
async def test_manage_affiliate_program():
    """Test management of an affiliate program."""
    result = await MarketingTools.manage_affiliate_program("AffiliatePro", 50)
    assert result == "Affiliate program 'AffiliatePro' managed with 50 affiliates."


@pytest.mark.asyncio
async def test_generate_lead_magnets():
    """Test generation of lead magnets."""
    result = await MarketingTools.generate_lead_magnets("Free Guide")
    assert result == "Lead magnet 'Free Guide' generated."


@pytest.mark.asyncio
async def test_organize_trade_show():
    """Test organization of a trade show."""
    result = await MarketingTools.organize_trade_show("B12", "Global Expo")
    assert result == "Trade show 'Global Expo' organized at booth number 'B12'."


@pytest.mark.asyncio
async def test_manage_retention_program():
    """Test management of a customer retention program."""
    result = await MarketingTools.manage_retention_program("RetentionX")
    assert result == "Customer retention program 'RetentionX' managed."


@pytest.mark.asyncio
async def test_run_ppc_campaign():
    """Test running a pay-per-click campaign."""
    result = await MarketingTools.run_ppc_campaign("PPC Spring", 15000.0)
    assert result == "PPC campaign 'PPC Spring' run with a budget of $15000.00."


@pytest.mark.asyncio
async def test_create_case_study():
    """Test creation of a case study."""
    result = await MarketingTools.create_case_study("Success Story", "Client A")
    assert result == "Case study 'Success Story' for client 'Client A' created."


@pytest.mark.asyncio
async def test_generate_lead_nurturing_emails():
    """Test generation of lead nurturing emails."""
    result = await MarketingTools.generate_lead_nurturing_emails("Welcome Sequence", 5)
    assert result == "Lead nurturing email sequence 'Welcome Sequence' generated with 5 steps."


@pytest.mark.asyncio
async def test_manage_crisis_communication():
    """Test management of crisis communication."""
    result = await MarketingTools.manage_crisis_communication("Product Recall")
    assert result == "Crisis communication managed for situation 'Product Recall'."


@pytest.mark.asyncio
async def test_create_interactive_content():
    """Test creation of interactive content."""
    result = await MarketingTools.create_interactive_content("Interactive Quiz")
    assert result == "Interactive content 'Interactive Quiz' created."


@pytest.mark.asyncio
async def test_handle_media_relations():
    """Test handling of media relations."""
    result = await MarketingTools.handle_media_relations("Tech Daily")
    assert result == "Media relations handled with 'Tech Daily'."


@pytest.mark.asyncio
async def test_create_testimonial_video():
    """Test creation of a testimonial video."""
    result = await MarketingTools.create_testimonial_video("Client B")
    assert result == "Testimonial video created for client 'Client B'."


@pytest.mark.asyncio
async def test_manage_event_sponsorship():
    """Test management of event sponsorship."""
    result = await MarketingTools.manage_event_sponsorship("Tech Conference", "SponsorCorp")
    assert result == "Event sponsorship for 'Tech Conference' managed with sponsor 'SponsorCorp'."


@pytest.mark.asyncio
async def test_optimize_conversion_funnel():
    """Test optimization of a conversion funnel stage."""
    result = await MarketingTools.optimize_conversion_funnel("Checkout")
    assert result == "Conversion funnel stage 'Checkout' optimized."


@pytest.mark.asyncio
async def test_run_influencer_campaign():
    """Test running an influencer marketing campaign."""
    result = await MarketingTools.run_influencer_campaign("Winter Campaign", ["Influencer1", "Influencer2"])
    assert result == "Influencer marketing campaign 'Winter Campaign' run with influencers: Influencer1, Influencer2."


@pytest.mark.asyncio
async def test_analyze_website_traffic():
    """Test analysis of website traffic from a specific source."""
    result = await MarketingTools.analyze_website_traffic("Google Ads")
    assert result == "Website traffic analyzed from source 'Google Ads'."


@pytest.mark.asyncio
async def test_develop_customer_personas():
    """Test development of customer personas for a market segment."""
    result = await MarketingTools.develop_customer_personas("Millennials")
    assert result == "Customer personas developed for segment 'Millennials'."
