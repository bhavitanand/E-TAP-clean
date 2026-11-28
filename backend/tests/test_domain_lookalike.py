"""Lookalike domains: genuine brand mail domains are not flagged, digit swaps are."""
import pytest

from forensics.brand_domains import known_brand_domain
from forensics.domain_similarity import analyze_domain, find_lookalike_brand


@pytest.mark.parametrize("domain", [
    "facebookmail.com",
    "e.facebookmail.com",        # a subdomain of a genuine domain
    "amazonses.com",
    "googlemail.com",
    "microsoftonline.com",
    "office365.com",
])
def test_genuine_brand_mail_domains_are_not_lookalikes(domain):
    assert find_lookalike_brand(domain) is None


@pytest.mark.parametrize("domain", [
    "evilfacebookmail.com",          # contains the name but is a different domain
    "facebookmail.com.evil.xyz",     # genuine name used as a subdomain of another site
    "notamazonses.com",
])
def test_known_domain_match_is_exact_not_substring(domain):
    assert known_brand_domain(domain) == ""


@pytest.mark.parametrize("domain,brand", [
    ("faceb00k.com", "facebook.com"),
    ("g00gle.com", "google.com"),
    ("paypa1.com", "paypal.com"),
    ("amaz0n.com", "amazon.com"),
    ("micr0soft.com", "microsoft.com"),
])
def test_digits_read_as_letters_are_lookalikes(domain, brand):
    match = find_lookalike_brand(domain)
    assert match is not None
    assert match["brand"] == brand
    assert match["match_type"] == "character_swap"


def test_digit_swap_with_a_lure_word_is_still_brand_plus_lure():
    match = find_lookalike_brand("paypa1-secure.com")
    assert match and match["brand"] == "paypal.com" and match["match_type"] == "brand_plus_lure"


@pytest.mark.parametrize("domain", [
    "example.com", "web3labs.com", "b2b-tools.com", "1password.com", "4chan.org",
    "mycompany.in", "facebook.com", "paypal.com",
])
def test_ordinary_names_and_exact_brands_are_not_flagged(domain):
    assert find_lookalike_brand(domain) is None


def test_existing_typosquat_and_lure_detection_is_unchanged():
    assert find_lookalike_brand("paypal-secure-login.com")["match_type"] == "brand_plus_lure"
    assert find_lookalike_brand("hdfcbnk.com")["brand"] == "hdfcbank.com"


def test_analyze_domain_records_a_known_domain_without_flagging_it():
    result = analyze_domain("facebookmail.com")
    assert result["lookalike_brand"] is None
    assert result["flags"] == []
    assert result["known_brand_domain"] == {"domain": "facebookmail.com", "brand": "facebook.com"}


def test_analyze_domain_flags_a_digit_swap():
    result = analyze_domain("faceb00k.com")
    assert result["lookalike_brand"]["brand"] == "facebook.com"
    assert "lookalike_of_facebook.com" in result["flags"]
    assert result["known_brand_domain"] is None


def test_known_domain_does_not_hide_other_sender_problems():
    """Being a genuine domain only removes the lookalike flag; the display-name check still runs."""
    result = analyze_domain("facebookmail.com", "PayPal Support")
    assert result["display_name_domain_mismatch"] is True
