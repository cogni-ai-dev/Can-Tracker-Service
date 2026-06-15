import pytest
from cryptography.exceptions import InvalidTag
from sqlalchemy import Column, MetaData, String, Table, create_engine, insert, select

from app.core.config import Settings
from app.core.pii import (
    bank_account_number_search_hash,
    decrypt_pii_value,
    email_search_hash,
    encrypt_pan,
    mask_bank_account_number,
    mask_email,
    mask_mobile,
    mask_pan,
    mobile_search_hash,
    pan_search_hash,
    protect_bank_account_number,
    protect_email,
    protect_mobile,
    protect_pan,
)


def test_same_pan_has_same_search_hash_and_different_ciphertext(test_settings: Settings) -> None:
    first = protect_pan("abcde1234f", test_settings)
    second = protect_pan("ABCDE 1234F", test_settings)

    assert first.search_hash == second.search_hash
    assert first.ciphertext != second.ciphertext
    assert first.masked == "ABCDE****F"
    assert first.ciphertext is not None
    assert "ABCDE1234F" not in first.ciphertext
    assert decrypt_pii_value("pan", first.ciphertext, test_settings) == "ABCDE1234F"


def test_ciphertext_is_bound_to_field_name(test_settings: Settings) -> None:
    ciphertext = encrypt_pan("ABCDE1234F", test_settings)

    with pytest.raises(InvalidTag):
        decrypt_pii_value("email", ciphertext, test_settings)


def test_field_specific_search_hash_helpers_are_deterministic(test_settings: Settings) -> None:
    assert pan_search_hash("ABCDE1234F", test_settings) == pan_search_hash("abcde 1234f", test_settings)
    assert mobile_search_hash("+1 (555) 123-7890", test_settings) == mobile_search_hash("15551237890", test_settings)
    assert email_search_hash("CLIENT@EXAMPLE.COM", test_settings) == email_search_hash(
        "client@example.com", test_settings
    )
    assert bank_account_number_search_hash(" 001122334455 ", test_settings) == bank_account_number_search_hash(
        "001122334455", test_settings
    )


def test_masking_helpers_cover_sensitive_fields() -> None:
    assert mask_pan("ABCDE1234F") == "ABCDE****F"
    assert mask_mobile("+91 98765 43210") == "********3210"
    assert mask_email("Client.Person@Example.COM") == "c************@e******.com"
    assert mask_bank_account_number("001122334455") == "bank account ending 4455"


def test_no_plaintext_pii_is_persisted_when_storing_protected_values(test_settings: Settings) -> None:
    metadata = MetaData()
    storage = Table(
        "pii_storage",
        metadata,
        Column("pan_encrypted", String, nullable=False),
        Column("pan_masked", String, nullable=False),
        Column("pan_search_hash", String, nullable=False),
        Column("mobile_encrypted", String, nullable=False),
        Column("mobile_masked", String, nullable=False),
        Column("mobile_search_hash", String, nullable=False),
        Column("email_encrypted", String, nullable=False),
        Column("email_masked", String, nullable=False),
        Column("email_search_hash", String, nullable=False),
        Column("bank_account_number_encrypted", String, nullable=False),
        Column("bank_account_number_masked", String, nullable=False),
        Column("bank_account_number_search_hash", String, nullable=False),
    )
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    metadata.create_all(engine)

    pan = protect_pan("ABCDE1234F", test_settings)
    mobile = protect_mobile("9876543210", test_settings)
    email = protect_email("client@example.com", test_settings)
    bank_account = protect_bank_account_number("001122334455", test_settings)

    with engine.begin() as connection:
        connection.execute(
            insert(storage).values(
                pan_encrypted=pan.ciphertext,
                pan_masked=pan.masked,
                pan_search_hash=pan.search_hash,
                mobile_encrypted=mobile.ciphertext,
                mobile_masked=mobile.masked,
                mobile_search_hash=mobile.search_hash,
                email_encrypted=email.ciphertext,
                email_masked=email.masked,
                email_search_hash=email.search_hash,
                bank_account_number_encrypted=bank_account.ciphertext,
                bank_account_number_masked=bank_account.masked,
                bank_account_number_search_hash=bank_account.search_hash,
            )
        )
        row = connection.execute(select(storage)).mappings().one()

    persisted_text = "|".join(str(value) for value in row.values())
    assert "ABCDE1234F" not in persisted_text
    assert "9876543210" not in persisted_text
    assert "client@example.com" not in persisted_text
    assert "001122334455" not in persisted_text
