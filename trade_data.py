from ibapi.client import *
from ibapi.wrapper import *
port = 4002
import threading
import datetime as dt
import time

# Ensure the same logger is used
logger = logging.getLogger('main')  # This should match the logger name from main.py

class IBKR(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)
        self.valid_id_received = threading.Event()
        self.data = []
        self.orderId = None
        self.lock = threading.Lock()

    def nextValidId(self, orderId):
        self.orderId = orderId
        self.valid_id_received.set()

    def nextId(self):
        with self.lock:
            self.orderId += 1
            return self.orderId

    def historicalData(self, reqId, bar):
        self.data.append(bar)

    def historicalDataEnd(self, reqId, start, end):
        self.done.set()

    def get_historical_data(self, symbol, currency, duration, bar_size):
        self.data = []  # Clear previous data
        self.done = threading.Event()

        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = currency

        now = dt.datetime.now().strftime('%Y%m%d %H:%M:%S Australia/Sydney')
        self.reqHistoricalData(self.nextId(), contract, now, duration, bar_size, "TRADES", 1, 1, False, [])

        # Wait until data is received or timeout
        self.done.wait(timeout=10)
        return self.data

if __name__ == "__main__":
    app = IBKR()
    app.connect("127.0.0.1", port, clientId=123)
    threading.Thread(target=app.run, daemon=True).start()
    time.sleep(1)

    for i in range(5):
        app.get_historical_data("MQG", "AUD", "1 D", "1 hour")
        print(app.data)