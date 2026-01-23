import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHAT_MODEL = "gpt-4.1-mini"
ANALYSIS_MODEL = "gpt-5-nano"
