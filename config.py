import addict


def create_config() -> addict.Dict:
    config = addict.Dict()
    config.limit = 1000
    config.symbol = 'BTC/USDT'
    config.exchange_id = 'binance'
    config.timeframe_from = '5m'
    config.timeframe_to = '1h'
    config.since = '2023-01-01T00:00:00Z'

    config.hard_to_grow_th = 60
    config.hard_to_fall_th = 40

    config.data_horizon = 60

    return config
