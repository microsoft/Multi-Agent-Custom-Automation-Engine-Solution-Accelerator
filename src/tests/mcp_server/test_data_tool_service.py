"""Unit tests for data_tool_service module."""

import os
import tempfile
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock

# Add the MCP server to path
mcp_server_path = Path(__file__).parent.parent.parent / "mcp_server"
sys.path.insert(0, str(mcp_server_path))

from services.data_tool_service import DataToolService, ALLOWED_FILES


class TestDataToolServiceInit:
    """Test DataToolService initialization."""

    def test_init_sets_dataset_path(self):
        """Test that dataset_path is correctly set."""
        service = DataToolService("/some/path")
        assert service.dataset_path == "/some/path"

    def test_init_sets_allowed_files(self):
        """Test that allowed_files is a set of ALLOWED_FILES."""
        service = DataToolService("/some/path")
        assert service.allowed_files == set(ALLOWED_FILES)

    def test_tool_count_is_two(self):
        """Test that tool_count returns 2 (data_provider and show_tables)."""
        service = DataToolService("/some/path")
        assert service.tool_count == 2

    def test_no_duplicate_tool_count_property(self):
        """Test that tool_count property is not duplicated (only one definition)."""
        # This test validates the fix for the duplicate @property issue
        import inspect
        source = inspect.getsource(DataToolService)
        count = source.count("def tool_count")
        assert count == 1, f"Expected 1 tool_count definition, found {count}"


class TestDataToolServiceFindFile:
    """Test DataToolService._find_file method."""

    def test_find_existing_file(self):
        """Test finding a file that exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test CSV file
            test_file = os.path.join(tmpdir, "test.csv")
            with open(test_file, "w") as f:
                f.write("col1,col2\nval1,val2\n")

            service = DataToolService(tmpdir)
            result = service._find_file("test.csv")
            assert result == test_file

    def test_find_nonexistent_file(self):
        """Test finding a file that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = DataToolService(tmpdir)
            result = service._find_file("nonexistent.csv")
            assert result is None


class TestDataToolServiceDataProvider:
    """Test DataToolService data_provider tool."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tmpdir = tempfile.mkdtemp()
        # Create one of the allowed files
        self.test_file = os.path.join(self.tmpdir, "product_table.csv")
        with open(self.test_file, "w") as f:
            f.write("id,name,price\n1,Widget,9.99\n")
        self.service = DataToolService(self.tmpdir)
        self.mock_mcp = Mock()
        self.tools = {}

        def tool_decorator(tags=None):
            def decorator(func):
                self.tools[func.__name__] = func
                return func
            return decorator

        self.mock_mcp.tool = tool_decorator
        self.service.register_tools(self.mock_mcp)

    def teardown_method(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_data_provider_reads_allowed_file(self):
        """Test data_provider reads content of allowed files."""
        data_provider = self.tools["data_provider"]
        result = data_provider("product_table")
        assert "id,name,price" in result
        assert "Widget" in result

    def test_data_provider_rejects_disallowed_file(self):
        """Test data_provider rejects files not in the allowed list."""
        data_provider = self.tools["data_provider"]
        result = data_provider("secret_data")
        assert "not allowed" in result

    def test_data_provider_returns_string_on_io_error(self):
        """Test data_provider returns an error string (not None) on IOError."""
        data_provider = self.tools["data_provider"]
        # Remove the file to cause IOError after path is found
        os.remove(self.test_file)
        # Create a directory with same name to cause IOError on read
        os.mkdir(self.test_file)
        result = data_provider("product_table")
        # Should return a string error message, not None
        assert result is not None
        assert isinstance(result, str)


class TestDataToolServiceShowTables:
    """Test DataToolService show_tables tool."""

    def test_show_tables_returns_found_tables(self):
        """Test show_tables returns list of found allowed tables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some allowed files
            for name in ["product_table.csv", "purchase_history.csv"]:
                with open(os.path.join(tmpdir, name), "w") as f:
                    f.write("col1\nval1\n")

            service = DataToolService(tmpdir)
            mock_mcp = Mock()
            tools = {}

            def tool_decorator(tags=None):
                def decorator(func):
                    tools[func.__name__] = func
                    return func
                return decorator

            mock_mcp.tool = tool_decorator
            service.register_tools(mock_mcp)

            show_tables = tools["show_tables"]
            result = show_tables()
            assert "product_table" in result
            assert "purchase_history" in result

    def test_show_tables_empty_directory(self):
        """Test show_tables with no matching files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = DataToolService(tmpdir)
            mock_mcp = Mock()
            tools = {}

            def tool_decorator(tags=None):
                def decorator(func):
                    tools[func.__name__] = func
                    return func
                return decorator

            mock_mcp.tool = tool_decorator
            service.register_tools(mock_mcp)

            show_tables = tools["show_tables"]
            result = show_tables()
            assert result == []
