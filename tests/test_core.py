import tempfile
import unittest
from pathlib import Path
from learning_harness import LearningSession, Store

class Model:
    name = 'test'
    def generate(self, context):
        return {'answer': 'A scoped explanation.', 'prerequisites': ['gradient', 'loss'], 'mastered': ['everything']}

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / 'test.sqlite3')
        self.store = Store(self.path)
        self.s = LearningSession.create(self.store, 'Routing', ['A 🧠 router selects experts.'])
        self.block = self.s.state['document']['blocks'][0]
    def tearDown(self):
        self.store.db.close()
        self.tmp.cleanup()
    def annotation(self):
        return self.s.annotate(self.block['id'], 4, 10, 'router', 'How?')
    def test_anchor_and_unicode(self):
        a = self.annotation()
        self.assertEqual(a['anchor']['quote'], 'router')
        with self.assertRaises(ValueError):
            self.s.annotate(self.block['id'], 4, 10, 'wrong', 'How?')
    def test_persistence_and_no_auto_mastery(self):
        a = self.annotation()
        self.s.step(Model(), a['id'])
        loaded = LearningSession.load(self.store, self.s.state['id'])
        self.assertEqual(loaded.state['concepts'][0]['status'], 'exposed')
        self.assertEqual(len(loaded.annotation(a['id'])['thread'][0]['prerequisites']), 1)
        self.assertEqual(loaded.annotation(a['id'])['status'], 'open')
        self.assertEqual(loaded.state['document'], self.s.state['document'])
    def test_navigation_and_resolution_are_independent(self):
        a = self.annotation()
        self.s.push('gradients')
        with self.assertRaises(ValueError): self.s.push('Routing')
        self.s.back()
        self.s.resolve(a['id'])
        self.assertEqual(self.s.state['concepts'][0]['status'], 'unseen')
        self.s.resolve(a['id'], False)
        self.assertEqual(a['status'], 'open')
    def test_failed_generation_is_atomic(self):
        a = self.annotation()
        class Bad:
            name='bad'
            def generate(self, context): return {'answer':'valid', 'prerequisites':None}
        with self.assertRaises(ValueError): self.s.step(Bad(), a['id'], 'follow up')
        self.assertEqual(a['thread'], [])
        self.assertEqual(self.store.load(self.s.state['id'])['annotations'][0]['thread'], [])
    def test_evidence_is_self_reported(self):
        cid = self.s.state['stack'][0]
        self.s.record_understanding(cid, 'I can explain the weighted mixture.')
        self.assertEqual(self.s.concept(cid)['status'], 'self_reported')
        self.assertFalse(self.s.concept(cid)['evidence'][0]['verified'])

if __name__ == '__main__': unittest.main()
