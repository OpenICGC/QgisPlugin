"""Test MCP server when run as module"""

# Simulate running as module
if __name__ == "__main__":
    # Import the way the server does when run as module
    from geofinder.mcp.server import mcp

    print("=" * 60)
    print("Testing MCP Server (as module)")
    print("=" * 60)

    print(f"\n1. MCP instance: {type(mcp).__name__}")

    # Check tool manager
    if hasattr(mcp, '_tool_manager'):
        tm = mcp._tool_manager
        if hasattr(tm, '_tools'):
            tools = tm._tools
            print(f"2. Number of tools registered: {len(tools)}")
            if tools:
                print("3. ✅ Tool names:")
                for i, name in enumerate(tools.keys(), 1):
                    print(f"   {i}. {name}")
            else:
                print("3. ⚠️ NO TOOLS REGISTERED")
                print("\n4. Forcing tools import...")
                from geofinder.mcp import tools as tools_module
                print(f"   Tools module imported: {tools_module is not None}")

                # Check again
                tools_after = tm._tools
                print(f"5. Tools after import: {len(tools_after)}")
                if tools_after:
                    print("6. ✅ NOW REGISTERED:")
                    for i, name in enumerate(tools_after.keys(), 1):
                        print(f"   {i}. {name}")

    print("\n" + "=" * 60)
