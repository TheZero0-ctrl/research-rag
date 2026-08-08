#!/bin/bash
set -e

# Clean up any existing PID files and processes
echo "Cleaning up any existing Airflow processes..."
if command -v pkill >/dev/null 2>&1; then
    pkill -f "airflow api-server" || true
    pkill -f "airflow dag-processor" || true
    pkill -f "airflow scheduler" || true
fi
rm -f /opt/airflow/airflow-api-server.pid
rm -f /opt/airflow/airflow-scheduler.pid

# Wait a moment for processes to fully terminate
sleep 2

echo "Migrating Airflow database..."
airflow db migrate

echo "Starting Airflow API server, DAG processor, and scheduler..."
airflow api-server --port 8082 &
airflow dag-processor &
airflow scheduler
