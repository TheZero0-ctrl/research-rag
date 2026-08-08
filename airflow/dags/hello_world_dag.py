import psycopg

import requests

from airflow.sdk import dag, task
from datetime import timedelta


@dag(
    dag_id='hello_world_dag',
    schedule=None,
    default_args={
        "owner": "rag",
        "depends_on_past": False,
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    }
)
def hello_world_dag():
    """
    ### Simple hello world dag
    this is a simple hello world dag
    """

    @task
    def hello_world():
        """
        ### hello world
        A simple hello world task
        """
        print("hello world")

        return "success"

    @task
    def check_service():
        """
        ### check service
        A simple check service task, this check if other service is running
        """
        try:
            # check api health
            response = requests.get("http://rag-api:8000/api/v1/health", timeout=5)
            print(f"API Health: {response.status_code}")

            # check dagabase connection
            conn = psycopg.connect(host="postgres", port=5432, dbname="rag_db", user="rag_user", password="rag_password")
            print("Database: Connected successfully")
            conn.close()

            return "Services are accessible"
        except Exception as e:
            print(f"Service check failed: {e}")
            raise

    hello_world()
    check_service()

hello_world_dag()
