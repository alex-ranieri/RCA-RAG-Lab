#!/usr/bin/env python3
"""RCA-RAG Lab: servidor web local para ensinar RAG com artigos científicos.

Python >=3.10, pypdf. Interface em http://127.0.0.1:8765
NÃO expõe dados na rede, não utiliza API em nuvem.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import logging
import re
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit
from rag_core import (BM25, build_index, check_citations, combine_scores, cosine,
                      doc_signature, pick_context, prompt_for, pdf_files)
from lmstudio_api import LMStudioError, chat, embed, list_models, validate_base_url, model_catalog, apply_context
from recursos import memory_snapshot
from conversation import number, clean_content, history_pairs, fit_messages, profile_for, embedding_input

ROOT=Path(__file__).resolve().parent
DOCS=ROOT/'documentos'
DATA=ROOT/'dados'
INDEX_FILE=DATA/'index.json'
VECTOR_FILE=DATA/'vetores.json'
WEB=ROOT/'web'/'index.html'
MAX_PDF_SIZE=30*1024*1024
def configure_workspace(folder):
    """Seleciona uma coleção isolada, sem copiar documentos nem índices históricos."""
    global DOCS, DATA, INDEX_FILE, VECTOR_FILE
    folder=Path(folder).resolve()
    DOCS=folder/'documentos'
    DATA=folder/'dados'
    INDEX_FILE=DATA/'index.json'
    VECTOR_FILE=DATA/'vetores.json'

def atomic_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    temp.replace(path)

def load_json(path):
    try:return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else None
    except (ValueError,OSError):return None

class State:
    def __init__(self, base_url):
        DOCS.mkdir(parents=True,exist_ok=True)
        DATA.mkdir(parents=True,exist_ok=True)
        self.collection_revision=0
        self.auto_backend=(base_url=='auto')
        self.base_url='http://127.0.0.1:1234/v1' if self.auto_backend else validate_base_url(base_url)
        self.lock=threading.RLock()
        self.inference_lock=threading.Lock()
        self.index=load_json(INDEX_FILE)
        self.bm25=BM25(self.index['chunks']) if self.index and self.index.get('chunks') else None
        self.vectors=load_json(VECTOR_FILE)
        self.job={'status':'idle','done':0,'total':0,'error':'','model':''}

    def catalog(self):
        self.connected_models()
        return model_catalog(self.base_url)

    def model_detail(self,model):
        detail=next((x for x in self.catalog() if x['id']==model),None)
        if not detail:raise ValueError('Modelo não listado pela API local. Clique em Atualizar.')
        return detail

    def load_model(self,request):
        model=str(request.get('model',''))
        length=number(request.get('context_length',4096),1024,131072,'Contexto',True)
        with self.inference_lock:
            detail=self.model_detail(model)
            if detail['type']!='llm' or not detail['native']:
                raise ValueError('A configuração de carga exige a API nativa do LM Studio e um LLM.')
            if detail.get('max_context_length') and length>detail['max_context_length']:
                raise ValueError('Contexto acima do máximo informado pelo modelo.')
            event={'at':time.time(),'model':model,'requested_context':length,'previous':detail['loaded_instances']}
            try:
                result=apply_context(self.base_url,model,length,detail['loaded_instances'])
                event['result']=result
            except Exception as exc:
                event['error']=str(exc)
                raise
            finally:
                with (DATA/'configuracoes_modelo.jsonl').open('a',encoding='utf-8') as log:
                    log.write(json.dumps(event,ensure_ascii=False)+'\n')
        return result

    def connected_models(self):
        if not self.auto_backend:
            return list_models(self.base_url)
        candidates=[self.base_url,'http://127.0.0.1:1234/v1','http://127.0.0.1:1235/v1']
        seen=set();first_reachable=None; errors=[]
        for url in candidates:
            if url in seen:continue
            seen.add(url)
            try:
                models=list_models(url)
                if models:
                    self.base_url=url
                    return models
                if first_reachable is None:first_reachable=url
            except LMStudioError as exc:errors.append(str(exc))
        if first_reachable is not None:
            self.base_url=first_reachable
            return []
        raise LMStudioError('Nenhuma API local respondeu em 1234 ou 1235. No Bionic, ative Settings → Local Models → Local Model API; ou inicie o servidor no LM Studio clássico. '+(errors[0] if errors else ''))

    def is_ready(self):
        return bool(self.index and self.bm25 and self.index.get('source_signature')==doc_signature(DOCS))

    def info(self):
        pdfs=[]
        for f in pdf_files(DOCS):
            pdfs.append({'filename':f.name,'size_mb':round(f.stat().st_size/1024**2,2)})
        with self.lock:
            valid=self.is_ready()
            return {'pdfs':pdfs,'indexed':valid,'stale':bool(self.index and not valid),
                    'collection':DOCS.parent.name,'workspace':str(DOCS.parent),
                    'chunk_count':len(self.index['chunks']) if valid else 0,
                    'index_docs':self.index['docs'] if valid else [],
                    'warnings':self.index.get('warnings',[]) if valid else [],
                    'embedding':({'model':self.vectors.get('model'),
                        'profile':self.vectors.get('profile','legado; gere novamente'),
                        'done':len(self.vectors.get('vectors',{})),
                        'total':len(self.index['chunks']),
                        'complete':self.vectors.get('complete',False)}
                        if valid and self.vectors and self.vectors.get('fingerprint')==self.index['fingerprint'] else None),
                    'base_has_data':bool(pdfs or any((DATA/name).exists() for name in ('index.json','vetores.json','embedding_cache.json'))),
                    'base_url':self.base_url}

    def rebuild(self,max_chars=880,overlap_words=24):
        with self.lock:
            if self.job['status']=='running':
                raise ValueError('Indexação de embeddings em andamento. Aguarde o término.')
            max_chars=number(max_chars,400,1600,'Tamanho do fragmento',True)
            overlap_words=number(overlap_words,0,60,'Sobreposição',True)
            index=build_index(DOCS,max_chars,overlap_words)
            atomic_json(INDEX_FILE,index)
            self.index=index
            self.bm25=BM25(index['chunks'])
            # Preserva vetores anteriores; fingerprint impede uso com índice diferente.
            # Uma reconstrução BM25 não deve apagar dados vetoriais existentes.
            return {'documents':len(index['docs']),'pages':sum(d['pages'] for d in index['docs']),
                    'chunks':len(index['chunks']),'warnings':index['warnings']}


    def remove_documents(self, request):
        """Retira PDFs da coleção e arquiva as cópias locais fora da busca."""
        if request.get('confirm') is not True:
            raise ValueError('Confirme a remoção dos documentos da base.')
        all_documents=request.get('all',False)
        if not isinstance(all_documents,bool):
            raise ValueError('Opção de limpeza inválida.')
        with self.lock:
            if self.job['status']=='running':
                raise ValueError('Aguarde a indexação de embeddings terminar antes de remover documentos.')
            if not self.inference_lock.acquire(blocking=False):
                raise ValueError('Aguarde a resposta do modelo terminar antes de remover documentos.')
            try:
                available={p.name:p for p in pdf_files(DOCS)}
                names=list(available) if all_documents else request.get('filenames')
                if not isinstance(names,list) or (not names and not all_documents):
                    raise ValueError('Selecione ao menos um PDF.')
                for name in names:
                    if (not isinstance(name,str) or not name or '/' in name or chr(92) in name
                            or ':' in name or name not in available):
                        raise ValueError('Seleção inválida; atualize a lista de PDFs.')
                    source=available[name]
                    if source.is_symlink() or source.resolve().parent!=DOCS.resolve():
                        raise ValueError('Não é permitido remover arquivos externos à coleção.')
                names=list(dict.fromkeys(names))
                parameters=(self.index or {}).get('parameters',{})
                archive=None
                moved=[]
                try:
                    if names:
                        archive=DOCS.parent/'removidos'/str(time.time_ns())
                        if not archive.resolve().is_relative_to(DOCS.parent.resolve()):
                            raise ValueError('Pasta de removidos fora da coleção.')
                        archive.mkdir(parents=True)
                        for name in names:
                            target=archive/name
                            available[name].rename(target)
                            moved.append((available[name],target))
                except Exception:
                    for source,target in reversed(moved):
                        target.rename(source)
                    raise
                # Nenhuma busca pode reaproveitar trechos/vetores da base anterior.
                self.index=None
                self.bm25=None
                self.vectors=None
                self.collection_revision+=1
                self.job={'status':'idle','done':0,'total':0,'error':'','model':''}
                generated=[DATA/'index.json',DATA/'vetores.json',DATA/'embedding_cache.json']
                generated+=list(DATA.glob('vetores_legado_*.json'))
                for file in generated:
                    file.unlink(missing_ok=True)
                    file.with_suffix(file.suffix+'.tmp').unlink(missing_ok=True)
                remaining=pdf_files(DOCS)
                warning=''
                if remaining:
                    try:
                        self.rebuild(parameters.get('max_chars',880),parameters.get('overlap_words',24))
                    except ValueError as exc:
                        warning='Os PDFs restantes estão sem índice utilizável. '+str(exc)
                return {'removed':names,'remaining':len(remaining),'indexed':self.is_ready(),
                        'archived_to':str(archive) if archive else None,'warning':warning,
                        'note':'Vetores e cache anteriores foram limpos. Gere os embeddings novamente se usar busca vetorial.'}
            finally:
                self.inference_lock.release()

    def retrieve(self, question, top_k=3, max_chars=2500, mode='bm25', embedding_model='',embedding_profile='auto'):
        started=time.perf_counter()
        if mode not in ('bm25','vector','hybrid'):raise ValueError('Método de recuperação inválido.')
        with self.lock:
            if not self.is_ready(): raise ValueError('Primeiro clique em Indexar PDFs.')
            index=self.index
            lex=self.bm25.search(question,limit=30)
            warning=''
            engine='BM25'
            ranking=lex
            if mode in ('hybrid','vector'):
                vectors=self.vectors
                profile=profile_for(embedding_model,embedding_profile)
                if not vectors or vectors.get('fingerprint')!=index['fingerprint'] or not vectors.get('complete'):
                    warning='Índice vetorial ausente ou incompleto; recuperando por BM25.'
                elif not embedding_model or embedding_model!=vectors.get('model'):
                    warning='Selecione o mesmo modelo usado na indexação vetorial; recuperando por BM25.'
                elif profile!=vectors.get('profile'):
                    warning='Perfil de embeddings diferente ou legado; gere o índice novamente. Fallback BM25.'
                else:
                    try:
                        with self.inference_lock:q=embed(self.base_url,embedding_model,embedding_input(question,profile,True))
                        semantic=[]
                        for i,c in enumerate(index['chunks']):
                            vec=vectors['vectors'].get(c['id'])
                            if vec:
                                if len(q)!=len(vec):raise ValueError('Dimensão dos vetores mudou; reindexe embeddings.')
                                sim=cosine(q,vec)
                                semantic.append((i,sim))
                        semantic.sort(key=lambda a:-a[1])
                        semantic=semantic[:30]
                        ranking=combine_scores(lex,semantic,limit=30) if mode=='hybrid' else semantic
                        engine='BM25 + embeddings (RRF)' if mode=='hybrid' else 'Vetorial (cosseno)'
                    except (LMStudioError,ValueError) as exc:
                        warning='Embeddings indisponíveis; fallback BM25. Detalhe: '+str(exc)[:180]
            # Retornos contêm só os trechos de maior relevância: nunca o PDF inteiro.
            evidence=pick_context(index,ranking,top_k,max_chars)
            return {'evidence':evidence,'engine':engine,'warning':warning,
                    'top_k_requested':top_k,'top_k_sent':len(evidence),
                    'ranked_count':len(ranking),'context_limited':any(e['truncated'] for e in evidence),
                    'requested_engine':mode,'retrieval_query':question,
                    'context_chars':sum(len(s['text']) for s in evidence),
                    'retrieval_seconds':round(time.perf_counter()-started,4),
                    'max_chars':max_chars}

    def ask(self,request):
        revision=self.collection_revision
        q=str(request.get('question','')).strip()[:1000]
        if not q:raise ValueError('Digite uma pergunta.')
        model=str(request.get('model','')).strip()
        if not model:raise ValueError('Selecione um modelo de geração no LM Studio.')
        no_rag=bool(request.get('no_rag',False))
        top_k=number(request.get('top_k',3),1,5,'Top-K',True)
        context_budget=max(1000,min(int(request.get('context_budget',2500)),4000))
        mode=str(request.get('mode','bm25'))
        embedding_model=str(request.get('embedding_model','')).strip()
        temperature=number(request.get('temperature',.1),0,1,'Temperatura')
        top_p=number(request.get('top_p',.95),.01,1,'Top-p')
        max_tokens=number(request.get('max_tokens',350),32,2048,'Máximo de geração',True)
        timeout_seconds=number(request.get('timeout_seconds',1800),60,7200,'Tempo de espera (segundos)',True)
        context_length=number(request.get('context_length',4096),1024,131072,'Contexto',True)
        seed=request.get('seed')
        if seed not in (None,''):seed=number(seed,0,2147483647,'Seed',True)
        else:seed=None
        history=history_pairs(request.get('history',[]))
        images=request.get('images',[])
        detail=self.model_detail(model)
        if detail['type']=='embedding':raise ValueError('Escolha um LLM para conversar, não um modelo de embeddings.')
        has_images=bool(images) or any(isinstance(m['content'],list) for m in history)
        if has_images and not detail['vision']:raise ValueError('O servidor não confirmou suporte a imagens neste modelo.')
        reasoning=request.get('reasoning','auto')
        if reasoning!='auto' and reasoning not in detail['reasoning_options']:
            raise ValueError('Reasoning não disponível nesse modelo/API.')
        if reasoning!='auto' and detail['reasoning_control']=='responses' and seed is not None:
            raise ValueError('Seed não está disponível no transporte Responses com reasoning. Deixe em branco.')
        effective_context=min(context_length,detail.get('loaded_context_length') or 4096,
                              detail.get('max_context_length') or detail.get('loaded_context_length') or 4096)
        retrieval_query=q
        if history and (len(q.split())<7 or re.search(r'\b(isso|esse|essa|esses|elas|eles|anterior)\b',q.lower())):
            prior=[m['content'] if isinstance(m['content'],str) else m['content'][0]['text'] for m in history if m['role']=='user']
            retrieval_query=' '.join(prior[-2:]+[q])[-2400:]
        retrieval={'evidence':[],'engine':'Sem RAG','warning':'','context_chars':0,'max_chars':context_budget} if no_rag else self.retrieve(retrieval_query,top_k,context_budget,mode,embedding_model,str(request.get('embedding_profile','auto')))
        if not no_rag and not retrieval['evidence']:
            return {'answer':'Nenhum trecho relevante foi encontrado na busca lexical. Reformule a pergunta ou teste a busca híbrida.',
                'citations':check_citations('',[]),'time_seconds':0,'usage':{},'finish_reason':'no_context',**retrieval}
        instructions=str(request.get('instructions','')).strip()
        if len(instructions)>800:raise ValueError('Instruções adicionais: máximo de 800 caracteres.')
        while True:
            messages=prompt_for(q,retrieval['evidence'])
            messages[0]['content']+=' O histórico serve apenas à continuidade, não como evidência científica. As fontes [F1] etc referem-se somente aos trechos deste turno. Diferencie imagens anexadas de evidências dos PDFs.'
            if instructions:messages[0]['content']+=' Preferências de formato do participante: '+instructions
            if detail['reasoning_control']=='qwen3_prompt':
                messages[-1]['content']+='\n'+('/think' if reasoning=='on' else '/no_think')
            messages[-1]['content']=clean_content(messages[-1]['content'],images)
            try:
                messages,dropped,estimated=fit_messages(messages[0],messages[-1],history,effective_context,max_tokens)
                break
            except ValueError:
                evidence=retrieval['evidence']
                # Mantém o top-K; reduz o texto para o contexto real do modelo.
                if not evidence or all(len(e['text'])<=170 for e in evidence):raise
                for e in evidence:
                    size=max(170,int(len(e['text'])*.8))
                    if size<len(e['text']):e['truncated']=True
                    e['text']=e['text'][:size]
                retrieval['context_chars']=sum(len(e['text']) for e in evidence)
                retrieval['context_limited']=True
        if self.auto_backend:self.connected_models()
        with self.inference_lock:
            if revision!=self.collection_revision:
                raise ValueError('A base foi alterada durante a consulta. Inicie uma nova conversa.')
            before=memory_snapshot()
            start=time.monotonic()
            result=chat(self.base_url,model,messages,max_tokens=max_tokens,temperature=temperature,top_p=top_p,seed=seed,
                        reasoning=reasoning if reasoning!='auto' and detail['reasoning_control']=='responses' else None,
                        timeout=timeout_seconds)
            elapsed=round(time.monotonic()-start,2)
            after=memory_snapshot()
        citations=check_citations(result['answer'],retrieval['evidence'])
        alerts=[]
        if dropped:alerts.append(f'{dropped//2} turno(s) antigo(s) omitido(s) do envio para caber no contexto; continuam visíveis na conversa.')
        if effective_context<context_length:alerts.append(f'Orçamento limitado a {effective_context} tokens; aplique o contexto no modelo para usar mais.')
        if not no_rag and not citations['has_citation']:
            alerts.append('Resposta sem marcadores de fonte; confira os trechos antes de usar.')
        if citations['invalid_citations']:
            alerts.append('A resposta cita fragmentos ausentes do contexto.')
        if result['finish_reason']=='length':alerts.append('Resposta interrompida pelo limite de geração.')
        if alerts:retrieval['warning']=' '.join(filter(None,[retrieval['warning'],*alerts]))
        return {'answer':result['answer'],'usage':result['usage'],'finish_reason':result['finish_reason'],
                'model':model,'base_url':self.base_url,
                'prompt_chars':sum(len(m['content']) if isinstance(m['content'],str) else sum(len(x.get('text','')) for x in m['content']) for m in messages),
                'history_messages_sent':len(messages)-2,'history_messages_dropped':dropped,
                'estimated_input_tokens':estimated,'effective_context_length':effective_context,
                'settings':{'top_k':top_k,'context_budget':context_budget,'temperature':temperature,'top_p':top_p,'max_tokens':max_tokens,'seed':seed,'timeout_seconds':timeout_seconds,
                            'reasoning':reasoning,'context_length':context_length,'reasoning_control':detail['reasoning_control']},
                'memory_before':before,'memory_after':after,
                'output_tokens_per_second':round(result['usage'].get('completion_tokens',0)/elapsed,2) if elapsed else None,
                'time_seconds':elapsed,'citations':citations,**retrieval}

    def start_embedding(self, model,profile='auto'):
        if not model:raise ValueError('Escolha um modelo de embeddings. Exemplo: nomic-embed-text-v1.5.')
        profile=profile_for(model,profile)
        with self.lock:
            if not self.is_ready():raise ValueError('Indexe os PDFs antes de criar embeddings.')
            if self.job['status']=='running':raise ValueError('Já existe uma indexação em andamento.')
            index=self.index
            fingerprint=index['fingerprint']
            existing=self.vectors or {}
            if existing and not existing.get('profile') and VECTOR_FILE.is_file():
                backup=DATA/f'vetores_legado_{time.time_ns()}.json'
                backup.write_bytes(VECTOR_FILE.read_bytes())
            cache_file=DATA/'embedding_cache.json'
            cache=load_json(cache_file) or {}
            namespace=model+'|'+profile
            cached=cache.setdefault(namespace,{})
            if existing.get('fingerprint')==fingerprint and existing.get('model')==model and existing.get('profile')==profile:
                vectors=dict(existing.get('vectors',{}))
            else:
                vectors={}
            self.job={'status':'running','done':len(vectors),'total':len(index['chunks']),'error':'','model':model,'profile':profile,'reused':len(vectors)}
        def worker():
            try:
                for c in index['chunks']:
                    if c['id'] in vectors:continue
                    digest=hashlib.sha256(c['text'].encode('utf-8')).hexdigest()
                    if digest in cached:
                        vector=cached[digest]
                        with self.lock:self.job['reused']+=1
                    else:
                        with self.inference_lock:vector=embed(self.base_url,model,embedding_input(c['text'],profile))
                        cached[digest]=vector
                    vectors[c['id']]=vector
                    with self.lock:self.job['done']=len(vectors)
                    if len(vectors)%10==0:
                        with self.lock:
                            partial={'fingerprint':fingerprint,'model':model,'profile':profile,'complete':False,'vectors':vectors}
                            atomic_json(VECTOR_FILE,partial)
                            atomic_json(cache_file,cache)
                            self.vectors=partial
                with self.lock:
                    complete={'fingerprint':fingerprint,'model':model,'profile':profile,'complete':True,'vectors':vectors}
                    atomic_json(VECTOR_FILE,complete)
                    atomic_json(cache_file,cache)
                    self.vectors=complete
                    self.job['status']='done'
            except Exception as exc:
                with self.lock:
                    self.job['status']='error';self.job['error']=str(exc)
                    partial={'fingerprint':fingerprint,'model':model,'profile':profile,'complete':False,'vectors':vectors}
                    atomic_json(VECTOR_FILE,partial)
                    atomic_json(cache_file,cache)
                    self.vectors=partial
        threading.Thread(target=worker,daemon=True,name='RCA-RAG-Embeddings').start()
        return dict(self.job)

STATE=None

class Handler(BaseHTTPRequestHandler):
    server_version='RCA-RAG/0.1'
    def log_message(self,format,*args):logging.info('%s - %s',self.address_string(),format%args)
    def json_out(self,obj,status=200):
        body=json.dumps(obj,ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers();self.wfile.write(body)
    def html_out(self):
        content=WEB.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type','text/html; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Length',str(len(content)))
        self.end_headers();self.wfile.write(content)
    def err(self,exc):
        logging.exception('Erro da operação')
        self.json_out({'error':str(exc)},400 if isinstance(exc,(ValueError,LMStudioError)) else 500)
    def read_json(self):
        length=int(self.headers.get('Content-Length','0'))
        if length>8_000_000:raise ValueError('Requisição muito grande. Reduza o histórico ou as imagens.')
        if length<0:raise ValueError('Requisição inválida.')
        body=self.rfile.read(length)
        return json.loads(body) if body else {}
    def do_GET(self):
        route=urlsplit(self.path).path
        try:
            if route in ('/','/index.html'):return self.html_out()
            if route=='/app.js':
                content=(ROOT/'web'/'app.js').read_bytes()
                self.send_response(200)
                self.send_header('Content-Type','text/javascript; charset=utf-8')
                self.send_header('Cache-Control','no-store')
                self.send_header('Content-Length',str(len(content)))
                self.end_headers();self.wfile.write(content);return
            if route=='/api/info':return self.json_out(STATE.info())
            if route=='/api/job':
                with STATE.lock:return self.json_out(dict(STATE.job))
            if route=='/api/models':
                catalog=STATE.catalog()
                return self.json_out({'models':[x['id'] for x in catalog],'catalog':catalog,'base_url':STATE.base_url})
            if route=='/api/health':return self.json_out({'status':'ok','server':'RCA-RAG', 'local_api_only':True})
            return self.json_out({'error':'Rota não encontrada'},404)
        except Exception as exc:return self.err(exc)
    def do_POST(self):
        parsed=urlsplit(self.path);route=parsed.path
        try:
            if route=='/api/upload':
                name=unquote(parse_qs(parsed.query).get('name',[''])[0])
                if not name or name!=Path(name).name or not name.lower().endswith('.pdf') or '/' in name or '\\' in name or ':' in name:
                    raise ValueError('Nome de arquivo inválido: use apenas PDF.')
                length=int(self.headers.get('Content-Length','0'))
                if not 5<=length<=MAX_PDF_SIZE:raise ValueError('PDF deve ter no máximo 30 MB.')
                raw=self.rfile.read(length)
                if not raw.startswith(b'%PDF-'):raise ValueError('Arquivo não parece PDF válido.')
                path=DOCS/name
                if path.exists():raise ValueError('Um documento com esse nome já existe. Renomeie o PDF antes de importar.')
                path.write_bytes(raw)
                return self.json_out({'ok':True,'name':name,'note':'Clique em Indexar PDFs para atualizar o índice.'})
            data=self.read_json()
            if route=='/api/documents/remove':
                if self.headers.get('Content-Type','').split(';')[0].strip().lower()!='application/json':
                    return self.json_out({'error':'Use uma requisição JSON para confirmar a remoção.'},415)
                origin=self.headers.get('Origin')
                if origin and origin!='http://'+self.headers.get('Host',''):
                    return self.json_out({'error':'Origem da requisição não autorizada.'},403)
                return self.json_out(STATE.remove_documents(data))
            if route=='/api/index':return self.json_out(STATE.rebuild(data.get('chunk_size',880),data.get('overlap_words',24)))
            if route=='/api/search':
                question=str(data.get('question','')).strip()[:1000]
                if not question:raise ValueError('Digite uma pergunta.')
                k=number(data.get('top_k',3),1,5,'Top-K',True)
                max_chars=max(1000,min(int(data.get('context_budget',2500)),4000))
                return self.json_out(STATE.retrieve(question,k,max_chars,str(data.get('mode','bm25')),str(data.get('embedding_model','')),str(data.get('embedding_profile','auto'))))
            if route=='/api/ask':return self.json_out(STATE.ask(data))
            if route=='/api/model/load':return self.json_out(STATE.load_model(data))
            if route=='/api/embedding/start':return self.json_out(STATE.start_embedding(str(data.get('embedding_model','')).strip(),str(data.get('embedding_profile','auto'))))
            return self.json_out({'error':'Rota não encontrada'},404)
        except Exception as exc:return self.err(exc)
    def do_DELETE(self):
        return self.json_out({'error':'Exclusão desabilitada para preservar os PDFs originais.'},403)

def main():
    parser=argparse.ArgumentParser(description='RCA-RAG Lab: demonstração de RAG com PDFs locais')
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--lmstudio',default='auto',help='auto (1234/1235) ou URL local http://127.0.0.1:1234/v1')
    parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--workspace',type=Path,default=ROOT/'demo',
                        help='Pasta da coleção de PDFs e índices (padrão: demo/)')
    args=parser.parse_args()
    global STATE
    configure_workspace(args.workspace)
    STATE=State(args.lmstudio)
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    url=f'http://127.0.0.1:{args.port}'
    print('\n'+'='*56+'\n  RCA-RAG Lab 0.1 — servidor LOCAL\n  '+url+'\n  API LM Studio/Bionic: '+('detecção automática 1234/1235' if STATE.auto_backend else STATE.base_url)+'\n  O app só contata localhost; selecione um LLM local.\n'+'='*56+'\n')
    if not args.no_browser:threading.Timer(1.0,lambda:webbrowser.open(url)).start()
    try:server.serve_forever()
    except KeyboardInterrupt:print('\nServidor encerrado.')
    finally:server.server_close()

if __name__=='__main__':main()
