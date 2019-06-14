def dict_compare(dict1, dict2):
    dict1_keys = set(dict1.keys())
    dict2_keys = set(dict2.keys())
    intersection = dict1_keys.difference(dict2_keys)
    if len(intersection) > 0:
        return (False, list(intersection))

    flag_no_error = True
    faulties = []
    for k, v in dict1.items():
        if (isinstance(v, dict)):
            status, faulty = dict_compare(v, dict2[k])
            flag_no_error = flag_no_error and status
            faulties.append(faulty)
        else:
            (True, [])
    if flag_no_error:
        return (True, [])
    else:
        return (False, faulties)
