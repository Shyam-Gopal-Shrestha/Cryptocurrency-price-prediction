import pandas as pd
import numpy as np
import ta

def add_lag_features(df, columns, lags=[1, 7, 14, 30]):
    """Add lagged features for specified columns."""
    for col in columns:
        for lag in lags:
            df[f'{col}_lag_{lag}'] = df[col].shift(lag)
    return df

def add_moving_averages(df, column='Close', windows=[7, 30]):
    """Add moving averages."""
    for window in windows:
        df[f'MA_{window}'] = df[column].rolling(window=window).mean()
    return df

def add_daily_returns(df, column='Close'):
    """Add daily returns."""
    df['Daily_Return'] = df[column].pct_change()
    return df

def add_rolling_volatility(df, column='Daily_Return', windows=[7, 30]):
    """Add rolling volatility."""
    for window in windows:
        df[f'RollVol_{window}'] = df[column].rolling(window=window).std()
    return df

def add_technical_indicators(df):
    """Add RSI and MACD using ta library."""
    # RSI
    df['RSI'] = ta.momentum.RSIIndicator(df['Close']).rsi()

    # MACD
    macd = ta.trend.MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    df['MACD_Hist'] = macd.macd_diff()

    return df

def preprocess_data(df):
    """Full preprocessing pipeline."""
    df = df.copy()
    df = add_daily_returns(df)
    df = add_moving_averages(df)
    df = add_rolling_volatility(df)
    df = add_lag_features(df, ['Close', 'Volume'])
    df = add_technical_indicators(df)
    df = df.dropna()  # Drop rows with NaN after lagging
    return df