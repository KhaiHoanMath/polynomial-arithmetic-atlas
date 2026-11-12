'use strict';
document.documentElement.classList.add('js');
const normalize=text=>String(text??'').toLowerCase().normalize('NFKD').replace(/\p{Diacritic}/gu,'').replace(/[‐‑–—]/g,'-');
const menu=document.querySelector('.nav-toggle');
menu?.addEventListener('click',()=>{const open=menu.getAttribute('aria-expanded')!=='true';menu.setAttribute('aria-expanded',String(open));document.querySelector('#main-nav').classList.toggle('is-open',open);});
for(const button of document.querySelectorAll('[data-print]'))button.addEventListener('click',()=>window.print());
const form=document.querySelector('[data-filter-form]');
if(form){
 const items=[...document.querySelectorAll('[data-filter-item]')].map((node,index)=>({node,index,text:normalize(node.dataset.search),title:normalize(node.dataset.title??node.querySelector('h2,h3')?.textContent??''),year:Number(node.dataset.year??0)}));
 const controls=[...form.querySelectorAll('input[name],select[name]')];
 const query=form.querySelector('[name=q]');
 const count=form.querySelector('[data-filter-count]');
 const empty=document.querySelector('[data-empty]');
 const list=document.querySelector('[data-filter-list]');
 const params=new URLSearchParams(location.search);
 for(const control of controls)if(params.has(control.name)){const value=params.get(control.name);if(control.tagName!=='SELECT'||[...control.options].some(o=>o.value===value))control.value=value;}
 function apply(updateURL=false,preserveHash=false){
  const words=normalize(query.value).trim().split(/\s+/).filter(Boolean);let visible=0;
  for(const item of items){const matches=words.every(w=>item.text.includes(w))&&controls.filter(c=>!['q','sort'].includes(c.name)).every(c=>!c.value||item.node.dataset[c.name]===c.value);item.node.hidden=!matches;if(matches)visible++;}
  const sort=form.querySelector('[name=sort]')?.value;
  if(list){const ordered=[...items].sort(sort==='title'?(a,b)=>a.title.localeCompare(b.title):sort==='newest'?(a,b)=>b.year-a.year||a.index-b.index:(a,b)=>a.index-b.index);for(const item of ordered)list.append(item.node);}
  count.textContent=`${visible} of ${items.length} ${form.dataset.noun??'items'} shown`;empty.hidden=visible!==0;
  if(updateURL&&location.protocol!=='file:'){const url=new URL(location.href);if(!preserveHash)url.hash='';for(const c of controls){if(c.value&&!(c.name==='sort'&&c.value==='default'))url.searchParams.set(c.name,c.value);else url.searchParams.delete(c.name);}history.replaceState(null,'',url.pathname+url.search+url.hash);}
 }
 for(const c of controls)c.addEventListener(c.tagName==='INPUT'?'input':'change',()=>apply(true));
 form.addEventListener('submit',e=>{e.preventDefault();apply(true);});
 form.addEventListener('reset',()=>{requestAnimationFrame(()=>{apply(true);query.focus();});});
 function revealHash(){if(!location.hash)return;let id;try{id=decodeURIComponent(location.hash.slice(1));}catch{return;}const target=document.getElementById(id);if(target?.matches('[data-filter-item]')){for(const c of controls)c.value=c.name==='sort'?'default':'';apply(true,true);requestAnimationFrame(()=>target.scrollIntoView({block:'start'}));}}
 apply();revealHash();window.addEventListener('hashchange',revealHash);
}
for(const button of document.querySelectorAll('[data-copy]'))button.addEventListener('click',async()=>{
 const original='Copy citation';
 try{if(!navigator.clipboard?.writeText)throw Error('clipboard unavailable');await navigator.clipboard.writeText(button.dataset.copy);button.textContent='Copied';setTimeout(()=>button.textContent=original,2000);}
 catch{let box=button.closest('.reference-content').querySelector('.copy-fallback');if(!box){box=document.createElement('textarea');box.className='copy-fallback';box.readOnly=true;box.setAttribute('aria-label','Citation text: select and copy');box.value=button.dataset.copy;button.closest('.reference-content').append(box);}box.focus();box.select();button.textContent='Select and copy below';}
});
const labButtons=[...document.querySelectorAll('[data-lab-select]')];
const labExamples=[...document.querySelectorAll('[data-lab-example]')];
function showExample(id,update=false){if(!labExamples.some(e=>e.dataset.labExample===id))return;for(const e of labExamples)e.hidden=e.dataset.labExample!==id;for(const b of labButtons)b.setAttribute('aria-pressed',String(b.dataset.labSelect===id));if(update&&location.protocol!=='file:')history.replaceState(null,'','#'+id);}
for(const b of labButtons)b.addEventListener('click',()=>showExample(b.dataset.labSelect,true));
for(const example of labExamples){const buttons=[...example.querySelectorAll('[data-prime-select]')];for(const b of buttons)b.addEventListener('click',()=>{for(const other of buttons)other.setAttribute('aria-pressed',String(other===b));for(const panel of example.querySelectorAll('[data-prime-panel]'))panel.hidden=panel.dataset.primePanel!==b.dataset.primeSelect;});}
if(labExamples.length){showExample(location.hash.slice(1));window.addEventListener('hashchange',()=>showExample(location.hash.slice(1)));}
// All content remains available without JavaScript. Make collapsed source details
// available to printed copies, and restore each reader's state afterward.
let printDetails=[];
window.addEventListener('beforeprint',()=>{printDetails=[...document.querySelectorAll('details')].map(d=>[d,d.open]);for(const[d]of printDetails)d.open=true;});
window.addEventListener('afterprint',()=>{for(const[d,open]of printDetails)d.open=open;printDetails=[];});
