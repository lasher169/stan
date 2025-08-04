from trade_data import IBKR
from ib_insync import *
import time
def setup_ibkr(port=4002):
    ibkr = IBKR()
    ibkr.connect("127.0.0.1", port, clientId=0)
    return ibkr

def getData(app, ticker, currency, duration, bar_size, dollar_size_limit, exchange_type):
    time.sleep(3)  # space requests to avoid rate limits

    data = (app.get_historical_data(ticker, currency, duration, bar_size, exchange_type))
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

def stop_pct_from_price(price):
    if price < 0.2:
        return 0.12
    elif price < 0.5:
        return 0.08
    elif price < 1:
        return 0.06
    elif price < 5:
        return 0.05
    elif price < 10:
        return 0.04
    elif price < 20:
        return 0.03
    else:
        return 0.025

def place_order(app, ticker, price, action, exchange, currency, volume, logger):
    """
    Places a limit entry order.
    action = 'BUY' or 'SELL'
    """
    contract = Stock(ticker, exchange, currency)
    limit_order = LimitOrder(action, volume, price)
    app.placeOrder(contract, limit_order)
    app.sleep(1)
    logger.info(f"Limit {action.upper()} order at {price} placed.")
    return contract, price  # Return contract for stop-loss


def place_stop_loss(app, contract, entry_price, action, volume, logger):
    """
    Places a protective stop-loss order.
    For BUY entry: places a SELL stop-loss.
    For SELL entry: places a BUY stop-loss.
    """
    stop_pct = stop_pct_from_price(entry_price)
    if action.upper() == 'BUY':
        stop_price = round(entry_price * (1 - stop_pct), 4)
        stop_action = 'SELL'
    else:
        stop_price = round(entry_price * (1 + stop_pct), 4)
        stop_action = 'BUY'

    stop_order = StopOrder(stop_action, volume, stop_price)
    app.placeOrder(contract, stop_order)
    logger.info(f"Stop {stop_action} at {stop_price} placed.")

if __name__ == "__main__":
    app = setup_ibkr(4002)
    ticker = "ACM"
    getData(app, ticker, currency="AUD", duration="120 d", bar_size="1 day", dollar_size_limit=1000000, exchange_type="ASX")