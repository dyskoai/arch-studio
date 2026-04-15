from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from google.adk.models.lite_llm import LiteLlm

from .prompt import ROUTER_PROMPT
from .tools.styling_tool import find_styling_ideas
from .tools.pairing_tool import find_pairing_suggestions
from .tools.product_tool import find_products_directly

root_agent = Agent(
    model=LiteLlm(model="cerebras/gpt-oss-120b",
        fallbacks=["groq/openai/gpt-oss-120b", "gemini/gemini-2.5-flash-lite"],
        num_retries=1
    ),
    name="main_chat_agent",
    instruction=ROUTER_PROMPT,
    tools= [
         FunctionTool(find_styling_ideas),
         FunctionTool(find_pairing_suggestions),
         FunctionTool(find_products_directly),
     ],
)
