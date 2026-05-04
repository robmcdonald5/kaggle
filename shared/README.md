# shared/

Cross-competition utilities. Anything that's useful in **two or more** competitions belongs here.

After `uv sync` (or `pip install -e .`) this package is importable from any notebook or script in the repo:

```python
from shared.io import load_competition_data   # for example
```

## What goes here

- I/O helpers (loading from `competitions/<name>/data/raw/`, caching to interim, etc.)
- CV utilities (custom fold splitters, OOF accumulators)
- Metric implementations Kaggle uses but sklearn doesn't ship
- Reproducibility helpers (seed everything, pin determinism)
- Plotting templates you reach for repeatedly

## What does NOT go here

- One-off transforms specific to a single competition -- those live in `competitions/<name>/src/`
- Speculative abstractions before you've seen the second use case. Copy-paste once, extract on the third call site.
