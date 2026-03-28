# Rationale Analysis: pydata__xarray-6109

**Repository**: pydata/xarray
**Instance ID**: pydata__xarray-6109
**Performance Improvement**: 0.0605 (~13.1% faster on primary test)
**Commit**: 228e0be009ddfb383495b0c9cfa5dcd7ae1b2793
**Type**: Single commit

---

## Pipeline Analysis Summary

- **Commit message**: "Update test_plot.py" (vague — actual change described in PR #6109 and issue #6102)
- **Merge**: No (1 parent)
- **Pattern analyzer output**: `redundancy_removal` (automated — confirmed semantically as **configuration normalization / external dependency removal**)
- **Related issues**: [#6102](https://github.com/pydata/xarray/issues/6102) — "Regression in datetime handling in plots"; [#6109](https://github.com/pydata/xarray/pull/6109) — PR "Remove registration of pandas datetime converter in plotting"
- **Problem statement (oracle)**: Optimize `import_matplotlib_pyplot` and `register_pandas_datetime_converter_if_needed` in `xarray/plot/utils.py`
- **Problem statement (realistic)**: Optimize functions in `duck_array_ops.py`, `plot.py`, `_reductions.py`, and `common.py` (test-facing entry points that all internally call `import_matplotlib_pyplot`)
- **Per-test speedups** (from `duration_changes`, 20 runs each):

  | Test | Base avg (s) | Head avg (s) | Avg Speedup |
  |------|-------------|-------------|-------------|
  | `test_xincrease_kwarg[2-True]` | 0.0303 | 0.0263 | **+13.1%** |
  | `test_coord_with_interval_step_x` | ~0.0136 | ~0.0135 | **+0.7%** (noise) |

---

## What Problem Does It Solve?

### The Bug / Regression

In 2017, xarray added `register_pandas_datetime_converter_if_needed()` (PR #1669) to work around a crash in matplotlib when rendering `numpy.datetime64` objects. The fix registered pandas' datetime converters into matplotlib's global converter registry.

However, matplotlib gained native `datetime64` support in version 2.2.0 (2018), making this workaround unnecessary. The workaround remained in the codebase years after it became obsolete.

This created a **regression documented in issue #6102**: simply importing xarray and using it to load a dataset would globally replace matplotlib's native datetime converters with pandas' converters — even if the user never used xarray's plotting utilities. As a result, code like:

```python
import xarray as xr  # pandas converters silently registered here
import matplotlib.pyplot as plt

fig, ax = plt.subplots()
ax.scatter(ds['time'], ds['sir'])  # CRASHES — pandas converter has a bug with scatter
```

...would break. The user never called any xarray plot function, yet matplotlib's converter was overridden as a side effect.

### The Performance Issue

Beyond the bug, `pd.plotting.register_matplotlib_converters()` has a non-trivial startup cost: it walks through all pandas converter types and inserts them into matplotlib's global `munits.registry` dict. This ran **on every first call to any xarray plot function** (which all route through `import_matplotlib_pyplot()`), costing roughly 4–5 ms that appeared as pure overhead unrelated to actual plotting work.

---

## Why Was This Particular Code Optimization Used?

The simplest correct fix: **remove the workaround entirely**, since the upstream library (matplotlib ≥ 2.2.0) now handles `datetime64` natively without needing any converter registration.

### Before

```python
_registered = False


def register_pandas_datetime_converter_if_needed():
    # based on https://github.com/pandas-dev/pandas/pull/17710
    global _registered
    if not _registered:
        pd.plotting.register_matplotlib_converters()  # global side effect
        _registered = True


def import_matplotlib_pyplot():
    """Import pyplot as register appropriate converters."""
    register_pandas_datetime_converter_if_needed()    # called on every first import
    import matplotlib.pyplot as plt
    return plt
```

### After

```python
def import_matplotlib_pyplot():
    """import pyplot"""
    # TODO: This function doesn't do anything (after #6109), remove it?
    import matplotlib.pyplot as plt
    return plt
```

The `register_pandas_datetime_converter_if_needed` function, the `_registered` flag, and the call inside `import_matplotlib_pyplot` are all removed. The function is now a thin wrapper around `import matplotlib.pyplot as plt` with a TODO suggesting even that wrapper may be removed later.

**Why not cache or defer the registration?** The correct answer is that the registration should not happen at all. No workaround or deferral is needed because matplotlib's native support is sufficient. The "lazy initialization" pattern used before (the `_registered` flag) was itself trying to limit the damage of an unwanted side effect — removing the cause is strictly better than optimizing the workaround.

---

## Are There Any Side Effects?

### Breaking Change (Intentional)

This is explicitly documented under **Breaking Changes** in `doc/whats-new.rst`:

> Rely on matplotlib's default datetime converters instead of pandas' (:issue:`6102`, :pull:`6109`).

Any code that depended on xarray's import silently registering pandas datetime converters will now receive matplotlib's native converters instead. In practice this is a **bug fix**, not a regression, since pandas' converter had known issues with matplotlib scatter plots.

### Test Assertion Tightened

The test patch changes:

```python
# Before — passes for any AutoDateLocator subclass (including pandas subclasses)
assert isinstance(ax.xaxis.get_major_locator(), mpl.dates.AutoDateLocator)

# After — passes only for exactly matplotlib's AutoDateLocator, not subclasses
assert type(ax.xaxis.get_major_locator()) is mpl.dates.AutoDateLocator
```

This is a deliberate tightening: the old `isinstance` check would pass even if pandas' converter registered a subclass of `AutoDateLocator`, masking regressions. The `type() is` check enforces that matplotlib's own converter — not any pandas-overridden one — is active.

### Functional Equivalence

For all **correct** usage (matplotlib ≥ 2.2.0), the plotting behavior is functionally equivalent. Datetime axes still render correctly; only the underlying converter implementation changes (from pandas back to matplotlib's native one).

---

## Performance Analysis Deep Dive

### Why Only `test_xincrease_kwarg` Sees a Speedup?

Both tests call plotting functions that route through `import_matplotlib_pyplot()`. However, Python caches module imports: after the first `import matplotlib.pyplot as plt` succeeds, subsequent calls skip the import machinery. The pandas converter registration (`pd.plotting.register_matplotlib_converters()`) was the only non-idempotent work that ran every time the function was called on a fresh test session.

- **`test_xincrease_kwarg[2-True]`**: This test exercises `plt.gca()` / axis manipulation paths that are among the first to call `import_matplotlib_pyplot()` in the test session, so it absorbs the full cost of the one-time registration (~4 ms). Removing registration yields a consistent **~13% speedup** across all 20 runs.
- **`test_coord_with_interval_step_x`**: This test exercises a code path where the import/registration overhead is either already amortized by previous tests or falls in a different execution order. The speedup is **~0.7%**, within measurement noise.

### Consistency

The `test_xincrease_kwarg` speedup is highly consistent (10–18% range, mean 13.1%), confirming a real, stable elimination of fixed overhead rather than measurement noise.

### Magnitude vs. Pattern Match

`human_performance = 0.0605` is a mid-range improvement in this dataset (between micro-optimizations < 0.01 and algorithmic improvements > 0.1). This matches the pattern: removing a one-time initialization call (not a hot loop, not an algorithm change) produces a modest but reliable speedup per test session. The absolute savings (~4 ms) are meaningful in test suite contexts where plotting tests run hundreds of times.

---

## Code Quality Assessment

### Strengths

- **Net code removal**: 13 lines removed, 4 added — complexity decreases. The `global` state variable `_registered` and the associated function are eliminated entirely, removing a subtle statefulness from the module.
- **Correct root-cause fix**: Instead of optimizing the workaround, the workaround is removed because the underlying problem no longer exists.
- **Self-documenting TODO**: The TODO comment on `import_matplotlib_pyplot` is honest — the function now does nothing special and its own removal is the logical next step.
- **Test precision improvement**: Switching from `isinstance` to `type() is` prevents future silent regressions where a converter subclass might pass the old check.

### Potential Risks

- **Minimum matplotlib version assumption**: This change is only safe if xarray requires matplotlib ≥ 2.2.0. If users run with older matplotlib, datetime plots could fail again. This should be enforced in `setup.cfg` / `pyproject.toml` version constraints.
- **`import_matplotlib_pyplot` is now a no-op wrapper**: Every call site in the codebase that calls this function (there are many — it is used throughout `xarray/plot/`) could be simplified to a direct `import matplotlib.pyplot as plt`. The TODO comment acknowledges this technical debt.

---

## Conclusion

The change removes `register_pandas_datetime_converter_if_needed()` — a 2017 workaround that called `pd.plotting.register_matplotlib_converters()` on the first invocation of any xarray plot function. This workaround became unnecessary once matplotlib 2.2.0 (2018) added native `numpy.datetime64` support. Keeping it caused two problems: a **bug** (pandas' converters globally overrode matplotlib's, breaking native matplotlib scatter plots after any xarray import), and a **performance overhead** (~4 ms per test session). Removing the workaround eliminates both. The primary efficiency test shows a consistent **~13% speedup** on plotting tests that previously bore the one-time registration cost. The fix is a textbook example of **removing obsolete workarounds when the underlying platform has caught up**: the correct optimization was not to make the workaround faster, but to recognize it was no longer needed and delete it.
