import copy
import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import pipeline
import server

class Contracts(unittest.TestCase):
    def report(self):return {'schema_version':'e11e12-1','kind':'incremental-check','commit':'a'*40,'status':'SUCCEEDED'}
    def test_accept_current_report(self):pipeline.check_envelope(self.report(),'a'*40,'incremental-check')
    def test_reject_old_commit(self):
        with self.assertRaisesRegex(pipeline.Failure,'another commit'):pipeline.check_envelope(self.report(),'b'*40)
    def test_reject_schema(self):
        r=self.report();r['schema_version']='old'
        with self.assertRaises(pipeline.Failure):pipeline.check_envelope(r,'a'*40)
    def test_reject_failed_upstream(self):
        r=self.report();r['status']='FAILED'
        with self.assertRaises(pipeline.Failure):pipeline.check_envelope(r,'a'*40)
    def test_reject_wrong_artifact_kind(self):
        with self.assertRaises(pipeline.Failure):pipeline.check_envelope(self.report(),'a'*40,'fixed-md')
    def test_artifact_uses_relative_uri_and_content_hash(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'x.json';p.write_text('{}')
            a=pipeline.artifact(p,root,'job-1');self.assertEqual(a['uri'],'artifact://job-1/x.json');self.assertEqual(len(a['sha256']),64)
    def test_existing_evidence_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'keep').write_text('keep')
            with self.assertRaises(pipeline.Failure):pipeline.execute({},root)
            self.assertEqual((root/'keep').read_text(),'keep')
    def test_changed_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'r.json';p.write_text('{}')
            with self.assertRaises(pipeline.Failure):pipeline.load_artifact(p,'0'*64)
    def test_same_key_same_request_same_job(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);store=server.Store(root/'jobs')
            request={'mode':'e11-a','repo':str(pipeline.ROOT/'data/p'),'base':'a','target':'b'}
            with patch.object(store.pool,'submit'):
                one=store.submit(request,'same');two=store.submit(request,'same')
                self.assertEqual(one['job_id'],two['job_id'])
                changed=dict(request,target='c')
                with self.assertRaisesRegex(ValueError,'IDEMPOTENCY_CONFLICT'):store.submit(changed,'same')
            store.pool.shutdown()
    def test_api_rejects_repo_outside_data(self):
        with tempfile.TemporaryDirectory() as d:
            store=server.Store(Path(d)/'jobs')
            with self.assertRaises(ValueError):store.submit({'mode':'e11-a','repo':str(Path(d)),'base':'a','target':'b'},'k')
            store.pool.shutdown()

class Student241880180E12Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name);data=root/'data';repo=data/'repo';repo.mkdir(parents=True)
        self.evidence=pipeline.ROOT/'work/241880180-e12-idempotency-conflict'
        if self.evidence.exists():shutil.rmtree(self.evidence)
        self.evidence.mkdir(parents=True)
        self.httpd=server.make_server('127.0.0.1',0,root=root/'jobs',data_root=data,executor=self.complete)
        self.thread=threading.Thread(target=self.httpd.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.httpd.server_port}/v1/jobs'
        self.repo=repo
        self.addCleanup(self.stop_server)

    def complete(self, request, out, job_id):
        return {'status':'SUCCEEDED','trace_id':'trace-contract'}

    def stop_server(self):
        self.httpd.shutdown();self.httpd.server_close();self.thread.join()
        self.httpd.store.pool.shutdown()

    def post(self, name, payload):
        (self.evidence/f'{name}-request.json').write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
        request=Request(self.url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
        try:
            with urlopen(request,timeout=5) as response:
                status=response.status;body=json.loads(response.read())
        except HTTPError as error:
            status=error.code;body=json.loads(error.read())
        (self.evidence/f'{name}-response.json').write_text(json.dumps({'status':status,'body':body},indent=2)+'\n',encoding='utf-8')
        return status,body

    def test_same_key_different_target_returns_idempotency_conflict(self):
        key='student-241880180-e12-conflict'
        first={'idempotency_key':key,'input':{'mode':'e11-a','repo':str(self.repo),'base':'a'*40,'target':'b'*40}}
        conflict={'idempotency_key':key,'input':dict(first['input'],target='c'*40)}
        first_status,first_body=self.post('first',first)
        conflict_status,conflict_body=self.post('conflict',conflict)
        (self.evidence/'test.log').write_text(
            f'first_status={first_status}\njob_id={first_body.get("job_id")}\n'
            f'conflict_status={conflict_status}\nerror={conflict_body.get("error")}\n',encoding='utf-8')
        self.assertEqual(first_status,202)
        self.assertIn(first_body['status'],('QUEUED','RUNNING','SUCCEEDED'))
        self.assertEqual(conflict_status,409)
        self.assertEqual(conflict_body,{'error':'IDEMPOTENCY_CONFLICT'})
        self.assertEqual(len(self.httpd.store.jobs),1)

if __name__=='__main__':unittest.main()
