# Logical Architecture

Layers and packages of browser-use, with dependency direction. Every box is a real directory or
module in the repository. Arrows point from the package that imports to the package it imports.

```mermaid
flowchart TD
    subgraph entry["Entry points"]
        EX["examples/"]
        CLI["browser_use/cli.py<br/>browser_use/skill_cli/"]
        MCP["browser_use/mcp/<br/>server.py, client.py"]
    end

    subgraph decide["Decision layer"]
        AG["browser_use/agent/<br/>service.py (Agent), views.py"]
        MM["browser_use/agent/message_manager/<br/>service.py (MessageManager)"]
    end

    subgraph act["Action layer"]
        TO["browser_use/tools/<br/>service.py (Tools), registry/"]
    end

    subgraph browser["Browser layer"]
        BS["browser_use/browser/<br/>session.py (BrowserSession), events.py, profile.py"]
        WD["browser_use/browser/watchdogs/<br/>15 watchdog classes"]
        AC["browser_use/actor/<br/>page.py, mouse.py, element.py"]
    end

    subgraph page["Page layer"]
        DOM["browser_use/dom/<br/>service.py (DomService), views.py, serializer/"]
    end

    subgraph model["Model layer"]
        LLM["browser_use/llm/<br/>base.py (BaseChatModel)"]
        PROV["browser_use/llm/google, anthropic,<br/>openai, deepseek, ... (14 providers)"]
    end

    subgraph shared["Cross-cutting, used by every layer"]
        CFG["config.py, logging_config.py,<br/>observability.py, utils.py"]
        TOK["browser_use/tokens/"]
        FS["browser_use/filesystem/"]
        TEL["browser_use/telemetry/"]
    end

    subgraph outside["Outside the codebase"]
        BUS["bubus.EventBus"]
        CDP["cdp-use over a websocket<br/>to Chrome"]
        API["provider HTTP APIs"]
    end

    EX --> AG
    CLI --> AG
    MCP --> AG
    AG --> MM
    AG --> TO
    AG --> LLM
    TO --> BS
    TO --> DOM
    BS --> WD
    BS --> AC
    BS --> DOM
    WD --> DOM
    LLM --> PROV
    AG -. also imports directly .-> BS
    AG -. also imports directly .-> DOM
    AG -.-> shared
    BS -.-> shared

    WD -. publishes and handles events on .-> BUS
    BS -. drives .-> CDP
    PROV -. calls .-> API
```

## Dependency notes

- The downward arrows come from counting `from browser_use.<package>` imports: `agent` imports
  `browser` 8 times, `dom` 5, `llm` 15, `tools` 3; `tools` imports `browser` 7 times and `dom` 4;
  `browser` imports `dom` 9 times.
- `dom` and `actor` refer back to `BrowserSession` only inside `if TYPE_CHECKING:` blocks
  (`dom/service.py:29`, `actor/page.py`), so those are type hints, not runtime dependencies.
- The only `llm` to `agent` imports are inside `browser_use/llm/tests/`, so the model layer does
  not depend on the agent in shipped code.
- `browser/watchdog_base.py:12` imports `BrowserSession` at module level while
  `session.py:1695` imports every watchdog inside `attach_all_watchdogs()`. That pair is a real
  cycle, documented as this assignment's architectural concern.
