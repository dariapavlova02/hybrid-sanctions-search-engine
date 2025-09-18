"""Property-based tests for identifier validators."""

import string

from hypothesis import assume, given, strategies as st

from src.ai_service.data.patterns.identifiers import (
    ISO_COUNTRY_CODES,
    validate_ein,
    validate_edrpou,
    validate_iban,
    validate_inn,
    validate_ogrn,
    validate_ogrnip,
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


# INN validation tests
def test_validate_inn_valid_10_digit():
    """Test valid 10-digit INN checksums"""
    # Known valid INN values with correct checksums
    assert validate_inn("7736050003")  # Valid checksum
    assert validate_inn("7707049388")  # Valid checksum


def test_validate_inn_valid_12_digit():
    """Test valid 12-digit INN checksums"""
    # Known valid 12-digit INN with correct checksums
    assert validate_inn("500100732259")  # Valid checksum


def test_validate_inn_invalid_checksum():
    """Test invalid INN checksums"""
    assert not validate_inn("1234567890")  # Invalid 10-digit
    assert not validate_inn("123456789012")  # Invalid 12-digit


def test_validate_inn_invalid_format():
    """Test invalid INN formats"""
    assert not validate_inn("")  # Empty
    assert not validate_inn("12345")  # Too short
    assert not validate_inn("12345678901234")  # Too long
    assert not validate_inn("773605000a")  # Contains letter
    assert not validate_inn("773605000-3")  # Contains dash


# EDRPOU validation tests
def test_validate_edrpou_valid_6_digit():
    """Test valid 6-digit EDRPOU (no checksum)"""
    assert validate_edrpou("123456")
    assert validate_edrpou("000001")
    assert validate_edrpou("999999")


def test_validate_edrpou_valid_8_digit():
    """Test valid 8-digit EDRPOU with checksum"""
    # Test with computed valid checksum: 1*1+2*2+3*3+4*4+5*5+6*6+7*7 = 140, 140%11 = 8
    assert validate_edrpou("12345678")  # Computed valid checksum


def test_validate_edrpou_invalid_format():
    """Test invalid EDRPOU formats"""
    assert not validate_edrpou("")  # Empty
    assert not validate_edrpou("12345")  # Too short
    assert not validate_edrpou("123456789")  # Too long
    assert not validate_edrpou("1234567a")  # Contains letter


# OGRN validation tests
def test_validate_ogrn_valid():
    """Test valid OGRN checksums"""
    # Test with computed valid checksum: 102770013219 % 11 = 5
    assert validate_ogrn("1027700132195")


def test_validate_ogrn_invalid_checksum():
    """Test invalid OGRN checksums"""
    assert not validate_ogrn("1027700132190")  # Wrong checksum


def test_validate_ogrn_invalid_format():
    """Test invalid OGRN formats"""
    assert not validate_ogrn("")  # Empty
    assert not validate_ogrn("123456789012")  # Too short
    assert not validate_ogrn("12345678901234")  # Too long
    assert not validate_ogrn("102770013219a")  # Contains letter


# OGRNIP validation tests
def test_validate_ogrnip_valid():
    """Test valid OGRNIP checksums"""
    # Test with computed valid checksum: 30477000001234 % 13 = 7
    assert validate_ogrnip("304770000012347")


def test_validate_ogrnip_invalid_checksum():
    """Test invalid OGRNIP checksums"""
    assert not validate_ogrnip("304770000012340")  # Wrong checksum (should be 7, not 0)


def test_validate_ogrnip_invalid_format():
    """Test invalid OGRNIP formats"""
    assert not validate_ogrnip("")  # Empty
    assert not validate_ogrnip("12345678901234")  # Too short
    assert not validate_ogrnip("1234567890123456")  # Too long
    assert not validate_ogrnip("30477000001234a")  # Contains letter


# Property-based tests for Russian/Ukrainian identifiers
@st.composite
def inn_10_digit_strings(draw):
    """Generate valid 10-digit INN numbers with correct checksums"""
    # Generate 9 random digits
    digits = [draw(st.integers(min_value=0, max_value=9)) for _ in range(9)]

    # Calculate check digit
    check_weights = [2, 4, 10, 3, 5, 9, 4, 6, 8]
    check_sum = sum(digits[i] * check_weights[i] for i in range(9))
    check_digit = check_sum % 11
    if check_digit > 9:
        check_digit = check_digit % 10

    return ''.join(map(str, digits + [check_digit]))


@st.composite
def inn_12_digit_strings(draw):
    """Generate valid 12-digit INN numbers with correct checksums"""
    # Generate 10 random digits
    digits = [draw(st.integers(min_value=0, max_value=9)) for _ in range(10)]

    # Calculate first check digit
    check_weights_1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    check_sum_1 = sum(digits[i] * check_weights_1[i] for i in range(10))
    check_digit_1 = check_sum_1 % 11
    if check_digit_1 > 9:
        check_digit_1 = check_digit_1 % 10

    # Calculate second check digit
    digits_with_first_check = digits + [check_digit_1]
    check_weights_2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    check_sum_2 = sum(digits_with_first_check[i] * check_weights_2[i] for i in range(11))
    check_digit_2 = check_sum_2 % 11
    if check_digit_2 > 9:
        check_digit_2 = check_digit_2 % 10

    return ''.join(map(str, digits + [check_digit_1, check_digit_2]))


@given(inn_10_digit_strings())
def test_validate_inn_accepts_valid_10_digit(inn: str):
    assert validate_inn(inn)


@given(inn_12_digit_strings())
def test_validate_inn_accepts_valid_12_digit(inn: str):
    assert validate_inn(inn)


@given(inn_10_digit_strings())
def test_validate_inn_rejects_corrupted_10_digit(inn: str):
    """Test that corrupting the check digit makes INN invalid"""
    # Corrupt the last digit
    corrupted_check = (int(inn[-1]) + 1) % 10
    corrupted_inn = inn[:-1] + str(corrupted_check)
    if corrupted_inn != inn:  # Only test if we actually changed something
        assert not validate_inn(corrupted_inn)


@given(inn_12_digit_strings())
def test_validate_inn_rejects_corrupted_12_digit(inn: str):
    """Test that corrupting either check digit makes 12-digit INN invalid"""
    # Corrupt the second-to-last digit (first check digit)
    corrupted_check_1 = (int(inn[-2]) + 1) % 10
    corrupted_inn = inn[:-2] + str(corrupted_check_1) + inn[-1]
    if corrupted_inn != inn:
        assert not validate_inn(corrupted_inn)
