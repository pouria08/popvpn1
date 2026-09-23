"""POPVPN X — self-updating VPN subscription pipeline.

The whole package is written against the Python standard library only, so the
pipeline runs on a bare ``python:3.11`` image with no ``pip install`` step.
"""

from __future__ import annotations

__version__ = "2.1.0"
__brand__ = "POPVPN X"

__all__ = ["__version__", "__brand__"]
