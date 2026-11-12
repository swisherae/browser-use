# Security Bug History

## Bug 1: Allowed-domain bypass via HTTP auth credentials

**CVE-2025-47241 / GHSA-x39x-9qw5-ghrf**, critical, CVSS 9.3, affecting `browser-use <= 0.1.44`,
patched in 0.1.45.
Advisory: https://github.com/browser-use/browser-use/security/advisories/GHSA-x39x-9qw5-ghrf
Fix: PR #1561, merged 2025-05-03, https://github.com/browser-use/browser-use/pull/1561

Reported by researchers at ARIMLABS.AI. A URL such as `https://allowed.com@evil.com` passed the
allow-list, because `_is_url_allowed` in `browser_use/browser/context.py` read
`urlparse(url).netloc`, which is `allowed.com@evil.com`, and then stripped a port by splitting on
`:`. The decoy before the `@` is what the check saw; the browser connects to what comes after it.

**Architectural root cause.** The check compared a token the code *believed* was the host against
the policy, while the component that performs the request, the browser, resolves a different host.
The policy and its enforcer disagreed about what the destination was.

**Structural or narrow?** Narrow in size, five lines added and six removed, plus a 21-line test, but
it did replace hand-rolled parsing with `urlparse(...).hostname`, which strips credentials and port
properly. A better primitive inside the same architecture, not a change to the architecture.

**OWASP:** A10:2021 Server-Side Request Forgery. A01:2021 Broken Access Control also fits.

## Bug 2: `block_ip_addresses` bypass via non-standard IPv4 forms

Fixed by **PR #4866**, merged 2026-05-19, https://github.com/browser-use/browser-use/pull/4866
The PR says it closes two high-severity reports, GHSA-xrfv-gg9f-wwjp and GHSA-g27c-8gp4-28cv,
described there as duplicates. **Both IDs return 404 from the GitHub advisories API, so neither
advisory is publicly readable**; I am citing the merged PR, which I did read, not the advisories.

`SecurityWatchdog._is_ip_address` recognised only what `ipaddress.ip_address()` accepts, the
canonical dotted quad and full IPv6. Chromium and the kernel resolver also accept decimal, hex,
octal and short forms, so `http://2130706433/` reached `127.0.0.1` while the check saw an ordinary
hostname and allowed it.

**Architectural root cause.** The same shape as Bug 1: the check canonicalises the host with one set
of rules, and the component that acts on it uses another.

**Structural or narrow?** Wider than Bug 1, 28 lines added against 10 removed and 194 lines of new
tests, and the new code deliberately mirrors WHATWG canonicalisation, including NFKC normalisation,
percent-decoding, ideographic separators and `inet_aton`. Still a hand-written canonicaliser inside
the watchdog, so it closed the known encodings rather than the class.

**OWASP:** A10:2021 Server-Side Request Forgery.

## The class reappeared, twice

These are two instances of one recurring defect: **trust decisions are made by matching text against
a policy, using rules that differ from the component that ultimately resolves and fetches the
address.** The evidence that the narrow fixes did not close the class is that it came back:

- 2025-05: credentials in the authority (CVE-2025-47241), fixed by reading `hostname`.
- 2026-05: alternative IPv4 encodings (PR #4866), fixed by mirroring WHATWG canonicalisation.
- 2026-10: **still open.** PR #6070, filed 2026-10-15, reports that the glob `*google.com` matches
  `evilgoogle.com`, because the pattern is treated as a suffix match rather than a domain boundary.
  Reported as high, CVSS 8.3, CWE-155. https://github.com/browser-use/browser-use/pull/6070

A structural fix would stop re-implementing the browser's host parsing and decide at the point the
request is made, using the host the browser itself resolved, which is the CDP-layer interception
described in threat model entry T2.
