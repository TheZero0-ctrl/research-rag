# OpenSearch Overview

This learning note explains why companies use OpenSearch, what it can do, and how it supports fast search across very large datasets.

## Why Companies Use OpenSearch

Companies use OpenSearch because it is a distributed search and analytics engine built for fast retrieval over large volumes of data. 
It is commonly used when normal database queries are too slow or too limited for search-heavy use cases.

OpenSearch is often used for:

- Full-text search across documents, logs, products, tickets, articles, and messages.
- Fast filtering, sorting, and faceting.
- Log analytics and observability.
- Search relevance tuning.
- Autocomplete and typo-tolerant search.
- Security analytics.
- Product search and recommendation support.
- Vector and hybrid search for AI/RAG systems.

A relational database is good at structured queries. OpenSearch is better when users need to search text, filter by many fields, 
rank by relevance, and get results quickly from very large datasets.

## What Is Achievable With OpenSearch

OpenSearch can power:

- Website search.
- E-commerce product search.
- Log monitoring dashboards.
- Real-time application analytics.
- Alerting on system events.
- Document search over PDFs, articles, and knowledge bases.
- Geo search, such as "stores near me".
- Autocomplete and suggestions.
- Faceted search, such as category, price, brand, and rating filters.
- Semantic/vector search using embeddings.
- Hybrid search that combines keyword relevance and vector similarity.

In this project, OpenSearch can store paper metadata, text chunks, embeddings, and search indexes for RAG-style retrieval.

## How OpenSearch Handles Billions of Documents

OpenSearch handles large scale by distributing data across a cluster.

The core idea is sharding. An index is split into smaller pieces called shards. Each shard is a Lucene index. 
These shards are distributed across multiple nodes. When a search request comes in, 
OpenSearch sends the query to the relevant shards in parallel, gathers the results, merges them, ranks them, and returns the final response.

OpenSearch also uses:

- Inverted indexes for fast text search.
- Columnar doc values for sorting and aggregations.
- Replicas for availability and read throughput.
- Segment merging for efficient storage and search.
- Caching for repeated filters and queries.
- Routing to reduce how many shards need to be searched.
- Tiered storage for hot, warm, and cold data.

## How Companies Search Through Billions of Documents

Companies usually do not scan billions of documents at query time. They search prebuilt indexes.

The flow is:

1. Documents are ingested.
2. Text is analyzed and tokenized.
3. Search indexes are created ahead of time.
4. Queries hit the index, not the raw documents.
5. Results are ranked by relevance and business rules.
6. Filters and aggregations are computed from optimized index structures.

For very large systems, companies also use:

- Partitioning by tenant, region, time, or category.
- Custom routing to search only relevant shards.
- Dedicated ingest pipelines.
- Separate clusters for hot and historical data.
- Reindexing pipelines for schema and relevance changes.
- Caches for popular queries.
- Async search for expensive analytics queries.

## How E-Commerce Giants Search Millions of Products Instantly

E-commerce search is fast because product data is indexed before the user searches.

A product search system usually indexes:

- Product title.
- Description.
- Brand.
- Category.
- Price.
- Inventory status.
- Ratings.
- Popularity.
- Seller information.
- Attributes like color, size, material, model, and compatibility.

When a user searches for "black running shoes size 9", OpenSearch does not scan every product row. It uses the inverted index to quickly find matching terms, applies filters like size and availability, ranks results using relevance plus business signals, then returns the top results.

Ranking may combine:

- Text relevance.
- Exact phrase matches.
- Brand and category boosts.
- Popularity.
- Conversion rate.
- Availability.
- Price rules.
- Personalization.
- Sponsored products.
- Semantic similarity.

This is why millions or billions of records can still feel instant: the expensive indexing work happens before the query, and the query fans out across optimized shards in parallel.
