from organism_tractability.db.feature_metadata import FeatureMetadata

from .client import NIHReporterClient, SearchResponse

_client = NIHReporterClient()


def search_nih_reporter_projects(organism_scientific_name: str) -> SearchResponse:
    """
    Search NIH RePORTER for projects related to a specific organism.

    Args:
        organism_scientific_name: Name of the organism to search for

    Returns:
        SearchResponse with typed project data
    """
    response = _client.search_projects(query=organism_scientific_name)
    return response


def get_nih_reporter(
    organism_id: int,
    organism_scientific_name: str,
    feature_metadata: FeatureMetadata,
) -> SearchResponse:
    """Get NIH RePORTER search results for an organism.

    Standardized function signature for SOURCE_REGISTRY.

    Args:
        organism_id: The organism identifier (unused, kept for consistency).
        organism_scientific_name: Scientific name of the organism to search for.
        feature_metadata: FeatureMetadata object (unused, kept for consistency).

    Returns:
        SearchResponse object with search results.
    """
    return search_nih_reporter_projects(organism_scientific_name)
