import importlib.util
import json
from pathlib import Path
import unittest

SCRIPT = Path(__file__).parents[1] / 'skills/learning-harness/scripts/build_workspace.py'
spec = importlib.util.spec_from_file_location('build_workspace', SCRIPT)
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)

class WorkspaceTests(unittest.TestCase):
    def test_embedded_content_cannot_close_script(self):
        payload = {'goal':'Test', 'paragraphs':['</script><script>alert(1)</script> __CLIENT__']}
        page,state = renderer.build(payload)
        self.assertNotIn('</script><script>alert(1)', page)
        data = page.split('id="lesson-state">',1)[1].split('</script>',1)[0]
        self.assertEqual(json.loads(data),state)
        self.assertIn('__CLIENT__',state['blocks'][0]['text'])
        self.assertEqual(state['schema_version'],2)
    def test_rebuild_preserves_ids_and_annotations(self):
        _,state=renderer.build({'goal':'Test','paragraphs':['Text']})
        _,restored=renderer.build(state)
        self.assertEqual(state,restored)
    def test_invalid_seed_rejected(self):
        for payload in [{'goal':'','paragraphs':['x']},{'goal':'test','paragraphs':[]},{'goal':'test','paragraphs':[None]}]:
            with self.assertRaises(ValueError):renderer.build(payload)
