"""
Tests for dataset discovery functionality.
Verifies that agents can properly extract and use dataset_id from MCP tool responses.
"""
import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path


def test_dataset_id_extraction_in_finance_forecasting():
    """Verify finance_forecasting agents include dataset_id extraction instructions."""
    config_path = Path("data/agent_teams/finance_forecasting.json")
    
    with open(config_path) as f:
        team_config = json.load(f)
    
    # Check FinancialStrategistAgent
    financial_strategist = team_config['agents'][0]
    assert financial_strategist['name'] == 'FinancialStrategistAgent'
    assert 'dataset_id' in financial_strategist['system_message'].lower()
    assert 'extract the dataset_id' in financial_strategist['system_message'].lower()
    assert 'summarize_financial_dataset(dataset_id=' in financial_strategist['system_message']
    
    # Check DataPreparationAgent
    data_prep = team_config['agents'][1]
    assert data_prep['name'] == 'DataPreparationAgent'
    assert 'dataset_id' in data_prep['system_message'].lower()
    assert 'extract the dataset_id' in data_prep['system_message'].lower()


def test_dataset_id_extraction_in_retail_operations():
    """Verify retail_operations agents include dataset_id extraction instructions."""
    config_path = Path("data/agent_teams/retail_operations.json")
    
    with open(config_path) as f:
        team_config = json.load(f)
    
    # Check OperationsStrategistAgent
    ops_strategist = team_config['agents'][0]
    assert ops_strategist['name'] == 'OperationsStrategistAgent'
    assert 'dataset_id' in ops_strategist['system_message'].lower()
    assert 'extract the dataset_id' in ops_strategist['system_message'].lower()
    
    # Check SupplyChainAnalystAgent
    supply_chain = team_config['agents'][1]
    assert supply_chain['name'] == 'SupplyChainAnalystAgent'
    assert 'dataset_id' in supply_chain['system_message'].lower()
    assert 'extract the dataset_id' in supply_chain['system_message'].lower()


def test_dataset_id_extraction_in_customer_intelligence():
    """Verify customer_intelligence agents include dataset_id extraction instructions."""
    config_path = Path("data/agent_teams/customer_intelligence.json")
    
    with open(config_path) as f:
        team_config = json.load(f)
    
    # Check ChurnPredictionAgent
    churn_prediction = team_config['agents'][0]
    assert churn_prediction['name'] == 'ChurnPredictionAgent'
    assert 'dataset_id' in churn_prediction['system_message'].lower()
    assert 'extract the dataset_id' in churn_prediction['system_message'].lower()


def test_dataset_id_extraction_in_revenue_optimization():
    """Verify revenue_optimization agents include dataset_id extraction instructions."""
    config_path = Path("data/agent_teams/revenue_optimization.json")
    
    with open(config_path) as f:
        team_config = json.load(f)
    
    # Check PricingStrategistAgent
    pricing_strategist = team_config['agents'][0]
    assert pricing_strategist['name'] == 'PricingStrategistAgent'
    assert 'dataset_id' in pricing_strategist['system_message'].lower()
    assert 'extract the dataset_id' in pricing_strategist['system_message'].lower()


def test_dataset_id_extraction_in_marketing_intelligence():
    """Verify marketing_intelligence agents include dataset_id extraction instructions."""
    config_path = Path("data/agent_teams/marketing_intelligence.json")
    
    with open(config_path) as f:
        team_config = json.load(f)
    
    # Check CampaignAnalystAgent
    campaign_analyst = team_config['agents'][0]
    assert campaign_analyst['name'] == 'CampaignAnalystAgent'
    assert 'dataset_id' in campaign_analyst['system_message'].lower()
    assert 'extract the dataset_id' in campaign_analyst['system_message'].lower()


@pytest.mark.asyncio
async def test_get_latest_completed_plan():
    """Test retrieving previous completed plan from PlanService."""
    try:
        import sys
        import os
        # Add src/backend to path for imports
        backend_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'backend')
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
        
        from v3.common.services.plan_service import PlanService
    except ImportError:
        pytest.skip("Backend imports not available in test environment")
    
    # Mock the database factory and container
    with patch('v3.common.services.plan_service.DatabaseFactory') as mock_db_factory:
        mock_memory_store = Mock()
        mock_container = Mock()
        
        # Setup mock to return a completed plan
        mock_container.query_items.return_value = [
            {
                'session_id': 'test-session-123',
                'overall_status': 'completed',
                'agent_messages': [
                    {'content': 'Previous result content', 'agent_type': 'Agent', 'is_final': True}
                ],
                'timestamp': '2024-01-01T00:00:00Z'
            }
        ]
        
        mock_memory_store.container_client_plans = mock_container
        # Make get_database return a coroutine that resolves to mock_memory_store
        mock_db_factory.get_database = AsyncMock(return_value=mock_memory_store)
        
        # Call the method
        result = await PlanService.get_latest_completed_plan('test-session-123', 'user-123')
        
        # Verify result
        assert result is not None
        assert result['session_id'] == 'test-session-123'
        assert result['overall_status'] == 'completed'
        
        # Verify database was called with correct parameters
        mock_db_factory.get_database.assert_called_once_with(user_id='user-123')


@pytest.mark.asyncio
async def test_get_latest_completed_plan_not_found():
    """Test that get_latest_completed_plan returns None when no plan exists."""
    try:
        import sys
        import os
        # Add src/backend to path for imports
        backend_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'backend')
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
        
        from v3.common.services.plan_service import PlanService
    except ImportError:
        pytest.skip("Backend imports not available in test environment")
    
    with patch('v3.common.services.plan_service.DatabaseFactory') as mock_db_factory:
        mock_memory_store = Mock()
        mock_container = Mock()
        
        # Setup mock to return empty list (no plans found)
        mock_container.query_items.return_value = []
        
        mock_memory_store.container_client_plans = mock_container
        # Make get_database return a coroutine that resolves to mock_memory_store
        mock_db_factory.get_database = AsyncMock(return_value=mock_memory_store)
        
        # Call the method
        result = await PlanService.get_latest_completed_plan('nonexistent-session', 'user-123')
        
        # Verify result is None
        assert result is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

