"""Build a complete, math-preserving handbook from the site's final JSON.

Write a standalone TeX source and source manifest to the selected output directory.
Compile the generated TeX until cross-references stabilize (normally three XeLaTeX passes on a fresh build).
"""
import json, re, html, hashlib, argparse
from html.parser import HTMLParser
from pathlib import Path
from datetime import date

HERE=Path(__file__).resolve().parent
arguments=argparse.ArgumentParser(description=__doc__)
arguments.add_argument('--site-root',type=Path,default=HERE.parent, help='Repository root; defaults to the parent of the script directory.')
arguments.add_argument('--output-dir',type=Path,default=HERE.parent/'build/handbook', help='Directory for the standalone TeX source and build manifest.')
options=arguments.parse_args()
REPO=options.site_root.resolve()
OUT=options.output_dir.resolve()
OUT.mkdir(parents=True,exist_ok=True)
read=lambda p: json.loads((REPO/p).read_text())
subjects=read('content/subjects.json')
catalogue=read('content/references.json'); refs=catalogue['references']
review_date=date.fromisoformat(catalogue['checked_through'])
review_date_long=f'{review_date.day} {review_date.strftime("%B")} {review_date.year}'
navigation=read('content/navigation.json')
articles=[a for f in sorted((REPO/'content/articles').glob('*.json')) for a in json.loads(f.read_text())]
byid={a['id']:a for a in articles}; byref={r['id']:r for r in refs}
order=['foundations','modular-irreducibility','eisenstein-dumas','newton-polygons','archimedean-criteria','integer-values','sparse-gaps','capelli-composition','frobenius','discriminants','ramification-inertia','permutation-groups','resolvents','reciprocity','trinomials','taylor','laguerre','orthogonal-families','eulerian','bernoulli-euler','fekete','height-counting','random-models','littlewood','factor-reversal','random-matrices','random-reciprocal','twisted-reciprocity','specialization','critical-points-monodromy','inverse-galois','composition-iteration','finite-field-irreducibility','finite-field-constructions','factorization-algorithms','galois-computation','multivariate-irreducibility']
articles.sort(key=lambda a:order.index(a['id']) if a['id'] in order else 999)

MATH=re.compile(r'\\\[([\s\S]*?)\\\]|\\\(([\s\S]*?)\\\)')
math_count=0
unicode_math={'≥':r'\ge','≤':r'\le','−':'-','↦':r'\mapsto','±':r'\pm','μ':r'\mu','∈':r'\in','→':r'\to','∞':r'\infty','α':r'\alpha','δ':r'\delta','ℤ':r'\mathbb Z','ε':r'\varepsilon','√':r'\surd','⋯':r'\cdots','≠':r'\ne','²':'{}^2','⁴':'{}^4','⁶':'{}^6','ⁿ':'{}^n','₂':'{}_2','₃':'{}_3','₄':'{}_4','₅':'{}_5','ₙ':'{}_n'}
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
    out=['\\begin{sources}\n\\textbf{Sources for this section}\\par\\smallskip\n']
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
\hypersetup{pdftitle={Polynomial Arithmetic Atlas: Complete Handbook},pdfauthor={Polynomial Arithmetic Atlas},pdfsubject={Irreducibility, Galois groups, methods, examples, and an annotated bibliography},pdfkeywords={polynomials, irreducibility, Galois theory, Newton polygons, research bibliography}}
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
\fancyfoot[L]{\sffamily\scriptsize\color{atlasgray}POLYNOMIAL ARITHMETIC ATLAS}
\fancyfoot[R]{\sffamily\scriptsize\color{atlasgray}@@REVIEW_DATE_UPPER@@}
\renewcommand{\headrulewidth}{0.3pt}
\renewcommand{\chaptermark}[1]{\markboth{#1}{}}
\fancypagestyle{plain}{\fancyhf{}\fancyfoot[R]{\sffamily\small\thepage}\renewcommand{\headrulewidth}{0pt}}
\begin{document}
\begin{titlepage}\thispagestyle{empty}
\vspace*{14mm}
{\sffamily\large\color{atlasgold}A CONNECTED RESEARCH HANDBOOK\par}
\vspace{14mm}
{\sffamily\bfseries\fontsize{38}{43}\selectfont\color{atlasgreen}Polynomial\\Arithmetic\\Atlas\par}
\vspace{11mm}
{\fontsize{18}{24}\selectfont Irreducibility, Galois groups,\\and the methods between them\par}
\vspace{10mm}\textcolor{atlasgold}{\rule{35mm}{1.2pt}}\par\vspace{8mm}
{\large Precise statements. Proof mechanisms. Exact examples.\\Connected literature, with explicit boundaries.\par}
\vfill
{\sffamily\large @@ARTICLE_COUNT@@ explanatory articles\quad /\quad @@REFERENCE_COUNT@@ annotated sources\par}
\vspace{4mm}
{\color{atlasgray}Complete offline edition / Literature checked through @@REVIEW_DATE@@\par}
\vspace{7mm}
{\small This handbook records the current atlas. It includes the complete article text, section-level citations, research questions, reading routes, and annotated reference catalogue. It is a curated collection, not a claim to contain every publication.\par}
\end{titlepage}
\frontmatter
\tableofcontents
\chapter{How to use this handbook}
The organizing question is not only whether a polynomial is irreducible or which group it has, but \emph{why} a particular method answers that question. Start with the ground field and the exact object, then separate factorization, transitivity, cycle evidence, and identification of the complete group.

This edition contains all @@ARTICLE_COUNT@@ articles and all @@REFERENCE_COUNT@@ annotated reference records in the current website source. Mathematics, qualifications, and source-specific research status have been retained. Section citations carry a stable reference key, precise source location where available, and a clickable source link; the annotated catalogue prints the complete URLs with publication details, DOI links, and verification links. Internal links and the PDF outline support offline navigation.

\section*{Read the status together with the statement}
\begin{description}
\item[Classical or published result.] Read the field, parameter range, exceptional cases, and quantifiers alongside the theorem.
\item[Preprint boundary.] A preprint is labelled as such. An abstract-level verification is not silently presented as a line-by-line proof audit.
\item[Open in a cited source.] This records a question's status in the named source; it is not an unsupported assertion that all subsequent literature has been exhausted.
\item[Research direction.] This is a useful question suggested by the connections, not necessarily a new conjecture or a verified unsolved problem.
\item[Exact example.] A computation supports the specified polynomial. A finite sample cannot establish a uniform theorem or an asymptotic statement.
\end{description}

\section*{Scope and editions}
The literature-review date is @@REVIEW_DATE@@. This handbook is a new, complete snapshot of the expanded atlas. The earlier @@ORIGINAL_COUNT@@-source, 37-page bibliography remains a separate fixed edition; it does not contain the full current explanations or all subsequent reference additions. Linked papers and books remain with their authors and publishers. The catalogue stores metadata, annotations, and links rather than reproducing their full text.

\section*{A reliable order of work}
\begin{enumerate}
\item Specify the field, degree, separability, coefficient assumptions, and any factor removed by normalization.
\item Establish irreducibility or list the possible factor degrees.
\item Obtain permutations or structural upper bounds without confusing local evidence with a complete group determination.
\item Use a stated group theorem, resolvent, or certificate to finish; use the discriminant for parity only within its proper scope.
\item Save the precise theorem, source location, prime, identity, or polygon that makes the conclusion reproducible.
\end{enumerate}
'''

for token,value in {'@@ARTICLE_COUNT@@':str(len(articles)), '@@REFERENCE_COUNT@@':str(len(refs)), '@@REVIEW_DATE@@':review_date_long, '@@REVIEW_DATE_UPPER@@':review_date_long.upper(), '@@ORIGINAL_COUNT@@':str(catalogue['original_collection_count'])}.items():
    preamble=preamble.replace(token,value)
parts=[preamble]
parts.append(r'\chapter{Reading routes and reference books}'+'\n')
for route in navigation['routes']:
    parts.append(r'\section*{'+text(route['title'])+'}\n'+text(route.get('goal',''))+'\\par\n'+(r'\textbf{Background:} '+text(route['audience'])+'\\par\n' if route.get('audience') else '')+r'\begin{enumerate}'+'\n')
    for step in route.get('steps',[]):
        title=step.get('title') or byid.get(step.get('article'),{}).get('title','Read')
        aid=step.get('article')
        link=r'\hyperlink{article:'+aid+'}{'+text(title)+'}' if aid else text(title)
        parts.append(r'\item \textbf{'+link+'}. '+text(step.get('note',''))+'\\par\n')
        if step.get('references'):parts.append(r'{\footnotesize References: '+', '.join(r'\hyperlink{ref:'+k+'}{'+plain(k)+'}' for k in step['references'])+'}\\par\n')
    parts.append(r'\end{enumerate}'+'\n')
parts.append(r'\section*{The book shelf}'+'\n')
for book in navigation['books']:
    r=byref[book['key']]
    parts.append(r'\needspace{5\baselineskip}\textbf{\hyperlink{ref:'+r['id']+'}{'+text(r['title'])+'}} / '+text(display_creators(r.get('authors','')))+'\\par\n'+text(book.get('role',book.get('use','')))+'\\par\n'+r'{\small '+text(book.get('level',''))+'}\\par\\medskip\n')

parts.append(r'\chapter{Choose a method}'+'\n')
for row in navigation['methods']:
    aid=row['article']
    parts.append(r'\section*{'+text(row.get('question',row['method']))+'}\n')
    parts.append(r'\textbf{Available information.} '+text(row.get('input',row.get('signal','')))+'\\par\n')
    parts.append(r'\textbf{Method.} \hyperlink{article:'+aid+'}{'+text(row['method'])+'}.\\par\n')
    parts.append(r'\textbf{Conclusion.} '+text(row['output'])+'\\par\n'+r'\textbf{Boundary.} '+text(row['boundary'])+'\\par\\medskip\n')

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
        parts.append(r'{\sffamily\small\color{atlasgold}'+text(' / '.join([a['kind'],a['level'],a['field'],a['status']]))+'}\\par\\medskip\n')
        parts.append(text(a['summary'])+'\\par\\medskip\n')
        if a.get('questionsAnswered'):
            parts.append(r'\textbf{Questions answered}\begin{itemize}'+'\n'+''.join(r'\item '+text(q)+'\n' for q in a['questionsAnswered'])+r'\end{itemize}'+'\n')
        if a.get('prerequisites'):
            parts.append(r'{\small\textbf{Prerequisites:} '+ '; '.join(r'\hyperlink{article:'+k+'}{'+text(byid[k]['title'])+'}' for k in a['prerequisites'])+'}\\par\n')
        for section in a['sections']:
            parts.append(r'\needspace{8\baselineskip}\section{'+text(section['title'])+'}\n'+convert_html(section['body'])+source_list(section.get('citations',[])))
        if a.get('questions'):
            parts.append(r'\needspace{11\baselineskip}\section*{Questions and research boundaries}'+'\n')
            for q in a['questions']:
                parts.append(r'\needspace{7\baselineskip}\subsection*{'+text(q['title'])+'}\n'+r'{\small\sffamily\color{atlasgold}'+text(q['status'])+' / '+text(q['scope'])+'}\\par\\smallskip\n'+convert_html(q['body'])+source_list(q.get('citations',[])))
        if a.get('related'):
            parts.append(r'\needspace{6\baselineskip}\par\medskip\begingroup\footnotesize\setlength{\parskip}{1pt}\textbf{\sffamily\color{atlasgreen}Connections}\par'+'\n')
            for rel in a['related']:
                parts.append(r'\color{black}\textbf{'+text(rel['relation'])+r'.} \hyperlink{article:'+rel['id']+'}{'+text(byid[rel['id']]['title'])+'}. '+text(rel['why'])+'\\par\n')
            parts.append(r'\endgroup'+'\n')

parts.append(r'\backmatter\setcounter{secnumdepth}{-1}\part{Annotated reference catalogue}\chapter{'+str(len(refs))+' sources, with links and annotations}'+'\n')
parts.append('The stable keys below are used in the section citations throughout the handbook. The reference list combines the original '+str(catalogue['original_collection_count'])+'-source collection with subsequent verified additions. Publication and preprint status are preserved record by record.\\par\\medskip\n')
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
(OUT/'polynomial_arithmetic_atlas_handbook.tex').write_text(tex)
manifest={'articles':len(articles),'sections':sum(len(a['sections']) for a in articles),'questions':sum(len(a.get('questions',[])) for a in articles),'references':len(refs),'math_expressions':math_count,'checked':review_date.isoformat(),'source_files':{str(f.relative_to(REPO)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((REPO/'content').rglob('*.json'))},'article_ids':[a['id'] for a in articles],'reference_ids':[r['id'] for r in refs]}
(OUT/'handbook-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({k:manifest[k] for k in ['articles','sections','questions','references','math_expressions']},indent=2))
print(OUT/'polynomial_arithmetic_atlas_handbook.tex')
