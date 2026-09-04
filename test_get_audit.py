import urllib.request, json, sys

req=urllib.request.Request('http://127.0.0.1:8000/api/audit-log')
try:
    res=urllib.request.urlopen(req, timeout=10)
    print(res.read().decode())
except Exception as e:
    print('ERROR', e)
    sys.exit(1)
