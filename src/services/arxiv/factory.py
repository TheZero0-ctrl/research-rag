from src.config import settings
from src.services.arxiv.client import ArxivClient

def make_arxiv_client() -> ArxivClient:
    """Factory function to create an arxiv client instance.
    :return: An instance of ArxivClient
    :rtype: ArxivClient
    """
    
    client = ArxivClient(settings.arxiv)
    return client

