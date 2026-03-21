"""
Fetch commit information from GitHub API.

This script:
1. Checks if a commit is a merge (multiple parents)
2. If merge: fetches all individual commits in that merge
3. Returns commit messages and metadata
4. Implements retry logic for API failures
"""

import requests
import time
import json
import sys


def fetch_with_retry(url, max_attempts=3):
    """Fetch from GitHub API with retry logic"""
    for attempt in range(max_attempts):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                print(f'  Rate limit hit, waiting 60s...', file=sys.stderr)
                time.sleep(60)
            else:
                print(f'  HTTP {response.status_code}, retrying...', file=sys.stderr)
                time.sleep(2)
        except Exception as e:
            print(f'  Error: {e}, retrying...', file=sys.stderr)
            if attempt < max_attempts - 1:
                time.sleep(2)

    return None


def get_commit_info(repo, head_commit):
    """
    Get basic commit information including parent count.

    Returns:
        dict with 'message', 'parents', 'is_merge'
    """
    url = f'https://api.github.com/repos/{repo}/commits/{head_commit}'
    data = fetch_with_retry(url)

    if not data:
        return None

    return {
        'message': data['commit']['message'],
        'parents': data.get('parents', []),
        'is_merge': len(data.get('parents', [])) > 1,
        'sha': head_commit
    }


def get_merge_commits(repo, base_commit, head_commit):
    """
    Get all individual commits in a merge.

    Returns:
        list of dicts with 'sha' and 'message' for each commit
    """
    url = f'https://api.github.com/repos/{repo}/compare/{base_commit}...{head_commit}'
    data = fetch_with_retry(url)

    if not data:
        return None

    commits = data.get('commits', [])

    return [
        {
            'sha': c['sha'],
            'message': c['commit']['message'].split('\n')[0],  # First line only
            'full_message': c['commit']['message']
        }
        for c in commits
    ]


def analyze_commit(repo, base_commit, head_commit):
    """
    Complete commit analysis following CLAUDE.md methodology.

    Returns:
        dict with complete commit information
    """
    print(f'Analyzing {repo} {head_commit[:8]}...', file=sys.stderr)

    # Step 1: Check if merge
    head_info = get_commit_info(repo, head_commit)

    if not head_info:
        return {
            'error': 'Failed to fetch head commit info',
            'repo': repo,
            'head_commit': head_commit
        }

    result = {
        'repo': repo,
        'base_commit': base_commit,
        'head_commit': head_commit,
        'head_message': head_info['message'],
        'is_merge': head_info['is_merge'],
        'parent_count': len(head_info['parents'])
    }

    # Step 2: If merge, get all commits
    if head_info['is_merge']:
        print(f'  Merge commit detected, fetching individual commits...', file=sys.stderr)
        commits = get_merge_commits(repo, base_commit, head_commit)

        if not commits:
            result['error'] = 'Failed to fetch merge commits'
        else:
            result['total_commits'] = len(commits)
            result['commits'] = commits
            print(f'  Found {len(commits)} commits in merge', file=sys.stderr)
    else:
        result['total_commits'] = 1
        result['commits'] = [{
            'sha': head_commit,
            'message': head_info['message'].split('\n')[0],
            'full_message': head_info['message']
        }]

    return result


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print('Usage: python fetch_commit_info.py <repo> <base_commit> <head_commit>')
        print('Example: python fetch_commit_info.py sphinx-doc/sphinx 5ba344d6 2c98e909')
        sys.exit(1)

    repo = sys.argv[1]
    base_commit = sys.argv[2]
    head_commit = sys.argv[3]

    result = analyze_commit(repo, base_commit, head_commit)

    # Output as JSON
    print(json.dumps(result, indent=2))
