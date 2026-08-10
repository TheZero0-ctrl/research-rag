from functools import lru_cache

from src.config import settings
from src.services.pdf_parser.parser import PDFParserService


@lru_cache(maxsize=1)
def make_pdf_parser_service() -> PDFParserService:
    """Create cached pdf parser service using docling."""

    return PDFParserService(
        max_pages=settings.pdf_parser.max_pages,
        max_file_size_mb=settings.pdf_parser.max_file_size_mb,
        do_ocr=settings.pdf_parser.do_ocr,
        do_table_structure=settings.pdf_parser.do_table_structure
    )

