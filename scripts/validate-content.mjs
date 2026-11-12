// Copyright © 2026 Khai-Hoan Nguyen-Dang. All rights reserved.
import { readFile, readdir } from 'node:fs/promises';
import { resolve } from 'node:path';

export const QUESTION_STATUSES = ['Settled', 'Claimed', 'Open', 'Research direction'];

// Local aliases retain their anchors and comment threads while sharing one statement.
export function resolveQuestionAliases(articles) {
 const byQuestion=new Map(articles.flatMap(a=>(a.questions??[]).map(q=>[q.id,{question:q,article:a.id}])));
 return articles.map(a=>({...a,questions:(a.questions??[]).map(q=>{
  if(!q.aliasOf)return q;
  const target=byQuestion.get(q.aliasOf);
  if(!target||target.question.aliasOf)throw Error(`Invalid canonical question for ${q.id}: ${q.aliasOf}`);
  return {...target.question,...q,canonicalArticle:target.article};
 })}));
}


// Validate the reusable knowledge graph, including IDs which never become HTML links.
export async function validateContent(root) {
 const read = async p => JSON.parse(await readFile(resolve(root,p),'utf8'));
 const [catalogue,subjects,navigation,laboratory,files] = await Promise.all([
  read('content/references.json'),read('content/subjects.json'),read('content/navigation.json'),
  read('content/data/laboratory.json'),readdir(resolve(root,'content/articles'))
 ]);
 const articles=resolveQuestionAliases((await Promise.all(files.filter(f=>f.endsWith('.json')).map(f=>read('content/articles/'+f)))).flat());
 const errors=[];
 const unique=(items,field,label)=>{const seen=new Set();for(const item of items){const id=item[field];if(!id||seen.has(id))errors.push(label+': missing or duplicate '+field+' '+id);seen.add(id);}return seen;};
 const articleIDs=unique(articles,'id','articles'),referenceIDs=unique(catalogue.references,'id','references'),subjectIDs=unique(subjects,'id','subjects');
 unique(navigation.routes,'id','reading routes');unique(laboratory,'id','laboratory examples');
 unique(articles.flatMap(a=>a.questions??[]),'id','questions');
 const requireID=(ids,id,context)=>{if(!ids.has(id))errors.push(context+': unknown ID '+id);};
 const article=(id,context)=>requireID(articleIDs,id,context);
 const reference=(id,context)=>requireID(referenceIDs,id,context);
 for(const a of articles) {
  requireID(subjectIDs,a.subject,a.id+' subject');
  unique(a.sections,'id',a.id+' sections');
  for(const q of a.questions??[])if(!QUESTION_STATUSES.includes(q.status))errors.push(a.id+'/'+q.id+': invalid question status '+q.status);
  for(const id of a.prerequisites??[])article(id,a.id+' prerequisite');
  for(const r of a.related??[])article(r.id,a.id+' connection');
  for(const s of [...a.sections,...(a.questions??[])])
   for(const c of s.citations??[])reference(c.key,a.id+'/'+s.id+' citation');
 }
 for(const r of navigation.routes) {
  for(const id of r.articles??[])article(id,r.id+' route');
  for(const key of r.references??[])reference(key,r.id+' route');
  for(const s of r.steps??[]) {
   if(s.article)article(s.article,r.id+' step');
   for(const key of s.references??[])reference(key,r.id+' step');
  }
 }
 for(const b of navigation.books) {
  reference(b.key,'book shelf');
  for(const id of b.articles??[])article(id,b.key+' book relation');
 }
 for(const m of navigation.methods) {
  article(m.article,'method: '+m.question);
  for(const key of m.references??[])reference(key,'method: '+m.question);
 }
 for(const e of laboratory)article(e.article,e.id+' laboratory relation');
 const sourceIDs={doi:new Map(),arxiv:new Map()};
 for(const r of catalogue.references) {
  for(const field of ['doi','arxiv']) {
   if(!r[field])continue;
   const value=String(r[field]).trim().toLowerCase().replace(/^https?:\/\/(?:dx\.)?doi\.org\//,'').replace(field==='arxiv'?/v\d+$/:/$^/,'');
   const previous=sourceIDs[field].get(value);
   if(previous)errors.push(r.id+': duplicate '+field+' also used by '+previous);
   sourceIDs[field].set(value,r.id);
  }
  if(!Number.isInteger(r.group_index)||r.group_index<0||r.group_index>=subjects.length)errors.push(r.id+': invalid reference group');
  for(const u of [r.url,r.open_url,...(r.verification_urls??[])].filter(Boolean)){
   try {const parsed=new URL(u);if(!['https:','http:'].includes(parsed.protocol))throw Error();}
   catch {errors.push(r.id+': invalid source URL '+u);}
  }
 }
 if(errors.length)throw Error('Content graph validation failed:\n'+errors.join('\n'));
 return {articles:articles.length,references:catalogue.references.length};
}
