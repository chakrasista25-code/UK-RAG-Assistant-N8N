UK RAG Assistant --- n8n

A low-code UK Pensions Retrieval-Augmented Generation (RAG) project
built to compare a standard vector-retrieval pipeline with a
second-stage cross-encoder reranking pipeline.

The project uses n8n for orchestration, Ollama for local
embeddings, Qdrant as the vector database, Claude for grounded
answer generation, and LlamaIndex + SentenceTransformers for local
reranking.

Project Objective

The project addresses two questions:

Can a grounded RAG assistant answer UK pensions questions using only
the supplied knowledge base?

Does adding a reranking stage materially improve retrieval quality
compared with a strong vector-retrieval baseline?

Rather than assuming that the more complex architecture is better, both
approaches were evaluated against the same knowledge base and golden
question set.

Architecture

Document ingestion

UK Pensions PDF
      ↓
Read File
      ↓
Extract PDF Text
      ↓
Recursive Character Splitter
(800 characters / 120 overlap)
      ↓
Ollama
mxbai-embed-large
      ↓
Qdrant
uk_pensions_mxbai_v1

Baseline RAG

User Question
      ↓
mxbai-embed-large
      ↓
Qdrant Vector Search
      ↓
Top 5 Chunks
      ↓
Aggregate Context
      ↓
Claude
      ↓
Grounded Answer

Reranked RAG

User Question
      ↓
mxbai-embed-large
      ↓
Qdrant Vector Search
      ↓
Top 20 Candidates
      ↓
Aggregate Candidates
      ↓
FastAPI
      ↓
LlamaIndex Cross-Encoder Reranker
      ↓
Top 5 Chunks
      ↓
Claude
      ↓
Grounded Answer

Technology Stack

Component                Purpose

n8n                      Low-code workflow orchestration
Ollama                   Local embedding inference
mxbai-embed-large        Final embedding model
Qdrant                   Vector storage and similarity search
Claude / Anthropic API   Grounded response generation
LlamaIndex               Reranking integration
SentenceTransformers     Local cross-encoder model
FastAPI                  Local reranker HTTP service
Docker                   n8n and Qdrant runtime
Python 3.11              Reranker runtime

The reranking model used is:

cross-encoder/ms-marco-MiniLM-L-2-v2

Repository Structure

UK-RAG-Assistant-N8N/
├── README.md
├── n8n-workflows/
│   ├── 01-uk-pensions-ingestion.json
│   ├── 02-uk-pensions-baseline-rag.json
│   └── 03-uk-pensions-reranked-rag.json
├── reranker/
│   ├── README.md
│   ├── reranker_api.py
│   └── requirements.txt
└── evaluation/
    ├── README.md
    ├── golden-dataset.csv
    └── evaluation-results.csv

n8n Workflows

01 --- UK Pensions Ingestion

Loads the source pension PDF, extracts its text, splits the content into
chunks, creates embeddings using mxbai-embed-large, and inserts the
resulting vectors into Qdrant.

Baseline chunking configuration:

Chunk size:    800 characters
Chunk overlap: 120 characters

02 --- UK Pensions Baseline RAG

Embeds the user question, retrieves the Top 5 Qdrant chunks, aggregates
the retrieved context, and sends it to Claude with grounding
instructions.

03 --- UK Pensions Reranked RAG

Retrieves the Top 20 Qdrant candidates and sends them to a local
LlamaIndex cross-encoder service. The reranker returns the Top 5 chunks,
which are then supplied to Claude.

Grounding Strategy

Claude is instructed to answer only from the retrieved context.

If the context is insufficient, the expected behaviour is to abstain
rather than answer from general model knowledge.

An out-of-scope test question was included:

What is the current Bank of England base rate?

Both pipelines correctly identified that the pension knowledge base did
not contain sufficient information to answer the question.

Embedding Model Experiment

The project initially used:

nomic-embed-text

For the test question:

What is a Defined Benefit pension?

the known definition was not retrieved even within the Top 20
candidates.

The embedding model was then changed to:

mxbai-embed-large

while keeping the source document, chunking approach and retrieval
architecture substantially constant.

The correct Defined Benefit definition moved to:

Rank #1

This was one of the most significant findings of the project:
embedding-model selection had a greater impact on retrieval quality
than adding reranking for this small corpus.

Data Quality

Repeated development-time ingestion produced duplicate Qdrant points.
Before formal evaluation, the collection was deleted and rebuilt using a
single clean ingestion.

Final clean collection:

88 Qdrant points

The Top-5 results were subsequently checked and contained no repeated
chunks.

Evaluation

A five-question golden dataset was used.

ID   Test                           Purpose

Q1   Defined Benefit pension        Direct definition
Q2   Defined Contribution pension   Similar concept discrimination
Q3   Pension drawdown               Terminology retrieval
Q4   DB vs DC comparison            Multi-evidence retrieval
Q5   Bank of England base rate      Out-of-scope / abstention

The complete questions and results are available in the evaluation/
directory.

Retrieval Results

For the three questions where a single first relevant result could
reasonably be identified:

Metric         Baseline   Reranked

Hit Rate@5         100%       100%
MRR               0.833      0.833

Relevant ranks:

Q1: Baseline 1 | Reranked 1
Q2: Baseline 2 | Reranked 2
Q3: Baseline 1 | Reranked 1

Q4 required evidence across multiple chunks; both pipelines retrieved
sufficient DB and DC evidence.

Q5 was an out-of-scope control; both pipelines correctly abstained.

Key Findings

1. Embedding quality mattered more than reranking

Changing the embedding model produced the largest observed retrieval
improvement:

nomic-embed-text
→ known DB definition not retrieved in Top 20

mxbai-embed-large
→ known DB definition retrieved at Rank #1

2. Reranking did not materially improve this small corpus

The baseline and reranked systems achieved the same Hit Rate@5 and MRR
on the applicable golden questions.

This does not imply that reranking is ineffective generally. The
corpus used here is small, domain-specific and glossary-oriented, and
the stronger embedding model already provided high-quality first-stage
retrieval.

A larger or noisier corpus containing many semantically similar
documents may benefit more from reranking.

3. Retrieval should be debugged before generation

A core lesson from the project was:

Poor retrieval
      ↓
Poor context
      ↓
The LLM cannot reliably recover missing evidence

The initial embedding experiment demonstrated why retrieval should be
inspected independently of the final generated answer.

4. Top-K retrieval does not imply relevance

For the out-of-scope Bank of England question, vector search still
returned the nearest available pension chunks.

A potential production enhancement would therefore be:

Question
   ↓
Retrieval
   ↓
Relevance / Confidence Gate
   ├── relevant → Claude
   └── insufficient relevance → abstain

Running the Local Reranker

Python 3.11 is recommended.

cd reranker

python3.11 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

uvicorn reranker_api:app --host 0.0.0.0 --port 8000

Health check:

curl http://127.0.0.1:8000/health

Expected response:

{"status":"ok"}

When n8n is running inside Docker, the reranked workflow calls the host
service at:

http://host.docker.internal:8000/rerank

Prerequisites

To reproduce the project, the following are required:

Docker / Docker Desktop

n8n

Qdrant

Ollama

mxbai-embed-large

Python 3.11

Anthropic API access for Claude

Pull the embedding model with:

ollama pull mxbai-embed-large

Import the JSON workflows from the n8n-workflows/ directory into n8n
and configure your own credentials/connections.

Security

No API secrets are intentionally included in this repository.

The exported n8n workflows have been prepared for sharing without the
original credential references. Users importing the workflows must
configure their own:

Anthropic API credential

Ollama connection

Qdrant connection

Never commit API keys, .env files containing secrets, or local
credential stores to source control.

Limitations

This is a proof-of-concept and evaluation project rather than a
production pension-advice service.

Current limitations include:

small source corpus;

small five-question golden dataset;

manually selected chunking parameters;

no automated relevance threshold;

no production authentication or observability layer;

evaluation results should not be generalized to larger corpora
without further testing.

Conclusion

The project successfully implemented and compared:

Baseline RAG
Vector Search → Top 5 → Claude

and:

Reranked RAG
Vector Search → Top 20 → Cross-Encoder → Top 5 → Claude

For this small UK pensions corpus, reranking did not materially improve
retrieval metrics over the strong vector-retrieval baseline.

The larger improvement came from selecting a more suitable embedding
model.

The main engineering conclusion is that RAG components should be
introduced based on measured retrieval needs rather than architectural
sophistication. A more complex RAG architecture is not automatically a
better RAG architecture.
