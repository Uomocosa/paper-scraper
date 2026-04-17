import tomllib
from dataclasses import dataclass

from loguru import logger
from pyalex import Works, Concepts, Topics
from paper_scraper import OpenAlex

OpenAlexOptions = OpenAlex.Options.Options


@dataclass
class Filter:
    topics: list[str] | None = None
    year_min: int | None = None
    year_max: int | None = None
    open_access_only: bool = True
    max_papers: int = 100


def get_dois_from_filter(filter: Filter) -> list[str]:
    assert filter.topics, "Topics must be provided to search for papers"
    concept_ids, topic_ids = get_concept_and_topic_ids(filter)

    query = Works()
    if topic_ids:
        query = query.filter(topics={"id": topic_ids})
    if concept_ids:
        query = query.filter(concepts={"id": concept_ids})

    if filter.year_min and filter.year_max:
        query = query.filter(
            from_publication_date=f"{filter.year_min}-01-01",
            to_publication_date=f"{filter.year_max}-12-31",
        )
    elif filter.year_min:
        query = query.filter(from_publication_date=f"{filter.year_min}-01-01")
    elif filter.year_max:
        query = query.filter(to_publication_date=f"{filter.year_max}-12-31")

    if filter.open_access_only:
        query = query.filter(is_oa=True)

    results = query.get(per_page=filter.max_papers)

    dois = []
    for work in results:
        doi = work.get("doi")
        if doi:
            dois.append(doi)

    logger.info(f"Found {len(dois)} DOIs from filter")
    return dois


def get_concept_and_topic_ids(filter: Filter) -> tuple[list[str], list[str]]:
    concept_ids = []
    topic_ids = []
    for topic_id in filter.topics:
        if topic_id.startswith("C"):
            results = Concepts().filter(openalex=topic_id).get(per_page=1)
            if results:
                concept = results[0]
                concept_full_id = concept["id"].replace("https://openalex.org/", "")
                concept_ids.append(concept_full_id)
                logger.info(
                    f"Concept: {concept['display_name']} -> concepts.id:{concept_full_id}"
                )
            else:
                logger.warning(f"Concept not found: {topic_id}")
        elif topic_id.startswith("T"):
            topic = Topics()[topic_id]
            logger.info(f"Topic: {topic['display_name']}")
            topic_ids.append(topic_id)
        else:
            logger.warning(f"Unknown ID format: {topic_id}, treating as topic")
            topic_ids.append(topic_id)
    return concept_ids, topic_ids



def test_usage():
    f = Filter(topics=["T11948"], max_papers=10)
    dois = get_dois_from_filter(f)
    logger.info(f"Found {len(dois)} DOIs: {dois}")


def test_concept_id():
    f = Filter(topics=["C185592680"], max_papers=10)
    dois = get_dois_from_filter(f)
    logger.info(f"Found {len(dois)} DOIs from concept ID: {dois}")
