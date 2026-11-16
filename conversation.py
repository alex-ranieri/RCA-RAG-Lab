"""Validação e orçamento de conversas locais; nenhum estado global de participantes."""
import base64
import math
import re

def number(value,low,high,name,integer=False):
    try:n=float(value)
    except (ValueError,TypeError):raise ValueError(f'{name}: valor inválido.')
    if not math.isfinite(n) or not low<=n<=high or (integer and n!=int(n)):
        raise ValueError(f'{name}: use um valor entre {low} e {high}.')
    return int(n) if integer else n

def image_url(value):
    if not isinstance(value,str) or len(value)>1_500_000:raise ValueError('Imagem excede 1 MB.')
    match=re.fullmatch(r'data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=]+)',value)
    if not match:raise ValueError('Use uma imagem PNG, JPEG ou WebP local.')
    try:raw=base64.b64decode(match[2],validate=True)
    except ValueError:raise ValueError('Imagem inválida.')
    if len(raw)>1024**2:raise ValueError('Imagem excede 1 MB.')
    valid=(match[1]=='png' and raw.startswith(b'\x89PNG\r\n\x1a\n') or
           match[1]=='jpeg' and raw.startswith(b'\xff\xd8\xff') or
           match[1]=='webp' and raw.startswith(b'RIFF') and raw[8:12]==b'WEBP')
    if not valid:raise ValueError('Conteúdo não corresponde ao formato da imagem.')
    return value

def clean_content(text,images=None):
    if not images:return text
    if not isinstance(images,list) or len(images)>2:raise ValueError('Anexe até duas imagens.')
    return [{'type':'text','text':text}]+[{'type':'image_url','image_url':{'url':image_url(x)}} for x in images]

def history_pairs(history):
    if not isinstance(history,list) or len(history)>40:raise ValueError('Histórico inválido ou muito longo.')
    result=[]
    for item in history:
        if not isinstance(item,dict) or item.get('role') not in ('user','assistant'):
            raise ValueError('Histórico aceita apenas usuário e assistente.')
        text=item.get('content')
        if not isinstance(text,str) or len(text)>12000:raise ValueError('Mensagem histórica inválida.')
        if item['role']=='assistant':text=re.sub(r'\[F\d+\]','[fonte de turno anterior]',text)
        result.append({'role':item['role'],'content':clean_content(text,item.get('images'))})
    if len(result)%2 or any(m['role']!=('user' if i%2==0 else 'assistant') for i,m in enumerate(result)):
        raise ValueError('Histórico deve conter pares completos de usuário e assistente.')
    return result

def estimate(messages):
    # Estimativa didática, não tokenização: imagens variam conforme o modelo.
    total=0
    for m in messages:
        content=m['content']
        if isinstance(content,list):
            total+=sum(len(x.get('text','').encode('utf-8'))/2.5 if x['type']=='text' else 1536 for x in content)
        else:total+=len(content.encode('utf-8'))/2.5
        total+=12
    return math.ceil(total)

def fit_messages(system,current,history,context,max_output):
    messages=[system]+list(history)+[current];dropped=0
    available=context-max_output-max(256,int(context*.1))
    while estimate(messages)>available and len(messages)>2:
        del messages[1:3];dropped+=2
    if estimate(messages)>available:
        raise ValueError('Pergunta/evidências/imagens excedem o orçamento estimado. Reduza evidências ou imagens, ou aplique contexto maior.')
    return messages,dropped,estimate(messages)

def profile_for(model,profile='auto'):
    if profile=='auto':
        profile='nomic' if 'nomic' in model.lower() else 'embeddinggemma' if 'embeddinggemma' in model.lower() else 'plain'
    if profile not in ('nomic','embeddinggemma','plain'):raise ValueError('Perfil de embeddings inválido.')
    return profile

def embedding_input(text,profile,query=False):
    if profile=='nomic':return ('search_query: ' if query else 'search_document: ')+text
    if profile=='embeddinggemma':return ('task: search result | query: ' if query else 'title: none | text: ')+text
    return text
