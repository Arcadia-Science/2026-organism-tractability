import click
from organism_tractability.db.features import FeaturesPipeline


@click.group()
def cli() -> None:
    """CLI for tractability feature fetching (publication snapshot)."""


@cli.command("get-features")
@click.option(
    "--input",
    "input_csv",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=str),
    help="Path to input CSV (requires: organism_scientific_name, organism_id).",
)
@click.option(
    "--output",
    "output_csv",
    required=True,
    type=click.Path(dir_okay=False, path_type=str),
    help="Path to output CSV to write.",
)
@click.option(
    "--source-ids",
    "-s",
    multiple=True,
    help="Optional source IDs to fetch (repeatable). If omitted, fetches all sources.",
)
def get_features_cli(input_csv: str, output_csv: str, source_ids: tuple[str, ...]) -> None:
    """Fetch features for organisms from an input CSV and write an output CSV.

    Example:
        python -m organism_tractability.db.cli get-features \\
          --input input/example_organisms.csv \\
          --output output/features.csv
    """
    pipeline = FeaturesPipeline()
    pipeline.run_csv(
        input_csv_path=input_csv,
        output_csv_path=output_csv,
        source_ids=list(source_ids) if source_ids else None,
    )


cli()
