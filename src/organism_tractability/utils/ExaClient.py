import os
from typing import Any

import requests
from pydantic import BaseModel

from organism_tractability.utils.rate_limiter import RateLimiter, retry_with_backoff

# Exa API allows 5 queries per second
_rate_limiter = RateLimiter(calls_per_second=5)


class Citation(BaseModel):
    """Pydantic model representing a citation from the Exa answer API."""

    id: str
    title: str
    url: str
    snippet: str | None = None
    image: str | None = None
    publishedDate: str | None = None
    score: float | None = None
    favicon: str | None = None


class ExaClient:
    """A generic class for calling the Exa API.

    This class uses requests to call the Exa API instead of the exa_py library. The former returns a
    json while the latter returns an AnswerResponse object, which requires manual conversion to a
    json. Erring towards flexibility for the time being.

    """

    def __init__(self):
        """
        Initialize the ExaClient class.
        """
        self.api_key = os.environ.get("EXA_API_KEY")
        self.headers = {"x-api-key": self.api_key}

    # TODO (Ahmed): We may want to limit this to trusted scientific domains e.g. pubmed.
    # TODO (Ahmed): Add arg for grabbing the full contents of the results.
    # TODO (Ahmed): Return a typed dictionary.
    @retry_with_backoff(max_attempts=5, min_wait=1.0, max_wait=60.0)
    def search(self, query: str, num_results: int = 10, **kwargs) -> dict[Any, Any]:
        """
        Perform a search using the Exa API.

        Args:
            query: The search query string
            num_results: Number of results to return (default: 10)
            **kwargs: Additional parameters to pass to search

        Returns:
            Dictionary containing search results
        """
        _rate_limiter.wait()
        response = requests.post(
            "https://api.exa.ai/search",
            headers=self.headers,
            json={"query": query, "num_results": num_results, **kwargs},
        )
        response.raise_for_status()
        return response.json()

    @retry_with_backoff(max_attempts=5, min_wait=1.0, max_wait=60.0)
    def answer(
        self,
        query: str,
        system_prompt: str | None = None,
        model: str | None = None,
        output_schema: dict[str, Any] | None = None,
        **kwargs,
    ) -> dict[Any, Any]:
        """
        Generate an answer to a query using Exa's Answer API endpoint (search + LLM).

        Args:
            query: The query to answer
            system_prompt: A system prompt to guide the LLM's behavior (optional)
            model: The model to use for answering (optional, e.g., 'exa', 'exa-pro')
            output_schema: JSON schema describing the desired answer structure (optional)
            **kwargs: Additional parameters to pass to the answer method

        Returns:
            Dictionary containing the answer and citations
        """
        _rate_limiter.wait()
        payload = {
            "query": query,
            "system_prompt": system_prompt,
            "model": model,
            "output_schema": output_schema,
            **kwargs,
        }
        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        response = requests.post("https://api.exa.ai/answer", headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()
