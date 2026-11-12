"""
Characterization tests for BaseWatchdog.attach_handler_to_session.

Every watchdog in browser_use/browser/watchdogs/ is wired to the event bus through this one
static method, so the naming contract it enforces and the circuit breaker it wraps around
each handler apply to the entire event-driven layer. It had no tests before this file.

No mocks: these use a real BrowserSession that is never started, which is exactly the state
in which the circuit breaker is supposed to act.
"""

import pytest
from bubus import BaseEvent

from browser_use.browser import BrowserProfile, BrowserSession
from browser_use.browser.events import BrowserErrorEvent
from browser_use.browser.watchdog_base import BaseWatchdog


class PlainTestEvent(BaseEvent):
	"""A non-lifecycle event, so the circuit breaker applies to it."""

	note: str = 'hello'


@pytest.fixture
async def session():
	"""An unstarted session: it has an event bus, and is_cdp_connected is False."""
	browser_session = BrowserSession(browser_profile=BrowserProfile(headless=True, user_data_dir=None))
	yield browser_session
	await browser_session.kill()


class TestHandlerNamingContract:
	"""The method asserts a naming convention instead of taking an event name argument."""

	def test_attachHandler_whenNameMatchesConvention_registersWithoutError(self, session):
		async def on_PlainTestEvent(event):
			return None

		BaseWatchdog.attach_handler_to_session(session, PlainTestEvent, on_PlainTestEvent)

	def test_attachHandler_whenNameDoesNotStartWithOn_raisesAssertionError(self, session):
		async def handle_PlainTestEvent(event):
			return None

		with pytest.raises(AssertionError, match='must start with "on_"'):
			BaseWatchdog.attach_handler_to_session(session, PlainTestEvent, handle_PlainTestEvent)

	def test_attachHandler_whenNameDoesNotEndWithEventClass_raisesAssertionError(self, session):
		async def on_SomethingElse(event):
			return None

		with pytest.raises(AssertionError, match='must end with event type PlainTestEvent'):
			BaseWatchdog.attach_handler_to_session(session, PlainTestEvent, on_SomethingElse)

	def test_attachHandler_whenHandlerHasNoName_raisesAssertionError(self, session):
		"""A callable object has no __name__, so the first assertion rejects it."""

		class CallableWithoutName:
			async def __call__(self, event):
				return None

		with pytest.raises(AssertionError, match='__name__'):
			BaseWatchdog.attach_handler_to_session(session, PlainTestEvent, CallableWithoutName())


class TestCircuitBreaker:
	"""Handlers are wrapped so they do not run while CDP is disconnected."""

	async def test_dispatch_whenCdpDisconnectedAndEventIsNotLifecycle_skipsHandler(self, session):
		"""The normal protective case: the handler never runs on a dead connection."""
		assert session.is_cdp_connected is False
		calls: list[str] = []

		async def on_PlainTestEvent(event):
			calls.append(event.note)
			return None

		BaseWatchdog.attach_handler_to_session(session, PlainTestEvent, on_PlainTestEvent)
		await session.event_bus.dispatch(PlainTestEvent(note='skipped'))

		assert calls == [], 'handler ran even though CDP was not connected'

	async def test_dispatch_whenCdpDisconnectedAndEventIsLifecycle_runsHandler(self, session):
		"""Boundary: lifecycle events are exempt, so the same wrapper lets them through."""
		assert session.is_cdp_connected is False
		calls: list[str] = []

		async def on_BrowserErrorEvent(event):
			calls.append(event.error_type)
			return None

		BaseWatchdog.attach_handler_to_session(session, BrowserErrorEvent, on_BrowserErrorEvent)
		await session.event_bus.dispatch(BrowserErrorEvent(error_type='TestError', message='x'))

		assert calls == ['TestError'], 'lifecycle event was skipped by the circuit breaker'

	async def test_dispatch_whenHandlerIsSkipped_askingForResultsRaisesValueError(self, session):
		"""Failure path worth knowing about.

		The skip is silent for the dispatch itself, but a caller that then asks for results gets
		a ValueError rather than an empty list, because no handler returned a non-None value.
		Callers of event_result() on a disconnected session therefore fail at the result, not at
		the dispatch.
		"""

		async def on_PlainTestEvent(event):
			return 'handler ran'

		BaseWatchdog.attach_handler_to_session(session, PlainTestEvent, on_PlainTestEvent)
		event = session.event_bus.dispatch(PlainTestEvent())
		await event

		with pytest.raises(ValueError, match='Expected at least one handler'):
			await event.event_results_list()
