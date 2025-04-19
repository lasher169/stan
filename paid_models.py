import os
import google.generativeai as genai
import itertools
import time

API_KEYS = [
    os.getenv("GOOGLE_API_KEY1"),
    os.getenv("GOOGLE_API_KEY2"),
    os.getenv("GOOGLE_API_KEY3"),
    os.getenv("GOOGLE_API_KEY4"),
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

def generate_insight(ticker_data):
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

        prompt = f"Here is the daily price data for the stock AAPL (or any symbol). Please apply Stan Weinstein’s 4-stage trend analysis using a 30-day moving average. Also identify all points where the 5-day moving average crosses the 30-day moving average (bullish or bearish). For each crossover: \
	            •	Note the date and direction (bullish or bearish) \
	            •	Classify the Weinstein stage at the time (Stage 1–4) \
	            •	Measure price change over the next 10, 20, and 30 trading days \
	            •	Summarize the strength of the trend (strong, weak, or flat)"

        print(f"Sending prompt to Gemini: {prompt}")

        response = model.generate_content(prompt)
        insight = response.text.strip()

        print(f"Gemini Response: {insight}")
        return insight

    except Exception as e:
        print(f"Error: {e} (API Key: {key}). Not retrying.")
        return None  # Or handle it as needed
