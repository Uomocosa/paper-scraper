from typing import Literal
from paper_scraper.Ollama import get_handle_pdf_function

HandlePDFType = Literal[tuple(get_handle_pdf_function.FUNCTIONS.keys())]

def test_():
    print(HandlePDFType)
