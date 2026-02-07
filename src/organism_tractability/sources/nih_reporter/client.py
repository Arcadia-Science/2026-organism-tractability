import requests
from pydantic import BaseModel

from organism_tractability.utils.rate_limiter import RateLimiter, retry_with_backoff

BASE_URL = "https://api.reporter.nih.gov/v2"

# NIH RePORTER rate limit: no more than one URL request per second
# https://api.reporter.nih.gov/
_rate_limiter = RateLimiter(calls_per_second=1)


# Cherry-picked fields from the NIH RePORTER API documentation:
# https://api.reporter.nih.gov/documents/Data%20Elements%20for%20RePORTER%20Project%20API_V2.pdf
class Organization(BaseModel):
    """Organization information from NIH RePORTER."""

    org_name: str | None = None
    org_country: str | None = None


class PrincipalInvestigator(BaseModel):
    """Principal Investigator information from NIH RePORTER."""

    profile_id: int | None = None
    full_name: str | None = None
    title: str | None = None


class NIHProject(BaseModel):
    """Simplified NIH project information."""

    fiscal_year: int | None = None
    organization: Organization | None = None
    award_amount: float | None = None
    is_active: bool | None = None
    principal_investigators: list[PrincipalInvestigator] | None = None
    project_start_date: str | None = None
    project_end_date: str | None = None
    project_title: str | None = None
    phr_text: str | None = None
    project_detail_url: str | None = None


class SearchMetaProperties(BaseModel):
    """Search metadata properties from NIH RePORTER."""

    URL: str | None = None


class SearchMeta(BaseModel):
    """Search metadata from NIH RePORTER."""

    total: int
    properties: SearchMetaProperties


class SearchResponse(BaseModel):
    """NIH RePORTER search response."""

    meta: SearchMeta
    results: list[NIHProject]


class NIHReporterClient:
    """Generic client for NIH RePORTER API."""

    def __init__(self):
        """Initialize the client."""
        self.session = requests.Session()
        self.session.headers.update(
            {"Content-Type": "application/json", "Accept": "application/json"}
        )

    # TODO (Ahmed): As a followup to search_projects(), add a method to fetch
    # principal investigator information by profile_id. This will be helpful
    # in building a "phonebook" of principal investigators for given species,
    # ones we may want to reach out to.

    # TODO (Ahmed): Currently, we only make a single API call to return the first 10 results on
    # the first page. Extend to support pagination using the offset parameter.
    @retry_with_backoff(max_attempts=5, min_wait=1.0, max_wait=60.0)
    def search_projects(self, query: str, limit: int = 10, offset: int = 0) -> SearchResponse:
        """
        Search for NIH projects by query term.

        Args:
            query: Search query term
            limit: Number of results per page (max: 500 as per API docs, default: 10)
            offset: Starting position (default: 0)

        Returns:
            SearchResponse with typed project data

        Note:
            The order of results returned by this API may differ from the order shown
            in the NIH RePORTER web interface. The total number of results is the same,
            but the sorting logic is different. In the API, we enforce most recent results first
            by project start date.

        See:
            https://api.reporter.nih.gov/ and
            https://api.reporter.nih.gov/documents/Data%20Elements%20for%20RePORTER%20Project%20API_V2.pdf
        """
        _rate_limiter.wait()
        payload = {
            "criteria": {
                "use_relevance": True,
                "advanced_text_search": {
                    "operator": "and",
                    "search_field": "projecttitle,abstracttext,terms",
                    "search_text": query,
                },
            },
            "offset": offset,
            "limit": limit,
            "sort_field": "project_start_date",
            "sort_order": "desc",
        }

        response = self.session.post(f"{BASE_URL}/projects/search", json=payload)
        response.raise_for_status()
        data = response.json()
        return SearchResponse.model_validate(data)
