# LLM Production Overview

This learning note explains common production issues with LLMs, t
he difference between fine-tuning and RAG, and how companies control LLM serving costs.

## Real Issues With LLMs in Production

LLMs are powerful, but production use introduces problems that are less visible in demos.

Common production issues include:

- **Hallucination:** the model can produce confident but incorrect answers.
- **Non-determinism:** the same prompt can return different answers unless generation settings are tightly controlled.
- **Latency:** large models can be slow, especially for long prompts or long outputs.
- **Cost:** every token has a cost when using hosted APIs, and GPU serving is expensive when self-hosting.
- **Context limits:** the model can only process a limited amount of input at once.
- **Prompt injection:** users or documents can contain instructions that try to override system behavior.
- **Data privacy:** prompts may contain sensitive user, company, or customer data.
- **Evaluation difficulty:** judging answer quality is harder than checking exact outputs from normal software.
- **Version drift:** hosted model behavior can change when providers update models.
- **Operational complexity:** production systems need retries, fallbacks, rate-limit handling, monitoring, logging, and safety controls.

The main production challenge is that LLMs are probabilistic systems. 
They need guardrails, observability, evaluation, and human-centered failure handling.

## Fine-Tuned LLM vs RAG

Fine-tuning and RAG solve different problems.

### Fine-Tuning

Fine-tuning changes the model's weights by training it on additional examples. 
It is useful when the model needs to learn a style, format, domain-specific behavior, or task pattern.

Fine-tuning is good for:

- Consistent tone or writing style.
- Structured output behavior.
- Domain-specific classification.
- Repeated task patterns.
- Reducing prompt length for common workflows.

Fine-tuning is not ideal for frequently changing facts. 
If company policies, product catalogs, or documents change often, retraining the model every time is expensive and slow.

### RAG

RAG, or Retrieval-Augmented Generation, keeps the model mostly unchanged. 
Instead of teaching the model everything, the system retrieves relevant documents from a database or search index and 
passes them into the prompt as context.

RAG is good for:

- Answering questions from private documents.
- Knowledge bases.
- Research papers.
- Customer support docs.
- Policies and manuals.
- Frequently changing information.
- Source-grounded answers with citations.

In a RAG system, OpenSearch or a vector database is often used to retrieve relevant chunks. 
The LLM then uses those chunks to generate an answer.

### Key Difference

Fine-tuning changes how the model behaves. RAG changes what information the model sees at answer time.

Use fine-tuning when the problem is behavior. Use RAG when the problem is knowledge.

Many production systems use both: RAG provides fresh company knowledge, 
while fine-tuning or prompt engineering controls response style and structure.

## How Companies Serve LLMs Without Burning Through Cash

Companies reduce LLM costs by avoiding unnecessary large-model calls and by optimizing every part of the request pipeline.

Common cost-control strategies include:

- **Use smaller models when possible:** route simple tasks to cheaper models and reserve large models for hard tasks.
- **Cache responses:** reuse answers for repeated or similar queries.
- **Cache embeddings:** do not regenerate embeddings for the same documents repeatedly.
- **Reduce prompt size:** retrieve only the most relevant context instead of sending huge documents.
- **Use RAG carefully:** chunk documents well, filter before vector search, and rerank only when needed.
- **Batch requests:** combine embedding or classification workloads where the provider/runtime supports batching.
- **Stream outputs:** improve perceived latency and stop generation early when enough answer has been produced.
- **Set token limits:** cap maximum output length and avoid runaway generations.
- **Use fallback chains:** try a cheap model first, then escalate to a stronger model only when needed.
- **Precompute expensive work:** summarize, index, classify, or enrich data before users ask questions.
- **Monitor usage by feature and customer:** track which workflows consume the most tokens and money.
- **Self-host selectively:** host open-weight models only when volume, privacy, or latency justifies GPU operations.

The biggest cost mistake is sending too much context to too large a model too often. 
Efficient production systems route requests, retrieve narrowly, cache aggressively, and measure token usage continuously.

## Practical Rule of Thumb

Use this decision guide:

- Need answers from changing documents: use RAG.
- Need a consistent output style or task behavior: use prompting or fine-tuning.
- Need lower cost: reduce tokens, cache, and route to smaller models.
- Need higher accuracy: improve retrieval, evaluation, and source grounding before assuming a bigger model will fix everything.
- Need production reliability: monitor latency, cost, failure rate, hallucination rate, and user feedback.
