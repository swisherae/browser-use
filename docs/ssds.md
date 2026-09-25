# System Sequence Diagrams

One SSD per fully-dressed use case. The system is a single black box; the only actor is the
Developer. Event names and parameters use the terms in `docs/domain-model.md`.

## SSD 1: Look Up Information Online

```mermaid
sequenceDiagram
    actor D as Developer
    participant S as :BrowserUseSystem
    D->>S: createTask(instructions, primaryModel, backupModel)
    S-->>D: task status
    D->>S: runTask(stepLimit)
    S-->>D: task status
    D->>S: getAnswer()
    S-->>D: answer text, succeeded
```

## SSD 2: Submit Web Form

```mermaid
sequenceDiagram
    actor D as Developer
    participant S as :BrowserUseSystem
    loop for each secret the form needs
        D->>S: supplySecret(name, value)
        S-->>D: placeholder
    end
    D->>S: createTask(instructions, primaryModel, backupModel)
    S-->>D: task status
    D->>S: runTask(stepLimit)
    S-->>D: task status
    D->>S: getAnswer()
    S-->>D: answer text, succeeded
```

## SSD 3: Collect Data From Website

```mermaid
sequenceDiagram
    actor D as Developer
    participant S as :BrowserUseSystem
    loop for each approved site
        D->>S: setSiteRule(pattern, kind)
    end
    D->>S: setAnswerFormat(answerFormat)
    D->>S: createTask(instructions, primaryModel, backupModel)
    S-->>D: task status
    D->>S: runTask(stepLimit)
    S-->>D: task status
    D->>S: getAnswer()
    S-->>D: answer text, succeeded
```
