"""Tool dispatcher — maps JSON actions to Python functions."""
import asyncio
import inspect
import json
import logging
from typing import Any, Callable, Dict, List

logger = logging.getLogger("aria.dispatcher")


class ToolDispatcher:
    def __init__(self):
        self._registry: Dict[str, Callable[[Dict[str, Any]], Any]] = {}

    def register_tools(self, tools: List[Any]):
        for tool in tools:
            try:
                func = getattr(tool, "func", tool)
                action_name = getattr(tool, "name", getattr(func, "__name__", None))
                if not action_name:
                    continue

                signature = inspect.signature(func)
                allowed = {
                    p
                    for p, param in signature.parameters.items()
                    if param.kind
                    in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
                }
                accepts_var = any(
                    p.kind == inspect.Parameter.VAR_KEYWORD
                    for p in signature.parameters.values()
                )

                if inspect.iscoroutinefunction(func):

                    async def _async_wrapper(
                        data, _f=func, _allowed=allowed, _accepts_var=accepts_var, _name=action_name
                    ):
                        payload = data if isinstance(data, dict) else {}
                        filtered = payload if _accepts_var else {k: v for k, v in payload.items() if k in _allowed}
                        return await _f(**filtered)

                    self._registry[action_name] = _async_wrapper
                else:

                    async def _wrapper(
                        data, _f=func, _allowed=allowed, _accepts_var=accepts_var, _name=action_name
                    ):
                        payload = data if isinstance(data, dict) else {}
                        filtered = payload if _accepts_var else {k: v for k, v in payload.items() if k in _allowed}
                        return await asyncio.to_thread(_f, **filtered)

                    self._registry[action_name] = _wrapper

                logger.info("Registered action '%s'", action_name)
            except Exception as e:
                logger.warning("Failed to register tool %s: %s", tool, e)

    def get_registered_actions(self) -> List[str]:
        return sorted(self._registry.keys())

    async def dispatch(self, action: str, data: Dict[str, Any]) -> str:
        if action not in self._registry:
            logger.warning("Unknown action '%s'. Registered: %s", action, self.get_registered_actions())
            return "No pude ejecutar esa accion. Intenta reformular tu mensaje."
        try:
            result = await self._registry[action](data)
            if isinstance(result, (dict, list)):
                return json.dumps(result, ensure_ascii=False)
            return str(result)
        except Exception as e:
            logger.error("Tool '%s' failed: %s", action, e)
            return f"Error ejecutando {action}: {e}"
