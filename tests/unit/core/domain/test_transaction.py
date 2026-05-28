import pytest

from src.core.domain.transaction import (
    TransactionStatus,
    can_transition_transaction_status,
)


@pytest.mark.parametrize(
    ("current_status", "new_status", "expected"),
    [
        (TransactionStatus.PENDING, TransactionStatus.PENDING, False),
        (TransactionStatus.PENDING, TransactionStatus.EFFECTIVE, True),
        (TransactionStatus.PENDING, TransactionStatus.CANCELED, True),
        (TransactionStatus.EFFECTIVE, TransactionStatus.PENDING, False),
        (TransactionStatus.EFFECTIVE, TransactionStatus.EFFECTIVE, False),
        (TransactionStatus.EFFECTIVE, TransactionStatus.CANCELED, True),
        (TransactionStatus.CANCELED, TransactionStatus.PENDING, False),
        (TransactionStatus.CANCELED, TransactionStatus.EFFECTIVE, False),
        (TransactionStatus.CANCELED, TransactionStatus.CANCELED, False),
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
