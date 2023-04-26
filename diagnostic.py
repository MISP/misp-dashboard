#!/usr/bin/env python3
import os
import sys
import stat
import time
import signal
import functools
import configparser
from urllib.parse import urlparse, parse_qs
import subprocess
import diagnostic_util
try:
    import redis
    import zmq
    import json
    import flask
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    from halo import Halo
except ModuleNotFoundError as e:
    print('Dependency not met. Either not in a virtualenv or dependency not installed.')
    print('- Error: {}'.format(e))
    sys.exit(1)

'''
Steps:
- check if dependencies exists
- check if virtualenv exists
- check if configuration is update-to-date
 - check file permission
 - check if redis is running and responding
 - check if able to connect to zmq
 - check zmq_dispatcher processing queue
    - check queue status: being filled up / being filled down
- check if subscriber responding
- check if dispatcher responding
- check if server listening
- check log static endpoint
- check log dynamic endpoint
'''

HOST = 'http://127.0.0.1'
PORT = 8001  # overriden by configuration file
configuration_file = {}
pgrep_subscriber_output = ''
pgrep_dispatcher_output = ''


signal.signal(signal.SIGALRM, diagnostic_util.timeout_handler)


def humanize(name, isResult=False):
    words = name.split('_')
    if isResult:
        words = words[1:]
        words[0] = words[0][0].upper() + words[0][1:]
    else:
        words[0] = words[0][0].upper() + words[0][1:] + 'ing'
    return ' '.join(words)


def add_spinner(_func=None, name='dots'):
    def decorator_add_spinner(func):
        @functools.wraps(func)
        def wrapper_add_spinner(*args, **kwargs):
            human_func_name = humanize(func.__name__)
            human_func_result = humanize(func.__name__, isResult=True)
            flag_skip = False

            with Halo(text=human_func_name, spinner=name) as spinner:
                result = func(spinner, *args, **kwargs)
                if isinstance(result, tuple):
                    status, output = result
                elif isinstance(result, list):
                    status = result[0]
                    output = result[1]
                elif isinstance(result, bool):
                    status = result
                    output = None
                else:
                    status = False
                    flag_skip = True
                    spinner.fail('{} -  Function return unexpected result: {}'.format(human_func_name, str(result)))

                if not flag_skip:
                    text = human_func_result
                    if output is not None and len(output) > 0:
                        text += ': {}'.format(output)

                    if isinstance(status, bool) and status:
                        spinner.succeed(text)
                    elif isinstance(status, bool) and not status:
                        spinner.fail(text)
                    else:
                        if status == 'info':
                            spinner.info(text)
                        else:
                            spinner.warn(text)
                return status
        return wrapper_add_spinner

    if _func is None:
        return decorator_add_spinner
    else:
        return decorator_add_spinner(_func)


@add_spinner
def check_virtual_environment_and_packages(spinner):
    result = os.environ.get('VIRTUAL_ENV')
    if result is None:
        return (False, 'This diagnostic tool should be started inside a virtual environment.')
    else:
        if redis.__version__.startswith('2'):
            return (False, '''Redis python client have version {}. Version 3.x required.
\t➥ [inside virtualenv] pip3 install -U redis'''.format(redis.__version__))
        else:
            return (True, '')


@add_spinner
def check_configuration(spinner):
    global configuration_file, port
    configfile = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config/config.cfg')
    cfg = configparser.ConfigParser()
    cfg.read(configfile)
    configuration_file = cfg
    cfg = {s: dict(cfg.items(s)) for s in cfg.sections()}
    configfile_default = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config/config.cfg.default')
    cfg_default = configparser.ConfigParser()
    cfg_default.read(configfile_default)
    cfg_default = {s: dict(cfg_default.items(s)) for s in cfg_default.sections()}

    # Check if all fields from config.default exists in config
    result, faulties = diagnostic_util.dict_compare(cfg_default, cfg)
    if result:
        port = configuration_file.get("Server", "port")
        return (True, '')
    else:
        return_text = '''Configuration incomplete.
\tUpdate your configuration file `config.cfg`.\n\t➥ Faulty fields:\n'''
        for field_name in faulties:
            return_text += '\t\t- {}\n'.format(field_name)
        return (False, return_text)


@add_spinner(name='dot')
def check_file_permission(spinner):
    max_mind_database_path = configuration_file.get('RedisMap', 'pathmaxminddb')
    try:
        st = os.stat(max_mind_database_path)
    except FileNotFoundError:
        return (False, 'Maxmind GeoDB - File not found')

    all_read_perm = bool(st.st_mode & stat.S_IROTH)  # FIXME: permission may be changed
    if all_read_perm:
        return (True, '')
    else:
        return (False, 'Maxmind GeoDB might have incorrect read file permission')


@add_spinner
def check_redis(spinner):
    redis_server = redis.StrictRedis(
        host=configuration_file.get('RedisGlobal', 'host'),
        port=configuration_file.getint('RedisGlobal', 'port'),
        db=configuration_file.getint('RedisLog', 'db'))
    if redis_server.ping():
        return (True, '')
    else:
        return (False, '''Can\'t reach Redis server.
\t➥ Make sure it is running and adapt your configuration accordingly''')


@add_spinner
def check_zmq(spinner):
    timeout = 15
    context = zmq.Context()
    misp_instances = json.loads(configuration_file.get('RedisGlobal', 'misp_instances'))
    instances_status = {}
    for misp_instance in misp_instances:
        socket = context.socket(zmq.SUB)
        socket.connect(misp_instance.get('zmq'))
        socket.setsockopt_string(zmq.SUBSCRIBE, '')
        poller = zmq.Poller()

        flag_skip = False
        start_time = time.time()
        poller.register(socket, zmq.POLLIN)
        for t in range(1, timeout+1):
            socks = dict(poller.poll(timeout=1*1000))
            if len(socks) > 0:
                if socket in socks and socks[socket] == zmq.POLLIN:
                    rcv_string = socket.recv()
                    if rcv_string.startswith(b'misp_json'):
                        instances_status[misp_instance.get('name')] = True
                        flag_skip = True
                        break
            else:
                spinner.text = 'checking zmq of {} - elapsed time: {}s'.format(misp_instance.get("name"), int(time.time() - start_time))
        if not flag_skip:
            instances_status[misp_instance.get('name')] = False

    results = [s for n, s in instances_status.items()]
    if all(results):
        return (True, '')
    elif any(results):
        return_text = 'Connection to ZMQ stream(s) failed.\n'
        for name, status in instances_status.items():
            return_text += '\t➥ {}: {}\n'.format(name, "success" if status else "failed")
        return (True, return_text)
    else:
        return (False, '''Can\'t connect to the ZMQ stream(s).
\t➥ Make sure the MISP ZMQ is running: `/servers/serverSettings/diagnostics`
\t➥ Make sure your network infrastucture allows you to connect to the ZMQ''')


@add_spinner
def check_processes_status(spinner):
    global pgrep_subscriber_output, pgrep_dispatcher_output
    try:
        response = subprocess.check_output(
            ["pgrep", "-laf", "zmq_"],
            universal_newlines=True
        )
    except subprocess.CalledProcessError as e:
        return (False, 'Could not get processes status. Error returned:\n'+str(e))

    for line in response.splitlines():
        lines = line.split(' ', maxsplit=1)
        pid, p_name = lines

        if 'zmq_subscriber.py' in p_name:
            pgrep_subscriber_output = line
        elif 'zmq_dispatcher.py' in p_name:
            pgrep_dispatcher_output = line

    if len(pgrep_subscriber_output) == 0:
        return (False, 'zmq_subscriber is not running')
    elif len(pgrep_dispatcher_output) == 0:
        return (False, 'zmq_dispatcher is not running')
    else:
        return (True, 'Both processes are running')


@add_spinner
def check_subscriber_status(spinner):
    global pgrep_subscriber_output
    pool = redis.ConnectionPool(
        host=configuration_file.get('RedisGlobal', 'host'),
        port=configuration_file.getint('RedisGlobal', 'port'),
        db=configuration_file.getint('RedisLIST', 'db'),
        decode_responses=True)
    monitor = diagnostic_util.Monitor(pool)
    commands = monitor.monitor()

    start_time = time.time()
    signal.alarm(15)
    try:
        for i, c in enumerate(commands):
            if i == 0:  # Skip 'OK'
                continue
            split = c.split()
            try:
                action = split[3]
                target = split[4]
            except IndexError:
                pass
            if action == '"LPUSH"' and target == '\"{}\"'.format(configuration_file.get("RedisLIST", "listName")):
                signal.alarm(0)
                break
            else:
                spinner.text = 'Checking subscriber status - elapsed time: {}s'.format(int(time.time() - start_time))
    except diagnostic_util.TimeoutException:
        return_text = '''zmq_subscriber seems not to be working.
\t➥ Consider restarting it: {}'''.format(pgrep_subscriber_output)
        return (False, return_text)
    return (True, 'subscriber is running and populating the buffer')


@add_spinner
def check_buffer_queue(spinner):
    redis_server = redis.StrictRedis(
            host=configuration_file.get('RedisGlobal', 'host'),
            port=configuration_file.getint('RedisGlobal', 'port'),
            db=configuration_file.getint('RedisLIST', 'db'))
    warning_threshold = 100
    elements_in_list = redis_server.llen(configuration_file.get('RedisLIST', 'listName'))
    return_status = 'warning' if elements_in_list > warning_threshold else ('info' if elements_in_list > 0 else True)
    return_text = 'Currently {} items in the buffer'.format(elements_in_list)
    return (return_status, return_text)


@add_spinner
def check_buffer_change_rate(spinner):
    redis_server = redis.StrictRedis(
        host=configuration_file.get('RedisGlobal', 'host'),
        port=configuration_file.getint('RedisGlobal', 'port'),
        db=configuration_file.getint('RedisLIST', 'db'))

    time_slept = 0
    sleep_duration = 0.001
    sleep_max = 10.0
    refresh_frequency = 1.0
    next_refresh = 0
    change_increase = 0
    change_decrease = 0
    elements_in_list_prev = 0
    elements_in_list = int(redis_server.llen(configuration_file.get('RedisLIST', 'listName')))
    elements_in_inlist_init = elements_in_list
    consecutive_no_rate_change = 0
    while True:
        elements_in_list_prev = elements_in_list
        elements_in_list = int(redis_server.llen(configuration_file.get('RedisLIST', 'listName')))
        change_increase += elements_in_list - elements_in_list_prev if elements_in_list - elements_in_list_prev > 0 else 0
        change_decrease += elements_in_list_prev - elements_in_list if elements_in_list_prev - elements_in_list > 0 else 0

        if next_refresh < time_slept:
            next_refresh = time_slept + refresh_frequency
            change_rate_text = '↑ {}/sec\t↓ {}/sec'.format(change_increase, change_decrease)
            spinner.text = 'Buffer: {}\t{}'.format(elements_in_list, change_rate_text)

            if consecutive_no_rate_change == 3:
                time_slept = sleep_max
            if elements_in_list == 0:
                consecutive_no_rate_change += 1
            else:
                consecutive_no_rate_change = 0
            change_increase = 0
            change_decrease = 0

        if time_slept >= sleep_max:
            return_flag = elements_in_list == 0 or (elements_in_list < elements_in_inlist_init or elements_in_list < 2)
            return_text = 'Buffer is consumed {} than being populated'.format("faster" if return_flag else "slower")
            break

        time.sleep(sleep_duration)
        time_slept += sleep_duration
    elements_in_inlist_final = int(redis_server.llen(configuration_file.get('RedisLIST', 'listName')))
    return (return_flag, return_text)


@add_spinner
def check_dispatcher_status(spinner):
    redis_server = redis.StrictRedis(
        host=configuration_file.get('RedisGlobal', 'host'),
        port=configuration_file.getint('RedisGlobal', 'port'),
        db=configuration_file.getint('RedisLIST', 'db'))
    content = {'content': time.time()}
    redis_server.rpush(configuration_file.get('RedisLIST', 'listName'),
        json.dumps({'zmq_name': 'diagnostic_channel', 'content': 'diagnostic_channel ' + json.dumps(content)})
    )

    return_flag = False
    return_text = ''
    time_slept = 0
    sleep_duration = 0.2
    sleep_max = 10.0
    redis_server.delete('diagnostic_tool_response')
    while True:
        reply = redis_server.get('diagnostic_tool_response')
        elements_in_list = redis_server.llen(configuration_file.get('RedisLIST', 'listName'))
        if reply is None:
            if time_slept >= sleep_max:
                return_flag = False
                return_text = 'zmq_dispatcher did not respond in the given time ({}s)'.format(int(sleep_max))
                if len(pgrep_dispatcher_output) > 0:
                    return_text += '\n\t➥ Consider restarting it: {}'.format(pgrep_dispatcher_output)
                else:
                    return_text += '\n\t➥ Consider starting it'
                break
            time.sleep(sleep_duration)
            spinner.text = 'Dispatcher status: No response yet'
            time_slept += sleep_duration
        else:
            return_flag = True
            return_text = 'Took {:.2f}s to complete'.format(float(reply))
            break

    return (return_flag, return_text)


@add_spinner
def check_server_listening(spinner):
    url = '{}:{}/_get_log_head'.format(HOST, PORT)
    spinner.text = 'Trying to connect to {}'.format(url)
    try:
        r = requests.get(url)
    except requests.exceptions.ConnectionError:
        return (False, 'Can\'t connect to {}'.format(url))
    
    if '/error_page' in r.url:
        o = urlparse(r.url)
        query = parse_qs(o.query)
        error_code = query.get('error_code', '')
        if error_code[0] == '1':
            return (False, 'To many redirects. Server may not be properly configured\n\t➥ Try to correctly setup an HTTPS server or change the cookie policy in the configuration')
        else:
            error_message = query.get('error_message', '')[0]
            return (False, 'Unkown error: {}\n{}'.format(error_code, error_message))
    else:
        return (
            r.status_code == 200,
            '{} {}reached. Status code [{}]'.format(url, "not " if r.status_code != 200 else "", r.status_code)
         )



@add_spinner
def check_server_dynamic_enpoint(spinner):
    payload = {
        'username': 'admin@admin.test',
        'password': 'Password1234',
        'submit': 'Sign In'
    }
    sleep_max = 15
    start_time = time.time()

    # Check MISP connectivity
    url_misp = configuration_file.get("Auth", "misp_fqdn")
    try:
        r = requests.get(url_misp, verify=configuration_file.getboolean("Auth", "ssl_verify"))
    except requests.exceptions.SSLError as e:
        if 'CERTIFICATE_VERIFY_FAILED' in str(e):
            return (False, 'SSL connection error certificate verify failed.\n\t➥ Review your configuration'.format(e))
        else:
            return (False, 'SSL connection error `{}`.\n\t➥ Review your configuration'.format(e))

    except requests.exceptions.ConnectionError:
        return (False, 'MISP `{}` cannot be reached.\n\t➥ Review your configuration'.format(url_misp))

    url_login = '{}:{}/login'.format(HOST, PORT)
    url = '{}:{}/_logs'.format(HOST, PORT)
    session = requests.Session()
    session.verify = configuration_file.getboolean("Auth", "ssl_verify")
    r_login = session.post(url_login, data=payload)

    # Check if we ended up on the error page
    if '/error_page' in r_login.url:
        o = urlparse(r_login.url)
        query = parse_qs(o.query)
        error_code = query.get('error_code', '')
        if error_code[0] == '2':
            return (False, 'MISP cannot be reached for authentication\n\t➥ Review MISP fully qualified name and SSL settings')
        else:
            error_message = query.get('error_message', '')[0]
            return (False, 'Unkown error: {}\n{}'.format(error_code, error_message))

    # Recover error message from the url
    if '/login' in r_login.url:
        o = urlparse(r_login.url)
        query = parse_qs(o.query)
        error_message = query.get('auth_error_message', ['Redirected to `loging` caused by an unknown error'])[0]
        return_text = 'Redirected to `loging` caused by: {}'.format(error_message)
        return (False, return_text)

    # Connection seems to be successful, checking if we receive data from event-stream
    r = session.get(url, stream=True, timeout=sleep_max, headers={'Accept': 'text/event-stream'})
    return_flag = False
    return_text = 'Dynamic endpoint returned data but not in the correct format.'
    try:
        for line in r.iter_lines():
            if line.startswith(b'data: '):
                data = line[6:]
                try:
                    json.loads(data)
                    return_flag = True
                    return_text = 'Dynamic endpoint returned data (took {:.2f}s)\n\t➥ {}...'.format(time.time()-start_time, line[6:20])
                    break
                except Exception:
                    return_flag = False
                    return_text = 'Something went wrong. Output {}'.format(line)
                    break
    except diagnostic_util.TimeoutException:
        return_text = 'Dynamic endpoint did not returned data in the given time ({}sec)'.format(int(time.time()-start_time))
    return (return_flag, return_text)


def start_diagnostic():
    if not (check_virtual_environment_and_packages() and check_configuration()):
        return
    check_file_permission()
    check_redis()
    check_zmq()
    check_processes_status()
    check_subscriber_status()
    if check_buffer_queue() is not True:
        check_buffer_change_rate()
    dispatcher_running = check_dispatcher_status()
    if check_server_listening() and dispatcher_running:
        check_server_dynamic_enpoint()


def main():
    start_diagnostic()


if __name__ == '__main__':
    main()
