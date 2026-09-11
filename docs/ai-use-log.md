# AI Use Log: Assignment 2

**Tool:** Claude Code (Anthropic's coding assistant) in VS Code, running the Claude Sonnet 5 and Claude Opus 5 models.
**When:** September 2026, over several sessions ending September 11.

## What the AI did, by part

| Part | What I asked for | What the AI did |
|---|---|---|
| 1. Outcome analysis | Map the 17 course outcomes to real evidence in the codebase | Searched the repository and cited files, classes and functions for each outcome. Ranked the strongest and weakest fits. Explained the event bus and `SecurityWatchdog` in plain language, and reviewed my own summary of the event flow. |
| Getting it to run | Help running the example agent | Diagnosed each failure (`403`, missing key, `402`, `503`/`429`, `404`), edited `examples/getting_started/01_basic_search.py`, tested which Gemini models respond, and ran the agent to confirm the fixes. |
| 2. Analysis and design | Two paragraphs using my project | Drafted them from the errors in my own runs, and checked every line of code they cite. |
| 3. Domain model | Which concepts to use | Proposed 8 conceptual classes with associations and multiplicities, and wrote the Mermaid source in `docs/domain-model.md`. |
| 4. Representational gap | Trace three concepts into the code | Found where Step, AI Model and Task live in the code and wrote the comparison table. |
| 5. Iteration | Which UP phase, and what one iteration looks like | Pulled evidence from the git history, release tags and GitHub's API (issue #5598, PR #5599) and drafted two paragraphs. |
| 6. Presentation | Prepare the live demo | Tested a demo task, recorded a backup GIF (`docs/demo-backup.gif`, kept local), and listed the code to have open. |
| Build notes | Record all the changes | Wrote `docs/build-notes.md`. |

## What I did myself

- Created the API keys (Google AI Studio, DeepSeek, browser-use Cloud) and put them in `.env`. The keys were never shared or committed, and the AI ran test tasks with my Google key.
- Ran the example scripts myself and brought the error output back to the AI.
- Chose my two best fits (outcomes 7 and 17) and two worst fits (14 and 15), and wrote the Project Outcome Analysis wiki page in my own words.
- Wrote my own explanation of how events move between the layers, which the AI then corrected.
- Created the wiki home page, the `docs/` folder and the `Build_notes` branch.

## Mistakes the AI made, and how they were caught

- It named a class `DOMElementNode` in the outcome analysis. That class doesn't exist; the real one is `EnhancedDOMTreeNode` (`browser_use/dom/views.py:375`). The AI caught this while checking the code for Part 4.
- It said CI blocks a merge when tests fail. It later checked and could only confirm that the test and lint workflows run on every pull request (`.github/workflows/test.yaml`, `lint.yml`). Whether a failure blocks merging is a GitHub setting that isn't visible in the repository.
- It switched the example to `ChatDeepSeek` without checking whether that class reads its key from the environment. It doesn't, which caused the misleading `OPENAI_API_KEY` error.
- It first picked the `gemini-flash-latest` model, which failed with `503` and `429` on the free tier. It chose new models after testing each one directly.

## Files the AI created or changed

- Changed: `examples/getting_started/01_basic_search.py` (the full diff is in `docs/build-notes.md`)
- Created: `docs/domain-model.md`, `docs/build-notes.md`, `docs/ai-use-log.md`
- Created, kept local only (gitignored): `docs/demo-backup.gif`
