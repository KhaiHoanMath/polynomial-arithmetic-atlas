import { readFile, readdir, stat } from 'node:fs/promises';
import { dirname, resolve, sep, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { validateContent } from './validate-content.mjs';
await validateContent(fileURLToPath(new URL('../',import.meta.url)));
const dist=fileURLToPath(new URL('../dist',import.meta.url));
async function walk(dir){const out=[];for(const entry of await readdir(dir,{withFileTypes:true})){const full=resolve(dir,entry.name);if(entry.isDirectory())out.push(...await walk(full));else if(entry.name.endsWith('.html'))out.push(full);}return out;}
const pages=new Map(await Promise.all((await walk(dist)).map(async f=>[f,await readFile(f,'utf8')])));
const ids=new Map([...pages].map(([f,h])=>[f,new Set([...h.matchAll(/\sid="([^"]+)"/g)].map(m=>m[1]))]));
const problems=[];
const decode=s=>s.replaceAll('&amp;','&').replaceAll('&quot;','"').replaceAll('&#39;',"'").replaceAll('&lt;','<').replaceAll('&gt;','>');
let localLinks=0,externalLinks=0;
for(const[file,html]of pages){
 const label=relative(dist,file);
 const declarations=[...html.matchAll(/\sid="([^"]+)"/g)];
 if(declarations.length!==ids.get(file).size)problems.push(`Duplicate IDs: ${label}`);
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
const content=JSON.parse(await readFile(resolve(dist,'downloads/atlas_content.json'),'utf8'));
const refs=JSON.parse(await readFile(resolve(dist,'downloads/atlas_references.json'),'utf8')).references;
const keys=new Set(refs.map(r=>r.id));
for(const e of content.articles){
 if(!e.questionsAnswered?.length)problems.push(`No orientation questions: ${e.id}`);
 if(!e.related?.length)problems.push(`No article connections: ${e.id}`);
 for(const section of e.sections){if(!section.citations?.length&&!/math-block (?:example|proof)/.test(section.body))problems.push(`No source or explicit derivation: ${e.id}/${section.id}`);for(const c of section.citations??[])if(!keys.has(c.key))problems.push(`Unknown citation: ${e.id}/${c.key}`);}
 for(const q of e.questions??[])if(!q.citations?.length)problems.push(`Question without sources: ${q.id}`);
}
if(problems.length){console.error(problems.join('\n'));process.exitCode=1;}else console.log(`Verified ${pages.size} pages, ${localLinks} local links/assets, ${externalLinks} external URL references, all citation keys, and rendered math.`);
