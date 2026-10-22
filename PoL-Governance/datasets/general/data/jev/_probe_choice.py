import sys, json, time, urllib.request, urllib.error
sys.path.insert(0, 'datasets/general')
import jev_fill as J

cfg = J.load_jev_config()
url = J.DEFAULT_DECISIONS_URL
KEY = 'q'
state = 'A user asks: what is 2 plus 2? The assistant must answer.'
instructions = 'Which option is the correct answer to the user question?'

variants = {
    'A_options_dict': {'type': 'choice', 'instructions': instructions,
                       'options': {'three': 'the number three', 'four': 'the number four'}},
    'B_criteria_dict': {'type': 'choice', 'instructions': instructions,
                        'criteria': {'three': 'the answer equals three', 'four': 'the answer equals four'}},
    'C_options_list': {'type': 'choice', 'instructions': instructions, 'options': ['three', 'four']},
    'D_criteria_list': {'type': 'choice', 'instructions': instructions,
                        'criteria': ['the answer equals three', 'the answer equals four']},
    'E_box': {'type': 'box', 'instructions': instructions,
              'criteria': {'three': 'the answer equals three', 'four': 'the answer equals four'}},
}
for name, spec in variants.items():
    body = {'model': J.MERCURY_MODEL, 'state': state, 'questions': {KEY: spec}}
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json', 'Accept': 'application/json',
                                          'Authorization': 'Bearer ' + cfg['apikey'], 'User-Agent': J.USER_AGENT},
                                 method='POST')
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            print(name, '->', resp.status, resp.read(700).decode('utf-8', 'replace'))
    except urllib.error.HTTPError as e:
        print(name, '-> HTTP', e.code, e.read(300).decode('utf-8', 'replace'))
    time.sleep(1.5)
