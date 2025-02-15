import os
from urllib.parse import urlparse
from pyairtable.orm import Model, fields as F
from pyairtable.formulas import match
import core

APP_ID = "appxVirwyt5V40t5S"
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")


def extract_domain(url: str) -> str:
    parsed_url = urlparse(url)

    # If the scheme is missing, add a scheme to make it parse
    if not parsed_url.scheme:
        parsed_url = urlparse("http://" + url)

    domain = parsed_url.netloc
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def test_extract_domain():
    assert extract_domain("https://www.akiliinteractive.com/") == "akiliinteractive.com"
    assert (
        extract_domain("https://akiliinteractive.com/path/to/page")
        == "akiliinteractive.com"
    )
    assert extract_domain("http://www.example.com") == "example.com"
    assert extract_domain("http://example.com") == "example.com"
    assert extract_domain("https://subdomain.example.com") == "subdomain.example.com"
    assert extract_domain("subdomain.example.com") == "subdomain.example.com"
    assert extract_domain("subdomain.example.com/fart") == "subdomain.example.com"


class Product(Model):
    """ORM model for the Products table in Airtable"""

    name = F.TextField("Name")
    steam_url = F.UrlField(
        "Steam"
    )  # Rather than being none, this will be an empty string
    google_play_url = F.UrlField("Google Play")
    apple_app_store_url = F.UrlField("Apple App Store")
    webpage_url = F.UrlField("Webpage")

    class Meta:
        api_key = AIRTABLE_API_KEY
        base_id = APP_ID
        table_name = "Products"

    def to_core_product(self) -> core.Product:
        """Convert the ORM Product to a core Product"""
        return core.Product(
            name=self.name,
            steam_url=self.steam_url or None,
            google_play_url=self.google_play_url or None,
            apple_app_store_url=self.apple_app_store_url or None,
            webpage_url=self.webpage_url or None,
        )


class Company(Model):
    """ORM model for the Companies table in Airtable"""

    name = F.TextField("Name")
    webpage_url = F.UrlField("Website")
    status = F.SelectField("Status")
    keywords = F.TextField("Keywords")
    refresh_days = F.NumberField("Refresh Days")
    products = F.LinkField[Product]("Products", Product)
    feature_flags = F.MultipleSelectField("Feature Flags")

    # TODO: Deprecate this
    key_product_name = F.TextField("Key Product Name")

    class Meta:
        api_key = AIRTABLE_API_KEY
        base_id = APP_ID
        table_name = "Companies"

    def to_core_company(self) -> core.Seed:
        """Convert the ORM Company to a core Seed"""
        return core.Seed.init(
            company=self.name,
            domain=extract_domain(self.webpage_url),
            product=self.key_product_name or self.name,
            keywords=tuple(self.keywords.split()) if self.keywords else None,
            primary_product=(
                self.products[0].to_core_product() if self.products else None
            ),
            feature_flags=self.get_core_feature_flags(),
        )
    
    def get_core_feature_flags(self) -> core.FeatureFlags:
        # This requires that the flags have the same names in the DB and the class
        return core.FeatureFlags(**{flag: True for flag in self.feature_flags})
    
    @staticmethod
    def all_approved():
        # TODO: There's a bug here once we have over 100 records
        return Company.all(formula=match({"Status": "Approved"}), sort=["Name"])


# Examples
# from pyairtable.formulas import match

# s6 = Company.first(formula=match({"Name": "Singularity 6"}))
# s6.to_core_company()

# for company in Company.all(formula=match({"Status": status}), sort=["Name"]):
#     yield company.to_core_company()
