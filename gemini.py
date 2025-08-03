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

def generate_insight(logger, data):
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
            base_prompt = (
                "Act as a rules-based trading analyst. Using the provided OHLCV data, determine the stock's current stage based on a strict, classic Stan Weinstein method.\n\n"
                "**Stage Rules:**\n"
                "1. **Stage 1 (Basing):** The 30-day SMA is flattening (trending sideways). The price oscillates above and below the 30-day SMA.\n"
                "2. **Stage 2 (Advancing):** Must meet all three criteria, all on the same day:\n"
                "   a. **Breakout:** The price closes decisively above the Stage 1 resistance range, with a bullish 5/30 SMA crossover in place.\n"
                "   b. **Volume:** The breakout occurs on volume at least 2 times the 30-day average.\n"
                "   c. **Do NOT wait for a pattern of higher highs or higher lows. Stage 2 is confirmed immediately on the breakout day if the above conditions are met.**\n"
                "   - After entry, monitor for continuation, but entry is made on breakout day if above criteria are met.\n\n"
                "3. **Stage 3 (Topping):** After a Stage 2 advance, the 30-day SMA flattens. Price action becomes choppy and more frequently crosses below the 30-day SMA. A bearish 5/30 crossover may occur.\n"
                "4. **Stage 4 (Declining):** The price is consistently below a declining 30-day SMA, often with the 5-day SMA also below. Price forms lower highs and lower lows.\n\n"
                "Evaluate the most recent data first. Identify:\n"
                "- The current stage of the stock (STAGE1, STAGE2, STAGE3, or STAGE4)\n"
                "- The most recent **confirmed 5/30 bullish crossover** date that initiated a valid Stage 2 breakout (if any)\n"
                "**Always identify the current stage based on the latest data, even if a previous Stage 2 breakout was detected. Never report Stage 2 if the stock is now in Stage 3 or Stage 4.**\n\n"
                "Return only the following format:\n"
                "STAGEX Crossover on YYYY-MM-DD at $CLOSE_PRICE\n"
            )

            # # === Optional Stage99 block for flagged shares
            # stage99_block = ""
            # if open_crossover_date and open_crossover_price:
            #     target_price = round(float(open_crossover_price) * 1.10, 4)
            #     stage99_block = (
            #         "**Momentum Failure Rule (only applies to flagged Stage 2 stocks):**\n"
            #         f"If the most recent confirmed 5/30 crossover was on {open_crossover_date} at ${open_crossover_price},\n"
            #         f"and 20 or more trading days have passed since that date, and the current price is less than 10% above the crossover price (i.e., less than ${target_price}),\n"
            #         "then return:\n"
            #         "STAGE99 on YYYY-MM-DD at $CLOSE_PRICE\n"
            #         "to indicate the breakout failed due to lack of momentum.\n\n"
            #     )
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