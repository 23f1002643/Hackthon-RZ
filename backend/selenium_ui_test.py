from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

opts = Options()
opts.add_argument('--headless=new')
opts.add_argument('--no-sandbox')
opts.add_argument('--disable-gpu')
opts.add_argument('--window-size=1200,800')

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=opts)

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import json

opts = Options()
opts.add_argument('--headless=new')
opts.add_argument('--no-sandbox')
opts.add_argument('--disable-gpu')
opts.add_argument('--window-size=1200,800')

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=opts)

def read_out(timeout=5):
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.find_element(By.ID, 'out').text is not None
        )
    except Exception:
        pass
    try:
        return driver.find_element(By.ID, 'out').text
    except Exception:
        return ''

def safe_json(s):
    try:
        return json.loads(s)
    except Exception:
        return s

report = {'results': {}, 'assertions': []}
try:
    driver.get('http://127.0.0.1:8000/demo')
    time.sleep(0.5)
    # improved flow: wait for final API response text for each action
    expected_markers = {
        'run': ['"ok"', '"result"', 'order', 'capture'],
        'audit': ['"logs"'],
        'metrics': ['"revenue"', 'order_count', 'upsell_acceptance_rate'],
        'toggle': ['agent_paused']
    }

    for btn_id in ['run', 'audit', 'metrics', 'toggle']:
        success = False
        out = ''
        attempts = 0
        while attempts < 3 and not success:
            attempts += 1
            el = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, btn_id)))
            el.click()
            if btn_id == 'toggle':
                try:
                    alert = WebDriverWait(driver, 3).until(EC.alert_is_present())
                    alert.accept()
                except Exception:
                    pass

            marker_list = expected_markers.get(btn_id, [])
            end_time = time.time() + 8
            while time.time() < end_time:
                out = read_out()
                if any(m in out for m in marker_list):
                    success = True
                    break
                time.sleep(0.4)

        report['results'][btn_id] = out
        parsed = safe_json(out)

        # detailed assertions per button
        if btn_id == 'run':
            ok = isinstance(parsed, dict) and parsed.get('ok') is True and isinstance(parsed.get('result'), dict)
            info = {
                'button': btn_id,
                'ok': bool(ok),
                'attempts': attempts,
                'notes': 'contains ok and result' if ok else 'missing ok/result'
            }
            if ok:
                res = parsed.get('result', {})
                info['order_present'] = 'order' in res
                info['capture_present'] = 'capture' in res
        elif btn_id == 'audit':
            ok = isinstance(parsed, dict) and 'logs' in parsed
            info = {'button': btn_id, 'ok': bool(ok), 'attempts': attempts, 'logs_count': len(parsed.get('logs', [])) if isinstance(parsed, dict) else None}
        elif btn_id == 'metrics':
            ok = isinstance(parsed, dict) and ('revenue' in parsed or 'order_count' in parsed)
            info = {'button': btn_id, 'ok': bool(ok), 'attempts': attempts, 'metrics': parsed if isinstance(parsed, dict) else None}
        elif btn_id == 'toggle':
            ok = isinstance(parsed, dict) and 'agent_paused' in parsed
            info = {'button': btn_id, 'ok': bool(ok), 'attempts': attempts, 'agent_paused': parsed.get('agent_paused') if isinstance(parsed, dict) else None}

        report['assertions'].append(info)
    # write report
    with open('backend/ui_test_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    print('WROTE backend/ui_test_report.json')
finally:
    driver.quit()
