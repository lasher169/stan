import pandas as pd
from io import StringIO

import ollama


def generate_insight(ticker, model):
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
        with open(f'data/{ticker}.csv', 'r') as file:
            contents = file.read()

        df = pd.read_csv(StringIO(contents), index_col='Date')
        # Rename columns to remove spaces for easier handling
        df.rename(columns={'Open Price': 'Open', 'Close Price': 'Close', 'High Price': 'High', 'Low Price': 'Low'},
                  inplace=True)

        # Introduce a 10-second delay before switching to the next API key
        prompt = f" Based on the most recent crossover between the 8-day and 21-day simple moving averages (SMA), and checking if today’s Volume is greater than the 20-day average Volume: \n \
                            Tell me: STAGE1, STAGE2, STAGE3 or STAGE4. \n \
                            Only the final decision — no code, tell me what day the 8 day broken past the 21 day. \n \
                            \n \
                            {df.to_string()}"

        print(f"Sending prompt to Ollamm: ")
        response = ollama.generate_insight(model=model, messages=[
            {
                "role": "system",
                "content": prompt
            },
        ])

        print(f"Sending prompt to Gemini: {prompt}")
        insight = response.text.strip()

        print(f"{model} Response: {insight}")
        return insight

    except Exception as e:
        return None  # Or handle it as needed
