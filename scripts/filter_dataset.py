"""
Apply filtering decisions to create the final filtered dataset.

This script:
1. Loads filtering decisions from filtering_v2.csv
2. Filters the original dataset to keep only KEEP samples
3. Creates dataset_filtered_v2.csv with same structure as original

Usage:
    python filter_dataset.py
"""

import pandas as pd
import sys


def create_filtered_dataset(decisions_file='filtering_v2.csv',
                            input_file='data/dataset.csv',
                            output_file='dataset_filtered_v2.csv'):
    """
    Create filtered dataset from filtering decisions.

    Args:
        decisions_file: CSV with filtering decisions
        input_file: Original dataset
        output_file: Output filtered dataset

    Returns:
        Number of samples in filtered dataset
    """
    print(f'Loading filtering decisions from {decisions_file}...')
    df_decisions = pd.read_csv(decisions_file)

    print(f'Loading original dataset from {input_file}...')
    df_full = pd.read_csv(input_file)

    # Get indices of KEEP samples
    keep_decisions = df_decisions[df_decisions['decision'] == 'KEEP']
    keep_indices = keep_decisions['index'].tolist()

    print(f'\nFiltering statistics:')
    print(f'  Total samples: {len(df_full)}')
    print(f'  KEEP: {len(keep_decisions)} ({len(keep_decisions)/len(df_full)*100:.1f}%)')
    print(f'  EXCLUDE: {len(df_decisions[df_decisions["decision"] == "EXCLUDE"])}')
    print(f'  UNCLEAR: {len(df_decisions[df_decisions["decision"] == "UNCLEAR"])}')

    # Filter dataset
    df_filtered = df_full.iloc[keep_indices].copy()

    # Save filtered dataset with SAME columns as original
    df_filtered.to_csv(output_file, index=False)

    print(f'\nCreated {output_file} with {len(df_filtered)} samples')
    print(f'Columns: {len(df_filtered.columns)} (same as original)')

    # Print performance stats
    print(f'\nPerformance statistics (KEEP samples):')
    print(f'  Mean: {df_filtered["human_performance"].mean():.6f}')
    print(f'  Median: {df_filtered["human_performance"].median():.6f}')
    print(f'  Min: {df_filtered["human_performance"].min():.6f}')
    print(f'  Max: {df_filtered["human_performance"].max():.6f}')

    return len(df_filtered)


def main():
    if len(sys.argv) > 1:
        decisions_file = sys.argv[1]
    else:
        decisions_file = 'filtering_v2.csv'

    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        output_file = 'dataset_filtered_v2.csv'

    create_filtered_dataset(
        decisions_file=decisions_file,
        output_file=output_file
    )


if __name__ == '__main__':
    main()
