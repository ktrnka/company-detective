import os
from typing import Optional
from pyairtable import Api
from urllib.parse import urlparse
import pandas as pd
from core import Product, Seed

api = Api(os.environ.get("AIRTABLE_API_KEY"))

APP_ID = "appxVirwyt5V40t5S"
company_table = api.table(APP_ID, "tbl2VTj1mFjoH4Gsx")
product_table = api.table(APP_ID, "tbliM8NuCBrs93x8b")

# TODO: Look into pyairtable ORM


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


def load_into_pandas(status: Optional[str] = "Approved") -> pd.DataFrame:
    df = pd.DataFrame(pd.json_normalize(company_table.all()))

    if status:
        df = df[df["fields.Status"] == status]

    # simplify the domain
    df["domain"] = df["fields.Website"].apply(extract_domain)

    # Replace NaN values with empty lists. Note that fillna doesn't work for this, nor does testing with pd.isnan nor does .replace work
    df["fields.Require Backlinks"] = df["fields.Require Backlinks"].apply(lambda val: val if not isinstance(val, float) else [])

    # Join the product table into the company table
    product_df = pd.DataFrame(pd.json_normalize(product_table.all())).set_index("id")
    df["products"] = df["fields.Products"].apply(lambda product_ids: product_df.loc[product_ids].to_dict(orient="records") if not pd.isnull(product_ids) else [])

    return df

def row_to_seed(row: pd.Series) -> Seed:
    return Seed.init(
        company=row["fields.Name"],
        domain=row["domain"],
        product=(
            row["fields.Key Product Name"]
            if not pd.isna(row["fields.Key Product Name"])
            else None
        ),
        keywords=(
            tuple(row["fields.Keywords"].split())
            if not pd.isna(row["fields.Keywords"])
            else None
        ),
        # Require Backlinks is a multi-select field which is represented as a list of strings
        require_news_backlinks="news" in row["fields.Require Backlinks"],
        require_reddit_backlinks="reddit" in row["fields.Require Backlinks"],
        primary_product=to_primary_product(row["products"]),
    )

def to_primary_product(products: list[dict]) -> Optional[Product]:
    if not products:
        return None
    
    return to_product(products[0])

def to_product(product: dict) -> Product:
    return Product(
        name=product["fields.Name"],
        # Optional fields may not be present in the row
        steam_url=product.get("fields.Steam"),
        google_play_url=product.get("fields.Google Play"),
        apple_app_store_url=product.get("fields.Apple App Store"),
        webpage_url=product.get("fields.Webpage"),
    )


def pandas_to_seeds(df: pd.DataFrame) -> pd.Series:
    return df.apply(
        row_to_seed,
        axis=1,
    )
