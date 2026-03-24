from data_loader import load_and_save

cryptos = ["BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD"]

for crypto in cryptos:
    df = load_and_save(crypto)

    if df is not None:
        print(f"\n{crypto} First rows:")
        print(df.head())

        print(f"\n{crypto} Last rows:")
        print(df.tail())