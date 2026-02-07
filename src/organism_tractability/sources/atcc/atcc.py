from pydantic import BaseModel, Field

from organism_tractability.db.feature_metadata import FeatureMetadata

from .client import ATCCClient, AtccProductDetail, AtccSearchResults

# Module-level client instance - reused across all calls for efficiency
# The client is stateless (only stores config), so sharing is safe
_client = ATCCClient()


class AtccSearchAndProductResults(BaseModel):
    """Combined search results and product details from ATCC."""

    search_results: AtccSearchResults | None = Field(
        None, description="Search results from ATCC search"
    )
    product_details: list[AtccProductDetail] = Field(
        default_factory=list, description="List of detailed product information"
    )


def search_and_get_atcc_products(
    organism_scientific_name: str, max_products: int = 0
) -> AtccSearchAndProductResults:
    """
    Search ATCC for organism products and extract details for the first N products.

    This function combines search and product extraction.

    Args:
        organism_scientific_name: Scientific name of the organism to search for.
        max_products: Maximum number of products to extract details for. Defaults to 3.

    Returns:
        AtccSearchAndProductResults with search_results and product_details.
    """
    # First, search for products
    search_results = _client.search_products(query=organism_scientific_name)
    product_details: list[AtccProductDetail] = []

    if search_results:
        # Next, extract product details
        products = search_results.products if search_results.products else []
        if products and max_products > 0:
            for product in products[:max_products]:
                if product and product.url:
                    product_detail = _client.get_product(product.url)
                    if product_detail:
                        product_details.append(product_detail)

    return AtccSearchAndProductResults(
        search_results=search_results, product_details=product_details
    )


def get_atcc(
    organism_id: int,
    organism_scientific_name: str,
    feature_metadata: FeatureMetadata,
) -> AtccSearchAndProductResults:
    """Get ATCC search results and product details for an organism.

    Standardized function signature for SOURCE_REGISTRY.

    Args:
        organism_id: The organism identifier (unused, kept for consistency).
        organism_scientific_name: Scientific name of the organism to search for.
        feature_metadata: FeatureMetadata object (unused, kept for consistency).

    Returns:
        AtccSearchAndProductResults object with search results and product details.
    """
    return search_and_get_atcc_products(
        organism_scientific_name=organism_scientific_name,
        max_products=feature_metadata.max_products or 0,
    )
