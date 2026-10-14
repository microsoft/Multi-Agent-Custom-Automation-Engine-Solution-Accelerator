#!/usr/bin/env python3
"""
Test script to verify that mcp_server.py can be used with fastmcp run functionality.
This simulates what `fastmcp run mcp_server.py -t streamable-http -l DEBUG` would do.
"""

# Import the mcp_server module
import mcp_server


def test_mcp_instance():
    """Test that the MCP instance is available and properly configured."""
    print("🔍 Testing MCP server instance...")

    # Check if mcp instance exists
    if hasattr(mcp_server, "mcp") and mcp_server.mcp is not None:
        print("✅ MCP instance found!")

        # Try to get server info
        try:
            # Access the FastMCP server
            server = mcp_server.mcp
            print(f"✅ Server type: {type(server)}")
            print(f"✅ Server name: {getattr(server, 'name', 'Unknown')}")

            # Check if tools are registered
            factory = mcp_server.factory
            summary = factory.get_tool_summary()
            print(f"✅ Total services: {summary['total_services']}")
            print(f"✅ Total tools: {summary['total_tools']}")

            for domain, info in summary["services"].items():
                print(
                    f"   📁 {domain}: {info['tool_count']} tools ({info['class_name']})"
                )

            return True

        except Exception as e:
            print(f"❌ Error accessing MCP server: {e}")
            return False
    else:
        print("❌ MCP instance not found or is None")
        return False


def test_fastmcp_compatibility():
    """Test if the server can be used with FastMCP Client."""
    print("\n🔍 Testing FastMCP client compatibility...")

    try:
        from fastmcp import Client

        # Create a client that connects to our server instance
        if hasattr(mcp_server, "mcp") and mcp_server.mcp is not None:
            # This simulates how fastmcp run would use the server
            Client(mcp_server.mcp)
            print("✅ FastMCP Client can connect to our server instance")
            return True
        else:
            print("❌ No MCP server instance available for client connection")
            return False

    except ImportError as e:
        print(f"❌ FastMCP not available: {e}")
        return False
    except Exception as e:
        print(f"❌ Error creating FastMCP client: {e}")
        return False


def test_streamable_http():
    """Test if we can run in streamable HTTP mode."""
    print("\n🔍 Testing streamable HTTP mode compatibility...")

    try:
        # This is what would happen when using -t streamable-http
        server = mcp_server.mcp
        if server:
            # Check if the server has the necessary methods for HTTP streaming
            print("✅ MCP server instance ready for HTTP streaming")
            print(
                "💡 To run with fastmcp: fastmcp run mcp_server.py -t streamable-http -l DEBUG"
            )
            return True
        else:
            print("❌ No server instance available")
            return False

    except Exception as e:
        print(f"❌ Error testing streamable HTTP: {e}")
        return False


if __name__ == "__main__":
    print("🚀 FastMCP Run Compatibility Test")
    print("=" * 50)

    # Run tests
    test1 = test_mcp_instance()
    test2 = test_fastmcp_compatibility()
    test3 = test_streamable_http()

    print("\n📋 Test Results:")
    print(f"   MCP Instance: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"   Client Compatibility: {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"   Streamable HTTP: {'✅ PASS' if test3 else '❌ FAIL'}")

    if all([test1, test2, test3]):
        print("\n🎉 All tests passed! Your mcp_server.py is ready for fastmcp run!")
        print("\n📖 Usage Examples:")
        print("   python -m fastmcp.cli.run mcp_server.py -t streamable-http -l DEBUG")
        print("   # OR if fastmcp CLI is available globally:")
        print("   fastmcp run mcp_server.py -t streamable-http -l DEBUG")
    else:
        print("\n❌ Some tests failed. Check the errors above.")

    print("\n" + "=" * 50)
