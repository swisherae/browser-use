"""
Setup:
1. Get your API key from https://aistudio.google.com/apikey
2. Set environment variable: export GOOGLE_API_KEY="your-key"
"""

import asyncio
import os
import sys

# Add the parent directory to the path so we can import browser_use
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv

load_dotenv()

from browser_use import Agent, ChatGoogle


async def main():
	llm = ChatGoogle(model='gemini-3.5-flash-lite', api_key=os.getenv('GOOGLE_API_KEY'))
	fallback_llm = ChatGoogle(model='gemini-3.1-flash-lite', api_key=os.getenv('GOOGLE_API_KEY'))
	default_task = "Search Google for 'what is browser automation' and tell me the top 3 results"
	task = ' '.join(sys.argv[1:]) or input('What should the agent do? (Enter for the default search)\n> ').strip() or default_task
	agent = Agent(task=task, llm=llm, fallback_llm=fallback_llm)
	history = await agent.run()
	print('\n=== ANSWER ===\n' + (history.final_result() or '(no answer - the task did not finish)'))


if __name__ == '__main__':
	asyncio.run(main())
