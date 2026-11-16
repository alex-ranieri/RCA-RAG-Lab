'use strict';
const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const path=require('node:path');
const elements=new Map();
class Element {
 constructor(tag='div'){this.tagName=tag;this.children=[];this.style={};this.classList={add(){},remove(){}};this.checked=false;this.disabled=false;this.value='';}
 append(...children){this.children.push(...children);}
 replaceChildren(...children){this.children=[...children];}
}
function findBoxes(){const out=[];function walk(n){if(n.type==='checkbox')out.push(n);for(const c of n.children||[])walk(c);}walk(elements.get('docs'));return out;}
const document={
 getElementById(id){if(!elements.has(id))elements.set(id,new Element());return elements.get(id);},
 createElement(tag){return new Element(tag);},
 querySelectorAll(selector){return findBoxes().filter(x=>!selector.endsWith(':checked')||x.checked);}
};
let confirmResult=false,posts=[];
let base={collection:'principal',workspace:'teste',pdfs:[{filename:'um.pdf',size_mb:1},{filename:'dois.pdf',size_mb:2}],indexed:true,stale:false,index_docs:[],chunk_count:2,warnings:[],embedding:null,base_has_data:true};
const context=vm.createContext({document,window:{confirm:()=>confirmResult},console,Date,setInterval:()=>1,clearInterval(){},setTimeout:()=>1,clearTimeout(){},testApi:async(route,options={})=>{
 if(route==='/api/info')return base;
 if(route==='/api/job')return {status:'idle',total:0,done:0};
 if(route==='/api/documents/remove'){
  const body=JSON.parse(options.body);posts.push(body);
  const removed=base.pdfs.filter(x=>body.all||body.filenames.includes(x.filename));
  base={...base,pdfs:base.pdfs.filter(x=>!removed.includes(x))};
  base.base_has_data=base.pdfs.length>0;base.indexed=base.base_has_data;
  return {removed:removed.map(x=>x.filename),remaining:base.pdfs.length,note:'Vetores limpos.',archived_to:'teste/removidos',warning:''};
 }
 throw Error('Rota inesperada: '+route);
}});
let source=fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8');
source=source.slice(0,source.lastIndexOf('(async()=>{try{await refreshInfo();'));
vm.runInContext(source,context);
vm.runInContext('api=testApi;',context);
(async()=>{
 await vm.runInContext('refreshInfo()',context);
 assert.equal(findBoxes().length,2);
 assert.equal(elements.get('removeSelected').disabled,true);
 findBoxes()[0].checked=true;
 vm.runInContext('sync()',context);
 assert.equal(elements.get('removeSelected').disabled,false);
 await vm.runInContext('removeDocuments(false)',context);
 assert.equal(posts.length,0,'Cancelar deve preservar a base');
 confirmResult=true;
 vm.runInContext("turns=[{question:'anterior'}];",context);
 await vm.runInContext('removeDocuments(false)',context);
 assert.deepEqual(posts[0].filenames,['um.pdf']);
 assert.equal(base.pdfs.length,1);
 assert.equal(vm.runInContext('turns.length',context),0,'Limpar histórico antigo');
 assert.equal(findBoxes()[0].value,'dois.pdf');
 vm.runInContext("$('selectAllDocs').onclick()",context);
 assert.equal(findBoxes()[0].checked,true);
 vm.runInContext('embeddingBusy=true;sync()',context);
 assert.equal(elements.get('removeSelected').disabled,true);
 assert.equal(elements.get('clearBase').disabled,true);
 vm.runInContext('embeddingBusy=false;sync()',context);
 await vm.runInContext('removeDocuments(true)',context);
 assert.equal(posts[1].all,true);
 assert.equal(base.pdfs.length,0);
 assert.equal(elements.get('clearBase').disabled,true);
 assert.equal(elements.get('removeSelected').disabled,true);
 console.log('Interface: seleção, cancelamento, remoção parcial/total, histórico e bloqueio durante embeddings OK');
})().catch(e=>{console.error(e);process.exitCode=1;});

