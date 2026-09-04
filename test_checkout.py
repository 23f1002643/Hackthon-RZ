import urllib.request, json, sys

payload={
    "cart":[
        {"name":"Hand-block printed kurta","price":2499,"qty":1},
        {"name":"Chanderi silk dupatta","price":1299,"qty":1}
    ],
    "customer":{"name":"Sim Buyer","email":"sim@zephyr.com","contact":"9999999999"}
}

data=json.dumps(payload).encode()
req=urllib.request.Request('http://127.0.0.1:8000/api/checkout', data=data, headers={'Content-Type':'application/json'})
try:
    res=urllib.request.urlopen(req, timeout=30)
    body=res.read().decode()
    print(body)
except Exception as e:
    try:
        # Try to print HTTP error body if available
        import urllib.error
        if isinstance(e, urllib.error.HTTPError):
            print(e.read().decode())
            sys.exit(1)
    except Exception:
        pass
    print('ERROR', e)
    sys.exit(1)
