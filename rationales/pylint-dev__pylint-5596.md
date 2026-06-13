# Rationale Analysis: pylint-dev__pylint-5596

**Repository**: pylint-dev/pylint
**Instance ID**: pylint-dev__pylint-5596
**Performance Improvement**: 0.7809 (mean speedup ~78% across 37 tests, 20 runs each)
**Commit**: 7f84caf238c17df33c95fd706617a473bfa347da
**Type**: Single commit
**Classification**: Targeted optimization

---

## Pipeline Analysis Summary

- **Commit message**: "Loop on the message states only once"
- **Merge**: No (1 parent, single commit by Pierre Sassoulas, 2021-12-27)
- **Pattern analyzer output**: "configuration_normalization" (surface label; actual pattern is redundancy removal — the config sync loop ran O(N) times instead of once per `_set_msg_status` invocation)
- **Related issues**: PR #5596 "Refactor message disabling and enabling" (closes issue #5587 "Optimizing speed of the message store during starting and initialisation phase")
- **Problem statement (oracle)**: Accelerate `PyLinter._set_msg_status`, `PyLinter._set_one_msg_status`, `PyLinter._register_by_id_managed_msg` in `pylint/lint/pylinter.py`
- **Problem statement (realistic)**: Accelerate `LintModuleTest.runTest`, `Run`, `LintModuleOutputUpdate`, `TextWriter.write` (test-facing entry points)
- **Benchmark data summary** (source: `duration_changes` field, 20 runs per test, 37 tests total):

  The benchmark data separates into three groups. The dominant group — 34 of 37 tests — shows highly consistent speedups in the 77–94% range (e.g., `test_functional[deprecated_module_py4]`: mean 89.97% ± 0.71%, `test_functional[old_division_floats]`: mean 93.50% ± 0.75%, `test_fail_under`: mean 80.38% ± 1.66%). These are all end-to-end pylint invocations that trigger `--disable`/`--enable` processing at startup; the tight standard deviations confirm the gain is structurally stable, not noise. A second group of two tests (`test_fail_on[-10-C-fail_under_plus7_5.py-16]`: mean 26.06% ± 5.02%; `test_wrong_import_position_when_others_disabled`: mean 31.69% ± 5.30%) shows smaller but still substantial gains with higher variance, likely because those test configurations disable only a category rather than all messages, so the quadratic cost is smaller in absolute terms. A third test (`test_functional[import_error]`: mean 17.71% ± 5.10%) shows the most modest improvement and the highest variance, consistent with a test that processes a file with few disabled messages, reducing the number of redundant config syncs.

---

## What Problem Does It Solve?

During pylint startup, `_set_msg_status` is called for every entry in `--disable` or `--enable`. When processing a broad specifier like `--disable=all` or `--disable=C`, it resolves to hundreds of individual messages. In the original code, every call to `_set_one_msg_status` that updated the package-scope state would immediately rebuild `self.config.enable` and `self.config.disable` — two full list comprehensions over all of `_msgs_state` — making the cost O(N²) in the number of messages. As noted in PR #5596: "The problem was that we synced the `config` object after every message, instead of doing so after all messages have been set." The profiler comparison in the PR shows `_config_initialization` dropping from 0.372 s to 0.026 s with `--disable=all`.

## Classification: Targeted Optimization or Side Effect?

**Targeted optimization.** The commit message explicitly states the mechanism ("Loop on the message states only once"), the PR is labelled as a Refactoring submitted in direct response to issue #5587 ("Optimizing speed of the message store during starting and initialisation phase"), and the PR description includes profiler output demonstrating the intent. There is no functional behavior change described or implied.

## Why Was This Particular Code Optimization Used?

The fix introduces a new method `_get_messages_to_set` (`pylint/lint/pylinter.py`, lines 1625–1673 in the head revision) that accumulates all `MessageDefinition` objects to be changed without touching `config`. `_set_msg_status` then calls this helper, applies all state changes, and performs the config sync exactly once (lines 1691–1697). Hoisting the sync out of the per-message loop converts the overall work from O(N²) — N messages × N-item dict comprehension each time — to O(N), which is the minimal cost to propagate state. This approach avoids any algorithmic restructuring beyond the straightforward refactor, keeping the change small and reviewable (net +15 lines in the patch, +7/−7 in the file per GitHub metadata).

## Are There Any Side Effects?

The change is functionally equivalent for all package-scope operations; `config.enable` and `config.disable` reach the same final state as before, just recomputed once at the end rather than incrementally after each message. The module-scope path in `_set_one_msg_status` (the `if scope == "module"` branch) is unaffected and untouched.

## Performance Analysis Deep Dive

Across the dominant group of 34 tests (20 runs each, source: `duration_changes`), the mean speedup is approximately 80–93% with standard deviations of 0.5–3%, indicating a consistent structural improvement rather than a measurement artifact. The two tests with lower gains (26% and 32% mean) have higher standard deviations (5%), suggesting the benefit scales with the number of messages being set per invocation — less aggressive disabling means fewer iterations saved. The magnitude (~80% reduction, or roughly 5× faster) is consistent with an O(N²) → O(N) improvement for a batch of hundreds of messages, matching the PR's own profiler data (14× improvement in `_config_initialization` with `--disable=all`).

## Code Quality Assessment

- **Pattern used**: Redundancy removal — separating the "collect what to change" phase from the "apply and sync" phase, a standard refactor for avoiding repeated expensive operations inside loops.
- **Strength**: The solution is minimal: the new `_get_messages_to_set` helper is a clean extraction with no added state, and the config sync is now a single, easy-to-find block rather than embedded inside a low-level setter.
- **Risk**: The config object now reflects the final batch state atomically rather than incrementally. Any code that reads `config.enable`/`config.disable` mid-loop during a batch disable/enable would see a different intermediate state than before — though no such consumer appears to exist in the codebase, this is the one behavioral assumption the change relies on.

## Conclusion

This is a **targeted optimization**: by extracting message resolution into `_get_messages_to_set` and moving the `config.enable`/`config.disable` sync to run once after all messages are set in `_set_msg_status`, the change eliminates O(N²) list comprehension work during `--disable=all` or category-level disable/enable operations, reducing startup cost by roughly 80% across all tested pylint invocations.
