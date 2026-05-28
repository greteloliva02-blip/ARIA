import sys, os
# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Ensure stdout handles Unicode
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import asyncio
from core.dispatcher import ToolDispatcher
from langchain_core.tools import tool

@tool
def echo(message: str) -> str:
    """Return the received message unchanged."""
    return f"Echo: {message}"

async def main():
    dispatcher = ToolDispatcher()
    # Register the dummy echo tool
    dispatcher.register_tools([echo])
    intent = {"action": "echo", "data": {"message": "hola mundo"}}
    result = await dispatcher.dispatch(intent["action"], intent["data"]) 
    print("Dispatch result:", result)

if __name__ == "__main__":
    asyncio.run(main())
