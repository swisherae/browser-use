# Build Notes

## Environment

- Windows 11, PowerShell
- Python 3.12.0 in the repo's `.venv` (dependencies were already installed)
- browser-use 0.13.8, code at upstream commit `564007d3`
- Google Chrome, driven by the agent over CDP

## How to run it

1. Put a Google AI Studio key in `.env` at the repo root (free from https://aistudio.google.com/apikey). `.env` is gitignored, so the key is never committed.
   ```
   GOOGLE_API_KEY=your-key
   ```
2. Run the example with a task in quotes:
   ```powershell
   .venv\Scripts\python.exe examples\getting_started\01_basic_search.py "Go to wikipedia.org, search for 'Unified Process', and tell me the first sentence of the article"
   ```
   Or run it with no task and type one at the prompt. Pressing Enter runs the default Google search.
3. The agent opens Chrome, works through the task, and prints its answer under `=== ANSWER ===`.

## Problems, in the order I hit them

| # | What I tried | Error | Cause | Fix |
|---|---|---|---|---|
| 1 | The example as shipped: `ChatBrowserUse(model='bu-2-0-mini-preview')` | `403 Forbidden`: "Free tier accounts are not allowed to use the LLM Gateway" | browser-use's own hosted model service needs a paid plan | Switched to another provider |
| 2 | `ChatDeepSeek(model='deepseek-v4-flash')` with `DEEPSEEK_API_KEY` in `.env` | "The api_key client option must be set ... by setting the OPENAI_API_KEY environment variable" | `ChatDeepSeek.api_key` defaults to `None` (`browser_use/llm/deepseek/chat.py:41`) and is handed to the OpenAI library's client (line 52), which only falls back to `OPENAI_API_KEY`. `ChatBrowserUse` reads its own key from the environment (`browser_use/llm/browser_use/chat.py:94`); `ChatDeepSeek` doesn't. | Passed the key explicitly: `api_key=os.getenv('DEEPSEEK_API_KEY')` |
| 3 | DeepSeek, key now passed correctly | `402 Insufficient Balance` | DeepSeek is prepaid and the account had no credit | Switched to Gemini's free tier |
| 4 | `ChatGoogle(model='gemini-flash-latest')`, which currently points to `gemini-3.8-flash` | `503 UNAVAILABLE` ("high demand"), then `429 RESOURCE_EXHAUSTED` | That model was overloaded, and the free tier allows 5 requests per minute on it | Picked a less busy model (next row) |
| 5 | Sent one tiny request to each candidate model | `gemini-2.5-flash` and `gemini-2.5-flash-lite`: `404 NOT_FOUND` | Google has retired them, though browser-use still lists them in `VerifiedGeminiModels` (`browser_use/llm/google/chat.py:26`) | Used `gemini-3.5-flash-lite` (answered in 0.5 s), with `gemini-3.1-flash-lite` (1.7 s) as the backup |

**Hardest problem:** row 2. I had set `DEEPSEEK_API_KEY`, but the error told me to set `OPENAI_API_KEY`, so the message pointed at the wrong cause. The fix was one argument; finding it meant reading `ChatDeepSeek` to see that it never reads its own environment variable.

**Other things I noticed while debugging:**
- The agent retried the `402` six times before stopping, even though a billing error can't fix itself between tries.
- DeepSeek can't use screenshots. The Agent prints "DeepSeek models do not support use_vision=True" and switches them off, based on a check of the model's name (`browser_use/agent/service.py:476`).

## Changes to the code

One file changed: `examples/getting_started/01_basic_search.py`.

- Uses Gemini (`gemini-3.5-flash-lite`) instead of browser-use's paid service, passing the key explicitly.
- Adds a backup model with `fallback_llm` (`gemini-3.1-flash-lite`). The Agent switches to it on a `429` or `503`, and it has its own quota.
- Takes the task from the command line, or asks for one, instead of always running the same search.
- Prints the final answer at the end.

Full diff against the original:

```diff
diff --git a/examples/getting_started/01_basic_search.py b/examples/getting_started/01_basic_search.py
index ba4f26f4c..e60acb1b7 100644
--- a/examples/getting_started/01_basic_search.py
+++ b/examples/getting_started/01_basic_search.py
@@ -1,7 +1,7 @@
 """
 Setup:
-1. Get your API key from https://cloud.browser-use.com/new-api-key
-2. Set environment variable: export BROWSER_USE_API_KEY="your-key"
+1. Get your API key from https://aistudio.google.com/apikey
+2. Set environment variable: export GOOGLE_API_KEY="your-key"
 """
 
 import asyncio
@@ -15,14 +15,17 @@ from dotenv import load_dotenv
 
 load_dotenv()
 
-from browser_use import Agent, ChatBrowserUse
+from browser_use import Agent, ChatGoogle
 
 
 async def main():
-	llm = ChatBrowserUse(model='bu-2-0-mini-preview')
-	task = "Search Google for 'what is browser automation' and tell me the top 3 results"
-	agent = Agent(task=task, llm=llm)
-	await agent.run()
+	llm = ChatGoogle(model='gemini-3.5-flash-lite', api_key=os.getenv('GOOGLE_API_KEY'))
+	fallback_llm = ChatGoogle(model='gemini-3.1-flash-lite', api_key=os.getenv('GOOGLE_API_KEY'))
+	default_task = "Search Google for 'what is browser automation' and tell me the top 3 results"
+	task = ' '.join(sys.argv[1:]) or input('What should the agent do? (Enter for the default search)\n> ').strip() or default_task
+	agent = Agent(task=task, llm=llm, fallback_llm=fallback_llm)
+	history = await agent.run()
+	print('\n=== ANSWER ===\n' + (history.final_result() or '(no answer - the task did not finish)'))
 
 
 if __name__ == '__main__':
```

## Runs that worked

- Default Google search: 4 steps. Top 3 results were BrowserStack, Skyvern and Oxylabs.
- "Go to example.com and tell me the main heading on the page": 1 step, answered "Example Domain".
- Typed at the prompt, "Go to example.com and tell me what the link on the page says": answered "Learn more".
- Wikipedia "Unified Process" task: 2 steps, about 80 seconds. Answered: "The unified software development process or unified process is an iterative and incremental software development process framework."

## Demo backup

`docs/demo-backup.gif` is a recording of the Wikipedia run, made by passing `generate_gif=<path>` to `Agent`. Recording roughly doubled the run time (158 s vs 79 s). `.gif` files are gitignored, so it stays on this machine only.
