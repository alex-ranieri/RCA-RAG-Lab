'use strict';
const $=id=>document.getElementById(id);
let busy=false,info=null,catalog=[],turns=[],pendingImages=[],pollTimer=null,waitTimer=null,embeddingBusy=false;
function el(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;}
function selected(){return catalog.find(x=>x.id===$('chatModel').value);}
function message(text,type='muted'){$('message').textContent=text;$('message').className=type;}
async function api(path,options={}){const response=await fetch(path,options);const data=await response.json();if(!response.ok)throw Error(data.error||'Falha no servidor local.');return data;}
const post=(path,data)=>api(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
function sync(){const ready=info?.indexed;for(const id of ['indexBtn','embedBtn','searchBtn','askBtn','compareBtn','refreshModels','applyContext','newChat','exportChat','files','chatModel','mode','clearImages'])$(id).disabled=busy;
 $('indexBtn').disabled=busy||!info?.pdfs.length;$('embedBtn').disabled=busy||!ready||!$('embedModel').value;
 $('searchBtn').disabled=busy||!ready;$('askBtn').disabled=busy||!$('chatModel').value||(!ready&&!$('noRag').checked);$('compareBtn').disabled=busy||!ready||!$('chatModel').value;
 $('applyContext').disabled=busy||!selected()?.native;$('images').disabled=busy||!selected()?.vision;$('reasoning').disabled=busy||!selected()?.reasoning_options.length;
 $('exportChat').disabled=busy||!turns.length;
 const selectedCount=document.querySelectorAll('#docs input[type=checkbox]:checked').length;
 $('removeSelected').disabled=busy||embeddingBusy||!selectedCount;
 $('clearBase').disabled=busy||embeddingBusy||!info?.base_has_data;
 $('selectAllDocs').disabled=busy||embeddingBusy||!info?.pdfs.length;
 for(const checkbox of document.querySelectorAll('#docs input[type=checkbox]'))checkbox.disabled=busy||embeddingBusy;
}
function waiting(text){clearInterval(waitTimer);const start=Date.now();const update=()=>{const s=Math.floor((Date.now()-start)/1000);message(`${text} · ${Math.floor(s/60)} min ${s%60} s decorridos. Modelos locais podem levar vários minutos.`,'busy');};update();waitTimer=setInterval(update,1000);}
function working(flag,text=''){busy=flag;clearInterval(waitTimer);sync();if(flag&&text)waiting(text);else if(text)message(text,'muted');}
function updateBudgetAdvice(){
 const m=selected();const context=Math.min(Number($('contextLength').value)||4096,m?.loaded_context_length||4096,m?.max_context_length||m?.loaded_context_length||4096);
 const chars=Math.max(1000,Math.floor(context*.45*2.5));const k=Math.max(1,Math.min(100,Math.floor(chars/880)));const output=Math.max(32,Math.floor(context*.25));
 const above=Number($('topK').value)>k||Number($('budget').value)>chars||Number($('maxTokens').value)>output;
 $('budgetAdvice').textContent=`Contexto efetivo estimado: ${context.toLocaleString('pt-BR')} tokens. Recomendações: até ${k} trechos, ${chars.toLocaleString('pt-BR')} caracteres de entrada dos PDFs e ${output.toLocaleString('pt-BR')} tokens de saída.`+(above?' Você ultrapassou uma recomendação; pode prosseguir, com maior custo de contexto e tempo.':'')+($('allowContextOverflow').checked?' Extrapolação autorizada: a API poderá recusar um pedido que não caiba no contexto.':'');
 $('budgetAdvice').className=above||$('allowContextOverflow').checked?'notice':'footnote';
}
function applyHelp(){
 const help={
  allowContextOverflow:'Permite tentar enviar mesmo acima do orçamento estimado de contexto. Evita os ajustes automáticos nesse caso; o LM Studio pode recusar ou truncar a solicitação. Não aumenta a capacidade real do modelo.',
  files:'Importa cópias dos seus PDFs para esta coleção. Até 30 MB por arquivo; PDFs escaneados precisam de OCR prévio.',
  selectAllDocs:'Marca todos os PDFs da lista; clique novamente para desmarcar.',removeSelected:'Retira somente os PDFs marcados da busca e arquiva suas cópias em removidos. Pede confirmação.',clearBase:'Retira todos os PDFs desta coleção da busca. Limpa índices e vetores; guarda os PDFs em removidos.',
  indexBtn:'Extrai texto dos PDFs e cria a busca lexical BM25. Use depois de importar novos arquivos.',chunkSize:'Tamanho aproximado de cada trecho, em caracteres. Trechos menores são mais específicos; maiores carregam mais contexto.',overlapWords:'Palavras repetidas entre trechos vizinhos para preservar a continuidade do texto.',
  chatModel:'Modelo local que redige as respostas. Deve ser um modelo de geração, e não de embeddings.',refreshModels:'Consulta a API local para atualizar os modelos e suas capacidades.',
  temperature:'Controla a variação da geração. Valores baixos tendem a produzir respostas mais estáveis; valores altos aumentam a variação.',maxTokens:'Máximo de tokens de saída, de 32 a 131.072. É um teto, não um tamanho obrigatório; tokens não são caracteres. Reasoning pode consumir parte desse limite; aumentá-lo pode alongar o tempo de geração.',
  contextLength:'Tokens disponíveis para instruções, histórico, documentos, imagens e resposta. Contextos maiores consomem mais memória. Clique em Aplicar ao modelo para recarregar com o tamanho escolhido.',applyContext:'Recarrega somente o modelo selecionado com o contexto escolhido. Pode demorar e aumentar o uso de memória. Não altera seus PDFs.',
  responseWait:'Tempo de espera pela resposta do modelo, em minutos. Aumentar esse valor evita timeout em modelos lentos, mas não acelera a inferência.',reasoning:'Controla o esforço de raciocínio quando o modelo/API oferece esse recurso. Mais raciocínio pode exigir mais tempo e tokens.',
  topP:'Amostragem por probabilidade acumulada. Valores menores restringem a variedade de tokens candidatos; 0,95 é um ponto de partida.',seed:'Número usado para tentar reproduzir a geração. Só é enviado quando preenchido; não garante respostas idênticas em todos os modelos.',instructions:'Preferências de formato, nível de detalhe ou público. Não substituem as evidências dos PDFs.',
  mode:'Escolhe como recuperar trechos: palavras (BM25), significado (vetores) ou combinação dos dois (híbrida).',embedModel:'Modelo que transforma textos em vetores para busca por similaridade. Deve ser o mesmo usado ao gerar o índice vetorial.',embedBtn:'Gera os vetores dos trechos da coleção no modelo local. Necessário para busca vetorial e híbrida; pode demorar.',
  topK:'Número máximo de trechos relevantes enviados ao modelo, de 1 a 100. Não obriga a resposta a citar todos. O espaço de evidências é dividido entre os trechos.',budget:'Limite total de caracteres dos PDFs enviados como evidência, de 1.000 a 1.000.000. Não é o tamanho da resposta. Esse espaço é dividido entre os trechos do top-K e pode ser reduzido para caber no contexto real do modelo.',embedProfile:'Prefixo de texto recomendado para a família do modelo de embeddings. Mudar o perfil exige gerar os vetores novamente.',
  question:'Escreva sua pergunta ou uma continuação da conversa. Enter envia; Shift+Enter cria uma nova linha.',images:'Anexa até duas imagens locais de até 1 MB, somente quando o modelo declara suporte visual.',clearImages:'Remove os anexos que ainda não foram enviados.',noRag:'Conversa sem recuperar novos trechos dos PDFs. O histórico existente permanece; use Nova conversa para começar sem conteúdo anterior.',
  askBtn:'Busca evidências, quando RAG está ativo, e envia a pergunta ao modelo local.',searchBtn:'Mostra os trechos recuperados e o top-K aplicado, sem gerar uma resposta no modelo.',compareBtn:'Gera duas respostas à mesma pergunta, sem histórico: uma sem RAG e outra com os trechos dos PDFs.',newChat:'Limpa a conversa desta aba e os anexos pendentes. Preserva os documentos e índices.',exportChat:'Baixa a conversa desta aba em JSON, incluindo fontes e configurações usadas.'
 };
 const descriptions={mode:{bm25:'Busca palavras e termos relacionados, sem usar modelo de embeddings.',vector:'Busca por similaridade de significado. Requer vetores completos e o mesmo modelo de embeddings.',hybrid:'Combina o ranking por palavras com o ranking por vetores. Requer o índice vetorial para usar os dois.'},reasoning:{auto:'Usa o padrão da aplicação; Qwen3 usa raciocínio desligado por padrão.',off:'Desliga o raciocínio explícito quando o modelo oferece esse controle.',on:'Ativa raciocínio explícito; pode demorar mais.',low:'Menor esforço de raciocínio declarado pelo modelo.',medium:'Esforço intermediário de raciocínio.',high:'Maior esforço de raciocínio; pode consumir mais tempo e tokens.'},embedProfile:{auto:'Escolhe o prefixo pela família conhecida do modelo; modelos desconhecidos usam texto sem prefixo.',nomic:'Usa os prefixos search_document e search_query da família Nomic.',embeddinggemma:'Usa os prefixos de documento e consulta da família EmbeddingGemma.',plain:'Envia o texto sem prefixo específico de família.'}};
 for(const [id,text] of Object.entries(help)){
  const node=$(id);if(!node)continue;node.title=text;node.setAttribute('aria-description',text);
  for(const label of node.labels||[])label.title=text;
  for(const option of node.options||[]){
   if(id==='contextLength'){const n=Number(option.value);option.title=`${n.toLocaleString('pt-BR')} tokens para entrada e saída. Contextos maiores exigem mais memória.`+(option.disabled?' Acima do máximo informado pelo modelo.':'');}
   else option.title=descriptions[id]?.[option.value]||text;
  }
 }
}
async function refreshInfo(){info=await api('/api/info');$('collectionName').textContent=info.collection;$('workspacePath').textContent=info.workspace;$('nDocs').textContent=info.pdfs.length;$('nChunks').textContent=info.chunk_count;
 $('docStatus').textContent=info.indexed?'Pronto':info.stale?'Reindexar':info.pdfs.length?'A indexar':'Vazio';$('docStatus').className='chip'+(info.indexed?' ok':'');
 const docs=$('docs');docs.replaceChildren();if(!info.pdfs.length)docs.append(el('p','muted','Nenhum PDF carregado.'));
 for(const file of info.pdfs){const d=info.index_docs.find(x=>x.filename===file.filename);const row=el('div','docitem');const label=el('label','row');const checkbox=el('input');checkbox.type='checkbox';checkbox.value=file.filename;checkbox.onchange=sync;label.append(checkbox,el('span','docname',file.filename));row.append(label,el('div','docmeta',`${file.size_mb} MB`+(d?` · ${d.pages} páginas · ${d.chunks} fragmentos`:'')));docs.append(row);}
 $('indexNote').textContent=info.indexed?`${info.chunk_count} fragmentos prontos.${info.warnings.length?' Alertas: '+info.warnings.join('; '):''}`:'Adicione PDFs e clique em Indexar PDFs.';
 $('vectorInfo').textContent=info.embedding?`${info.embedding.model} · ${info.embedding.done}/${info.embedding.total} vetores · perfil ${info.embedding.profile}`:'Nenhum índice vetorial nesta coleção.';sync();
}
async function refreshModels(){try{const data=await api('/api/models');catalog=data.catalog;for(const [id,type] of [['chatModel','llm'],['embedModel','embedding']]){const old=$(id).value;$(id).replaceChildren();const first=el('option','','Escolha um modelo');first.value='';$(id).append(first);
 for(const model of catalog.filter(x=>x.type===type)){const option=el('option','',model.name);option.value=model.id;$(id).append(option);}$(id).value=old||((id==='embedModel'&&info?.embedding?.model)||'');}
 $('modelStatus').textContent='API local conectada.';updateCapabilities();
 }catch(error){$('modelStatus').textContent=error.message;catalog=[];updateCapabilities();}}
function updateCapabilities(){const m=selected();const old=$('reasoning').value;$('reasoning').replaceChildren();const automatic=el('option','','Padrão da aplicação');automatic.value='auto';$('reasoning').append(automatic);
 for(const value of m?.reasoning_options||[]){const option=el('option','',({off:'Desligado',on:'Ligado',low:'Baixo',medium:'Médio',high:'Alto'})[value]);option.value=value;$('reasoning').append(option);}
 $('reasoning').value=(m?.reasoning_options||[]).includes(old)?old:'auto';
 const maximum=m?.max_context_length;const contextOptions=[...$('contextLength').options];
 for(const option of contextOptions)option.disabled=Boolean(maximum&&Number(option.value)>maximum);
 if(maximum&&Number($('contextLength').value)>maximum){const allowed=contextOptions.filter(x=>!x.disabled);$('contextLength').value=allowed.at(-1)?.value||'4096';}
 $('reasoningNote').textContent=m?.reasoning_control==='qwen3_prompt'?'Qwen3: controle por /think e /no_think no prompt. Padrão da aplicação: desligado.':m?.reasoning_options.length?'Níveis expostos pelo modelo; enviados pela API Responses.':'O servidor não expôs controle de reasoning utilizável para este modelo.';
 $('contextNote').textContent=(m?.loaded_context_length?`Carregado: ${m.loaded_context_length} tokens. `:'Contexto carregado desconhecido; orçamento conservador de até 4096 tokens. ')+(maximum?`Máximo informado: ${maximum} tokens. `:'')+'Aplicar recarrega somente este modelo. Contextos maiores exigem mais memória.';
 $('visionNote').textContent=m?.vision?'PNG, JPEG ou WebP; até 2 imagens de 1 MB. Somente à API local; no máximo as duas imagens mais recentes, conforme o orçamento.':'Anexos desabilitados: nenhum suporte visual confirmado para o modelo selecionado.';
 $('capabilityNote').textContent=m?`Imagens: ${m.vision?'sim':'não confirmadas'} · reasoning: ${m.reasoning_options.length?'disponível':'não exposto'}`:'';applyHelp();updateBudgetAdvice();sync();}
function options(){return {question:$('question').value.trim(),model:$('chatModel').value,temperature:Number($('temperature').value),max_tokens:Number($('maxTokens').value),allow_context_overflow:$('allowContextOverflow').checked,timeout_seconds:Number($('responseWait').value)*60,context_length:Number($('contextLength').value),reasoning:$('reasoning').value,top_p:Number($('topP').value),seed:$('seed').value===''?null:Number($('seed').value),instructions:$('instructions').value,top_k:Number($('topK').value),context_budget:Number($('budget').value),mode:$('mode').value,embedding_model:$('embedModel').value,embedding_profile:$('embedProfile').value,no_rag:$('noRag').checked};}
function history(currentImageCount=0){let left=2-currentImageCount;const recent=turns.slice(-20);const sent=new Map();for(const t of [...recent].reverse()){const images=left>0?t.images.slice(-left).map(x=>x.data):[];left-=images.length;sent.set(t,images);}return recent.flatMap(t=>[{role:'user',content:t.question+(sent.get(t).length<t.images.length?'\n[Imagem antiga omitida do envio por limite de anexos; reanexe se necessário.]':''),images:sent.get(t)},{role:'assistant',content:t.result.answer}]);}
function sources(target,data){target.replaceChildren();if(!data.evidence?.length){target.append(el('p','muted','Nenhum trecho de PDF enviado.'));return;}for(const e of data.evidence){const card=el('div','source');card.append(el('div','file',`[${e.label}] ${e.doc} · p. ${e.page}`),el('div','score',`${e.id} · escore ${e.score}`),el('div','text',e.text));target.append(card);}}
function detail(label){const d=el('details');d.append(el('summary','',label));return d;}
function retrievalSummary(data){
 if(data.engine==='Sem RAG')return 'Sem RAG: nenhum trecho de PDF enviado.';
 const count=data.evidence?.length||0;const requested=data.top_k_requested??data.settings?.top_k??count;
 let text=`Top-K: ${requested} solicitado(s) · ${count} trecho(s) enviado(s)`;
 if(data.citations){const labels=new Set((data.evidence||[]).map(e=>'['+e.label+']'));const cited=new Set((data.citations.citations||[]).filter(x=>labels.has(x)));text+=` · ${cited.size} citado(s)`;}
 if(count<requested)text+=(data.ranked_count!==undefined&&data.ranked_count>=requested?' · Quantidade reduzida pelo orçamento de evidências/contexto.':' · A busca encontrou menos trechos relevantes.');
 if(data.context_limited)text+=' · Textos abreviados para caber no limite de evidências/contexto.';
 return text;
}
function renderTurn(turn){$('chatEmpty')?.remove();const user=el('article','chat-message user-message');user.append(el('strong','speaker','Você'),el('div','result',turn.question));
 for(const image of turn.images){const img=el('img','chat-image');img.src=image.data;img.alt=image.name;user.append(img);}
 const answer=el('article','chat-message assistant-message');const r=turn.result;answer.append(el('strong','speaker',`Assistente · ${turn.settings.model}`),el('div','result',r.answer||'O modelo não retornou texto; confira o limite de saída/reasoning.'));
 answer.append(el('p','footnote',`${r.engine} · ${r.time_seconds||0} s · ${r.context_chars||0} caracteres de evidências · ${r.answer_chars??r.answer?.length??0} caracteres na resposta`));
 answer.append(el('p','footnote',retrievalSummary(r)));
 if(r.warning)answer.append(el('p','notice','Aviso: '+r.warning));
 const evidence=detail(`Fontes deste turno (${r.evidence?.length||0})`);const body=el('div');sources(body,r);evidence.append(body);answer.append(evidence);
 const metrics=detail('Configurações e métricas');metrics.append(el('p','footnote',`Temperatura ${r.settings?.temperature??turn.settings.temperature} · top-p ${turn.settings.top_p} · saída máxima ${r.settings?.max_tokens??turn.settings.max_tokens} tokens (solicitada: ${r.settings?.requested_max_tokens??turn.settings.max_tokens}) · reasoning ${turn.settings.reasoning}`),el('p','footnote',`Contexto efetivo: ${r.effective_context_length||'—'} · entrada estimada: ${r.estimated_input_tokens||'—'} tokens (inclui estimativa de imagens) · histórico enviado: ${r.history_messages_sent||0} mensagens`),el('p','footnote',`Tokens da API: ${r.usage?.prompt_tokens??'—'} entrada / ${r.usage?.completion_tokens??'—'} saída · reasoning ${r.usage?.completion_tokens_details?.reasoning_tokens??'não informado'} tokens · busca ${r.retrieval_seconds||0}s · RAM livre ${r.memory_after?.ram_available_mib??'—'} MiB · término ${r.finish_reason||'—'}`),el('p','footnote','Consulta de recuperação: '+(r.retrieval_query||'Sem recuperação')));answer.append(metrics);
 $('conversation').append(user,answer);answer.scrollIntoView({behavior:'smooth',block:'nearest'});
 $('historyNote').textContent=`${turns.length} turno(s) nesta aba. O envio considera até 20 turnos recentes e é reduzido para caber no contexto. Exporte antes de recarregar.`;
}
async function send(){const opt=options();if(!opt.question){message('Escreva uma mensagem.','error');return;}working(true,'Consultando o modelo local...');try{const images=pendingImages.map(x=>({...x}));const result=await post('/api/ask',{...opt,history:history(images.length),images:images.map(x=>x.data)});const turn={question:opt.question,settings:opt,images,result};turns.push(turn);renderTurn(turn);$('question').value='';clearImages();message(result.warning||'Resposta concluída.',result.warning?'notice':'muted');}catch(error){message(error.message,'error');}finally{working(false);}}
async function search(){const opt=options();if(!opt.question){message('Escreva uma mensagem para buscar.','error');return;}working(true,'Buscando trechos...');try{const data=await post('/api/search',opt);$('searchPanel').classList.remove('hidden');$('searchEngine').textContent=data.engine;sources($('searchSources'),data);$('searchMeta').textContent=`${retrievalSummary(data)} · ${data.context_chars} caracteres · ${data.retrieval_seconds}s. Prévia usa apenas a mensagem digitada; a conversa pode acrescentar perguntas anteriores à busca de continuações.`;message(data.warning||'Busca concluída sem geração.',data.warning?'notice':'muted');}catch(e){message(e.message,'error');}finally{working(false);}}
async function compare(){const opt=options();if(!opt.question){message('Escreva a pergunta para comparar.','error');return;}working(true,'Experimento sem histórico: gerando sem RAG...');$('comparePanel').classList.remove('hidden');$('compareQuestion').textContent=opt.question;$('withoutText').textContent='Aguardando...';$('withText').textContent='Aguardando...';$('compareSources').replaceChildren();try{
 const base={...opt,history:[],images:pendingImages.map(x=>x.data)};const without=await post('/api/ask',{...base,no_rag:true});$('withoutText').textContent=without.answer;waiting('Gerando com RAG...');const withRag=await post('/api/ask',{...base,no_rag:false});$('withText').textContent=withRag.answer;sources($('compareSources'),withRag);message([without.warning,withRag.warning].filter(Boolean).join(' ')||'Comparação concluída; ela não entra no histórico.',withRag.warning||without.warning?'notice':'muted');}catch(e){message(e.message,'error');}finally{working(false);}}
async function upload(){const files=[...$('files').files];working(true,'Importando PDFs...');try{for(const file of files){if(file.size>30*1024**2)throw Error('PDF excede 30 MB.');await api('/api/upload?name='+encodeURIComponent(file.name),{method:'POST',body:await file.arrayBuffer()});}await refreshInfo();message('PDFs importados. Clique em Indexar PDFs.');}catch(e){message(e.message,'error');await refreshInfo();}finally{$('files').value='';working(false);}}
async function index(){working(true,'Extraindo e fragmentando PDFs...');try{const r=await post('/api/index',{chunk_size:Number($('chunkSize').value),overlap_words:Number($('overlapWords').value)});await refreshInfo();message(`Índice pronto: ${r.chunks} fragmentos.`+(r.warnings.length?' '+r.warnings.join('; '):''),r.warnings.length?'notice':'muted');}catch(e){message(e.message,'error');}finally{working(false);}}
async function vectors(){working(true,'Iniciando embeddings locais...');try{await post('/api/embedding/start',{embedding_model:$('embedModel').value,embedding_profile:$('embedProfile').value});message('Geração iniciada. Acompanhe o progresso no painel.');await poll();}catch(e){message(e.message,'error');}finally{working(false);}}
async function poll(){try{const j=await api('/api/job');embeddingBusy=j.status==='running';sync();$('jobBar').style.width=(j.total?Math.round(j.done/j.total*100):0)+'%';$('jobStatus').textContent=j.status==='running'?`${j.done}/${j.total} · ${j.reused||0} reaproveitados · ${j.profile}`:j.status==='done'?`Pronto: ${j.done} vetores; ${j.reused||0} reaproveitados. Perfil: ${j.profile}.`:j.status==='error'?'Falha: '+j.error:'Nenhuma indexação vetorial em andamento.';clearTimeout(pollTimer);if(j.status==='running')pollTimer=setTimeout(poll,1500);if(j.status==='done'||j.status==='error')await refreshInfo();}catch(e){$('jobStatus').textContent=e.message;}}
async function applyContext(){working(true,'Carregando o modelo com o contexto selecionado...');try{const result=await post('/api/model/load',{model:$('chatModel').value,context_length:Number($('contextLength').value)});await refreshModels();message(`Modelo carregado. Contexto: ${result.load_config?.context_length||'consulte o estado atualizado'} tokens.`);}catch(e){message(e.message,'error');await refreshModels();}finally{working(false);}}
function clearImages(){pendingImages=[];$('images').value='';$('imagePreview').replaceChildren();}
$('images').onchange=async()=>{try{const files=[...$('images').files];if(files.length>2)throw Error('Anexe até duas imagens.');const next=[];for(const file of files){if(file.size>1024**2)throw Error(file.name+': limite de 1 MB por imagem.');const data=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=reject;r.readAsDataURL(file);});next.push({name:file.name,data});}pendingImages=next;$('imagePreview').replaceChildren();for(const item of next){const img=el('img','chat-image');img.src=item.data;img.alt=item.name;$('imagePreview').append(img);}}catch(e){clearImages();message(e.message,'error');}};
$('newChat').onclick=()=>{turns=[];clearImages();$('conversation').replaceChildren(el('p','empty muted','Nova conversa. Escreva sua mensagem.'));$('historyNote').textContent='Histórico somente nesta aba. Exporte para guardar.';$('comparePanel').classList.add('hidden');$('searchPanel').classList.add('hidden');$('question').value='';message('Nova conversa iniciada; documentos e índices preservados.');sync();};
$('exportChat').onclick=()=>{const blob=new Blob([JSON.stringify({collection:info.collection,exported_at:new Date().toISOString(),turns},null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=el('a');a.href=url;a.download='conversa-rca-'+Date.now()+'.json';a.click();URL.revokeObjectURL(url);};
$('mode').onchange=()=>{$('methodHelp').textContent=({bm25:'Busca lexical, sem modelo extra.',vector:'Busca por similaridade entre vetores (cosseno).',hybrid:'Combina os rankings BM25 e vetorial por RRF.'})[$('mode').value];};
$('question').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();if(!$('askBtn').disabled)send();}};
$('chatModel').onchange=updateCapabilities;$('noRag').onchange=()=>{sync();if(turns.length)message('O histórico foi mantido e pode conter dados de PDFs. Use Nova conversa ou Comparar para uma condição sem RAG isolada.');};$('embedModel').onchange=sync;$('clearImages').onclick=clearImages;$('files').onchange=upload;$('indexBtn').onclick=index;$('embedBtn').onclick=vectors;$('searchBtn').onclick=search;$('askBtn').onclick=send;$('compareBtn').onclick=compare;$('applyContext').onclick=applyContext;$('refreshModels').onclick=refreshModels;

async function removeDocuments(all=false){
 const filenames=[...document.querySelectorAll('#docs input[type=checkbox]:checked')].map(x=>x.value);
 if(!all&&!filenames.length){message('Selecione os PDFs que deseja remover.','error');return;}
 const target=all?'toda a base desta coleção':filenames.length+' PDF(s) selecionado(s)';
 if(!window.confirm('Remover '+target+'? Os PDFs serão guardados em removidos, fora da busca. Os vetores antigos e a conversa desta aba serão limpos. Exporte a conversa antes, se necessário.'))return;
 working(true,'Removendo documentos da base...');
 try{
  const result=await post('/api/documents/remove',{all,filenames,confirm:true});
  $('newChat').onclick();
  await refreshInfo();await poll();
  message(result.removed.length+' PDF(s) retirado(s); '+result.remaining+' restante(s). '+result.note+(result.archived_to?' PDFs guardados em: '+result.archived_to+'. ':' ')+(result.warning||''),result.warning?'notice':'muted');
 }catch(error){message(error.message,'error');await refreshInfo();}
 finally{working(false);}
}
$('selectAllDocs').onclick=()=>{const boxes=[...document.querySelectorAll('#docs input[type=checkbox]')];const check=boxes.some(x=>!x.checked);for(const box of boxes)box.checked=check;sync();};
$('removeSelected').onclick=()=>removeDocuments(false);
$('clearBase').onclick=()=>removeDocuments(true);

for(const id of ['topK','budget','maxTokens','contextLength','allowContextOverflow'])$(id).oninput=updateBudgetAdvice;
applyHelp();updateBudgetAdvice();
(async()=>{try{await refreshInfo();await refreshModels();await poll();$('mode').onchange();}catch(e){message(e.message,'error');}})();
