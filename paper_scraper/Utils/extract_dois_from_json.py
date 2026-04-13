import json
from loguru import logger

def extract_dois_from_json(json_str: str) -> list[str]:
    papers = json.loads(json_str) 
    dois = []
    for paper in papers:
        doi = paper.get("doi")
        if doi:
            dois.append(doi)
    return dois


def test_usage():
    papers_json = """
    [
        {
            "title": "The Maximum Reservoir Capacity of Soils for Persistent Organic Pollutants: Implications for Global Cycling",
            "doi": "10.1016/j.envpol.2004.07.011"
        },
        {
            "title": "Pharmaceutical Wastewater as Emerging Contaminants (EC): Treatment Technologies, Impact on Environment and Human Health",
            "doi": "10.1016/j.nexus.2022.100076"
        },
        {
            "title": "Fate of Estrogenic Hormones in Wastewater and Sludge Treatment: A Review of Properties and Analytical Detection Techniques in Sludge Matrix",
            "doi": "10.1016/j.watres.2012.08.002"
        }
    ]
    """
    dois = extract_dois_from_json(papers_json)
    logger.info(dois)
