import ollama

def generate_insight(ticker_data, model):
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
        header = ticker_data[0]
        rows = ticker_data[1:]
        stock_data_str = '\n'.join([', '.join(map(str, row)) for row in [header] + rows])
        # Introduce a 10-second delay before switching to the next API key
        prompt = f"""Here is the daily stock data with Date and Close. Please apply Stan Weinstein’s 4-stage trend analysis. Use a 30-day moving average to assess the stage (Basing, Advancing, Topping, Declining). Also, identify all points where the 5-day moving average crosses the 30-day moving average (upward or downward). For each crossover: 
        	                •	Mark the date and whether it’s a bullish (SMA5 > SMA30) or bearish (SMA5 < SMA30) crossover. 
        	                •	Tell me which Weinstein stage the stock is in at that time. 
        	                •	Measure the price change in the 10, 20, and 30 days after the crossover. 
        	                •	Give an opinion on whether the trend that followed was strong, weak, or flat. 
        	      Stock data:          
                  {stock_data_str}
        	      """

        print(f"Sending prompt to Ollamm: ")
        response = ollama.chat(model=model, messages=[
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
