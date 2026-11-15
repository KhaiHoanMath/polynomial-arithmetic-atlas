#!/usr/bin/env python3
# Copyright © 2026 Khai-Hoan Nguyen-Dang. All rights reserved.
"""Exact checks for displayed diagram examples, not proof certification of preprints."""
from fractions import Fraction
from math import comb, factorial, gcd, isqrt
import sympy as S

x = S.symbols('x')

def factor_degrees(poly, prime):
    return sorted(g.degree() for g, multiplicity in S.Poly(poly, x, modulus=prime).factor_list()[1]
                  for _ in range(multiplicity))

def power_mod(base, exponent, modulus):
    result = S.Poly(1, x, modulus=modulus.get_modulus())
    while exponent:
        if exponent & 1:
            result = (result * base).rem(modulus)
        base = (base * base).rem(modulus)
        exponent >>= 1
    return result

def valuation(value, prime):
    value = Fraction(value)
    assert value
    def integer_order(n):
        n = abs(n)
        count = 0
        while n % prime == 0:
            count += 1
            n //= prime
        return count
    return integer_order(value.numerator) - integer_order(value.denominator)

def square(n):
    return n >= 0 and isqrt(n) ** 2 == n

def check_local_certificates():
    quartic = x**4 + x**3 + x + 2
    assert factor_degrees(quartic, 2) == [1, 3]
    assert factor_degrees(quartic, 3) == [2, 2]
    quintic = x**5 - x - 1
    assert factor_degrees(quintic, 2) == [2, 3]
    assert factor_degrees(quintic, 3) == [5]
    assert S.discriminant(quintic, x) == 2869 == 19 * 151
    f = S.Poly(quintic, x, modulus=3)
    X = S.Poly(x, x, modulus=3)
    assert (power_mod(X, 3**5, f) - X).is_zero
    assert S.gcd(f, power_mod(X, 3, f) - X).degree() == 0
    reciprocal = x**4 - x**2 + 1
    assert reciprocal == S.cyclotomic_poly(12, x)
    assert S.polys.numberfields.galois_group(reciprocal, x)[0].order() == 4
    print('Local certificates: incompatible degree sets, S5 witnesses, discriminant, and reciprocal kernel example.')

def check_legendre_values():
    total = 0
    for prime in [2, 3, 5, 7, 11, 13]:
        values = [Fraction(1), Fraction(prime)]
        for n in range(1, 150):
            values.append(((2*n+1)*prime*values[-1] - n*values[-2])/(n+1))
        orders = [valuation(v, prime) for v in values]
        for n, value in enumerate(values):
            expected = valuation(Fraction(comb(n, n//2), 2**n), prime)
            if n % 2:
                expected += valuation(prime*(n+1), prime)
            assert orders[n] == expected
            if prime != 2:
                q, a = divmod(n, prime)
                assert orders[n] == orders[q] + (q % 2 if a % 2 == 0 else 1-q % 2)
            total += 1
        if prime == 3:
            assert values[13] == 1409933619 and orders[13] == 2
    witnesses = {(-1,-1):(53,13),(-1,1):(5,11),(1,-1):(11,19),(1,1):(17,67)}
    for (lam, mu), (p, q) in witnesses.items():
        polynomial = S.Poly(S.jacobi(5, S.Rational(lam,3), S.Rational(mu,2), x), x).clear_denoms()[1].primitive()[1]
        assert factor_degrees(polynomial.as_expr(), p) == [5]
        assert factor_degrees(polynomial.as_expr(), q) == [2,3]
        assert S.discriminant(polynomial.as_expr(), x) % (p*q) != 0
    print(f'Legendre/Jacobi: {total} exact valuation values and digit recurrences; four independent S5 certificates.')

def check_laguerre_and_taylor():
    for m in range(2,32):
        a=m*m-2
        polynomial=S.expand(2*S.assoc_laguerre(2,a,x))
        assert S.expand(polynomial-(x-(a+2-m))*(x-(a+2+m))) == 0
    assert S.expand(24*S.assoc_laguerre(4,5,x)-(x-6)*(x**3-30*x**2+252*x-504)) == 0
    assert S.expand(24*S.assoc_laguerre(4,23,x)-(x-30)*(x**3-78*x**2+1872*x-14040)) == 0
    exceptions={(60,61),(61,64),(64,65),(68,69),(72,73),(76,77),(80,81),(81,80),(84,85),(88,89)}
    observed=set()
    for n in range(2,181):
        for s in range(61,93):
            # Square class of Schur's monic discriminant; even powers removed.
            kernel=(-1)**(n*(n-1)//2)
            for j in range(1,n+1):
                kernel *= j if j % 2 else n+s+1-j
            if square(kernel):
                observed.add((n,s))
    assert observed == exceptions
    for n in range(2,25):
        polynomial=sum(S.binomial(2*j,j)*x**j for j in range(n+1))
        discriminant=int(S.discriminant(polynomial,x))
        exceptional=any(n==2*r*(r+1) for r in range(1,n+1))
        assert square(discriminant) == exceptional
    print('Laguerre/Taylor: all 32 displayed positive exceptions, 5728 negative-strip square classes, and 23 central-binomial discriminants.')

def check_trace_normalization():
    # The monic shifted Jacobi example J_2^(0,0)=x^2-x+1/6.
    # Compute the power sums from the companion matrix, independently of the
    # printed diagonal formula discussed in orthogonal-families#jacobi-trace-forms.
    companion = S.Matrix([[0, -S.Rational(1,6)], [1, 1]])
    gram = S.Matrix(2, 2, lambda i,j: S.trace(companion**(i+j)))
    assert gram == S.Matrix([[2,1], [1,S.Rational(2,3)]])
    assert gram.det() == S.Rational(1,3)
    assert [gram[0,0], gram.det()/gram[0,0]] == [2,S.Rational(1,6)]
    # v1 Theorem 6 prints D_0=2/5 and D_1=2/3 at these parameters.
    ratio = (S.Rational(2,5)*S.Rational(2,3))/gram.det()
    assert ratio == S.Rational(4,5)
    assert not (square(int(S.numer(ratio))) and square(int(S.denom(ratio))))
    print('Trace-form normalization: exact quadratic Gram matrix and diagonal ratios checked.')

def check_fixed_field_and_iteration():
    phi=S.Poly(S.cyclotomic_poly(24,x),x,domain=S.QQ)
    value=S.Poly(0,x,domain=S.QQ)
    for d in S.divisors(21):
        value += int(S.mobius(d))*S.Poly(x**d,x)*S.invert(S.Poly(1-x**d,x),phi)
    assert value.rem(phi) == S.Poly(x**6,x,domain=S.QQ)
    primes=[p for p in list(S.primerange(5,44)) if p != 7]
    for p in primes:
        N=21*p
        residue=S.Poly(sum(x**(a % 24) for a in range(1,N+1) if gcd(a,N)==1),x).rem(phi)
        assert residue.is_zero == (p % 4 == 1)
    c=S.Rational(3,2)
    first=-c
    second=c*c+c
    assert first == -S.Rational(6,4) and second == S.Rational(15,4)
    assert all(not square(int(v)) for v in [-6,15,-90])
    iterate=S.expand((x*x+c)**2+c)
    assert S.polys.numberfields.galois_group(iterate,x)[0].order() == 8
    print(f'Fixed fields and iteration: R21(zeta24)=i; {len(primes)} prime extensions; c=3/2 has full level-two group.')

if __name__ == '__main__':
    check_local_certificates()
    check_legendre_values()
    check_laguerre_and_taylor()
    check_trace_normalization()
    check_fixed_field_and_iteration()
