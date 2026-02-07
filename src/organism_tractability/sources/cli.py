import click

from organism_tractability.db.feature_metadata import FeatureMetadataService
from organism_tractability.sources.atcc import search_and_get_atcc_products
from organism_tractability.sources.exa_answer.exa_answer import answer_organism_query
from organism_tractability.sources.ncbi import get_ncbi
from organism_tractability.sources.nih_reporter import search_nih_reporter_projects
from organism_tractability.sources.protocols_io import search_public_protocols


@click.group()
def cli() -> None:
    pass


DEFAULT_ORGANISM_SCIENTIFIC_NAME = "Chlorella vulgaris"
DEFAULT_ORGANISM_ID = 3077

METADATA_SERVICE = FeatureMetadataService()


@cli.command("get-protocols-io")
@click.option(
    "--organism-scientific-name",
    "-n",
    default=DEFAULT_ORGANISM_SCIENTIFIC_NAME,
    help="Scientific name of the organism to search protocols.io for",
)
def get_protocols_dot_io_cli(organism_scientific_name: str) -> None:
    """
    Search protocols.io for organism-related protocols.

    Example:
        python -m organism_tractability.sources.cli get-protocols-io -n "Escherichia coli"
    """
    result = search_public_protocols(organism_scientific_name=organism_scientific_name)
    click.echo(result.model_dump_json(indent=2))


@cli.command("get-ncbi")
@click.option(
    "--organism-scientific-name",
    "-n",
    type=str,
    default=DEFAULT_ORGANISM_SCIENTIFIC_NAME,
    help="Scientific name of the organism to get NCBI info for",
)
@click.option(
    "--organism-id",
    "-i",
    type=int,
    default=DEFAULT_ORGANISM_ID,
    help="Taxonomy ID of the organism to get NCBI info for",
)
def get_ncbi_cli(organism_scientific_name: str, organism_id: int) -> None:
    """
    Analyze an organism using NCBI data sources.

    Both organism name and taxonomy ID are required. Different databases use
    different query types (name vs ID) based on their configuration.

    Example:
        python -m organism_tractability.sources.cli get-ncbi -n "Escherichia coli" -i 562
    """
    # Get the first NCBI feature for the CLI (default behavior)

    ncbi_features = METADATA_SERVICE.get_feature_metadata_by_source("ncbi")
    default_feature_metadata = ncbi_features[0]

    result = get_ncbi(
        organism_id=organism_id,
        organism_scientific_name=organism_scientific_name,
        feature_metadata=default_feature_metadata,
    )
    click.echo(result.model_dump_json(indent=2))


@cli.command("get-nih-reporter")
@click.option(
    "--organism-scientific-name",
    "-n",
    default=DEFAULT_ORGANISM_SCIENTIFIC_NAME,
    help="Scientific name of the organism to search NIH RePORTER for",
)
def get_nih_reporter_cli(organism_scientific_name: str) -> None:
    """
    Search NIH RePORTER for projects related to a specific organism.

    Example:
        python -m organism_tractability.sources.cli get-nih-reporter -n "Escherichia coli"
    """
    result = search_nih_reporter_projects(organism_scientific_name)

    click.echo(
        f"Found {result.meta.total} projects for '{organism_scientific_name}' "
        f"@ {result.meta.properties.URL}"
    )
    click.echo(f"Returned {len(result.results)} results")
    click.echo(result.model_dump_json(indent=2))


@cli.command("get-atcc")
@click.option(
    "--organism-scientific-name",
    "-n",
    default=DEFAULT_ORGANISM_SCIENTIFIC_NAME,
    help="Scientific name of the organism to search ATCC for",
)
def get_atcc_cli(organism_scientific_name: str) -> None:
    """
    Search ATCC for organism products and extract details.

    Example:
        python -m organism_tractability.sources.cli get-atcc -n "Escherichia coli"
    """
    result = search_and_get_atcc_products(organism_scientific_name)
    click.echo(result.model_dump_json(indent=2))


@cli.command("get-exa-answer")
@click.option(
    "--organism-scientific-name",
    "-n",
    default=DEFAULT_ORGANISM_SCIENTIFIC_NAME,
    help="Scientific name of the organism to get Exa answer for",
)
def get_exa_answer_cli(organism_scientific_name: str) -> None:
    """
    Search the web to answer specific queries using the ExaClient.

    Example:
        python -m organism_tractability.sources.cli get-exa-answer -n "Escherichia coli"
    """

    exa_answer_features = METADATA_SERVICE.get_feature_metadata_by_source("exa_answer")
    default_feature_metadata = exa_answer_features[0]
    result = answer_organism_query(
        organism_scientific_name=organism_scientific_name,
        feature_metadata=default_feature_metadata,
    )
    click.echo(result.model_dump_json(indent=2))


cli()
