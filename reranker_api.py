

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

from llama_index.core.schema import TextNode, NodeWithScore, QueryBundle
from llama_index.core.postprocessor import SentenceTransformerRerank

app = FastAPI()

reranker = SentenceTransformerRerank(
    model="cross-encoder/ms-marco-MiniLM-L-2-v2",
    top_n=5,
    device="cpu",
)


class Document(BaseModel):
    text: str
    score: float | None = None


class RerankRequest(BaseModel):
    query: str
    documents: List[Document]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/rerank")
def rerank(request: RerankRequest):

    nodes = []

    for doc in request.documents:
        node = TextNode(text=doc.text)

        nodes.append(
            NodeWithScore(
                node=node,
                score=doc.score
            )
        )

    query_bundle = QueryBundle(request.query)

    reranked_nodes = reranker.postprocess_nodes(
        nodes,
        query_bundle=query_bundle
    )

    results = []

    for rank, item in enumerate(reranked_nodes, start=1):
        results.append({
            "rank": rank,
            "text": item.node.get_content(),
            "rerank_score": float(item.score),
        })

    return {
        "query": request.query,
        "results": results
    }
