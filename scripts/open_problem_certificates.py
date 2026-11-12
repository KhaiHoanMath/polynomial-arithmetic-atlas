#!/usr/bin/env python3
# Copyright © 2026 Khai-Hoan Nguyen-Dang. All rights reserved.
"""Exact calculations for the open-problem additions of 12 November 2026.

Requires SymPy. Run: python3 scripts/open_problem_certificates.py
These finite checks verify displayed examples and normalization boundaries.
They do not verify the cited research proofs, computation ranges, or conjectures.
"""
from functools import lru_cache
from itertools import combinations
from math import gcd, isqrt

import sympy as s

x, y, q, c = s.symbols('x y q c')
checks = []


def verify(name, condition):
    if not bool(condition):
        raise AssertionError(name)
    checks.append(name)


def equal(left, right):
    return s.cancel(left - right) == 0


def rational_square(value):
    value = s.Rational(value)
    num, den = map(int, value.as_numer_denom())
    return num >= 0 and isqrt(num) ** 2 == num and isqrt(den) ** 2 == den


# Modular forms: compute finite q-expansions directly from their definitions.
def truncate(expression, order):
    return s.Poly(s.expand(expression), q).rem(s.Poly(q ** (order + 1), q)).as_expr()


def eisenstein(weight, order):
    return 1 - s.Rational(2 * weight) / s.bernoulli(weight) * sum(
        s.divisor_sigma(n, weight - 1) * q ** n for n in range(1, order + 1)
    )


def delta(order):
    product = s.Integer(1)
    for n in range(1, order):
        factor = sum((-1) ** j * s.binomial(24, j) * q ** (n * j)
                     for j in range(min(24, (order - 1) // n) + 1))
        product = truncate(product * factor, order - 1)
    return s.expand(q * product)


order = 6
E4, Delta = eisenstein(4, order), delta(order)
f = truncate(Delta * E4 ** 3, order)
g = truncate(Delta ** 2, order)
verify('Delta coefficients through q^4',
       [Delta.coeff(q, j) for j in range(1, 5)] == [1, -24, 252, -1472])


def hecke_two(series, weight, output_order):
    return sum((series.coeff(q, 2 * n) +
                (2 ** (weight - 1) * series.coeff(q, n // 2) if n % 2 == 0 else 0))
               * q ** n for n in range(1, output_order + 1))


# In the basis f=Delta E4^3, g=Delta^2, q and q^2 determine coordinates.
T2f, T2g = hecke_two(f, 24, 3), hecke_two(g, 24, 3)
verify('weight-24 T2 first column through q^3',
       equal(T2f, truncate(696 * f + 20736000 * g, 3)))
verify('weight-24 T2 second column through q^3',
       equal(T2g, truncate(f + 384 * g, 3)))
H = s.Matrix([[696, 1], [20736000, 384]]).charpoly(x).as_expr()
verify('weight-24 Hecke characteristic polynomial', equal(H, x ** 2 - 1080 * x - 20468736))
verify('weight-24 discriminant', s.discriminant(H, x) == 576 * 144169)
verify('weight-24 nonsquare certificate', 379 ** 2 < 144169 < 380 ** 2)

# E16=E4^4-(3456000/3617) Delta E4, hence the displayed j-polynomial.
# This checks coefficients through q^6, not an independent modular-form proof.
verify('E16 normalization through q^6', equal(
    truncate(eisenstein(16, order) - E4 ** 4 + s.Rational(3456000, 3617) * Delta * E4, order), 0))


# Critical-parameter polynomials, obtained from the defining recurrences.
def critical_orbit(degree, count):
    values = [s.Integer(0)]
    for _ in range(count):
        values.append(s.expand(values[-1] ** degree + c))
    return values


def gleason(period):
    orbit = critical_orbit(2, period)
    return s.cancel(s.prod(orbit[d] ** s.mobius(period // d) for d in s.divisors(period)))


G1, G2, G3, G4 = [gleason(n) for n in range(1, 5)]
verify('first three Gleason polynomials',
       equal(G1, c) and equal(G2, c + 1) and equal(G3, c ** 3 + 2 * c ** 2 + c + 1))
G3mod2 = s.Poly(G3, c, modulus=2)
verify('Gleason cubic modulo two', G3mod2 == s.Poly(c ** 3 + c + 1, c, modulus=2)
       and all(G3mod2.eval(a) != 0 for a in (0, 1)))
verify('Gleason cubic discriminant', s.discriminant(G3, c) == -23)
G4factors = s.factor_list(s.Poly(G4, c, modulus=2))[1]
verify('period-four Gleason modular factor degrees',
       sorted(factor.degree() for factor, mult in G4factors for _ in range(mult)) == [2, 4])


def quadratic_misiurewicz(tail, period):
    orbit = critical_orbit(2, tail + period - 1)
    numerator = s.prod((orbit[tail + k - 1] + orbit[tail - 1]) ** s.mobius(period // k)
                       for k in s.divisors(period))
    denominator = s.prod(orbit[k] ** s.mobius(period // k) for k in s.divisors(period)) \
        if (tail - 1) % period == 0 else 1
    return s.cancel(numerator / denominator)


verify('Misiurewicz G_(2,1)', equal(quadratic_misiurewicz(2, 1), c + 2))
verify('tail-two period-one orbit at c=-2', [-2, (-2) ** 2 - 2, 2 ** 2 - 2] == [-2, 2, 2])
verify('Buff normalization: degree-seven period-three cyclotomic factor',
       s.rem(x * (x + 1) ** 7 + 1, x ** 2 + x + 1, x) == 0)

# The squareclass test is exact, with no numerical square-root decisions.
for parameter, square_root in [(s.Rational(2, 3), s.Rational(530, 243)),
                               (s.Rational(-6, 7), s.Rational(2262, 16807))]:
    orbit = [-parameter]
    for _ in range(3):
        orbit.append(orbit[-1] ** 2 + parameter)
    products = [s.prod(orbit[j] for j in range(3) if mask & (1 << j)) for mask in range(1, 8)]
    verify(f'Stoll a={parameter}: first three squareclasses independent',
           all(not rational_square(product) for product in products))
    verify(f'Stoll a={parameter}: level-four square relation', orbit[1] * orbit[3] == square_root ** 2)


# Touchard polynomials: T_(n+1)=x(T_n+T_n').
T = s.Integer(1)
touchard = [T]
for _ in range(4):
    T = s.expand(x * (T + s.diff(T, x)))
    touchard.append(T)
Q3, Q4 = [s.cancel(touchard[n] / x) for n in (3, 4)]
verify('Touchard examples from recurrence', equal(Q3, x ** 2 + 3 * x + 1)
       and equal(Q4, x ** 3 + 6 * x ** 2 + 7 * x + 1))
verify('Touchard discriminants', s.discriminant(Q3, x) == 5 and s.discriminant(Q4, x) == 257)
verify('Touchard cubic rational-root test', Q4.subs(x, 1) == 15 and Q4.subs(x, -1) == -1)
verify('Touchard n=2 exceptional alternating sum', touchard[2].subs(x, -1) == 0)


# Graph polynomials are computed by subset sums, independently of cycle formulas.
def subset_components(vertex_count, edges, selected):
    parent = list(range(vertex_count))

    def root(v):
        while parent[v] != v:
            v = parent[v]
        return v

    for index in selected:
        u, v = edges[index]
        parent[root(u)] = root(v)
    return len({root(v) for v in range(vertex_count)})


def graph_polynomials(vertex_count, edges):
    rank = vertex_count - subset_components(vertex_count, edges, range(len(edges)))
    chromatic, tutte = 0, 0
    for size in range(len(edges) + 1):
        for subset in combinations(range(len(edges)), size):
            components = subset_components(vertex_count, edges, subset)
            subset_rank = vertex_count - components
            chromatic += (-1) ** size * q ** components
            tutte += (x - 1) ** (rank - subset_rank) * (y - 1) ** (size - subset_rank)
    return s.expand(chromatic), s.expand(tutte)


C4, TC4 = graph_polynomials(4, [(j, (j + 1) % 4) for j in range(4)])
C7, _ = graph_polynomials(7, [(j, (j + 1) % 7) for j in range(7)])
verify('four-cycle chromatic factorization', equal(C4, q * (q - 1) * (q ** 2 - 3 * q + 3)))
verify('seven-cycle chromatic factorization',
       equal(C7, q * (q - 1) * (q - 2) * (q ** 2 - q + 1) * (q ** 2 - 3 * q + 3)))
verify('cycle quadratic factors share discriminant -3',
       s.discriminant(q ** 2 - q + 1, q) == s.discriminant(q ** 2 - 3 * q + 3, q) == -3)
verify('four-cycle Tutte polynomial', equal(TC4, x ** 3 + x ** 2 + x + y))
D = s.discriminant(TC4, x)
verify('four-cycle Tutte discriminant', equal(D, -27 * y ** 2 + 14 * y - 3))
verify('Tutte discriminant has simple zeros', s.gcd(s.Poly(D, y), s.Poly(s.diff(D, y), y)).degree() == 0)
verify('four-cycle Tutte specialization', equal(TC4.subs(y, 0), x * (x ** 2 + x + 1)))
_, path_tutte = graph_polynomials(3, [(0, 1), (1, 2)])
verify('two-edge path Tutte boundary', path_tutte == x ** 2)


# Sparse polynomials and coefficient-modification boundaries.
@lru_cache(None)
def stern_zero_one(n):
    if n < 2:
        return s.Integer(n)
    half = n // 2
    if n % 2 == 0:
        return s.expand(stern_zero_one(half).subs(x, x ** 2))
    return s.expand(x * stern_zero_one(half).subs(x, x ** 2) + stern_zero_one(half + 1).subs(x, x ** 2))


@lru_cache(None)
def stern_other(n):
    if n < 2:
        return s.Integer(n)
    half = n // 2
    return s.expand(x * stern_other(half) if n % 2 == 0 else stern_other(half) + stern_other(half + 1))


verify('Stern a17 recurrence', stern_zero_one(17) == x ** 8 + x ** 4 + x ** 2 + x + 1)
verify('Stern a17 factorization', equal(stern_zero_one(17), s.cyclotomic_poly(5, x) * (x ** 4 - x ** 3 + 1)))
verify('two Stern conventions at index five', stern_zero_one(5) == 1 + x + x ** 2 and stern_other(5) == 1 + 2 * x)
newman_factors = [1 + x + x ** 3, 1 + x ** 4 + x ** 9]
newman = s.expand(s.prod(newman_factors))
verify('nine-term Newman product', newman == 1 + x + x ** 3 + x ** 4 + x ** 5 + x ** 7 + x ** 9 + x ** 10 + x ** 12)
verify('Newman product has no cyclotomic factor',
       all(not factor.is_cyclotomic for polynomial in newman_factors
           for factor, _ in s.factor_list(s.Poly(polynomial, x))[1]))
n = s.symbols('n', integer=True)
verify('quadratic truncated-binomial discriminant',
       equal(s.discriminant(1 + n * x + n * (n - 1) * x ** 2 / 2, x), n * (2 - n)))
F23 = sum(s.binomial(2 - j + 3, 2 - j) * x ** j / s.factorial(j) for j in range(3))
verify('Laguerre coefficient-modification boundary', equal(2 * F23 - 40, (x - 2) * (x + 10)))

# Binary degree-eight pentanomial: Rabin/Frobenius irreducibility certificate.
binary = s.Poly(x ** 8 + x ** 4 + x ** 3 + x + 1, x, modulus=2)
verify('binary pentanomial: Frobenius congruence', s.Poly(x ** 256 - x, x, modulus=2).rem(binary).is_zero)
verify('binary pentanomial: proper-subfield gcd',
       s.gcd(binary, s.Poly(x ** 16 - x, x, modulus=2)).degree() == 0)


# Fekete boundaries: principal and quadratic characters are kept separate.
def quadratic_fekete(discriminant):
    return s.Poly(sum(s.kronecker_symbol(discriminant, a) * x ** a
                      for a in range(1, abs(discriminant))), x)


for discriminant in (5, 8, 12):
    factors = s.factor_list(quadratic_fekete(discriminant))[1]
    verify(f'Fekete Delta={discriminant}: cyclotomic-only remainder',
           all(factor.as_expr() == x or factor.is_cyclotomic for factor, _ in factors))


def trace_polynomial(polynomial):
    degree = s.degree(polynomial, x)
    verify(f'reciprocal degree {degree} is even', degree % 2 == 0)
    half = degree // 2
    remainder = s.expand(polynomial)
    trace = 0
    for j in range(half, -1, -1):
        coefficient = remainder.coeff(x, half + j)
        trace += coefficient * y ** j
        remainder = s.expand(remainder - coefficient * x ** half * (x + 1 / x) ** j)
    verify(f'reciprocal trace identity in degree {degree}', remainder == 0)
    return s.Poly(trace, y)


for p, smaller_prime, expected_degree, expected_square in [(5, 3, 6, True), (7, 3, 16, False), (7, 5, 22, True)]:
    modulus = p * smaller_prime
    orders = ({d for d in s.divisors(p - 1) if d > 1 and d != smaller_prime}
              | {d for d in s.divisors(smaller_prime - 1) if d > 1}
              | {d for d in s.divisors(gcd(modulus + 1, p + smaller_prime)) if d > 1})
    principal = sum(x ** a for a in range(1, modulus) if gcd(a, modulus) == 1)
    divisor = x * s.prod(s.cyclotomic_poly(d, x) for d in orders)
    remainder, division_remainder = s.div(principal, divisor, x)
    verify(f'principal Fekete n={modulus}: exact division', division_remainder == 0)
    poly = s.Poly(remainder, x)
    trace = trace_polynomial(remainder)
    verify(f'principal Fekete n={modulus}: degree and monicity', poly.degree() == expected_degree and poly.LC() == 1)
    verify(f'principal Fekete n={modulus}: irreducibility of both factors', poly.is_irreducible and trace.is_irreducible)
    verify(f'principal Fekete n={modulus}: discriminant squareclass', rational_square(poly.discriminant()) == expected_square)

for p in (5, 13, 17):
    F = quadratic_fekete(-3 * p).as_expr()
    divisor = x * s.cyclotomic_poly(1, x) * s.cyclotomic_poly(3, x) * s.cyclotomic_poly(p, x)
    h, remainder = s.div(-F, divisor, x)
    verify(f'quadratic Fekete Delta={-3*p}: division and degree', remainder == 0 and s.degree(h, x) == 2 * (p - 2))
    trace_polynomial(h)
    verify(f'quadratic Fekete Delta={-3*p}: sample discriminant squareclass',
           rational_square(s.discriminant(h, x)) == (p % 8 == 5))

print(f'Passed {len(checks)} exact example and boundary checks.')
for name in checks:
    print('  ' + name)
print('Scope: finite examples and identities only; no general conjecture or cited proof is certified.')
