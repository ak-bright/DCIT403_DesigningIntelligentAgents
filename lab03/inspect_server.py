import asyncio, sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = Path(__file__).parent
params = StdioServerParameters(command=sys.executable, args=[str(HERE / "server.py")], cwd=str(HERE))

async def main():
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            for t in (await s.list_tools()).tools:
                print("TOOL:", t.name, "-", (t.description or "").split("\n")[0])
            for name, args in [("check_stock", {"item": "amoxicillin", "strength": "500mg"}),
                               ("search_items", {"query": "tablet"}),
                               ("list_expiring", {"days": 60})]:
                res = await s.call_tool(name, args)
                print(f"\n{name}({args}) ->")
                print("\n".join(c.text for c in res.content if hasattr(c, "text")) or "[]")

asyncio.run(main())