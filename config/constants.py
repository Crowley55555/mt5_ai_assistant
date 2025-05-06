class Timeframes:
    M1 = 1
    M5 = 5
    M15 = 15
    M30 = 30
    H1 = 60
    H4 = 240
    D1 = 1440
    W1 = 10080
    MN1 = 43200

class TradeAction:
    BUY = 'buy'
    SELL = 'sell'
    CLOSE = 'close'

class OrderType:
    MARKET = 0
    LIMIT = 1
    STOP = 2

class StrategyNames:
    SNIPER = "Снайпер"
    SMART_SNIPER = "Смарт Снайпер"
    SMART_MONEY = "Смарт Мани"