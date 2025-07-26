from trade_data import IBKR
import time
def setup_ibkr(port=4002):
    ibkr = IBKR()
    ibkr.connect("127.0.0.1", port, clientId=0)
    return ibkr

def getData(app, ticker, currency, duration, bar_size, dollar_size_limit):
    time.sleep(3)  # space requests to avoid rate limits

    data = (app.get_historical_data(ticker, currency, duration, bar_size))
    # if data:
    #     close_price = data[-1][-1].close
    #     vol = data[-1][-1].volume
    #     volume_dollar = close_price * vol
    #     if volume_dollar > float(dollar_size_limit):
    #         print(f"keeping Stock over", dollar_size_limit)
    #         return data
    #     else:
    #         print(f"kicking out Stock under",dollar_size_limit)
    #         return []
    # else:
    #     print(f"kicking out no data")

    if data:
        total_dollar_volume = 0

        for i in range(len(data)):
            entry = data[i]
            close_price = entry.close
            vol = entry.volume
            dollar_vol = close_price * vol

            total_dollar_volume += dollar_vol

        average_dollar_volume = total_dollar_volume / len(data)

        if average_dollar_volume > float(dollar_size_limit):
            print(f"Keeping stock {ticker} over {dollar_size_limit} dollar volume, average dollar amount is {average_dollar_volume}")
            return data
        else:
            print(f"Kicking out stock {ticker} under {dollar_size_limit} dollar volume, average amount is {average_dollar_volume}")
    else:
        print(f"No data available {ticker}")

    return []