// Copyright © 2026 Khai-Hoan Nguyen-Dang. All rights reserved.
import test from 'node:test';
import assert from 'node:assert/strict';
import { cp, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { validateContent } from './validate-content.mjs';

test('content validation rejects accidental TeX control characters before rendering', async () => {
 const root=await mkdtemp(join(tmpdir(),'atlas-content-validation-'));
 try {
  await cp(fileURLToPath(new URL('../content',import.meta.url)),join(root,'content'),{recursive:true});
  await validateContent(root);
  const file=join(root,'content/articles/random.json');
  const original=await readFile(file,'utf8');
  for(const control of ['\t','\b','\f','\r','\n','\u0000']) {
   const articles=JSON.parse(original);
   const section=articles.find(a=>a.id==='random-matrices').sections.find(s=>s.id==='other-ensembles');
   section.body=`<p>\\(H${control}o\\infty\\)</p>`;
   await writeFile(file,JSON.stringify(articles));
   await assert.rejects(validateContent(root),/random\.json.*unexpected (?:control character|newline in mathematics)/);
  }
  await writeFile(file,original);
  const bibliography=join(root,'content/references.json');
  const catalogue=JSON.parse(await readFile(bibliography,'utf8'));
  catalogue.references[0].annotation='\\(x\t y\\)';
  await writeFile(bibliography,JSON.stringify(catalogue));
  await assert.rejects(validateContent(root),/references\.json.*unexpected control character/);
  catalogue.references[0].annotation='A valid paragraph.\nA second paragraph.';
  catalogue.references[0].title_tex='A title with $x\nu$';
  await writeFile(bibliography,JSON.stringify(catalogue));
  await assert.rejects(validateContent(root),/references\.json.*unexpected newline in mathematics/);
 } finally {
  await rm(root,{recursive:true,force:true});
 }
});
