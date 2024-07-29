from typing import NamedTuple

class CompanyProduct(NamedTuple):
    company: str
    product: str

    @classmethod
    def same(cls, name: str):
        return cls(company=name, product=name)
    
assert CompanyProduct.same("98point6")

