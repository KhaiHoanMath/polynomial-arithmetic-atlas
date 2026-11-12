#!/usr/bin/env python3
# Copyright © 2026 Khai-Hoan Nguyen-Dang. All rights reserved.
"""Exact arithmetic certificates for the Polynomial Arithmetic Atlas.

Requires Python 3 and SymPy (verified with 1.14.0).
Run: python scripts/atlas_certificates.py [--check | --write]
The default verifies all examples without writing files. --check compares
with the repository data; --write regenerates that data. The source contains no numerical root approximations.
"""
from __future__ import annotations
import argparse
import itertools
import json
from fractions import Fraction
from pathlib import Path
import sympy as sp

x = sp.Symbol('x')
ROOT = Path(__file__).resolve().parents[1]
checks = 0

def verify(condition, message):
    global checks
    if not condition:
        raise AssertionError(message)
    checks += 1

def degrees_allowed(degrees):
    values = {0}
    for degree in degrees:
        values |= {n + degree for n in values}
    return sorted(values - {0, sum(degrees)})

def modular_record(f, p):
    fp = sp.Poly(f, x, modulus=p)
    unit, factors = fp.factor_list()
    product = sp.Poly(unit, x, modulus=p)
    degree_list = []
    parts = []
    for factor, multiplicity in factors:
        verify(factor.is_irreducible, f'factor at {p} must be irreducible')
        product *= factor ** multiplicity
        degree_list += [factor.degree()] * multiplicity
        term = sp.latex(factor.as_expr()).replace('\\left', '').replace('\\right', '')
        term = '(' + term + ')' if len(factors) > 1 or multiplicity > 1 else term
        if multiplicity > 1:
            term += '^{' + str(multiplicity) + '}'
        parts.append(term)
    verify(product == fp, f'exact modular product at {p}')
    squarefree = sp.gcd(fp, fp.diff()).degree() == 0
    verify(squarefree == all(m == 1 for _, m in factors), f'squarefree test at {p}')
    if unit != 1:
        parts.insert(0, sp.latex(unit))
    degrees = sorted(degree_list)
    allowed = degrees_allowed(degrees)
    if not squarefree:
        conclusion = 'The reduction has repeated factors, so the Frobenius cycle criterion does not apply. It still restricts factor degrees because the degree is preserved.'
    elif not allowed:
        conclusion = 'The irreducible reduction proves irreducibility over Q and gives a cycle of full length in the Galois group.'
    else:
        conclusion = 'The factor degrees are the cycle lengths of a Frobenius element. Every proper rational factor has one of the listed degrees.'
    return {'prime': p, 'latex': ''.join(parts), 'degrees': degrees,
            'squarefree': squarefree, 'allowed': allowed, 'conclusion': conclusion,
            'factors': [{'coefficients': [int(c) for c in factor.all_coeffs()], 'multiplicity': int(m)} for factor,m in factors]}

def valuation(a,p):
    a=abs(int(a));v=0
    while a and a%p==0:
        v+=1;a//=p
    return v

def newton_record(f,p):
    poly=sp.Poly(f,x)
    points=[(i,valuation(poly.nth(i),p)) for i in range(poly.degree()+1) if poly.nth(i)]
    hull=[]
    for point in points:
        while len(hull)>=2:
            a,b=hull[-2:]
            if (b[0]-a[0])*(point[1]-b[1])-(b[1]-a[1])*(point[0]-b[0]) <= 0:
                hull.pop()
            else:break
        hull.append(point)
    slopes=[Fraction(b[1]-a[1],b[0]-a[0]) for a,b in zip(hull,hull[1:])]
    values={0}
    for a,b,slope in zip(hull,hull[1:],slopes):
        length=b[0]-a[0]
        values={v+d for v in values for d in range(0,length+1,slope.denominator)}
    def latex_fraction(q):
        return str(q.numerator) if q.denominator==1 else ('-' if q<0 else '')+r'\frac{'+str(abs(q.numerator))+'}{'+str(q.denominator)+'}'
    return {'prime':p,'vertices':hull,'slopes':[latex_fraction(s) for s in slopes],'allowed':sorted(values-{0,poly.degree()}),'points':points}

def build():
    samples=[
      dict(id='selmer',shortTitle=r'\(x^5-x-1\)',title='A quintic with symmetric Galois group',latex=r'x^5-x-1',f=x**5-x-1,ps=[2,3,5,7,11],article='frobenius',
        intro='Reduction modulo 3 proves irreducibility. Reduction modulo 2 then determines the Galois group.',resultTitle=r'The group is \(S_5\).',
        result=r'<p>Modulo 3 the polynomial is irreducible. Its Galois group is therefore transitive of prime degree 5, hence primitive.</p><p>Modulo 2 the factor degrees are 2 and 3. Cubing the corresponding permutation leaves a single transposition. A primitive group containing a transposition is the full symmetric group.</p>'),
      dict(id='cyclotomic',shortTitle=r'\(x^4+1\)',title='An irreducible cyclotomic polynomial',latex=r'x^4+1',f=x**4+1,ps=[2,3,5,7,11,13,17],article='modular-irreducibility',
        intro='This polynomial is irreducible over Q but reducible modulo every prime.',resultTitle=r'Eisenstein after translation',
        result=r'<p>The shift is \(f(x+1)=x^4+4x^3+6x^2+4x+2\), which is Eisenstein at 2.</p><p>At an odd prime, every primitive eighth root of unity lies in \(\mathbb F_{p^2}\), since \(p^2\equiv1\pmod8\). All irreducible factors therefore have degree at most 2. The Galois group is \((\mathbb Z/8\mathbb Z)^\times\cong C_2^2\), which has no 4-cycle.</p>'),
      dict(id='eulerian',shortTitle=r'\(A_5(x)\)',title='A reciprocal quartic',latex=r'x^4+26x^3+66x^2+26x+1',f=x**4+26*x**3+66*x**2+26*x+1,ps=[2,11,13,17,23],article='eulerian',
        intro='Galois automorphisms permute the two inverse pairs of roots. The Galois group is therefore contained in the wreath product of order eight.',resultTitle=r'The group is \(C_2\wr S_2\).',
        result=r'<p>The irreducible reduction modulo 11 supplies a 4-cycle and proves irreducibility over \(\mathbb Q\). The factorization modulo 23 supplies a transposition.</p><p>Reciprocity bounds the group by \(C_2\wr S_2\), of order 8. A 4-cycle generates a subgroup of order 4, and a single transposition lies outside that cyclic subgroup. The generated subgroup has order 8, so it is the full wreath product.</p>'),
      dict(id='exponential',shortTitle=r'\(6!\,e_6(x)\)',title='Two Newton polygons',latex=r'720+720x+360x^2+120x^3+30x^4+6x^5+x^6',f=sum(sp.factorial(6)//sp.factorial(i)*x**i for i in range(7)),ps=[2,3,5,7,11],article='newton-polygons',
        intro='The coefficient valuations at 2 and 3 exclude all proper factor degrees.',resultTitle=r'Irreducibility',
        result=r'<p>At 2, the Newton polygon leaves only proper factor degrees 2 and 4. At 3, it leaves only degree 3. These sets have empty intersection, so the polynomial is irreducible over \(\mathbb Q\).</p><p>This argument uses valuations, not a squarefree Frobenius factorization. The reductions at 2 and 3 have repeated factors.</p>')]
    samples.append(dict(id='residual',shortTitle=r'\(x^4+2x^2+4\)',title='A residual polynomial',latex=r'x^4+2x^2+4',f=x**4+2*x**2+4,ps=[2,3,5,7],article='newton-polygons',
      intro='The Newton slope permits a quadratic factor. The residual polynomial rules it out.',resultTitle=r'Irreducible, with group \(V_4\).',
      result=r'<p>At 2 the single slope is \(-1/2\). Its residual polynomial is \(Y^2+Y+1\), irreducible over \(\mathbb F_2\). The residual criterion proves irreducibility over \(\mathbb Q_2\), hence over \(\mathbb Q\).</p><p>The four roots \((\pm\sqrt2\pm\sqrt{-6})/2\) generate \(\mathbb Q(\sqrt2,\sqrt{-6})\). Thus the group is \(V_4\); all its nonidentity elements act as double transpositions. A slope denominator 2 alone does not supply a single transposition.</p>'))
    result=[]
    for sample in samples:
        f=sample.pop('f');ps=sample.pop('ps')
        sample['primes']=[modular_record(f,p) for p in ps]
        sample['coefficients']=[int(c) for c in sp.Poly(f,x).all_coeffs()]
        sample['discriminant']=str(sp.discriminant(f,x))
        verify(sp.Poly(f,x).is_irreducible,'sample irreducibility cross-check over Q')
        if sample['id']=='exponential':
            sample['newton']=[newton_record(f,p) for p in [2,3]]
            verify(sample['newton'][0]['vertices']==[(0,4),(4,1),(6,0)],'Newton vertices at2')
            verify(sample['newton'][1]['vertices']==[(0,2),(6,0)],'Newton vertices at3')
            verify(not set(sample['newton'][0]['allowed'])&set(sample['newton'][1]['allowed']),'disjoint Newton degree constraints')
        if sample['id']=='residual':
            sample['newton']=[newton_record(f,2)]
            verify(sample['newton'][0]['vertices']==[(0,2),(4,0)],'residual quartic Newton edge')
            verify(sample['newton'][0]['allowed']==[2],'slope alone permits degree two')
            verify(sp.Poly(x*x+x+1,x,modulus=2).is_irreducible,'residual polynomial irreducible')
        result.append(sample)
    verify(result[0]['primes'][0]['degrees']==[2,3],'Selmer mod2')
    verify(result[0]['primes'][1]['degrees']==[5],'Selmer mod3')
    verify(result[2]['primes'][1]['degrees']==[4],'Eulerian mod11')
    verify(result[2]['primes'][-1]['degrees']==[1,1,2],'Eulerian mod23')
    verify(all(max(p['degrees'])<=2 for p in result[1]['primes']),'cyclotomic sample factor degrees')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group();mode.add_argument('--check',action='store_true');mode.add_argument('--write',action='store_true');args=parser.parse_args()
    result=build();output=ROOT/'content/data/laboratory.json'
    if args.check:
        # JSON comparison intentionally normalizes tuple/list representations.
        verify(json.loads(output.read_text())==json.loads(json.dumps(result)),'stored laboratory data matches exact generation')
    elif args.write:
        output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(f'{checks} exact arithmetic checks passed (SymPy {sp.__version__}).')
