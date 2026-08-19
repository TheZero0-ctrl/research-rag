import json
import logging

from datetime import datetime

from airflow.sdk import task

from .common import get_cached_services

logger = logging.getLogger(__name__)

@task
def generate_daily_report(**context):
    """Generate a daily report of the ingestion pipeline results.

    Collects statistics from all previous tasks and generates a summary report.
    """
    logger.info("Generating daily ingestion report")

    fetch_stats = context.get("fetch_results", {})

    report = {
        "execution_date": context.get("execution_date", datetime.now()).isoformat(),
        "fetch_statistics": {
            "papers_fetched": fetch_stats.get("papers_fetched", 0),
            "papers_stored": fetch_stats.get("papers_stored", 0),
            "target_date": fetch_stats.get("date", "unknown"),
        },
        "pipeline_status": "success" if fetch_stats else "failed",
    }

    try:
        _arxiv_client, _pdf_parser, database, _metadata_fetcher, _ = get_cached_services()

        with database.get_session() as session:
            from sqlalchemy import func
            from src.models.paper import Paper

            total_papers = session.query(func.count(Paper.id)).scalar()
            report["database_statistics"] = {"total_papers": total_papers}
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        report["error"] = str(e)

    logger.info("Daily Ingestion Report:")
    logger.info(json.dumps(report, indent=2))

    return report
