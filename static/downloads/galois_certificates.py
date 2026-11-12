#!/usr/bin/env python3
"""Exact checks for the Polynomial Arithmetic Atlas's small Galois certificates.

Run with Python 3.10+ and SymPy 1.14: python galois_certificates.py
No numerical root approximations and no black-box Galois-group routine are used.
The finite-field, discriminant, and resolvent calculations below support the
explicit group-theoretic proofs in the accompanying articles. They do not
replace those proofs by a group label.
"""
import json
from math import isqrt
import sympy as sp

x, T = sp.symbols('x T')


def check(condition, description):
    if not condition:
        raise RuntimeError('Certificate failed: ' + description)


def roots_mod(poly, p):
    return [a for a in range(p) if int(poly.subs(x, a)) % p == 0]


def rem_mod(f, g, p):
    return sp.Poly(f, x, modulus=p).rem(sp.Poly(g, x, modulus=p)).as_expr()


def eisenstein(f, p):
    cs = [int(c) for c in sp.Poly(f, x).all_coeffs()]
    return (cs[0] % p != 0 and all(c % p == 0 for c in cs[1:])
            and cs[-1] % (p*p) != 0)


def quartic_resolvent(f):
    cs = sp.Poly(f, x).all_coeffs()
    check(len(cs) == 5 and cs[0] == 1, 'monic quartic input')
    _, a, b, c, d = cs
    return T**3-b*T**2+(a*c-4*d)*T+4*b*d-a*a*d-c*c


def main():
    f = x**5-x-1
    qs = [x**2+1, x**2+x+2, x**2+2*x+2]
    check(not roots_mod(f, 3), 'quintic has no linear factor mod 3')
    # Exhaust all monic quadratic polynomials: irreducible iff rootless.
    actual = [x*x+a*x+b for a in range(3) for b in range(3)
              if not roots_mod(x*x+a*x+b, 3)]
    check(actual == qs, 'complete list of irreducible quadratics over F3')
    remainders = [rem_mod(f, q, 3) for q in qs]
    check(remainders == [-1, x-1, x-1], 'mod 3 quadratic remainders')
    # A reducible quintic has an irreducible factor of degree <=2.
    q2, q3 = x*x+x+1, x**3+x*x+1
    check(sp.Poly(f-q2*q3, x, modulus=2).is_zero, 'mod 2 factor product')
    check(not roots_mod(q2, 2) and not roots_mod(q3, 2),
          'quadratic and cubic factors are irreducible over F2')
    check(sp.gcd(sp.Poly(q2, x, modulus=2), sp.Poly(q3, x, modulus=2)).degree() == 0,
          'mod 2 factors are distinct and coprime')
    check(int(sp.discriminant(f, x)) == 2869, 'quintic discriminant')

    quartic = x**4+2*x+2
    check(eisenstein(quartic, 2), 'quartic Eisenstein at 2')
    R = quartic_resolvent(quartic)
    check(R == T**3-8*T-4, 'quartic cubic resolvent')
    candidates = [-4, -2, -1, 1, 2, 4]
    values = [int(R.subs(T, t)) for t in candidates]
    check(values == [-36, 4, 3, -11, -12, 28], 'all rational-root candidates excluded')
    D = int(sp.discriminant(quartic, x))
    check(D == 1616 == int(sp.discriminant(R, T)), 'equal quartic/resolvent discriminants')
    check(isqrt(D)**2 != D, 'nonsquare discriminant')
    check(D == 16*101, 'square-class simplification')

    b = x**4+x
    fixed = []
    for a in range(16):
        h = sum(((a >> i) & 1)*x**i for i in range(4))
        if rem_mod(h*h-h, b, 2) == 0:
            fixed.append(h)
    check(len(fixed) == 8, 'Frobenius-fixed subspace has dimension 3')
    for h in [1+0*x, x*x+x, x**3]:
        check(rem_mod(h*h-h, b, 2) == 0, 'listed Berlekamp basis vector is fixed')
    check(sp.Poly(x*(x+1)*(x*x+x+1)-b, x, modulus=2).is_zero,
          'Berlekamp factor product over F2')
    check(not roots_mod(x*x+x+1, 2), 'remaining Berlekamp quadratic is irreducible')

    real_f = x**5-4*x+2
    check(eisenstein(real_f, 2), 'real-root example Eisenstein at 2')
    check(sp.Rational(4,5) > sp.Rational(5,8)**4, 'exact critical-value inequality')
    real_count = sp.Poly(real_f, x).count_roots(-sp.oo, sp.oo)
    check(real_count == 3, 'Sturm count gives three real roots')
    check(int(sp.discriminant(x**4+1, x)) == 256, 'cyclotomic discriminant')
    check(int(sp.discriminant(x**4-2, x)) == -2048, 'dihedral discriminant')

    result = {
        'status': 'All exact checks passed',
        'sympy_version': sp.__version__,
        'coefficient_field': 'Q, with specified finite-field reductions',
        'used_numerical_roots': False,
        'used_galois_group_black_box': False,
        'quintic': {'polynomial': str(f), 'mod_3_quadratic_remainders': list(map(str, remainders)),
                    'mod_2_factors': [str(q2), str(q3)], 'cycle_types': [[5], [2,3]],
                    'discriminant': 2869,
                    'group_conclusion': 'S5 by the primitive-transposition theorem'},
        'quartic': {'polynomial': str(quartic), 'resolvent': str(R),
                    'rational_root_candidates': candidates, 'values': values,
                    'discriminant': D, 'group_conclusion': 'S4 by the cubic-resolvent classification'},
        'berlekamp': {'polynomial': str(b), 'field': 'F2', 'fixed_space_dimension': 3,
                      'factorization': ['x', 'x+1', 'x^2+x+1']},
        'real_root_example': {'polynomial': str(real_f), 'exact_real_roots': int(real_count),
                              'group_conclusion': 'S5 by Eisenstein, prime degree, and complex conjugation'}
    }
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
