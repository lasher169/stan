import os
import google.generativeai as genai
import itertools
import time

API_KEYS = [
    os.getenv("GOOGLE_API_KEY1"),
    os.getenv("GOOGLE_API_KEY2"),
    os.getenv("GOOGLE_API_KEY3"),
    os.getenv("GOOGLE_API_KEY4"),
    os.getenv("GOOGLE_API_KEY5"),
    os.getenv("GOOGLE_API_KEY6")
]

# Remove None values in case some keys are missing
API_KEYS = [key for key in API_KEYS if key]

if not API_KEYS:
    raise ValueError("No valid API keys found. Please check your environment variables.")

# Create a cycle iterator for API keys
api_key_cycle = itertools.cycle(API_KEYS)

# Track the number of requests per API key
api_usage = {key: 0 for key in API_KEYS}
REQUEST_LIMIT = 15  # Max requests per API key per minute
TIME_WINDOW = 60  # Time window in seconds (1 minute)

def get_next_api_key():
    """Returns the next API key in the cycle."""
    return next(api_key_cycle)

def configure_gemini():
    """Configures the Gemini API with the next available API key."""
    next_key = get_next_api_key()
    genai.configure(api_key=next_key)
    return next_key

# Set initial API key
current_api_key = configure_gemini()
model = genai.GenerativeModel('gemini-2.0-flash')

def enforce_rate_limit():
    """Ensures requests do not exceed the allowed limit per API key per minute."""
    global current_api_key

    if api_usage[current_api_key] >= REQUEST_LIMIT:
        print(f"API key {current_api_key} reached limit. Switching keys...")
        current_api_key = configure_gemini()
        api_usage[current_api_key] = 0  # Reset usage for the new key
        print(f"Switched to API key: {current_api_key}")

    api_usage[current_api_key] += 1
    print(f"Using API key {current_api_key}, Request Count: {api_usage[current_api_key]}")

def generate_insight(ticker):
    """
    Generates an investment insight based on a given RAG status, ticker symbol,
    5-day SMA, and 30-day SMA using the Gemini Pro model.

    Args:
        rag_status (str): The RAG (Red, Amber, Green) status of the stock.
        ticker (str): The ticker symbol of the stock.
        sma_5 (float): The 5-day Simple Moving Average.
        sma_30 (float): The 30-day Simple Moving Average.

    Returns:
        str: The generated investment insight, or "Insight generation failed"
             if an error occurs.
    """
    try:

        # Introduce a 10-second delay before switching to the next API key
        time.sleep(10)

        # Switch to the next API key
        key = configure_gemini()

        with open(f'data/{ticker}.csv', "rb") as file:
            uploaded_file = model.files.upload(file=file)
            print(f"File uploaded successfully. File ID: {uploaded_file.id}")

        prompt = f"Given daily prices and dividend history for {ticker}: \
	            •	Use 30-day MA to assign Stan Weinstein stage (1–4) \
	            •	Identify 5/30-day MA crossovers: \
	            •	Date, type (bullish/bearish), stage, price change after 10/20/30 days, trend strength \
	            •	Comment on dividend pattern (e.g., consistency, yield impact on trend)"

        print(f"Sending prompt to Gemini: {prompt}")

        response = model.generate_content(prompt)
        insight = response.text.strip()

        print(f"Gemini Response: {insight}")
        return insight

    except FileNotFoundError as e:
        print(f"Error: File not found at path {e.filename}. Not retrying.")
        return None
    except Exception as e:
        print(f"Error: {e} (API Key: {key}). Not retrying.")
        return None  # Or handle it as needed
