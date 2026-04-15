from __future__ import annotations
import importlib
import sys

import pytest
from organism_tractability.db.feature_metadata import FeatureMetadata


def _clear_pipeline_related_modules() -> None:
    module_prefixes = (
        "organism_tractability.db.features.pipeline",
        "organism_tractability.sources.ncbi",
        "organism_tractability.sources.protocols_io",
        "organism_tractability.sources.atcc",
        "organism_tractability.sources.exa_answer",
        "organism_tractability.sources.nih_reporter",
        "organism_tractability.utils.FirecrawlClient",
    )
    for module_name in list(sys.modules):
        if module_name.startswith(module_prefixes):
            sys.modules.pop(module_name, None)


def test_pipeline_import_does_not_require_all_api_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    for env_name in (
        "NCBI_API_KEY",
        "NCBI_API_EMAIL",
        "PROTOCOLS_IO_API_CLIENT_ACCESS_TOKEN",
        "FIRECRAWL_API_KEY",
        "EXA_API_KEY",
    ):
        monkeypatch.delenv(env_name, raising=False)

    _clear_pipeline_related_modules()
    module = importlib.import_module("organism_tractability.db.features.pipeline")

    assert hasattr(module, "FeaturesPipeline")


def test_fetch_features_only_processes_selected_source(monkeypatch: pytest.MonkeyPatch) -> None:
    from organism_tractability.db.features import pipeline

    selected_source = "nih_reporter"
    called_sources: list[str] = []

    def _stubbed_source(
        organism_id: int, organism_scientific_name: str, feature_metadata: FeatureMetadata
    ) -> dict[str, str]:
        called_sources.append(feature_metadata.source_id)
        return {"source": feature_metadata.source_id, "name": organism_scientific_name}

    monkeypatch.setitem(
        pipeline.SOURCE_REGISTRY,
        selected_source,
        {"function": _stubbed_source},
    )
    monkeypatch.setattr(
        pipeline.FeatureMetadataService,
        "get_feature_metadata_by_source",
        lambda self, source_id: [
            FeatureMetadata(
                feature_id="nih_reporter",
                source_id=source_id,
                display_name="NIH RePORTER",
                category="Community",
                description="smoke-test feature",
            )
        ],
    )

    result_rows = pipeline.FeaturesPipeline().fetch_features_for_organism(
        organism_id=562,
        organism_scientific_name="Escherichia coli",
        source_ids=[selected_source],
    )

    assert called_sources == [selected_source]
    assert len(result_rows) == 1
    assert result_rows[0]["source_id"] == selected_source
