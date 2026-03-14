import pandas as pd
from datasets import load_dataset

def load_from_csv(path):
    return pd.read_csv(path)

def load_from_hf(name, split = None):
    ds = load_dataset(name)
    if split is not None:
        ds = ds[split]
    return ds.to_pandas()
