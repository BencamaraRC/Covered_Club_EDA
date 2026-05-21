"""
Ingest layer. One module per data source.

Each module exposes:
    fetch(force_refresh: bool = False) -> pd.DataFrame

Convention: cache the raw download in data/raw/, return a tidy DataFrame.
"""
