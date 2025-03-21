import os
import sys
import pytest
from unittest.mock import MagicMock
from autogen_core.components.tools import FunctionTool

# Import marketing functions for testing
from src.backend.agents.marketing import (
    create_marketing_campaign,
    analyze_market_trends,
    develop_brand_strategy,
    generate_social_media_posts,
    get_marketing_tools,
    manage_loyalty_program,
    plan_advertising_budget,
    conduct_customer_survey,
    generate_marketing_report,
    perform_competitor_analysis,
    optimize_seo_strategy,
    run_influencer_marketing_campaign,
    schedule_marketing_event,
    design_promotional_material,
    manage_email_marketing,
    track_campaign_performance,
    create_content_calendar,
    update_website_content,
    plan_product_launch,
    handle_customer_feedback,
    generate_press_release,
    run_ppc_campaign,
    create_infographic
)


# Set mock environment variables for Azure and CosmosDB
os.environ["COSMOSDB_ENDPOINT"] = "https://mock-endpoint"
os.environ["COSMOSDB_KEY"] = "mock-key"
os.environ["COSMOSDB_DATABASE"] = "mock-database"
os.environ["COSMOSDB_CONTAINER"] = "mock-container"
os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "mock-deployment-name"
os.environ["AZURE_OPENAI_API_VERSION"] = "2023-01-01"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock-openai-endpoint"

# Mock Azure dependencies
sys.modules["azure.monitor.events.extension"] = MagicMock()


# Test cases
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
async def test_generate_marketing_report():
    result = await generate_marketing_report("Winter Campaign")
    assert "Marketing report generated for campaign 'Winter Campaign'." in result


@pytest.mark.asyncio
async def test_perform_competitor_analysis():
    result = await perform_competitor_analysis("Competitor A")
    assert "Competitor analysis performed on 'Competitor A'." in result


@pytest.mark.asyncio
async def test_perform_competitor_analysis_empty_input():
    result = await perform_competitor_analysis("")
    assert "Competitor analysis performed on ''." in result


@pytest.mark.asyncio
async def test_optimize_seo_strategy():
    result = await optimize_seo_strategy(["keyword1", "keyword2"])
    assert "SEO strategy optimized with keywords: keyword1, keyword2." in result


@pytest.mark.asyncio
async def test_optimize_seo_strategy_empty_keywords():
    result = await optimize_seo_strategy([])
    assert "SEO strategy optimized with keywords: ." in result


@pytest.mark.asyncio
async def test_schedule_marketing_event():
    result = await schedule_marketing_event("Product Launch", "2025-01-30", "Main Hall")
    assert "Marketing event 'Product Launch' scheduled on 2025-01-30 at Main Hall." in result


@pytest.mark.asyncio
async def test_schedule_marketing_event_empty_details():
    result = await schedule_marketing_event("", "", "")
    assert "Marketing event '' scheduled on  at ." in result


@pytest.mark.asyncio
async def test_design_promotional_material():
    result = await design_promotional_material("Spring Sale", "poster")
    assert "Poster for campaign 'Spring Sale' designed." in result


@pytest.mark.asyncio
async def test_design_promotional_material_empty_input():
    result = await design_promotional_material("", "")
    assert " for campaign '' designed." in result


@pytest.mark.asyncio
async def test_manage_email_marketing_large_email_list():
    result = await manage_email_marketing("Holiday Offers", 100000)
    assert "Email marketing managed for campaign 'Holiday Offers' targeting 100000 recipients." in result


@pytest.mark.asyncio
async def test_manage_email_marketing_zero_recipients():
    result = await manage_email_marketing("Holiday Offers", 0)
    assert "Email marketing managed for campaign 'Holiday Offers' targeting 0 recipients." in result


@pytest.mark.asyncio
async def test_track_campaign_performance():
    result = await track_campaign_performance("Fall Promo")
    assert "Performance of campaign 'Fall Promo' tracked." in result


@pytest.mark.asyncio
async def test_track_campaign_performance_empty_name():
    result = await track_campaign_performance("")
    assert "Performance of campaign '' tracked." in result


@pytest.mark.asyncio
async def test_create_content_calendar():
    result = await create_content_calendar("March")
    assert "Content calendar for 'March' created." in result


@pytest.mark.asyncio
async def test_create_content_calendar_empty_month():
    result = await create_content_calendar("")
    assert "Content calendar for '' created." in result


@pytest.mark.asyncio
async def test_update_website_content():
    result = await update_website_content("Homepage")
    assert "Website content on page 'Homepage' updated." in result


@pytest.mark.asyncio
async def test_update_website_content_empty_page():
    result = await update_website_content("")
    assert "Website content on page '' updated." in result


@pytest.mark.asyncio
async def test_plan_product_launch():
    result = await plan_product_launch("Smartwatch", "2025-02-15")
    assert "Product launch for 'Smartwatch' planned on 2025-02-15." in result


@pytest.mark.asyncio
async def test_plan_product_launch_empty_input():
    result = await plan_product_launch("", "")
    assert "Product launch for '' planned on ." in result


@pytest.mark.asyncio
async def test_handle_customer_feedback():
    result = await handle_customer_feedback("Great service!")
    assert "Customer feedback handled: Great service!" in result


@pytest.mark.asyncio
async def test_handle_customer_feedback_empty_feedback():
    result = await handle_customer_feedback("")
    assert "Customer feedback handled: " in result


@pytest.mark.asyncio
async def test_generate_press_release():
    result = await generate_press_release("Key updates for the press release.")
    assert "Identify the content." in result
    assert "generate a press release based on this content Key updates for the press release." in result


@pytest.mark.asyncio
async def test_generate_press_release_empty_content():
    result = await generate_press_release("")
    assert "generate a press release based on this content " in result


@pytest.mark.asyncio
async def test_generate_marketing_report_empty_name():
    result = await generate_marketing_report("")
    assert "Marketing report generated for campaign ''." in result


@pytest.mark.asyncio
async def test_run_ppc_campaign():
    result = await run_ppc_campaign("Spring PPC", 10000.00)
    assert "PPC campaign 'Spring PPC' run with a budget of $10000.00." in result


@pytest.mark.asyncio
async def test_run_ppc_campaign_zero_budget():
    result = await run_ppc_campaign("Spring PPC", 0.00)
    assert "PPC campaign 'Spring PPC' run with a budget of $0.00." in result


@pytest.mark.asyncio
async def test_run_ppc_campaign_large_budget():
    result = await run_ppc_campaign("Spring PPC", 1e7)
    assert "PPC campaign 'Spring PPC' run with a budget of $10000000.00." in result


@pytest.mark.asyncio
async def test_generate_social_media_posts_no_campaign_name():
    """Test generating social media posts with no campaign name."""
    result = await generate_social_media_posts("", ["Twitter", "LinkedIn"])
    assert "Social media posts for campaign '' generated for platforms: Twitter, LinkedIn." in result


@pytest.mark.asyncio
async def test_plan_advertising_budget_negative_value():
    """Test planning an advertising budget with a negative value."""
    result = await plan_advertising_budget("Summer Sale", -10000)
    assert "Advertising budget planned for campaign 'Summer Sale' with a total budget of $-10000.00." in result


@pytest.mark.asyncio
async def test_conduct_customer_survey_invalid_target_group():
    """Test conducting a survey with an invalid target group."""
    result = await conduct_customer_survey("Product Feedback", None)
    assert "Customer survey on 'Product Feedback' conducted targeting 'None'." in result


@pytest.mark.asyncio
async def test_manage_email_marketing_boundary():
    """Test managing email marketing with boundary cases."""
    result = await manage_email_marketing("Year-End Deals", 1)
    assert "Email marketing managed for campaign 'Year-End Deals' targeting 1 recipients." in result


@pytest.mark.asyncio
async def test_create_marketing_campaign_no_audience():
    """Test creating a marketing campaign with no specified audience."""
    result = await create_marketing_campaign("Holiday Sale", "", 10000)
    assert "Marketing campaign 'Holiday Sale' created targeting '' with a budget of $10000.00." in result


@pytest.mark.asyncio
async def test_analyze_market_trends_no_industry():
    """Test analyzing market trends with no specified industry."""
    result = await analyze_market_trends("")
    assert "Market trends analyzed for the '' industry." in result


@pytest.mark.asyncio
async def test_generate_social_media_posts_no_platforms():
    """Test generating social media posts with no specified platforms."""
    result = await generate_social_media_posts("Black Friday", [])
    assert "Social media posts for campaign 'Black Friday' generated for platforms: ." in result


@pytest.mark.asyncio
async def test_plan_advertising_budget_large_budget():
    """Test planning an advertising budget with a large value."""
    result = await plan_advertising_budget("Mega Sale", 1e9)
    assert "Advertising budget planned for campaign 'Mega Sale' with a total budget of $1000000000.00." in result


@pytest.mark.asyncio
async def test_conduct_customer_survey_no_target():
    """Test conducting a customer survey with no specified target group."""
    result = await conduct_customer_survey("Product Feedback", "")
    assert "Customer survey on 'Product Feedback' conducted targeting ''." in result


@pytest.mark.asyncio
async def test_schedule_marketing_event_invalid_date():
    """Test scheduling a marketing event with an invalid date."""
    result = await schedule_marketing_event("Product Launch", "invalid-date", "Main Hall")
    assert "Marketing event 'Product Launch' scheduled on invalid-date at Main Hall." in result


@pytest.mark.asyncio
async def test_design_promotional_material_no_type():
    """Test designing promotional material with no specified type."""
    result = await design_promotional_material("Spring Sale", "")
    assert " for campaign 'Spring Sale' designed." in result


@pytest.mark.asyncio
async def test_manage_email_marketing_no_campaign_name():
    """Test managing email marketing with no specified campaign name."""
    result = await manage_email_marketing("", 5000)
    assert "Email marketing managed for campaign '' targeting 5000 recipients." in result


@pytest.mark.asyncio
async def test_track_campaign_performance_no_data():
    """Test tracking campaign performance with no data."""
    result = await track_campaign_performance(None)
    assert "Performance of campaign 'None' tracked." in result


@pytest.mark.asyncio
async def test_update_website_content_special_characters():
    """Test updating website content with a page name containing special characters."""
    result = await update_website_content("Home!@#$%^&*()Page")
    assert "Website content on page 'Home!@#$%^&*()Page' updated." in result


@pytest.mark.asyncio
async def test_plan_product_launch_past_date():
    """Test planning a product launch with a past date."""
    result = await plan_product_launch("Old Product", "2000-01-01")
    assert "Product launch for 'Old Product' planned on 2000-01-01." in result


@pytest.mark.asyncio
async def test_handle_customer_feedback_long_text():
    """Test handling customer feedback with a very long text."""
    feedback = "Great service!" * 1000
    result = await handle_customer_feedback(feedback)
    assert f"Customer feedback handled: {feedback}" in result


@pytest.mark.asyncio
async def test_generate_press_release_special_characters():
    """Test generating a press release with special characters in content."""
    result = await generate_press_release("Content with special characters !@#$%^&*().")
    assert "generate a press release based on this content Content with special characters !@#$%^&*()." in result


@pytest.mark.asyncio
async def test_run_ppc_campaign_negative_budget():
    """Test running a PPC campaign with a negative budget."""
    result = await run_ppc_campaign("Negative Budget Campaign", -100)
    assert "PPC campaign 'Negative Budget Campaign' run with a budget of $-100.00." in result


@pytest.mark.asyncio
async def test_create_marketing_campaign_no_name():
    """Test creating a marketing campaign with no name."""
    result = await create_marketing_campaign("", "Gen Z", 10000)
    assert "Marketing campaign '' created targeting 'Gen Z' with a budget of $10000.00." in result


@pytest.mark.asyncio
async def test_analyze_market_trends_empty_industry():
    """Test analyzing market trends with an empty industry."""
    result = await analyze_market_trends("")
    assert "Market trends analyzed for the '' industry." in result


@pytest.mark.asyncio
async def test_plan_advertising_budget_no_campaign_name():
    """Test planning an advertising budget with no campaign name."""
    result = await plan_advertising_budget("", 20000)
    assert "Advertising budget planned for campaign '' with a total budget of $20000.00." in result


@pytest.mark.asyncio
async def test_conduct_customer_survey_no_topic():
    """Test conducting a survey with no topic."""
    result = await conduct_customer_survey("", "Frequent Buyers")
    assert "Customer survey on '' conducted targeting 'Frequent Buyers'." in result


@pytest.mark.asyncio
async def test_generate_marketing_report_no_name():
    """Test generating a marketing report with no name."""
    result = await generate_marketing_report("")
    assert "Marketing report generated for campaign ''." in result


@pytest.mark.asyncio
async def test_perform_competitor_analysis_no_competitor():
    """Test performing competitor analysis with no competitor specified."""
    result = await perform_competitor_analysis("")
    assert "Competitor analysis performed on ''." in result


@pytest.mark.asyncio
async def test_manage_email_marketing_no_recipients():
    """Test managing email marketing with no recipients."""
    result = await manage_email_marketing("Holiday Campaign", 0)
    assert "Email marketing managed for campaign 'Holiday Campaign' targeting 0 recipients." in result


# Include all imports and environment setup from the original file.

# New test cases added here to improve coverage:


@pytest.mark.asyncio
async def test_create_content_calendar_no_month():
    """Test creating a content calendar with no month provided."""
    result = await create_content_calendar("")
    assert "Content calendar for '' created." in result


@pytest.mark.asyncio
async def test_schedule_marketing_event_no_location():
    """Test scheduling a marketing event with no location provided."""
    result = await schedule_marketing_event("Event Name", "2025-05-01", "")
    assert "Marketing event 'Event Name' scheduled on 2025-05-01 at ." in result


@pytest.mark.asyncio
async def test_generate_social_media_posts_missing_platforms():
    """Test generating social media posts with missing platforms."""
    result = await generate_social_media_posts("Campaign Name", [])
    assert "Social media posts for campaign 'Campaign Name' generated for platforms: ." in result


@pytest.mark.asyncio
async def test_handle_customer_feedback_no_text():
    """Test handling customer feedback with no feedback provided."""
    result = await handle_customer_feedback("")
    assert "Customer feedback handled: " in result


@pytest.mark.asyncio
async def test_develop_brand_strategy():
    """Test developing a brand strategy."""
    result = await develop_brand_strategy("My Brand")
    assert "Brand strategy developed for 'My Brand'." in result


@pytest.mark.asyncio
async def test_create_infographic():
    """Test creating an infographic."""
    result = await create_infographic("Top 10 Marketing Tips")
    assert "Infographic 'Top 10 Marketing Tips' created." in result


@pytest.mark.asyncio
async def test_run_influencer_marketing_campaign():
    """Test running an influencer marketing campaign."""
    result = await run_influencer_marketing_campaign(
        "Launch Campaign", ["Influencer A", "Influencer B"]
    )
    assert "Influencer marketing campaign 'Launch Campaign' run with influencers: Influencer A, Influencer B." in result


@pytest.mark.asyncio
async def test_manage_loyalty_program():
    """Test managing a loyalty program."""
    result = await manage_loyalty_program("Rewards Club", 5000)
    assert "Loyalty program 'Rewards Club' managed with 5000 members." in result


@pytest.mark.asyncio
async def test_create_marketing_campaign_empty_fields():
    """Test creating a marketing campaign with empty fields."""
    result = await create_marketing_campaign("", "", 0)
    assert "Marketing campaign '' created targeting '' with a budget of $0.00." in result


@pytest.mark.asyncio
async def test_plan_product_launch_empty_fields():
    """Test planning a product launch with missing fields."""
    result = await plan_product_launch("", "")
    assert "Product launch for '' planned on ." in result


@pytest.mark.asyncio
async def test_get_marketing_tools():
    """Test retrieving the list of marketing tools."""
    tools = get_marketing_tools()
    assert len(tools) > 0
    assert all(isinstance(tool, FunctionTool) for tool in tools)


@pytest.mark.asyncio
async def test_get_marketing_tools_complete():
    """Test that all tools are included in the marketing tools list."""
    tools = get_marketing_tools()
    assert len(tools) > 40  # Assuming there are more than 40 tools
    assert any(tool.name == "create_marketing_campaign" for tool in tools)
    assert all(isinstance(tool, FunctionTool) for tool in tools)


@pytest.mark.asyncio
async def test_schedule_marketing_event_invalid_location():
    """Test scheduling a marketing event with invalid location."""
    result = await schedule_marketing_event("Event Name", "2025-12-01", None)
    assert "Marketing event 'Event Name' scheduled on 2025-12-01 at None." in result


@pytest.mark.asyncio
async def test_plan_product_launch_no_date():
    """Test planning a product launch with no launch date."""
    result = await plan_product_launch("Product X", None)
    assert "Product launch for 'Product X' planned on None." in result


@pytest.mark.asyncio
async def test_handle_customer_feedback_none():
    """Test handling customer feedback with None."""
    result = await handle_customer_feedback(None)
    assert "Customer feedback handled: None" in result


@pytest.mark.asyncio
async def test_generate_press_release_no_key_info():
    """Test generating a press release with no key information."""
    result = await generate_press_release("")
    assert "generate a press release based on this content " in result


@pytest.mark.asyncio
async def test_schedule_marketing_event_invalid_inputs():
    """Test scheduling marketing event with invalid inputs."""
    result = await schedule_marketing_event("", None, None)
    assert "Marketing event '' scheduled on None at None." in result


@pytest.mark.asyncio
async def test_plan_product_launch_invalid_date():
    """Test planning a product launch with invalid date."""
    result = await plan_product_launch("New Product", "not-a-date")
    assert "Product launch for 'New Product' planned on not-a-date." in result


@pytest.mark.asyncio
async def test_handle_customer_feedback_empty_input():
    """Test handling customer feedback with empty input."""
    result = await handle_customer_feedback("")
    assert "Customer feedback handled: " in result


@pytest.mark.asyncio
async def test_manage_email_marketing_invalid_recipients():
    """Test managing email marketing with invalid recipients."""
    result = await manage_email_marketing("Campaign X", -5)
    assert "Email marketing managed for campaign 'Campaign X' targeting -5 recipients." in result


@pytest.mark.asyncio
async def test_track_campaign_performance_none():
    """Test tracking campaign performance with None."""
    result = await track_campaign_performance(None)
    assert "Performance of campaign 'None' tracked." in result


@pytest.fixture
def mock_agent_dependencies():
    """Provide mocked dependencies for the MarketingAgent."""
    return {
        "mock_model_client": MagicMock(),
        "mock_session_id": "session123",
        "mock_user_id": "user123",
        "mock_context": MagicMock(),
        "mock_tools": [MagicMock()],
        "mock_agent_id": "agent123",
    }
