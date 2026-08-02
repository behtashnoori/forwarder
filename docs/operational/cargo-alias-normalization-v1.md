# Cargo alias normalization v1

Release 1.6.0 uses one deterministic normalization function for alias uniqueness and admin search preparation:

1. Unicode NFC normalization.
2. Arabic `ي`/`ى` to Persian `ی`, and Arabic `ك` to Persian `ک`.
3. Arabic-Indic and Persian digits to ASCII digits `0`–`9`.
4. Any run of whitespace or ZWNJ becomes one ordinary space.
5. Leading/trailing space is removed.
6. Unicode case folding is applied (materially affecting Latin text).

No fuzzy matching, trigram index, transliteration, token stemming, or cross-organization matching is performed.
