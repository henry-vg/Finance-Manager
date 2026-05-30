import pytest

from src.core.domain.transaction import (
    TransactionStatus,
    can_transition_transaction_status,
)


@pytest.mark.parametrize(
    ("current_status", "new_status", "expected"),
    [
        (TransactionStatus.PENDING, TransactionStatus.PENDING, False),
        (TransactionStatus.PENDING, TransactionStatus.POSTED, True),
        (TransactionStatus.PENDING, TransactionStatus.VOIDED, True),
        (TransactionStatus.POSTED, TransactionStatus.PENDING, False),
        (TransactionStatus.POSTED, TransactionStatus.POSTED, False),
        (TransactionStatus.POSTED, TransactionStatus.VOIDED, False),
        (TransactionStatus.VOIDED, TransactionStatus.PENDING, False),
        (TransactionStatus.VOIDED, TransactionStatus.POSTED, False),
        (TransactionStatus.VOIDED, TransactionStatus.VOIDED, False),
    ],
)
def test_can_transition_transaction_status_matches_transition_matrix(
    current_status: TransactionStatus,
    new_status: TransactionStatus,
    expected: bool,
) -> None:
    assert (
        can_transition_transaction_status(
            current_status=current_status,
            new_status=new_status,
        )
        is expected
    )
