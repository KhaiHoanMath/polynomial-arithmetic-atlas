#!/usr/bin/env python3
# Copyright © 2026 Khai-Hoan Nguyen-Dang. All rights reserved.
"""Exact checks for the literature additions of 12 November 2026.

Requires SymPy. Run: python3 scripts/literature_certificates.py
These finite calculations verify examples, not the cited general theorems.
"""
from functools import lru_cache
from math import gcd

import sympy as s

x, y, t = s.symbols('x y t')
checks = []


def verify(name, condition):
    if not bool(condition):
        raise AssertionError(name)
    checks.append(name)


@lru_cache(None)
def stern(n):
    if n < 2:
        return n
    if n % 2 == 0:
        return stern(n // 2)
    return stern(n // 2) + stern(n // 2 + 1)


# P_n(x) = sum s(j+1)x^(n-j). Equal residue-class sums imply Phi_p|P_n.
for n, p, expected in [(62, 7, 52), (1022, 11, 2684), (4094, 13, 20440)]:
    sums = [0] * p
    for j in range(n + 1):
        sums[(n - j) % p] += stern(j + 1)
    verify(f'Stern coefficients: Phi_{p} divides P_{n}', sums == [expected] * p)

# Principal-character Fekete polynomials and rational necklace functions.
for n in (6, 10, 15, 105):
    fekete = sum(x ** a for a in range(1, n) if gcd(a, n) == 1)
    necklace = sum(s.mobius(d) * x ** d / (1 - x ** d) for d in s.divisors(n))
    verify(f'Fekete rational identity n={n}', s.cancel(fekete / (1 - x ** n) - necklace) == 0)
verify('Möbius residue cancellation n=105, m=8', all(
    sum(s.mobius(d) for d in s.divisors(105) if d % 8 == r) == 0
    for r in range(8)))

# The number of cyclotomic factors grows with the iterate.
for n in (1, 2, 3):
    product = s.prod(s.cyclotomic_poly(2 ** (n + 1) * 3 ** j, x) for j in range(n + 1))
    verify(f'power-map cyclotomic factorization n={n}', s.expand(product) == x ** (6 ** n) + 1)

# A primitive element need not be normal over F_2.
modulus = s.Poly(x ** 4 + x + 1, x, modulus=2)
verify('x^4+x+1 irreducible over F_2', modulus.is_irreducible)


def power_mod(exponent):
    return s.Poly(x ** exponent, x, modulus=2).rem(modulus)


one = s.Poly(1, x, modulus=2)
verify('root has multiplicative order 15', power_mod(15) == one and
       power_mod(3) != one and power_mod(5) != one)
trace = sum((power_mod(2 ** j) for j in range(4)), s.Poly(0, x, modulus=2))
verify('root is not normal: conjugates sum to zero', trace.is_zero)

# B_2^(12) from the exponential generating function, truncated at t^2.
generating = s.expand((1 - t / 2 + t ** 2 / 12) ** 12 *
                      (1 + x * t + x ** 2 * t ** 2 / 2))
bernoulli = s.expand(2 * generating.coeff(t, 2))
verify('higher-order Bernoulli B_2^(12)', bernoulli == x ** 2 - 12 * x + 35)
verify('higher-order Bernoulli factorization', s.expand((x - 5) * (x - 7)) == bernoulli)

sparse = s.Poly(3 + x + x ** 2 + x ** 5, x)
verify('sparse prime-constant example irreducible', sparse.is_irreducible)
bad = x + x ** 3 + x ** 5 + 3
verify('sparse common-root obstruction', s.expand((x + 1) *
       (x ** 4 - x ** 3 + 2 * x ** 2 - 2 * x + 3)) == bad)

# Central-binomial Taylor polynomial: an exact A_4 certificate.
C4 = sum(s.binomial(2 * j, j) * x ** j for j in range(5))
Q4 = x ** 4 + 2 * x ** 3 + 6 * x ** 2 + 20 * x + 70
T = 1 - s.Rational(4, 3) * y + s.Rational(6, 5) * y ** 2 - s.Rational(4, 7) * y ** 3 + y ** 4 / 9
verify('C4 reciprocal equals Q4', s.expand(x ** 4 * C4.subs(x, 1 / x)) == Q4)
verify('C4 Taylor transformation', s.expand(s.Rational(315, 128) * T.subs(y, 1 - 4 * x)) == C4)


def valuation(value, prime):
    numerator, denominator = s.Rational(value).as_numer_denom()
    return s.multiplicity(prime, abs(numerator)) - s.multiplicity(prime, denominator)


def lower_hull(points):
    hull = []
    for point in points:
        while len(hull) > 1:
            a, b = hull[-2:]
            if ((b[0] - a[0]) * (point[1] - b[1]) -
                    (b[1] - a[1]) * (point[0] - b[0])) > 0:
                break
            hull.pop()
        hull.append(point)
    return hull


possible_degrees = {}
for prime, vertices in [(5, [(0, 0), (2, -1), (4, 0)]),
                        (7, [(0, 0), (3, -1), (4, 0)])]:
    points = [(j, valuation(T.coeff(y, j), prime)) for j in range(5)]
    hull = lower_hull(points)
    verify(f'T Newton polygon at {prime}', hull == vertices)
    degrees = {0}
    for a, b in zip(hull, hull[1:]):
        width = b[0] - a[0]
        denominator = int(s.Rational(b[1] - a[1], width).q)
        degrees = {d + contribution for d in degrees
                   for contribution in range(0, width + 1, denominator)}
    possible_degrees[prime] = degrees - {0, 4}
verify('Newton factor-degree restrictions are incompatible',
       not (possible_degrees[5] & possible_degrees[7]))
verify('Q4 irreducible over Q', s.Poly(Q4, x).is_irreducible)
verify('Q4 square discriminant', s.discriminant(Q4, x) == 7560 ** 2)
cubic = x ** 3 - x ** 2 - 4 * x + 6
verify('Q4 factorization modulo 13', s.Poly(Q4 - (x + 3) * cubic, x, modulus=13).is_zero)
verify('modulo-13 cubic has no root', all(int(cubic.subs(x, a)) % 13 != 0 for a in range(13)))
verify('modulo-13 reduction squarefree', s.gcd(s.Poly(Q4, x, modulus=13),
       s.Poly(s.diff(Q4, x), x, modulus=13)).degree() == 0)
group, _ = s.polys.numberfields.galois_group(Q4, x)
verify('Q4 group is A4', group.degree == 4 and group.order() == 12 and
       all(generator.is_even for generator in group.generators))

print(f'Passed {len(checks)} exact literature example checks.')
print('Finite certificates only; general theorem proofs and conjectures are not verified here.')
