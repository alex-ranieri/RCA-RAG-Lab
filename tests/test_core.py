import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rag_core import BM25, chunk_page, check_citations, combine_scores, cosine, pick_context, prompt_for
from lmstudio_api import validate_base_url, LMStudioError

class RagTests(unittest.TestCase):
    def test_chunks_size_and_overlap(self):
        chunks=chunk_page(' '.join('genome%d'%i for i in range(400)),max_chars=230,overlap_words=5)
        self.assertGreater(len(chunks),10)
        self.assertTrue(all(len(c)<=230 for c in chunks))
        self.assertTrue(set(chunks[0].split())&set(chunks[1].split()))

    def test_bm25_portuguese_english(self):
        chunks=[{'doc':'CHIKV.pdf','id':'a','page':2,'text':'Minimum coverage 100 reads base quality above 30 and allele frequency 10% for variants.'},
                {'doc':'DENV.pdf','id':'b','page':4,'text':'Phylogenetic clustering of samples, with no description of depth parameters.'}]
        found=BM25(chunks).search('Quais critérios de profundidade e qualidade para iSNVs?',limit=2)
        self.assertEqual(found[0][0],0)

    def test_context_limits(self):
        chunks=[{'id':'c1','doc':'CHIKV.pdf','page':1,'text':'x'*800},
                {'id':'c2','doc':'DENV.pdf','page':3,'text':'y'*800}]
        picks=pick_context({'chunks':chunks},[(0,2.1),(1,1.5)],top_k=2,max_chars=1000)
        self.assertEqual([p['label'] for p in picks],['F1','F2'])
        self.assertLessEqual(sum(len(p['text']) for p in picks),1000)
        messages=prompt_for('Quantos genomas?',picks)
        self.assertIn('[F1]',messages[1]['content'])

    def test_citation_formal(self):
        d=check_citations('Resposta [F1] e [F9].',[{'label':'F1'}])
        self.assertEqual(d['invalid_citations'],['[F9]'])
        self.assertTrue(d['has_citation'])

    def test_rrf_and_cosine(self):
        self.assertEqual(combine_scores([(0,10),(1,8)],[(1,.9),(0,.8)],limit=2)[0][0],0)
        self.assertAlmostEqual(cosine([1,0],[1,0]),1)
        self.assertAlmostEqual(cosine([1,0],[0,1]),0)

    def test_blocks_nonlocal_api(self):
        with self.assertRaises(LMStudioError):validate_base_url('https://api.openai.com/v1')
        with self.assertRaises(LMStudioError):validate_base_url('http://192.168.1.3:1234/v1')
        self.assertEqual(validate_base_url('http://127.0.0.1:1235/v1'),'http://127.0.0.1:1235/v1')

if __name__=='__main__':unittest.main()
