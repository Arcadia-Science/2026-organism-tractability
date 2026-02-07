from typing import Literal

from organism_tractability.db.feature_metadata import FeatureMetadata

from .client import ProtocolSearchResults, ProtocolsIOClient

_client = ProtocolsIOClient()


def search_public_protocols(
    organism_scientific_name: str,
    page_size: int = 10,
    page_id: int = 0,
    order_field: Literal["activity", "date", "name", "id"] = "activity",
    order_dir: Literal["asc", "desc"] = "desc",
) -> ProtocolSearchResults:
    """
    Search for public protocols on protocols.io.

    This is a convenience function that uses the ProtocolsIOClient internally.

    Args:
        organism_scientific_name: Scientific name of the organism to search for
        page_size: Number of items per page (1-100, default: 10)
        page_id: Page number (0-based, default: 0)
        order_field: Order field (activity, date, name, id)
        order_dir: Order direction (asc, desc)

    Returns:
        ProtocolSearchResults object with search results

    Raises:
        requests.RequestException: If API request fails
        ValueError: If PROTOCOLS_IO_API_CLIENT_ACCESS_TOKEN is not set
    """
    return _client.search_protocols(
        key=organism_scientific_name,
        page_size=page_size,
        page_id=page_id,
        order_field=order_field,
        order_dir=order_dir,
    )


def get_protocols_io(
    organism_id: int,
    organism_scientific_name: str,
    feature_metadata: FeatureMetadata,
) -> ProtocolSearchResults:
    """Get protocols.io search results for an organism.

    Standardized function signature for SOURCE_REGISTRY.

    Args:
        organism_id: The organism identifier (unused, kept for consistency).
        organism_scientific_name: Scientific name of the organism to search for.
        feature_metadata: FeatureMetadata object (unused, kept for consistency).

    Returns:
        ProtocolSearchResults object with search results.
    """
    return search_public_protocols(organism_scientific_name)
