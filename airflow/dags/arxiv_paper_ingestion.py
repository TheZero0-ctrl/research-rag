from datetime import datetime, timedelta

from airflow.sdk import dag, task

from arxiv_ingestion.fetching import fetch_daily_papers
from arxiv_ingestion.reporting import generate_daily_report
from arxiv_ingestion.setup import setup_environment

default_args = {
    "owner": "arxiv-curator",
    "depends_on_past": False,
    "start_date": datetime(2026, 8, 3),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=30),
    "catchup": False,
}


@dag(
    dag_id="arxiv_paper_ingestion",
    default_args=default_args,
    schedule="0 6 * * 1-5",  # Monday-Friday at 6 AM UTC
    max_active_runs=1,
    catchup=False,
    tags=["arxiv", "papers", "ingestion", "hybrid-search", "embeddings", "chunks"],
)
def arxiv_paper_ingestion_dag():
    """
    ### Daily arXiv Cs.AI paper pipeline
    fetch → store to PostgreSQL → chunk & embed → hybrid OpenSearch indexing
    """

    @task.bash
    def cleanup_temp_files(**context):
        return """
        echo "Cleaning up temporary files..."

        # Remove PDFs older than 30 days
        find /tmp -name "*.pdf" -type f -mtime +30 -delete 2>/dev/null || true

        echo "Cleanup completed"
        """



    environment_setup = setup_environment()

    fetch_results = fetch_daily_papers(environment_setup=environment_setup)

    report = generate_daily_report(fetch_results=fetch_results)

    cleanup_temp_files(report=report)

arxiv_paper_ingestion_dag()
