import json

def format_dict(dict_string):
    try:
        return json.loads(dict_string)
    except:
        return {}
