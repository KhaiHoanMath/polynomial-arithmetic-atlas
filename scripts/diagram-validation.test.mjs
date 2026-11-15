// Copyright © 2026 Khai-Hoan Nguyen-Dang. All rights reserved.
import test from 'node:test';
import assert from 'node:assert/strict';
import { validateDiagrams } from './validate-diagrams.mjs';

const articles=[{id:'polynomial',sections:[{id:'theorem'}]}];
const references=[{id:'Source'}];
const fixture=()=>({id:'proof-map',title:'Proof map',summary:'An argument.',scope:'Exact hypotheses.',body:'<p>Full statement.</p>',checked:'2026-11-15',status:'Classical',placements:[{article:'polynomial',afterSection:'theorem'}],nodes:[{id:'A',label:'Hypotheses',kind:'hypothesis',article:'polynomial',section:'theorem'},{id:'B',label:'Criterion',kind:'method'},{id:'C',label:'Conclusion',kind:'result'}],edges:[{from:'A',to:'B',type:'flow',label:'Construct',citations:[],explanation:'Construct the auxiliary object.'},{from:'B',to:'C',type:'equivalence',label:'Theorem 1',citations:['R1'],explanation:'The criterion is necessary and sufficient under the displayed hypotheses.'}],sources:[{id:'R1',key:'Source',locator:'Theorem 1, p. 2',url:'https://example.org/paper.pdf#page=2'}],related:[]});

test('diagram validation accepts sourced arguments and rejects unsupported equivalences',()=>{
 const d=fixture();
 assert.deepEqual(validateDiagrams([d],articles,references),[]);
 d.edges[1].citations=[];
 assert.match(validateDiagrams([d],articles,references).join('\n'),/deduction\/equivalence needs evidence/);
});
test('diagram validation rejects broken internal destinations and graph endpoints',()=>{
 const d=fixture();
 d.nodes[0].section='missing';
 d.edges[1].to='D';
 const errors=validateDiagrams([d],articles,references).join('\n');
 assert.match(errors,/unknown section polynomial#missing/);
 assert.match(errors,/unknown to node D/);
 assert.match(errors,/isolated node C/);
});
test('diagram validation rejects duplicate identifiers and unresolvable evidence',()=>{
 const d=fixture();
 d.sources[0].key='Absent';
 d.edges[1].citations=['R2'];
 const errors=validateDiagrams([d,d],articles,references).join('\n');
 assert.match(errors,/duplicate ID/);
 assert.match(errors,/unknown reference Absent/);
 assert.match(errors,/unknown source R2/);
});
