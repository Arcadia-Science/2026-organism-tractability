import copy
from typing import Any

from pydantic import BaseModel

from organism_tractability.db.feature_metadata import FeatureMetadata, FeatureMetadataService
from organism_tractability.utils.ExaClient import Citation, ExaClient


class AnswerContent(BaseModel):
    """Pydantic model representing the answer content from Exa API."""

    reasoning: str
    confidence: str
    answer: str


class ExaAnswer(BaseModel):
    """Pydantic model representing Exa API answer."""

    requestId: str
    answer: AnswerContent
    citations: list[Citation]
    costDollars: dict[str, float]


class OrganismWebSearchQuery(BaseModel):
    """Pydantic model representing a web search query for an organism."""

    query: str
    output_schema: dict[str, Any]


BASE_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["answer", "reasoning", "confidence"],
    "additionalProperties": False,
    "properties": {
        "reasoning": {
            "type": "string",
            "description": "Scientific reasoning and evidence for the answer",
        },
        "confidence": {
            "type": "string",
            "enum": [
                "low",
                "medium",
                "high",
            ],
            "description": "Confidence level in the answer based on available evidence",
        },
    },
}


class ExaAnswerClient:
    """Client for interacting with the Exa API to search the web for organism information."""

    def __init__(self):
        """Initialize the ExaAnswer client."""
        self.exa_client = ExaClient()
        self.metadata_service = FeatureMetadataService()

    def _create_query_output_schema(
        self,
        query: str,
        answer_enum: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Create an output schema for a specific query by extending the base schema.

        Args:
            query: The query being asked
            answer_enum: Custom enum values for the answer. If None, uses plain text.

        Returns:
            Complete output schema for the query
        """
        if answer_enum:
            answer_field = {
                "type": "string",
                "enum": answer_enum,
                "description": f"Answer to: {query}",
            }
        else:
            answer_field = {
                "type": "string",
                "description": f"Answer to: {query}",
            }

        # Create the complete schema
        output_schema = copy.deepcopy(BASE_OUTPUT_SCHEMA)
        output_schema["properties"]["answer"] = answer_field

        return output_schema

    def _create_organism_web_search_query(
        self, organism_scientific_name: str, feature_metadata: FeatureMetadata
    ) -> OrganismWebSearchQuery:
        """
        Create a query object for the Exa API based on feature metadata.

        Args:
            organism_scientific_name: The scientific name of the organism to search for
            feature_metadata: FeatureMetadata object.

        Returns:
            OrganismWebSearchQuery object containing query and schema information
        """

        query_template = feature_metadata.query
        answer_enum = feature_metadata.answer_enum

        query = (
            query_template.format(organism=organism_scientific_name)
            if query_template
            else organism_scientific_name
        )

        output_schema = self._create_query_output_schema(
            query=query,
            answer_enum=answer_enum,
        )

        return OrganismWebSearchQuery(
            query=query,
            output_schema=output_schema,
        )

    def answer_organism_query(
        self, organism_scientific_name: str, feature_metadata: FeatureMetadata
    ) -> ExaAnswer:
        """
        Search the internet to answer a specific query using the ExaClient.

        Args:
            organism_scientific_name: The scientific name of the organism to search for
            feature_metadata: FeatureMetadata object.

        Returns:
            ExaAnswer object containing organism web search results
        """
        query_metadata = self._create_organism_web_search_query(
            organism_scientific_name=organism_scientific_name,
            feature_metadata=feature_metadata,
        )

        raw_answer = self.exa_client.answer(
            query=query_metadata.query, output_schema=query_metadata.output_schema
        )

        return ExaAnswer(
            requestId=raw_answer["requestId"],
            answer=AnswerContent(**raw_answer["answer"]),
            citations=[Citation(**citation) for citation in raw_answer["citations"]],
            costDollars=raw_answer["costDollars"],
        )
