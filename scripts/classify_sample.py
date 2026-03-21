"""
Classify a sample as KEEP/EXCLUDE/UNCLEAR.

Combines:
1. Commit information (from fetch_commit_info.py)
2. Code pattern analysis (from analyze_code_patterns.py)
3. Performance metrics

Makes final classification decision following CLAUDE.md methodology.
"""

import json
import sys


def classify_sample(commit_info, code_analysis, performance):
    """
    Make final KEEP/EXCLUDE/UNCLEAR decision.

    Args:
        commit_info: dict from fetch_commit_info.py
        code_analysis: dict from analyze_code_patterns.py
        performance: float (human_performance metric)

    Returns:
        dict with decision, reason, and metadata
    """
    # PRIMARY: Code analysis
    has_optimization = code_analysis.get('has_optimization', False)
    primary_pattern = code_analysis.get('primary_pattern')
    evidence = code_analysis.get('evidence', [])

    # SECONDARY: Commit messages
    all_messages = [c['message'] for c in commit_info.get('commits', [])]
    combined_messages = ' '.join(all_messages).lower()

    # Decision logic
    if has_optimization:
        # Code shows optimization pattern - KEEP
        decision = 'KEEP'

        # Generate reason from pattern
        pattern_descriptions = {
            'caching': 'Caching/memoization',
            'early_return': 'Early return to skip computation',
            'library_optimization': 'Uses optimized library function',
            'data_structure': 'Data structure change for efficiency',
            'redundancy_removal': 'Removes redundant operations',
            'identity_check': 'Identity check optimization',
            'lazy_evaluation': 'Lazy evaluation/initialization',
            'configuration_normalization': 'Configuration normalization'
        }

        reason = pattern_descriptions.get(primary_pattern, 'Code optimization')

        # Add specifics from evidence if available
        if evidence:
            reason = f"{reason} - {evidence[0]}"

    else:
        # No optimization pattern detected in code
        # Check commit messages for hints

        exclude_indicators = [
            ('doc', 'Documentation'),
            ('test', 'Test-only change'),
            ('format', 'Formatting'),
            ('type hint', 'Type annotations'),
            ('deprecat', 'Deprecation'),
            ('compatibility', 'Compatibility fix'),
            ('feature', 'New feature'),
            ('error', 'Error handling'),
            ('validation', 'Validation')
        ]

        decision = None
        reason = None

        for keyword, category in exclude_indicators:
            if keyword in combined_messages:
                decision = 'EXCLUDE'
                reason = category
                break

        if not decision:
            # No clear pattern and no obvious non-optimization indicators
            decision = 'UNCLEAR'
            reason = 'No clear optimization pattern detected'

    return {
        'decision': decision,
        'reason': reason,
        'performance': performance,
        'is_merge': commit_info.get('is_merge', False),
        'commits_analyzed': commit_info.get('total_commits', 1),
        'primary_pattern': primary_pattern,
        'evidence': evidence[:3]
    }


def main():
    if len(sys.argv) != 4:
        print('Usage: python classify_sample.py <commit_info.json> <code_analysis.json> <performance>')
        print('Example: python classify_sample.py commit.json analysis.json 0.0045')
        sys.exit(1)

    # Load commit info
    with open(sys.argv[1], 'r') as f:
        commit_info = json.load(f)

    # Load code analysis
    with open(sys.argv[2], 'r') as f:
        code_analysis = json.load(f)

    # Parse performance
    performance = float(sys.argv[3])

    # Classify
    result = classify_sample(commit_info, code_analysis, performance)

    # Output
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
