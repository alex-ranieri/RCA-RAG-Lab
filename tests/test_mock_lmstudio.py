"""Teste de contrato da API, sem qualquer modelo real."""
import json
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from lmstudio_api import list_models, chat, embed, LMStudioError

class FakeLMStudio(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def respond(self, data):
        output=json.dumps(data).encode()
        self.send_response(200);self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(output)))
        self.end_headers()
        try:self.wfile.write(output)
        except (BrokenPipeError,ConnectionError):pass
    def do_GET(self):
        if self.path=='/v1/models':return self.respond({'data':[{'id':'mock-chat'},{'id':'mock-embedding'}]})
        self.send_error(404)
    def do_POST(self):
        data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.path=='/v1/chat/completions':
            if 'slow-model-test' in str(data.get('messages')):time.sleep(.15)
            has_sources='[F1]' in str(data.get('messages'))
            return self.respond({'choices':[{'message':{'content':'Com evidência [F1].' if has_sources else 'Sem fonte.'},'finish_reason':'stop'}], 'usage':{'total_tokens':52}})
        if self.path=='/v1/embeddings':
            return self.respond({'data':[{'embedding':[1,0.2,0.4,0.1]}]})
        self.send_error(404)

class LMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),FakeLMStudio)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}/v1'
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close()
    def test_models(self):self.assertEqual(list_models(self.url)[0],'mock-chat')
    def test_chat(self):
        result=chat(self.url,'mock-chat',[{'role':'user','content':'[F1]'}])
        self.assertIn('[F1]',result['answer']);self.assertEqual(result['usage']['total_tokens'],52)
    def test_embedding(self):self.assertEqual(len(embed(self.url,'mock-embedding','search_query: genoma')),4)
    def test_slow_model_can_finish_with_longer_wait(self):
        messages=[{'role':'user','content':'slow-model-test'}]
        with self.assertRaisesRegex(LMStudioError,'excedeu a espera'):
            chat(self.url,'mock-chat',messages,timeout=.02)
        self.assertEqual(chat(self.url,'mock-chat',messages,timeout=2)['answer'],'Sem fonte.')

if __name__=='__main__':unittest.main()
