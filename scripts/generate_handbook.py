# Copyright © 2026 Khai-Hoan Nguyen-Dang. All rights reserved.
"""Create an optional author-only handbook from the site's final JSON.

Write standalone TeX and a source manifest under author-only/. This script does
not compile a PDF or place files in the published website.
"""
import json, re, html, hashlib, argparse
from html.parser import HTMLParser
from pathlib import Path
from datetime import date

HERE=Path(__file__).resolve().parent
arguments=argparse.ArgumentParser(description=__doc__)
arguments.add_argument('--site-root',type=Path,default=HERE.parent, help='Repository root; defaults to the parent of the script directory.')
arguments.add_argument('--output-dir',type=Path, help='Output directory under the repository author-only/ directory (default: author-only/handbook).')
options=arguments.parse_args()
REPO=options.site_root.resolve()
AUTHOR_ONLY=REPO/'author-only'
AUTHOR='Khai-Hoan Nguyen-Dang'
COPYRIGHT=f'© 2026 {AUTHOR}. All rights reserved.'

def author_output(path):
    resolved=path.resolve()
    if any(resolved.is_relative_to(REPO/folder) for folder in ('dist','static')):
        arguments.error('Generated files must not be written under dist/ or static/.')
    if not resolved.is_relative_to(AUTHOR_ONLY):
        arguments.error('Generated files must remain under the repository author-only/ directory.')
    return resolved

OUT=author_output(options.output_dir or AUTHOR_ONLY/'handbook')
TEX_OUTPUT=author_output(OUT/'polynomial_arithmetic_atlas_handbook.tex')
MANIFEST_OUTPUT=author_output(OUT/'handbook-manifest.json')
OUT.mkdir(parents=True,exist_ok=True)
read=lambda p: json.loads((REPO/p).read_text())
subjects=read('content/subjects.json')
catalogue=read('content/references.json'); refs=catalogue['references']
review_date=date.fromisoformat(catalogue['checked_through'])
review_date_long=f'{review_date.day} {review_date.strftime("%B")} {review_date.year}'
navigation=read('content/navigation.json')
articles=[a for f in sorted((REPO/'content/articles').glob('*.json')) for a in json.loads(f.read_text())]
byid={a['id']:a for a in articles}; byref={r['id']:r for r in refs}
order=['foundations','modular-irreducibility','eisenstein-dumas','newton-polygons','archimedean-criteria','integer-values','sparse-gaps','capelli-composition','frobenius','discriminants','ramification-inertia','permutation-groups','resolvents','reciprocity','trinomials','taylor','laguerre','orthogonal-families','krawtchouk','kaneko-zagier','laguerre-negative-parameters','eulerian','bernoulli-euler','fekete','truncated-binomial','stern-polynomials','newman-pentanomials','touchard','chromatic-polynomials','tutte-polynomials','hecke-polynomials','eisenstein-zero-polynomials','height-counting','random-models','littlewood','factor-reversal','random-matrices','random-reciprocal','twisted-reciprocity','specialization','critical-points-monodromy','inverse-galois','composition-iteration','critical-parameter-polynomials','finite-field-irreducibility','finite-field-constructions','sparse-finite-fields','factorization-algorithms','galois-computation','multivariate-irreducibility']
articles.sort(key=lambda a:order.index(a['id']) if a['id'] in order else 999)

MATH=re.compile(r'\\\[([\s\S]*?)\\\]|\\\(([\s\S]*?)\\\)')
math_count=0
unicode_math={'≥':r'\ge','≤':r'\le','−':'-','↦':r'\mapsto','±':r'\pm','μ':r'\mu','∈':r'\in','→':r'\to','∞':r'\infty','α':r'\alpha','δ':r'\delta','ℤ':r'\mathbb Z','ε':r'\varepsilon','√':r'\surd','⋯':r'\cdots','≠':r'\ne','²':'{}^2','⁴':'{}^4','⁶':'{}^6','ⁿ':'{}^n','₂':'{}_2','₃':'{}_3','₄':'{}_4','₅':'{}_5','ₙ':'{}_n'}
unicode_math.update({'≡':r'\equiv','₆':'{}_6','φ':r'\varphi','∖':r'\setminus','ζ':r'\zeta','ℓ':r'\ell','₀':'{}_0'})
def plain(s):
    s=str(s or '').replace('–','-').replace('—','-').replace('‑','-').replace('’',"'").replace('“','``').replace('”',"''").replace('·', ' / ')
    escaped=[]
    specials={'\\':r'\textbackslash{}','{':r'\{','}':r'\}','%':r'\%','&':r'\&','#':r'\#','_':r'\_\allowbreak{}','$':r'\$','^':r'\textasciicircum{}','~':r'\textasciitilde{}'}
    for c in s:
        if c in unicode_math:escaped.append(r'\ensuremath{'+unicode_math[c]+'}')
        else:escaped.append(specials.get(c,c))
    return ''.join(escaped)

def mathtex(m):
    global math_count
    math_count+=1
    val=html.unescape(m.group(1) if m.group(1) is not None else m.group(2))
    val=val.replace(r'\lt ', '<').replace(r'\gt ', '>')
    if m.group(1) is not None:
        return '\n'+r'\atlasdisplay{'+val+'}\n'
    return r'\('+val+r'\)'

def text(s):
    s=re.sub(r'√([A-Za-z0-9])', lambda m: r'\(\sqrt{'+m.group(1)+r'}\)', str(s or ''))
    s=re.sub(r'(?<!\\)\$([^$\n]+)\$',lambda m:r'\('+m.group(1)+r'\)',str(s or ''))
    bits=[];last=0
    for m in MATH.finditer(s):bits.extend([plain(s[last:m.start()]),mathtex(m)]);last=m.end()
    bits.append(plain(s[last:]));return ''.join(bits)

class Node:
    def __init__(self,tag='',attrs=None):self.tag=tag;self.attrs=dict(attrs or []);self.children=[]
class Parser(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.root=Node();self.stack=[self.root]
    def handle_starttag(self,t,a):
        n=Node(t,a);self.stack[-1].children.append(n)
        if t not in ('br','hr','img','meta','link','input'):self.stack.append(n)
    def handle_endtag(self,t):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==t:self.stack=self.stack[:i];break
    def handle_data(self,d):self.stack[-1].children.append(d)

def rawcontent(n):
    return ''.join(c if isinstance(c,str) else rawcontent(c) for c in n.children)

def convert_html(body):
    math_blocks=[]
    def hide(m):math_blocks.append(mathtex(m));return f'ATLASMATHTOKEN{len(math_blocks)-1}ENDTOKEN'
    masked=MATH.sub(hide,body)
    parser=Parser();parser.feed(masked)
    def render(n):
        if isinstance(n,str):return plain(n)
        if n.tag=='pre':
            literal=plain(rawcontent(n)).replace('\n',r'\par '+'\n')
            return '\n'+r'\begin{quote}\small\ttfamily\raggedright '+literal+r'\end{quote}'+'\n'
        children=''.join(render(c) for c in n.children)
        tag=n.tag;classes=n.attrs.get('class','')
        if tag=='p':
            if 'block-label' in classes:return r'\textbf{\sffamily '+children+r'}\par\smallskip'+'\n'
            return r'\color{black} '+children+'\\par\n'
        if tag in ('strong','b'):return r'\textbf{'+children+'}'
        if tag in ('em','i'):return r'\emph{'+children+'}'
        if tag=='code':return r'\texttt{'+children+'}'
        if tag in ('ul','ol'):
            env='itemize' if tag=='ul' else 'enumerate'
            return '\n'+r'\begin{'+env+'}\n'+children+r'\end{'+env+'}\n'
        if tag=='li':return r'\item\leavevmode\color{black} '+children+'\n'
        if tag=='br':return r'\newline '+'\n'
        if tag=='a':
            url=n.attrs.get('href','')
            return children+(' ('+r'\url{'+url+'})' if url else '')
        if tag=='div' and 'math-block' in classes:
            style='boundary' if 'boundary' in classes else 'standard'
            return '\n'+r'\begin{atlasblock}['+style+']\n'+children+r'\end{atlasblock}\color{black}'+'\n'
        if tag=='table':
            rows=[]
            def gather(z):
                if isinstance(z,Node):
                    if z.tag=='tr':rows.append(z)
                    else:
                        for c in z.children:gather(c)
            gather(n)
            count=max(sum(isinstance(c,Node) and c.tag in ('td','th') for c in row.children) for row in rows)
            result=r'\begin{center}\small\begin{tabularx}{\linewidth}{@{}'+(r'>{\raggedright\arraybackslash}X'*count)+r'@{}}\toprule'+'\n'
            for i,row in enumerate(rows):
                cells=[c for c in row.children if isinstance(c,Node) and c.tag in ('td','th')]
                result+=' & '.join((r'\textbf{'+''.join(render(k) for k in c.children)+'}') if c.tag=='th' else ''.join(render(k) for k in c.children) for c in cells)+r' \\'+'\n'
                if i==0 and any(c.tag=='th' for c in cells):result+=r'\midrule'+'\n'
            return result+r'\bottomrule\end{tabularx}\end{center}'+'\n'
        return children
    result=render(parser.root)
    return re.sub(r'ATLASMATHTOKEN(\d+)ENDTOKEN',lambda m:math_blocks[int(m.group(1))],result)

def display_creators(value):
    # BibTeX braces protect corporate names; omit those markers only in creator displays.
    return str(value or '').replace('{', '').replace('}', '')

def urls(r):
    links=[r.get('url'),r.get('open_url')]
    if r.get('doi'):links.append('https://doi.org/'+r['doi'])
    if r.get('arxiv'):links.append('https://arxiv.org/abs/'+r['arxiv'])
    links+=r.get('verification_urls',[])
    return list(dict.fromkeys(u for u in links if isinstance(u,str) and u))

def source_list(cs):
    if not cs:return ''
    out=['\\begin{sources}\n\\textbf{References}\\par\\smallskip\n']
    for c in cs:
        r=byref[c['key']]
        href=r['url'].replace('%',r'\%').replace('#',r'\#')
        out.append(r'\noindent\hyperlink{ref:'+r['id']+'}{'+plain('['+r['id']+']')+'}'+(' / '+text(c['locator']) if c.get('locator') else '')+'. '+text(c.get('note',''))+' '+r'\href{'+href+r'}{'+plain(r.get('url_label','Source'))+r'}.\par'+'\n')
    return ''.join(out)+r'\end{sources}\color{black}'+'\n'

preamble=r'''\documentclass[11pt,a4paper,oneside,openany]{book}
\usepackage[margin=23mm,top=24mm,bottom=25mm,headheight=15pt,headsep=8mm]{geometry}
\usepackage{fontspec}
\setmainfont{Latin Modern Roman}
\setsansfont{Latin Modern Sans}
\setmonofont[Scale=0.83]{DejaVu Sans Mono}
\usepackage{amsmath,amssymb,mathtools}
\usepackage{unicode-math}
\setmathfont{Latin Modern Math}
\usepackage{microtype,xcolor,graphicx,adjustbox,booktabs,tabularx,array,enumitem}
\usepackage[most]{tcolorbox}
\usepackage{titlesec,fancyhdr,needspace,xurl}
\usepackage[unicode,colorlinks=true,linkcolor=atlasgreen,urlcolor=atlasgreen,bookmarksnumbered=true,pdfborder={0 0 0}]{hyperref}
\definecolor{atlasgreen}{HTML}{183F36}
\definecolor{atlaspale}{HTML}{F4F6F1}
\definecolor{atlasgold}{HTML}{946B30}
\definecolor{atlasgray}{HTML}{5A6260}
\hypersetup{pdftitle={Polynomial Arithmetic Atlas: Author's Handbook},pdfauthor={Khai-Hoan Nguyen-Dang},pdfsubject={Irreducibility, Galois groups, methods, examples, and an annotated bibliography},pdfkeywords={polynomials, irreducibility, Galois theory, Newton polygons, research bibliography},pdfinfo={Copyright={© 2026 Khai-Hoan Nguyen-Dang. All rights reserved.}}}
\setlength{\parindent}{0pt}
\setlength{\parskip}{3pt}
\linespread{1.06}
\setcounter{tocdepth}{0}
\setcounter{secnumdepth}{1}
\setlist{topsep=4pt,itemsep=3pt,parsep=1pt,leftmargin=1.6em}
\frenchspacing
\emergencystretch=3em
\widowpenalty=10000\clubpenalty=10000
\newcommand{\atlasdisplay}[1]{\par\begingroup\centering\vspace{3pt}\noindent\adjustbox{max width=\linewidth}{\(\displaystyle #1\)}\par\vspace{5pt}\endgroup}
\providecommand{\lt}{<}\providecommand{\gt}{>}
\newtcolorbox{atlasblock}[1][standard]{enhanced,breakable,colback=atlaspale,colframe=atlasgreen,coltext=black,boxrule=0pt,borderline west={1pt}{0pt}{atlasgreen},arc=0pt,outer arc=0pt,left=9pt,right=9pt,top=8pt,bottom=6pt,before skip=9pt,after skip=9pt,standard/.style={},boundary/.style={colback=atlasgold!6,borderline west={1pt}{0pt}{atlasgold}},#1}
\newenvironment{sources}{\par\smallskip\begingroup\footnotesize\color{atlasgray}\leftskip=10pt\setlength{\parskip}{2pt}}{\par\endgroup\smallskip}
\titleformat{\chapter}[display]{\sffamily\bfseries\raggedright\color{atlasgreen}}{\fontsize{12}{15}\selectfont CHAPTER \thechapter}{8pt}{\fontsize{25}{30}\selectfont}
\titlespacing*{\chapter}{0pt}{-6pt}{20pt}
\titleformat{\section}{\sffamily\large\bfseries\color{atlasgreen}}{\thesection}{0.7em}{}
\titlespacing*{\section}{0pt}{16pt}{7pt}
\titleformat{\subsection}{\sffamily\normalsize\bfseries\color{atlasgreen}}{}{0em}{}
\pagestyle{fancy}\fancyhf{}
\fancyhead[L]{\sffamily\scriptsize\color{atlasgray}\nouppercase{\leftmark}}
\fancyhead[R]{\sffamily\small\thepage}
\fancyfoot[C]{\sffamily\scriptsize\color{atlasgray}© 2026 Khai-Hoan Nguyen-Dang. All rights reserved.}
\renewcommand{\headrulewidth}{0.3pt}
\renewcommand{\chaptermark}[1]{\markboth{#1}{}}
\fancypagestyle{plain}{\fancyhf{}\fancyfoot[C]{\sffamily\scriptsize\color{atlasgray}© 2026 Khai-Hoan Nguyen-Dang. All rights reserved.}\fancyfoot[R]{\sffamily\small\thepage}\renewcommand{\headrulewidth}{0pt}}
\begin{document}
\begin{titlepage}\thispagestyle{empty}
\vspace*{14mm}
{\sffamily\large\color{atlasgold}REFERENCE HANDBOOK\par}
\vspace{14mm}
{\sffamily\bfseries\fontsize{38}{43}\selectfont\color{atlasgreen}Polynomial\\Arithmetic\\Atlas\par}
\vspace{11mm}
{\fontsize{18}{24}\selectfont Polynomial irreducibility\\and Galois groups\par}
\vspace{10mm}\textcolor{atlasgold}{\rule{35mm}{1.2pt}}\par\vspace{8mm}
{\large Results, methods, examples, and references.\par}
\vspace{4mm}
{\large Khai-Hoan Nguyen-Dang\par}
\vfill
{\sffamily\large @@ARTICLE_COUNT@@ articles\quad /\quad @@REFERENCE_COUNT@@ references\par}
\vspace{4mm}
{\color{atlasgray}Author's copy / Literature checked through @@REVIEW_DATE@@\par}
\vspace{7mm}
{\small This edition includes the articles, references, questions, and reading guides from the website. The bibliography is not exhaustive.\par}
\vspace{4mm}
{\small © 2026 Khai-Hoan Nguyen-Dang. All rights reserved.\par}
\end{titlepage}
\frontmatter
\chapter*{Copyright}
© 2026 Khai-Hoan Nguyen-Dang. All rights reserved.

This author-only export contains the atlas's original text, annotations, and organization. Rights in cited works remain with their respective authors or publishers. The copyright notice does not claim ownership of mathematical facts or third-party works. See the repository LICENSE for the terms governing this material.

\tableofcontents
\chapter{Introduction}
This handbook describes methods for proving polynomial irreducibility and determining Galois groups. It covers the rationals, number fields, and finite fields, with related material on specialization, iteration, and absolute irreducibility in several variables.

The edition contains @@ARTICLE_COUNT@@ articles and @@REFERENCE_COUNT@@ annotated references. Each result includes its hypotheses and source. References give theorem or section numbers when these have been checked, together with links and publication details. Central statements were compared with the cited sources, and selected examples were checked by exact computation. Not every cited proof has been checked independently.

\section*{Publication status}
\begin{description}
\item[Classical or published result.] The statement appears in a published work or an established exposition.
\item[Conditional result.] An additional assumption is part of the statement.
\item[Preprint.] The entry reports the cited version. Limits on access and verification are recorded in the reference entry.
\item[Open in a cited source.] The question was open in that source; later work may have resolved it.
\item[Research direction.] A suggested question for further study, not necessarily a new conjecture or an open problem.
\item[Example.] A computation concerns the stated polynomial. A finite sample does not prove a result for an entire family.
\end{description}

\section*{Editions}
The literature review is dated @@REVIEW_DATE@@. The earlier @@ORIGINAL_COUNT@@-source bibliography is a separate fixed edition. The current handbook includes later additions and corrections. Linked books and papers remain with their authors or publishers; this bibliography provides publication details, annotations, and links.

\section*{Using the methods}
\begin{enumerate}
\item State the field, degree, separability, coefficient assumptions, and any factor removed by normalization.
\item Establish irreducibility or list the possible factor degrees.
\item Find elements of the Galois group or a subgroup containing it.
\item Apply group-theoretic criteria or resolvents to determine the group. Check the hypotheses before using the discriminant criterion.
\item Record the computations and theorem references used in the proof.
\end{enumerate}
'''

for token,value in {'@@ARTICLE_COUNT@@':str(len(articles)), '@@REFERENCE_COUNT@@':str(len(refs)), '@@REVIEW_DATE@@':review_date_long, '@@REVIEW_DATE_UPPER@@':review_date_long.upper(), '@@ORIGINAL_COUNT@@':str(catalogue['original_collection_count'])}.items():
    preamble=preamble.replace(token,value)
parts=[preamble]
parts.append(r'\chapter{Reading guide}'+'\n')
for route in navigation['routes']:
    parts.append(r'\section*{'+text(route['title'])+'}\n'+text(route.get('goal',''))+'\\par\n'+(r'\textbf{Background:} '+text(route['audience'])+'\\par\n' if route.get('audience') else '')+r'\begin{enumerate}'+'\n')
    for step in route.get('steps',[]):
        title=step.get('title') or byid.get(step.get('article'),{}).get('title','Read')
        aid=step.get('article')
        link=r'\hyperlink{article:'+aid+'}{'+text(title)+'}' if aid else text(title)
        parts.append(r'\item \textbf{'+link+'}. '+text(step.get('note',''))+'\\par\n')
        if step.get('references'):parts.append(r'{\footnotesize References: '+', '.join(r'\hyperlink{ref:'+k+'}{'+plain(k)+'}' for k in step['references'])+'}\\par\n')
    parts.append(r'\end{enumerate}'+'\n')
parts.append(r'\section*{Books}'+'\n')
for book in navigation['books']:
    r=byref[book['key']]
    parts.append(r'\needspace{5\baselineskip}\textbf{\hyperlink{ref:'+r['id']+'}{'+text(r['title'])+'}} / '+text(display_creators(r.get('authors','')))+'\\par\n'+text(book.get('role',book.get('use','')))+'\\par\n'+r'{\small '+text(book.get('level',''))+'}\\par\\medskip\n')

parts.append(r'\chapter{Methods}'+'\n')
for row in navigation['methods']:
    aid=row['article']
    parts.append(r'\section*{'+text(row.get('question',row['method']))+'}\n')
    parts.append(r'\textbf{Given.} '+text(row.get('input',row.get('signal','')))+'\\par\n')
    parts.append(r'\textbf{Method.} \hyperlink{article:'+aid+'}{'+text(row['method'])+'}.\\par\n')
    parts.append(r'\textbf{Conclusion.} '+text(row['output'])+'\\par\n'+r'\textbf{Limitations.} '+text(row['boundary'])+'\\par\\medskip\n')

parts.append(r'\mainmatter'+'\n')
subject_titles={s['id']:s for s in subjects}
subject_order=['foundations','criteria','galois','families','random','specialization','dynamics','finite-fields','algorithms','multivariate']
subject_order += [sid for sid in subject_titles if sid not in subject_order]
for sid in subject_order:
    group=[a for a in articles if a['subject']==sid]
    if not group:continue
    subject=subject_titles[sid]
    parts.append(r'\part{'+text(subject['title'])+'}\n')
    for a in group:
        parts.append(r'\chapter{'+text(a['title'])+'}\\label{article:'+a['id']+'}'+r'\hypertarget{article:'+a['id']+'}{}\\color{black}\n')
        parts.append(r'{\sffamily\small\color{atlasgold}'+text(' / '.join([a['kind'],a['level'],a['field'],('Preprint' if a['status']=='Preprint boundary' else a['status'])]))+'}\\par\\medskip\n')
        parts.append(text(a['summary'])+'\\par\\medskip\n')
        if a.get('questionsAnswered'):
            parts.append(r'\textbf{Overview}\begin{itemize}'+'\n'+''.join(r'\item '+text(q)+'\n' for q in a['questionsAnswered'])+r'\end{itemize}'+'\n')
        if a.get('prerequisites'):
            parts.append(r'{\small\textbf{Prerequisites:} '+ '; '.join(r'\hyperlink{article:'+k+'}{'+text(byid[k]['title'])+'}' for k in a['prerequisites'])+'}\\par\n')
        for section in a['sections']:
            parts.append(r'\needspace{8\baselineskip}\section{'+text(section['title'])+'}\n'+convert_html(section['body'])+source_list(section.get('citations',[])))
        if a.get('questions'):
            parts.append(r'\needspace{11\baselineskip}\section*{Questions}'+'\n')
            for q in a['questions']:
                parts.append(r'\needspace{7\baselineskip}\subsection*{'+text(q['title'])+'}\n'+r'{\small\sffamily\color{atlasgold}'+text(q['status'])+' / '+text(q['scope'])+'}\\par\\smallskip\n'+convert_html(q['body'])+source_list(q.get('citations',[])))
        if a.get('related'):
            parts.append(r'\needspace{3\baselineskip}\par\medskip\begingroup\footnotesize\setlength{\parskip}{1pt}\textbf{\sffamily\color{atlasgreen}Related topics}\par'+'\n')
            for rel in a['related']:
                parts.append(r'\color{black}\textbf{'+text(rel['relation'])+r'.} \hyperlink{article:'+rel['id']+'}{'+text(byid[rel['id']]['title'])+'}. '+text(rel['why'])+'\\par\n')
            parts.append(r'\endgroup'+'\n')

parts.append(r'\backmatter\setcounter{secnumdepth}{-1}\part{Bibliography}\chapter{'+str(len(refs))+' references}'+'\n')
parts.append('The reference keys are used throughout the handbook. This list includes the original '+str(catalogue['original_collection_count'])+'-source collection and later additions. Publication status is recorded for each entry.\\par\\medskip\n')
for gi in sorted({r.get('group_index') for r in refs}):
    group=[r for r in refs if r.get('group_index')==gi]
    if not group:continue
    parts.append(r'\needspace{12\baselineskip}\section{'+text(group[0]['group'])+'}\n')
    for r in group:
        parts.append(r'\needspace{7\baselineskip}\hypertarget{ref:'+r['id']+'}{}\n'+r'{\sffamily\bfseries\color{atlasgreen}'+plain('['+r['id']+']')+' '+text(r['title'])+'}\\par\n')
        creators=display_creators(r.get('authors') or r.get('editors',''))
        if r.get('author_role')=='editors':creators+=' (editors)'
        details=[creators,str(r['year']) if r.get('year') is not None else 'Undated',r.get('venue','')]
        volume=r.get('volume')
        if volume:details.append(str(volume)+('('+str(r['issue'])+')' if r.get('issue') else ''))
        if r.get('pages'):details.append('pp. '+str(r['pages']).replace('--','-'))
        if r.get('edition'):
            edition=str(r['edition']).strip()
            details.append('Edition '+edition if edition.isdecimal() else edition)
        if r.get('publisher') and r.get('publisher')!=r.get('venue'):details.append(r['publisher'])
        if r.get('series'):details.append(r['series'])
        if r.get('editor'):details.append('Edited by '+display_creators(r['editor']))
        if r.get('report_number'):details.append('Report no. '+str(r['report_number']))
        if r.get('article'):details.append('Article '+str(r['article']))
        parts.append(r'\color{black} '+text('. '.join(str(v).rstrip('. ') for v in details if v))+'.\\par\n')
        parts.append(r'{\small\sffamily\color{atlasgold}'+text(str(r.get('kind',''))+' / '+str(r.get('status','')))+'}\\par\n')
        parts.append(r'\color{black} '+text(r.get('annotation',''))+'\\par\n')
        if r.get('note'):parts.append(r'{\small '+text(r['note'])+'}\\par\n')
        if r.get('metadata_note'):parts.append(r'{\small '+text(r['metadata_note'])+'}\\par\n')
        for url in urls(r):parts.append(r'{\footnotesize\url{'+url+'}}\\par\n')
        parts.append(r'\vspace{9pt}'+'\n')
parts.append(r'\end{document}'+'\n')
tex=''.join(parts)
TEX_OUTPUT.write_text(tex,encoding='utf-8')
manifest={'author':AUTHOR,'copyright':COPYRIGHT,'distribution':'Author-only export','articles':len(articles),'sections':sum(len(a['sections']) for a in articles),'questions':sum(len(a.get('questions',[])) for a in articles),'references':len(refs),'math_expressions':math_count,'checked':review_date.isoformat(),'source_files':{str(f.relative_to(REPO)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((REPO/'content').rglob('*.json'))},'article_ids':[a['id'] for a in articles],'reference_ids':[r['id'] for r in refs]}
MANIFEST_OUTPUT.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:manifest[k] for k in ['articles','sections','questions','references','math_expressions']},indent=2))
print(TEX_OUTPUT)
