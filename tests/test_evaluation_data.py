"""Validação dos casos de avaliação sintéticos e inteiramente fictícios."""

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).parents[1]
ALLOWED_STATUSES = {
    "answerable",
    "partial",
    "insufficient_evidence",
    "context_required",
    "conflict",
}


def test_synthetic_evaluation_cases_are_well_formed() -> None:
    data = json.loads(
        (PROJECT_ROOT / "evaluation" / "synthetic-cases.json").read_text(encoding="utf-8")
    )

    assert data["format_version"] == 1
    assert "fictícios" in data["description"]
    assert len(data["cases"]) == 5

    case_ids = [case["id"] for case in data["cases"]]
    assert len(case_ids) == len(set(case_ids))

    for case in data["cases"]:
        expected = case["expected"]
        assert expected["status"] in ALLOWED_STATUSES
        assert case["question"].strip()
        assert expected["answer_requirements"]
        if expected["status"] == "insufficient_evidence":
            assert expected["evidence"] == []
        else:
            assert expected["evidence"]
        for evidence in expected["evidence"]:
            assert evidence["page_number"] >= 1
            assert evidence["excerpt"].strip()
            assert "fict" in evidence["document_name"].casefold()
