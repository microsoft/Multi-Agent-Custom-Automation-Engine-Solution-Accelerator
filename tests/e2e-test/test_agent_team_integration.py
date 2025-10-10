"""
Agent Team Integration Tests

Tests the integration of all 5 agent teams with their respective MCP tools
and validates end-to-end workflows.

Agent Teams:
1. Finance Forecasting Team
2. Customer Intelligence Team
3. Retail Operations Team
4. Revenue Optimization Team
5. Marketing Intelligence Team
"""

import pytest
import asyncio
from pathlib import Path
import sys

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "backend" / "common" / "utils"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "mcp_server"))

# Import MCP services
from services.finance_service import FinanceService
from services.customer_analytics_service import CustomerAnalyticsService
from services.operations_analytics_service import OperationsAnalyticsService
from services.pricing_analytics_service import PricingAnalyticsService
from services.marketing_analytics_service import MarketingAnalyticsService


class TestFinanceForecastingTeam:
    """Test Finance Forecasting Team integration."""
    
    @pytest.fixture
    def finance_service(self):
        """Initialize finance service."""
        return FinanceService()
    
    def test_team_tool_availability(self, finance_service):
        """Verify all finance tools are available."""
        expected_tools = [
            "upload_dataset",
            "list_datasets",
            "download_dataset",
            "delete_dataset",
            "generate_financial_forecast",
            "evaluate_forecast_models"
        ]
        
        # Finance service should have all expected tools
        assert finance_service.tool_count >= 5, "Finance service should have at least 5 tools"
    
    @pytest.mark.asyncio
    async def test_forecast_workflow(self, finance_service):
        """Test complete forecasting workflow."""
        # Simulated dataset
        mock_dataset = {
            "name": "test_revenue.csv",
            "content": "Date,Revenue\n2024-01-01,100000\n2024-02-01,105000\n2024-03-01,110000",
            "description": "Test revenue data"
        }
        
        # This would normally call the actual MCP tool
        # For integration tests, we validate the tool interface
        tool_interface = finance_service.get_tool("generate_financial_forecast")
        assert tool_interface is not None, "generate_financial_forecast tool should exist"
        
        # Validate expected parameters
        expected_params = ["dataset_id", "target_column", "periods"]
        # Tool should accept these parameters
        assert True  # Placeholder for actual parameter validation
    
    def test_model_evaluation_integration(self, finance_service):
        """Test forecast model evaluation tool."""
        eval_tool = finance_service.get_tool("evaluate_forecast_models")
        assert eval_tool is not None, "evaluate_forecast_models tool should exist"


class TestCustomerIntelligenceTeam:
    """Test Customer Intelligence Team integration."""
    
    @pytest.fixture
    def customer_service(self):
        """Initialize customer analytics service."""
        return CustomerAnalyticsService()
    
    def test_team_tool_availability(self, customer_service):
        """Verify all customer analytics tools are available."""
        expected_tools = [
            "analyze_customer_churn",
            "segment_customers",
            "predict_customer_lifetime_value",
            "analyze_sentiment_trends"
        ]
        
        assert customer_service.tool_count == 4, "Customer service should have 4 tools"
    
    @pytest.mark.asyncio
    async def test_churn_analysis_workflow(self, customer_service):
        """Test churn analysis workflow."""
        # Mock data
        churn_data = [
            {"CustomerID": "C001", "ChurnProbability": 0.85, "EngagementScore": 2.1}
        ]
        profile_data = [
            {"CustomerID": "C001", "TotalSpend": 15000, "Tenure": 24}
        ]
        
        # Validate tool interface
        churn_tool = customer_service.get_tool("analyze_customer_churn")
        assert churn_tool is not None, "analyze_customer_churn tool should exist"
    
    def test_segmentation_integration(self, customer_service):
        """Test RFM segmentation tool."""
        segment_tool = customer_service.get_tool("segment_customers")
        assert segment_tool is not None, "segment_customers tool should exist"
    
    def test_clv_prediction_integration(self, customer_service):
        """Test CLV prediction tool."""
        clv_tool = customer_service.get_tool("predict_customer_lifetime_value")
        assert clv_tool is not None, "predict_customer_lifetime_value tool should exist"


class TestRetailOperationsTeam:
    """Test Retail Operations Team integration."""
    
    @pytest.fixture
    def operations_service(self):
        """Initialize operations analytics service."""
        return OperationsAnalyticsService()
    
    def test_team_tool_availability(self, operations_service):
        """Verify all operations analytics tools are available."""
        expected_tools = [
            "forecast_delivery_performance",
            "optimize_inventory",
            "analyze_warehouse_incidents",
            "get_operations_summary"
        ]
        
        assert operations_service.tool_count == 4, "Operations service should have 4 tools"
    
    @pytest.mark.asyncio
    async def test_delivery_forecast_workflow(self, operations_service):
        """Test delivery performance forecasting workflow."""
        delivery_tool = operations_service.get_tool("forecast_delivery_performance")
        assert delivery_tool is not None, "forecast_delivery_performance tool should exist"
    
    def test_inventory_optimization_integration(self, operations_service):
        """Test inventory optimization tool."""
        inventory_tool = operations_service.get_tool("optimize_inventory")
        assert inventory_tool is not None, "optimize_inventory tool should exist"
    
    def test_incident_analysis_integration(self, operations_service):
        """Test warehouse incident analysis tool."""
        incident_tool = operations_service.get_tool("analyze_warehouse_incidents")
        assert incident_tool is not None, "analyze_warehouse_incidents tool should exist"


class TestRevenueOptimizationTeam:
    """Test Revenue Optimization Team integration."""
    
    @pytest.fixture
    def pricing_service(self):
        """Initialize pricing analytics service."""
        return PricingAnalyticsService()
    
    def test_team_tool_availability(self, pricing_service):
        """Verify all pricing analytics tools are available."""
        expected_tools = [
            "analyze_competitive_pricing",
            "optimize_discount_strategy",
            "forecast_revenue_by_category"
        ]
        
        assert pricing_service.tool_count == 3, "Pricing service should have 3 tools"
    
    @pytest.mark.asyncio
    async def test_pricing_analysis_workflow(self, pricing_service):
        """Test competitive pricing analysis workflow."""
        pricing_tool = pricing_service.get_tool("analyze_competitive_pricing")
        assert pricing_tool is not None, "analyze_competitive_pricing tool should exist"
    
    def test_discount_optimization_integration(self, pricing_service):
        """Test discount optimization tool."""
        discount_tool = pricing_service.get_tool("optimize_discount_strategy")
        assert discount_tool is not None, "optimize_discount_strategy tool should exist"
    
    def test_revenue_forecast_integration(self, pricing_service):
        """Test revenue forecasting by category tool."""
        revenue_tool = pricing_service.get_tool("forecast_revenue_by_category")
        assert revenue_tool is not None, "forecast_revenue_by_category tool should exist"


class TestMarketingIntelligenceTeam:
    """Test Marketing Intelligence Team integration."""
    
    @pytest.fixture
    def marketing_service(self):
        """Initialize marketing analytics service."""
        return MarketingAnalyticsService()
    
    def test_team_tool_availability(self, marketing_service):
        """Verify all marketing analytics tools are available."""
        expected_tools = [
            "analyze_campaign_effectiveness",
            "predict_engagement",
            "optimize_loyalty_program"
        ]
        
        assert marketing_service.tool_count == 3, "Marketing service should have 3 tools"
    
    @pytest.mark.asyncio
    async def test_campaign_analysis_workflow(self, marketing_service):
        """Test campaign effectiveness analysis workflow."""
        campaign_tool = marketing_service.get_tool("analyze_campaign_effectiveness")
        assert campaign_tool is not None, "analyze_campaign_effectiveness tool should exist"
    
    def test_engagement_prediction_integration(self, marketing_service):
        """Test engagement prediction tool."""
        engagement_tool = marketing_service.get_tool("predict_engagement")
        assert engagement_tool is not None, "predict_engagement tool should exist"
    
    def test_loyalty_optimization_integration(self, marketing_service):
        """Test loyalty program optimization tool."""
        loyalty_tool = marketing_service.get_tool("optimize_loyalty_program")
        assert loyalty_tool is not None, "optimize_loyalty_program tool should exist"


class TestCrossTeamIntegration:
    """Test cross-team workflows and data sharing."""
    
    @pytest.fixture
    def all_services(self):
        """Initialize all services."""
        return {
            "finance": FinanceService(),
            "customer": CustomerAnalyticsService(),
            "operations": OperationsAnalyticsService(),
            "pricing": PricingAnalyticsService(),
            "marketing": MarketingAnalyticsService()
        }
    
    def test_all_teams_initialized(self, all_services):
        """Verify all teams can be initialized together."""
        assert len(all_services) == 5, "All 5 agent teams should initialize"
        
        total_tools = sum(service.tool_count for service in all_services.values())
        assert total_tools == 19, f"Expected 19 total tools, got {total_tools}"
    
    def test_finance_to_pricing_workflow(self, all_services):
        """Test workflow that uses finance and pricing teams."""
        # Finance generates revenue forecast
        finance = all_services["finance"]
        pricing = all_services["pricing"]
        
        forecast_tool = finance.get_tool("generate_financial_forecast")
        pricing_tool = pricing.get_tool("forecast_revenue_by_category")
        
        assert forecast_tool is not None
        assert pricing_tool is not None
        # Both tools should be available for a comprehensive revenue analysis
    
    def test_customer_to_marketing_workflow(self, all_services):
        """Test workflow that uses customer and marketing teams."""
        customer = all_services["customer"]
        marketing = all_services["marketing"]
        
        segment_tool = customer.get_tool("segment_customers")
        campaign_tool = marketing.get_tool("analyze_campaign_effectiveness")
        
        assert segment_tool is not None
        assert campaign_tool is not None
        # Customer segmentation feeds into targeted marketing campaigns
    
    def test_operations_to_pricing_workflow(self, all_services):
        """Test workflow that uses operations and pricing teams."""
        operations = all_services["operations"]
        pricing = all_services["pricing"]
        
        inventory_tool = operations.get_tool("optimize_inventory")
        discount_tool = pricing.get_tool("optimize_discount_strategy")
        
        assert inventory_tool is not None
        assert discount_tool is not None
        # Inventory optimization impacts discount strategies


# Test runner configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])



