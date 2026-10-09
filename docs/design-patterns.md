# Design Pattern Diagrams

Design class diagrams for the three GoF patterns found in browser-use. Rendered copies:
`pattern-1-strategy.png`, `pattern-2-observer.png`, `pattern-3-adapter.png`.

## Strategy: swappable AI models

```mermaid
classDiagram
    class BaseChatModel {
        <<Protocol>>
        +model: str
        +provider: str
        +name: str
        +supports_vision: bool
        +ainvoke(messages: list~BaseMessage~, output_format: type~T~) ChatInvokeCompletion~T~
    }
    class ChatGoogle {
        +model: str
        +api_key: Optional~str~
        +provider: str
        +ainvoke(messages: list~BaseMessage~, output_format: type~T~) ChatInvokeCompletion~T~
    }
    class ChatDeepSeek {
        +model: str
        +api_key: Optional~str~
        +provider: str
        +supports_vision: bool
        +ainvoke(messages: list~BaseMessage~, output_format: type~T~) ChatInvokeCompletion~T~
    }
    class Agent {
        -llm: BaseChatModel
        -_fallback_llm: Optional~BaseChatModel~
        +get_model_output(input_messages: list~BaseMessage~) AgentOutput
        -_try_switch_to_fallback_llm(error: ModelProviderError) bool
    }
    BaseChatModel <|.. ChatGoogle
    BaseChatModel <|.. ChatDeepSeek
    Agent o-- BaseChatModel : llm, fallback_llm
```

## Observer: the event bus and the watchdogs

```mermaid
classDiagram
    class EventBus {
        +dispatch(event: BaseEvent) BaseEvent
        +on(event_type: str, handler: Callable) None
    }
    class BaseWatchdog {
        <<abstract>>
        +LISTENS_TO: list~BaseEvent~
        +EMITS: list~BaseEvent~
        +event_bus: EventBus
        +browser_session: BrowserSession
        +attach_handler_to_session(session, event_class, handler) None
    }
    class SecurityWatchdog {
        +on_NavigateToUrlEvent(event: NavigateToUrlEvent) None
        +on_NavigationCompleteEvent(event: NavigationCompleteEvent) None
        -_is_url_allowed(url: str) bool
    }
    class DefaultActionWatchdog {
        +on_ClickElementEvent(event: ClickElementEvent) dict
        +on_TypeTextEvent(event: TypeTextEvent) dict
    }
    class Tools {
        +act(action: ActionModel, browser_session: BrowserSession) ActionResult
    }
    BaseWatchdog <|-- SecurityWatchdog
    BaseWatchdog <|-- DefaultActionWatchdog
    BaseWatchdog --> EventBus : subscribes to
    Tools --> EventBus : dispatch(ClickElementEvent)
    EventBus --> DefaultActionWatchdog : on_ClickElementEvent(...)
```

## Adapter: per-provider message serializers

```mermaid
classDiagram
    class BaseMessage {
        +role: str
        +content: str
    }
    class DeepSeekMessageSerializer {
        +serialize(message: BaseMessage) MessageDict
        +serialize_messages(messages: list~BaseMessage~) list~MessageDict~
    }
    class GoogleMessageSerializer {
        +serialize_messages(messages: list~BaseMessage~) tuple
    }
    class ChatDeepSeek {
        +ainvoke(messages: list~BaseMessage~, output_format: type~T~) ChatInvokeCompletion~T~
    }
    class AsyncOpenAI {
        <<vendor SDK>>
        +create(model: str, messages: list~MessageDict~) Response
    }
    ChatDeepSeek --> DeepSeekMessageSerializer : serialize_messages(messages)
    DeepSeekMessageSerializer --> BaseMessage : adapts
    ChatDeepSeek --> AsyncOpenAI : sends adapted messages
```
