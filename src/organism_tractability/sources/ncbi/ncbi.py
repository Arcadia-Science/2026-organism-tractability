from organism_tractability.db.feature_metadata import FeatureMetadata

from .client import NCBIClient, NCBISearchResult

_client = NCBIClient()


def get_ncbi(
    organism_id: int, organism_scientific_name: str, feature_metadata: FeatureMetadata
) -> NCBISearchResult:
    """Get comprehensive organism overview with search results.

    Args:
        organism_id: The organism identifier (taxonomy ID).
        organism_scientific_name: The scientific name of the organism.
        feature_metadata: FeatureMetadata to search.

    Returns:
        NCBISearchResult with search URL and count.
    """
    return _client.comprehensive_ncbi_search(
        organism_scientific_name=organism_scientific_name,
        organism_id=organism_id,
        feature_metadata=feature_metadata,
    )
