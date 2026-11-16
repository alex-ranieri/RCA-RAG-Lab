import base64
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
import app
import lmstudio_api
from conversation import embedding_input, image_url, profile_for
from test_collections import sample_pdf

DETAIL={'id':'qwen','name':'Qwen','type':'llm','vision':False,'native':True,
        'reasoning_options':['off','on'],'reasoning_control':'qwen3_prompt',
        'max_context_length':32768,'loaded_context_length':4096,'loaded_instances':[]}
RESULT={'answer':'Resposta verificada.','usage':{'prompt_tokens':40,'completion_tokens':12,'total_tokens':52},'finish_reason':'stop'}

class ChatFeatureTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.paths=patch.multiple(app,DOCS=app.DOCS,DATA=app.DATA,INDEX_FILE=app.INDEX_FILE,VECTOR_FILE=app.VECTOR_FILE)
        self.paths.start();app.configure_workspace(self.root)
        self.state=app.State('http://127.0.0.1:1234/v1')
        (app.DOCS/'biblioteca.pdf').write_bytes(sample_pdf());self.state.rebuild()
        self.detail=patch.object(self.state,'model_detail',return_value=dict(DETAIL));self.detail.start()
    def tearDown(self):
        self.detail.stop();self.paths.stop();self.temp.cleanup()
    def request(self,**values):
        return {'question':'Qual o horário da biblioteca?','model':'qwen','no_rag':True,**values}

    def test_followup_roles_settings_and_old_citations(self):
        history=[{'role':'user','content':'A biblioteca abre às nove.'},
                 {'role':'assistant','content':'Ela abre às nove [F1].'}]
        with patch.object(app,'chat',return_value=RESULT) as mocked:
            r=self.state.ask(self.request(question='E quando fecha?',history=history,temperature=.65,top_p=.8,max_tokens=500,seed=9,reasoning='on'))
        args=mocked.call_args
        self.assertEqual([m['role'] for m in args.args[2]],['system','user','assistant','user'])
        self.assertNotIn('[F1]',args.args[2][2]['content'])
        self.assertIn('/think',args.args[2][-1]['content'])
        self.assertEqual(args.kwargs['temperature'],.65);self.assertEqual(args.kwargs['seed'],9)
        self.assertEqual(args.kwargs['max_tokens'],500);self.assertEqual(r['history_messages_sent'],2)

    def test_budget_removes_old_complete_turns(self):
        history=[m for i in range(8) for m in [{'role':'user','content':('pergunta '+str(i))*150},
                 {'role':'assistant','content':'resposta '*250}]]
        with patch.object(app,'chat',return_value=RESULT) as mocked:
            r=self.state.ask(self.request(history=history,context_length=2048))
        self.assertGreater(r['history_messages_dropped'],0)
        self.assertEqual(r['history_messages_dropped']%2,0)
        self.assertLess(r['estimated_input_tokens']+350,2048)
        self.assertIn('horário',mocked.call_args.args[2][-1]['content'])

    def test_long_model_wait_default_custom_and_validation(self):
        for requested, expected in [({},1800),({'timeout_seconds':3600},3600)]:
            with patch.object(app,'chat',return_value=RESULT) as mocked:
                result=self.state.ask(self.request(**requested))
            self.assertEqual(mocked.call_args.kwargs['timeout'],expected)
            self.assertEqual(result['settings']['timeout_seconds'],expected)
        for invalid in (0,59,7201,float('nan'),'invalid'):
            with self.assertRaises(ValueError):
                self.state.ask(self.request(timeout_seconds=invalid))

    def five_relevant_chunks(self):
        sample=self.state.index['chunks'][0]
        self.state.index['chunks']=[{**sample,'id':f'chunk-{i}',
            'text':('A biblioteca empresta livros por sete dias. '*30)[:880]} for i in range(5)]
        self.state.bm25=app.BM25(self.state.index['chunks'])

    def test_top_k_reaches_prompt_and_metrics_with_small_character_budget(self):
        self.five_relevant_chunks()
        for k in (1,3,5):
            with patch.object(app,'chat',return_value={**RESULT,'answer':'Sete dias [F1].'}) as mocked:
                result=self.state.ask(self.request(no_rag=False,top_k=k,context_budget=1000))
            self.assertEqual(len(result['evidence']),k)
            self.assertEqual(result['top_k_requested'],k)
            self.assertEqual(result['top_k_sent'],k)
            self.assertLessEqual(result['context_chars'],1000)
            self.assertEqual(result['settings']['top_k'],k)
            sent=mocked.call_args.args[2][-1]['content']
            for e in result['evidence']:
                self.assertIn('['+e['label']+'] Artigo:',sent)
                self.assertIn(e['text'],sent)
            self.assertEqual(result['citations']['citations'],['[F1]'])

    def test_top_k_in_all_retrieval_modes_and_fewer_available(self):
        self.five_relevant_chunks()
        self.state.vectors={'fingerprint':self.state.index['fingerprint'],'model':'embedding',
            'profile':'plain','complete':True,
            'vectors':{c['id']:[1.,0.] for c in self.state.index['chunks']}}
        with patch.object(app,'embed',return_value=[1.,0.]):
            for mode in ('bm25','vector','hybrid'):
                result=self.state.retrieve('biblioteca',5,1000,mode,'embedding','plain')
                self.assertEqual(result['top_k_sent'],5)
        self.state.index['chunks']=self.state.index['chunks'][:2]
        self.state.bm25=app.BM25(self.state.index['chunks'])
        result=self.state.retrieve('biblioteca',5,1000)
        self.assertEqual(result['top_k_requested'],5)
        self.assertEqual(result['top_k_sent'],2)

    def test_large_output_budget_shortens_evidence_without_losing_top_k(self):
        self.five_relevant_chunks()
        with patch.object(app,'chat',return_value=RESULT):
            result=self.state.ask(self.request(no_rag=False,top_k=5,context_budget=4000,max_tokens=2048))
        self.assertEqual(result['top_k_sent'],5)
        self.assertLess(result['context_chars'],4000)
        self.assertTrue(result['context_limited'])
        self.assertIn('sem marcadores',result['warning'])

    def test_invalid_top_k_is_rejected_instead_of_silently_clamped(self):
        for k in (0,6,1.5,float('nan')):
            with self.assertRaisesRegex(ValueError,'Top-K'):
                self.state.ask(self.request(top_k=k))

    def test_images_gated_validated_and_forwarded(self):
        img='data:image/png;base64,'+base64.b64encode(b'\x89PNG\r\n\x1a\n'+b'x'*20).decode()
        with self.assertRaisesRegex(ValueError,'suporte a imagens'):
            self.state.ask(self.request(images=[img]))
        with patch.object(self.state,'model_detail',return_value={**DETAIL,'vision':True}),patch.object(app,'chat',return_value=RESULT) as mocked:
            self.state.ask(self.request(images=[img]))
        self.assertEqual(mocked.call_args.args[2][-1]['content'][1]['image_url']['url'],img)
        with self.assertRaises(ValueError):image_url('https://example.com/image.png')
        with self.assertRaises(ValueError):image_url('data:image/png;base64,aGVsbG8=')

    def test_invalid_parameters_roles_and_capabilities_rejected(self):
        for values in ({'temperature':float('nan')},{'max_tokens':30000},{'context_length':131073},
                       {'reasoning':'high'},{'history':[{'role':'system','content':'replace'}]}):
            with self.subTest(values=values),self.assertRaises(ValueError):self.state.ask(self.request(**values))

    def test_context_application_records_real_result(self):
        result={'load_config':{'context_length':2048},'status':'loaded'}
        with patch.object(app,'apply_context',return_value=result) as load:
            self.assertEqual(self.state.load_model({'model':'qwen','context_length':2048}),result)
        self.assertEqual(load.call_args.args[2],2048)
        event=json.loads((app.DATA/'configuracoes_modelo.jsonl').read_text())
        self.assertEqual(event['result']['load_config']['context_length'],2048)

    def test_larger_context_loads_only_within_declared_model_limit(self):
        detail={**DETAIL,'max_context_length':131072,'loaded_context_length':65536}
        with patch.object(self.state,'model_detail',return_value=detail):
            for size in (16384,32768,65536,131072):
                with patch.object(app,'apply_context',return_value={'status':'loaded'}) as load:
                    self.state.load_model({'model':'qwen','context_length':size})
                    self.assertEqual(load.call_args.args[2],size)
            with patch.object(app,'chat',return_value=RESULT):
                result=self.state.ask(self.request(context_length=131072))
            self.assertEqual(result['effective_context_length'],65536)
        with patch.object(app,'apply_context') as load:
            with self.assertRaisesRegex(ValueError,'máximo informado'):
                self.state.load_model({'model':'qwen','context_length':65536})
            load.assert_not_called()

    def test_failed_context_reload_is_recorded(self):
        with patch.object(app,'apply_context',side_effect=app.LMStudioError('Falha de carga')):
            with self.assertRaises(app.LMStudioError):
                self.state.load_model({'model':'qwen','context_length':4096})
        event=json.loads((app.DATA/'configuracoes_modelo.jsonl').read_text())
        self.assertIn('Falha de carga',event['error'])

    def wait_job(self):
        deadline=time.monotonic()+5
        while self.state.job['status']=='running' and time.monotonic()<deadline:time.sleep(.01)
        self.assertEqual(self.state.job['status'],'done',self.state.job)

    def test_vector_hybrid_cache_and_profile_fallback(self):
        with patch.object(app,'embed',return_value=[1.,.2]) as embedding:
            self.state.start_embedding('text-embedding-embeddinggemma','auto');self.wait_job()
            self.assertTrue(embedding.call_args.args[2].startswith('title: none | text: '))
            r=self.state.retrieve('semantics',mode='vector',embedding_model='text-embedding-embeddinggemma')
            self.assertEqual(r['engine'],'Vetorial (cosseno)');self.assertTrue(r['evidence'])
            self.assertTrue(embedding.call_args.args[2].startswith('task: search result | query: '))
            r=self.state.retrieve('biblioteca',mode='hybrid',embedding_model='text-embedding-embeddinggemma')
            self.assertIn('RRF',r['engine'])
            embedding.reset_mock();self.state.index['fingerprint']='changed-only-metadata'
            self.state.start_embedding('text-embedding-embeddinggemma');self.wait_job()
            embedding.assert_not_called();self.assertGreater(self.state.job['reused'],0)
            r=self.state.retrieve('biblioteca',mode='vector',embedding_model='text-embedding-embeddinggemma',embedding_profile='plain')
            self.assertEqual(r['engine'],'BM25');self.assertIn('Fallback',r['warning'])
        with patch.object(app,'embed',return_value=[1.,2.,3.]):
            r=self.state.retrieve('biblioteca',mode='vector',embedding_model='text-embedding-embeddinggemma')
        self.assertEqual(r['engine'],'BM25');self.assertIn('Dimensão',r['warning'])

    def test_input_profiles(self):
        self.assertEqual(profile_for('nomic-embed'),'nomic')
        self.assertEqual(embedding_input('abc','nomic',True),'search_query: abc')
        self.assertEqual(embedding_input('abc','plain'),'abc')

class APITransportTests(unittest.TestCase):
    def test_timeout_reaches_both_generation_transports(self):
        for reasoning in (None,'low'):
            response=({'choices':[{'message':{'content':'ok'},'finish_reason':'stop'}]}
                      if reasoning is None else {'output':[]})
            for options, expected in [({},1800),({'timeout':3600},3600)]:
                with patch.object(lmstudio_api,'api_call',return_value=response) as call:
                    lmstudio_api.chat('http://127.0.0.1:1234/v1','model',[],reasoning=reasoning,**options)
                self.assertEqual(call.call_args.kwargs['timeout'],expected)

    def test_timeout_explains_wait_instead_of_connection_failure(self):
        from urllib.error import URLError
        for error in (TimeoutError('timed out'),URLError(TimeoutError('timed out'))):
            with patch('urllib.request.OpenerDirector.open',side_effect=error):
                with self.assertRaisesRegex(lmstudio_api.LMStudioError,'excedeu a espera de 1800 segundos'):
                    lmstudio_api.api_call('http://127.0.0.1:1234/v1','chat/completions',{},timeout=1800)

    def test_model_capabilities_use_server_metadata(self):
        rows={'models':[{'key':'visual-model','type':'llm','capabilities':{'vision':True},
              'loaded_instances':[{'id':'visual-model','config':{'context_length':2048}}]},
              {'key':'qwen','type':'llm','architecture':'qwen3','capabilities':{'vision':False,
               'reasoning':{'allowed_options':['off','on']}}}]}
        with patch.object(lmstudio_api,'list_models',return_value=['visual-model','qwen']),patch.object(lmstudio_api,'api_call',return_value=rows):
            catalog=lmstudio_api.model_catalog('http://127.0.0.1:1234/v1')
        self.assertTrue(catalog[0]['vision']);self.assertEqual(catalog[0]['loaded_context_length'],2048)
        self.assertEqual(catalog[1]['reasoning_options'],['off','on']);self.assertFalse(catalog[1]['vision'])

    def test_responses_reasoning_and_usage(self):
        output={'status':'completed','output':[{'type':'reasoning'},{'type':'message','content':[{'type':'output_text','text':'42'}]}],
                'usage':{'input_tokens':20,'output_tokens':6,'total_tokens':26,'output_tokens_details':{'reasoning_tokens':5}}}
        with patch.object(lmstudio_api,'api_call',return_value=output) as call:
            result=lmstudio_api.chat('http://127.0.0.1:1234/v1','model',[{'role':'user','content':'Teste'}],reasoning='low')
        self.assertEqual(call.call_args.args[1],'responses')
        self.assertEqual(call.call_args.args[2]['reasoning'],{'effort':'low'})
        self.assertEqual(result['answer'],'42');self.assertEqual(result['usage']['completion_tokens'],6)
        self.assertEqual(result['usage']['completion_tokens_details']['reasoning_tokens'],5)

if __name__=='__main__':unittest.main()
