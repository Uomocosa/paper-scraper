# import tyro
# from loguru import logger

# import paper_scraper
# from paper_scraper.OpenAlex.get_dois_from_filter import (
#     Filter,
#     get_dois_from_filter,
#     load_config,
#     apply_cli_overrides,
# )
# from paper_scraper.OpenAlex.get_reference_dois import from_dois
# from paper_scraper.OpenAlex.download_papers_from_dois import download_papers_from_dois
# from paper_scraper.OpenAlex import Options as OpenAlexOptions
# from paper_scraper.Utils.extract_dois_from_json import extract_dois_from_json
# from paper_scraper.__global__ import EXTRACTED_REFERENCES


# def main(
#     mode: str = "recursive",
#     topics: list[str] | None = None,
#     year_min: int | None = None,
#     year_max: int | None = None,
#     open_access_only: bool | None = None,
#     max_papers: int = 100,
#     depth: int = 0,
# ):
#     """Download papers from OpenAlex.

#     Args:
#         mode: Download mode - "recursive" (from seed refs) or "search" (by filters).
#         topics: OpenAlex topic/concept IDs for search, e.g. ["C1264102"] or ["T11948"].
#         year_min: Minimum publication year (search mode).
#         year_max: Maximum publication year (search mode).
#         open_access_only: Only open access papers (search mode).
#         max_papers: Maximum papers to download (search mode).
#         depth: Recursion depth (recursive mode).
#     """
#     openalex_options = OpenAlexOptions()

#     if mode == "search":
#         filter = load_config()
#         apply_cli_overrides(
#             filter, topics, year_min, year_max, open_access_only, max_papers
#         )
#         dois = get_dois_from_filter(filter)
#         logger.info(f"Found {len(dois)} DOIs from filter")
#         download_papers_from_dois(dois, openalex_options)
#     else:
#         dois = load_extracted_references()
#         logger.info(f"Found {len(dois)} DOIs to download")
#         if depth > 0:
#             reference_dois = from_dois(dois, openalex_options, depth=depth)
#             logger.info(f"Found {len(reference_dois)} reference DOIs")
#         else:
#             download_papers_from_dois(dois, openalex_options)


# def load_extracted_references() -> list[str]:
#     if not EXTRACTED_REFERENCES.exists():
#         logger.warning(f"No extracted references found at {EXTRACTED_REFERENCES}")
#         return []

#     with open(EXTRACTED_REFERENCES, "r") as f:
#         papers_json = f.read()

#     dois = extract_dois_from_json(papers_json)
#     return dois


# def test_usage():
#     main(mode="recursive", depth=0)


# def test_search():
#     main(mode="search", topics=["T11948"], year_min=2022, max_papers=10)
