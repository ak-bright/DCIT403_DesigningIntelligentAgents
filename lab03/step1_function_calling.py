import csv, json, os
from pathlib import Path
from dotenv import load_dotenv
from litellm import completion

load_dotenv()
MODEL = os.getenv("LLM_MODEL", "groq/openai/gpt-oss-20b")
DATA = Path(__file__).parent / "data" / "pharmacy_stock.csv"


def check_stock(item: str, strength: str = ""):
    with open(DATA, newline="") as f:
        rows = [r for r in csv.DictReader(f) if item.lower() in r["item"].lower()]
    if strength:
        rows = [r for r in rows if strength.lower() in r["strength"].lower()]
    return rows


TOOLS = {"check_stock": check_stock}

tool_schemas = [{
    "type": "function",
    "function": {
        "name": "check_stock",
        "description": "Check pharmacy stock for one medicine. Returns rows with quantity, price (GHS) and expiry.",
        "parameters": {
            "type": "object",
            "properties": {
                "item": {"type": "string", "description": "Medicine name, e.g. 'amoxicillin'"},
                "strength": {"type": "string", "description": "Optional strength, e.g. '500mg'"},
            },
            "required": ["item"],
        },
    },
}]

messages = [
    {"role": "system", "content": "You are a pharmacy stock assistant. Use tools for stock facts."},
    {"role": "user", "content": "Do we have amoxicillin 500mg?"},
]

resp = completion(model=MODEL, messages=messages, tools=tool_schemas, temperature=0)
msg = resp.choices[0].message
print("MODEL DECISION:", msg.tool_calls)          # message 2: the action

messages.append(msg.model_dump(exclude_none=True))
for tc in msg.tool_calls or []:
    args = json.loads(tc.function.arguments)
    result = TOOLS[tc.function.name](**args)
    print("PERCEPT:", result)                      # message 3: the percept
    messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)})

resp = completion(model=MODEL, messages=messages, tools=tool_schemas, temperature=0)
print("ANSWER:", resp.choices[0].message.content)  # message 4