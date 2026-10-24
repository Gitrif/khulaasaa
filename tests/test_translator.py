import pytest
from scrapers.translator import (
    is_dhivehi,
    clean_dhivehi_markers,
    translate_dhivehi_title,
    translate_agency,
)


def test_is_dhivehi():
    assert is_dhivehi("އއ. އުކުޅަހު ޞިއްޙީ މަރުކަޒު") is True
    assert is_dhivehi("Reconstruction of B.Kamadhoo Harbour") is False
    assert is_dhivehi("") is False
    assert is_dhivehi(None) is False


def test_translate_dhivehi_title_works_and_construction():
    # Health Centre Lab construction
    t1 = "އއ. އުކުޅަހު ޞިއްޙީ މަރުކަޒުގެ ލެބޯޓްރީ ޢިމާރާތުގެ މަސައްކަތް ކޮށްދޭނެ ފަރާތެއް ހޯދުމަށް"
    en1 = translate_dhivehi_title(t1)
    assert "Seeking contractor" in en1
    assert "AA. Ukulhas" in en1
    assert "Health Centre" in en1
    assert "Laboratory" in en1
    assert "Building" in en1

    # Security services
    t2 = "ކައުންސިލް އިދާރާގެ ސެކިއުރިޓީ ބަލަހައްޓައިދޭނެ ފަރާތެއް ހޯދުމަށް"
    en2 = translate_dhivehi_title(t2)
    assert "security services" in en2.lower()
    assert "Council Secretariat" in en2

    # Supply and delivery
    t3 = "ކޮމްޕިއުޓަރ ސިސްޓަމް ސަޕްލައި ކޮށްދޭނެ ފަރާތެއް ހޯދުމަށް"
    en3 = translate_dhivehi_title(t3)
    assert "Supply and delivery" in en3
    assert "Computer Systems" in en3

    # English title untouched
    t4 = "Upgrading of A.Dh Fenfushi Harbour"
    assert translate_dhivehi_title(t4) == t4


def test_translate_agency():
    # 5 Official Cities
    assert translate_agency("މާލެ ސިޓީ ކައުންސިލްގެ އިދާރާ") == "Male' City Council"
    assert translate_agency("އައްޑޫ ސިޓީ ކައުންސިލްގެ އިދާރާ") == "Addu City Council"
    assert translate_agency("ފުވައްމުލައް ސިޓީ ކައުންސިލް") == "Fuvahmulah City Council"
    assert translate_agency("ކުޅުދުއްފުށި ސިޓީ ކައުންސިލް") == "Kulhudhuffushi City Council"
    assert translate_agency("ތިނަދޫ ސިޓީ ކައުންސިލްގެ އިދާރާ") == "Thinadhoo City Council"

    # Island councils with official long-form atolls
    assert translate_agency("މާޅޮސްމަޑުލު އުތުރުބުރީ ހުޅުދުއްފާރު ކައުންސިލްގެ އިދާރާ") == "Secretariat of the R. Hulhudhuffaaru Council"
    assert translate_agency("ނިލަންދެއަތޮޅު އުތުރުބުރީ މަގޫދޫ ކައުންސިލްގެ އިދާރާ") == "Secretariat of the F. Magoodhoo Council"
    assert translate_agency("މިލަދުންމަޑުލު އުތުރުބުރީ ކަންޑިތީމު ކައުންސިލްގެ އިދާރާ") == "Secretariat of the Sh. Kanditheemu Council"
    assert translate_agency("ތިލަދުންމަތީ އުތުރުބުރީ އުލިގަމު ކައުންސިލްގެ އިދާރާ") == "Secretariat of the HA. Uligan Council"

    assert translate_agency("Ministry of Finance") == "Ministry of Finance"
    assert translate_agency(None) == "Unknown Agency"


def test_zero_thaana_leakage():
    from scrapers.translator import clean_residual_thaana
    sample_dv_title = "ބީލަން ހުށަހެޅުމުގެ ދަޢުވަތު - މި އިދާރާގެ ބޭނުމަށް ހެވީ ވެހިކަލްތައް (1 އެކްސްކަވޭޓަރ އަދި 1 ބެކްހޯލޯޑަރ) ސަޕްލައިކޮށްދިނުމަށް ޝައުޤުވެރިވާ ފަރާތްތައް ހޯދުމަށް"
    en_title = translate_dhivehi_title(sample_dv_title)
    # Must have ZERO Thaana Unicode characters
    assert not any(0x0780 <= ord(c) <= 0x07BF for c in en_title)
    assert "Supply and delivery" in en_title
    assert "Heavy Vehicles" in en_title

    sample_agency = "ހުވަދުއަތޮޅު ދެކުނުބުރީ ތިނަދޫ ސިޓީ ކައުންސިލްގެ އިދާރާ"
    en_agency = translate_agency(sample_agency)
    assert not any(0x0780 <= ord(c) <= 0x07BF for c in en_agency)
    assert en_agency == "Thinadhoo City Council"


def test_translate_venue():
    from scrapers.translator import translate_venue
    assert translate_venue("އައްޑޫ ސިޓީ ކައުންސިލް އިދާރާ") == "Addu City Council Secretariat"
    assert translate_venue("ހުޅުދުއްފާރު ކައުންސިލް އިދާރާ") == "Hulhudhuffaaru Council Secretariat"
    assert translate_venue("މި އިދާރާއަށް") == "Council Secretariat / Agency Office"
    assert translate_venue(None) is None
    assert translate_venue("Zoom Meeting Online") == "Zoom Meeting Online"
