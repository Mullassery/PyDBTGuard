"""PyDBTGuard: pre-deployment validation for dbt tests.

Analysis runs entirely on real, locally-produced dbt artifacts (``manifest``,
``catalog``, ``run_results``, ``sources``). No warehouse connection is made.
The compiled ``pydbtguard._core`` extension does the analysis; this package is
the I/O and CLI layer around it.
"""

from __future__ import annotations

try:
    from . import _core
except ImportError as exc:  # pragma: no cover - exercised only when unbuilt
    raise ImportError(
        "pydbtguard's compiled engine (pydbtguard._core) is not built. "
        "Install a wheel (pip install pydbtguard) or, in a source checkout, "
        "run 'maturin develop' before importing pydbtguard."
    ) from exc

__version__ = _core.engine_version()

__all__ = ["__version__", "_core"]
