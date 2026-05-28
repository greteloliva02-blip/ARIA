# core/dispatcher.py
"""
Dispatcher that maps JSON "action" strings to concrete async tool functions.
All tool functions are regular async callables (or sync wrappers) that accept a dict of parameters
and return a string (or JSON‑serialisable) result.
"""

import json
import logging
import inspect
from typing import Callable, Dict, Any, List

logger = logging.getLogger("dispatcher")

class ToolDispatcher:
    """Register tool callables and dispatch based on action name."""

    def __init__(self):
        # Mapping action name -> async callable
        self._registry: Dict[str, Callable[[Dict[str, Any]], Any]] = {}

    def register_tools(self, tools: List[Any]):
        """Extract callable functions from LangChain tool objects.
        Each tool object has a ``name`` attribute and is itself callable (async).
        """
        for tool in tools:
            try:
                # Resolve the underlying function: LangChain tools may expose .func
                func = getattr(tool, "func", tool)
                action_name = getattr(tool, "name", getattr(func, "__name__", None))
                if not action_name:
                    continue

                names = [action_name]
                if hasattr(tool, "aliases"):
                    names.extend(tool.aliases)

                for name in names:
                    if inspect.iscoroutinefunction(func):
                        async def _async_wrapper(data, _f=func):
                            return await _f(**data)
                        self._registry[name] = _async_wrapper
                    else:
                        async def _wrapper(data, _f=func):
                            return _f(**data)
                        self._registry[name] = _wrapper
                    logger.info(f"Dispatcher registered tool '{name}'.")
            except Exception as e:
                logger.warning(f"Failed to register tool {tool}: {e}")

    def get_registered_actions(self) -> List[str]:
        return sorted(self._registry.keys())

    async def dispatch(self, action: str, data: Dict[str, Any]) -> str:
        """Call the appropriate tool and return its string result.
        If the action is unknown, returns an informative message.
        """
        if action not in self._registry:
            logger.warning(f"Action '{action}' not found in dispatcher registry.")
            return f"⚠️ Acción desconocida: {action}"
        try:
            result = await self._registry[action](data)
            if isinstance(result, (dict, list)):
                return json.dumps(result, ensure_ascii=False)
            return str(result)
        except Exception as e:
            logger.error(f"Error executing tool '{action}': {e}")
            return f"⚠️ Error ejecutando la acción {action}: {e}"
