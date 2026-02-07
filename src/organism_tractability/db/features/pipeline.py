from __future__ import annotations
import csv
import json
from pathlib import Path
from typing import Any, Protocol

from organism_tractability.db.feature_metadata import FeatureMetadata, FeatureMetadataService
from organism_tractability.sources.atcc import atcc
from organism_tractability.sources.exa_answer import exa_answer
from organism_tractability.sources.ncbi import ncbi
from organism_tractability.sources.nih_reporter import nih_reporter
from organism_tractability.sources.protocols_io import protocols_io


# Protocol for source functions
# All source functions must follow this signature:
# (organism_id: int, organism_scientific_name: str, feature_metadata: FeatureMetadata) -> ResultType
class SourceFunction(Protocol):
    """Protocol defining the standard signature for all source functions."""

    def __call__(
        self,
        organism_id: int,
        organism_scientific_name: str,
        feature_metadata: FeatureMetadata,
    ) -> Any:
        """Call the source function."""
        ...


SOURCE_REGISTRY: dict[str, dict[str, Any]] = {
    "protocols_io": {
        "function": protocols_io.get_protocols_io,
    },
    "ncbi": {
        "function": ncbi.get_ncbi,
    },
    "nih_reporter": {
        "function": nih_reporter.get_nih_reporter,
    },
    "atcc": {
        "function": atcc.get_atcc,
    },
    "exa_answer": {
        "function": exa_answer.get_exa_answer,
    },
    # Add new sources here...
}


class FeaturesPipeline:
    """Orchestrates fetching features for organisms (public CSV pipeline)."""

    def __init__(self) -> None:
        self._metadata_service = FeatureMetadataService()

    def run_csv(
        self,
        input_csv_path: str | Path,
        output_csv_path: str | Path,
        source_ids: list[str] | None = None,
    ) -> None:
        """Read organisms from an input CSV and write long-format feature rows to an output CSV.

        Input CSV required columns:
        - organism_scientific_name
        - organism_id  (taxonomy id; UniProt taxonomy id == NCBI taxid)

        Output CSV columns:
        - organism_id
        - feature_id
        - source_id
        - fetched_object (JSON string)
        """
        input_csv_path = Path(input_csv_path)
        output_csv_path = Path(output_csv_path)
        output_csv_path.parent.mkdir(parents=True, exist_ok=True)

        with input_csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                raise ValueError("Input CSV has no header row.")

            required = {"organism_scientific_name", "organism_id"}
            missing = required - set(reader.fieldnames)
            if missing:
                raise ValueError(
                    f"Input CSV missing required columns: {', '.join(sorted(missing))}. "
                    f"Found columns: {', '.join(reader.fieldnames)}"
                )

            organisms: list[dict[str, Any]] = []
            for i, row in enumerate(reader, start=2):  # header is line 1
                name = (row.get("organism_scientific_name") or "").strip()
                oid_raw = (row.get("organism_id") or "").strip()
                if not name or not oid_raw:
                    raise ValueError(
                        f"Input CSV row {i} missing organism_scientific_name or organism_id: {row}"
                    )
                try:
                    oid = int(oid_raw)
                except ValueError as e:
                    raise ValueError(
                        f"Input CSV row {i} organism_id must be an integer taxonomy id, got: {oid_raw}"
                    ) from e

                organisms.append({"organism_scientific_name": name, "organism_id": oid})

        fieldnames = ["organism_id", "feature_id", "source_id", "fetched_object"]
        with output_csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for org in organisms:
                rows = self.fetch_features_for_organism(
                    organism_id=org["organism_id"],
                    organism_scientific_name=org["organism_scientific_name"],
                    source_ids=source_ids,
                )
                for r in rows:
                    writer.writerow(
                        {
                            "organism_id": r["organism_id"],
                            "feature_id": r["feature_id"],
                            "source_id": r["source_id"],
                            "fetched_object": json.dumps(
                                r["fetched_object"], ensure_ascii=False, sort_keys=True
                            ),
                        }
                    )

    def _get_sources_to_process(
        self, source_ids: list[str] | None = None
    ) -> dict[str, dict[str, Any]]:
        """Get the sources to process, filtered by source_ids if provided.

        Args:
            source_ids: Optional list of source IDs to process. If None, returns all sources.

        Returns:
            Filtered source registry dictionary.

        Raises:
            ValueError: If any source_id in source_ids is not found in SOURCE_REGISTRY.
        """
        if source_ids is None:
            return SOURCE_REGISTRY

        # Validate that all requested sources exist
        invalid_sources = [sid for sid in source_ids if sid not in SOURCE_REGISTRY]
        if invalid_sources:
            available = ", ".join(SOURCE_REGISTRY.keys())
            raise ValueError(
                f"Invalid source IDs: {', '.join(invalid_sources)}. Available sources: {available}"
            )

        return {source_id: SOURCE_REGISTRY[source_id] for source_id in source_ids}

    def fetch_features_for_organism(
        self,
        organism_id: int,
        organism_scientific_name: str,
        source_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch all configured features for a single organism.

        Returns a list of dicts suitable for writing to the public output CSV.
        """
        rows: list[dict[str, Any]] = []

        sources_to_process = self._get_sources_to_process(source_ids)
        for source_id, config in sources_to_process.items():
            features_metadata = self._metadata_service.get_feature_metadata_by_source(source_id)
            for feature_metadata in features_metadata:
                print(
                    f"Fetching: {organism_scientific_name} (taxid={organism_id}) "
                    f"feature={feature_metadata.feature_id} source={feature_metadata.source_id}"
                )
                result = config["function"](
                    organism_id=organism_id,
                    organism_scientific_name=organism_scientific_name,
                    feature_metadata=feature_metadata,
                )

                fetched_obj: Any
                if result is None:
                    fetched_obj = {}
                elif hasattr(result, "model_dump"):
                    fetched_obj = result.model_dump()
                else:
                    fetched_obj = result

                rows.append(
                    {
                        "organism_id": organism_id,
                        "feature_id": feature_metadata.feature_id,
                        "source_id": feature_metadata.source_id,
                        "fetched_object": fetched_obj,
                    }
                )

        return rows
