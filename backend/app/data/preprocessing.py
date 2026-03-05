"""Document ingestion helpers, anonymization, and chunking."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable
from typing import Iterable

import pandas as pd
import numpy as np

WORD_CHUNK_SIZE = 800
WORD_CHUNK_OVERLAP = 200

# Patterns for detecting Q&A content in product sheets
QA_QUESTION_PATTERNS = [
    r"^what\s",
    r"^how\s",
    r"^can\s",
    r"^is\s",
    r"^are\s",
    r"^do\s",
    r"^does\s",
    r"^who\s",
    r"^when\s",
    r"^where\s",
    r"^why\s",
    r"^i\s+would\s+like",
    r"^i\s+want\s+to",
    r"\?$",
]


@dataclass(frozen=True)
class Document:
    id: str
    text: str
    metadata: dict[str, str]


@dataclass(frozen=True)
class DocumentChunk:
    id: str
    text: str
    metadata: dict[str, str | int]


ACCOUNT_PATTERN = re.compile(r"\b\d{10,16}\b")
PHONE_PATTERN = re.compile(r"\+?\d{2,3}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}")
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
CNIC_PATTERN = re.compile(r"\b\d{5}-\d{7}-\d{1}\b")


def load_documents(root: Path) -> list[Document]:
    """Load documents from files under `root` supporting JSON, CSV, Excel, and plain text."""

    documents: list[Document] = []
    for candidate in sorted(root.glob("*")):
        if not candidate.is_file():
            continue
        documents.extend(load_documents_from_path(candidate))
    return documents


def load_documents_from_path(path: Path) -> list[Document]:
    match path.suffix.lower():
        case ".json":
            return _load_from_json(path)
        case ".csv":
            return _load_from_dataframe(path, pd.read_csv)
        case ".xlsx" | ".xls":
            return _load_from_excel(path)
        case _:
            return _load_plain_text(path)


def _load_from_json(path: Path) -> list[Document]:
    if not path.exists():
        return []

    with path.open() as handle:
        payload = json.load(handle)

    documents: list[Document] = []
    for category in payload.get("categories", []):
        cat_name = category.get("category", path.stem)
        for idx, qa in enumerate(category.get("questions", [])):
            question = qa.get("question", "").strip()
            answer = qa.get("answer", "").strip()
            if not question and not answer:
                continue
            text = "\n".join(
                filter(
                    None,
                    (
                        f"Q: {question}" if question else "",
                        f"A: {answer}" if answer else "",
                    ),
                )
            )
            doc_id = f"{path.stem}:{cat_name}:{idx}"
            documents.append(
                Document(
                    id=doc_id,
                    text=text,
                    metadata={"source": path.name, "category": cat_name},
                )
            )
    return documents


def _load_from_excel(path: Path) -> list[Document]:
    """Load documents from all sheets in an Excel file with intelligent parsing."""
    try:
        xlsx = pd.ExcelFile(path)
    except Exception:
        return []

    documents: list[Document] = []
    for sheet_name in xlsx.sheet_names:
        try:
            df = pd.read_excel(xlsx, sheet_name=sheet_name, header=None)
        except Exception:
            continue

        # Determine sheet type and process accordingly
        sheet_name_lower = sheet_name.lower()
        if "rate" in sheet_name_lower:
            docs = _process_rate_sheet(df, path, sheet_name)
        elif sheet_name_lower in ("main", "sheet1"):
            docs = _process_index_sheet(df, path, sheet_name)
        else:
            docs = _process_product_sheet(df, path, sheet_name)

        documents.extend(docs)

    return documents


def _is_question(text: str) -> bool:
    """Check if text appears to be a question."""
    if not text:
        return False
    text_lower = text.lower().strip()
    for pattern in QA_QUESTION_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def _clean_cell_value(value) -> str:
    """Clean a cell value, handling NaN and other edge cases."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    return str(value).strip()


def _process_rate_sheet(
    df: pd.DataFrame, path: Path, sheet_name: str
) -> list[Document]:
    """Process rate sheets with table structure awareness.

    Extracts rate tables and creates documents with full context including
    section headers, account types, and column headers with each data row.

    Handles complex Excel layouts where multiple tables (e.g., Savings and
    Term Deposits) appear side by side in the same row range.
    """
    documents: list[Document] = []

    # Find the title/header of the sheet
    sheet_title = ""
    for idx in range(min(5, len(df))):
        for col in df.columns:
            val = _clean_cell_value(df.iloc[idx, col])
            if val and len(val) > 10 and "profit" in val.lower():
                sheet_title = val.replace("\n", " ").strip()
                break
        if sheet_title:
            break

    # The rate sheet has specific column layouts:
    # Savings: cols 1 (payment), 3 (rate)
    # Term Deposits: cols 5 (tenor), 6 (payout), 8 (rate)

    table_configs = [
        {
            "name": "Savings Accounts",
            "cols": [1, 3],
            "account_keywords": ["account", "savings", "citizen"],
        },
        {
            "name": "Term Deposits",
            "cols": [5, 6, 8],
            "account_keywords": [
                "deposit",
                "receipt",
                "sndr",
                "term",
                "value plus",
                "citizen",
            ],
        },
    ]

    # Process each table region
    for table_config in table_configs:
        table_name = table_config["name"]
        col_indices = table_config["cols"]
        account_keywords = table_config["account_keywords"]

        current_account = ""
        current_headers: dict[int, str] = {}

        for idx, row in df.iterrows():
            # Extract values only from this table's columns
            row_data: dict[int, str] = {}
            for col_idx in col_indices:
                if col_idx < len(row.values):
                    val = _clean_cell_value(row.values[col_idx])
                    if val:
                        row_data[col_idx] = val

            if not row_data:
                continue

            first_col = col_indices[0]
            first_val = row_data.get(first_col, "")
            first_lower = first_val.lower() if first_val else ""

            # Skip main section headers
            if "savings accounts" in first_lower or first_lower == "term deposits":
                continue

            # Check if this is a header row (contains header keywords)
            if any(kw in first_lower for kw in ["profit payment", "tenor"]):
                current_headers = {}
                for col_idx in col_indices:
                    val = row_data.get(col_idx, "")
                    if val:
                        current_headers[col_idx] = val.strip()
                continue

            # Check if this is an account/product name row
            if first_val and len(first_val) > 5:
                # Has account keywords and doesn't look like data
                if any(kw in first_lower for kw in account_keywords):
                    # Make sure it's not a data row (data rows have values in multiple cols or numeric)
                    is_data = False
                    for col_idx in col_indices[1:]:
                        if col_idx in row_data:
                            try:
                                float(row_data[col_idx])
                                is_data = True
                                break
                            except (ValueError, TypeError):
                                pass

                    if not is_data:
                        current_account = first_val
                        continue

            # Process data rows (rows with values when we have headers)
            if current_headers and row_data:
                # Build document with full context
                context_parts = []
                if sheet_title:
                    context_parts.append(f"Document: {sheet_title}")
                context_parts.append(f"Category: {table_name}")
                if current_account:
                    context_parts.append(f"Account/Product: {current_account}")

                # Pair headers with values
                data_pairs = []
                for col_idx, header in current_headers.items():
                    val = row_data.get(col_idx, "")
                    if val and val.lower() != header.lower():
                        # Format percentage values
                        try:
                            num = float(val)
                            if 0 < num < 1:
                                val = f"{num * 100:.2f}%"
                        except (ValueError, TypeError):
                            pass
                        data_pairs.append(f"{header}: {val}")

                if data_pairs:
                    context_parts.extend(data_pairs)
                    text = "\n".join(context_parts)
                    doc_id = f"{path.stem}:{sheet_name}:{table_name}:{idx}"
                    documents.append(
                        Document(
                            id=doc_id,
                            text=text,
                            metadata={
                                "source": path.name,
                                "sheet": sheet_name,
                                "section": table_name,
                                "account": current_account,
                                "type": "rate",
                            },
                        )
                    )

    # If no structured data found, fall back to row-by-row with context
    if not documents:
        documents = _process_sheet_fallback(df, path, sheet_name, "rate")

    return documents


def _process_product_sheet(
    df: pd.DataFrame, path: Path, sheet_name: str
) -> list[Document]:
    """Process product sheets with Q&A awareness.

    Groups questions with their answers to maintain semantic coherence.
    """
    documents: list[Document] = []

    # Get product name from first non-empty cell or sheet name
    product_name = sheet_name
    for idx in range(min(3, len(df))):
        for col in df.columns:
            val = _clean_cell_value(df.iloc[idx, col])
            if val and len(val) > 3:
                product_name = val
                break
        if product_name != sheet_name:
            break

    # Collect all text content with row tracking
    # Filter out navigation/link cells that are commonly in the last columns
    noise_values = {"main", "latest rate sheet", "back", "home", "menu"}

    rows_content: list[tuple[int, str]] = []
    for idx, row in df.iterrows():
        row_values = [_clean_cell_value(v) for v in row.values]
        # Filter out noise values and very short navigational text
        non_empty = [
            v for v in row_values if v and v.lower() not in noise_values and len(v) > 2
        ]
        if non_empty:
            # Join row content, but prefer the primary content (first substantive cell)
            if len(non_empty) > 1:
                # If first cell is a question, keep it alone to avoid mixing Q with other data
                if _is_question(non_empty[0]):
                    row_text = non_empty[0]
                else:
                    row_text = " | ".join(non_empty)
            else:
                row_text = non_empty[0]
            rows_content.append((int(idx), row_text))

    # Group Q&A pairs
    current_qa: dict = {"question": "", "answer_parts": [], "start_idx": 0}

    for idx, text in rows_content:
        if _is_question(text):
            # Save previous Q&A if exists
            if current_qa["question"]:
                qa_text = _format_qa_document(product_name, sheet_name, current_qa)
                if qa_text:
                    doc_id = f"{path.stem}:{sheet_name}:qa:{current_qa['start_idx']}"
                    documents.append(
                        Document(
                            id=doc_id,
                            text=qa_text,
                            metadata={
                                "source": path.name,
                                "sheet": sheet_name,
                                "product": product_name,
                                "type": "qa",
                            },
                        )
                    )
            # Start new Q&A
            current_qa = {"question": text, "answer_parts": [], "start_idx": idx}
        else:
            # Add to current answer
            if current_qa["question"]:
                current_qa["answer_parts"].append(text)
            else:
                # Content before first question - could be product description
                if text and text != product_name:
                    doc_id = f"{path.stem}:{sheet_name}:intro:{idx}"
                    intro_text = (
                        f"Product: {product_name}\nSheet: {sheet_name}\n\n{text}"
                    )
                    documents.append(
                        Document(
                            id=doc_id,
                            text=intro_text,
                            metadata={
                                "source": path.name,
                                "sheet": sheet_name,
                                "product": product_name,
                                "type": "intro",
                            },
                        )
                    )

    # Don't forget the last Q&A
    if current_qa["question"]:
        qa_text = _format_qa_document(product_name, sheet_name, current_qa)
        if qa_text:
            doc_id = f"{path.stem}:{sheet_name}:qa:{current_qa['start_idx']}"
            documents.append(
                Document(
                    id=doc_id,
                    text=qa_text,
                    metadata={
                        "source": path.name,
                        "sheet": sheet_name,
                        "product": product_name,
                        "type": "qa",
                    },
                )
            )

    # If no Q&A found, fall back to row-by-row with context
    if not documents:
        documents = _process_sheet_fallback(df, path, sheet_name, "product")

    return documents


def _format_qa_document(product_name: str, sheet_name: str, qa: dict) -> str:
    """Format a Q&A pair into a document string."""
    if not qa["question"]:
        return ""

    parts = [
        f"Product: {product_name}",
        f"Sheet: {sheet_name}",
        "",
        f"Q: {qa['question']}",
    ]

    if qa["answer_parts"]:
        answer = "\n".join(qa["answer_parts"])
        parts.append(f"A: {answer}")

    return "\n".join(parts)


def _process_index_sheet(
    df: pd.DataFrame, path: Path, sheet_name: str
) -> list[Document]:
    """Process index/main sheets that list available products."""
    documents: list[Document] = []

    # Extract product listings
    products: list[str] = []
    current_category = ""

    for idx, row in df.iterrows():
        row_values = [_clean_cell_value(v) for v in row.values]
        non_empty = [v for v in row_values if v]

        for val in non_empty:
            # Skip numeric values and short strings
            if val.isdigit() or len(val) < 3:
                continue
            # Detect category headers
            if "products" in val.lower() or "services" in val.lower():
                current_category = val
            elif len(val) > 5:
                products.append(
                    f"{current_category}: {val}" if current_category else val
                )

    if products:
        text = f"Sheet: {sheet_name}\nAvailable Products and Services:\n\n"
        text += "\n".join(f"- {p}" for p in products[:50])  # Limit to prevent huge docs

        documents.append(
            Document(
                id=f"{path.stem}:{sheet_name}:index",
                text=text,
                metadata={
                    "source": path.name,
                    "sheet": sheet_name,
                    "type": "index",
                },
            )
        )

    return documents


def _process_sheet_fallback(
    df: pd.DataFrame, path: Path, sheet_name: str, sheet_type: str
) -> list[Document]:
    """Fallback processing for sheets that don't match expected patterns.

    Groups rows with context from sheet name and includes column relationships.
    """
    documents: list[Document] = []
    content_rows: list[str] = []

    for idx, row in df.iterrows():
        row_values = [_clean_cell_value(v) for v in row.values]
        non_empty = [v for v in row_values if v]

        if non_empty:
            row_text = " | ".join(non_empty)
            content_rows.append(row_text)

    if content_rows:
        # Group rows into logical chunks (every 10 rows or so)
        chunk_size = 10
        for i in range(0, len(content_rows), chunk_size):
            chunk_rows = content_rows[i : i + chunk_size]
            text = f"Sheet: {sheet_name}\n\n" + "\n".join(chunk_rows)

            doc_id = f"{path.stem}:{sheet_name}:chunk:{i}"
            documents.append(
                Document(
                    id=doc_id,
                    text=text,
                    metadata={
                        "source": path.name,
                        "sheet": sheet_name,
                        "type": sheet_type,
                    },
                )
            )

    return documents


def _load_from_dataframe(
    path: Path, reader: Callable[[Path], pd.DataFrame]
) -> list[Document]:
    try:
        df = reader(path)
    except ValueError:
        return []

    documents: list[Document] = []
    for idx, row in enumerate(df.to_dict("records")):
        values = [
            str(value).strip()
            for value in row.values()
            if value not in (None, "", float("nan"))
        ]
        text = "\n".join(values)
        if not text:
            continue
        doc_id = f"{path.stem}:{idx}"
        documents.append(
            Document(
                id=doc_id, text=text, metadata={"source": path.name, "row": str(idx)}
            )
        )
    return documents


def _load_plain_text(path: Path) -> list[Document]:
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        return []
    doc_id = path.stem
    return [Document(id=doc_id, text=text, metadata={"source": path.name})]


def anonymize_pii(text: str) -> str:
    """Mask sensitive identifiers within the provided text."""

    masked = ACCOUNT_PATTERN.sub("[ACCOUNT_MASKED]", text)
    masked = PHONE_PATTERN.sub("[PHONE_MASKED]", masked)
    masked = EMAIL_PATTERN.sub("[EMAIL_MASKED]", masked)
    masked = CNIC_PATTERN.sub("[CNIC_MASKED]", masked)
    return masked


def preprocess_text(text: str) -> str:
    """Apply text-cleaning rules (lowercase, whitespace compression)."""

    normalized = text.strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.lower()


def chunk_document(
    document: Document,
    *,
    chunk_size: int = WORD_CHUNK_SIZE,
    overlap: int = WORD_CHUNK_OVERLAP,
) -> list[DocumentChunk]:
    """Split a document into smaller chunks suitable for embeddings."""

    text = document.text
    if chunk_size <= overlap:
        chunk_size = max(chunk_size, overlap + 1)

    step = chunk_size - overlap
    chunks: list[DocumentChunk] = []
    for index in range(0, max(len(text), 1), step):
        end = min(len(text), index + chunk_size)
        chunk_text = text[index:end].strip()
        if not chunk_text:
            continue
        chunk_id = f"{document.id}:{index}"
        metadata = {
            "source": document.metadata.get("source", ""),
            "chunk_index": len(chunks),
        }
        metadata.update(document.metadata)
        chunks.append(DocumentChunk(id=chunk_id, text=chunk_text, metadata=metadata))
        if end == len(text):
            break
    return chunks
