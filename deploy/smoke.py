"""Test isolated fixture data; never package the test database."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import db
with tempfile.TemporaryDirectory() as folder:
    database = Path(folder) / 'fixture.db'
    c = db.connect(database)
    db.init_db(c)
    c.execute("INSERT INTO manufacturers(id,name) VALUES (1,'Fixture')")
    c.execute("INSERT INTO products(id,manufacturer_id,name) VALUES ('p',1,'Product')")
    c.commit()
    c.close()
    env = dict(os.environ, MASTER_CATALOG_DB=str(database), MASTER_CATALOG_PORT='28766', MASTER_CATALOG_NO_BROWSER='1')
    p = subprocess.Popen([sys.executable, 'serve.py'], env=env)
    try:
        for _ in range(50):
            try:
                result = json.load(urllib.request.urlopen('http://127.0.0.1:28766/api/stats'))
                break
            except urllib.error.URLError:
                time.sleep(.1)
        else:
            raise AssertionError('Server did not start')
        assert result['products'] == 1
        for route in ('/', '/master_catalog.html', '/house.html', '/manufacturers.html', '/api/products?q=Product'):
            assert urllib.request.urlopen('http://127.0.0.1:28766'+route).status == 200
        for route in ('/db.py', '/aareas.db', '/.git/config', '/%2e%2e/db.py'):
            try:
                urllib.request.urlopen('http://127.0.0.1:28766'+route)
            except urllib.error.HTTPError as e:
                assert e.code == 404
            else:
                raise AssertionError('Private path exposed: '+route)
    finally:
        p.terminate()
        p.wait(timeout=10)
print('Smoke tests passed')
