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
 remove(){}
 scrollIntoView(){}
 setAttribute(key,value){this[key]=value;}
 get options(){return this.tagName==='select'?this.children:[];}
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
 context.testTurn={question:'Pergunta',images:[],settings:{model:'teste'},result:{
  answer:'Resposta sem marcador.',engine:'BM25',warning:'Resposta sem marcadores de fonte; confira os trechos antes de usar.',
  top_k_requested:5,top_k_sent:5,context_limited:true,citations:{citations:[]},
  evidence:Array.from({length:5},(_,i)=>({label:'F'+(i+1),doc:'teste.pdf',page:1,text:'Texto',id:String(i),score:1}))}};
 vm.runInContext('renderTurn(testTurn)',context);
 const answer=elements.get('conversation').children.at(-1);
 assert(answer.children.some(x=>x.className==='notice'&&x.textContent.startsWith('Aviso:')));
 assert(!answer.children.some(x=>x.className==='error'));
 const summary=vm.runInContext('retrievalSummary(testTurn.result)',context);
 assert(summary.includes('5 solicitado(s) · 5 trecho(s) enviado(s) · 0 citado(s)'));
 assert(summary.includes('abreviados'));
 vm.runInContext("$('topK').value='4'",context);
 assert.equal(vm.runInContext('options().top_k',context),4);
 vm.runInContext("message('Falha real','error')",context);
 assert.equal(elements.get('message').className,'error');
 elements.get('contextLength').tagName='select';
 for(const size of [1024,2048,4096,8192,16384,32768,65536,131072]){const option=new Element('option');option.value=String(size);elements.get('contextLength').append(option);}
 elements.get('contextLength').value='131072';
 elements.get('chatModel').value='teste';
 vm.runInContext("catalog=[{id:'teste',max_context_length:32768,loaded_context_length:8192,reasoning_options:[],native:true}];updateCapabilities()",context);
 assert.equal(elements.get('contextLength').value,'32768');
 assert(elements.get('contextLength').options.find(x=>x.value==='65536').disabled);
 assert(!elements.get('contextLength').options.find(x=>x.value==='16384').disabled);
 assert(elements.get('topK').title.includes('Não obriga'));
 assert(elements.get('contextLength').title.includes('memória'));
 assert(elements.get('contextLength').options.at(-1).title.includes('Acima do máximo'));
 assert(elements.get('askBtn')['aria-description']);
 elements.get('topK').value='50';elements.get('maxTokens').value='8192';elements.get('budget').value='50000';
 vm.runInContext('updateBudgetAdvice()',context);
 assert.equal(elements.get('budgetAdvice').className,'notice');
 assert.equal(vm.runInContext('options().top_k',context),50);
 elements.get('allowContextOverflow').checked=true;
 assert.equal(vm.runInContext('options().allow_context_overflow',context),true);
 const fourCited={...context.testTurn.result,citations:{citations:['[F1]','[F2]','[F3]','[F4]']}};
 context.fourCited=fourCited;
 assert(vm.runInContext('retrievalSummary(fourCited)',context).includes('5 trecho(s) enviado(s) · 4 citado(s)'));
 console.log('Interface: remoção, top-K, métricas, avisos e falhas reais OK');
})().catch(e=>{console.error(e);process.exitCode=1;});

