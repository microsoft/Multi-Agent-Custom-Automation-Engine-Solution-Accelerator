"""Unit tests for backend.v4.callbacks.global_debug module."""
import sys
from unittest.mock import Mock

# Mock the dependencies before importing the module under test
sys.modules['azure'] = Mock()
sys.modules['azure.ai'] = Mock()
sys.modules['azure.ai.inference'] = Mock() 
sys.modules['azure.ai.inference.models'] = Mock()

sys.modules['agent_framework'] = Mock()
sys.modules['agent_framework.ai'] = Mock()
sys.modules['agent_framework.ai.reasoning'] = Mock()
sys.modules['agent_framework.ai.reasoning.chat'] = Mock()

sys.modules['common'] = Mock()
sys.modules['common.logging'] = Mock()

sys.modules['v4'] = Mock()
sys.modules['v4.config'] = Mock()
sys.modules['v4.config.settings'] = Mock()

# Import the module under test
from backend.v4.callbacks.global_debug import DebugGlobalAccess


class TestDebugGlobalAccess:
    """Test cases for DebugGlobalAccess class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Reset the class variable to ensure clean state for each test
        DebugGlobalAccess._managers = []

    def teardown_method(self):
        """Clean up after each test method."""
        # Reset the class variable to ensure clean state after each test
        DebugGlobalAccess._managers = []

    def test_initial_state(self):
        """Test that the class starts with empty managers list."""
        assert DebugGlobalAccess._managers == []
        assert DebugGlobalAccess.get_managers() == []

    def test_add_single_manager(self):
        """Test adding a single manager."""
        mock_manager = Mock()
        mock_manager.name = "TestManager1"
        
        DebugGlobalAccess.add_manager(mock_manager)
        
        managers = DebugGlobalAccess.get_managers()
        assert len(managers) == 1
        assert managers[0] is mock_manager
        assert managers[0].name == "TestManager1"

    def test_add_multiple_managers(self):
        """Test adding multiple managers."""
        mock_manager1 = Mock()
        mock_manager1.name = "Manager1"
        mock_manager2 = Mock()
        mock_manager2.name = "Manager2"
        mock_manager3 = Mock()
        mock_manager3.name = "Manager3"
        
        DebugGlobalAccess.add_manager(mock_manager1)
        DebugGlobalAccess.add_manager(mock_manager2)
        DebugGlobalAccess.add_manager(mock_manager3)
        
        managers = DebugGlobalAccess.get_managers()
        assert len(managers) == 3
        assert managers[0] is mock_manager1
        assert managers[1] is mock_manager2
        assert managers[2] is mock_manager3

    def test_add_manager_order_preservation(self):
        """Test that managers are added in the correct order."""
        managers_to_add = []
        for i in range(5):
            manager = Mock()
            manager.id = i
            managers_to_add.append(manager)
            DebugGlobalAccess.add_manager(manager)
        
        retrieved_managers = DebugGlobalAccess.get_managers()
        assert len(retrieved_managers) == 5
        
        for i, manager in enumerate(retrieved_managers):
            assert manager.id == i

    def test_add_none_manager(self):
        """Test adding None as a manager."""
        DebugGlobalAccess.add_manager(None)
        
        managers = DebugGlobalAccess.get_managers()
        assert len(managers) == 1
        assert managers[0] is None

    def test_add_duplicate_managers(self):
        """Test adding the same manager multiple times."""
        mock_manager = Mock()
        mock_manager.name = "DuplicateManager"
        
        DebugGlobalAccess.add_manager(mock_manager)
        DebugGlobalAccess.add_manager(mock_manager)
        DebugGlobalAccess.add_manager(mock_manager)
        
        managers = DebugGlobalAccess.get_managers()
        assert len(managers) == 3
        assert all(manager is mock_manager for manager in managers)

    def test_add_different_types_of_managers(self):
        """Test adding different types of objects as managers."""
        string_manager = "string_manager"
        int_manager = 42
        list_manager = [1, 2, 3]
        dict_manager = {"type": "dict_manager"}
        mock_manager = Mock()
        
        DebugGlobalAccess.add_manager(string_manager)
        DebugGlobalAccess.add_manager(int_manager)
        DebugGlobalAccess.add_manager(list_manager)
        DebugGlobalAccess.add_manager(dict_manager)
        DebugGlobalAccess.add_manager(mock_manager)
        
        managers = DebugGlobalAccess.get_managers()
        assert len(managers) == 5
        assert managers[0] == "string_manager"
        assert managers[1] == 42
        assert managers[2] == [1, 2, 3]
        assert managers[3] == {"type": "dict_manager"}
        assert managers[4] is mock_manager

    def test_get_managers_returns_reference(self):
        """Test that get_managers returns the same list reference."""
        mock_manager = Mock()
        DebugGlobalAccess.add_manager(mock_manager)
        
        managers1 = DebugGlobalAccess.get_managers()
        managers2 = DebugGlobalAccess.get_managers()
        
        # They should be the same reference
        assert managers1 is managers2
        assert managers1 is DebugGlobalAccess._managers

    def test_managers_state_persistence(self):
        """Test that managers state persists across multiple get_managers calls."""
        mock_manager1 = Mock()
        mock_manager2 = Mock()
        
        DebugGlobalAccess.add_manager(mock_manager1)
        first_get = DebugGlobalAccess.get_managers()
        assert len(first_get) == 1
        
        DebugGlobalAccess.add_manager(mock_manager2)
        second_get = DebugGlobalAccess.get_managers()
        assert len(second_get) == 2
        
        # First get should now also show 2 managers (same reference)
        assert len(first_get) == 2

    def test_class_variable_direct_access(self):
        """Test direct access to the class variable."""
        mock_manager = Mock()
        mock_manager.test_attr = "direct_access"
        
        DebugGlobalAccess.add_manager(mock_manager)
        
        # Direct access should work
        assert len(DebugGlobalAccess._managers) == 1
        assert DebugGlobalAccess._managers[0].test_attr == "direct_access"

    def test_multiple_instances_share_managers(self):
        """Test that multiple instances of the class share the same managers."""
        # Even though this is a class with only class methods,
        # test that instantiation doesn't affect the class variable
        instance1 = DebugGlobalAccess()
        instance2 = DebugGlobalAccess()
        
        mock_manager = Mock()
        mock_manager.shared = True
        
        # Add via class method
        DebugGlobalAccess.add_manager(mock_manager)
        
        # Access via instances
        assert len(instance1.get_managers()) == 1
        assert len(instance2.get_managers()) == 1
        assert instance1.get_managers() is instance2.get_managers()

    def test_managers_list_modification(self):
        """Test that external modification of returned list affects internal state."""
        mock_manager1 = Mock()
        mock_manager2 = Mock()
        
        DebugGlobalAccess.add_manager(mock_manager1)
        managers_ref = DebugGlobalAccess.get_managers()
        
        # Modify the returned list directly
        managers_ref.append(mock_manager2)
        
        # Internal state should be affected
        assert len(DebugGlobalAccess._managers) == 2
        assert DebugGlobalAccess._managers[1] is mock_manager2

    def test_empty_managers_after_clear(self):
        """Test behavior after clearing the managers list."""
        mock_manager1 = Mock()
        mock_manager2 = Mock()
        
        DebugGlobalAccess.add_manager(mock_manager1)
        DebugGlobalAccess.add_manager(mock_manager2)
        assert len(DebugGlobalAccess.get_managers()) == 2
        
        # Clear the list
        DebugGlobalAccess._managers.clear()
        
        assert len(DebugGlobalAccess.get_managers()) == 0
        assert DebugGlobalAccess.get_managers() == []

    def test_managers_with_complex_objects(self):
        """Test adding managers with complex attributes and methods."""
        class ComplexManager:
            def __init__(self, name, config):
                self.name = name
                self.config = config
                self.active = True
                
            def get_status(self):
                return f"Manager {self.name} is {'active' if self.active else 'inactive'}"
        
        manager1 = ComplexManager("ComplexManager1", {"setting1": "value1"})
        manager2 = ComplexManager("ComplexManager2", {"setting2": "value2"})
        
        DebugGlobalAccess.add_manager(manager1)
        DebugGlobalAccess.add_manager(manager2)
        
        managers = DebugGlobalAccess.get_managers()
        assert len(managers) == 2
        assert managers[0].name == "ComplexManager1"
        assert managers[1].name == "ComplexManager2"
        assert managers[0].get_status() == "Manager ComplexManager1 is active"
        assert managers[1].config == {"setting2": "value2"}

    def test_stress_add_many_managers(self):
        """Test adding a large number of managers."""
        num_managers = 1000
        managers_to_add = []
        
        for i in range(num_managers):
            manager = Mock()
            manager.id = i
            manager.name = f"Manager{i}"
            managers_to_add.append(manager)
            DebugGlobalAccess.add_manager(manager)
        
        retrieved_managers = DebugGlobalAccess.get_managers()
        assert len(retrieved_managers) == num_managers
        
        # Verify a few random ones
        assert retrieved_managers[0].id == 0
        assert retrieved_managers[500].id == 500
        assert retrieved_managers[999].id == 999