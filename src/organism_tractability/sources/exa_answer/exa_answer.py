from organism_tractability.db.feature_metadata import FeatureMetadata
from organism_tractability.sources.exa_answer.client import ExaAnswer, ExaAnswerClient

_client = ExaAnswerClient()


def answer_organism_query(
    organism_scientific_name: str, feature_metadata: FeatureMetadata
) -> ExaAnswer:
    """
    Search the internet to answer specific queries using the ExaClient.

    Args:
        organism_scientific_name: The scientific name of the organism to search for
        feature_metadata: FeatureMetadata object.

    Returns:
        ExaAnswer object containing organism web search results
    """
    return _client.answer_organism_query(
        organism_scientific_name=organism_scientific_name,
        feature_metadata=feature_metadata,
    )


def get_exa_answer(
    organism_id: int,
    organism_scientific_name: str,
    feature_metadata: FeatureMetadata,
) -> ExaAnswer:
    """Get web search results for an organism.

    Standardized function signature for SOURCE_REGISTRY.

    Args:
        organism_id: The organism identifier (unused, kept for consistency).
        organism_scientific_name: Scientific name of the organism to search for.
        feature_metadata: FeatureMetadata object.

    Returns:
        ExaAnswer object with web search results.
    """
    return answer_organism_query(
        organism_scientific_name=organism_scientific_name,
        feature_metadata=feature_metadata,
    )
