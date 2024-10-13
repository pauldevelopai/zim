import os
import openai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve the OpenAI API key from the environment
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OpenAI API key not found. Please set it in the .env file.")

# Set the OpenAI API key
openai.api_key = api_key

# Function to test OpenAI API call
def test_openai_api():
    try:
        response = chat.completions.create(model="gpt-4",  # Change to "gpt-4" if available to you
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, can you help me with some coding advice?"}
        ],
        max_tokens=100,
        temperature=0.5)
        response_text = response.choices[0].message.content
        print("Response from OpenAI API:", response_text)

    except Exception as e:
        print(f"Failed to connect to OpenAI API: {e}")

if __name__ == "__main__":
    test_openai_api()