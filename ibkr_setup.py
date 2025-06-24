from trade_data import IBKR
def setup_ibkr(port=4002):
    ibkr = IBKR()
    ibkr.connect("127.0.0.1", port, clientId=0)
    return ibkr