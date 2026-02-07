## Public (archived) tractability pipeline

This repository snapshot is configured for **CSV-in / CSV-out** feature fetching.

### Adding a new source / feature (public version)

1. Add a client + source function under `src/organism_tractability/sources/<source_id>/`.
   - Tip: Look at existing sources (e.g. `src/organism_tractability/sources/ncbi/`, `.../atcc/`, `.../protocols_io/`) to infer the expected structure and the standardized `get_<source_id>(organism_id, organism_scientific_name, feature_metadata)` signature.
2. Add one or more entries to `src/organism_tractability/db/feature_metadata/feature_metadata.yaml`.
3. Register the source in `src/organism_tractability/db/features/pipeline.py` under `SOURCE_REGISTRY`.
4. Run the main pipeline CLI (documented in the repo root `README.md`).