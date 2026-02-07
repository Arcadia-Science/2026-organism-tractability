import os
from typing import Any, Literal
from urllib.parse import quote

import requests
from dotenv import load_dotenv
from pydantic import BaseModel

from organism_tractability.utils.rate_limiter import RateLimiter, retry_with_backoff

load_dotenv()

PROTOCOLS_IO_BASE_URL = "https://www.protocols.io/api/v3"

# Protocols.io enforces a rate limit of 100 requests per minute per user (~1.67 req/s)
# https://apidoc.protocols.io/#api-usage-limits
_rate_limiter = RateLimiter(calls_per_second=1.67)


# TODO (Ahmed): Other fields of interest to consider adding: stats (contains views, exports,
# bookmarks ..etc) and published_on date.
class Protocol(BaseModel):
    """Protocol information from protocols.io."""

    title: str
    url: str


class ProtocolSearchResults(BaseModel):
    """Search results from protocols.io."""

    protocols: list[Protocol]
    total_results: int
    current_page: int
    total_pages: int
    status_code: int = 0
    web_search_url: str = ""


class ProtocolsIOClient:
    """Generic client for protocols.io API."""

    def __init__(
        self,
        access_token: str | None = None,
        base_url: str | None = None,
    ):
        """Initialize the client with configuration options."""
        self.access_token = access_token or os.environ.get("PROTOCOLS_IO_API_CLIENT_ACCESS_TOKEN")
        self.base_url = base_url or PROTOCOLS_IO_BASE_URL

        if not self.access_token:
            raise ValueError("PROTOCOLS_IO_API_CLIENT_ACCESS_TOKEN must be provided")

    @retry_with_backoff(max_attempts=5, min_wait=1.0, max_wait=60.0)
    def _throttled_request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        timeout: int = 30,
    ) -> requests.Response:
        """
        Perform a throttled HTTP request with retry logic.

        Protocols.io enforces a rate limit of 100 requests per minute per user.
        If the limit is exceeded, the API will return a 429 Too Many Requests response.

        See: https://apidoc.protocols.io/#api-usage-limits

        Args:
            method: HTTP method (GET, POST, etc.)
            url: The endpoint URL
            headers: Optional headers
            params: Optional query parameters
            timeout: Request timeout in seconds

        Returns:
            The response object

        Raises:
            requests.RequestException: If all retry attempts are exhausted
        """
        _rate_limiter.wait()
        response = requests.request(
            method=method, url=url, headers=headers, params=params, timeout=timeout
        )
        response.raise_for_status()
        return response

    def _get_headers(self) -> dict[str, str]:
        """Get headers for protocols.io API requests."""

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _generate_web_search_url(self, search_term: str) -> str:
        """
        Generate the protocols.io web search URL for a given search term.

        Args:
            search_term: The search term to encode in the URL

        Returns:
            The complete web search URL with encoded search term

        Note:
            The web search interface uses broader matching (OR logic) and includes
            results for genus-only OR species-only matches, which will return more
            hits than the API's phrase-based search.
        """
        encoded_term = quote(search_term)
        return f"https://www.protocols.io/search?q={encoded_term}"

    # TODO (Ahmed): Add pagination support to get all pages of results automatically.
    # Current implementation only returns results from the requested page (default: first page).
    # If results spill over into subsequent pages, the page_id argument must be incremented.
    def search_protocols(
        self,
        key: str,
        page_size: int = 10,
        page_id: int = 0,
        order_field: Literal["activity", "date", "name", "id"] = "activity",
        order_dir: Literal["asc", "desc"] = "desc",
        filter: Literal["public"] = "public",
    ) -> ProtocolSearchResults:
        """
        Search for protocols on protocols.io.

        See: https://apidoc.protocols.io/#get-list

        Args:
            key: Search query string
            page_size: Number of items per page (1-100, default: 10)
            page_id: Page number (0-based, default: 0)
            order_field: Order field (activity, date, name, id)
            order_dir: Order direction (asc, desc)
            filter: Filter type (Since we are using the "client access" method for API access, we
            can only access public data. See .env.example)

        Returns:
            ProtocolSearchResults object with search results

        Raises:
            requests.RequestException: If API request fails

        Note 1:
            IMPORTANT: The protocols.io API documentation incorrectly states that page_id
            is "1-based" with "default is 1", but the actual API behavior is 0-based:
            - page_id=0 → First page (API returns current_page=1)
            - page_id=1 → Second page (API returns current_page=2)
            The API internally uses 0-based pagination despite the
            documentation claiming it's 1-based.

        Note 2:
            IMPORTANT: The API documentation lists "relevance" as a valid order_field option,
            but using order_field="relevance" causes a 400 Bad Request.

        Note 3:
            This API searches for the complete search_key as a phrase (e.g., "Chlorella vulgaris"
            will find protocols containing both "Chlorella" and "vulgaris" together). For OR
            logic with multiple terms, we can implement this by making multiple API calls and
            combining the results programmatically. See note in _generate_web_search_url().
            TODO (Ahmed): Ask Brae about the utility of searching by genus only.
        """

        url = f"{self.base_url}/protocols"
        headers = self._get_headers()

        params = {
            "key": key,
            "page_size": min(max(page_size, 1), 100),  # Ensure between 1-100
            "page_id": max(page_id, 0),  # Ensure >= 0 (0-based pagination)
            "order_field": order_field,
            "order_dir": order_dir,
            "filter": filter,
        }

        response = self._throttled_request("GET", url, headers=headers, params=params)
        data = response.json()

        pagination = data.get("pagination", {})
        transformed_data = {
            "protocols": [Protocol.model_validate(item) for item in data.get("items", [])],
            "total_results": pagination.get("total_results", 0),
            "current_page": pagination.get("current_page", 0),
            "total_pages": pagination.get("total_pages", 0),
            "status_code": response.status_code,
            "web_search_url": self._generate_web_search_url(key),
        }

        return ProtocolSearchResults.model_validate(transformed_data)
