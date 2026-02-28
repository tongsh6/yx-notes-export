import os

# pyright: reportMissingImports=false

import pytest

from src.auth import AuthConfig, build_client
from src.exporter import Exporter
from src.fetcher import Fetcher


@pytest.mark.skipif(
    not os.environ.get("YX_TOKEN"),
    reason="Requires YX_TOKEN environment variable",
)
def test_real_api_export_one(tmp_path):
    token = os.environ.get("YX_TOKEN")
    client = build_client(AuthConfig(mode="token", token=token))
    fetcher = Fetcher(client)

    notebooks = fetcher.list_notebooks()
    assert notebooks is not None
    if not notebooks:
        pytest.skip("No notebooks available")

    nb = notebooks[0]
    metas = list(fetcher.iter_notes(notebook_guid=nb.guid))
    if not metas:
        pytest.skip("No notes in first notebook")

    exporter = Exporter(fetcher, str(tmp_path))
    path, _skipped = exporter.export_note(metas[0], nb, {})
    assert os.path.exists(path)
