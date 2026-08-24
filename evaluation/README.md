# RAG Evaluation

This folder contains the golden dataset and evaluation results used to compare the baseline and reranked RAG pipelines.

The evaluation compares:

- Hit Rate@5
- Mean Reciprocal Rank (MRR)
- Answer quality
- Groundedness
- Multi-evidence context coverage
- Out-of-scope abstention

The same knowledge base, embedding model, chunking strategy, and LLM were used for both pipelines so that reranking was the primary architectural variable being evaluated.
