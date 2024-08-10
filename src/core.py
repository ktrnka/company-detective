from typing import NamedTuple
import re
import os
from datetime import datetime

class CompanyProduct(NamedTuple):
    company: str
    product: str

    @classmethod
    def same(cls, name: str):
        return cls(company=name, product=name)
    
assert CompanyProduct.same("98point6")


def make_experiment_dir(target: CompanyProduct) -> str:
    folder_name = re.sub(r"[^a-zA-Z0-9]", "_", f"{target.company} {target.product}")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    folder_path = f"experiments/{folder_name}/{timestamp}"

    os.makedirs(folder_path, exist_ok=True)

    return folder_path