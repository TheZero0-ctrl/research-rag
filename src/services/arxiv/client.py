import asyncio
import httpx
import logging
import time

from functools import cached_property
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote, urlencode
import xml.etree.ElementTree as ET

from src.config import ArxivSettings
from src.exceptions import ArxivAPIException, ArxivAPITimeoutError, ArxivParseError, PDFDownloadException, PDFDownloadTimeoutError
from src.schemas.arxiv.paper import ArxivPaper

logger = logging.getLogger(__name__)


class ArxivClient:
    """Client for fetching papers from arXiv API."""

    def __init__(self, settings: ArxivSettings):
        self._settings = settings
        self._last_request_time: Optional[float] = None

    @cached_property
    def pdf_cache_dir(self) -> Path:
        """PDF cache directory."""
        cache_dir = Path(self._settings.pdf_cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    @property
    def base_url(self) -> str:
        return self._settings.base_url

    @property
    def namespaces(self) -> dict:
        return self._settings.namespaces

    @property
    def rate_limit_delay(self) -> float:
        return self._settings.rate_limit_delay

    @property
    def timeout_seconds(self) -> int:
        return self._settings.timeout_seconds

    @property
    def max_results(self) -> int:
        return self._settings.max_results

    @property
    def search_category(self) -> str:
        return self._settings.search_category

    async def fetch_papers(
        self,
        max_results: Optional[int] = None,
        start: int = 0,
        sort_by: str = "submittedDate",
        sort_order: str = "descending",
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> List[ArxivPaper]:
        """
        Fetch papers from arXiv for the given category.

        Args:
            max_results: Maximum number of results to fetch. Defaults to None.
            start: Starting index for fetching results. Defaults to 0.
            sort_by: Field to sort by. Defaults to "submittedDate".
            sort_order: Sort order. Defaults to "descending" (ascending, descending).
            from_date: Starting date for fetching results. Defaults to None. (format: YYYYMMDD)
            to_date: Ending date for fetching results. Defaults to None. (format: YYYYMMDD)
        """

        if max_results is None:
            max_results = self.max_results

        # build the search query
        search_query = f"cat:{self.search_category}"

        # Add date filtering if provided
        if from_date or to_date:
            date_from = f"{from_date}0000" if from_date else "*"
            date_to = f"{to_date}0000" if to_date else "*"
            search_query += f" AND submittedDate:[{date_from}+TO+{date_to}]"

        params = {
            "search_query": search_query,
            "start": start,
            "max_results": max_results,
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }

        safe = ":+[]"
        url = f"{self.base_url}?{urlencode(params, quote_via=quote, safe=safe)}"

        try:
            logger.info(f"Fetching {max_results} {self.search_category} papers from arXiv")

            if self._last_request_time is not None:
                time_since_last = time.time() - self._last_request_time

                if time_since_last < self.rate_limit_delay:
                    sleep_time = self.rate_limit_delay - time_since_last
                    await asyncio.sleep(sleep_time)

            self._last_request_time = time.time()

            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url)
                response.raise_for_status()

                xlm_data = response.text

            papers = self._parse_response(xlm_data)
            logger.info(f"Query returned {len(papers)} papers")

            return papers
        except httpx.TimeoutException as e:
            logger.error(f"arXiv API timeout: {e}")
            raise ArxivAPITimeoutError(f"arXiv API request timed out: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"arXiv API HTTP error: {e}")
            raise ArxivAPIException(f"arXiv API returned error {e.response.status_code}: {e}")
        except ArxivAPIException:
            raise
        except Exception as e:
            logger.error(f"Failed to fetch papers from arXiv: {e}")
            raise ArxivAPIException(f"Unexpected error fetching papers from arXiv: {e}")

    async def download_pdf(self, paper: ArxivPaper, force_download: bool = False) -> Optional[Path]:
        """
        Download the PDF file for the given paper.
        Args:
            paper: The ArxivPaper object to download the PDF for.
            force_download: If True, download the PDF even if it already exists.
        Returns:
            The path to the downloaded PDF file or None if the download fails.
        """

        if not paper.pdf_url:
            logger.error(f"PDF URL not found for paper {paper.arxiv_id}")
            return None

        pdf_path = self._get_pdf_path(paper.arxiv_id)

        if pdf_path.exists() and not force_download:
            logger.info(f"Using cached PDF: {pdf_path.name}")
            return pdf_path

        # Download with retry
        if await self._download_with_retry(paper.pdf_url, pdf_path):
            return pdf_path
        else:
            return None


    def _parse_response(self, xml_data: str) -> List[ArxivPaper]:
        """
        Parse the XML data and return a list of ArxivPaper objects.

        Args:
            xml_data: The XML data to parse.

        Returns:
            A list of ArxivPaper objects.
        """

        try:
            root = ET.fromstring(xml_data)
            entries = root.findall("atom:entry", self.namespaces)

            papers = []

            for entry in entries:
                paper = self._parse_single_entry(entry)
                if paper:
                    papers.append(paper)

            return papers

        except ET.ParseError as e:
            logger.error(f"Failed to parse arXiv XML response: {e}")
            raise ArxivParseError(f"Failed to parse arXiv XML response: {e}")
        except Exception as e:
            logger.error(f"Unexpected error parsing arXiv response: {e}")
            raise ArxivParseError(f"Unexpected error parsing arXiv response: {e}")

    def _parse_single_entry(self, entry: ET.Element) -> Optional[ArxivPaper]:
        """
        Parse a single arXiv entry and return an ArxivPaper object.

        Args:
            entry: The arXiv entry to parse.

        Returns:
            An ArxivPaper object, or None if the entry is invalid.
        """
        try:
            arxiv_id = self._get_arxiv_id(entry)
            if not arxiv_id:
                return None

            title = self._get_text(entry, "atom:title", clean_newlines=True)
            authors = self._get_authors(entry)
            abstract = self._get_text(entry, "atom:summary", clean_newlines=True)
            published = self._get_text(entry, "atom:published")
            categories = self._get_categories(entry)
            pdf_url = self._get_pdf_url(entry)

            return ArxivPaper(
                arxiv_id=arxiv_id,
                title=title,
                authors=authors,
                abstract=abstract,
                published_date=published,
                categories=categories,
                pdf_url=pdf_url,
            )
        except Exception as e:
            logger.error(f"Failed to parse entry: {e}")
            return None

    def _get_arxiv_id(self, entry: ET.Element) -> Optional[str]:
        """
        Extract the arXiv ID from an arXiv entry.

        Args:
            entry: The arXiv entry to extract the ID from.

        Returns:
            The arXiv ID, or None if not found.
        """
        id_element = entry.find("atom:id", self.namespaces)
        if id_element is None or id_element.text is None:
            return None
        
        return id_element.text.split("/")[-1]

    def _get_text(self, element: ET.Element, path: str, clean_newlines: bool = False) -> str:
        """
        Extract text from an arXiv element.

        Args:
            element: The arXiv element to extract text from.
            path: The path to the text element.
            clean_newlines: Whether to remove newlines from the text.

        Returns:
            the text or empty string
        """
        elem = element.find(path, self.namespaces)
        if elem is None or elem.text is None:
            return ""

        text = elem.text.strip()
        return text.replace("\n", " ") if clean_newlines else text

    def _get_authors(self, entry: ET.Element) -> List[str]:
        """
        Extract authors from an arXiv entry.

        Args:
            entry: The arXiv entry to extract authors from.

        Returns:
            A list of authors.
        """
        authors = []
        for author in entry.findall("atom:author", self.namespaces):
            name = self._get_text(author, "atom:name")
            if name:
                authors.append(name)
        return authors

    def _get_categories(self, entry: ET.Element) -> List[str]:
        """
        Extract categories from entry.

        Args:
            entry: XML entry element

        Returns:
            List of category terms
        """
        categories = []
        for category in entry.findall("atom:category", self.namespaces):
            term = category.get("term")
            if term:
                categories.append(term)
        return categories
    
    def _get_pdf_url(self, entry: ET.Element) -> str:
        """
        Extract PDF URL from entry links.

        Args:
            entry: XML entry element

        Returns:
            PDF URL or empty string (always HTTPS)
        """
        for link in entry.findall("atom:link", self.namespaces):
            if link.get("type") == "application/pdf":
                url = link.get("href", "")
                # Convert HTTP to HTTPS for arXiv URLs
                if url.startswith("http://arxiv.org/"):
                    url = url.replace("http://arxiv.org/", "https://arxiv.org/")
                return url
        return ""

    def _get_pdf_path(self, arxiv_id: str) -> Path:
        """
        Get the local path for a PDF file.

        Args:
            arxiv_id: arXiv paper ID

        Returns:
            Path object for the PDF file
        """
        safe_filename = arxiv_id.replace("/", "_") + ".pdf"
        return self.pdf_cache_dir / safe_filename

    async def _download_with_retry(self, url: str, path: Path, max_retries: Optional[int] = None) -> bool:
        """Download a file with retry logic."""
        if max_retries is None:
            max_retries = self._settings.download_max_retries

        logger.info(f"Downloading PDF from {url}")

        await asyncio.sleep(self.rate_limit_delay)

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=float(self.timeout_seconds)) as client:
                    async with client.stream("GET", url) as response:
                        response.raise_for_status()
                        with open(path, "wb") as f:
                            async for chunk in response.aiter_bytes():
                                f.write(chunk)
                logger.info(f"Successfully downloaded to {path.name}")
                return True

            except httpx.TimeoutException as e:
                if attempt < max_retries - 1:
                    wait_time = self._settings.download_retry_delay_base * (attempt + 1)
                    logger.warning(f"PDF download timeout (attempt {attempt + 1}/{max_retries}): {e}")
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"PDF download failed after {max_retries} attempts due to timeout: {e}")
                    raise PDFDownloadTimeoutError(f"PDF download timed out after {max_retries} attempts: {e}")
            except httpx.HTTPError as e:
                if attempt < max_retries - 1:
                    wait_time = self._settings.download_retry_delay_base * (attempt + 1)  # Exponential backoff
                    logger.warning(f"Download failed (attempt {attempt + 1}/{max_retries}): {e}")
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed after {max_retries} attempts: {e}")
                    raise PDFDownloadException(f"PDF download failed after {max_retries} attempts: {e}")
            except Exception as e:
                logger.error(f"Unexpected download error: {e}")
                raise PDFDownloadException(f"Unexpected error during PDF download: {e}")

        # Clean up partial download
        if path.exists():
            path.unlink()

        return False
