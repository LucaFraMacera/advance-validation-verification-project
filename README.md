# Analysis Pipeline Scripts

This directory contains the complete pipeline for analyzing and filtering the SWE-Perf dataset.

## Pipeline Overview

```
dataset.csv
    ↓
[1] fetch_commit_info.py → commit_info.json
    ↓
[2] analyze_code_patterns.py → code_analysis.json
    ↓
[3] classify_sample.py → classification.json
    ↓
[4] filter_dataset.py → dataset_filtered_v2.csv
```

## Scripts

### 1. `fetch_commit_info.py`

**Purpose**: Fetch commit information from GitHub API

**Features**:
- Detects if commit is a merge (multiple parents)
- Retrieves all individual commits in a merge
- Implements retry logic for API failures
- Returns commit messages and metadata

**Usage**:
```bash
python fetch_commit_info.py <repo> <base_commit> <head_commit>

# Example:
python fetch_commit_info.py sphinx-doc/sphinx 5ba344d6 2c98e909
```

**Output**: JSON with commit information
```json
{
  "repo": "sphinx-doc/sphinx",
  "is_merge": true,
  "total_commits": 96,
  "commits": [
    {
      "sha": "...",
      "message": "..."
    }
  ]
}
```

### 2. `analyze_code_patterns.py`

**Purpose**: Analyze code patches for optimization patterns

**Patterns Detected**:
- Caching/memoization (`@lru_cache`, `@cacheit`, cache variables)
- Early returns (skip computation)
- Library function optimization (scipy, numpy, numbagg)
- Data structure changes (list→set, dict→defaultdict)
- Redundancy removal (net code reduction)
- Identity checks (`is not None` vs truthiness)
- Lazy evaluation (conditional initialization)
- Configuration normalization (bypass environmental queries)

**Usage**:
```bash
python analyze_code_patterns.py <patch_file>
cat patch.diff | python analyze_code_patterns.py -

# Example with sample from dataset:
python -c "import pandas as pd; print(pd.read_csv('data/dataset.csv').iloc[0]['patch'])" | python analyze_code_patterns.py -
```

**Output**: JSON with pattern analysis
```json
{
  "has_optimization": true,
  "primary_pattern": "caching",
  "patterns": {
    "caching": true,
    "early_return": false,
    ...
  },
  "evidence": ["Cache variable: _cache = {}"],
  "stats": {
    "lines_added": 10,
    "lines_removed": 5,
    "net_change": 5
  }
}
```

### 3. `classify_sample.py`

**Purpose**: Make KEEP/EXCLUDE/UNCLEAR decision

**Decision Logic**:
1. **PRIMARY**: Code analysis - does code show optimization pattern?
2. **SECONDARY**: Commit messages - hints for non-optimization changes

**Classification**:
- **KEEP**: Code demonstrates performance optimization
- **EXCLUDE**: Feature, bug fix, documentation, compatibility
- **UNCLEAR**: Ambiguous or insufficient information

**Usage**:
```bash
python classify_sample.py <commit_info.json> <code_analysis.json> <performance>

# Example:
python classify_sample.py commit.json analysis.json 0.0045
```

**Output**: JSON with decision
```json
{
  "decision": "KEEP",
  "reason": "Caching/memoization - Cache variable: _cache = {}",
  "performance": 0.0045,
  "is_merge": false,
  "commits_analyzed": 1
}
```

### 4. `analyze_single_sample.py`

**Purpose**: End-to-end analysis orchestrator

**What it does**:
1. Loads sample from dataset.csv
2. Fetches commit info from GitHub
3. Analyzes code patterns
4. Makes classification decision
5. Displays complete analysis
6. Optionally saves to decisions file

**Usage**:
```bash
python analyze_single_sample.py <sample_index>

# Example:
python analyze_single_sample.py 119
```

**Output**: Complete analysis printed to console + optional CSV append

### 5. `filter_dataset.py`

**Purpose**: Create final filtered dataset

**What it does**:
1. Reads filtering decisions from `filtering_v2.csv`
2. Filters original dataset to KEEP samples only
3. Creates `dataset_filtered_v2.csv` with same columns as original

**Usage**:
```bash
python filter_dataset.py [decisions_file] [output_file]

# Default:
python filter_dataset.py

# Custom files:
python filter_dataset.py my_decisions.csv my_filtered_dataset.csv
```

**Output**: Filtered dataset CSV + statistics

### 6. `utils.py`

**Purpose**: Utility functions for loading data

**Functions**:
- `load_from_csv(path)` - Load dataset from CSV
- `load_from_hf(name, split)` - Load from HuggingFace

## Complete Workflow Example

```bash
# 1. Analyze a single sample (e.g., sample 119 - the famous merge case)
python analyze_single_sample.py 119

# 2. Batch analyze multiple samples (manual loop or script)
for i in {0..139}; do
    python analyze_single_sample.py $i >> analysis_log.txt
done

# 3. After all samples analyzed, create filtered dataset
python filter_dataset.py

# Result: dataset_filtered_v2.csv with 79 KEEP samples
```

## Methodology (from CLAUDE.md)

### Key Principles

1. **Code Analysis as PRIMARY**
   - Examine actual behavioral changes in code
   - Identify semantic patterns, not syntax
   - Focus on what the code DOES, not what it's called

2. **Commit Messages as SECONDARY**
   - Use as hints, not definitive classification
   - Messages can be vague or misleading
   - Verify claims against code changes

3. **Merge Commit Handling**
   - Detect merges by checking parent count
   - Analyze ALL individual commits in merge
   - Don't make snap judgments on merge message alone

4. **Pattern Focus**
   - Look for optimization patterns (caching, early returns, etc.)
   - Not specific implementations
   - Generic behavioral improvements

### Decision Criteria

**KEEP** if code change:
- Introduces caching/memoization
- Adds early termination to skip work
- Improves algorithmic complexity
- Uses optimized library functions
- Changes data structures for performance
- Removes redundant operations
- Normalizes configuration to avoid queries

**EXCLUDE** if code change:
- Adds new features
- Fixes bugs (without optimization)
- Adds error handling/validation
- Updates documentation
- Adds type annotations
- Refactors without performance intent

## Files Generated

- `filtering_v2.csv` - All filtering decisions (index, instance_id, decision, reason, performance)
- `dataset_filtered_v2.csv` - Filtered dataset with KEEP samples only (same columns as original)
- `FILTERING_V2_SUMMARY.md` - Analysis summary and statistics

## Dependencies

```bash
pip install pandas requests
```

For GitHub API (optional but recommended):
- Set `GITHUB_TOKEN` environment variable for higher rate limits
- Unauthenticated: 60 requests/hour
- Authenticated: 5,000 requests/hour

## Notes

- Scripts assume running from project root directory
- GitHub API retry logic handles rate limits automatically
- All scripts output JSON for easy parsing/chaining
- Semantic analysis requires human judgment - scripts provide data, not final decisions
