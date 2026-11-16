"""Remoção seletiva/total, persistência, concorrência e isolamento da coleção."""
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import HTTPError
import app
from test_collections import sample_pdf

class RemovalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.paths=patch.multiple(app,DOCS=app.DOCS,DATA=app.DATA,INDEX_FILE=app.INDEX_FILE,VECTOR_FILE=app.VECTOR_FILE)
        self.paths.start()
        app.configure_workspace(self.root/'colecao')
        self.state=app.State('http://127.0.0.1:1234/v1')
        (app.DOCS/'primeiro.pdf').write_bytes(sample_pdf())
        (app.DOCS/'segundo.pdf').write_bytes(sample_pdf().replace(b'biblioteca',b'hemeroteca'))
        self.state.rebuild()
        for name in ('vetores.json','embedding_cache.json','vetores_legado_123.json'):
            app.atomic_json(app.DATA/name,{'dados_antigos':True})
        app.atomic_json(app.DATA/'configuracoes_modelo.jsonl',{'preservar':True})
        self.state.vectors={'fingerprint':self.state.index['fingerprint'],'vectors':{}}
    def tearDown(self):
        self.paths.stop()
        self.temp.cleanup()
    def remove(self, **values):
        return self.state.remove_documents({'confirm':True,'filenames':['primeiro.pdf'],**values})
    def test_selected_removed_from_search_and_restart_and_archived(self):
        result=self.remove()
        self.assertEqual(result['remaining'],1)
        self.assertTrue(result['indexed'])
        self.assertEqual((Path(result['archived_to'])/'primeiro.pdf').read_bytes(),sample_pdf())
        self.assertFalse((app.DOCS/'primeiro.pdf').exists())
        self.assertTrue((app.DOCS/'segundo.pdf').is_file())
        for state in (self.state,app.State('auto')):
            docs=state.retrieve('emprestimo')['evidence']
            self.assertTrue(docs)
            self.assertEqual({d['doc'] for d in docs},{'segundo.pdf'})
            self.assertIsNone(state.vectors)
        for name in ('vetores.json','embedding_cache.json','vetores_legado_123.json'):
            self.assertFalse((app.DATA/name).exists())
        self.assertTrue((app.DATA/'configuracoes_modelo.jsonl').exists())
    def test_clear_all_even_without_pdfs_and_preserve_other_collections(self):
        outside=self.root/'outra'
        outside.mkdir()
        (outside/'original.pdf').write_bytes(sample_pdf())
        result=self.remove(all=True)
        self.assertEqual(set(result['removed']),{'primeiro.pdf','segundo.pdf'})
        self.assertEqual(result['remaining'],0)
        self.assertFalse(self.state.info()['base_has_data'])
        self.assertFalse(app.INDEX_FILE.exists())
        self.assertFalse(app.State('auto').is_ready())
        self.assertEqual((outside/'original.pdf').read_bytes(),sample_pdf())
        with self.assertRaises(ValueError):
            self.state.retrieve('biblioteca')
        app.atomic_json(app.DATA/'embedding_cache.json',{'stale':[]})
        self.assertTrue(self.state.info()['base_has_data'])
        self.assertEqual(self.remove(all=True)['removed'],[])
        self.assertFalse((app.DATA/'embedding_cache.json').exists())
    def test_validate_entire_selection_before_changes(self):
        for values in ({'confirm':False},{'all':'true'},{'filenames':[]},
                       {'filenames':['primeiro.pdf','../original.pdf']},
                       {'filenames':['primeiro.pdf','ausente.pdf']},
                       {'filenames':['C:/original.pdf']},{'filenames':[None]},
                       {'filenames':'primeiro.pdf'}):
            with self.assertRaises(ValueError):
                self.remove(**values)
            self.assertTrue((app.DOCS/'primeiro.pdf').exists())
            self.assertTrue(self.state.is_ready())
    def test_block_while_embedding_or_model_is_busy(self):
        self.state.job['status']='running'
        with self.assertRaisesRegex(ValueError,'embeddings'):
            self.remove()
        self.state.job['status']='idle'
        with self.state.inference_lock:
            with self.assertRaisesRegex(ValueError,'resposta do modelo'):
                self.remove()
        self.assertTrue(self.state.is_ready())
    def test_failed_move_rolls_back_before_changing_index(self):
        rename=Path.rename
        def fail(source,target):
            if source==app.DOCS/'segundo.pdf':
                raise PermissionError('Arquivo em uso')
            return rename(source,target)
        with patch.object(Path,'rename',fail):
            with self.assertRaises(PermissionError):
                self.remove(all=True)
        self.assertEqual(len(app.pdf_files(app.DOCS)),2)
        self.assertTrue(self.state.is_ready())
    def test_nonextractable_remaining_pdf_does_not_keep_old_evidence(self):
        (app.DOCS/'segundo.pdf').write_bytes(b'%PDF-invalid')
        result=self.remove()
        self.assertFalse(result['indexed'])
        self.assertTrue(result['warning'])
        self.assertIsNone(self.state.index)
        self.assertFalse(app.INDEX_FILE.exists())
        with self.assertRaises(ValueError):
            self.state.retrieve('biblioteca')
    def test_http_json_confirmation_and_origin(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        opener=build_opener(ProxyHandler({}))
        url=f'http://127.0.0.1:{server.server_port}/api/documents/remove'
        body=json.dumps({'confirm':True,'filenames':['primeiro.pdf']}).encode()
        try:
            with patch.object(app,'STATE',self.state):
                for headers,code in [({'Content-Type':'text/plain'},415),
                                     ({'Content-Type':'application/json','Origin':'https://external.invalid'},403)]:
                    with self.assertRaises(HTTPError) as caught:
                        opener.open(Request(url,data=body,headers=headers))
                    self.assertEqual(caught.exception.code,code)
                    caught.exception.close()
                    self.assertTrue(self.state.is_ready())
                with opener.open(Request(url,data=body,headers={'Content-Type':'application/json'})) as response:
                    self.assertEqual(json.load(response)['remaining'],1)
        finally:
            server.shutdown()
            server.server_close()

if __name__=='__main__':
    unittest.main()
