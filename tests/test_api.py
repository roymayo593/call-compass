import json
import os
import sys
import threading
import unittest
import uuid
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
os.environ['STORAGE']='sqlite'
os.environ['SQLITE_PATH']=':memory:'
import server

class APITest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
  threading.Thread(target=cls.http.serve_forever,daemon=True).start()
  cls.url='http://127.0.0.1:'+str(cls.http.server_port)
 @classmethod
 def tearDownClass(cls):
  cls.http.shutdown();cls.http.server_close()
 def setUp(self):
  self.token=uuid.uuid4().hex+uuid.uuid4().hex
 def req(self,path,method='GET',data=None,token=None,origin=None):
  headers={'Authorization':'Bearer '+(token or self.token),'Content-Type':'application/json'}
  if origin:headers['Origin']=origin
  req=Request(self.url+path,data=json.dumps(data).encode() if data is not None else None,headers=headers,method=method)
  try:
   with urlopen(req) as r:return r.status,json.load(r)
  except HTTPError as r:return r.code,json.load(r)
 def start(self):
  data={'id':str(uuid.uuid4()),'prospect':'Test caller','company':'Sample company'}
  status,c=self.req('/calls','POST',data);self.assertEqual(status,201);self.assertNotIn('owner_hash',c)
  return data,c
 def test_all_stages_exact_words_and_retry(self):
  data,c=self.start();cid=c['id']
  self.assertEqual(self.req('/calls','POST',data)[1]['started_at'],c['started_at'])
  words='  नई product line चाहिए — not margins.\nKeep exact words.  '
  for n in range(1,9):
   s,c=self.req('/calls/'+cid+'/stages','PUT',{'stage':n,'result':'Recorded','words':words if n==5 else ''})
   self.assertEqual(s,200)
  self.assertEqual(len(c['call_stages']),8)
  self.assertEqual(next(s['words'] for s in c['call_stages'] if s['stage']==5),words)
  self.req('/calls/'+cid+'/stages','PUT',{'stage':5,'result':'Corrected','words':words})
  self.assertEqual(len(self.req('/calls/'+cid)[1]['call_stages']),8)
  status,c=self.req('/calls/'+cid+'/close','POST',{'stage':8,'outcome':'send_information','next_step':'Send overview by email; no meeting agreed.'})
  self.assertEqual(status,200);self.assertEqual(c['reached_stage'],8)
  first=c['ended_at'];self.assertEqual(self.req('/calls/'+cid+'/close','POST',{'stage':8,'outcome':'meeting','next_step':'Changed'})[1]['ended_at'],first)
  self.assertEqual(self.req('/calls/'+cid+'/stages','PUT',{'stage':1,'result':'Edited','words':''})[0],409)
 def test_workspace_isolation(self):
  _,c=self.start();other='f'*64
  self.assertEqual(self.req('/calls/'+c['id'],token=other)[0],404)
  self.assertFalse(any(x['id']==c['id'] for x in self.req('/calls',token=other)[1]['calls']))
  self.assertEqual(self.req('/calls/'+c['id']+'/stages','PUT',{'stage':1,'result':'x'},token=other)[0],404)
 def test_early_exit_without_fabricated_stages(self):
  _,c=self.start();s,c=self.req('/calls/'+c['id']+'/close','POST',{'stage':1,'outcome':'wrong_person','next_step':''})
  self.assertEqual(s,200);self.assertEqual(c['reached_stage'],1);self.assertEqual(c['call_stages'],[])
 def test_validation_and_required_followup(self):
  _,c=self.start();cid=c['id']
  for n in [0,9,True,'1']:
   self.assertEqual(self.req('/calls/'+cid+'/stages','PUT',{'stage':n,'result':'x'})[0],400)
  self.assertEqual(self.req('/calls/'+cid+'/stages','PUT',{'stage':1,'result':'x','words':'x'*4001})[0],400)
  self.assertEqual(self.req('/calls/'+cid+'/close','POST',{'stage':3,'outcome':'meeting','next_step':''})[0],400)
  self.assertEqual(self.req('/calls','POST',{'id':'bad','prospect':'x'})[0],400)
 def test_no_ai_does_not_lose_call(self):
  _,c=self.start();cid=c['id'];self.req('/calls/'+cid+'/close','POST',{'stage':2,'outcome':'not_interested'})
  old=os.environ.pop('GEMINI_API_KEY',None)
  try:self.assertEqual(self.req('/calls/'+cid+'/summary','POST',{})[0],503)
  finally:
   if old:os.environ['GEMINI_API_KEY']=old
  self.assertEqual(self.req('/calls/'+cid)[1]['outcome'],'not_interested')
 def test_cors_and_auth(self):
  self.assertEqual(self.req('/calls',token='bad')[0],401)
  self.assertEqual(self.req('/calls',origin='https://untrusted.example')[0],403)
  self.assertEqual(self.req('/health')[1]['database'],'connected')

if __name__=='__main__':unittest.main()
