# CLAUDE.md - Project Documentation

## Your Role

**You are an AI software engineer agent specialized in analyzing code performance and quality.**

Your task is to generate detailed rationales (explanations) for performance-improving code changes from real-world Python repositories.

### Rationale Generation Guidelines

When asked to generate a rationale about code changes:

1. **Be concise** - Get to the point without unnecessary elaboration
2. **Respond to each question in a clear separate way** - Use distinct sections for each aspect
3. **Format it in markdown** - Use proper headings, lists, and code blocks

### Analysis Approach

When analyzing code changes, use a **two-phase approach**:

#### Phase 1: Information Gathering (Use Scripts)
1. **Use scripts to collect data**:
   - Fetch commit message from GitHub API
   - **Check if commit is a merge/PR** (has multiple parents)
   - If merge: get ALL individual commits in that merge
   - Get the code patch/diff
   - Retrieve test patches if available
   - Extract performance metrics

2. **Scripts provide raw data**, not final analysis:
   - Scripts are for gathering, not classification
   - Automated pattern matching is unreliable
   - Semantic understanding requires human-like reasoning

3. **CRITICAL: Handling Merge/PR Commits**:
   - **Detect merges**: Check if `head_commit` has multiple parents
   - **Get individual commits**: Use GitHub API to retrieve all commits between `base_commit` and `head_commit`
   - **Analyze each commit separately**: Get message, files changed, and patch for each
   - **Combine analysis**: Make final decision based on ALL commits, not just the merge message
   - **If GitHub API fails**: Retry the request - commit information is essential
   - **Never make snap judgments** on large merges - they may contain hidden optimizations

#### Phase 2: Manual Semantic Analysis (You Do This)

1. **Read and understand the actual code changes**:
   - What computation existed before?
   - What computation exists after?
   - What work is now avoided or made more efficient?

2. **Identify the semantic pattern**:
   - **CACHING/MEMOIZATION**: Compute once, store, reuse (e.g., lazy dict initialization, @lru_cache)
   - **LIBRARY FUNCTION OPTIMIZATION**: Manual implementation → optimized library function (e.g., `1/(1+exp(-x))` → `expit(x)`)
   - **DATA STRUCTURE CHANGE**: Different container for better performance (e.g., `list` → `set` for membership tests)
   - **CONFIGURATION NORMALIZATION**: Remove environmental dependencies (e.g., bypass terminal size queries)
   - **EARLY TERMINATION**: Add early returns to skip unnecessary work
   - **REDUNDANCY REMOVAL**: Remove duplicate or unnecessary computations
   - **ALGORITHM CHANGE**: Different algorithmic approach with better complexity

3. **Don't rely on keywords or variable names**:
   - A variable named `_cache` might not be caching
   - A change adding `dict()` might be caching, not a data structure change
   - Focus on **behavior change**, not syntax

4. **Use commit messages as hints, not truth**:
   - **For single commits**: Use message as context, verify with code
   - **For merge commits**: Analyze ALL individual commit messages
   - If commit message is vague → fully rely on code analysis
   - If commit message is clear → verify it matches code changes
   - Commit messages can be misleading ("Reformated Files" might hide real optimizations)
   - Merge messages are often useless ("Merge branch 'x'") - look at individual commits instead

5. **Consider the performance impact**:
   - Does the magnitude of improvement match the pattern?
   - Large improvements (>0.1) suggest fundamental changes (caching, algorithm)
   - Small improvements (<0.01) suggest micro-optimizations (library functions, redundancy removal)

#### Example: Correct Analysis Process

```
Sample: sympy__sympy-26004
Commit: "_invert_trig_hyp: cache dicts with data on inverses"

BEFORE code pattern:
- Dictionary with trig function mappings rebuilt every function call (implied)

AFTER code pattern:
+_trig_inverses = None                    # Module-level variable
+if _trig_inverses is None:              # Check if built
+    _trig_inverses = { ... }             # Build once
+return _trig_inverses[func]              # Reuse

Semantic Understanding:
- Expensive dictionary construction moved from "every call" to "first call only"
- Subsequent calls reuse the cached dictionary
- Pattern: Lazy initialization + memoization

Classification: CACHING/MEMOIZATION
Performance: 0.3726 (significant, matches caching benefit)
```

#### What NOT to Do

❌ **Don't use keyword matching** (e.g., "if 'cache' in code → CACHING")
❌ **Don't assume variable names indicate pattern** (e.g., `_inv` doesn't mean caching)
❌ **Don't trust commit messages blindly** (they can be vague or misleading)
❌ **Don't automate the classification** (requires semantic understanding)

✅ **Do manual semantic analysis**
✅ **Do understand the behavioral change**
✅ **Do verify classification matches performance impact**
✅ **Do use scripts only for data gathering**

---

## Handling Merge/PR Commits

**CRITICAL REQUIREMENT**: When analyzing a sample, always check if the `head_commit` is a merge commit. Merge commits bundle multiple changes and require special handling.

### How to Detect a Merge Commit

Use GitHub API to check the number of parents:

```python
GET https://api.github.com/repos/{repo}/commits/{head_commit}

# Response includes:
{
  "parents": [
    {"sha": "abc123..."},
    {"sha": "def456..."}
  ]
}

# If len(parents) > 1 → This is a MERGE COMMIT
```

### Analysis Process for Merge Commits

When you detect a merge commit, follow this process:

#### Step 1: Get All Individual Commits

```python
GET https://api.github.com/repos/{repo}/compare/{base_commit}...{head_commit}

# Returns:
{
  "commits": [
    {
      "sha": "commit1",
      "commit": {
        "message": "Fix performance issue",
        "author": {...}
      }
    },
    # ... more commits
  ]
}
```

#### Step 2: Analyze Each Commit

For each commit in the merge:
1. Read the commit message
2. Get the specific code changes for that commit
3. Identify if it contains optimizations
4. Note the pattern type (caching, early return, etc.)

```python
# For each commit SHA:
GET https://api.github.com/repos/{repo}/commits/{sha}

# Returns:
{
  "commit": {
    "message": "fix #8522: avoid __bool__ calls"
  },
  "files": [
    {
      "filename": "path/to/file.py",
      "patch": "@@ -10,1 +10,1 @@\n-old code\n+new code"
    }
  ]
}
```

#### Step 3: Combined Analysis

After analyzing all commits:
- **If ANY commit contains an optimization** → Classify as KEEP
- **Document which specific commit(s)** contain the optimization
- **Use combined understanding** from all commit messages
- **Consider the overall context** - why were these changes bundled?

### Example: Merge Commit Analysis

```
Sample: sphinx-doc__sphinx-8537

HEAD COMMIT: 2c98e909
Message: "Merge branch '3.x'"  ← VAGUE, USELESS
Parents: 2  ← IT'S A MERGE!

Step 1: Get all commits
→ Found 96 commits in this merge

Step 2: Scan commit messages
- "fix_8522" ← Interesting, check this
- "Fix pycode becomes slow" ← Performance mention
- "Add napoleon_google_attr_annotations" ← Feature
- "Deprecate Documenter.get_object_members()" ← API change
- ... 91 more commits

Step 3: Analyze optimization commits
Commit 6fdbce93 - "fix_8522":
  - if safe_getattr(member, '__sphinx_mock__', False):
  + if safe_getattr(member, '__sphinx_mock__', None) is not None:

  Analysis: Avoids implicit __bool__() call - OPTIMIZATION!
  Pattern: Avoid implicit method calls
  Impact: 0.709746 (71% improvement)

DECISION: KEEP
Reason: Contains genuine optimization in commit 6fdbce93
Attribution: Part of merge 2c98e909, optimization in 6fdbce93
```

### Common Pitfalls to Avoid

❌ **Don't judge by merge message alone**
- "Merge branch X" tells you nothing
- "Merge pull request #123" is equally useless

❌ **Don't judge by total patch size**
- A 2000-line merge might have a 1-line optimization
- Size indicates scope, not optimization quality

❌ **Don't assume "bundled" means "no optimization"**
- Real-world PRs mix features, fixes, and optimizations
- Each commit should be evaluated independently

✅ **Do analyze individual commits**
- Each commit has its own message and purpose
- Optimizations can be buried among other changes

✅ **Do retry failed API calls**
- GitHub API can fail - retry before making decisions
- Commit information is essential, not optional

✅ **Do document your findings**
- Note which specific commit(s) contain optimizations
- Reference commit SHAs for traceability

### API Call Pattern for Merges

```python
def analyze_sample(base_commit, head_commit, repo):
    # 1. Check if merge
    head_data = fetch_commit(repo, head_commit)
    is_merge = len(head_data['parents']) > 1

    if not is_merge:
        # Single commit - straightforward analysis
        return analyze_single_commit(head_commit)

    # 2. Get all commits in merge
    compare_data = fetch_compare(repo, base_commit, head_commit)
    commits = compare_data['commits']

    print(f"Analyzing merge with {len(commits)} commits...")

    # 3. Analyze each commit
    optimizations_found = []

    for commit in commits:
        sha = commit['sha']
        message = commit['commit']['message']

        # Get detailed patch
        commit_detail = fetch_commit(repo, sha)

        # Check for optimization patterns
        if contains_optimization(commit_detail):
            optimizations_found.append({
                'sha': sha,
                'message': message,
                'pattern': identify_pattern(commit_detail),
                'files': commit_detail['files']
            })

    # 4. Make decision based on all commits
    if optimizations_found:
        return {
            'decision': 'KEEP',
            'type': 'merge',
            'total_commits': len(commits),
            'optimizations': optimizations_found,
            'head_commit': head_commit
        }
    else:
        return {
            'decision': 'EXCLUDE',
            'reason': f'Analyzed {len(commits)} commits, no optimizations found'
        }
```

### When API Calls Fail

**If GitHub API returns an error**:
1. **Wait and retry** (rate limits, network issues)
2. **Try up to 3 times** with delays between attempts
3. **Never proceed without commit information**

```python
def fetch_with_retry(url, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                # Rate limit - wait longer
                time.sleep(60)
            else:
                time.sleep(2)
        except Exception as e:
            if attempt < max_attempts - 1:
                time.sleep(2)
            else:
                raise

    raise Exception(f"Failed to fetch {url} after {max_attempts} attempts")
```

---

## Project Overview

This is a **Rationale Generation for Performance-Improving Code Changes** project based on the **SWE-Perf dataset**. The goal is to use LLMs (Large Language Models) to automatically generate explanations for performance optimizations in real-world Python code.

**Course**: AV&V (Analysis, Verification & Validation) - A.Y. 25-26
**Institution**: Università dell'Aquila
**Reference**: See `docs/AVV26_rationale-generation.pdf` for full project description

---

## Dataset: SWE-Perf

### Location
`data/dataset.csv` (5.9MB, 140 instances)

### Dataset Overview
- **140 curated performance-improving code changes** from 9 popular Python repositories
- **Date range**: 2014-2026 (over 10 years of real-world optimizations)
- **Repositories**: pydata/xarray (54), scikit-learn (32), sympy (20), astropy (12), sphinx (8), seaborn (6), matplotlib (3), pylint (3), requests (2)

### Column Descriptions

| Column | Type | Description |
|--------|------|-------------|
| `repo` | string | GitHub repository (e.g., "astropy/astropy") |
| `instance_id` | string | Unique identifier (e.g., "astropy__astropy-16065") |
| `patch` | string | Git unified diff showing the code changes |
| `test_patch` | string | Git diff for test changes (85% have this) |
| `base_commit` | string | SHA of commit before the change |
| `head_commit` | string | SHA of commit with the optimization |
| `created_at` | int64 | Unix timestamp (milliseconds) of commit |
| `version` | string | Repository version/release |
| `duration_changes` | string | JSON array of performance measurements (base vs head) |
| `efficiency_test` | string | List of test cases used for performance measurement |
| `patch_functions` | string | JSON mapping files to modified function names |
| `test_functions` | string | JSON mapping files to test function names |
| `problem_statement_oracle` | string | Ideal problem statement (references actual changed functions) |
| `problem_statement_realistic` | string | Realistic problem statement (references test functions) |
| `human_performance` | float | Performance improvement metric (lower is better) |

---

## Accessing Additional Information from GitHub

### Commit Messages

**Method 1: GitHub API (JSON)**
```python
import requests

def fetch_commit_message(repo, commit_hash):
    url = f"https://api.github.com/repos/{repo}/commits/{commit_hash}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()['commit']['message']
    return None

# Example
row = df.iloc[0]
commit_msg = fetch_commit_message(row['repo'], row['head_commit'])
# Returns: "BUG: make report_diff_values returns consistent (ignoring terminal size)"
```

**Method 2: WebFetch Tool (if available)**
```python
# Use Claude's WebFetch tool
url = f"https://api.github.com/repos/{repo}/commits/{commit_hash}"
# Prompt: "Extract the commit message from this GitHub API response"
```

### Full Commit Diff

The dataset contains the unified diff in the `patch` column, but you can fetch the **full commit with metadata** from GitHub:

```python
def fetch_commit_diff(repo, commit_hash):
    """Fetch full commit diff including metadata"""
    url = f"https://github.com/{repo}/commit/{commit_hash}.patch"
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    return None
```

**What you get from GitHub that's NOT in the dataset:**
- Author name and email
- Commit date and time
- Full commit message (dataset only has commit hash)
- File statistics (lines added/removed)
- Complete diff headers

**Example Output:**
```
From 7eac388cd073eb50f44afac72ae90c244bb390c2 Mon Sep 17 00:00:00 2001
From: Clément Robert <cr52@protonmail.com>
Date: Mon, 19 Feb 2024 11:22:43 +0100
Subject: [PATCH] BUG: make report_diff_values returns consistent (ignoring terminal size)

---
 astropy/utils/diff.py               | 12 ++++++++++++
 docs/changes/utils/16065.bugfix.rst |  2 ++
 2 files changed, 14 insertions(+)

[... full diff follows ...]
```

**Note**: Dataset patch (1,039 chars) is a SUBSET of GitHub diff (1,498 chars). GitHub adds metadata headers.

---

## Rationale Generation Task

### Objective

Generate detailed explanations for each performance-improving code change covering:

1. **Intent**: What problem does the change solve?
2. **Motivation**: Why was this particular optimization chosen?
3. **Risk Assessment**: Are the codes functionally equivalent? Any side effects?
4. **Change Type**: Algorithm optimization, data structure, caching, early termination, etc.

### Example Prompt Template (from PDF)

```
You are an AI software engineer.
Below is a GitHub diff that claims to improve performance.

<code change from 'patch' column>

Questions to answer:
- What problem does it solve? (Intent)
- Why was this particular optimization chosen? (Motivation)
- Are the code functionally equivalent? Are there side effects? (Risk assessment)
- Which type of code change is this? (Algo, data structure, synchronization)

Reply with ... format including the following fields ...
Be clear and concise. Do not include ....
```

### Evaluation Criteria (Step 2)

After generating rationales, evaluate:
- What types of performance-improving changes are in the dataset?
- How accurate is the explanation?
- Is it correct?
- Is it comprehensive?
- Is it coherent with the commit message?

---

## Available Scripts

### `scripts/utils.py`
Utility functions for loading data:
- `load_from_csv(path)` - Load dataset from CSV
- `load_from_hf(name, split)` - Load from HuggingFace

### `scripts/analyze_dataset.py`
Basic dataset statistics (run: `python scripts/analyze_dataset.py`)

### `scripts/dataset_summary.py`
Comprehensive summary with repository breakdown, performance distribution, etc.

### `scripts/analyze_first_sample.py`
Detailed analysis of the first dataset instance with all available fields

### `scripts/fetch_commit_message.py`
Example of fetching commit message from GitHub API

### `scripts/fetch_commit_diff.py`
Compare dataset patch with full GitHub commit diff

### `scripts/show_sample_patches.py`
Interactive script to browse through sample patches

---

## Python Environment

### Virtual Environment
Location: `.venv/`

### Activation
```bash
source .venv/Scripts/activate  # On Windows with Git Bash
.venv\Scripts\activate         # On Windows CMD
```

### Dependencies
See `requirements.txt`:
- pandas (3.0.1)
- datasets (4.7.0) - HuggingFace datasets
- jupyter (1.1.1)
- notebook (7.5.5)
- ipykernel (7.2.0)

### Installation
```bash
.venv/Scripts/pip install -r requirements.txt
```

---

## Jupyter Notebook

### Location
`notebook.ipynb` - Basic notebook that loads and displays the dataset

### Running
```bash
.venv/Scripts/jupyter notebook
```

---

## Key Statistics

### Performance Improvements
- **Mean**: 0.1085 (median: 0.0095)
- **Best**: 0.000037 (extremely fast optimization)
- **Largest**: 0.878 (significant performance gain)
- **Distribution**:
  - <0.01 (very fast): 70 instances (50%)
  - 0.01-0.1: 34 instances
  - 0.1-0.5: 28 instances
  - ≥0.5: 8 instances

### Code Changes
- **Average patch size**: ~10,000 characters (median: 4,000)
- **Average lines changed**: 261 (median: 103)
- **Functions modified**: Average 7.6 per instance
- **Test coverage**: 85% have test patches

### Top Performers
All top 10 best optimizations are from **pydata/xarray**, suggesting many micro-optimizations in array processing!

---

## Working with the Data

### Load Dataset
```python
import pandas as pd

df = pd.read_csv('./data/dataset.csv')
row = df.iloc[0]  # First instance

print(f"Instance: {row['instance_id']}")
print(f"Repository: {row['repo']}")
print(f"Performance: {row['human_performance']:.6f}")
print("\nPatch:\n", row['patch'])
```

### Parse JSON Fields
```python
import json

# Patch functions
patch_funcs = json.loads(row['patch_functions'].replace("'", '"'))
# Returns: {"astropy/utils/diff.py": ["report_diff_values"]}

# Efficiency tests
eff_tests = json.loads(row['efficiency_test'].replace("'", '"'))
# Returns: ['test_distribution[False-True-log]', 'test_kwarg_default[7-1]']
```

### Access Performance Metrics
```python
import json

duration_changes = json.loads(row['duration_changes'])
# List of dicts with 'base' and 'head' timing measurements

# Example: Get average speedup
for run in duration_changes:
    for test_name, timings in run.items():
        base_time = timings['base']
        head_time = timings['head']
        speedup = (base_time - head_time) / base_time * 100
        print(f"{test_name}: {speedup:.2f}% faster")
```

---

## Best Practices for Rationale Generation

### 1. Always Fetch Commit Message
The commit message provides crucial context about whether a change is a bug fix, optimization, refactoring, etc.

### 2. Analyze the Test Patch
The test patch often reveals the specific scenario being optimized (e.g., "test_large_table_diff" shows it's about 100+ column tables).

### 3. Check Performance Metrics
Look at `duration_changes` to see if the optimization is:
- Consistent across runs
- Affecting all tests or just some
- A micro-optimization or significant speedup

### 4. Categorize the Optimization Type
Common patterns found in this dataset:
- **Caching/Memoization**: Store computed values
- **Early termination**: Exit loops/functions sooner
- **Algorithm change**: Better complexity (O(n²) → O(n))
- **Data structure**: Use more efficient containers
- **Configuration normalization**: Remove environmental dependencies
- **Lazy evaluation**: Defer expensive operations

### 5. Consider the Context
- Is this a library or application code?
- What domain is it? (astronomy, ML, symbolic math)
- Are there trade-offs? (memory vs speed, readability vs performance)

---

## Example: Complete Analysis Workflow

```python
import pandas as pd
import requests
import json

def analyze_instance(idx):
    """Complete analysis of a single instance"""
    df = pd.read_csv('./data/dataset.csv')
    row = df.iloc[idx]

    # 1. Basic info
    print(f"Instance: {row['instance_id']}")
    print(f"Repository: {row['repo']}")

    # 2. Fetch commit message
    url = f"https://api.github.com/repos/{row['repo']}/commits/{row['head_commit']}"
    response = requests.get(url)
    commit_msg = response.json()['commit']['message']
    print(f"Commit Message: {commit_msg}")

    # 3. Show patch
    print(f"\nPatch:\n{row['patch']}")

    # 4. Performance metrics
    print(f"\nPerformance Improvement: {row['human_performance']:.6f}")

    # 5. Modified functions
    patch_funcs = json.loads(row['patch_functions'].replace("'", '"'))
    print(f"Modified Functions: {patch_funcs}")

    # 6. Generate rationale (your task!)
    rationale = generate_rationale(row, commit_msg)

    return rationale

# Usage
rationale = analyze_instance(0)
```

---

## GitHub API Rate Limits

**Important**: GitHub API has rate limits:
- **Unauthenticated**: 60 requests/hour
- **Authenticated**: 5,000 requests/hour

For 140 instances, you'll need ~280 requests (commit message + diff for each). Consider:
1. **Caching results** after first fetch
2. **Using authenticated requests** (set up GitHub token)
3. **Adding delays** between requests

### Authenticated Requests
```python
import os
headers = {'Authorization': f'token {os.environ.get("GITHUB_TOKEN")}'}
response = requests.get(url, headers=headers)
```

---

## Next Steps

1. ✅ Environment setup complete
2. ✅ Dataset analyzed
3. ✅ GitHub data access confirmed
4. 🔄 **Current**: Generate rationales for all 140 instances
5. ⏳ **Future**: Evaluate rationale quality
6. ⏳ **Future**: Categorize optimization types

---

## Reference Papers

See `docs/` folder:
1. **SWE-Perf**: Dataset paper on code performance optimization
2. **NExT**: Teaching LLMs to reason about code execution
3. **Learning Performance Improvements**: ICLR 2024 paper
4. **AVV26 Rationale Generation**: Project description (this work!)

---

## Notes

- All scripts assume you're running from the project root directory
- The dataset is large (~6MB) but manageable in memory
- Performance metrics are in seconds (float)
- Git hashes are the full 40-character SHA-1 hashes
- Some instances lack test patches (15%) - handle gracefully

---

Last Updated: 2026-03-14
