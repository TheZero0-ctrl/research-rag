# Research RAG

Research RAG is a work-in-progress attempt to build a ChatGPT-like research assistant for papers. The goal is to ingest research papers, index their content, and eventually let users search, retrieve, and ask source-grounded questions over a research corpus.

This project is still in the early setup phase. The current work focuses on the backend foundation, local infrastructure, and learning notes around the systems involved.

## Current Stack

- FastAPI for the API layer
- Airflow for background workflows
- PostgreSQL for relational state and metadata
- OpenSearch for search and retrieval
- Ollama/local LLM infrastructure for future RAG experiments
- Docker Compose for local development

## Current Capabilities

- FastAPI application bootstrapping
- Health check route with PostgreSQL connectivity check
- Local Docker Compose stack for API, Airflow, PostgreSQL, OpenSearch, OpenSearch Dashboards, and Ollama
- Learning documentation for system design, OpenSearch, PostgreSQL scaling, and LLM production concerns

## Project Goal

The long-term goal is to build a production-style research assistant that can help users explore papers, retrieve relevant sections, and answer questions with grounded context from the indexed documents.

## Status

This repository is actively evolving and should be treated as WIP. APIs, infrastructure, configuration, and architecture are expected to change as the project develops.
