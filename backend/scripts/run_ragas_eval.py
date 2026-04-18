#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import _NonLLMContextPrecisionWithReference, _NonLLMContextRecall
from ragas.run_config import RunConfig
from tqdm import tqdm

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import settings
from app.core.prompts import build_prompt
from app.data.preprocessing import load_documents_from_path
from app.data.vectorstore import VectorStore
from app.services.embedding import EmbeddingService
from app.services.retrieval import RetrievalService


def load_qa_pairs_from_json(path: Path) -> list[tuple[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    pairs: list[tuple[str, str]] = []
    for cat in data.get("categories", []):
        for item in cat.get("questions", []):
            q = str(item.get("question", "")).strip()
            a = str(item.get("answer", "")).strip()
            if q and a:
                pairs.append((q, a))
    return pairs


def _extract_qa_from_text(text: str) -> tuple[str, str]:
    question_match = re.search(r"(?:^|\n)Q:\s*(.+?)(?:\n|$)", text, flags=re.IGNORECASE)
    answer_match = re.search(
        r"(?:^|\n)A:\s*(.*)$",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    question = question_match.group(1).strip() if question_match else ""
    answer = answer_match.group(1).strip() if answer_match else ""
    return question, answer


def load_qa_pairs_from_xlsx(path: Path) -> list[tuple[str, str]]:
    docs = load_documents_from_path(path)
    pairs: list[tuple[str, str]] = []
    for doc in docs:
        if str(doc.metadata.get("type", "")).lower() != "qa":
            continue
        question, answer = _extract_qa_from_text(doc.text)
        if question and answer:
            pairs.append((question, answer))
    return pairs


def load_qa_pairs(
    source: str,
    qa_json_path: Path,
    qa_xlsx_path: Path,
    *,
    json_limit: int,
    xlsx_limit: int,
) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    if source in {"json", "both"}:
        json_pairs = load_qa_pairs_from_json(qa_json_path)
        if json_limit > 0:
            json_pairs = json_pairs[:json_limit]
        pairs.extend(json_pairs)
    if source in {"xlsx", "both"}:
        xlsx_pairs = load_qa_pairs_from_xlsx(qa_xlsx_path)
        if xlsx_limit > 0:
            xlsx_pairs = xlsx_pairs[:xlsx_limit]
        pairs.extend(xlsx_pairs)

    deduped: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for pair in pairs:
        if pair in seen:
            continue
        seen.add(pair)
        deduped.append(pair)
    return deduped


async def retrieve_contexts(
    retrieval_service: RetrievalService, question: str
) -> list[str]:
    results = await retrieval_service.retrieve(question)
    return [r.text for r in results]


def generate_with_retries(
    base_url: str,
    model: str,
    prompt: str,
    system: str,
    timeout_sec: float,
    retries: int,
) -> str:
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {"temperature": 0},
    }

    last_err: Exception | None = None
    for _ in range(retries):
        try:
            with httpx.Client(timeout=timeout_sec) as client:
                resp = client.post(f"{base_url}/api/generate", json=payload)
                resp.raise_for_status()
                return str(resp.json().get("response", "")).strip()
        except Exception as exc:
            last_err = exc
            time.sleep(2.0)

    raise RuntimeError(f"Generation failed after {retries} tries: {last_err}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RAGAS eval with tqdm progress.")
    parser.add_argument(
        "--qa-file",
        default="/app/rag_data/qa.json",
        help="Path to QA json file",
    )
    parser.add_argument(
        "--qa-xlsx-file",
        default="/app/rag_data/NUST Bank-Product-Knowledge.xlsx",
        help="Path to Excel file used to extract QA pairs",
    )
    parser.add_argument(
        "--qa-source",
        choices=["json", "xlsx", "both"],
        default="both",
        help="Source of QA pairs for evaluation",
    )
    parser.add_argument(
        "--json-limit",
        type=int,
        default=0,
        help="Max JSON QA samples to include (0 = all)",
    )
    parser.add_argument(
        "--xlsx-limit",
        type=int,
        default=0,
        help="Max XLSX QA samples to include (0 = all)",
    )
    parser.add_argument(
        "--output",
        default="/app/data/ragas_eval_result.json",
        help="Where to write JSON output",
    )
    parser.add_argument(
        "--gen-timeout",
        type=float,
        default=300.0,
        help="Timeout (seconds) for each Ollama generation call",
    )
    parser.add_argument(
        "--gen-retries",
        type=int,
        default=3,
        help="Retries per sample generation",
    )
    args = parser.parse_args()

    qa_pairs = load_qa_pairs(
        source=args.qa_source,
        qa_json_path=Path(args.qa_file),
        qa_xlsx_path=Path(args.qa_xlsx_file),
        json_limit=args.json_limit,
        xlsx_limit=args.xlsx_limit,
    )
    if not qa_pairs:
        raise RuntimeError("No QA pairs found in dataset.")

    vector_store = VectorStore(str(settings.chroma_path))
    embedding_service = EmbeddingService(model_name=settings.embedding_model)
    retrieval_service = RetrievalService(
        vector_store=vector_store,
        embedding_service=embedding_service,
    )

    rows: dict[str, list[Any]] = {
        "user_input": [],
        "response": [],
        "reference": [],
        "retrieved_contexts": [],
        "reference_contexts": [],
    }

    for question, reference in tqdm(
        qa_pairs,
        desc="Building eval samples",
        unit="sample",
    ):
        contexts = asyncio.run(retrieve_contexts(retrieval_service, question))
        system_prompt, user_prompt = build_prompt(question, contexts, history=[])

        answer = generate_with_retries(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            prompt=user_prompt,
            system=system_prompt,
            timeout_sec=args.gen_timeout,
            retries=args.gen_retries,
        )

        rows["user_input"].append(question)
        rows["response"].append(answer)
        rows["reference"].append(reference)
        rows["retrieved_contexts"].append(contexts)
        rows["reference_contexts"].append([reference])

    dataset = Dataset.from_dict(rows)

    metrics = [
        _NonLLMContextPrecisionWithReference(),
        _NonLLMContextRecall(),
    ]

    result = evaluate(
        dataset=dataset,
        metrics=metrics,
        run_config=RunConfig(timeout=180, max_retries=1, max_workers=1),
        raise_exceptions=False,
        show_progress=True,
    )

    output = {
        "sample_count": len(rows["user_input"]),
        "empty_context_samples": sum(1 for c in rows["retrieved_contexts"] if not c),
        "metrics": result._repr_dict,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")

    print("\nRAGAS evaluation complete")
    print(json.dumps(output, indent=2, sort_keys=True))
    print(f"Saved to: {out_path}")


if __name__ == "__main__":
    main()
