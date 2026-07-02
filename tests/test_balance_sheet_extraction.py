import tomllib
from pathlib import Path

import pytest

from utils.pdf_extractor import (
    extract_balance_sheet_from_pdf, validate_balance_sheet, BALANCE_SHEET_FIELDS,
)
from utils.data_manager import add_balance_sheet_extraction
import utils.data_manager as data_manager

FIXTURE_PDF  = Path(__file__).parent / "fixtures" / "nxsn_q3_2025.pdf"
SECRETS_FILE = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"


def _load_api_key() -> str | None:
    if not SECRETS_FILE.exists():
        return None
    with open(SECRETS_FILE, "rb") as f:
        secrets = tomllib.load(f)
    return secrets.get("ANTHROPIC_API_KEY")


API_KEY = _load_api_key()

pytestmark = [
    pytest.mark.skipif(
        API_KEY is None,
        reason="ANTHROPIC_API_KEY not found in .streamlit/secrets.toml — skipping live-API test",
    ),
    pytest.mark.live_api,
]


@pytest.fixture(scope="module")
def extracted_record() -> dict:
    """Calls the live Claude API exactly once for the whole module — every test
    below reuses this single extraction to avoid repeated cost/latency."""
    if not FIXTURE_PDF.exists():
        pytest.skip(f"fixture PDF not found: {FIXTURE_PDF}")
    pdf_bytes = FIXTURE_PDF.read_bytes()
    return extract_balance_sheet_from_pdf(pdf_bytes, API_KEY, source_reference=FIXTURE_PDF.name)


def test_all_31_fields_present(extracted_record):
    expected_keys = set(BALANCE_SHEET_FIELDS) | {"balance_check"}
    assert set(extracted_record["fields"].keys()) == expected_keys


def test_period_metadata(extracted_record):
    assert extracted_record["period_type"] == "quarterly_cumulative"
    assert extracted_record["period_length_months"] == 9
    assert extracted_record["period_end"] == "2025-09-30"


def test_balance_check(extracted_record):
    bc = extracted_record["fields"]["balance_check"]
    assert bc is not None
    assert abs(bc) <= 1


@pytest.mark.parametrize("field,expected,tolerance", [
    ("cash", 27533, 5),
    ("total_assets", 610000, 1000),
    ("equity", 581999, 1000),
])
def test_known_figures(extracted_record, field, expected, tolerance):
    value = extracted_record["fields"][field]
    assert value is not None
    assert abs(value - expected) <= tolerance


def test_validate_balance_sheet_reports_no_imbalance(extracted_record):
    warnings = validate_balance_sheet(extracted_record)
    imbalance_warnings = [w for w in warnings if "אינו מאוזן" in w]
    assert imbalance_warnings == []


def test_storage_add_then_duplicate(extracted_record, monkeypatch):
    # add_balance_sheet_extraction calls save_data(data), which would otherwise
    # write straight into the real data/companies.json — patch it to a no-op.
    monkeypatch.setattr(data_manager, "save_data", lambda d: None)

    data = {"companies": [{"id": "test-co", "name": "Test Co", "balance_sheet_extractions": []}]}

    first = add_balance_sheet_extraction(data, "test-co", extracted_record)
    assert first["status"] == "added"

    second = add_balance_sheet_extraction(data, "test-co", extracted_record)
    assert second["status"] == "duplicate"

    assert len(data["companies"][0]["balance_sheet_extractions"]) == 1
