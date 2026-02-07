import os
from typing import Any
from urllib.parse import quote

import requests
from dotenv import load_dotenv
from pydantic import BaseModel

from organism_tractability.db.feature_metadata import FeatureMetadata
from organism_tractability.utils.rate_limiter import RateLimiter, retry_with_backoff

load_dotenv()

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
SEARCH_ENDPOINT = f"{BASE}/esearch.fcgi"
NCBI_API_TOOL_ID = "organism_tractability"

# NCBI allows up to 10 requests per second with an API key
_rate_limiter = RateLimiter(calls_per_second=10)


class NCBISearchResult(BaseModel):
    """Result from an NCBI database search."""

    search_url: str
    count: int


class NCBIClient:
    """Client for NCBI E-utilities API."""

    def __init__(
        self,
        api_key: str | None = None,
        api_email: str | None = None,
        tool_id: str | None = None,
    ):
        """Initialize the client with configuration options.

        Args:
            api_key: NCBI API key (defaults to NCBI_API_KEY env var).
            api_email: NCBI API email (defaults to NCBI_API_EMAIL env var).
            tool_id: Tool identifier for NCBI API (defaults to NCBI_API_TOOL_ID).
        """
        self.api_key = api_key or os.environ.get("NCBI_API_KEY")
        self.api_email = api_email or os.environ.get("NCBI_API_EMAIL")
        self.tool_id = tool_id or NCBI_API_TOOL_ID

        if not self.api_key:
            raise ValueError("NCBI_API_KEY must be provided")
        if not self.api_email:
            raise ValueError("NCBI_API_EMAIL must be provided")

    @retry_with_backoff(max_attempts=5, min_wait=1.0, max_wait=60.0)
    def _throttled_get(
        self, url: str, params: dict[str, Any], timeout: int = 30
    ) -> requests.Response:
        """
        Perform a GET request to the specified URL with throttling to respect NCBI rate limits.

        By including an API key, a site can post up to 10 requests per second by default.

        Args:
            url: The endpoint URL to send the GET request to.
            params: Dictionary of query parameters to include in the request.
            timeout: Timeout in seconds for the request (default: 30).

        Returns:
            The response object from the requests library.
        """
        _rate_limiter.wait()
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp

    def _params(self, extra: dict[str, Any]) -> dict[str, Any]:
        """
        Construct a dictionary of parameters for NCBI E-utilities requests, including
        required tool identification, email, and API key, merged with any additional
        parameters provided.

        Args:
            extra (dict): Additional parameters to include in the request.

        Returns:
            dict[str, Any]: Dictionary of parameters for the NCBI request.
        """
        params = {
            "tool": self.tool_id,
            "email": self.api_email,
            "api_key": self.api_key,
            **extra,
        }
        return params

    def _get_search_term(
        self, feature_metadata: FeatureMetadata, organism_scientific_name: str, organism_id: int
    ) -> str:
        """Get the appropriate search term based on database query type.

        Args:
            feature_metadata: The FeatureMetadata object.
            organism_scientific_name: The scientific name of the organism.
            organism_id: The ID of the organism (aka taxonomy ID).

        Returns:
            A search term string appropriate for the database.
        """
        query_type = feature_metadata.organism_query_type

        def _quoted_and_term(name: str) -> str:
            # Quote each token and AND-join so multi-word names (e.g. "Hornefia sp.")
            # search as: "Hornefia" AND "sp."
            tokens = [t for t in name.split() if t]
            return " AND ".join(f'"{t}"' for t in tokens) if tokens else name

        if query_type == "scientific_name":
            return _quoted_and_term(organism_scientific_name)
        elif query_type == "taxonomy_id":
            return f"txid{organism_id}[Organism]"
        else:
            # Default to scientific_name if not specified
            return _quoted_and_term(organism_scientific_name)

    def _get_search_url(
        self, feature_metadata: FeatureMetadata, organism_scientific_name: str, organism_id: int
    ) -> str:
        """Generate the appropriate search URL for each NCBI database.

        Args:
            feature_metadata: The FeatureMetadata object.
            organism_scientific_name: The scientific name of the organism.
            organism_id: The ID of the organism (aka taxonomy ID).

        Returns:
            A properly formatted search URL for the specified database.
        """
        term = self._get_search_term(feature_metadata, organism_scientific_name, organism_id)
        encoded_term = quote(term)

        db_code = feature_metadata.feature_id

        if db_code == "pubmed":
            return f"https://pubmed.ncbi.nlm.nih.gov/?term={encoded_term}&sort=date&ac=yes"
        return f"https://www.ncbi.nlm.nih.gov/{db_code}/?term={encoded_term}"

    def comprehensive_ncbi_search(
        self, organism_scientific_name: str, organism_id: int, feature_metadata: FeatureMetadata
    ) -> NCBISearchResult:
        """Comprehensive search across NCBI databases with search result URLs.

        Searches across multiple NCBI database categories including Literature, Genes,
        Proteins, and Genomes. Each database uses either organism name or taxonomy ID
        based on its configured query type.

        The API documentation can be found at:
        https://www.ncbi.nlm.nih.gov/books/NBK25501/ and a quick start guide at:
        https://www.ncbi.nlm.nih.gov/books/NBK25500/

        Notes:
            - Clinical databases (e.g., ClinicalTrials.gov, ClinVar, dbGaP) are excluded
              because these are primarily human-centric and will be queried via their own APIs.
            - PubChem-related databases are excluded because PubChem APIs will be queried directly.
            - Each database uses either scientific_name or taxonomy_id based on its configuration.

        Args:
            organism_scientific_name: The scientific name of the organism.
            organism_id: The ID of the organism.
            feature_metadata: FeatureMetadata to search.

        Returns:
            NCBISearchResult with search URL and count.

        Raises:
            Exception: If an NCBI API request fails.
            ValidationError: If the API response doesn't match the expected result structure.
        """

        term = self._get_search_term(feature_metadata, organism_scientific_name, organism_id)
        search_url = self._get_search_url(feature_metadata, organism_scientific_name, organism_id)

        params = self._params(
            {
                "db": feature_metadata.feature_id,
                "term": term,
                "retmode": "json",
                "retmax": 5,
            }
        )

        response = self._throttled_get(SEARCH_ENDPOINT, params=params, timeout=30)
        data = response.json()
        count = int(data["esearchresult"]["count"])

        result_dict = {
            "search_url": search_url,
            "count": count,
        }

        return NCBISearchResult.model_validate(result_dict)
