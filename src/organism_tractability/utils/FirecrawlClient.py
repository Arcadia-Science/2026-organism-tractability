import os
from typing import Any

from firecrawl import FirecrawlApp
from firecrawl.v2.types import ScrapeOptions

from organism_tractability.utils.rate_limiter import ConcurrencyLimiter

# Firecrawl Standard plan: 50 concurrent browsers, 500 requests/min for /scrape and /extract. https://docs.firecrawl.dev/rate-limits
_concurrency_limiter = ConcurrencyLimiter(max_concurrent=50)


class FirecrawlExtractionError(RuntimeError):
    """Raised when Firecrawl returns an incomplete/empty response that should be retried."""


class FirecrawlClient:
    """Generic wrapper for Firecrawl API.

    Loads the API key from environment and provides a simple helpers to run `extract` against a
    single URL with retry logic and optional JSON schema enforcement.

    Example:
        firecrawl_client = FirecrawlClient()
        data = firecrawl_client.extract(
            url="https://example.com",
            prompt="Extract title and headings as JSON",
            schema=None,
        )
    """

    def __init__(self) -> None:
        """Initialize the extractor, loading API key from environment."""
        self.api_key = os.environ.get("FIRECRAWL_API_KEY")
        if not self.api_key:
            raise ValueError("FIRECRAWL_API_KEY environment variable is required")
        self.app = FirecrawlApp(api_key=self.api_key)

    # TODO (Ahmed): Turning off caching here as calls with different urls are not invalidating
    # the cache (changes come after the hash). Need to test this further.
    # TODO (Ahmed): Extend this to run on multiple URLs with retry logic. The extract API endpoint
    # already supports multiple urls.
    def extract(
        self,
        url: str,
        prompt: str,
        schema: dict[str, Any] | None = None,
        timeout_ms: int = 100000,
        store_in_cache: bool = False,
    ) -> dict[str, Any] | None:
        """Run Firecrawl structured extraction for a single URL.

        Args:
            url: URL to extract from.
            prompt: The natural language instruction for extraction.
            schema: Optional JSON schema dict to enforce structured output.
            timeout_ms: Optional per-call timeout in milliseconds.
            store_in_cache: Whether Firecrawl should store results in cache (default False).

        Returns:
            Parsed `data` from Firecrawl response.

        Raises:
            FirecrawlExtractionError: If Firecrawl returns no/empty data (this is retried).
        """
        with _concurrency_limiter:
            result = self.app.extract(
                urls=[url],
                prompt=prompt,
                schema=schema,
                timeout=timeout_ms,
                scrape_options=ScrapeOptions(
                    store_in_cache=store_in_cache,
                    wait_for=5000,
                ),
            )

            if not result or not hasattr(result, "data"):
                raise FirecrawlExtractionError("Firecrawl extract returned no data")

            if result.data is None:
                raise FirecrawlExtractionError("Firecrawl extract returned data=None")

            return result.data

    def scrape_with_json_mode(
        self,
        url: str,
        schema: dict[str, Any] | None = None,
        prompt: str | None = None,
        timeout_ms: int = 120000,
        only_main_content: bool = False,
        store_in_cache: bool = False,
    ) -> dict[str, Any] | None:
        """Scrape a URL and extract structured JSON data using Firecrawl v2 API.

        Uses the /scrape endpoint with JSON mode to extract structured data.
        Either `schema` or `prompt` (or both) should be provided.

        Args:
            url: URL to scrape and extract from.
            schema: Optional JSON schema dict (OpenAI format) to enforce structured output.
                    Can be generated from a Pydantic model using `Model.model_json_schema()`.
            prompt: Optional natural language prompt to guide extraction.
                    If no schema is provided, the LLM chooses the structure.
            timeout_ms: Per-call timeout in milliseconds (default 120000 = 2 minutes).
            only_main_content: Whether to extract only main content (default False).
            store_in_cache: Whether Firecrawl should store results in cache (default False).

        Returns:
            The extracted JSON data from the response.

        Raises:
            FirecrawlExtractionError: If Firecrawl returns no/empty JSON (this is retried).
        """
        if not schema and not prompt:
            raise ValueError("Either 'schema' or 'prompt' must be provided")

        # Build the format object for v2 API
        json_format: dict[str, Any] = {"type": "json"}
        if schema:
            json_format["schema"] = schema
        if prompt:
            json_format["prompt"] = prompt

        with _concurrency_limiter:
            result = self.app.scrape(
                url=url,
                formats=[json_format],
                only_main_content=only_main_content,
                timeout=timeout_ms,
                store_in_cache=store_in_cache,
            )

            if not result or not hasattr(result, "json"):
                raise FirecrawlExtractionError("Firecrawl scrape returned no json")

            if result.json is None:
                raise FirecrawlExtractionError("Firecrawl scrape returned json=None")

            return result.json
