"""Member 4: receipt OCR."""

from tools.ocr_tool import extract_receipt, parse_receipt_text

SAMPLE_RECEIPT_TEXT = """
CHAI POINT
Koramangala, Bengaluru
Date: 09/10/2026
Masala Chai          120.00
Samosa (2)            80.00
Sub Total            200.00
CGST 2.5%              5.00
SGST 2.5%              5.00
Grand Total        Rs 210.00
Thank you!
"""


def test_receipt_text_is_turned_into_fields():
    fields = parse_receipt_text(SAMPLE_RECEIPT_TEXT)

    assert fields["merchant"] == "CHAI POINT"
    assert fields["date"] == "09-10-2026"
    assert fields["total"] == 210.0
    assert fields["tax"] == 10.0
    assert [item["price"] for item in fields["items"]] == [120.0, 80.0]


def test_text_without_a_total_is_not_guessed():
    assert parse_receipt_text("hello\nworld") is None


def test_without_any_ocr_engine_a_clearly_labelled_demo_is_returned(monkeypatch):
    monkeypatch.setenv("TESSERACT_CMD_PATH", "")
    monkeypatch.setattr("shutil.which", lambda name: None)

    result = extract_receipt(b"not-really-an-image", filename_hint="receipt.jpg")

    assert result["engine"].startswith("Demo receipt")
    assert result["total"] > 0
    assert result["category"] == "Food"
