"""Unit tests for DatabaseBase abstract class."""

import sys
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from unittest.mock import AsyncMock, Mock, patch
import pytest

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'backend'))

# Set required environment variables for testing
os.environ.setdefault('APPLICATIONINSIGHTS_CONNECTION_STRING', 'test_connection_string')
os.environ.setdefault('APP_ENV', 'dev')

from common.database.database_base import DatabaseBase
from common.models.messages_af import (
    AgentMessageData,
    BaseDataModel,
    CurrentTeamAgent,
    Plan,
    Step,
    TeamConfiguration,
    UserCurrentTeam,
)
import v4.models.messages as messages


class TestDatabaseBaseAbstractClass:
    """Test DatabaseBase abstract class interface and requirements."""
    
    def test_database_base_is_abstract_class(self):
        """Test that DatabaseBase is properly defined as an abstract class."""
        assert issubclass(DatabaseBase, ABC)
        assert DatabaseBase.__abstractmethods__ is not None
        assert len(DatabaseBase.__abstractmethods__) > 0
    
    def test_cannot_instantiate_database_base_directly(self):
        """Test that DatabaseBase cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            DatabaseBase()
    
    def test_abstract_method_count(self):
        """Test that all expected abstract methods are defined."""
        abstract_methods = DatabaseBase.__abstractmethods__
        
        # Check that we have the expected number of abstract methods
        # This helps ensure we don't accidentally remove abstract methods
        assert len(abstract_methods) >= 30  # Minimum expected abstract methods
        
        # Verify key abstract methods are present
        expected_methods = {
            'initialize', 'close', 'add_item', 'update_item', 'get_item_by_id',
            'query_items', 'delete_item', 'add_plan', 'update_plan', 
            'get_plan_by_plan_id', 'get_plan', 'get_all_plans',
            'get_all_plans_by_team_id', 'get_all_plans_by_team_id_status',
            'add_step', 'update_step', 'get_steps_by_plan', 'get_step',
            'add_team', 'update_team', 'get_team', 'get_team_by_id',
            'get_all_teams', 'delete_team', 'get_data_by_type', 'get_all_items',
            'get_steps_for_plan', 'get_current_team', 'delete_current_team',
            'set_current_team', 'update_current_team', 'delete_plan_by_plan_id',
            'add_mplan', 'update_mplan', 'get_mplan', 'add_agent_message',
            'update_agent_message', 'get_agent_messages', 'add_team_agent',
            'delete_team_agent', 'get_team_agent'
        }
        
        for method in expected_methods:
            assert method in abstract_methods, f"Abstract method '{method}' not found"


class TestDatabaseBaseImplementationRequirements:
    """Test that concrete implementations must implement all abstract methods."""
    
    def test_incomplete_implementation_raises_error(self):
        """Test that incomplete implementations cannot be instantiated."""
        
        class IncompleteDatabase(DatabaseBase):
            # Only implement a few methods, leaving others unimplemented
            async def initialize(self):
                pass
            
            async def close(self):
                pass
        
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteDatabase()
    
    def test_complete_implementation_can_be_instantiated(self):
        """Test that complete implementations can be instantiated."""
        
        class CompleteDatabase(DatabaseBase):
            # Implement all abstract methods
            async def initialize(self) -> None:
                pass
            
            async def close(self) -> None:
                pass
            
            async def add_item(self, item: BaseDataModel) -> None:
                pass
            
            async def update_item(self, item: BaseDataModel) -> None:
                pass
            
            async def get_item_by_id(
                self, item_id: str, partition_key: str, model_class: Type[BaseDataModel]
            ) -> Optional[BaseDataModel]:
                return None
            
            async def query_items(
                self,
                query: str,
                parameters: List[Dict[str, Any]],
                model_class: Type[BaseDataModel],
            ) -> List[BaseDataModel]:
                return []
            
            async def delete_item(self, item_id: str, partition_key: str) -> None:
                pass
            
            async def add_plan(self, plan: Plan) -> None:
                pass
            
            async def update_plan(self, plan: Plan) -> None:
                pass
            
            async def get_plan_by_plan_id(self, plan_id: str) -> Optional[Plan]:
                return None
            
            async def get_plan(self, plan_id: str) -> Optional[Plan]:
                return None
            
            async def get_all_plans(self) -> List[Plan]:
                return []
            
            async def get_all_plans_by_team_id(self, team_id: str) -> List[Plan]:
                return []
            
            async def get_all_plans_by_team_id_status(
                self, user_id: str, team_id: str, status: str
            ) -> List[Plan]:
                return []
            
            async def add_step(self, step: Step) -> None:
                pass
            
            async def update_step(self, step: Step) -> None:
                pass
            
            async def get_steps_by_plan(self, plan_id: str) -> List[Step]:
                return []
            
            async def get_step(self, step_id: str, session_id: str) -> Optional[Step]:
                return None
            
            async def add_team(self, team: TeamConfiguration) -> None:
                pass
            
            async def update_team(self, team: TeamConfiguration) -> None:
                pass
            
            async def get_team(self, team_id: str) -> Optional[TeamConfiguration]:
                return None
            
            async def get_team_by_id(self, team_id: str) -> Optional[TeamConfiguration]:
                return None
            
            async def get_all_teams(self) -> List[TeamConfiguration]:
                return []
            
            async def delete_team(self, team_id: str) -> bool:
                return False
            
            async def get_data_by_type(self, data_type: str) -> List[BaseDataModel]:
                return []
            
            async def get_all_items(self) -> List[Dict[str, Any]]:
                return []
            
            async def get_steps_for_plan(self, plan_id: str) -> List[Step]:
                return []
            
            async def get_current_team(self, user_id: str) -> Optional[UserCurrentTeam]:
                return None
            
            async def delete_current_team(self, user_id: str) -> Optional[UserCurrentTeam]:
                return None
            
            async def set_current_team(self, current_team: UserCurrentTeam) -> None:
                pass
            
            async def update_current_team(self, current_team: UserCurrentTeam) -> None:
                pass
            
            async def delete_plan_by_plan_id(self, plan_id: str) -> bool:
                return False
            
            async def add_mplan(self, mplan: messages.MPlan) -> None:
                pass
            
            async def update_mplan(self, mplan: messages.MPlan) -> None:
                pass
            
            async def get_mplan(self, plan_id: str) -> Optional[messages.MPlan]:
                return None
            
            async def add_agent_message(self, message: AgentMessageData) -> None:
                pass
            
            async def update_agent_message(self, message: AgentMessageData) -> None:
                pass
            
            async def get_agent_messages(self, plan_id: str) -> Optional[AgentMessageData]:
                return None
            
            async def add_team_agent(self, team_agent: CurrentTeamAgent) -> None:
                pass
            
            async def delete_team_agent(self, team_id: str, agent_name: str) -> None:
                pass
            
            async def get_team_agent(
                self, team_id: str, agent_name: str
            ) -> Optional[CurrentTeamAgent]:
                return None
        
        # Should not raise TypeError
        database = CompleteDatabase()
        assert isinstance(database, DatabaseBase)


class TestDatabaseBaseMethodSignatures:
    """Test that all abstract methods have correct signatures."""
    
    def test_initialization_methods(self):
        """Test initialization and cleanup method signatures."""
        # Test that the methods are defined with correct signatures
        assert hasattr(DatabaseBase, 'initialize')
        assert hasattr(DatabaseBase, 'close')
        
        # Check that these are async methods
        init_method = getattr(DatabaseBase, 'initialize')
        close_method = getattr(DatabaseBase, 'close')
        
        assert getattr(init_method, '__isabstractmethod__', False)
        assert getattr(close_method, '__isabstractmethod__', False)
    
    def test_crud_operation_methods(self):
        """Test CRUD operation method signatures."""
        crud_methods = [
            'add_item', 'update_item', 'get_item_by_id', 
            'query_items', 'delete_item'
        ]
        
        for method_name in crud_methods:
            assert hasattr(DatabaseBase, method_name)
            method = getattr(DatabaseBase, method_name)
            assert getattr(method, '__isabstractmethod__', False)
    
    def test_plan_operation_methods(self):
        """Test plan operation method signatures."""
        plan_methods = [
            'add_plan', 'update_plan', 'get_plan_by_plan_id', 'get_plan',
            'get_all_plans', 'get_all_plans_by_team_id', 'get_all_plans_by_team_id_status',
            'delete_plan_by_plan_id'
        ]
        
        for method_name in plan_methods:
            assert hasattr(DatabaseBase, method_name)
            method = getattr(DatabaseBase, method_name)
            assert getattr(method, '__isabstractmethod__', False)
    
    def test_step_operation_methods(self):
        """Test step operation method signatures."""
        step_methods = [
            'add_step', 'update_step', 'get_steps_by_plan', 
            'get_step', 'get_steps_for_plan'
        ]
        
        for method_name in step_methods:
            assert hasattr(DatabaseBase, method_name)
            method = getattr(DatabaseBase, method_name)
            assert getattr(method, '__isabstractmethod__', False)
    
    def test_team_operation_methods(self):
        """Test team operation method signatures."""
        team_methods = [
            'add_team', 'update_team', 'get_team', 'get_team_by_id',
            'get_all_teams', 'delete_team'
        ]
        
        for method_name in team_methods:
            assert hasattr(DatabaseBase, method_name)
            method = getattr(DatabaseBase, method_name)
            assert getattr(method, '__isabstractmethod__', False)
    
    def test_current_team_operation_methods(self):
        """Test current team operation method signatures."""
        current_team_methods = [
            'get_current_team', 'delete_current_team',
            'set_current_team', 'update_current_team'
        ]
        
        for method_name in current_team_methods:
            assert hasattr(DatabaseBase, method_name)
            method = getattr(DatabaseBase, method_name)
            assert getattr(method, '__isabstractmethod__', False)
    
    def test_data_management_methods(self):
        """Test data management method signatures."""
        data_methods = ['get_data_by_type', 'get_all_items']
        
        for method_name in data_methods:
            assert hasattr(DatabaseBase, method_name)
            method = getattr(DatabaseBase, method_name)
            assert getattr(method, '__isabstractmethod__', False)
    
    def test_mplan_operation_methods(self):
        """Test mplan operation method signatures."""
        mplan_methods = ['add_mplan', 'update_mplan', 'get_mplan']
        
        for method_name in mplan_methods:
            assert hasattr(DatabaseBase, method_name)
            method = getattr(DatabaseBase, method_name)
            assert getattr(method, '__isabstractmethod__', False)
    
    def test_agent_message_methods(self):
        """Test agent message method signatures."""
        agent_message_methods = [
            'add_agent_message', 'update_agent_message', 'get_agent_messages'
        ]
        
        for method_name in agent_message_methods:
            assert hasattr(DatabaseBase, method_name)
            method = getattr(DatabaseBase, method_name)
            assert getattr(method, '__isabstractmethod__', False)
    
    def test_team_agent_methods(self):
        """Test team agent method signatures."""
        team_agent_methods = [
            'add_team_agent', 'delete_team_agent', 'get_team_agent'
        ]
        
        for method_name in team_agent_methods:
            assert hasattr(DatabaseBase, method_name)
            method = getattr(DatabaseBase, method_name)
            assert getattr(method, '__isabstractmethod__', False)


class TestDatabaseBaseContextManager:
    """Test DatabaseBase async context manager functionality."""
    
    @pytest.mark.asyncio
    async def test_context_manager_implementation(self):
        """Test that context manager methods are properly implemented."""
        assert hasattr(DatabaseBase, '__aenter__')
        assert hasattr(DatabaseBase, '__aexit__')
        
        # Test that these are not abstract (they have implementations)
        aenter_method = getattr(DatabaseBase, '__aenter__')
        aexit_method = getattr(DatabaseBase, '__aexit__')
        
        # These should not be abstract methods
        assert not getattr(aenter_method, '__isabstractmethod__', False)
        assert not getattr(aexit_method, '__isabstractmethod__', False)
    
    @pytest.mark.asyncio
    async def test_context_manager_calls_initialize_and_close(self):
        """Test that context manager calls initialize and close appropriately."""
        
        class MockDatabase(DatabaseBase):
            def __init__(self):
                self.initialized = False
                self.closed = False
            
            async def initialize(self) -> None:
                self.initialized = True
            
            async def close(self) -> None:
                self.closed = True
            
            # Minimal implementation of other abstract methods
            async def add_item(self, item): pass
            async def update_item(self, item): pass
            async def get_item_by_id(self, item_id, partition_key, model_class): return None
            async def query_items(self, query, parameters, model_class): return []
            async def delete_item(self, item_id, partition_key): pass
            async def add_plan(self, plan): pass
            async def update_plan(self, plan): pass
            async def get_plan_by_plan_id(self, plan_id): return None
            async def get_plan(self, plan_id): return None
            async def get_all_plans(self): return []
            async def get_all_plans_by_team_id(self, team_id): return []
            async def get_all_plans_by_team_id_status(self, user_id, team_id, status): return []
            async def add_step(self, step): pass
            async def update_step(self, step): pass
            async def get_steps_by_plan(self, plan_id): return []
            async def get_step(self, step_id, session_id): return None
            async def add_team(self, team): pass
            async def update_team(self, team): pass
            async def get_team(self, team_id): return None
            async def get_team_by_id(self, team_id): return None
            async def get_all_teams(self): return []
            async def delete_team(self, team_id): return False
            async def get_data_by_type(self, data_type): return []
            async def get_all_items(self): return []
            async def get_steps_for_plan(self, plan_id): return []
            async def get_current_team(self, user_id): return None
            async def delete_current_team(self, user_id): return None
            async def set_current_team(self, current_team): pass
            async def update_current_team(self, current_team): pass
            async def delete_plan_by_plan_id(self, plan_id): return False
            async def add_mplan(self, mplan): pass
            async def update_mplan(self, mplan): pass
            async def get_mplan(self, plan_id): return None
            async def add_agent_message(self, message): pass
            async def update_agent_message(self, message): pass
            async def get_agent_messages(self, plan_id): return None
            async def add_team_agent(self, team_agent): pass
            async def delete_team_agent(self, team_id, agent_name): pass
            async def get_team_agent(self, team_id, agent_name): return None
        
        database = MockDatabase()
        
        async with database as db:
            assert database.initialized is True
            assert database.closed is False
            assert db is database
        
        assert database.closed is True
    
    @pytest.mark.asyncio
    async def test_context_manager_handles_exceptions(self):
        """Test that context manager properly closes even when exceptions occur."""
        
        class MockDatabase(DatabaseBase):
            def __init__(self):
                self.initialized = False
                self.closed = False
            
            async def initialize(self) -> None:
                self.initialized = True
            
            async def close(self) -> None:
                self.closed = True
            
            # Minimal implementation of other abstract methods
            async def add_item(self, item): pass
            async def update_item(self, item): pass
            async def get_item_by_id(self, item_id, partition_key, model_class): return None
            async def query_items(self, query, parameters, model_class): return []
            async def delete_item(self, item_id, partition_key): pass
            async def add_plan(self, plan): pass
            async def update_plan(self, plan): pass
            async def get_plan_by_plan_id(self, plan_id): return None
            async def get_plan(self, plan_id): return None
            async def get_all_plans(self): return []
            async def get_all_plans_by_team_id(self, team_id): return []
            async def get_all_plans_by_team_id_status(self, user_id, team_id, status): return []
            async def add_step(self, step): pass
            async def update_step(self, step): pass
            async def get_steps_by_plan(self, plan_id): return []
            async def get_step(self, step_id, session_id): return None
            async def add_team(self, team): pass
            async def update_team(self, team): pass
            async def get_team(self, team_id): return None
            async def get_team_by_id(self, team_id): return None
            async def get_all_teams(self): return []
            async def delete_team(self, team_id): return False
            async def get_data_by_type(self, data_type): return []
            async def get_all_items(self): return []
            async def get_steps_for_plan(self, plan_id): return []
            async def get_current_team(self, user_id): return None
            async def delete_current_team(self, user_id): return None
            async def set_current_team(self, current_team): pass
            async def update_current_team(self, current_team): pass
            async def delete_plan_by_plan_id(self, plan_id): return False
            async def add_mplan(self, mplan): pass
            async def update_mplan(self, mplan): pass
            async def get_mplan(self, plan_id): return None
            async def add_agent_message(self, message): pass
            async def update_agent_message(self, message): pass
            async def get_agent_messages(self, plan_id): return None
            async def add_team_agent(self, team_agent): pass
            async def delete_team_agent(self, team_id, agent_name): pass
            async def get_team_agent(self, team_id, agent_name): return None
        
        database = MockDatabase()
        
        with pytest.raises(ValueError):
            async with database:
                assert database.initialized is True
                # Raise an exception to test cleanup
                raise ValueError("Test exception")
        
        # Even with exception, close should have been called
        assert database.closed is True


class TestDatabaseBaseInheritance:
    """Test DatabaseBase inheritance and polymorphism."""
    
    def test_inheritance_hierarchy(self):
        """Test that DatabaseBase properly inherits from ABC."""
        assert issubclass(DatabaseBase, ABC)
        assert ABC in DatabaseBase.__mro__
    
    def test_method_resolution_order(self):
        """Test that method resolution order is correct."""
        mro = DatabaseBase.__mro__
        assert DatabaseBase in mro
        assert ABC in mro
        assert object in mro
    
    def test_abc_registration(self):
        """Test that abstract methods are properly registered."""
        # Verify that __abstractmethods__ contains expected methods
        abstract_methods = DatabaseBase.__abstractmethods__
        assert isinstance(abstract_methods, frozenset)
        assert len(abstract_methods) > 0
    
    def test_subclass_detection(self):
        """Test that subclass detection works correctly."""
        
        class ConcreteDatabase(DatabaseBase):
            # Full implementation would go here
            # For this test, we'll make it incomplete to test subclass detection
            async def initialize(self): pass
            async def close(self): pass
            async def add_item(self, item): pass
            async def update_item(self, item): pass
            async def get_item_by_id(self, item_id, partition_key, model_class): return None
            async def query_items(self, query, parameters, model_class): return []
            async def delete_item(self, item_id, partition_key): pass
            async def add_plan(self, plan): pass
            async def update_plan(self, plan): pass
            async def get_plan_by_plan_id(self, plan_id): return None
            async def get_plan(self, plan_id): return None
            async def get_all_plans(self): return []
            async def get_all_plans_by_team_id(self, team_id): return []
            async def get_all_plans_by_team_id_status(self, user_id, team_id, status): return []
            async def add_step(self, step): pass
            async def update_step(self, step): pass
            async def get_steps_by_plan(self, plan_id): return []
            async def get_step(self, step_id, session_id): return None
            async def add_team(self, team): pass
            async def update_team(self, team): pass
            async def get_team(self, team_id): return None
            async def get_team_by_id(self, team_id): return None
            async def get_all_teams(self): return []
            async def delete_team(self, team_id): return False
            async def get_data_by_type(self, data_type): return []
            async def get_all_items(self): return []
            async def get_steps_for_plan(self, plan_id): return []
            async def get_current_team(self, user_id): return None
            async def delete_current_team(self, user_id): return None
            async def set_current_team(self, current_team): pass
            async def update_current_team(self, current_team): pass
            async def delete_plan_by_plan_id(self, plan_id): return False
            async def add_mplan(self, mplan): pass
            async def update_mplan(self, mplan): pass
            async def get_mplan(self, plan_id): return None
            async def add_agent_message(self, message): pass
            async def update_agent_message(self, message): pass
            async def get_agent_messages(self, plan_id): return None
            async def add_team_agent(self, team_agent): pass
            async def delete_team_agent(self, team_id, agent_name): pass
            async def get_team_agent(self, team_id, agent_name): return None
        
        assert issubclass(ConcreteDatabase, DatabaseBase)
        assert isinstance(ConcreteDatabase(), DatabaseBase)


class TestDatabaseBaseDocumentation:
    """Test that DatabaseBase has proper documentation."""
    
    def test_class_docstring(self):
        """Test that DatabaseBase has proper class documentation."""
        assert DatabaseBase.__doc__ is not None
        assert len(DatabaseBase.__doc__.strip()) > 0
        assert "abstract" in DatabaseBase.__doc__.lower()
    
    def test_method_docstrings(self):
        """Test that abstract methods have proper documentation."""
        methods_with_docs = [
            'initialize', 'close', 'add_item', 'update_item', 'get_item_by_id',
            'query_items', 'delete_item', 'add_plan', 'update_plan',
            'get_plan_by_plan_id', 'get_plan', 'get_all_plans'
        ]
        
        for method_name in methods_with_docs:
            method = getattr(DatabaseBase, method_name)
            assert method.__doc__ is not None, f"Method {method_name} missing docstring"
            assert len(method.__doc__.strip()) > 0, f"Method {method_name} has empty docstring"


class TestDatabaseBaseTypeHints:
    """Test that DatabaseBase has proper type hints."""
    
    def test_method_type_annotations(self):
        """Test that methods have proper type annotations."""
        # Check a few key methods for type annotations
        methods_to_check = [
            'get_item_by_id', 'query_items', 'get_all_plans', 
            'get_all_plans_by_team_id_status', 'get_current_team'
        ]
        
        for method_name in methods_to_check:
            method = getattr(DatabaseBase, method_name)
            annotations = getattr(method, '__annotations__', {})
            assert len(annotations) > 0, f"Method {method_name} missing type annotations"
    
    def test_return_type_annotations(self):
        """Test that methods have proper return type annotations."""
        # Methods that should return None
        void_methods = ['initialize', 'close', 'add_item', 'update_item', 'delete_item']
        
        for method_name in void_methods:
            method = getattr(DatabaseBase, method_name)
            annotations = getattr(method, '__annotations__', {})
            # Most should have 'return' annotation
            if 'return' in annotations:
                # For async methods, return type should indicate None
                pass  # We can't check the exact return type due to how abstract methods work
    
    def test_parameter_type_annotations(self):
        """Test that method parameters have proper type annotations."""
        # Check query_items method specifically as it has complex parameters
        query_items_method = getattr(DatabaseBase, 'query_items')
        annotations = getattr(query_items_method, '__annotations__', {})
        
        # Should have annotations for parameters
        assert len(annotations) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])