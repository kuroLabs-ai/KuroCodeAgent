"""
core/io_bus.py — UI-agnostic I/O, events, prompts, and cancellation.

Presentation adapters (CLI, WebView) implement IOHost. The domain layer
emits structured events and requests input through this host instead of
touching stdout/stdin.
"""

from __future__ import annotations

import time
import uuid
from concurrent.futures import Future
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from enum import Enum
from threading import Event, Lock
from typing import Any, Callable, Dict, List, Optional


class EventLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class EventKind(str, Enum):
    LOG = "log"
    PROGRESS = "progress"
    STATUS = "status"
    TOOL = "tool"
    THOUGHT = "thought"
    RESPONSE = "response"
    COMMAND = "command"
    NOTIFICATION = "notification"
    PROMPT = "prompt"
    CANCELLED = "cancelled"
    TASK = "task"
    METRIC = "metric"


class PromptKind(str, Enum):
    CONFIRM = "confirm"
    TEXT = "text"
    PASSWORD = "password"
    SELECT = "select"
    MULTISELECT = "multiselect"
    FILE = "file"


@dataclass
class CoreEvent:
    kind: str
    level: str = EventLevel.INFO.value
    message: str = ""
    data: Any = None
    progress: Optional[float] = None
    step: Optional[int] = None
    total: Optional[int] = None
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        return payload


@dataclass
class InputRequest:
    kind: str
    title: str = ""
    message: str = ""
    options: Optional[List[str]] = None
    default: Any = None
    mask: bool = False
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class IOHost:
    """Protocol-style base for presentation adapters."""

    def emit(self, event: CoreEvent) -> None:
        raise NotImplementedError

    def request(self, req: InputRequest, timeout: Optional[float] = None) -> Any:
        raise NotImplementedError

    def is_cancelled(self) -> bool:
        return False

    def request_cancel(self) -> None:
        return None

    def reset_cancel(self) -> None:
        return None

    def log(self, message: str, level: str = "INFO", **kwargs: Any) -> None:
        self.emit(CoreEvent(kind=EventKind.LOG.value, level=level, message=message, data=kwargs or None))


class NullHost(IOHost):
    """Silent host for tests and non-interactive automation (denies prompts)."""

    def __init__(self, auto_confirm: bool = False):
        self.auto_confirm = auto_confirm
        self.events: List[CoreEvent] = []
        self._cancel = Event()

    def emit(self, event: CoreEvent) -> None:
        self.events.append(event)

    def request(self, req: InputRequest, timeout: Optional[float] = None) -> Any:
        if req.kind == PromptKind.CONFIRM.value:
            return "y" if self.auto_confirm else "n"
        if req.kind == PromptKind.SELECT.value and req.options:
            return req.default if req.default is not None else req.options[0]
        if req.kind == PromptKind.MULTISELECT.value:
            return req.default or []
        return req.default

    def is_cancelled(self) -> bool:
        return self._cancel.is_set()

    def request_cancel(self) -> None:
        self._cancel.set()

    def reset_cancel(self) -> None:
        self._cancel.clear()


class CallbackHost(IOHost):
    """Host used by adapters: emit via callback, prompt via blocking function."""

    def __init__(
        self,
        on_event: Optional[Callable[[CoreEvent], None]] = None,
        on_request: Optional[Callable[[InputRequest], Any]] = None,
    ):
        self.on_event = on_event
        self.on_request = on_request
        self._cancel = Event()

    def emit(self, event: CoreEvent) -> None:
        if self.on_event:
            self.on_event(event)

    def request(self, req: InputRequest, timeout: Optional[float] = None) -> Any:
        if not self.on_request:
            return None
        return self.on_request(req)

    def is_cancelled(self) -> bool:
        return self._cancel.is_set()

    def request_cancel(self) -> None:
        self._cancel.set()
        self.emit(CoreEvent(kind=EventKind.CANCELLED.value, level="WARN", message="Operation cancelled"))

    def reset_cancel(self) -> None:
        self._cancel.clear()


class QueueHost(IOHost):
    """
    Thread-safe host for WebView IPC.
    Events are queued for polling; prompts block on a Future until JS responds.
    """

    def __init__(self, max_events: int = 2000):
        self._events: List[Dict[str, Any]] = []
        self._lock = Lock()
        self._max = max_events
        self._cancel = Event()
        self._pending: Dict[str, Future] = {}
        self.active_prompt: Optional[Dict[str, Any]] = None

    def emit(self, event: CoreEvent) -> None:
        with self._lock:
            self._events.append(event.to_dict())
            if len(self._events) > self._max:
                self._events = self._events[-self._max :]

    def drain(self) -> List[Dict[str, Any]]:
        with self._lock:
            items = list(self._events)
            self._events.clear()
            return items

    def request(self, req: InputRequest, timeout: Optional[float] = 300.0) -> Any:
        fut: Future = Future()
        with self._lock:
            self._pending[req.id] = fut
            self.active_prompt = req.to_dict()
        self.emit(CoreEvent(kind=EventKind.PROMPT.value, message=req.message, data=req.to_dict()))
        try:
            return fut.result(timeout=timeout)
        except Exception:
            return None
        finally:
            with self._lock:
                self._pending.pop(req.id, None)
                if self.active_prompt and self.active_prompt.get("id") == req.id:
                    self.active_prompt = None

    def respond(self, request_id: str, value: Any) -> bool:
        with self._lock:
            fut = self._pending.get(request_id)
            if self.active_prompt and self.active_prompt.get("id") == request_id:
                self.active_prompt = None
        if fut and not fut.done():
            fut.set_result(value)
            return True
        return False

    def is_cancelled(self) -> bool:
        return self._cancel.is_set()

    def request_cancel(self) -> None:
        self._cancel.set()
        with self._lock:
            prompt = self.active_prompt
            pending = dict(self._pending)
        for fut in pending.values():
            if not fut.done():
                fut.set_result(None)
        self.emit(CoreEvent(kind=EventKind.CANCELLED.value, level="WARN", message="Operation cancelled"))

    def reset_cancel(self) -> None:
        self._cancel.clear()


_current_host: ContextVar[Optional[IOHost]] = ContextVar("kuro_io_host", default=None)


def get_host() -> IOHost:
    return _current_host.get() or NullHost()


def set_host(host: Optional[IOHost]):
    return _current_host.set(host)


def reset_host(token) -> None:
    _current_host.reset(token)


def emit(kind: str, message: str = "", **kwargs: Any) -> None:
    get_host().emit(CoreEvent(kind=kind, message=message, **kwargs))
