"""Fluxo genérico de participantes: coleção vazia, upload, busca e isolamento."""
import io
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
import app

def sample_pdf():
    writer=PdfWriter()
    page=writer.add_blank_page(width=595,height=842)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),
        NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):font})})
    stream=DecodedStreamObject()
    stream.set_data(b'BT /F1 12 Tf 50 700 Td (A biblioteca abre as 9 horas e fecha as 18 horas. O emprestimo dura sete dias. Os livros devem ser devolvidos no balcao principal.) Tj ET')
    page[NameObject('/Contents')]=writer._add_object(stream)
    output=io.BytesIO();writer.write(output);return output.getvalue()

class CollectionTests(unittest.TestCase):
    def test_empty_upload_index_reload_and_isolation(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with patch.multiple(app,DOCS=app.DOCS,DATA=app.DATA,INDEX_FILE=app.INDEX_FILE,VECTOR_FILE=app.VECTOR_FILE):
                app.configure_workspace(root/'primeira')
                state=app.State('auto')
                self.assertEqual(state.info()['pdfs'],[])
                self.assertFalse(state.is_ready())
                self.assertEqual(state.info()['chunk_count'],0)
                with self.assertRaises(ValueError):state.retrieve('biblioteca')
                server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
                thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                opener=build_opener(ProxyHandler({}))
                base=f'http://127.0.0.1:{server.server_port}'
                with patch.object(app,'STATE',state):
                    try:
                        with self.assertRaises(HTTPError) as caught:
                            opener.open(base+'/api/questions')
                        self.assertEqual(caught.exception.code,404);caught.exception.close()
                        with opener.open(Request(base+'/api/upload?name=biblioteca.pdf',data=sample_pdf())):pass
                        with opener.open(Request(base+'/api/index',data=b'{}')) as response:
                            self.assertEqual(json.load(response)['documents'],1)
                        with opener.open(Request(base+'/api/search',data=json.dumps({'question':'biblioteca horario'}).encode())) as response:
                            result=json.load(response)
                        self.assertIn('9 horas',result['evidence'][0]['text'])
                        self.assertEqual(result['evidence'][0]['page'],1)
                        self.assertTrue(app.State('auto').is_ready())
                    finally:server.shutdown();server.server_close()
                app.configure_workspace(root/'segunda')
                self.assertEqual(app.State('auto').info()['pdfs'],[])
                self.assertFalse(app.State('auto').is_ready())
                app.configure_workspace(root/'primeira')
                self.assertTrue(app.State('auto').is_ready())
                self.assertEqual(len(app.State('auto').info()['pdfs']),1)

if __name__=='__main__':unittest.main()
