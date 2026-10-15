import re
from dataclasses import dataclass


@dataclass
class CompoundMatch:
    """Class for handling compound matches between query adduct mass and NP Atlas"""

    npaid: str
    coconut_id: str
    exact_mass: float
    smiles: str
    name: str
    mass: float
    compound_number: int
    adduct: str
    origin_organism_type: str
    molecular_formula: str

    @property
    def npatlas_url(self) -> str:
        return f"https://www.npatlas.org/explore/compounds/{self.npaid}"

    @property
    def coconut_url(self) -> str:
        return (
            f"https://coconut.naturalproducts.net/compound/coconut_id/{self.coconut_id}"
        )

    def friendly_name(self) -> str:
        """JvS - This should no longer be required with unicode normalization on atlas import
        but there are still some issues
        Elementree has some problems reading special characters from the Atlas input because the input is
        occasionally not clean UTF-8. This if/ else statement cleans up names to eliminate crashes due to string
        parsing failure from the graphML file."""
        if re.match(
            r"^[A-Za-z0-9 α-ωΑ-Ω\-‐~,\"'$&*()±\[\]′’+./–″<>−{}|_:;]+$", self.name
        ):
            return xml_safe_name(self.name)
        else:
            return "Unknown"


def xml_safe_name(n):
    return n.replace("\f", "").encode("ascii", "replace").decode()
