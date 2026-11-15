// Copyright © 2026 Khai-Hoan Nguyen-Dang. All rights reserved.
import { readFile, readdir } from 'node:fs/promises';
import { resolve } from 'node:path';

export async function loadDiagrams(root) {
 const dir=resolve(root,'content/diagrams');
 const files=(await readdir(dir).catch(e=>{if(e.code==='ENOENT')return [];throw e;})).filter(f=>f.endsWith('.json')).sort();
 return (await Promise.all(files.map(async file=>{
  const data=JSON.parse(await readFile(resolve(dir,file),'utf8'));
  if(!Array.isArray(data))throw Error(`content/diagrams/${file}: expected an array`);
  return data;
 }))).flat();
}

// A diagram is an argument with references, not merely a collection of boxes.
export function validateDiagrams(diagrams,articles,references) {
 const errors=[];
 const byArticle=new Map(articles.map(a=>[a.id,a]));
 const refs=new Set(references.map(r=>r.id));
 const ids=new Set();
 const fail=(d,message)=>errors.push(`diagram ${d.id??'(missing ID)'}: ${message}`);
 const internal=(d,link,context,sectionKey='section')=>{
  if(!link.article){if(link[sectionKey])fail(d,`${context}: section without article`);return;}
  const article=byArticle.get(link.article);
  if(!article)fail(d,`${context}: unknown article ${link.article}`);
  else if(link[sectionKey]&&!article.sections.some(s=>s.id===link[sectionKey]))fail(d,`${context}: unknown section ${link.article}#${link[sectionKey]}`);
 };
 for(const d of diagrams){
  if(!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(d.id??'')||ids.has(d.id))fail(d,'missing, invalid or duplicate ID');
  ids.add(d.id);
  for(const field of ['title','summary','scope','body','checked'])if(typeof d[field]!=='string'||!d[field].trim())fail(d,`missing ${field}`);
  if(!/^\d{4}-\d{2}-\d{2}$/.test(d.checked??''))fail(d,'invalid checked date');
  if(!['Classical','Published','Claimed','Conditional'].includes(d.status))fail(d,`invalid status ${d.status}`);
  if(!d.placements?.length)fail(d,'missing canonical placement');
  const placements=new Set();
  for(const p of d.placements??[]){
   internal(d,p,'placement','afterSection');
   if(!p.article||!p.afterSection)fail(d,'placement must identify an article and section');
   if(placements.has(p.article))fail(d,`duplicate placement in ${p.article}`);
   placements.add(p.article);
  }
  if(!Array.isArray(d.nodes)||d.nodes.length<3||d.nodes.length>14)fail(d,'expected 3–14 nodes');
  const nodes=new Map();
  for(const n of d.nodes??[]){
   if(!/^[a-zA-Z][a-zA-Z0-9_-]*$/.test(n.id??'')||nodes.has(n.id))fail(d,`invalid or duplicate node ${n.id}`);
   nodes.set(n.id,n);
   if(!n.label||/\\[([]/.test(n.label))fail(d,`node ${n.id}: label must be plain text`);
   if(!['object','method','result','gate','hypothesis'].includes(n.kind))fail(d,`node ${n.id}: invalid kind`);
   if(n.kind==='gate'&&!['AND','OR'].includes(n.label))fail(d,`node ${n.id}: gate must say AND or OR`);
   internal(d,n,`node ${n.id}`);
  }
  const sources=new Map();
  for(const s of d.sources??[]){
   if(!s.id||sources.has(s.id))fail(d,`duplicate or missing source ID ${s.id}`);
   sources.set(s.id,s);
   if(!refs.has(s.key))fail(d,`unknown reference ${s.key}`);
   if(!s.locator?.trim())fail(d,`source ${s.id}: missing exact locator`);
   if(s.url)try{if(new URL(s.url).protocol!=='https:')throw Error();}catch{fail(d,`source ${s.id}: invalid HTTPS URL`);}
  }
  const connected=new Set(),usedSources=new Set();
  for(const [i,e] of (d.edges??[]).entries()){
   for(const key of ['from','to']){if(!nodes.has(e[key]))fail(d,`edge ${i+1}: unknown ${key} node ${e[key]}`);connected.add(e[key]);}
   if(e.from===e.to)fail(d,`edge ${i+1}: self-loop`);
   if(!['deduction','equivalence','flow'].includes(e.type))fail(d,`edge ${i+1}: invalid arrow type`);
   if(!e.explanation?.trim())fail(d,`edge ${i+1}: missing explanation`);
   if(!Array.isArray(e.citations))fail(d,`edge ${i+1}: citations must be an array`);
   else {
    if(e.type!=='flow'&&!e.citations.length)fail(d,`edge ${i+1}: deduction/equivalence needs evidence`);
    for(const id of e.citations){if(!sources.has(id))fail(d,`edge ${i+1}: unknown source ${id}`);usedSources.add(id);}
   }
   if(e.preprint!==undefined&&typeof e.preprint!=='boolean')fail(d,`edge ${i+1}: invalid preprint flag`);
  }
  for(const id of nodes.keys())if(!connected.has(id))fail(d,`isolated node ${id}`);
  for(const id of sources.keys())if(!usedSources.has(id))fail(d,`source ${id} is not attached to an arrow`);
  for(const r of d.related??[])internal(d,r,'related link');
 }
 return errors;
}
