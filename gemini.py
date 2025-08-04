from dotenv import load_dotenv
load_dotenv()
import os
import google.generativeai as genai
import itertools
import time
import pandas as pd
from io import StringIO


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
    #"""Configures the Gemini API with the next available API key."""
    next_key = get_next_api_key()
    genai.configure(api_key=next_key)
    return next_key

# Set initial API key
current_api_key = configure_gemini()
# Configure the API key
genai.configure(api_key=current_api_key)


def enforce_rate_limit():
    """Ensures requests do not exceed the allowed limit per API key per minute."""
    global current_api_key

    if api_usage[current_api_key] >= REQUEST_LIMIT:
        print(f"API key {current_api_key} reached limit. Switching keys...")
        # current_api_key = configure_gemini()
        # api_usage[current_api_key] = 0  # Reset usage for the new key
        print(f"Switched to API key: {current_api_key}")

    api_usage[current_api_key] += 1
    print(f"Using API key {current_api_key}, Request Count: {api_usage[current_api_key]}")

def generate_insight(ticker, logger, data, crossover_date, crossover_price):
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
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.0-flash')

        content = []


        for row in data:
            content.append(f"{row.date},{row.open},{row.high},{row.low},{row.close},{row.volume}\n")

            # === Base rules for all stocks ===
            base_prompt = ""
            breakout_prompt = (
                f"Act as a strict rules-based trading analyst. Using the provided OHLCV data, determine the first date the stock {ticker} entered Stage 2 based on the classic Stan Weinstein method.\n\n"
                "**Stage 2 confirmation requires ALL of the following on the SAME day:**\n"
                "1. CLOSE is ABOVE the resistance (highest CLOSE in past 6–8 weeks).\n"
                "2. 5-day SMA is ABOVE the 30-day SMA.\n"
                "3. Volume is at least 2× the 30-day average volume.\n\n"
                "**Return ONLY this format. No explanation:**\n"
                "- STAGEX on YYYY-MM-DD at $CLOSE_PRICE\n"
            )
            validation_prompt = (
                f"Act as a strict rules-based trading analyst. Using the provided OHLCV data, determine if Stage 2 is still valid for {ticker}.\n\n"
                f"Stage 2 breakout was previously confirmed on {crossover_date} at ${crossover_price:.2f}.\n"
                "**Stage 2 is considered FAILED if either of the following occurs:**\n"
                "- CLOSE remains below the 30-day SMA for 5 or more consecutive days.\n"
                "- The 30-day SMA flattens or turns downward.\n"
                "If failed, reclassify as Stage 1 or Stage 4 based on recent price action.\n\n"
                "**Return ONLY ONE of the following (no explanation):**\n"
                "- STAGEX on YYYY-MM-DD at $CLOSE_PRICE\n"
            )

            if crossover_date != None and crossover_price != None:
                base_prompt += validation_prompt
            else:
                base_prompt += breakout_prompt

        csv_header = "\n\nDate, Open, High, Low, Close, Volume\n"
        csv_data = ', '.join(map(str, content))
        prompt = f"{base_prompt}{csv_header}{csv_data}"

        logger.info(prompt)

        response = model.generate_content(prompt)

        # store this insight into a db table
        print(f"Gemini Response: {response.text}")
        return response.text

    except Exception as e:
        logger.error(f"Error: {e} (API Key: {key}). Not retrying.")
        return None  # Or handle it as needed

if __name__ == "__main__":
    ticker = "14D"
    generate_insight(ticker)