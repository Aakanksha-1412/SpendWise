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


def test_unreadable_real_receipt_is_not_replaced_by_demo_data(monkeypatch):
    monkeypatch.setenv("TESSERACT_CMD_PATH", "")
    monkeypatch.setattr("shutil.which", lambda name: None)

    result = extract_receipt(b"not-really-an-image", filename_hint="receipt.jpg")

    assert result["read_ok"] is False
    assert result["total"] == 0
    assert result["merchant"] == ""
    assert "Starbucks" not in str(result)


def test_demo_receipt_only_when_no_image_was_given():
    result = extract_receipt(None, filename_hint="starbucks_receipt.jpg")

    assert result["read_ok"] is True
    assert result["engine"].startswith("Demo receipt")


def test_bill_total_line_is_read_as_the_total():
    fields = parse_receipt_text("CAFE MOCHA" + chr(10) + "Latte 150.00" + chr(10) + "Bill Total 150.00")

    assert fields["total"] == 150.0


def test_quantity_line_after_grand_total_does_not_replace_it():
    text = chr(10).join(["CAFE MOCHA", "Latte 150.00", "Grand Total 150.00", "Total Qty: 1", "Total Savings 20.00"])

    fields = parse_receipt_text(text)

    assert fields["total"] == 150.0


def test_gst_number_line_is_not_counted_as_tax():
    text = chr(10).join(["CHAI POINT", "GST No: 29ABCDE1234F1Z5", "Masala Chai 120.00", "CGST 2.5% 3.00", "SGST 2.5% 3.00", "Grand Total 126.00"])

    fields = parse_receipt_text(text)

    assert fields["tax"] == 6.0
    assert fields["total"] == 126.0


def test_amount_payable_line_is_read_as_the_total():
    fields = parse_receipt_text(chr(10).join(["CAFE X", "Tea 40.00", "Amount Payable 40.00"]))

    assert fields["total"] == 40.0
