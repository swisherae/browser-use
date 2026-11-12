# Threat Model

The three most significant risks in browser-use's architecture. Two I reproduced locally; the third
is an open issue filed upstream. Supply chain risk is covered separately in Part 6.

## T1: Secrets reach the model provider and local disk through screenshots

| | |
|---|---|
| **Asset** | The values passed in `sensitive_data`: credentials, email addresses, personal data, plus the run artifacts that persist them |
| **STRIDE** | Information Disclosure |
| **OWASP** | A04:2021 Insecure Design. The redaction was designed for one channel, message text, while a second channel carrying the same data was left open. Secondarily A02:2021, sensitive data exposure |
| **Likelihood** | **High.** `use_vision` defaults to on, and any form that echoes what it was given, which is most of them, puts the value on screen |
| **Impact** | **High.** The secret leaves the machine to a third party and is written to disk in the conversation log and the final answer, where it stays after the run |
| **Mitigation** | In `browser_use/agent/service.py`, at the point where `use_vision` is resolved: refuse to attach screenshots while `sensitive_data` is configured, unless the developer opts in explicitly. The complete fix extends `MessageManager._filter_sensitive_data` (`message_manager/service.py:577`) to cover images and model output, not just input text |

**Why that component.** `Agent` is the only place that holds both facts at once: that secrets were
supplied, and whether screenshots are being sent. `BrowserSession` takes the screenshot but has
never heard of `sensitive_data`; `Tools` substitutes the secret but does not control vision. Putting
the check anywhere else means passing secret-awareness into a component that has no other reason to
know about it.

## T2: Requests leave before the allowed-domain check runs

| | |
|---|---|
| **Asset** | Data the agent holds, and reachability of hosts the operator intended to be off limits, including internal network addresses |
| **STRIDE** | Information Disclosure |
| **OWASP** | A10:2021 Server-Side Request Forgery. The agent issues requests to addresses chosen by content it read, which is what `allowed_domains` and `block_ip_addresses` exist to contain |
| **Likelihood** | **Medium to high.** It needs attacker-controlled text on a page the agent reads, which is the agent's normal working environment |
| **Impact** | **High.** Anything in the URL has already been sent when the check fires, and the operator believes the allow-list prevented it |
| **Mitigation** | In `browser_use/browser/session.py`: either register `SecurityWatchdog`'s handler ahead of the session's own (`_register_session_event_handlers`, line 718, runs at construction while `attach_all_watchdogs` runs at line 798), or consult the policy inside `BrowserSession.on_NavigateToUrlEvent` (line 907) before issuing the CDP command. The strongest version intercepts at the CDP layer so no request leaves undecided |

**Why that component.** `session.py` is the single point every navigation passes through. Putting
the check in `Tools.navigate` would work for one action and then have to be repeated in `search`,
`go_back` and `switch`, which is how a policy ends up enforced in four places and missing from the
fifth. The check itself is already correct and already owned by `SecurityWatchdog`; only its
position in the sequence is wrong.

## T3: A corrupt config file silently becomes an allow-all profile

| | |
|---|---|
| **Asset** | The browser security profile, specifically `allowed_domains`, and the user's saved configuration file |
| **STRIDE** | Elevation of Privilege, with Tampering as a side effect since the original file is overwritten |
| **OWASP** | A05:2021 Security Misconfiguration |
| **Likelihood** | **Medium.** It needs a malformed `config.json`, which a partial write, a disk error or a hand edit can produce |
| **Impact** | **High.** The agent silently gains unrestricted browsing, and the user's restrictions are destroyed rather than merely ignored, so the next run is unrestricted too |
| **Mitigation** | In `browser_use/config.py:349`: fail closed. On a parse failure, refuse to start, or fall back to a profile with `allowed_domains` empty, and never overwrite the original. Write the unreadable file aside as `config.json.corrupt` instead of replacing it |

**Why that component.** `config.py` owns reading the policy, so it is the only component that can
tell the difference between "the user asked for no restrictions" and "the restrictions could not be
read". By the time `mcp/server.py` receives a profile, both look identical, which is precisely how
the issue reporter found it (upstream issue #6218, open, filed 2026-10-26).
