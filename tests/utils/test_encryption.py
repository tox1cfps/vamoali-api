from utils.encryption import decrypt, encrypt


def test_encrypt_and_decrypt_round_trip():
    encrypted = encrypt("ana@example.com")
    assert encrypted != "ana@example.com"
    assert decrypt(encrypted) == "ana@example.com"
