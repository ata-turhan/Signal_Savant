import ccxt
import addict
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def get_data(symbol: str, exchange_id: str, timeframe: str, 
            since: str, limit: int) -> pd.DataFrame:
    """
    This function downloads data from exchange using ccxt library

    Args:
        symbol (str): name of trading pair
        exchange_id (str): name of exchange 
        timeframe (str): timeframe: 1d, 4h, 1h, 15m, 5m, etc.
        since (str): time from which the download starts
        limit (int): api limit

    Returns:
        pd.DataFrame: downloaded data 
    """

    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class({
            'timeout': 30000,
            'enableRateLimit': True,
    })
    since = exchange.parse8601(since) 

    while True:
        try: 
            loaded_markets = exchange.load_markets()

            if exchange.has['fetchOHLCV']:
                all_orders = []
                while since < exchange.milliseconds(): 
                    orders = exchange.fetch_ohlcv(symbol=symbol, 
                                                    timeframe=timeframe, 
                                                    since=since, limit=limit)
                    if len(orders) == 1:
                        break
                    if len(orders):
                        since = orders[len(orders) - 1][0]
                        all_orders += orders
                    else:
                        break
            break
        except Exception as e:
            print("Exception in get_data: ", e) 
            exchange.sleep(exchange.rateLimit * 2)
            continue

    data = pd.DataFrame(data=all_orders, 
                        columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume']).drop_duplicates().reset_index(drop=True)
    data['Date'] = pd.to_datetime(data['Date'], unit='ms')
    data['Symbol'] = symbol
 
    return data


def get_signal(config: addict.Dict) -> pd.DataFrame:
    # Download data
    data = get_data(symbol=config.symbol, exchange_id=config.exchange_id, 
                     timeframe=config.timeframe_from, 
                     since=config.since, limit=config.limit) 

    # Prepare data to compute vpr
    data = data.set_index('Date')
    data['return'] = data.Close.diff()
    data['positive_return'] = (data['return'] > 0).astype(int)

    data['volume_price_pos'] = 0
    data['volume_price_neg'] = 0
    
    def calculate_vpr(ser: pd.Series) -> float:
        # Select portion of data
        window = data.loc[ser.index]

        # Computes sums of negative and positive returns 
        positive_return = window[window['positive_return'] == 1]
        negative_return = window[window['positive_return'] == 0]
        return_pos_sum = positive_return['return'].sum()
        return_neg_sum = negative_return['return'].sum()

        # Computes Volumes in positive and negative returns
        volume_price_pos = (positive_return['Volume'].sum() / return_pos_sum).round(3)
        volume_price_neg = (negative_return['Volume'].sum() / return_neg_sum).round(3)

        # Calculate vpr
        vpr = (abs(volume_price_pos) * 100 / (abs(volume_price_pos) + abs(volume_price_neg))).round(3)

        return vpr

    # Resample to the target timeframe and apply calculate_vpr
    # as aggregation function to get vpr
    vpr = data.resample(config.timeframe_to)[['Close']].apply(calculate_vpr)
    vpr.name = 'vpr'

    # Resample all data to the target timeframe
    resampled_data = data.resample(config.timeframe_to).agg({
        'Open': 'first', 
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum',
        'Symbol': 'first'
    })

    # Add vpr to the main dataframe
    resampled_data = resampled_data.join(vpr).reset_index()
    
    # Calculate signals
    resampled_data['hard_to_grow'] = resampled_data.vpr >= config.hard_to_grow_th
    resampled_data['hard_to_fall'] = resampled_data.vpr <= config.hard_to_fall_th
    
    return resampled_data


def create_plot(config: addict.Dict, data: pd.DataFrame) -> bytes:
    data = data.tail(config.data_horizon)
    fig = make_subplots(rows=2, cols=1, start_cell="top-left", 
                    subplot_titles=('OHLC', 'VPR'), vertical_spacing = 0.05)
    fig.add_trace(go.Candlestick(x=data['Date'],
                    open=data['Open'],
                    high=data['High'],
                    low=data['Low'],
                    close=data['Close'], 
                    increasing_line_color='green', 
                    decreasing_line_color='red'),
                row=1, col=1)
    fig.add_trace(go.Scatter(x=data['Date'], 
                            y=data['vpr'],
                            line_color="red", mode='lines',
                    name='vpr'),
                row=2, col=1)
    fig = fig.update_layout(hovermode="x", height=900, width=1000,
                title_text="VPR", xaxis_rangeslider_visible=False)
    fig = fig.to_image(format="png")
    
    return fig