"""Centralized service for reading and managing feature metadata from YAML."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


def get_feature_metadata_path() -> Path:
    """Get the standardized path to feature_metadata.yaml.

    Returns:
        Path to the feature_metadata.yaml file.
    """
    current_dir = Path(__file__).parent
    return current_dir / "feature_metadata.yaml"


class FeatureMetadata(BaseModel):
    """Pydantic model for feature metadata validation.

    Extra fields are allowed during validation but will not be inserted into the database.
    Only the defined fields (feature_id, source_id, display_name, category, description) are synced.
    """

    feature_id: str = Field(...)
    source_id: str = Field(...)
    display_name: str = Field(...)
    category: str = Field(...)
    description: str = Field(..., min_length=1)
    # Optional extra fields. These are not synced to the database, but rather used by the source
    # functions or the FeaturesWidePipeline.
    organism_query_type: str | None = Field(default=None)
    answer_enum: list[str] | None = Field(default=None)
    query: str | None = Field(default=None)
    max_products: int | None = Field(default=None)
    type: str | None = Field(default=None)


class FeatureMetadataService:
    """Centralized service for reading feature metadata from YAML."""

    def _load_yaml(self) -> dict[str, Any]:
        """Load YAML file.

        Returns:
            Dictionary containing the YAML data.
        """
        yaml_path = get_feature_metadata_path()
        with open(yaml_path) as f:
            return yaml.safe_load(f)

    def get_all_feature_metadata(self) -> list[FeatureMetadata]:
        """Get all feature metadata from the YAML file, validated as FeatureMetadata objects.

        Returns:
            List of validated FeatureMetadata objects.

        Raises:
            ValidationError: If any feature fails Pydantic validation.
        """
        data = self._load_yaml()
        feature_dicts = data.get("features", [])
        return [FeatureMetadata.model_validate(f) for f in feature_dicts]

    def get_feature_ids_for_source(self, source_id: str) -> list[str]:
        """Get feature IDs for a given source.

        Args:
            source_id: The source ID to filter by (e.g., "protocols_io", "ncbi").

        Returns:
            List of feature_ids for the specified source.
        """
        features = self.get_all_feature_metadata()
        return [f.feature_id for f in features if f.source_id == source_id]

    def get_feature_metadata_by_source(self, source_id: str) -> list[FeatureMetadata]:
        """Get all feature metadata for a given source as FeatureMetadata objects.

        Args:
            source_id: The source ID to filter by.

        Returns:
            List of FeatureMetadata objects for the specified source.
        """
        features = self.get_all_feature_metadata()
        return [f for f in features if f.source_id == source_id]
