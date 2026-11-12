"""
A host glob in allowed_domains must match at a domain boundary, not as bare text.

Reproduces the defect reported upstream in PR #6070 (open, filed 2026-10-15): the pattern
`*google.com` is passed to fnmatch against the hostname, so it also matches `evilgoogle.com`,
and an attacker only has to register a domain ending in the allowed string.

The legitimate matches are asserted alongside the bypasses so a fix cannot pass by simply
rejecting the pattern outright.
"""

import pytest
from bubus import EventBus

from browser_use.browser import BrowserProfile, BrowserSession
from browser_use.browser.watchdogs.security_watchdog import SecurityWatchdog


def watchdog_allowing(*patterns: str) -> SecurityWatchdog:
	session = BrowserSession(browser_profile=BrowserProfile(allowed_domains=list(patterns), headless=True, user_data_dir=None))
	return SecurityWatchdog(event_bus=session.event_bus, browser_session=session)


class TestHostGlobRespectsDomainBoundary:
	"""`*google.com` should mean google.com and its subdomains, not any host ending in those letters."""

	@pytest.mark.parametrize(
		'url',
		[
			'https://google.com/',
			'https://www.google.com/',
			'https://mail.google.com/inbox',
		],
	)
	def test_isUrlAllowed_whenHostIsTheDomainOrASubdomain_returnsTrue(self, url):
		assert watchdog_allowing('*google.com')._is_url_allowed(url) is True

	@pytest.mark.parametrize(
		'url',
		[
			'https://evilgoogle.com/',
			'https://nonegoogle.com/x?a=1',
			'https://notgoogle.com/',
		],
	)
	def test_isUrlAllowed_whenHostMerelyEndsWithTheAllowedText_returnsFalse(self, url):
		"""The bypass: these are separate registrable domains and must not be allowed."""
		assert watchdog_allowing('*google.com')._is_url_allowed(url) is False

	def test_isUrlAllowed_whenHostHasAllowedTextAsASubdomain_returnsFalse(self):
		"""Already correct today, asserted so a fix does not regress it."""
		assert watchdog_allowing('*google.com')._is_url_allowed('https://google.com.attacker.net/') is False

	def test_isUrlAllowed_whenDottedGlobIsUsed_stillMatchesSubdomainsOnly(self):
		"""The documented `*.` form must keep working unchanged."""
		watchdog = watchdog_allowing('*.google.com')
		assert watchdog._is_url_allowed('https://mail.google.com/') is True
		assert watchdog._is_url_allowed('https://google.com/') is True
		assert watchdog._is_url_allowed('https://evilgoogle.com/') is False
