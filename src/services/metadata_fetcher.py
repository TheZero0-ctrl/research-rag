import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dateutil import parser as date_parser
from sqlalchemy.orm import Session

from src.config import Settings
from src.exceptions import MetadataFetchingException, PipelineException
from src.repositories.paper import PaperRepository
from src.schemas.arxiv.paper import ArxivPaper, PaperCreate
from src.schemas.pdf_parser.models import ArxivMetadata, ParsedPaper
from src.services.arxiv.client import ArxivClient
from src.services.pdf_parser.parser import PDFParserService

logger = logging.getLogger(__name__)

class MetadataFetcher:
    """Service for fetching arXiv papers and processing and database storage"""

    def __init__(
        self,
        arxiv_client: ArxivClient,
        pdf_parser: PDFParserService,
        pdf_cache_dir: Optional[Path] = None,
        max_concurrent_downloads: int = 5,
        max_concurrent_parsing: int = 3,
        default_settings: Optional[Settings] = None,
    ):
        """
        initialize the metadata fetcher with services and settings

        Args:
            arxiv_client (ArxivClient): arxiv client service
            pdf_parser (PDFParserService): pdf parser service
            pdf_cache_dir (Optional[Path], optional): pdf cache directory. Defaults to None.
            max_concurrent_downloads (int, optional): maximum number of concurrent downloads. Defaults to 5.
            max_concurrent_parsing (int, optional): maximum number of concurrent parsing. Defaults to 3.
            settings (Optional[Settings], optional): settings. Defaults to None.
        """

        from src.config import settings

        self.arxiv_client = arxiv_client
        self.pdf_parser = pdf_parser
        self.pdf_cache_dir = pdf_cache_dir or self.arxiv_client.pdf_cache_dir
        self.max_concurrent_downloads = max_concurrent_downloads
        self.max_concurrent_parsing = max_concurrent_parsing
        self.settings = default_settings or settings

    async def fetch_and_process_papers(
        self,
        max_results: Optional[int] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        process_pdfs: bool = True,
        store_to_db: bool = True,
        db_session: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Fetch papers from arXiv and process and store to database

        Args:
            max_results (Optional[int], optional): maximum number of results to fetch. Defaults to None.
            from_date (Optional[str], optional): starting date for fetching results. Defaults to None. (format: YYYYMMDD)
            to_date (Optional[str], optional): ending date for fetching results. Defaults to None. (format: YYYYMMDD)
            process_pdfs (bool, optional): whether to process pdfs. Defaults to True.
            store_to_db (bool, optional): whether to store to database. Defaults to True.
            db_session (Optional[Session], optional): database session. Defaults to None.

        Returns:
            Dict[str, Any]: results Dictionary of processing results and stats.
        """

        results = {
            "papers_fetched": 0,
            "pdfs_downloaded": 0,
            "pdfs_parsed": 0,
            "papers_stored": 0,
            "papers_indexed": 0,
            "errors": [],
            "processing_time": 0,
        }

        start_time = datetime.now()

        try:
            # step 1 fetch paper metadata

            papers = await self.arxiv_client.fetch_papers(
                max_results=max_results, from_date=from_date, to_date=to_date, sort_by="submittedDate", sort_order="descending"
            )
            
            results["papers_fetched"] = len(papers)

            if not papers:
                logger.warning("No papers fetched")
                return results

            # step 2 process pdf
            pdf_results = {}
            if process_pdfs:
                pdf_results = await self._process_pdfs_batch(papers)
                results["pdfs_downloaded"] = pdf_results["downloaded"]
                results["pdfs_parsed"] = pdf_results["parsed"]
                results["errors"].extend(pdf_results["errors"])

            # step 3 store to database
            if store_to_db and db_session:
                logger.info("Storing papers to database...")
                stored_count = self._store_papers_to_db(papers, pdf_results.get("parsed_papers", {}), db_session)
                results["papers_stored"] = stored_count
            elif store_to_db:
                logger.warning("Database storage requested but no session provided")
                results["errors"].append("Database session not provided for storage")

            processing_time = (datetime.now() - start_time).total_seconds()
            results["processing_time"] = processing_time

            logger.info(
                f"Pipeline completed in {processing_time:.1f}s: {results['papers_fetched']} papers, {results['pdfs_downloaded']} PDFs, {len(results['errors'])} errors"
            )

            if results["errors"]:
                logger.warning("Errors summary:")
                for i, error in enumerate(results["errors"][:5], 1):  # Show first 5 errors
                    logger.warning(f"  {i}. {error}")
                if len(results["errors"]) > 5:
                    logger.warning(f"  ... and {len(results['errors']) - 5} more errors")

            return results
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            results["errors"].append(f"Pipeline error: {str(e)}")
            raise PipelineException(f"Pipeline execution failed: {e}") from e


    async def _process_pdfs_batch(self, papers: List[ArxivPaper]) -> Dict[str, Any]:
        """
        Process pdfs for batch of papers with async concurrency

        Args:
            papers (List[ArxivPaper]): list of arxiv papers

        Returns:
            Dictionary with processing results and stats
        """

        results = {
            "downloaded": 0,
            "parsed": 0,
            "parsed_papers": {},
            "errors": [],
            "download_failures": [],
            "parse_failures": [],
        }

        logger.info(f"Starting async pipeline for {len(papers)} PDFs...")
        logger.info(f"Concurrent downloads: {self.max_concurrent_downloads}")
        logger.info(f"Concurrent parsing: {self.max_concurrent_parsing}")

        download_semaphore = asyncio.Semaphore(self.max_concurrent_downloads)
        parse_semaphore = asyncio.Semaphore(self.max_concurrent_parsing)

        pipeline_tasks = [self._download_and_parse_pipeline(paper, download_semaphore, parse_semaphore) for paper in papers]
        
        pipeline_results = await asyncio.gather(*pipeline_tasks, return_exceptions=True)

        for paper, result in zip(papers, pipeline_results):
            if isinstance(result, Exception):
                error_msg = f"Pipeline error for {paper.arxiv_id}: {str(result)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
            elif result:
                if isinstance(result, tuple) and len(result) == 2:
                    download_success, parsed_paper = result
                else:
                    error_msg = f"Pipeline error for {paper.arxiv_id}: Unexpected result type {type(result).__name__}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
                    continue

                if download_success:
                    results["downloaded"] += 1

                    if parsed_paper:
                        results["parsed"] += 1
                        results["parsed_papers"][paper.arxiv_id] = parsed_paper
                    else:
                        # Download succeeded but parsing failed
                        results["parse_failures"].append(paper.arxiv_id)
                else:
                    # Download failed
                    results["download_failures"].append(paper.arxiv_id)
            else:
                results["download_failures"].append(paper.arxiv_id)

        logger.info(f"PDF processing: {results['downloaded']}/{len(papers)} downloaded, {results['parsed']} parsed")

        if results["download_failures"]:
            logger.warning(f"Download failures: {len(results['download_failures'])}")

        if results["parse_failures"]:
            logger.warning(f"Parse failures: {len(results['parse_failures'])}")

        return results


    async def _download_and_parse_pipeline(
        self, paper: ArxivPaper, download_semaphore: asyncio.Semaphore, parse_semaphore: asyncio.Semaphore
    ) -> tuple:
        """
        Download and parse pipeline for a single paper

        Args:
            paper (ArxivPaper): arxiv paper object
            download_semaphore (asyncio.Semaphore): semaphore for downloading
            parse_semaphore (asyncio.Semaphore): semaphore for parsing

        Returns:
            Tuple of (download_success: bool, parsed_paper: Optional[ParsedPaper])
        """

        download_success = False
        parsed_paper = None

        try:
            # step 1 Download paper
            async with download_semaphore:
                logger.debug(f"Starting download: {paper.arxiv_id}")
                pdf_path = await self.arxiv_client.download_pdf(paper, False)

                if pdf_path:
                    download_success = True
                    logger.debug(f"Download complete: {paper.arxiv_id}")
                else:
                    logger.error(f"Download failed: {paper.arxiv_id}")
                    return (False, None)

            # step 2 Parse paper
            async with parse_semaphore:
                logger.debug(f"Starting parse: {paper.arxiv_id}")
                pdf_content = await self.pdf_parser.parse_pdf(pdf_path)

                if pdf_content:
                    # Create ArxivMetadata from the paper
                    arxiv_metadata = ArxivMetadata(
                        title=paper.title,
                        authors=paper.authors,
                        abstract=paper.abstract,
                        arxiv_id=paper.arxiv_id,
                        categories=paper.categories,
                        published_date=paper.published_date,
                        pdf_url=paper.pdf_url,
                    )
                    parsed_paper = ParsedPaper(arxiv_metadata=arxiv_metadata, pdf_content=pdf_content)
                    logger.debug(f"Parse complete: {paper.arxiv_id} - {len(pdf_content.raw_text)} chars extracted")
                else:
                    logger.warning(f"PDF parsing failed for {paper.arxiv_id}, continuing with metadata only")
        except Exception as e:
            logger.error(f"Pipeline error for {paper.arxiv_id}: {e}")
            raise MetadataFetchingException(f"Pipeline error for {paper.arxiv_id}: {e}") from e

        return (download_success, parsed_paper)

    def _store_papers_to_db(
        self,
        papers: List[ArxivPaper],
        parsed_papers: Dict[str, ParsedPaper],
        db_session: Session,
    ) -> int:
        """
        Store papers and parsed content to database with comprehensive content storage.

        Args:
            papers: List of ArxivPaper metadata
            parsed_papers: Dictionary of parsed PDF content by arxiv_id
            db_session: Database session

        Returns:
            Number of papers stored successfully
        """
        paper_repo = PaperRepository(db_session)
        stored_count = 0

        for paper in papers:
            try:
                # Get parsed content if available
                parsed_paper = parsed_papers.get(paper.arxiv_id)

                # Base paper data
                published_date = (
                    date_parser.parse(paper.published_date) if isinstance(paper.published_date, str) else paper.published_date
                )
                paper_data = {
                    "arxiv_id": paper.arxiv_id,
                    "title": paper.title,
                    "authors": paper.authors,
                    "abstract": paper.abstract,
                    "categories": paper.categories,
                    "published_date": published_date,
                    "pdf_url": paper.pdf_url,
                }

                # Add parsed content if available
                if parsed_paper:
                    parsed_content = self._serialize_parsed_content(parsed_paper)
                    paper_data.update(parsed_content)
                    logger.debug(
                        f"Storing paper {paper.arxiv_id} with parsed content ({len(parsed_content.get('raw_text', '')) if parsed_content.get('raw_text') else 0} chars)"
                    )
                else:
                    # No parsed content - just store metadata
                    paper_data.update(
                        {"pdf_processed": False, "parser_metadata": {"note": "PDF processing not available or failed"}}
                    )
                    logger.debug(f"Storing paper {paper.arxiv_id} with metadata only")

                paper_create = PaperCreate(**paper_data)
                stored_paper = paper_repo.upsert(paper_create)

                if stored_paper:
                    stored_count += 1
                    content_info = "with parsed content" if parsed_paper else "metadata only"
                    logger.debug(f"Stored paper {paper.arxiv_id} to database ({content_info})")

            except Exception as e:
                logger.error(f"Failed to store paper {paper.arxiv_id}: {e}")

        # Commit all changes
        try:
            db_session.commit()
            logger.info(f"Committed {stored_count} papers to database with full content storage")
        except Exception as e:
            logger.error(f"Failed to commit papers to database: {e}")
            db_session.rollback()
            stored_count = 0

        return stored_count

    def _serialize_parsed_content(self, parsed_paper: ParsedPaper) -> Dict[str, Any]:
        """Serialize ParsedPaper content for database storage.

        :param parsed_paper: ParsedPaper object with PDF content
        :type parsed_paper: ParsedPaper
        :returns: Dictionary with serialized content for database storage
        :rtype: Dict[str, Any]
        """
        try:
            pdf_content = parsed_paper.pdf_content
            
            if not pdf_content:
                raise Exception("PDF content not available")

            # Serialize sections
            sections = [{"title": section.title, "content": section.content} for section in pdf_content.sections]

            # Serialize references
            references = list(pdf_content.references)

            return {
                "raw_text": pdf_content.raw_text,
                "sections": sections,
                "references": references,
                "parser_used": pdf_content.parser_used.value if pdf_content.parser_used else None,
                "parser_metadata": pdf_content.metadata or {},
                "pdf_processed": True,
                "pdf_processing_date": datetime.now(),
            }
        except Exception as e:
            logger.error(f"Failed to serialize parsed content: {e}")
            return {"pdf_processed": False, "parser_metadata": {"error": str(e)}}

def make_metadata_fetcher(
    arxiv_client: ArxivClient,
    pdf_parser: PDFParserService,
    pdf_cache_dir: Optional[Path] = None,
    default_settings: Optional[Settings] = None,
) -> MetadataFetcher:
    """Create MetadataFetcher instance with configuration settings.

    :param arxiv_client: Client for arXiv API operations
    :param pdf_parser: Service for parsing PDF documents
    :param pdf_cache_dir: Directory for caching downloaded PDFs
    :param settings: Application settings instance (uses default if None)
    :type arxiv_client: ArxivClient
    :type pdf_parser: PDFParserService
    :type pdf_cache_dir: Optional[Path]
    :type settings: Optional[Settings]
    :returns: Configured MetadataFetcher instance
    :rtype: MetadataFetcher
    """
    from src.config import settings

    if default_settings is None:
        default_settings = settings

    return MetadataFetcher(
        arxiv_client=arxiv_client,
        pdf_parser=pdf_parser,
        pdf_cache_dir=pdf_cache_dir,
        max_concurrent_downloads=settings.arxiv.max_concurrent_downloads,
        max_concurrent_parsing=settings.arxiv.max_concurrent_parsing,
        default_settings=default_settings,
    )
