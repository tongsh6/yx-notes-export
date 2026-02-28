from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def screenshot_dir(request) -> Path:
    root = Path("tests") / "artifacts" / "screenshots"
    root.mkdir(parents=True, exist_ok=True)

    if request.config.getoption("--clean-screenshots"):
        for item in root.glob("*.png"):
            item.unlink()
    return root


def pytest_addoption(parser):
    parser.addoption(
        "--clean-screenshots",
        action="store_true",
        default=True,
        help="Clean screenshots folder before tests (default: true)",
    )
