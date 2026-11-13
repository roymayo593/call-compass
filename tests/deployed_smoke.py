"""Run explicitly against a deployed demo. Uses synthetic data only."""
import json
import secrets
import sys
import uuid
from urllib.request import Request,urlopen
from urllib.error import HTTPError
base=sys.argv[1].rstrip('/')
token=secrets.token_hex(32)
def req(path,method='GET',data=None,override=None):
 r=Request(base+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json','Authorization':'Bearer '+(override or token)},method=method)
 try:
  with urlopen(r,timeout=60) as x:return x.status,json.load(x)
 except HTTPError as x:
  body=x.read()
  try:return x.code,json.loads(body)
  except ValueError:return x.code,{'error':'Non-JSON response from hosting platform'}
status,health=req('/health');assert status==200,(status,health)
print('Health:',json.dumps(health))
cid=str(uuid.uuid4());data={'id':cid,'prospect':'Deployment verification — sample only','company':'Synthetic Manufacturing'}
status,c=req('/calls','POST',data);assert status==201,(status,c)
original_start=c['started_at'];assert req('/calls','POST',data)[1]['started_at']==original_start
for n in range(1,9):
 status,c=req('/calls/'+cid+'/stages','PUT',{'stage':n,'result':'Sample result '+str(n),'words':'We need a new product line. अभी cost is a concern.' if n==5 else ''})
 assert status==200,(status,c)
assert len(c['call_stages'])==8
assert req('/calls/'+cid,override=secrets.token_hex(32))[0]==404
status,c=req('/calls/'+cid+'/close','POST',{'stage':8,'outcome':'send_information','next_step':'Send sample information by email. No meeting or date agreed.'})
assert status==200 and c['reached_stage']==8 and c['outcome']=='send_information',(status,c)
status,c=req('/calls/'+cid);assert status==200 and len(c['call_stages'])==8
status,summary=req('/calls/'+cid+'/summary','POST',{})
print('Persisted all 8 stages, retry-safe start, workspace isolation, finished call: PASS')
print('Gemini status:',status)
print('Gemini result:',json.dumps(summary,ensure_ascii=False))
if status!=200:sys.exit(2)
assert summary.get('summary')
