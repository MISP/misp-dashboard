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
