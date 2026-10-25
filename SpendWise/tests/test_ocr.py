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


def test_detects_when_a_receipt_date_is_outside_the_current_month():
    from freezegun import freeze_time
    from utils.helpers import is_in_current_month

    with freeze_time("2026-10-11"):
        assert is_in_current_month("05-10-2026") is True
        assert is_in_current_month("03-03-2026") is False  # old bill
        assert is_in_current_month("not a date") is False


def test_receipt_amounts_with_indian_commas():
    receipt = parse_receipt_text("Croma Electronics\n20-10-2026\nLaptop 1,25,000.00\nGrand Total Rs 1,25,000.00")

    assert receipt["total"] == 125000.0


def test_total_gst_line_is_tax_not_the_bill_total():
    receipt = parse_receipt_text("Cafe Coffee Day\n20-10-2026\nCappuccino 250.00\nSandwich 300.00\nTotal 550.00\nTotal GST 26.20")

    assert receipt["total"] == 550.0 and receipt["tax"] == 26.2


def test_cash_handed_over_and_change_are_not_the_bill_total():
    receipt = parse_receipt_text("Cafe Coffee Day\n20-10-2026\nCappuccino 550.00\nTotal 550.00\nAmount Paid 1000.00\nChange 450.00")

    assert receipt["total"] == 550.0
    assert [item["name"] for item in receipt["items"]] == ["Cappuccino"]


def test_amount_paid_is_used_when_there_is_no_total_line():
    assert parse_receipt_text("Chai Point\n20-10-2026\nMasala Chai 40.00\nAmount Paid 40.00")["total"] == 40.0


def test_heading_lines_are_not_the_shop_name_and_percentages_are_not_tax():
    receipt = parse_receipt_text("TAX INVOICE\nBehrouz Biryani\n20-10-2026\nBiryani 450.00\nCGST @ 2.5%\nTotal 471.00")

    assert receipt["merchant"] == "Behrouz Biryani"
    assert receipt["tax"] == 0.0 and receipt["total"] == 471.0


def test_total_including_gst_is_still_the_bill_total():
    receipt = parse_receipt_text("Dominos\n20-10-2026\nPizza 500.00\nCGST 2.5% 12.50\nSGST 2.5% 12.50\nTotal (incl. GST) 525.00")

    assert receipt["total"] == 525.0 and receipt["tax"] == 25.0
