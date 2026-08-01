# System Design Overview

This learning note explains how the project systems are commonly scaled, monitored, integrated, deployed, and tested. 
The current stack includes the FastAPI API, Airflow, PostgreSQL, OpenSearch, Ollama, and Docker Compose infrastructure.

## How They Are Scaled

The API is scaled horizontally by running multiple Uvicorn workers or multiple API containers behind a load balancer. 
The current Docker command already starts Uvicorn with multiple workers.

Airflow is scaled by separating its webserver, scheduler, workers, triggerer, and metadata database. 
For production workloads, Airflow should generally use CeleryExecutor or KubernetesExecutor instead of LocalExecutor.

PostgreSQL is usually scaled vertically first, then with connection pooling, read replicas, partitioning, and managed database services. 
OpenSearch scales horizontally by adding data nodes and tuning shards and replicas. 
Ollama or other model-serving workloads scale by adding CPU/GPU-backed workers and routing requests through a queue or model gateway.

## Bottlenecks

Likely bottlenecks include:

- PostgreSQL connection limits, lock contention, and slow queries.
- OpenSearch indexing latency, search latency, shard sizing, and vector payload size.
- Airflow scheduler overload from many DAGs, expensive DAG parsing, or too many queued tasks.
- API worker saturation from long-running requests.
- Ollama/model inference latency and CPU/GPU memory pressure.
- Docker host limits, especially memory pressure from OpenSearch and model serving.

## Monitoring and Management

These systems are commonly monitored with health checks, structured logs, metrics, and alerts. 
Common choices include Prometheus, Grafana, OpenTelemetry, and centralized log aggregation.

Important metrics include:

- API: request rate, latency, error rate, worker count, CPU, and memory.
- PostgreSQL: active connections, slow queries, locks, replication lag, and disk usage.
- OpenSearch: cluster health, JVM heap, indexing latency, search latency, and shard status.
- Airflow: DAG success/failure rate, task duration, scheduler heartbeat, queue depth, and retry counts.
- Ollama/model serving: inference latency, queue time, CPU/GPU usage, and memory usage.

Management should include backups, database migrations, alerting, log retention, runbooks, and clear ownership for each service.

## Integration With Other Systems

The API exposes HTTP endpoints and connects to PostgreSQL and OpenSearch. 
Airflow orchestrates background workflows and can call APIs, query databases, ingest documents, update OpenSearch, and trigger external services. 
PostgreSQL stores application and workflow state, while OpenSearch supports indexing and search. Ollama provides local model inference.

Integration should happen through explicit contracts: HTTP APIs, DAG interfaces, database migrations, environment-based configuration, 
and typed application settings.

## Best Practices

Use separate configuration for local, staging, and production environments. 
Avoid hardcoded hostnames and ports in application code. Use readiness and health checks for every service. 
Keep long-running work out of API request handlers and move it to Airflow or a queue-backed worker.

Use connection pooling for PostgreSQL, tune OpenSearch shards deliberately, and keep the Airflow metadata database separate from application data 
in production. Store secrets in a secrets manager rather than plain `.env` files. 
Pin dependency versions, run migrations explicitly, and maintain backups for PostgreSQL plus snapshots for OpenSearch.

## Production Deployment

Docker Compose is useful for local development. 
Production deployments usually use a more robust platform such as Kubernetes, ECS, Nomad, or managed cloud services.

A production deployment typically includes:

- API containers behind a load balancer or ingress controller.
- Managed PostgreSQL or a highly available PostgreSQL cluster.
- Managed OpenSearch or a dedicated OpenSearch node group.
- Airflow deployed as separate webserver, scheduler, worker, and triggerer services.
- Centralized logs, metrics, and alerting.
- Secrets from Vault, AWS Secrets Manager, Doppler, Kubernetes Secrets, or an equivalent system.
- CI/CD pipelines for image builds, tests, migrations, deploys, and rollbacks.

## Load and Performance Testing

Testing should happen at multiple levels:

- Unit tests for business logic.
- Integration tests for the API, database, OpenSearch, and Airflow DAG behavior.
- Contract tests for external interfaces.
- End-to-end tests for full user and workflow scenarios.
- Load tests for API endpoints using tools such as k6, Locust, or JMeter.
- Database performance tests with realistic data volumes and query plans.
- OpenSearch tests for indexing throughput, search latency, and vector query performance.
- Airflow performance tests for task duration, retries, scheduler load, and backfill behavior.

Performance testing should track p50, p95, and p99 latency, throughput, error rate, resource usage, and saturation points. 
The goal is to identify where the system fails first, how gracefully it degrades, and what capacity limits should trigger scaling.
