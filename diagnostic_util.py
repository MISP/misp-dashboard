import configparser


def dict_compare(dict1, dict2, itercount=0):
    dict1_keys = set(dict1.keys())
    dict2_keys = set(dict2.keys())
    intersection = dict1_keys.difference(dict2_keys)
    faulties = []
    if itercount > 0 and len(intersection) > 0:
        return (False, list(intersection))

    flag_no_error = True
    for k, v in dict1.items():
        if isinstance(v, dict):
            if k not in dict2:
                faulties.append({k: dict1[k]})
                flag_no_error = False
            else:
                status, faulty = dict_compare(v, dict2[k], itercount+1)
                flag_no_error = flag_no_error and status
                if len(faulty) > 0:
                    faulties.append({k: faulty})
        else:
            return (True, [])
    if flag_no_error:
        return (True, [])
    else:
        return (False, faulties)


class TimeoutException(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeoutException


# https://stackoverflow.com/a/10464730
class Monitor():
    def __init__(self, connection_pool):
        self.connection_pool = connection_pool
        self.connection = None

    def __del__(self):
        try:
            self.reset()
        except Exception:
            pass

    def reset(self):
        if self.connection:
            self.connection_pool.release(self.connection)
            self.connection = None

    def monitor(self):
        if self.connection is None:
            self.connection = self.connection_pool.get_connection(
                'monitor', None)
        self.connection.send_command("monitor")
        return self.listen()

    def parse_response(self):
        return self.connection.read_response()

    def listen(self):
        while True:
            yield self.parse_response()
