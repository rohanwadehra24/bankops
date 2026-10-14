from app import evaluate_transaction

def test_review_transaction_at_threshold():
    assert evaluate_transaction(100000) == "REVIEW"


def test_clear_transaction():
    assert evaluate_transaction(25000) == "CLEAR"


def test_review_transaction():
    assert evaluate_transaction(150000) == "REVIEW"
