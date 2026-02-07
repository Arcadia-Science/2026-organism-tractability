from urllib.parse import quote

from pydantic import BaseModel, Field, ValidationError

from organism_tractability.utils.FirecrawlClient import FirecrawlClient
from organism_tractability.utils.rate_limiter import retry_with_backoff

ATCC_SEARCH_EXTRACT_PROMPT: str = """
Extract all product cards visible on the ATCC search results page.

If you see "No results for <query organism name>" or similar no-results message,
return total_results as 0 and products as an empty array.
"""

ATCC_PRODUCT_EXTRACT_PROMPT: str = "Extract detailed information from the ATCC product detail page."


class AtccProduct(BaseModel):
    """Product card from ATCC search results."""

    url: str | None = Field(
        None, description="The product detail page URL e.g. https://www.atcc.org/products/9765"
    )


class AtccSearchResults(BaseModel):
    """Search results from ATCC."""

    url: str | None = Field(None, description="The search URL that was used")
    products: list[AtccProduct] = Field(default_factory=list, description="List of products")
    total_results: int | None = Field(
        None,
        description=(
            "The total number of results displayed at the top of the page e.g. from text "
            "like 'Results 145-192 of 25,559 for Saccharomyces cerevisiae'. "
            "IMPORTANT: When extracting numbers, handle thousands separators (commas) correctly. "
            "For example, '25,559' should be extracted as 25559 (not 25). "
            "If not present, count the number of products on the page and return that as "
            "the total_results."
        ),
    )


class AtccProductDetail(BaseModel):
    """Detailed product information from ATCC product page."""

    name: str | None = Field(
        None, description="The product name e.g., 'Chlorella vulgaris Beijerinck'"
    )
    atcc_id: str | None = Field(None, description="The ATCC identifier e.g., '9765'")
    bioz_stars: str | None = Field(None, description="The Bioz score text e.g., '94/100'")
    product_citations: int | None = Field(None, description="Number of citations e.g., '31'")
    product_category: str | None = Field(None, description="Product category, e.g., 'Protists'")
    product_type: str | None = Field(None, description="Product type, e.g., 'Algae'")
    classification: str | None = Field(None, description="Classification, e.g., 'KINGDOM: Plantae'")
    strain_designation: str | None = Field(None, description="Strain designation, e.g., 'L-756a'")
    type_strain: str | None = Field(None, description="Type strain, e.g., 'Yes' or 'No'")
    applications: list[str] | None = Field(
        None,
        description="Applications, e.g., ['Biofuel production', 'Food production research']",
    )
    product_format: str | None = Field(None, description="Product format, e.g., 'Frozen'")
    storage_conditions: str | None = Field(None, description="Storage conditions and requirements")
    bsl_level: str | None = Field(None, description="The biosafety level text e.g. 'BSL 1'")
    price: str | None = Field(
        None,
        description=(
            "Price text for the product. If a price cannot be found, set it to null. "
            "Do not guess or default to '0'."
        ),
    )
    # TODO (Ahmed): I have found this in_stock field to be not reliable. Will need to find a better
    # way to determine if the product is in stock.
    in_stock: bool | None = Field(
        None,
        description=(
            "Boolean stock flag based on availability. Rules: 1) If mission_collection_item "
            "is true, then in_stock must be false. 2) An item that is out of stock may still "
            "show 'Buy Now' or 'Add to Cart' text/button. It will have buttons that show "
            "'Notify Me When Available' "
            "or show 'This item is currently not in stock. We cannot estimate a shipment date for "
            "this item.'. 3) For an item that is in_stock, it would show 'Generally ships within X "
            "business days'. 4) An item that shows 'limited inventory' is in stock. Otherwise, "
            "set in_stock to true."
        ),
    )
    mission_collection_item: bool | None = Field(
        None,
        description=(
            "Boolean flag indicating Mission Collection items: Set to true if the product "
            "card contains the phrase 'This is a Mission Collection Item' OR if there is a Mission "
            "Collection CTA link or a button saying 'Check Purchase Information'. Otherwise, set "
            "to false."
        ),
    )


class ATCCClient:
    """Client for scraping ATCC website."""

    def __init__(self):
        """Initialize the ATCC client."""
        self.firecrawl_client = FirecrawlClient()

    def _build_page_urls(
        self,
        query: str,
        num_pages: int = 1,
        results_per_page: int = 12,
        filter_products: bool = True,
        filter_organism: bool = False,
    ) -> list[str]:
        """
        Build ATCC search URLs using hash offset pagination.

        An example URL with both filters:
        https://www.atcc.org/search#q=Saccharomyces%20cerevisiae&sort=relevancy&numberOfResults=48
        &f:Contenttype=%5BProducts%5D
        &f:Organism=%5BSaccharomyces%20cerevisiae%5D

        Args:
            query: The search query string of the organism.
            num_pages: Number of pages to generate URLs for. Defaults to 1.
            results_per_page: Number of results per page. Defaults to 12.
            filter_products: Whether to filter for products. Defaults to True.
            filter_organism: Whether to filter for the organism. Defaults to False.

        Returns:
            List of ATCC search result page URLs.
        """
        enc_q = quote(query, safe="")
        base = "https://www.atcc.org/search"
        urls: list[str] = []
        for i in range(num_pages):
            offset = i * results_per_page
            # First page does not include &first=
            first_param = f"&first={offset}" if offset > 0 else ""
            urls.append(
                f"{base}#q={enc_q}{first_param}&sort=relevancy&numberOfResults={results_per_page}"
                f"{'&f:Contenttype=%5BProducts%5D' if filter_products else ''}"
                f"{f'&f:Organism=%5B{enc_q}%5D' if filter_organism else ''}"
            )
        return urls

    @retry_with_backoff(max_attempts=4, min_wait=5.0, max_wait=60.0, retry_on=(Exception,))
    def search_products(
        self, query: str, num_pages: int = 1, results_per_page: int = 12
    ) -> AtccSearchResults | None:
        """
        Extract ATCC search results for a given query.

        Args:
            query: The search query string of the organism.
            num_pages: Number of pages to extract. Defaults to 1.
            results_per_page: Number of results per page. Defaults to 12.

        Returns:
            AtccSearchResults object containing search results, or None if extraction fails.
        """
        urls = self._build_page_urls(
            query=query, num_pages=num_pages, results_per_page=results_per_page
        )
        # TODO: This method is designed to only work with 1 page (num_pages=1).
        # If num_pages > 1, only the first page is processed. To support multiple pages,
        # we would need to accumulate results from all pages instead of overwriting data.
        first_url = urls[0] if urls else None

        if not first_url:
            return None

        try:
            data = self._search_products_extract(url=first_url)
            data["url"] = first_url
            return AtccSearchResults.model_validate(data)
        except ValidationError as e:
            # Treat schema/parse failures as extraction failures (do not coerce to "0 results")
            raise RuntimeError(
                f"ATCC search extraction validation failed for url={first_url}"
            ) from e

    def _search_products_extract(self, url: str) -> dict:
        data = self.firecrawl_client.extract(
            url=url,
            prompt=ATCC_SEARCH_EXTRACT_PROMPT,
            schema=AtccSearchResults.model_json_schema(),
        )
        if data is None:
            # Shouldn't happen: FirecrawlClient now raises on missing data, but keep a guard.
            raise RuntimeError("ATCC search extraction returned None")
        if not isinstance(data, dict):
            raise RuntimeError(f"ATCC search extraction returned unexpected type: {type(data)}")
        return data

    @retry_with_backoff(max_attempts=4, min_wait=5.0, max_wait=60.0, retry_on=(Exception,))
    def get_product(self, url: str) -> AtccProductDetail | None:
        """
        Extract detailed information from an ATCC product detail page.

        Args:
            url: The product detail page URL.

        Returns:
            AtccProductDetail object containing extracted product details, or None if extraction
            fails.
        """
        data = self._get_product_extract(url=url)
        try:
            return AtccProductDetail.model_validate(data)
        except ValidationError as e:
            raise RuntimeError(f"ATCC product extraction validation failed for url={url}") from e

    def _get_product_extract(self, url: str) -> dict:
        data = self.firecrawl_client.extract(
            url=url,
            prompt=ATCC_PRODUCT_EXTRACT_PROMPT,
            schema=AtccProductDetail.model_json_schema(),
        )
        if data is None:
            raise RuntimeError("ATCC product extraction returned None")
        if not isinstance(data, dict):
            raise RuntimeError(f"ATCC product extraction returned unexpected type: {type(data)}")
        return data
