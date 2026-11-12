# Security Analysis — Presentation Walkthrough

Two minutes, no slides, shown from the wiki. Four things are required: the misuse case diagram with
one case walked through, the first mitigation you would make and where it goes, the dependency risk
and whether it is reachable, and the control you implemented with the crossing it defends.

## Before you start

- [ ] Tab 1: wiki page `Security Analysis`, scrolled to the misuse case diagram.
- [ ] Tab 2: `https://github.com/swisherae/browser-use/commit/162dd844` — the diff, not the repo home.
- [ ] Both tabs open **before** class. Navigating eats the clock.
- [ ] Optional tab 3: `docs/sbom.json` on GitHub, only if someone asks to see the SBOM.

## The script

### 0:00–0:35 — Diagram on screen, walk one misuse case

> browser-use drives a real Chrome browser from an AI model. Red boxes are attacker goals, green are
> the controls that mitigate them. Take *Exfiltrate Data in a Blocked URL*. The agent reads a page,
> the page tells it to visit an attacker's address with data in the query string, and the agent goes.
> There is an allow-list meant to stop that. I tested it with only example.com allowed, and the page
> still loaded: the request went out first, and the tab was switched to about:blank afterwards. So
> the control blocks what the agent *reads*, not what it *sends*.

### 0:35–1:05 — The first mitigation, and where it goes

> The fix I would make first is ordering, in `browser_use/browser/session.py`. The session registers
> its own navigate handler at construction, line 718, and the watchdogs attach later, at line 798,
> so the navigator always runs before the security check. Either the SecurityWatchdog registers
> first, or the session consults the policy before issuing the CDP command. The check itself is
> already correct; only its position is wrong. It belongs in session.py because that is the one
> place every navigation passes through. Putting it in Tools would mean repeating it for navigate,
> search, go_back and switch.

### 1:05–1:30 — The dependency risk, and reachability

> I generated a CycloneDX SBOM: 37 declared dependencies become 237 installed packages, and 22 of
> those carry advisories. The one that matters is pypdf 6.15.0, GHSA-5jq2-8x83-x246, also
> CVE-2026-102994, high severity, fixed in 6.18.0. It breaks availability only; the CVSS vector has
> confidentiality and integrity at none. And it is reachable: the `read_file` action calls
> `FileSystem.read_file`, which calls `pypdf.PdfReader` at `file_system.py:704`. A malicious page
> serves a crafted PDF, the agent downloads it, reads it, and hangs.

### 1:30–2:00 — The control, switch to tab 2

> The control I implemented defends crossing 6, agent to model provider. Secrets passed as
> `sensitive_data` are masked in the message text, but screenshots were never redacted, so the model
> read a secret off an image and repeated it in its answer. I reproduced that. Twelve lines in
> `agent/service.py`: if `sensitive_data` is set, vision is off unless you explicitly opt in. It sits
> before the tool registry is built, so it also removes the screenshot action the model could
> otherwise call on demand. 107 security tests pass. What it does not do is redact anything. It
> removes a channel, and the opt-in flag brings the leak straight back.

## Numbers and names, so you quote them correctly

| Fact | Value |
|---|---|
| Advisory you cite | GHSA-5jq2-8x83-x246, alias CVE-2026-102994 |
| Affected range | all pypdf before 6.18.0; installed 6.15.0 |
| What it breaks | availability only (`VC:N/VI:N/VA:H`) |
| Reachable at | `browser_use/filesystem/file_system.py:704` |
| Direct dependencies | 37 (plus 15 across nine optional extras) |
| Packages in SBOM | 237 (uv.lock resolves 403) |
| Packages with advisories | 22 of 237 |
| Ordering defect | `session.py:718` registers before `session.py:798` attaches watchdogs |
| Your control commit | `162dd844`, 12 lines, `agent/service.py:170` and `310-320` |
| Tests run | 107 passed (security + screenshot exclusion), 10 vision tests passed |
| Published CVE in the project | CVE-2025-47241, CVSS 9.3, fixed in 0.1.45 |

## Questions you are likely to get

**Why not implement the ordering fix, if it is more important?**
Because it changes event ordering across the whole browser layer and risks breaking navigation,
while the screenshot control was a one-commit slice that changes nothing for runs without secrets.
The brief asked for the smallest meaningful change.

**Did you find a new vulnerability?**
No. I found a reachable instance of a known advisory, plus two behaviours I reproduced locally that
are design gaps rather than disclosed bugs.

**Why does the control belong in Agent and not in BrowserSession?**
`Agent` is the only component that knows both that secrets were supplied and whether screenshots are
being sent. `BrowserSession` takes the screenshot but has never heard of `sensitive_data`.

**Is the allow-list broken then?**
It works for what it checks. The defect is that the check runs after the request is issued, and that
the same class of bypass has recurred three times: credentials in the authority in 2025, alternative
IPv4 encodings in 2026, and glob suffix matching, which is still open as PR #6070.

**How do you know the screenshot leak is real?**
I ran the form task with a secret. With screenshots on, one of three saved conversation files
contained the real value and the final answer repeated it. With `use_vision=False`, none did.

## Do not say

- Do not call it a new CVE. It is a known advisory, reachable from this code.
- Do not say the SBOM shows 237 shipped dependencies. It is the development environment, including
  test tooling.
- Do not say the control "fixes" the leak. It closes one channel and can be opted out of.

## If you are running long

Cut the SBOM numbers in beat 3 down to "22 of 237 packages carry advisories, and one of them is
reachable from our own code." That buys about fifteen seconds and loses nothing important.
