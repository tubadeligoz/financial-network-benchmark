"""Audit only Git-visible publication candidates; never print matching secret values."""
import json,re,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]
raw=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=root)
files=sorted(x.decode() for x in raw.split(b'\0') if x)
patterns={'private_key':r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----','github_token':r'gh[pousr]_[A-Za-z0-9]{30,}','aws_access_key':r'AKIA[0-9A-Z]{16}'}
findings=[]
for name in files:
 p=root/name
 if p.suffix.lower() in ('.png','.jpg','.zip'):continue
 try:text=p.read_text(encoding='utf-8-sig')
 except UnicodeError:continue
 for kind,pattern in patterns.items():
  for m in re.finditer(pattern,text):findings.append({'file':name,'line':text.count('\n',0,m.start())+1,'kind':kind})
for name in ('datasets','graph-explorer','benchmarks','results'):
 assert (root/f'docs/screenshots/{name}.png').read_bytes().startswith(b'\x89PNG')
assert not any(f.startswith(('data/raw/','data/processed/','experiments/','.venv/','frontend/node_modules/')) for f in files)
(root/'docs/publication-files.txt').write_text('\n'.join(files)+'\n',encoding='utf-8')
report={'candidate_count':len(files),'credential_pattern_findings':findings,'limitations':'Pattern scan, not an exhaustive security audit; publication state is recorded separately in publication-review.md.','screenshots_png_valid':True}
(root/'docs/publication-audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
objects=subprocess.check_output(['git','cat-file','--batch-all-objects','--batch-check=%(objectname) %(objecttype)'],cwd=root).decode().splitlines()
blob_findings=[]
for line in objects:
 sha,kind=line.split()
 if kind!='blob':continue
 text=subprocess.check_output(['git','cat-file','blob',sha],cwd=root).decode('utf-8',errors='ignore')
 for label,pattern in patterns.items():
  if re.search(pattern,text):blob_findings.append({'object':sha,'kind':label})
report['git_object_count']=len(objects);report['git_object_credential_findings']=blob_findings
(root/'docs/publication-audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('Git objects inspected:',len(objects),'credential pattern findings:',len(blob_findings))
