# Rationale Generation for Performance-Improving Code Changes

Course project for **AV&V (Analysis, Verification & Validation), A.Y. 25-26 — Università dell'Aquila**, built on the **SWE-Perf** dataset of 140 real-world performance-improving commits from nine popular Python libraries (`pydata/xarray`, `scikit-learn`, `sympy`, and others). Each instance pairs a Git diff with repeated timing measurements.

The goal is to instruct a large language model (Anthropic's **Claude**) to generate a detailed, evidence-based analysis explaining *why* a given code change improves performance.

## Pipeline

The rationale generation pipeline is defined entirely in the project's [`.claude/CLAUDE.md`](.claude/CLAUDE.md) file, which the agent loads automatically at startup. It accepts two types of input:

- **Dataset reference** — an index or instance ID from the SWE-Perf CSV. All five steps are executed.
- **GitHub commit reference** — a repository name and commit hash (or URL). Step 1 is skipped and the pipeline begins at step 2, using the commit as the sole entry point.

No step may be silently skipped: if a step fails, the agent documents the failure and continues with the remaining steps.

1. **Load dataset fields** *(dataset input only)* — Load the target instance from the dataset CSV and extract all available fields: repository, patch, test patch, problem statements, efficiency tests, timing data, and commit hashes. The `duration_changes` field (a JSON array of repeated base/head timing measurements) is parsed and per-run speedups are computed for every test case.

2. **Fetch commit information** — Using the GitHub API, retrieve the commit associated with the change and check whether it is a merge commit (multiple parents). If so, all individual commits bundled in the merge are retrieved and analysed separately, since merge messages are typically uninformative and the relevant optimisation may be buried in one of many commits.

3. **Analyse code patterns** — Pass the patch to a static pattern analyser (`scripts/analyze_code_patterns.py`) that classifies the change into a known pattern: caching/memoisation, library function substitution, data structure change, early termination, redundancy removal, or algorithm change. This output is a starting point only — not the final classification.

4. **Fetch GitHub context** — Retrieve the full source file(s) modified by the patch, plus any related issues or pull request discussions referenced in the commit message. This provides surrounding context absent from the diff alone and helps establish the motivation behind the change.

5. **Semantic analysis** — With all data gathered, reason explicitly about what computation existed before and after the change, what work is eliminated or made more efficient, and whether the performance improvement was the primary intent or an incidental side effect. The change is classified as one of: **targeted optimization**, **side effect of bug fix**, **ambiguous**, or **not a performance change**.

The output is written in a fixed, section-by-section format covering the problem solved, the classification, the rationale for the chosen optimisation, behavioural side effects, a statistical summary of the benchmark data, and a code quality assessment. Two rules are mandatory: every performance figure must be traceable to a concrete source (typically the `duration_changes` field), and the rationale must never reference the dataset as a whole (e.g. relative rankings across instances).

The user can customise the output via the initial prompt (e.g. changing the output structure or how the classification is done) but cannot alter the core pipeline logic — skipping steps or ignoring gathered data — since these steps build the context needed to fully capture the consequences of a change.
