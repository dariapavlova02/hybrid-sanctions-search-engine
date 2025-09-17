"""Property-based tests for identifier validators."""

import string

from hypothesis import assume, given, strategies as st

from src.ai_service.data.patterns.identifiers import (
    ISO_COUNTRY_CODES,
    validate_ein,
    validate_iban,
    validate_ssn,
    validate_swift_bic,
)


def _compute_iban_check_digits(country: str, bban: str) -> str:
    rearranged = bban + country + "00"
    remainder = 0
    for char in rearranged:
        if char.isdigit():
            remainder = (remainder * 10 + int(char)) % 97
        else:
            remainder = (remainder * 100 + (ord(char) - 55)) % 97
    check_digits = 98 - remainder
    return f"{check_digits:02d}"


@st.composite
def iban_strings(draw):
    country = draw(st.sampled_from(sorted(ISO_COUNTRY_CODES)))
    bban_length = draw(st.integers(min_value=11, max_value=30))
    bban = draw(st.text(string.ascii_uppercase + string.digits, min_size=bban_length, max_size=bban_length))
    check_digits = _compute_iban_check_digits(country, bban)
    iban = f"{country}{check_digits}{bban}"
    if draw(st.booleans()):
        groups = [iban[i:i + 4] for i in range(0, len(iban), 4)]
        iban = " ".join(groups)
    return iban


@given(iban_strings())
def test_validate_iban_accepts_valid_values(iban: str):
    assert validate_iban(iban)


@given(iban_strings())
def test_validate_iban_rejects_invalid_checksum(iban: str):
    normalized = iban.replace(" ", "")
    current_check = normalized[2:4]
    new_check = (int(current_check) + 1) % 100
    # Ensure new check digits differ from original
    if f"{new_check:02d}" == current_check:
        new_check = (new_check + 1) % 100
    mutated = f"{normalized[:2]}{new_check:02d}{normalized[4:]}"
    assert not validate_iban(mutated)


@st.composite
def swift_bic_strings(draw):
    bank_code = "".join(draw(st.lists(st.sampled_from(string.ascii_uppercase), min_size=4, max_size=4)))
    country = draw(st.sampled_from(sorted(ISO_COUNTRY_CODES)))

    def _location_strategy():
        return st.text(string.ascii_uppercase + string.digits, min_size=2, max_size=2).filter(
            lambda loc: loc.upper() not in {"00", "0O", "O0", "OO"}
        )

    location = draw(_location_strategy())
    branch = draw(
        st.one_of(
            st.just(""),
            st.text(string.ascii_uppercase + string.digits, min_size=3, max_size=3).filter(lambda b: b.upper() != "000"),
        )
    )
    return bank_code + country + location + branch


@given(swift_bic_strings())
def test_validate_swift_bic_accepts_valid(bic: str):
    assert validate_swift_bic(bic)


@given(swift_bic_strings())
def test_validate_swift_bic_rejects_bad_country(bic: str):
    mutated = bic[:4] + "ZZ" + bic[6:]
    assert not validate_swift_bic(mutated)


def test_validate_swift_bic_rejects_zero_branch():
    assert not validate_swift_bic("DEUTDEFF000")


VALID_EIN_PREFIXES = (
    '01', '02', '03', '04', '05', '06',
    '10', '11', '12', '13', '14', '15', '16',
    '20', '21', '22', '23', '24', '25', '26', '27',
    '30', '31', '32', '33', '34', '35', '36', '37', '38', '39',
    '40', '41', '42', '43', '44', '45', '46', '47', '48',
    '50', '51', '52', '53', '54', '55', '56', '57', '58', '59',
    '60', '61', '62', '63', '64', '65', '66', '67', '68',
    '71', '72', '73', '74', '75', '76', '77',
    '80', '81', '82', '83', '84', '85', '86', '87', '88',
    '90', '91', '92', '93', '94', '95', '98', '99',
)


@st.composite
def ein_strings(draw):
    prefix = draw(st.sampled_from(VALID_EIN_PREFIXES))
    suffix = draw(st.text(string.digits, min_size=7, max_size=7))
    formatted = prefix + suffix
    if draw(st.booleans()):
        formatted = f"{prefix}-{suffix}"
    return formatted


@given(ein_strings())
def test_validate_ein_accepts_valid_values(ein: str):
    assert validate_ein(ein)


@given(st.text(string.digits, min_size=9, max_size=9))
def test_validate_ein_rejects_unknown_prefix(ein_digits: str):
    prefix = ein_digits[:2]
    assume(prefix not in VALID_EIN_PREFIXES)
    assert not validate_ein(ein_digits)


@st.composite
def ssn_strings(draw):
    area = draw(st.integers(min_value=1, max_value=665))
    if area == 666:
        area = 665
    area_str = f"{area:03d}"
    group = draw(st.integers(min_value=1, max_value=99))
    group_str = f"{group:02d}"
    serial = draw(st.integers(min_value=1, max_value=9999))
    serial_str = f"{serial:04d}"
    ssn = area_str + group_str + serial_str
    if draw(st.booleans()):
        ssn = f"{area_str}-{group_str}-{serial_str}"
    return ssn


@given(ssn_strings())
def test_validate_ssn_accepts_valid_values(ssn: str):
    assert validate_ssn(ssn)


@given(st.integers(min_value=900, max_value=999))
def test_validate_ssn_rejects_high_prefix(area: int):
    ssn = f"{area:03d}01-0001"
    assert not validate_ssn(ssn)


def test_validate_ssn_rejects_known_invalid_numbers():
    assert not validate_ssn("666-12-1234")
    assert not validate_ssn("000-12-1234")
    assert not validate_ssn("078-05-1120")
