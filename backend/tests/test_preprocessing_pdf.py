"""Tests for PDF ingestion in preprocessing."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data import preprocessing


class _FakePage:
    def __init__(self, text: str | None) -> None:
        self._text = text

    def extract_text(self) -> str | None:
        return self._text


class _FakePdfReader:
    def __init__(self, _path: str) -> None:
        self.pages = [
            _FakePage("Bank account opening requires CNIC and proof of income."),
            _FakePage("   "),
            _FakePage(None),
            _FakePage("Debit card annual fee is waived for the first year."),
        ]


def test_load_documents_from_pdf_skips_empty_pages(tmp_path, monkeypatch) -> None:
    pdf_path = tmp_path / "bank_faq.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")

    monkeypatch.setattr(preprocessing, "PdfReader", _FakePdfReader)

    docs = preprocessing.load_documents_from_path(pdf_path)

    assert len(docs) == 2
    assert docs[0].metadata["type"] == "pdf"
    assert docs[0].metadata["page"] == "1"
    assert docs[1].metadata["page"] == "4"
    assert docs[0].id == "bank_faq:pdf:p0"
    assert docs[1].id == "bank_faq:pdf:p3"


def test_load_documents_from_pdf_raises_when_reader_unavailable(
    tmp_path, monkeypatch
) -> None:
    pdf_path = tmp_path / "bank_faq.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")

    monkeypatch.setattr(preprocessing, "PdfReader", None)

    try:
        preprocessing.load_documents_from_path(pdf_path)
        assert False, "Expected RuntimeError when PdfReader is unavailable"
    except RuntimeError as exc:
        assert "pypdf" in str(exc).lower()
