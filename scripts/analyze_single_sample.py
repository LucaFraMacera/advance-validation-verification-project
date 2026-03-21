"""
End-to-end analysis of a single sample.

This is the main orchestrator that:
1. Loads sample data from dataset.csv
2. Fetches commit information (merge detection)
3. Analyzes code patterns
4. Makes classification decision

Usage:
    python analyze_single_sample.py <sample_index>
    python analyze_single_sample.py 119
"""

import sys
import pandas as pd
import json
from fetch_commit_info import analyze_commit
from analyze_code_patterns import analyze_optimization_patterns, classify_from_commit_message
from classify_sample import classify_sample


def analyze_sample(idx):
    """
    Complete analysis pipeline for a single sample.

    Args:
        idx: integer index in dataset.csv

    Returns:
        dict with all analysis results
    """
    print(f'\n{"="*80}')
    print(f'ANALYZING SAMPLE {idx}')
    print(f'{"="*80}\n')

    # Step 1: Load sample from dataset
    df = pd.read_csv('./data/dataset.csv')
    row = df.iloc[idx]

    instance_id = row['instance_id']
    repo = row['repo']
    base_commit = row['base_commit']
    head_commit = row['head_commit']
    patch = row['patch']
    performance = row['human_performance']

    print(f'Instance ID: {instance_id}')
    print(f'Repository: {repo}')
    print(f'Performance: {performance:.6f}')
    print()

    # Step 2: Fetch commit information
    print('Step 1: Fetching commit information from GitHub API...')
    commit_info = analyze_commit(repo, base_commit, head_commit)

    if 'error' in commit_info:
        print(f'  ERROR: {commit_info["error"]}')
        return {
            'index': idx,
            'instance_id': instance_id,
            'error': commit_info['error']
        }

    print(f'  Type: {"MERGE" if commit_info["is_merge"] else "SINGLE"} commit')
    print(f'  Total commits: {commit_info["total_commits"]}')

    if commit_info['is_merge']:
        print(f'  Sample commit messages:')
        for i, c in enumerate(commit_info['commits'][:5]):
            print(f'    {i+1}. {c["message"][:70]}')
        if len(commit_info['commits']) > 5:
            print(f'    ... and {len(commit_info["commits"]) - 5} more')
    else:
        print(f'  Message: {commit_info["commits"][0]["message"][:80]}')

    print()

    # Step 3: Analyze code patterns
    print('Step 2: Analyzing code patterns (PRIMARY)...')
    code_analysis = analyze_optimization_patterns(patch)

    print(f'  Has optimization: {code_analysis["has_optimization"]}')

    if code_analysis['has_optimization']:
        print(f'  Primary pattern: {code_analysis["primary_pattern"]}')
        print(f'  Evidence:')
        for ev in code_analysis['evidence']:
            print(f'    - {ev}')
    else:
        print(f'  No optimization patterns detected')

    print()

    # Step 4: Make classification decision
    print('Step 3: Making classification decision...')
    classification = classify_sample(commit_info, code_analysis, performance)

    print(f'  Decision: {classification["decision"]}')
    print(f'  Reason: {classification["reason"]}')
    print()

    # Combine all results
    result = {
        'index': idx,
        'instance_id': instance_id,
        'decision': classification['decision'],
        'reason': classification['reason'],
        'performance': performance,
        'is_merge': commit_info['is_merge'],
        'commits_analyzed': commit_info['total_commits'],
        'primary_pattern': classification['primary_pattern'],
        'code_stats': code_analysis['stats']
    }

    return result


def main():
    if len(sys.argv) != 2:
        print('Usage: python analyze_single_sample.py <sample_index>')
        print('Example: python analyze_single_sample.py 119')
        sys.exit(1)

    idx = int(sys.argv[1])
    result = analyze_sample(idx)

    if 'error' not in result:
        print(f'\n{"="*80}')
        print('RESULT')
        print(f'{"="*80}\n')
        print(json.dumps(result, indent=2))

        # Optionally append to decisions file
        print('\nAppend to filtering_decisions_v2.csv? [y/N]: ', end='')
        choice = input().strip().lower()

        if choice == 'y':
            df_result = pd.DataFrame([{
                'index': result['index'],
                'instance_id': result['instance_id'],
                'decision': result['decision'],
                'reason': result['reason'],
                'performance': result['performance']
            }])

            import os
            file_exists = os.path.exists('filtering_decisions_v2.csv')

            df_result.to_csv(
                'filtering_decisions_v2.csv',
                mode='a',
                header=not file_exists,
                index=False
            )
            print('Saved to filtering_decisions_v2.csv')


if __name__ == '__main__':
    main()
