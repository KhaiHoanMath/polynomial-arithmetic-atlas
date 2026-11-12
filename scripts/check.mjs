// Copyright © 2026 Khai-Hoan Nguyen-Dang. All rights reserved.
import { readFile, readdir, stat } from 'node:fs/promises';
import { dirname, resolve, sep, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { validateContent, resolveQuestionAliases } from './validate-content.mjs';
await validateContent(fileURLToPath(new URL('../',import.meta.url)));
const dist=fileURLToPath(new URL('../dist',import.meta.url));
async function walk(dir){const out=[];for(const entry of await readdir(dir,{withFileTypes:true})){const full=resolve(dir,entry.name);if(entry.isDirectory())out.push(...await walk(full));else if(entry.name.endsWith('.html'))out.push(full);}return out;}
const pages=new Map(await Promise.all((await walk(dist)).map(async f=>[f,await readFile(f,'utf8')])));
const ids=new Map([...pages].map(([f,h])=>[f,new Set([...h.matchAll(/\sid="([^"]+)"/g)].map(m=>m[1]))]));
const problems=[];
const publicBase=new URL(process.env.SITE_URL??'https://khaihoanmath.github.io/polynomial-arithmetic-atlas/');
if(!publicBase.pathname.endsWith('/'))publicBase.pathname+='/';
const decode=s=>s.replaceAll('&amp;','&').replaceAll('&quot;','"').replaceAll('&#39;',"'").replaceAll('&lt;','<').replaceAll('&gt;','>');
let localLinks=0,externalLinks=0;
for(const[file,html]of pages){
 const label=relative(dist,file);
 const expectedURL=new URL(label==='index.html'?'./':label,publicBase).href;
 const canonical=html.match(/<link rel="canonical" href="([^"]+)"/);
 if(!canonical||decode(canonical[1])!==expectedURL)problems.push(`Missing or incorrect canonical URL: ${label}`);
 for(const field of ['og:title','og:description','og:url'])if(!html.includes(`property="${field}"`))problems.push(`Missing sharing metadata ${field}: ${label}`);
 if(!html.includes('© 2026 Khai-Hoan Nguyen-Dang. All rights reserved.')||!html.includes('name="author" content="Khai-Hoan Nguyen-Dang"'))problems.push(`Missing copyright/author: ${label}`);
 if(/\bdownload(?:\s|=|>)/.test(html)||/href="[^"#]*(?:downloads\/|handbook\.html)/.test(html))problems.push(`Public download link: ${label}`);
 const declarations=[...html.matchAll(/\sid="([^"]+)"/g)];
 if(declarations.length!==ids.get(file).size)problems.push(`Duplicate IDs: ${label}`);
 let previousHeading=0;
 for(const[,level]of html.matchAll(/<h([1-6])(?:\s|>)/g)){if(Number(level)>previousHeading+1)problems.push(`Skipped heading level h${previousHeading} to h${level}: ${label}`);previousHeading=Number(level);}
 if(html.includes('katex-error'))problems.push(`Math rendering error: ${label}`);
 if((html.match(/<h1(?:\s|>)/g)||[]).length!==1)problems.push(`Expected one h1: ${label}`);
 if(!html.includes('lang="en"')||!html.includes('name="viewport"'))problems.push(`Missing document metadata: ${label}`);
 if(/href="(?:https?:)?\/\/[^"]+"[^>]*>\s*<\/a>/.test(html))problems.push(`Empty external link: ${label}`);
 for(const[,attribute,raw]of html.matchAll(/\s(href|src)="([^"]+)"/g)){
  const value=decode(raw);
  if(/^(?:https?:|mailto:|data:)/.test(value)){externalLinks++;if(value.startsWith('http'))try{new URL(value);}catch{problems.push(`Malformed URL ${value}: ${label}`);}continue;}
  const[destination,fragment]=value.split('#');const target=destination?resolve(dirname(file),decodeURIComponent(destination.split('?')[0])):file;
  localLinks++;
  if(target!==dist&&!target.startsWith(dist+sep))problems.push(`Link leaves site ${value}: ${label}`);
  else if(!await stat(target).then(s=>s.isFile(),()=>false))problems.push(`Missing asset ${value}: ${label}`);
  else if(fragment&&ids.has(target)&&!ids.get(target).has(decodeURIComponent(fragment)))problems.push(`Missing fragment ${value}: ${label}`);
 }
}
const root=fileURLToPath(new URL('../',import.meta.url));
const articleFiles=(await readdir(resolve(root,'content/articles'))).filter(f=>f.endsWith('.json'));
const content={articles:resolveQuestionAliases((await Promise.all(articleFiles.map(f=>readFile(resolve(root,'content/articles',f),'utf8').then(JSON.parse)))).flat())};
const refs=JSON.parse(await readFile(resolve(root,'content/references.json'),'utf8')).references;
const keys=new Set(refs.map(r=>r.id));
for(const e of content.articles){
 if(!e.questionsAnswered?.length)problems.push(`No orientation questions: ${e.id}`);
 if(!e.related?.length)problems.push(`No article connections: ${e.id}`);
 for(const section of e.sections){if(!section.citations?.length&&!/math-block (?:example|proof)/.test(section.body))problems.push(`No source or explicit derivation: ${e.id}/${section.id}`);for(const c of section.citations??[])if(!keys.has(c.key))problems.push(`Unknown citation: ${e.id}/${c.key}`);}
 for(const q of e.questions??[])if(!q.citations?.length)problems.push(`Question without sources: ${q.id}`);
}
const readingHTML=pages.get(resolve(dist,'reading.html'));
const navigation=JSON.parse(await readFile(resolve(root,'content/navigation.json'),'utf8'));
for(const route of navigation.routes){
 const start=readingHTML.indexOf(`id="reading-${route.id}"`),end=readingHTML.indexOf('</section>',start);
 const card=readingHTML.slice(start,end);
 for(const key of new Set([...(route.references??[]),...(route.steps??[]).flatMap(step=>step.references??[])]))
  if(!card.includes(`href="bibliography.html#${key}"`))problems.push(`Omitted reading-route reference: ${route.id}/${key}`);
}
const bibliographyHTML=pages.get(resolve(dist,'bibliography.html'));
for(const key of ['Tsaknias2012','MullenPanario2013','LagariasOdlyzko1977']){
 const source=refs.find(r=>r.id===key),start=bibliographyHTML.indexOf(`id="${key}"`),end=bibliographyHTML.indexOf('</article>',start),card=decode(bibliographyHTML.slice(start,end));
 const citation=card.match(/<p class="citation-text">([^<]*)<\/p>/)?.[1]??'';
 const expected=source.author_role==='editors'?(source.editors??source.editor):source.authors;
 if(!citation.startsWith(expected))problems.push(`Incorrect principal creator: ${key}`);
 if(source.author_role!=='editors'&&(source.editors??source.editor)&&!citation.includes(source.editors??source.editor))problems.push(`Missing chapter editor: ${key}`);
 if(!card.includes(`data-copy="${expected}`))problems.push(`Incorrect copied citation creator: ${key}`);
}
async function checkPublicFiles(dir){for(const entry of await readdir(dir,{withFileTypes:true})){const file=resolve(dir,entry.name);const name=relative(dist,file);if(entry.isDirectory()){if(entry.name==='downloads')problems.push(`Public downloads directory: ${name}`);await checkPublicFiles(file);}else if(/\.(?:pdf|tex|bib|json|csv|zip|py|map)$/i.test(entry.name)||entry.name==='handbook.html')problems.push(`Author file in public build: ${name}`);}}
await checkPublicFiles(dist);
if(problems.length){console.error(problems.join('\n'));process.exitCode=1;}else console.log(`Verified ${pages.size} pages, ${localLinks} local links/assets, ${externalLinks} external URL references, all citation keys, and rendered math.`);
