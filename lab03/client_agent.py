"""Lab 3 client: an agent that discovers its tools from an MCP server."""
import asyncio, json, os, sys, time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from litellm import acompletion
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()
HERE = Path(__file__).parent
MODEL = os.getenv("LLM_MODEL", "groq/openai/gpt-oss-20b")
LOG = HERE / "evidence" / "tool_calls.jsonl"
LOG.parent.mkdir(exist_ok=True)

SYSTEM = (
    "You are a community pharmacy assistant. Use the tools for every stock, price or expiry fact; "
    "never guess. Prices are in GHS. To record a sale, call record_sale only when the user clearly "
    "asks for a sale. If a tool returns REFUSED, tell the user why in plain words."
)

DEFAULT_QUESTIONS = [
    "Do we have amoxicillin 500mg?",
    "Which items expire within 60 days?",
    "What do 2 packs of paracetamol cost?",
    "Do you stock anything in syrup form?",
    "Sell 2 packs of amoxicillin 500mg.",
    "Sell 500 packs of ibuprofen 200mg.",       # deliberate oversale
]

params = StdioServerParameters(
    command=sys.executable, args=[str(HERE / "server.py")], cwd=str(HERE)
)


def log_call(question, name, args, result_text, ms):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "tool": name,
        "arguments": args,
        "result_summary": result_text[:150],
        "duration_ms": round(ms, 1),
    }
    with open(LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


async def call_tool(session, question, name, args):
    start = time.perf_counter()
    result = await session.call_tool(name, args)
    ms = (time.perf_counter() - start) * 1000
    text = "\n".join(c.text for c in result.content if hasattr(c, "text")) or "[]"
    log_call(question, name, args, text, ms)
    return text


async def ask(session, schemas, question, max_steps=6):
    print(f"\n=== {question}")
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": question}]
    for _ in range(max_steps):
        resp = await acompletion(model=MODEL, messages=messages,
                                 tools=schemas, temperature=0)
        msg = resp.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))
        if not msg.tool_calls:
            print("ANSWER:", msg.content)
            return msg.content
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
                print(f"ACTION: {tc.function.name}({args})")
                text = await call_tool(session, question, tc.function.name, args)
            except Exception as e:                      # bad args, unknown tool, etc.
                text = f"Error: {e}"
            print("PERCEPT:", text[:200])
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": text})
    print("ANSWER: (stopped: max_steps reached)")


async def main():
    questions = sys.argv[1:] or DEFAULT_QUESTIONS
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            print("Discovered tools:", [t.name for t in tools])
            schemas = [{"type": "function", "function": {
                "name": t.name, "description": t.description,
                "parameters": t.inputSchema}} for t in tools]
            for q in questions:
                await ask(session, schemas, q)


asyncio.run(main())