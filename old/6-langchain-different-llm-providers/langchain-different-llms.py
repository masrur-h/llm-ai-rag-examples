import os
from langchain.chat_models import init_chat_model

# Comparing Mistral, OpenAI (Azure), and Gemini with langchain

# API keys from environment variables
if not os.environ.get('MISTRAL_API_KEY'):
    raise ValueError("MISTRAL_API_KEY environment variable not set")

if not os.environ.get('AZURE_API_KEY'):
    raise ValueError("AZURE_API_KEY environment variable not set")

if not os.environ.get('AZURE_ENDPOINT'):
    raise ValueError("AZURE_ENDPOINT environment variable not set")

if not os.environ.get('GEMINI_API_KEY'):
    raise ValueError("GEMINI_API_KEY environment variable not set")


# Our prompt
prompt = "Explain LLM prompting in a concise way"

# Example of how to initialize different LLMs using langchain's init_chat_model
# Mistral model names here: https://docs.mistral.ai/getting-started/models/models_overview/
mistral_llm = init_chat_model(
    model="magistral-small-latest",
    model_provider="mistral",
    api_key=os.environ['MISTRAL_API_KEY'],
    temperature=0.7,
    max_retries=3
)

# Streaming output from mistral model
for chunk in mistral_llm.stream(prompt):
    print(chunk, end='', flush=True)

# Get full response from mistral model
#response = mistral_llm.invoke(prompt)

# Your task, implement the same for Azure OpenAI and Google Gemini
# Make sure to use the appropriate model names and parameters for each provider
# See more information here: https://python.langchain.com/docs/integrations/chat/
