import os
from dotenv import load_dotenv
import streamlit as st

# Load environment variables from a .env file if available
load_dotenv()

# Preferred way: get OpenAI API key from .env, otherwise from Streamlit secrets
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    # Fallback to Streamlit secrets if .env is not provided or doesn't contain the key
    try:
        OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    except Exception:
        OPENAI_API_KEY = None

# Optionally, you can define default model names or other configuration
# e.g. for OpenAI and local Ollama model.
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2")

# Timezone for interpreting naive datetimes (e.g. in calendar events)
TIMEZONE = os.getenv("TIMEZONE", "Europe/Berlin")

# If an OpenAI API key was loaded, optionally set the openai library's key for convenience
try:
    import openai
    if OPENAI_API_KEY:
        openai.api_key = OPENAI_API_KEY
except ImportError:
    # openai library might not be installed if not using OpenAI
    pass
