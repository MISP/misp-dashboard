import redis
import os
import configparser
import logging


configfile = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config/config.cfg')
cfg = configparser.ConfigParser()
cfg.read(configfile)
serv_log = redis.StrictRedis(
        host=cfg.get('RedisGlobal', 'host'),
        port=cfg.getint('RedisGlobal', 'port'),
        db=cfg.getint('RedisLog', 'db'))
serv_redis_db = redis.StrictRedis(
        host=cfg.get('RedisGlobal', 'host'),
        port=cfg.getint('RedisGlobal', 'port'),
        db=cfg.getint('RedisDB', 'db'))
serv_list = redis.StrictRedis(
        host=cfg.get('RedisGlobal', 'host'),
        port=cfg.getint('RedisGlobal', 'port'),
        db=cfg.getint('RedisLIST', 'db'))

# logger
# logDir = cfg.get('Log', 'directory')
# logfilename = cfg.get('Log', 'update_filename')
# logPath = os.path.join(logDir, logfilename)
# if not os.path.exists(logDir):
#     os.makedirs(logDir)
# try:
#     logging.basicConfig(filename=logPath, filemode='a', level=logging.INFO)
# except PermissionError as error:
#     print(error)
#     print("Please fix the above and try again.")
#     sys.exit(126)
# update_logger = logging.getLogger(__name__)
logDir = cfg.get('Log', 'directory')
logfilename = cfg.get('Log', 'update_filename')
logPath = os.path.join(logDir, logfilename)
if not os.path.exists(logDir):
    os.makedirs(logDir)
handler = logging.FileHandler(logPath)
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s:%(message)s')
handler.setFormatter(formatter)
update_logger = logging.getLogger(__name__)
update_logger.setLevel(logging.INFO)
update_logger.addHandler(handler)


def check_for_updates():
    db_version = serv_redis_db.get(cfg.get('RedisDB', 'dbVersion'))
    db_version = db_version if db_version is not None else 0
    result = False

    if db_version == 0:
        result = apply_update_1()

    if result:
        serv_redis_db.set(cfg.get('RedisDB', 'dbVersion'), db_version+1)
        update_logger.warning(f'Bumped dbVersion to {db_version+1}')
    else:
        update_logger.info('Database up-to-date')


# Data format changed. Wipe the key.
def apply_update_1():
    serv_redis_db.delete('TEMP_CACHE_LIVE:Attribute')
    log_text = 'Executed update 1. Deleted Redis key `TEMP_CACHE_LIVE:Attribute`'
    print(log_text)
    update_logger.info(log_text)
    return True
