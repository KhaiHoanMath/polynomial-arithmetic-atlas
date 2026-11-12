#!/usr/bin/env python3
# Copyright © 2026 Khai-Hoan Nguyen-Dang. All rights reserved.
"""Generate the Eulerian table with exact arithmetic.

Install the dependency with `python -m pip install sympy==1.14.0`.
The coefficients in the CSV are ordered from the constant term up.
An empty modular witness means the search found none for primes up to 199.
The tracked table is content/data/eulerian.csv. CSV has no standard metadata
header; generation writes a separate metadata file under author-only/.
"""

import argparse
import csv
import io
import json
from pathlib import Path

from sympy import Poly, Symbol, ZZ, primerange


X = Symbol("x")
ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "content/data/eulerian.csv"
METADATA_PATH = ROOT / "author-only/eulerian/eulerian.csv.metadata.json"
COPYRIGHT = "© 2026 Khai-Hoan Nguyen-Dang. All rights reserved."
FIELDS = (
    "index",
    "degree",
    "removed_factor",
    "rational_factor_degrees",
    "prime_for_irreducible_reduction",
    "certified_galois_group",
    "frobenius_cycle_witnesses",
    "coefficients_ascending",
)


def normalized_polynomials():
    """Yield the descent Eulerian polynomials after removing x+1 at even indices."""
    coefficients = [1]
    for index in range(2, 31):
        updated = [0] * index
        for k, coefficient in enumerate(coefficients):
            updated[k] += (k + 1) * coefficient
            updated[k + 1] += (index - 1 - k) * coefficient
        coefficients = updated
        if index >= 3:
            polynomial = Poly.from_list(coefficients[::-1], X, domain=ZZ)
            if index % 2 == 0:
                polynomial = polynomial.exquo(Poly(X + 1, X, domain=ZZ))
            yield index, polynomial


def first_irreducible_reduction(polynomial):
    for prime in primerange(2, 200):
        if polynomial.set_modulus(prime).is_irreducible:
            return prime
    return ""


def is_nonsquare(value, prime):
    return value % prime not in {j * j % prime for j in range(prime)}


def verify_fifth_index(polynomial):
    """Check the explicit modular witnesses for Gal(A_5) = C2 wr S2."""
    y = Symbol("y")
    pair_polynomial = Poly(y**2 + 26 * y + 64, y, domain=ZZ)
    lifted = Poly((X**2 * pair_polynomial.as_expr().subs(y, X + 1 / X)).expand(), X, domain=ZZ)
    if polynomial != lifted or polynomial.eval(1) * polynomial.eval(-1) == 0:
        raise ValueError("Reciprocal quartic certificate failed")

    # The pair polynomial is irreducible mod 11. For one of its roots y,
    # the norm of y^2 - 4 is q(2)q(-2), a nonsquare. Thus x^2 - yx + 1
    # is irreducible over F_(11^2) and its roots have degree 4 over F_11.
    norm = pair_polynomial.eval(2) * pair_polynomial.eval(-2)
    if not is_nonsquare(pair_polynomial.discriminant(), 11) or not is_nonsquare(norm, 11):
        raise ValueError("Irreducible reduction at 11 failed")

    first = Poly(X + 5, X, modulus=23)
    second = Poly(X - 9, X, modulus=23)
    quadratic = Poly(X**2 + 7 * X + 1, X, modulus=23)
    if first * second * quadratic != polynomial.set_modulus(23):
        raise ValueError("Factorization at 23 failed")
    if first == second or not is_nonsquare(quadratic.discriminant(), 23):
        raise ValueError("Squarefree factor degrees at 23 failed")

    # Reciprocity embeds the group in C2 wr S2, of order 8. Frobenius
    # yields a 4-cycle and a transposition. The cyclic subgroup generated
    # by the 4-cycle does not contain a transposition, so the order is 8.
    return "D4 (order 8)", "11:4 | 23:1+1+2"


def make_csv():
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    for index, polynomial in normalized_polynomials():
        _, factors = polynomial.factor_list()
        degrees = sorted(factor.degree() for factor, exponent in factors for _ in range(exponent))
        group, cycles = verify_fifth_index(polynomial) if index == 5 else ("", "")
        writer.writerow(
            {
                "index": index,
                "degree": polynomial.degree(),
                "removed_factor": "x+1" if index % 2 == 0 else "",
                "rational_factor_degrees": "+".join(map(str, degrees)),
                "prime_for_irreducible_reduction": first_irreducible_reduction(polynomial),
                "certified_galois_group": group,
                "frobenius_cycle_witnesses": cycles,
                "coefficients_ascending": " ".join(map(str, reversed(polynomial.all_coeffs()))),
            }
        )
    return output.getvalue().encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify the tracked CSV without editing it")
    args = parser.parse_args()
    if not CSV_PATH.resolve().is_relative_to(ROOT / "content/data"):
        parser.error("The tracked Eulerian table must remain under content/data/.")
    if not METADATA_PATH.resolve().is_relative_to(ROOT / "author-only"):
        parser.error("Generated metadata must remain under author-only/.")
    contents = make_csv()
    if args.check:
        if not CSV_PATH.exists() or CSV_PATH.read_bytes() != contents:
            parser.exit(1, "Eulerian CSV differs from regenerated exact data.\n")
        print("Verified Eulerian CSV for 3 <= index <= 30.")
    else:
        CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
        CSV_PATH.write_bytes(contents)
        METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        METADATA_PATH.write_text(json.dumps({
            "title": "Polynomial Arithmetic Atlas: Eulerian table",
            "author": "Khai-Hoan Nguyen-Dang",
            "copyright": COPYRIGHT,
            "source": "content/data/eulerian.csv",
            "description": "Exact computations for normalized descent Eulerian polynomials, 3 <= index <= 30.",
            "coefficients": "Ascending order, from constant term to leading coefficient",
            "fields": list(FIELDS),
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Generated {CSV_PATH} and author-only metadata.")


if __name__ == "__main__":
    main()
