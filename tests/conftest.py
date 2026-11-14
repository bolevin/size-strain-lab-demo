from __future__ import annotations

import os
from pathlib import Path

import pytest

# the window tests need no screen; must be set before Qt is imported
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from sizeout_demo.adapters import CsvReflectionReader
from sizeout_demo.application import ReflectionData, SizeStrainService
from sizeout_demo.main import build_service, data_path


@pytest.fixture(scope="session")
def sample_path() -> Path:
    return data_path("sample_reflections.csv")


@pytest.fixture(scope="session")
def sample(sample_path: Path) -> ReflectionData:
    return CsvReflectionReader().read(sample_path)


@pytest.fixture
def service() -> SizeStrainService:
    return build_service()
