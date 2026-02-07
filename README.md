# 2026-organism-tractability

This repository is an **archived** code snapshot accompanying the paper **“A tractability atlas for experimental organism selection”**.

- **Paper**: `https://thestacks.org/publications/resource-tractability-atlas`
- **Raw dataset (Zenodo)**: `https://doi.org/10.5281/zenodo.18491198` ([Zenodo record](https://doi.org/10.5281/zenodo.18491198))
- **Interface (searchable table)**: `https://organism-tractability-data.arcadiascience.com`
- **Visual map**: `https://organism-tractability.arcadiascience.com`

We plan to refresh the **data** periodically; this **code repo** is not intended to be updated.

## What this code does

Given a list of organisms, this code fetches tractability features across **four domains**:
- Community
- Logistics
- Throughput
- Tooling

Features are defined in:
- `src/organism_tractability/db/feature_metadata/feature_metadata.yaml`

## Setup

This repo uses `uv`.

```sh
brew install uv
uv sync
source .venv/bin/activate
```

### API keys

Populate required keys in `.env` (see `.env.example`):
- **NCBI**: `NCBI_API_KEY`, `NCBI_API_EMAIL`
- **ATCC** (scraping): `FIRECRAWL_API_KEY`
- **Exa Answer**: `EXA_API_KEY`
- **protocols.io**: `PROTOCOLS_IO_API_CLIENT_ACCESS_TOKEN`
- **NIH RePORTER**: no key required

## Input CSV contract

The features pipeline reads a CSV with these columns:
- **organism_scientific_name**: e.g. `Escherichia coli`
- **organism_id**: taxonomy id (integer). **UniProt taxonomy id == NCBI taxonomy id (taxid)**.

Example input file:
- `input/example_organisms.csv`

## Run: fetch all features for all organisms

```sh
python -m organism_tractability.db.cli get-features \\
  --input input/example_organisms.csv \\
  --output output/features.csv
```

You can optionally restrict sources:

```sh
python -m organism_tractability.db.cli get-features \\
  --input input/example_organisms.csv \\
  --output output/features.csv \\
  -s ncbi -s protocols_io
```

The implementation lives in:
- `src/organism_tractability/db/features/pipeline.py` (`FeaturesPipeline.run_csv`)

## Output CSV contract

The pipeline writes **one row per (organism, feature)** pair.

Output columns:
- **organism_id**: taxonomy id
- **feature_id**
- **source_id**
- **fetched_object**: JSON string (the raw returned object)

Example output row (illustrative):

```csv
organism_id,feature_id,source_id,fetched_object
562,pubmed,ncbi,"{""search_url"":""https://pubmed.ncbi.nlm.nih.gov/?term=%22Escherichia%22%20AND%20%22coli%22&sort=date&ac=yes"",""count"":123456}"
```

## Run sources directly (per organism)

Each source can also be queried directly:

```sh
python -m organism_tractability.sources.cli get-ncbi -n "Escherichia coli" -i 562
python -m organism_tractability.sources.cli get-atcc -n "Escherichia coli"
python -m organism_tractability.sources.cli get-nih-reporter -n "Escherichia coli"
python -m organism_tractability.sources.cli get-protocols-io -n "Escherichia coli"
python -m organism_tractability.sources.cli get-exa-answer -n "Escherichia coli"
```

## Sources

| Source | Notes | Required API key(s) |
|---|---|---|
| NCBI | Entrez E-utilities searches across multiple NCBI databases | `NCBI_API_KEY`, `NCBI_API_EMAIL` |
| ATCC | Scrapes ATCC search + product pages | `FIRECRAWL_API_KEY` |
| Exa Answer | Web search + LLM answer w/ citations + confidence | `EXA_API_KEY` |
| protocols.io | Searches public protocols | `PROTOCOLS_IO_API_CLIENT_ACCESS_TOKEN` |
| NIH RePORTER | Searches NIH-funded projects | None |
