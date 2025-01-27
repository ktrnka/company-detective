import os
from typing import Optional
from pyairtable import Api
from urllib.parse import urlparse
import pandas as pd
from core import Seed

api = Api(os.environ.get("AIRTABLE_API_KEY"))

company_table = api.table("appxVirwyt5V40t5S", "tbl2VTj1mFjoH4Gsx")

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
        require_backlinks=row["fields.Require Backlinks"],
    )


def pandas_to_seeds(df: pd.DataFrame) -> pd.Series:
    return df.apply(
        row_to_seed,
        axis=1,
    )
