"""Cliente HTTP usando somente biblioteca padrão; nenhum dado vai para serviços externos."""
from __future__ import annotations
import json
import socket
import urllib.error
import urllib.request
from urllib.parse import urlparse

class LMStudioError(RuntimeError):pass

MODEL_TIMEOUT_SECONDS=30*60

def validate_base_url(base_url):
    url=urlparse(base_url)
    if url.scheme!='http' or url.hostname not in ('localhost','127.0.0.1','::1') or url.username or url.password:
        raise LMStudioError('Use apenas servidor local: http://127.0.0.1:1234/v1')
    if url.path.rstrip('/')!='/v1' or url.query or url.fragment:
        raise LMStudioError('A URL da API deve terminar em /v1.')
    return base_url.rstrip('/')

def api_call(base_url,endpoint,payload=None,timeout=20,native=False):
    base=validate_base_url(base_url)
    url=(base[:-3]+'/api/v1/' if native else base+'/')+endpoint.lstrip('/')
    body=None if payload is None else json.dumps(payload,ensure_ascii=False).encode('utf-8')
    request=urllib.request.Request(url,data=body,headers={'Content-Type':'application/json'},
                                   method='GET' if body is None else 'POST')
    try:
        # Ignora proxies do sistema e bloqueia redirects: PDFs/prompts ficam locais.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                raise LMStudioError('Redirecionamento da API local bloqueado.')
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        with opener.open(request, timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        detail=exc.read(700).decode('utf-8','replace')
        raise LMStudioError(f'LM Studio retornou HTTP {exc.code}: {detail}') from exc
    except (TimeoutError,socket.timeout) as exc:
        raise LMStudioError(f'O modelo local excedeu a espera de {timeout:g} segundos. '
                            'Aumente a espera em Parâmetros de geração ou reduza a saída/reasoning. '
                            'O processamento no LM Studio pode continuar; confira antes de reenviar.') from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason,(TimeoutError,socket.timeout)):
            raise LMStudioError(f'O modelo local excedeu a espera de {timeout:g} segundos. '
                                'Aumente a espera em Parâmetros de geração. '
                                'O processamento no LM Studio pode continuar; confira antes de reenviar.') from exc
        raise LMStudioError(f'Sem resposta do LM Studio em {url}. Confira servidor, modelo carregado e porta. Detalhe: {exc}') from exc
    except ConnectionError as exc:
        raise LMStudioError(f'Sem resposta do LM Studio em {url}. Confira servidor, modelo carregado e porta. Detalhe: {exc}') from exc
    except (ValueError,UnicodeError) as exc:
        raise LMStudioError('Resposta inválida da API local LM Studio.') from exc

def list_models(base_url):
    result=api_call(base_url,'models')
    return [str(m['id']) for m in result.get('data',[]) if isinstance(m,dict) and m.get('id')]

def model_catalog(base_url):
    """Capacidades declaradas pelo servidor, nunca inferidas do tamanho do nome."""
    ids=list_models(base_url)
    try:
        rows=api_call(base_url,'models',timeout=5,native=True)['models']
        details=[]
        for row in rows:
            key=row['key'];caps=row.get('capabilities') or {}
            if not isinstance(caps,dict):caps={}
            instances=row.get('loaded_instances') or []
            options=(caps.get('reasoning') or {}).get('allowed_options',[])
            # Qwen3 usa o controle por prompt documentado; níveis usam Responses.
            reasoning=[x for x in options if x in ('low','medium','high')]
            control='responses' if reasoning else None
            if row.get('architecture')=='qwen3':
                reasoning=[x for x in options if x in ('off','on')];control='qwen3_prompt'
            details.append({'id':key,'name':row.get('display_name',key),'type':row.get('type'),
                'vision':caps.get('vision') is True,'reasoning_options':reasoning,
                'reasoning_control':control,'max_context_length':row.get('max_context_length'),
                'loaded_context_length':instances[0].get('config',{}).get('context_length') if instances else None,
                'loaded_instances':instances,'native':True})
        return details
    except (LMStudioError,KeyError,TypeError):
        return [{'id':key,'name':key,'type':'embedding' if 'embed' in key.lower() else 'llm',
                 'vision':False,'reasoning_options':[],'reasoning_control':None,
                 'max_context_length':None,'loaded_context_length':None,'loaded_instances':[],
                 'native':False} for key in ids]

def apply_context(base_url,model,length,instances):
    for instance in instances:
        api_call(base_url,'models/unload',{'instance_id':instance['id']},timeout=90,native=True)
    return api_call(base_url,'models/load',{'model':model,'context_length':length,
                    'echo_load_config':True},timeout=MODEL_TIMEOUT_SECONDS,native=True)

def chat(base_url,model,messages,max_tokens=350,temperature=0.1,top_p=0.95,seed=None,reasoning=None,timeout=MODEL_TIMEOUT_SECONDS):
    payload={'model':model,'messages':messages,'temperature':temperature,'max_tokens':max_tokens,'stream':False}
    payload['top_p']=top_p
    if seed is not None:payload['seed']=seed
    if reasoning:
        converted=[]
        for m in messages:
            content=m['content']
            if isinstance(content,list):
                content=[{'type':'input_text','text':x['text']} if x['type']=='text' else
                         {'type':'input_image','image_url':x['image_url']['url']} for x in content]
            converted.append({'role':m['role'],'content':content})
        request={'model':model,'input':converted,'max_output_tokens':max_tokens,
                 'temperature':temperature,'top_p':top_p,'reasoning':{'effort':reasoning},'store':False}
        result=api_call(base_url,'responses',request,timeout=timeout)
        answer='\n'.join(c.get('text','') for item in result.get('output',[]) if item.get('type')=='message'
                         for c in item.get('content',[]) if c.get('type')=='output_text')
        usage=result.get('usage',{})
        return {'answer':answer,'usage':{'prompt_tokens':usage.get('input_tokens',0),
                'completion_tokens':usage.get('output_tokens',0),'total_tokens':usage.get('total_tokens',0),
                'completion_tokens_details':usage.get('output_tokens_details',{})},
                'finish_reason':'length' if result.get('status')=='incomplete' else 'stop'}
    result=api_call(base_url,'chat/completions',payload,timeout=timeout)
    try:
        message=result['choices'][0]['message']
        answer=message.get('content') or ''
        if isinstance(answer,list):
            answer='\n'.join(str(item.get('text','')) for item in answer if isinstance(item,dict))
        return {'answer':str(answer).strip(), 'usage':result.get('usage',{}),
                'finish_reason':result['choices'][0].get('finish_reason','')}
    except (IndexError,KeyError,TypeError) as exc:
        raise LMStudioError('Resposta inesperada no endpoint de chat.') from exc

def embed(base_url,model,text):
    result=api_call(base_url,'embeddings',{'model':model,'input':text},timeout=MODEL_TIMEOUT_SECONDS)
    try:
        vector=result['data'][0]['embedding']
        if not isinstance(vector,list) or not vector:raise ValueError('vetor vazio')
        import math
        vector=[float(v) for v in vector]
        if not all(math.isfinite(v) for v in vector):raise ValueError('vetor não finito')
        return vector
    except (IndexError,KeyError,TypeError,ValueError) as exc:
        raise LMStudioError('Modelo não retornou vetor de embedding válido. Confira se é um embedding model.') from exc
