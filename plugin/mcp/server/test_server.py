import pytest
from server import create_server

def test_server_creates():
    server = create_server()
    assert server is not None

@pytest.mark.anyio
async def test_server_has_health_tool():
    server = create_server()
    tools = await server.list_tools()
    tool_names = [t.name for t in tools]
    assert "health" in tool_names
