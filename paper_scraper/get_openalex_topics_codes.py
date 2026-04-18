from pyalex import Topics
from dataclasses import dataclass, field

from paper_scraper import OpenAlex
OpenAlexOptions = OpenAlex.Options.Options

@dataclass
class Config:
    search_term: str
    top_n: int = 15
    openalex_opts: OpenAlexOptions = field(default_factory=OpenAlexOptions)


def get_openalex_topics_codes(config: Config) -> dict[str, str]:
    """
    Searches OpenAlex for a topic and returns a dictionary of {topic_name: code}.
    
    Args:
        search_term: The string you would type into the OpenAlex search bar.
        top_n: Number of top results to fetch (default: 5).
        
    Returns:
        A dictionary mapping the topic display name to its OpenAlex ID (e.g., 'T12345').
    """
    config.openalex_opts.setup_pyalex_key()
    topic_dict = {}
    
    # Search the topics database
    results = Topics().search(config.search_term).get(per_page=config.top_n)
    
    for topic in results:
        # Extract the ID by stripping the URL portion
        topic_id = topic["id"].replace("https://openalex.org/", "")
        topic_name = topic["display_name"]
        
        topic_dict[topic_name] = topic_id
        
    return topic_dict


def main(config: Config):
    results_dict = get_openalex_topics_codes(config)
    print(f">>> Results for '{config.search_term}':")
    for name, code in results_dict.items():
        print(f">>  '{name}': {code}")


def test_usage():
    main(Config(
        search_term="Wastewater treatment",
        top_n=5
    ))
