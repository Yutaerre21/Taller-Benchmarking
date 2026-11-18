"""Prueba funcional contra la API levantada; crea un pedido de ejemplo."""
import json
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

root = Path(__file__).resolve().parent.parent
body = (root / 'examples/order.json').read_bytes()
request = urllib.request.Request('http://localhost:5001/api/orders', data=body,
                                 headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(request, timeout=15) as response:
    assert response.status == 201
    result = json.load(response)
assert result['totalAmount'] == 26 and result['itemsCount'] == 3
assert len(result['orderId']) == 32 and result['processedAt'].endswith('Z')
order_id = result['orderId']
assert all(c in '0123456789abcdef' for c in order_id)
sql = f"SELECT o.total_amount,o.items_count,count(i.id),sum(i.quantity*i.price) FROM orders o JOIN order_items i USING(order_id) WHERE o.order_id='{order_id}' GROUP BY o.total_amount,o.items_count;"
db = subprocess.check_output(['docker','compose','exec','-T','db','psql','-U','postgres','-d','orders_db','-At','-c',sql], cwd=root, text=True).strip()
assert db == '26.00|3|2|26.00', db
for bad in [b'{}', b'{', b'{"customerId":"C","items":[]}']:
    try:
        urllib.request.urlopen(urllib.request.Request('http://localhost:5001/api/orders', data=bad, headers={'Content-Type':'application/json'}))
        raise AssertionError('La entrada incorrecta fue aceptada')
    except urllib.error.HTTPError as e:
        assert e.code == 400, e.code
print(json.dumps({'functional_check':'PASS','response':result,'database':db}, indent=2))
