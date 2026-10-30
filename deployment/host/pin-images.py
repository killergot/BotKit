import json, subprocess, sys
from pathlib import Path
p=Path(sys.argv[1]); data=json.loads(p.read_text())
data['services'].pop('migrate',None)
for service in data['services'].values():
 info=json.loads(subprocess.check_output(['docker','inspect',service['container_name']]))[0]
 service['image']=info['Image']; service.pop('build',None)
p.write_text(json.dumps(data)); p.chmod(0o600)
