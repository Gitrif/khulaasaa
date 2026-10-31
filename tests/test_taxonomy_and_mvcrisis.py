import pytest
from scrapers.tenders.gazette import classify_procurement
from scrapers.news import fetch_telegram_posts, format_relative_time
from unittest.mock import patch, MagicMock

def test_classify_procurement_two_tier():
    # 1. Services
    nat, disc = classify_procurement("Provision of Security Services for Maafaru School")
    assert nat == "Service"
    assert "Security" in disc

    nat, disc = classify_procurement("Seeking contractor for transfer and transport of waste from V. Keyodhoo to Thilafushi")
    assert nat == "Service"
    assert disc == "Cleaning & Waste Management"

    nat, disc = classify_procurement("Seeking contractor for 1-Year Servicing, Repair and Maintenance of Air Conditioners (AC)")
    assert nat == "Service"
    assert disc == "Repair & Maintenance"

    nat, disc = classify_procurement("Official Logo Design for Naivaadhoo Council")
    assert nat == "Service"
    assert disc == "Consultancy & Design"

    nat, disc = classify_procurement("Invitation to Tender - SAP S/4HANA Application Management Services (AMS)")
    assert nat == "Service"
    assert disc == "IT"

    # 2. Supplies
    nat, disc = classify_procurement("Supply and delivery of Electric Buggy")
    assert nat == "Supply"
    assert disc == "Logistics & Transport"

    nat, disc = classify_procurement("Tailoring and supply of uniforms for Gaddhoo Council School")
    assert nat == "Supply"
    assert disc == "Uniforms & Apparel"

    nat, disc = classify_procurement("Procurement of IT Hardware and Equipment for Virtual Booths")
    assert nat == "Supply"
    assert disc == "IT"

    nat, disc = classify_procurement("Supply and Delivery of Tissue Paper and Office Stationery")
    assert nat == "Supply"
    assert disc == "General Consumables & Office Supplies"

    # 3. Leases
    nat, disc = classify_procurement("Lease, Development and Operation of Tourist Guesthouse in HA. Hoarafushi")
    assert nat == "Lease"
    assert disc == "Real Estate & Leasing"


def test_fetch_telegram_posts_mocked():
    html_mock = """
    <div class="tgme_widget_message">
      <div class="tgme_widget_message_text">🚨 #Breaking : K. Guraidhoo ga dhe meehaku dhemedhu hingi maaraamaaree ehgai valhin hamalaa dheefi</div>
      <a class="tgme_widget_message_date" href="https://t.me/MvCrisis/114540">
        <time datetime="2026-10-15T08:00:00+00:00">08:00</time>
      </a>
    </div>
    <div class="tgme_widget_message">
      <div class="tgme_widget_message_text">HAYAT MATTRESS | Engineered for Comfort Call 7991234</div>
      <a class="tgme_widget_message_date" href="https://t.me/MvCrisis/114542">
        <time datetime="2026-10-15T08:21:00+00:00">08:21</time>
      </a>
    </div>
    <div class="tgme_widget_message">
      <div class="tgme_widget_message_text">Male ah miadhu vaarey veheyne kamah loafa weather mood</div>
      <a class="tgme_widget_message_date" href="https://t.me/MvCrisis/114543">
        <time datetime="2026-10-15T08:30:00+00:00">08:30</time>
      </a>
    </div>
    <div class="tgme_widget_message">
      <div class="tgme_widget_message_text">Good morning everyone! Have a blessed Friday ahead Jumaa Mubarak</div>
      <a class="tgme_widget_message_date" href="https://t.me/MvCrisis/114544">
        <time datetime="2026-10-15T08:45:00+00:00">08:45</time>
      </a>
    </div>
    """
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html_mock
        mock_get.return_value = mock_resp

        articles = fetch_telegram_posts("mvcrisis", "https://t.me/s/mvcrisis")
        # Only the real incident notice should pass (promo, rain hope, and greeting filtered)
        assert len(articles) == 1
        a = articles[0]
        assert "Guraidhoo" in a["headline"]
        assert a["url"] == "https://t.me/MvCrisis/114540"
        assert a["sources"] == ["mvcrisis"]
        assert a["section"] == "breaking"
