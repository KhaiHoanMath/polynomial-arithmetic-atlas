#!/usr/bin/env python3
# Copyright © 2026 Khai-Hoan Nguyen-Dang. All rights reserved.
"""Exact identities used in the 12 November 2026 review.

Requires SymPy. These checks verify the displayed examples, not all cited
research proofs. Run from any directory: python3 review_certificates.py.
"""
import sympy as s
x,T=s.symbols('x T')
checks=[]
def verify(name, condition):
    assert condition, name
    checks.append(name)

# One generic cubic, four very different rational fibers.
f=x**3-3*x-T
verify('cubic discriminant formula',s.discriminant(f,x)==27*(4-T**2))
verify('reducible fiber at zero',s.expand(f.subs(T,0)-x*(x**2-3))==0)
verify('irreducible cyclic fiber at one',s.Poly(f.subs(T,1),x).is_irreducible and s.discriminant(f.subs(T,1),x)==81)
verify('branch fiber at two',s.expand(f.subs(T,2)-(x-2)*(x+1)**2)==0)
verify('symmetric fiber at three',s.Poly(f.subs(T,3),x).is_irreducible and s.discriminant(f.subs(T,3),x)==-135)

# The residual-polynomial certificate and its noncyclic quartic group.
g=x**4+2*x**2+4
residual=s.Poly(T**2+T+1,T,modulus=2)
verify('irreducible residual polynomial',residual.is_irreducible)
a=(s.sqrt(2)+s.sqrt(-6))/2;b=(s.sqrt(2)-s.sqrt(-6))/2
verify('quartic radical roots',all(s.simplify(g.subs(x,r))==0 for r in [a,-a,b,-b]))
verify('quartic radical product',s.simplify((x-a)*(x+a)*(x-b)*(x+b)-g)==0)
verify('recover both quadratic generators',s.simplify(a+b-s.sqrt(2))==0 and s.simplify(a-b-s.sqrt(-6))==0)
verify('quartic discriminant',s.discriminant(g,x)==2**10*3**2)

# Evaluate the defining Laguerre formula rather than relying on a name convention.
def laguerre(n,alpha):
    return s.expand(sum(s.binomial(n+alpha,n-j)*(-x)**j/s.factorial(j) for j in range(n+1)))
verify('ordinary Laguerre exception',s.expand(laguerre(2,s.Rational(1,4))-(4*x-3)*(4*x-15)/32)==0)
verify('power substitution boundary',s.expand(laguerre(1,s.Rational(-3,4)).subs(x,x**4)-(s.Rational(1,2)-x**2)*(s.Rational(1,2)+x**2))==0)
he1=x;he3=x**3-3*x
verify('Wronskian unit remainder',s.expand((he1*s.diff(he3,x)-s.diff(he1,x)*he3)/2)==x**3)

# Adjusted critical values for x^2+2/3, including the exact level-four relation.
a=s.Rational(2,3);v=s.Integer(0);orbit=[]
for _ in range(4):v=v*v+a;orbit.append(v)
c=[-orbit[0],*orbit[1:]]
verify('critical orbit values',c==[s.Rational(-2,3),s.Rational(10,9),s.Rational(154,81),s.Rational(28090,6561)])
verify('level-four square relation',c[1]*c[3]==s.Rational(530,243)**2)

# A Frobenius modular-composition identity.
mod=s.Poly(x**3+x+1,x,modulus=2)
verify('Frobenius modular composition',s.rem(s.Poly((x**2+x)**2-x,x,modulus=2),mod).is_zero)

# Quartic resolvent conventions in the worked C4 / D4 / S4 examples.
for f in [x**4+x**3+x**2+x+1,x**4-2,x**4+2*x+2]:
    _,a,b,c,d=s.Poly(f,x).all_coeffs()
    R=T**3-b*T**2+(a*c-4*d)*T+4*b*d-a*a*d-c*c
    verify('resolvent discriminant: '+str(f),s.discriminant(f,x)==s.discriminant(R,T))
print(f'Passed {len(checks)} exact identity and factorization checks.')
for name in checks:print('  '+name)
