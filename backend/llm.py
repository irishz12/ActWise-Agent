import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

BASE_URL = os.getenv("OPENAI_BASE_URL")
API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("ACTWISE_MODEL")

if not BASE_URL:
    raise RuntimeError("OPENAI_BASE_URL is not set")

if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set")

if not MODEL:
    raise RuntimeError("ACTWISE_MODEL is not set")

client = OpenAI(
    base_url=BASE_URL,
    api_key=API_KEY,
)
