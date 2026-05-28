import asyncio, sys, os
sys.path.append('C:/ARIA')
from core.config import Config
from core.memory import MemoryManager
from core.agent import AriaAgent

async def test():
    config = Config()
    memory = MemoryManager(config)
    agent = AriaAgent(config, memory)
    response = await agent.process_message(user_id='12345', message='Hola, ¿cómo estás?')
    print('Agent response:', response)

if __name__ == '__main__':
    asyncio.run(test())
