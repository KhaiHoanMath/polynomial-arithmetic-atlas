#!/usr/bin/env python3
# Copyright © 2026 Khai-Hoan Nguyen-Dang. All rights reserved.
"""Write an author-only BibTeX export, preserving mathematics and accents."""
import argparse
import json
import re
import unicodedata
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
AUTHOR_ONLY=ROOT/'author-only'
COPYRIGHT='© 2026 Khai-Hoan Nguyen-Dang. All rights reserved.'

def plain_tex(s):
    replacements={'–':'--','—':'---','’':"'",'‘':"'",'“':'``','”':"''",'ℤ':r'$\mathbb{Z}$','ℚ':r'$\mathbb{Q}$','≥':r'$\geq$','≤':r'$\leq$','±':r'$\pm$','∞':r'$\infty$','−':'-','→':r'$\to$','ε':r'$\varepsilon$','α':r'$\alpha$','θ':r'$\theta$','μ':r'$\mu$','√':r'$\sqrt{}$','Ł':r'{\L}','ł':r'{\l}','ß':r'{\ss}','ø':r'{\o}','Ø':r'{\O}','ı':'i','×':r'$\times$','ℓ':r'$\ell$','≠':r'$\neq$','∈':r'$\in$','⊆':r'$\subseteq$','⋯':r'$\cdots$','²':r'$^2$','³':r'$^3$','⁴':r'$^4$'}
    accents={'\u0301':"'",'\u0300':'`','\u0302':'^','\u0308':'"','\u0303':'~','\u030c':'v','\u030b':'H','\u0306':'u','\u0327':'c','\u030a':'r','\u0304':'='}
    out=[]
    for ch in str(s):
        if ch in replacements:out.append(replacements[ch]);continue
        if ch in '&%#_':out.append('\\'+ch);continue
        if ch=='^':out.append(r'\textasciicircum{}');continue
        dec=unicodedata.normalize('NFD',ch)
        if len(dec)==2 and dec[1] in accents:out.append('{\\'+accents[dec[1]]+'{'+dec[0]+'}}')
        else:out.append(ch)
    return ''.join(out)

def tex(value):
    value=re.sub(r'\\\((.*?)\\\)',lambda m:'$'+m.group(1)+'$',str(value))
    # Trusted bibliographic math is kept as TeX, never escaped as ordinary text.
    return ''.join(part if i%2 else plain_tex(part) for i,part in enumerate(re.split(r'(\$[^$]*\$)',value)))

def render(records, checked):
    output=[f'% Polynomial Arithmetic Atlas. Literature checked through {checked}.\n% {COPYRIGHT}\n% Author-only export. Original annotations and compilation; cited works retain their own rights.\n% Selective bibliography; preprints and source limitations are recorded.\n']
    for r in records:
        kind=r.get('type','misc')
        if kind not in ['article','book','incollection','inproceedings','techreport','misc']:kind='misc'
        fields={}
        if r.get('editors'):fields['editor']=r['editors']
        else:fields['author']=r['authors']
        if r.get('editor'):fields['editor']=r['editor']
        fields['title']=r['title']
        if r.get('year'):fields['year']=str(r['year'])
        fields['publisher' if kind=='book' else 'booktitle' if kind in ['incollection','inproceedings'] else 'journal' if kind=='article' else 'institution' if kind=='techreport' else 'howpublished']=r.get('venue','')
        for k in ['volume','pages','edition','series','isbn','publisher']:
            if r.get(k):fields[k]=str(r[k]).replace('–','--')
        if r.get('issue'):fields['number']=r['issue']
        if r.get('report_number'):fields['number']=r['report_number']
        if r.get('article'):
            fields['eid']=str(r['article'])
            if not r.get('pages'):fields['pages']='Article '+str(r['article'])
        for k in ['doi','url']:
            if r.get(k):fields[k]=r[k]
        if r.get('arxiv'):fields['eprint']=r['arxiv'];fields['archivePrefix']='arXiv'
        fields['urldate']=r.get('accessed','2026-11-11')
        notes=[r.get('note',''),r.get('metadata_note','')]
        if r.get('article') and r.get('pages'):notes.append('Article '+str(r['article'])+'.')
        if r['kind'] in ['Preprint','Exposition','Resource'] or 'conditional' in r.get('status','').lower():notes.append(r.get('status',''))
        if any(notes):fields['note']=' '.join(n for n in notes if n)
        fields['annote']=r['annotation'];fields['keywords']=r.get('group',r.get('section',''))
        lines=['@'+kind+'{'+r['id']+',']
        for k,v in fields.items():
            if not v:continue
            v=str(v) if k in ['url','doi','eprint','urldate'] else tex(v)
            if k=='title':v='{'+v+'}'
            if k=='author' and ',' not in r['authors'] and ' and ' not in r['authors'] and any(w in r['authors'] for w in ['NIST','LMFDB','Developers','Team']):v='{'+v+'}'
            lines.append('  '+k+' = {'+v+'},')
        output.append('\n'.join(lines+['}\n']))
    return '\n'.join(output)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=AUTHOR_ONLY/'bibliography',help='Output directory under author-only/ (default: author-only/bibliography).')
    args=parser.parse_args()
    output=args.output_dir.resolve()
    target=(output/'atlas_references.bib').resolve()
    for path in (output,target):
        if any(path.is_relative_to(ROOT/folder) for folder in ('dist','static')):
            parser.error('Generated files must not be written under dist/ or static/.')
        if not path.is_relative_to(AUTHOR_ONLY):
            parser.error('Generated files must remain under the repository author-only/ directory.')
    catalogue=json.loads((ROOT/'content/references.json').read_text())
    records=catalogue['references']
    output.mkdir(parents=True,exist_ok=True)
    target.write_text(render(records,catalogue['checked_through']),encoding='utf-8')
    print(f'Exported {len(records)} BibTeX records to {target}.')
