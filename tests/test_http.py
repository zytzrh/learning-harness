import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from learning_harness import Store, CompatibleModel
from learning_harness.models import DemoModel
from learning_harness.server import make_handler

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = Store(':memory:')
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), BaseHTTPRequestHandler)
        cls.port = cls.server.server_port
        cls.server.RequestHandlerClass = make_handler(cls.store, DemoModel(), cls.port)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.port}'
        with urllib.request.urlopen(cls.base + '/api/bootstrap') as r:
            cls.token = json.load(r)['token']
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.store.db.close()
    def post(self, path, data, origin=None, token=None):
        req = urllib.request.Request(self.base + '/api/' + path, data=json.dumps(data).encode(), headers={'Content-Type':'application/json', 'Origin':origin or self.base, 'X-Learning-Token':self.token if token is None else token})
        with urllib.request.urlopen(req) as r: return json.load(r)
    def test_complete_learning_flow(self):
        s = self.post('create', {'demo':True})
        b = s['document']['blocks'][0]
        s = self.post('annotate', {'session_id':s['id'], 'block_id':b['id'], 'start':0, 'end':3, 'quote':b['text'][:3], 'question':'Why?'})
        aid = s['annotations'][0]['id']
        s = self.post('ask', {'session_id':s['id'], 'annotation_id':aid})
        self.assertTrue(s['annotations'][0]['thread'])
        s = self.post('push', {'session_id':s['id'], 'name':'gradient'})
        self.assertEqual(len(s['stack']), 2)
        s = self.post('back', {'session_id':s['id']})
        s = self.post('resolve', {'session_id':s['id'], 'annotation_id':aid})
        with urllib.request.urlopen(self.base+'/api/session?id='+s['id']) as r:
            loaded=json.load(r)
        self.assertEqual(loaded['annotations'][0]['status'], 'resolved')
        self.assertEqual(loaded['concepts'][0]['status'], 'exposed')
    def test_cross_origin_and_missing_token_rejected(self):
        for kwargs in [{'origin':'https://example.com'}, {'token':''}]:
            with self.assertRaises(urllib.error.HTTPError) as e:
                self.post('create', {'demo':True}, **kwargs)
            self.assertEqual(e.exception.code, 403)
    def test_static_assets_and_csp(self):
        for path in ['/', '/app.js', '/style.css']:
            with urllib.request.urlopen(self.base+path) as r:
                self.assertEqual(r.status, 200)
                self.assertIn("frame-ancestors 'none'", r.headers['Content-Security-Policy'])
                self.assertGreater(len(r.read()), 100)
    def test_adapter_uses_real_http_contract(self):
        captured = {}
        class Provider(BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def do_POST(self):
                captured['path'] = self.path
                captured['body'] = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                payload = json.dumps({'choices':[{'message':{'content':json.dumps({'answer':'mock model response', 'prerequisites':[]})}}]}).encode()
                self.send_response(200); self.end_headers(); self.wfile.write(payload)
        provider = ThreadingHTTPServer(('127.0.0.1',0), Provider)
        threading.Thread(target=provider.serve_forever, daemon=True).start()
        try:
            model = CompatibleModel(model='test-model', base_url=f'http://127.0.0.1:{provider.server_port}/v1', api_key='')
            result = model.generate({'goal':'test'})
            self.assertEqual(result['answer'], 'mock model response')
            self.assertEqual(captured['path'], '/v1/chat/completions')
            self.assertEqual(captured['body']['model'], 'test-model')
        finally:
            provider.shutdown(); provider.server_close()
