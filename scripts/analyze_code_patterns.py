"""
Analyze code patterns in patches to identify optimization types.

This script examines the actual code changes (patch) and identifies
semantic patterns that indicate performance optimizations.

Following CLAUDE.md methodology:
- Code analysis as PRIMARY (what does the code DO behaviorally)
- Commit messages as SECONDARY (hints, not truth)
- Focus on patterns, not specific implementations
"""

import sys
import json


def analyze_optimization_patterns(patch):
    """
    Analyze a patch for optimization patterns.

    Returns:
        dict with pattern indicators and evidence
    """
    lines = patch.split('\n')
    added = [l for l in lines if l.startswith('+') and not l.startswith('+++')]
    removed = [l for l in lines if l.startswith('-') and not l.startswith('---')]

    patterns = {
        'caching': False,
        'early_return': False,
        'library_optimization': False,
        'data_structure': False,
        'redundancy_removal': False,
        'identity_check': False,
        'lazy_evaluation': False,
        'configuration_normalization': False,
    }

    evidence = []

    # Pattern 1: Caching/Memoization
    # Look for: @lru_cache, @cacheit, _cache variables, lazy init patterns
    for line in added:
        code = line[1:].strip()
        if '@lru_cache' in code or '@cache' in code or '@cacheit' in code:
            patterns['caching'] = True
            evidence.append(f'Cache decorator: {code[:60]}')
        elif '_cache' in code and '=' in code:
            patterns['caching'] = True
            evidence.append(f'Cache variable: {code[:60]}')
        elif 'is None:' in code and any('_' in c and '=' in c for c in added):
            # Lazy initialization pattern: if _var is None: _var = ...
            patterns['lazy_evaluation'] = True
            evidence.append(f'Lazy init: {code[:60]}')

    # Pattern 2: Early Return
    # Look for: early returns that skip computation
    for i, line in enumerate(lines):
        if line.startswith('+') and 'return' in line:
            # Check if there's a condition before it
            if i > 0 and 'if' in lines[i-1]:
                patterns['early_return'] = True
                evidence.append(f'Early return: {line[1:60]}')
                break

    # Pattern 3: Library Function Optimization
    # Look for: scipy, numpy, numbagg functions replacing manual code
    lib_keywords = ['scipy.', 'np.', 'expit', 'numbagg', 'duck_array']
    for i, line in enumerate(added):
        if any(kw in line for kw in lib_keywords):
            # Check if it's replacing something
            if i > 0 and any(lines[j].startswith('-') for j in range(max(0, i-3), i)):
                patterns['library_optimization'] = True
                evidence.append(f'Library function: {line[1:60]}')
                break

    # Pattern 4: Identity Check Optimization
    # Look for: "is not None" replacing truthiness checks
    for i, line in enumerate(added):
        if 'is not None' in line or 'is None' in line:
            # Check if replacing different pattern
            if i > 0 and lines[i-1].startswith('-'):
                old = lines[i-1]
                if 'is not None' not in old and 'is None' not in old:
                    patterns['identity_check'] = True
                    evidence.append(f'Identity check: {line[1:60]}')
                    break

    # Pattern 5: Data Structure Change
    # Look for: list->set, dict->defaultdict, etc.
    for i, line in enumerate(added):
        if i > 0 and lines[i-1].startswith('-'):
            old_line = lines[i-1][1:].strip()
            new_line = line[1:].strip()

            # list -> set
            if 'list(' in old_line and 'set(' in new_line:
                patterns['data_structure'] = True
                evidence.append('Data structure: list -> set')
            # dict -> defaultdict
            elif 'dict(' in old_line and 'defaultdict' in new_line:
                patterns['data_structure'] = True
                evidence.append('Data structure: dict -> defaultdict')

    # Pattern 6: Redundancy Removal
    # Look for: more code removed than added (net reduction)
    if len(removed) > len(added) * 1.5 and len(removed) > 3:
        patterns['redundancy_removal'] = True
        evidence.append(f'Code removal: {len(removed)} removed, {len(added)} added')

    # Pattern 7: Configuration Normalization
    # Look for: bypassing environmental queries
    config_keywords = ['terminal', 'size', 'config', 'environ']
    for line in removed:
        if any(kw in line.lower() for kw in config_keywords):
            patterns['configuration_normalization'] = True
            evidence.append(f'Bypasses config: {line[1:60]}')
            break

    # Summary
    has_optimization = any(patterns.values())
    primary_pattern = None
    if has_optimization:
        # Identify primary pattern
        for pattern, detected in patterns.items():
            if detected:
                primary_pattern = pattern
                break

    return {
        'has_optimization': has_optimization,
        'patterns': patterns,
        'primary_pattern': primary_pattern,
        'evidence': evidence[:5],  # Top 5 pieces of evidence
        'stats': {
            'lines_added': len(added),
            'lines_removed': len(removed),
            'net_change': len(added) - len(removed)
        }
    }


def classify_from_commit_message(messages):
    """
    Use commit messages as SECONDARY hint for classification.

    Returns:
        dict with hints from commit messages
    """
    combined = ' '.join(messages).lower()

    hints = {
        'likely_exclude': False,
        'reason': None
    }

    # Indicators of non-optimization changes
    exclude_keywords = {
        'doc': 'Documentation',
        'test only': 'Test-only change',
        'format': 'Formatting',
        'type hint': 'Type annotations',
        'deprecat': 'Deprecation',
        'add feature': 'New feature',
        'compatibility': 'Compatibility fix',
        'fix bug': 'Bug fix'
    }

    for keyword, category in exclude_keywords.items():
        if keyword in combined:
            hints['likely_exclude'] = True
            hints['reason'] = category
            break

    # Indicators of optimization
    if any(kw in combined for kw in ['perf', 'optim', 'speed', 'fast', 'slow', 'cache']):
        hints['likely_exclude'] = False
        hints['reason'] = 'Performance mentioned'

    return hints


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python analyze_code_patterns.py <patch_file>')
        print('   or: echo "patch content" | python analyze_code_patterns.py -')
        sys.exit(1)

    if sys.argv[1] == '-':
        patch = sys.stdin.read()
    else:
        with open(sys.argv[1], 'r') as f:
            patch = f.read()

    result = analyze_optimization_patterns(patch)
    print(json.dumps(result, indent=2))
