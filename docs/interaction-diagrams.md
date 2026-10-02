# Interaction Diagrams

Object-level collaborations inside browser-use. Every participant is a real class in the
repository, with the file and line where it is defined.

## 1. Inside `runTask(stepLimit)` — one agent step

Expands the `runTask(stepLimit)` system event from SSD 2 (Submit Web Form). Last week the whole
system was one box; this is what happens inside it when that event arrives.

Participants: `Agent` (`agent/service.py:2503`), `BrowserSession` (`browser/session.py:1595`),
`DOMWatchdog` (`browser/watchdogs/dom_watchdog.py:244`), `DomService` (`dom/service.py:703`),
`MessageManager` (`agent/message_manager/service.py:424`), `ChatGoogle` (`llm/google/chat.py`),
`Tools` (`tools/service.py:2178`), `DefaultActionWatchdog`
(`browser/watchdogs/default_action_watchdog.py:337`).

```mermaid
sequenceDiagram
    participant AG as :Agent
    participant BS as :BrowserSession
    participant DW as :DOMWatchdog
    participant DS as :DomService
    participant MM as :MessageManager
    participant LLM as :ChatGoogle
    participant TO as :Tools
    participant AW as :DefaultActionWatchdog

    loop until done, or stepLimit reached
        AG->>BS: get_browser_state_summary()
        BS->>DW: on_BrowserStateRequestEvent(event)
        DW->>DS: get_dom_tree()
        DS-->>DW: EnhancedDOMTreeNode tree
        DW-->>BS: BrowserStateSummary
        BS-->>AG: BrowserStateSummary
        AG->>MM: create_state_messages(state, history)
        MM-->>AG: list[BaseMessage]
        AG->>LLM: ainvoke(messages, AgentOutput)
        LLM-->>AG: AgentOutput(evaluation, next_goal, actions)
        AG->>TO: act(action, browser_session)
        TO->>AW: ClickElementEvent(node) via event bus
        AW-->>TO: click metadata
        TO-->>AG: ActionResult
    end
    AG-->>AG: AgentHistoryList.final_result()
```

## 2. Inside the `navigate(url)` action — the security check

A different operation: what happens when the agent asks to open a page, and how a site outside
`allowed_domains` is handled.

Participants: `Tools` (`tools/service.py:507`), `EventBus` (bubus), `BrowserSession`
(`browser/session.py:905`), `SecurityWatchdog` (`browser/watchdogs/security_watchdog.py:35`).

```mermaid
sequenceDiagram
    participant TO as :Tools
    participant EB as :EventBus
    participant BS as :BrowserSession
    participant SW as :SecurityWatchdog

    TO->>EB: dispatch(NavigateToUrlEvent(url))
    EB->>BS: on_NavigateToUrlEvent(event)
    BS-->>EB: page load started
    EB->>SW: on_NavigateToUrlEvent(event)
    SW->>SW: _is_url_allowed(url)
    alt url matches a SiteRule
        SW-->>EB: no objection
        EB-->>TO: event_result() returns
        TO-->>TO: ActionResult(extracted_content="navigated")
    else url is not allowed
        SW->>EB: dispatch(BrowserErrorEvent(NavigationBlocked))
        SW->>BS: Page.navigate(about:blank)
        SW-->>EB: raise ValueError("blocked by security policy")
        EB-->>TO: event_result() re-raises
        TO-->>TO: ActionResult(error="Navigation failed: ... blocked by security policy")
    end
```

Note on ordering: `BrowserSession.on_NavigateToUrlEvent` runs before
`SecurityWatchdog.on_NavigateToUrlEvent`, so the page starts loading before the check runs. I
confirmed this with `allowed_domains=['example.com']`: the tab was switched to `about:blank` after
the fact, and the blocked site still received the request.
