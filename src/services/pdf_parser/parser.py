import logging
from pathlib import Path
from typing import Optional

from src.exceptions import PDFParsingException
from src.schemas.pdf_parser.models import PdfContent
from src.services.pdf_parser.docling import DoclingParser

logger = logging.getLogger(__name__)


class PDFParserService:
    """Main PDF parsing service using Docling only."""

    def __init__(self, max_pages: int, max_file_size_mb: int, do_ocr: bool = False, do_table_structure: bool = True):
        """Initialize the PDF parser wth configurable options."""
        self.docling_parser = DoclingParser(
            max_pages=max_pages,
            max_file_size_mb=max_file_size_mb,
            do_ocr=do_ocr,
            do_table_structure=do_table_structure
        )

    async def parse_pdf(self, pdf_path: Path) -> Optional[PdfContent]:
        """
        Parse a pdf file using Docling.

        Args:
            pdf_path (Path): Path to the PDF file.

        Returns:
            Optional[PdfContent]: Parsed PDF content or None if parsing fails.
        """

        if not pdf_path.exists():
            logger.error(f"PDF file not found: {pdf_path}")
            return None
        
        try:
            result = await self.docling_parser.parse_pdf(pdf_path)

            if result:
                logger.info(f"Docling parsing successful for {pdf_path.name}")
                return result
            else:
                logger.error(f"Docling parsing returned no result for {pdf_path.name}")
                raise PDFParsingException(f"Docling parsing returned no result for {pdf_path.name}")
        except Exception as e:
            logger.error(f"Docling parsing error for {pdf_path.name}: {e}")
            raise PDFParsingException(f"Docling parsing error for {pdf_path.name}: {e}")

