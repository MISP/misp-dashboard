#!/usr/bin/env python3
import configparser
import datetime
import uuid
import errno
import json
import logging
import math
import os
import re
from datetime import timedelta
import random
from time import gmtime as now
from time import sleep, strftime

import redis

import util
from flask import (Flask, Response, jsonify, render_template, request, make_response,
                   send_from_directory, stream_with_context, url_for, redirect)
from flask_login import (UserMixin, LoginManager, current_user, login_user, logout_user, login_required)
from helpers import (contributor_helper, geo_helper, live_helper,
                     trendings_helper, users_helper)

import requests
from wtforms import Form, SubmitField, StringField, PasswordField, validators

configfile = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config/config.cfg')
cfg = configparser.ConfigParser()
cfg.read(configfile)

logger = logging.getLogger('werkzeug')
logger.setLevel(logging.ERROR)

server_host = cfg.get("Server", "host")
server_port = cfg.getint("Server", "port")
server_debug = cfg.get("Server", "debug")
server_ssl = cfg.get("Server", "ssl")
try:
    server_ssl_cert = cfg.get("Server", "ssl_cert")
    server_ssl_key = cfg.get("Server", "ssl_key")
except:
    server_ssl_cert = None
    server_ssl_key = None
    pass
auth_host = cfg.get("Auth", "misp_fqdn")
auth_enabled = cfg.getboolean("Auth", "auth_enabled")
auth_ssl_verify = cfg.getboolean("Auth", "ssl_verify")
auth_session_secret = cfg.get("Auth", "session_secret")
auth_session_cookie_secure = cfg.getboolean("Auth", "session_cookie_secure")
auth_session_cookie_samesite = cfg.get("Auth", "session_cookie_samesite")
auth_permanent_session_lifetime = cfg.getint("Auth", "permanent_session_lifetime")

app = Flask(__name__)
#app.secret_key = auth_session_secret
app.config.update(
    SECRET_KEY=auth_session_secret,
    SESSION_COOKIE_SECURE=auth_session_cookie_secure,
    SESSION_COOKIE_SAMESITE=auth_session_cookie_samesite,
    PERMANENT_SESSION_LIFETIME=timedelta(days=auth_permanent_session_lifetime)
)

redis_server_log = redis.StrictRedis(
        host=cfg.get('RedisGlobal', 'host'),
        port=cfg.getint('RedisGlobal', 'port'),
        db=cfg.getint('RedisLog', 'db'),
        decode_responses=True)
redis_server_map = redis.StrictRedis(
        host=cfg.get('RedisGlobal', 'host'),
        port=cfg.getint('RedisGlobal', 'port'),
        db=cfg.getint('RedisMap', 'db'),
        decode_responses=True)
serv_redis_db = redis.StrictRedis(
        host=cfg.get('RedisGlobal', 'host'),
        port=cfg.getint('RedisGlobal', 'port'),
        db=cfg.getint('RedisDB', 'db'),
        decode_responses=True)

streamLogCacheKey = cfg.get('RedisLog', 'streamLogCacheKey')
streamMapCacheKey = cfg.get('RedisLog', 'streamMapCacheKey')

live_helper = live_helper.Live_helper(serv_redis_db, cfg)
geo_helper = geo_helper.Geo_helper(serv_redis_db, cfg)
contributor_helper = contributor_helper.Contributor_helper(serv_redis_db, cfg)
users_helper = users_helper.Users_helper(serv_redis_db, cfg)
trendings_helper = trendings_helper.Trendings_helper(serv_redis_db, cfg)

login_manager = LoginManager(app)
login_manager.session_protection = "strong"
login_manager.init_app(app)

##########
## Auth ##
##########

class User(UserMixin):
    def __init__(self, id, password):
        self.id = id
        self.password = password

    def misp_login(self):
        """
        Use login form data to authenticate a user to MISP.

        This function uses requests to log a user into the MISP web UI. When authentication is successful MISP redirects the client to the '/users/routeafterlogin' endpoint. The requests session history is parsed for a redirect to this endpoint.
        :param misp_url: The FQDN of a MISP instance to authenticate against.
        :param user: The user account to authenticate.
        :param password: The user account password.
        :return:
        """
        post_data = {
            "_method": "POST",
            "data[_Token][key]": "",
            "data[_Token][fields]": "",
            "data[_Token][unlocked]": "",
            "data[_Token][debug]": "",
            "data[User][email]": self.id,
            "data[User][password]": self.password,
        }

        misp_login_page = auth_host + "/users/login"
        misp_user_me_page = auth_host + "/users/view/me.json"
        session = requests.Session()
        session.verify = auth_ssl_verify

        # The login page contains hidden form values required for authenticaiton.
        login_page = session.get(misp_login_page)

        # This regex matches the "data[_Token][fields]" value needed to make a POST request on the MISP login page.
        token_fields_exp = re.compile(r'name="data\[_Token]\[fields]" value="([^\s]+)"')
        token_fields = token_fields_exp.search(login_page.text)

        # This regex matches the "data[_Token][key]" value needed to make a POST request on the MISP login page.
        token_key_exp = re.compile(r'name="data\[_Token]\[key]" value="([^\s]+)"')
        token_key = token_key_exp.search(login_page.text)

        # This regex matches the "data[_Token][debug]" value needed to make a POST request on the MISP login page.
        token_key_exp = re.compile(r'name="data\[_Token]\[debug]" value="([^\s]+)"')
        token_debug = token_key_exp.search(login_page.text)

        post_data["data[_Token][fields]"] = token_fields.group(1)
        post_data["data[_Token][key]"] = token_key.group(1)
        post_data["data[_Token][debug]"] = token_debug.group(1)

        # POST request with user credentials + hidden form values.
        post_to_login_page = session.post(misp_login_page, data=post_data, allow_redirects=False)
        # Consider setup with MISP baseurl set
        redirect_location = post_to_login_page.headers.get('Location', '')
        # Authentication is successful if MISP returns a redirect to '/users/routeafterlogin'.
        if '/users/routeafterlogin' in redirect_location:
            # Logged in, check if logged in user can access the dashboard
            me_json = session.get(misp_user_me_page).json()
            dashboard_access = me_json.get('UserSetting', {}).get('dashboard_access', False)
            if dashboard_access is True or dashboard_access == 1:
                return (True, '')
            else:
                return (None, 'User does not have dashboard access')
        return (None, '')


@login_manager.user_loader
def load_user(user_id):
    """
    Return a User object required by flask-login to keep state of a user session.

    Typically load_user is used to perform a user lookup on a db; it should return a User object or None if the user is not found. Authentication is defered to MISP via User.misp_login() and so this function always returns a User object .
    :param user_id: A MISP username.
    :return:
    """
    return User(user_id, "")


@login_manager.unauthorized_handler
def unauthorized():
    """
    Redirect unauthorized user to login page.
    :return:
    """
    redirectCount = int(request.cookies.get('redirectCount', '0'))
    if redirectCount > 5:
        response = make_response(redirect(url_for(
            'error_page',
            error_message='Too many redirects. This can be due to your brower not accepting cookies or the misp-dashboard website is badly configured',
            error_code='1'
        )))
        response.set_cookie('redirectCount', '0', secure=False, httponly=True)
    else:
        response = make_response(redirect(url_for('login', auth_error=True, auth_error_message='Unauthorized. Review your cookie settings')))
        response.set_cookie('redirectCount', str(redirectCount+1), secure=False, httponly=True)
    return response


@app.route('/error_page')
def error_page():
    error_message = request.args.get('error_message', False)
    return render_template('error_page.html', error_message=error_message)


@app.route('/logout')
@login_required
def logout():
    """
    Logout the user and redirect to the login form.
    :return:
    """
    logout_user()
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login form route.
    :return:
    """
    if not auth_enabled:
        # Generate a random user name and redirect the automatically authenticated user to index.
        user = User(str(uuid.uuid4()).replace('-',''), '')
        login_user(user)
        return redirect(url_for('index'))

    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        user = User(form.username.data, form.password.data)

        error_message = 'Username and Password does not match when connecting to MISP or incorrect MISP permission'
        try:
            is_logged_in, misp_error_message = user.misp_login()
            if len(misp_error_message) > 0:
                error_message = misp_error_message
            if is_logged_in:
                login_user(user)
                return redirect(url_for('index'))
        except requests.exceptions.SSLError:
            return redirect(url_for('login', auth_error=True, auth_error_message='MISP cannot be reached for authentication'))

        return redirect(url_for('login', auth_error=True, auth_error_message=error_message))
    else:
        auth_error = request.args.get('auth_error', False)
        auth_error_message = request.args.get('auth_error_message', '')
        return render_template('login.html', title='Login', form=form, authError=auth_error, authErrorMessage=auth_error_message)



class LoginForm(Form):
    """
    WTForm form object.  This object defines form fields in the login endpoint.
    """
    username = StringField('Username', [validators.Length(max=255)])
    password = PasswordField('Password', [validators.Length(max=255)])
    submit = SubmitField('Sign In')


##########
## UTIL ##
##########

''' INDEX '''
class LogItem():

    FIELDNAME_ORDER = []
    FIELDNAME_ORDER_HEADER = []
    for item in json.loads(cfg.get('Dashboard', 'fieldname_order')):
        if type(item) is list:
            FIELDNAME_ORDER_HEADER.append(" | ".join(item))
        else:
            FIELDNAME_ORDER_HEADER.append(item)
        FIELDNAME_ORDER.append(item)

    def __init__(self, feed, filters={}):
        self.filters = filters
        self.feed = feed
        self.fields = []

    def get_head_row(self):
        to_ret = []
        for fn in LogItem.FIELDNAME_ORDER_HEADER:
            to_ret.append(fn)
        return to_ret

    def get_row(self):
        if not self.pass_filter():
            return False

        to_ret = {}
        for i, field in enumerate(json.loads(cfg.get('Dashboard', 'fieldname_order'))):
            if type(field) is list:
                to_join = []
                for subField in field:
                    to_join.append(str(util.getFields(self.feed, subField)))
                to_add = cfg.get('Dashboard', 'char_separator').join(to_join)
            else:
                to_add = util.getFields(self.feed, field)
            to_ret[i] = to_add if to_add is not None else ''
        return to_ret


    def pass_filter(self):
        for filter, filterValue in self.filters.items():
            jsonValue = util.getFields(self.feed, filter)
            if jsonValue is None or jsonValue != filterValue:
                return False
        return True


class EventMessage():
    # Suppose the event message is a json with the format {name: 'feedName', log:'logData'}
    def __init__(self, msg, filters):
        if not isinstance(msg, dict):
            try:
                jsonMsg = json.loads(msg)
                jsonMsg['log'] = json.loads(jsonMsg['log'])
            except json.JSONDecodeError as e:
                logger.error(e)
                jsonMsg = { 'name': "undefined" ,'log': json.loads(msg) }
        else:
            jsonMsg = msg

        self.name = jsonMsg['name']
        self.zmqName = jsonMsg['zmqName']

        if self.name == 'Attribute':
            self.feed = jsonMsg['log']
            self.feed = LogItem(self.feed, filters).get_row()
        elif self.name == 'ObjectAttribute':
            self.feed = jsonMsg['log']
            self.feed = LogItem(self.feed, filters).get_row()
        else:
            self.feed = jsonMsg['log']

    def to_json_ev(self):
        if self.feed is not False:
            to_ret = { 'log': self.feed, 'name': self.name, 'zmqName': self.zmqName }
            return 'data: {}\n\n'.format(json.dumps(to_ret))
        else:
            return ''

    def to_json(self):
        if self.feed is not False:
            to_ret = { 'log': self.feed, 'name': self.name, 'zmqName': self.zmqName }
            return json.dumps(to_ret)
        else:
            return ''

    def to_dict(self):
        return {'log': self.feed, 'name': self.name, 'zmqName': self.zmqName}


###########
## ROUTE ##
###########

''' MAIN ROUTE '''

@app.route("/")
@login_required
def index():
    ratioCorrection = 88
    pannelSize = [
            "{:.0f}".format(cfg.getint('Dashboard' ,'size_openStreet_pannel_perc')/100*ratioCorrection),
            "{:.0f}".format((100-cfg.getint('Dashboard' ,'size_openStreet_pannel_perc'))/100*ratioCorrection),
            "{:.0f}".format(cfg.getint('Dashboard' ,'size_world_pannel_perc')/100*ratioCorrection),
            "{:.0f}".format((100-cfg.getint('Dashboard' ,'size_world_pannel_perc'))/100*ratioCorrection)
            ]
    return render_template('index.html',
            pannelSize=pannelSize,
            size_dashboard_width=[cfg.getint('Dashboard' ,'size_dashboard_left_width'), 12-cfg.getint('Dashboard', 'size_dashboard_left_width')],
            itemToPlot=cfg.get('Dashboard', 'item_to_plot'),
            graph_log_refresh_rate=cfg.getint('Dashboard' ,'graph_log_refresh_rate'),
            char_separator=cfg.get('Dashboard', 'char_separator'),
            rotation_wait_time=cfg.getint('Dashboard' ,'rotation_wait_time'),
            max_img_rotation=cfg.getint('Dashboard' ,'max_img_rotation'),
            hours_spanned=cfg.getint('Dashboard' ,'hours_spanned'),
            zoomlevel=cfg.getint('Dashboard' ,'zoomlevel')
            )

@app.route('/favicon.ico')
@login_required
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route("/geo")
@login_required
def geo():
    return render_template('geo.html',
            zoomlevel=cfg.getint('GEO' ,'zoomlevel'),
            default_updateFrequency=cfg.getint('GEO' ,'updateFrequency')
            )

@app.route("/contrib")
@login_required
def contrib():
    categ_list = contributor_helper.categories_in_datatable
    categ_list_str = [ s[0].upper() + s[1:].replace('_', ' ') for s in categ_list]
    categ_list_points = [contributor_helper.DICO_PNTS_REWARD[categ] for categ in categ_list]

    org_rank = contributor_helper.org_rank
    org_rank_requirement_pnts = contributor_helper.org_rank_requirement_pnts
    org_rank_requirement_text = contributor_helper.org_rank_requirement_text
    org_rank_list = [[rank, title, org_rank_requirement_pnts[rank], org_rank_requirement_text[rank]] for rank, title in org_rank.items()]
    org_rank_list.sort(key=lambda x: x[0])
    org_rank_additional_text = contributor_helper.org_rank_additional_info

    org_honor_badge_title = contributor_helper.org_honor_badge_title
    org_honor_badge_title_list = [ [num, text] for num, text in contributor_helper.org_honor_badge_title.items()]
    org_honor_badge_title_list.sort(key=lambda x: x[0])

    trophy_categ_list = contributor_helper.categories_in_trophy
    trophy_categ_list_str = [ s[0].upper() + s[1:].replace('_', ' ') for s in trophy_categ_list]
    trophy_title = contributor_helper.trophy_title
    trophy_title_str = []
    for i in range(contributor_helper.trophyNum+1):
        trophy_title_str.append(trophy_title[i])
    trophy_mapping = ["Top 1"] + [ str(x)+"%" for x in contributor_helper.trophyMapping] + [" "]
    trophy_mapping.reverse()

    currOrg = request.args.get('org')
    if currOrg is None:
        currOrg = ""
    return render_template('contrib.html',
            currOrg=currOrg,
            rankMultiplier=contributor_helper.rankMultiplier,
            default_pnts_per_contribution=contributor_helper.default_pnts_per_contribution,
            additional_help_text=json.loads(cfg.get('CONTRIB', 'additional_help_text')),
            categ_list=json.dumps(categ_list),
            categ_list_str=categ_list_str,
            categ_list_points=categ_list_points,
            org_rank_json=json.dumps(org_rank),
            org_rank_list=org_rank_list,
            org_rank_additional_text=org_rank_additional_text,
            org_honor_badge_title=json.dumps(org_honor_badge_title),
            org_honor_badge_title_list=org_honor_badge_title_list,
            trophy_categ_list=json.dumps(trophy_categ_list),
            trophy_categ_list_id=trophy_categ_list,
            trophy_categ_list_str=trophy_categ_list_str,
            trophy_title=json.dumps(trophy_title),
            trophy_title_str=trophy_title_str,
            trophy_mapping=trophy_mapping,
            min_between_reload=cfg.getint('CONTRIB', 'min_between_reload')
            )

@app.route("/users")
@login_required
def users():
    return render_template('users.html',
            )


@app.route("/trendings")
@login_required
def trendings():
    maxNum = request.args.get('maxNum')
    try:
        maxNum = int(maxNum)
    except:
        maxNum = 15
    url_misp_event = cfg.get('RedisGlobal', 'misp_web_url')

    return render_template('trendings.html',
            maxNum=maxNum,
            url_misp_event=url_misp_event
            )

''' INDEX '''

@app.route("/_logs")
@login_required
def logs():
    if request.accept_mimetypes.accept_json or request.method == 'POST':
        key = 'Attribute'
        j = live_helper.get_stream_log_cache(key)
        to_ret = []
        for item in j:
            filters = request.cookies.get('filters', '{}')
            filters = json.loads(filters)
            ev = EventMessage(item, filters)
            if ev is not None:
                dico = ev.to_dict()
                if dico['log'] != False:
                    to_ret.append(dico)
        return jsonify(to_ret)
    else:
        return Response(stream_with_context(event_stream_log()), mimetype="text/event-stream")

@app.route("/_maps")
@login_required
def maps():
    if request.accept_mimetypes.accept_json or request.method == 'POST':
        key = 'Map'
        j = live_helper.get_stream_log_cache(key)
        return jsonify(j)
    else:
        return Response(event_stream_maps(), mimetype="text/event-stream")

@app.route("/_get_log_head")
@login_required
def getLogHead():
    return json.dumps(LogItem('').get_head_row())

def event_stream_log():
    subscriber_log = redis_server_log.pubsub(ignore_subscribe_messages=True)
    subscriber_log.subscribe(live_helper.CHANNEL)
    try:
        for msg in subscriber_log.listen():
            filters = request.cookies.get('filters', '{}')
            filters = json.loads(filters)
            content = msg['data']
            ev = EventMessage(content, filters)
            if ev is not None:
                yield ev.to_json_ev()
            else:
                pass
    except GeneratorExit:
        subscriber_log.unsubscribe()

def event_stream_maps():
    subscriber_map = redis_server_map.pubsub(ignore_subscribe_messages=True)
    subscriber_map.psubscribe(cfg.get('RedisMap', 'channelDisp'))
    try:
        for msg in subscriber_map.listen():
            content = msg['data']
            to_ret = 'data: {}\n\n'.format(content)
            yield to_ret
    except GeneratorExit:
        subscriber_map.unsubscribe()

''' GEO '''

@app.route("/_getTopCoord")
@login_required
def getTopCoord():
    try:
        date = datetime.datetime.fromtimestamp(float(request.args.get('date')))
    except:
        date = datetime.datetime.now()
    data = geo_helper.getTopCoord(date)
    return jsonify(data)

@app.route("/_getHitMap")
@login_required
def getHitMap():
    try:
        date = datetime.datetime.fromtimestamp(float(request.args.get('date')))
    except:
        date = datetime.datetime.now()
    data = geo_helper.getHitMap(date)
    return jsonify(data)

@app.route("/_getCoordsByRadius")
@login_required
def getCoordsByRadius():
    try:
        dateStart = datetime.datetime.fromtimestamp(float(request.args.get('dateStart')))
        dateEnd = datetime.datetime.fromtimestamp(float(request.args.get('dateEnd')))
        centerLat = request.args.get('centerLat')
        centerLon = request.args.get('centerLon')
        radius = int(math.ceil(float(request.args.get('radius'))))
    except:
        return jsonify([])

    data = geo_helper.getCoordsByRadius(dateStart, dateEnd, centerLat, centerLon, radius)
    return jsonify(data)

''' CONTRIB '''

@app.route("/_getLastContributors")
@login_required
def getLastContributors():
    return jsonify(contributor_helper.getLastContributorsFromRedis())

@app.route("/_eventStreamLastContributor")
@login_required
def getLastContributor():
    return Response(eventStreamLastContributor(), mimetype="text/event-stream")

@app.route("/_eventStreamAwards")
@login_required
def getLastStreamAwards():
    return Response(eventStreamAwards(), mimetype="text/event-stream")

def eventStreamLastContributor():
    subscriber_lastContrib = redis_server_log.pubsub(ignore_subscribe_messages=True)
    subscriber_lastContrib.psubscribe(cfg.get('RedisLog', 'channelLastContributor'))
    try:
        for msg in subscriber_lastContrib.listen():
            content = msg['data']
            contentJson = json.loads(content)
            lastContribJson = json.loads(contentJson['log'])
            org = lastContribJson['org']
            to_return = contributor_helper.getContributorFromRedis(org)
            epoch = lastContribJson['epoch']
            to_return['epoch'] = epoch
            yield 'data: {}\n\n'.format(json.dumps(to_return))
    except GeneratorExit:
        subscriber_lastContrib.unsubscribe()

def eventStreamAwards():
    subscriber_lastAwards = redis_server_log.pubsub(ignore_subscribe_messages=True)
    subscriber_lastAwards.psubscribe(cfg.get('RedisLog', 'channelLastAwards'))
    try:
        for msg in subscriber_lastAwards.listen():
            content = msg['data']
            contentJson = json.loads(content)
            lastAwardJson = json.loads(contentJson['log'])
            org = lastAwardJson['org']
            to_return = contributor_helper.getContributorFromRedis(org)
            epoch = lastAwardJson['epoch']
            to_return['epoch'] = epoch
            to_return['award'] = lastAwardJson['award']
            yield 'data: {}\n\n'.format(json.dumps(to_return))
    except GeneratorExit:
        subscriber_lastAwards.unsubscribe()

@app.route("/_getTopContributor")
@login_required
def getTopContributor(suppliedDate=None, maxNum=100):
    if suppliedDate is None:
        try:
            date = datetime.datetime.fromtimestamp(float(request.args.get('date')))
        except:
            date = datetime.datetime.now()
    else:
        date = suppliedDate

    data = contributor_helper.getTopContributorFromRedis(date, maxNum=maxNum)
    return jsonify(data)

@app.route("/_getFameContributor")
@login_required
def getFameContributor():
    try:
        date = datetime.datetime.fromtimestamp(float(request.args.get('date')))
    except:
        today = datetime.datetime.now()
        # get previous month
        date = (datetime.datetime(today.year, today.month, 1) - datetime.timedelta(days=1))
    return getTopContributor(suppliedDate=date, maxNum=10)

@app.route("/_getFameQualContributor")
@login_required
def getFameQualContributor():
    try:
        date = datetime.datetime.fromtimestamp(float(request.args.get('date')))
    except:
        today = datetime.datetime.now()
        # get previous month
        date = (datetime.datetime(today.year, today.month, 1) - datetime.timedelta(days=1))
    return getTopContributor(suppliedDate=date, maxNum=10)

@app.route("/_getTop5Overtime")
@login_required
def getTop5Overtime():
    return jsonify(contributor_helper.getTop5OvertimeFromRedis())

@app.route("/_getOrgOvertime")
@login_required
def getOrgOvertime():
    try:
        org = request.args.get('org')
    except:
        org = ''
    return jsonify(contributor_helper.getOrgOvertime(org))

@app.route("/_getCategPerContrib")
@login_required
def getCategPerContrib():
    try:
        date = datetime.datetime.fromtimestamp(float(request.args.get('date')))
    except:
        date = datetime.datetime.now()

    return jsonify(contributor_helper.getCategPerContribFromRedis(date))

@app.route("/_getLatestAwards")
@login_required
def getLatestAwards():
    try:
        date = datetime.datetime.fromtimestamp(float(request.args.get('date')))
    except:
        date = datetime.datetime.now()

    return jsonify(contributor_helper.getLastAwardsFromRedis())

@app.route("/_getAllOrg")
@login_required
def getAllOrg():
    return jsonify(contributor_helper.getAllOrgFromRedis())

@app.route("/_getOrgRank")
@login_required
def getOrgRank():
    try:
        org = request.args.get('org')
    except:
        org = ''
    return jsonify(contributor_helper.getCurrentOrgRankFromRedis(org))

@app.route("/_getContributionOrgStatus")
@login_required
def getContributionOrgStatus():
    try:
        org = request.args.get('org')
    except:
        org = ''
    return jsonify(contributor_helper.getCurrentContributionStatus(org))

@app.route("/_getHonorBadges")
@login_required
def getHonorBadges():
    try:
        org = request.args.get('org')
    except:
        org = ''
    return jsonify(contributor_helper.getOrgHonorBadges(org))

@app.route("/_getTrophies")
@login_required
def getTrophies():
    try:
        org = request.args.get('org')
    except:
        org = ''
    return jsonify(contributor_helper.getOrgTrophies(org))

@app.route("/_getAllOrgsTrophyRanking")
@app.route("/_getAllOrgsTrophyRanking/<string:categ>")
@login_required
def getAllOrgsTrophyRanking(categ=None):
    return jsonify(contributor_helper.getAllOrgsTrophyRanking(categ))


''' USERS '''

@app.route("/_getUserLogins")
@login_required
def getUserLogins():
    try:
        date = datetime.datetime.fromtimestamp(float(request.args.get('date')))
    except:
        date = datetime.datetime.now()

    org = request.args.get('org', None)
    data = users_helper.getUserLoginsForPunchCard(date, org)
    return jsonify(data)

@app.route("/_getAllLoggedOrg")
@login_required
def getAllLoggedOrg():
    return jsonify(users_helper.getAllOrg())

@app.route("/_getTopOrglogin")
@login_required
def getTopOrglogin():
    try:
        date = datetime.datetime.fromtimestamp(float(request.args.get('date')))
    except:
        date = datetime.datetime.now()

    data = users_helper.getTopOrglogin(date, maxNum=12)
    return jsonify(data)

@app.route("/_getLoginVSCOntribution")
@login_required
def getLoginVSCOntribution():
    try:
        date = datetime.datetime.fromtimestamp(float(request.args.get('date')))
    except:
        date = datetime.datetime.now()

    data = users_helper.getLoginVSCOntribution(date)
    return jsonify(data)

@app.route("/_getUserLoginsAndContribOvertime")
@login_required
def getUserLoginsAndContribOvertime():
    try:
        date = datetime.datetime.fromtimestamp(float(request.args.get('date')))
    except:
        date = datetime.datetime.now()

    org = request.args.get('org', None)
    data = users_helper.getUserLoginsAndContribOvertime(date, org)
    return jsonify(data)

''' TRENDINGS '''
@app.route("/_getTrendingEvents")
@login_required
def getTrendingEvents():
    try:
        dateS = datetime.datetime.fromtimestamp(float(request.args.get('dateS')))
        dateE = datetime.datetime.fromtimestamp(float(request.args.get('dateE')))
    except:
        dateS = datetime.datetime.now() - datetime.timedelta(days=7)
        dateE = datetime.datetime.now()

    specificLabel = request.args.get('specificLabel')
    data = trendings_helper.getTrendingEvents(dateS, dateE, specificLabel, topNum=int(request.args.get('topNum', 10)))
    return jsonify(data)

@app.route("/_getTrendingCategs")
@login_required
def getTrendingCategs():
    try:
        dateS = datetime.datetime.fromtimestamp(float(request.args.get('dateS')))
        dateE = datetime.datetime.fromtimestamp(float(request.args.get('dateE')))
    except:
        dateS = datetime.datetime.now() - datetime.timedelta(days=7)
        dateE = datetime.datetime.now()


    data = trendings_helper.getTrendingCategs(dateS, dateE, topNum=int(request.args.get('topNum', 10)))
    return jsonify(data)

@app.route("/_getTrendingTags")
@login_required
def getTrendingTags():
    try:
        dateS = datetime.datetime.fromtimestamp(float(request.args.get('dateS')))
        dateE = datetime.datetime.fromtimestamp(float(request.args.get('dateE')))
    except:
        dateS = datetime.datetime.now() - datetime.timedelta(days=7)
        dateE = datetime.datetime.now()


    data = trendings_helper.getTrendingTags(dateS, dateE, topNum=int(request.args.get('topNum', 10)))
    return jsonify(data)

@app.route("/_getTrendingSightings")
@login_required
def getTrendingSightings():
    try:
        dateS = datetime.datetime.fromtimestamp(float(request.args.get('dateS')))
        dateE = datetime.datetime.fromtimestamp(float(request.args.get('dateE')))
    except:
        dateS = datetime.datetime.now() - datetime.timedelta(days=7)
        dateE = datetime.datetime.now()

    data = trendings_helper.getTrendingSightings(dateS, dateE)
    return jsonify(data)

@app.route("/_getTrendingDisc")
@login_required
def getTrendingDisc():
    try:
        dateS = datetime.datetime.fromtimestamp(float(request.args.get('dateS')))
        dateE = datetime.datetime.fromtimestamp(float(request.args.get('dateE')))
    except:
        dateS = datetime.datetime.now() - datetime.timedelta(days=7)
        dateE = datetime.datetime.now()


    data = trendings_helper.getTrendingDisc(dateS, dateE)
    return jsonify(data)

@app.route("/_getTypeaheadData")
@login_required
def getTypeaheadData():
    try:
        dateS = datetime.datetime.fromtimestamp(float(request.args.get('dateS')))
        dateE = datetime.datetime.fromtimestamp(float(request.args.get('dateE')))
    except:
        dateS = datetime.datetime.now() - datetime.timedelta(days=7)
        dateE = datetime.datetime.now()

    data = trendings_helper.getTypeaheadData(dateS, dateE)
    return jsonify(data)

@app.route("/_getGenericTrendingOvertime")
@login_required
def getGenericTrendingOvertime():
    try:
        dateS = datetime.datetime.fromtimestamp(float(request.args.get('dateS')))
        dateE = datetime.datetime.fromtimestamp(float(request.args.get('dateE')))
    except:
        dateS = datetime.datetime.now() - datetime.timedelta(days=7)
        dateE = datetime.datetime.now()
    choice = request.args.get('choice', 'events')

    data = trendings_helper.getGenericTrendingOvertime(dateS, dateE, choice=choice)
    return jsonify(data)

if __name__ == '__main__':
    try:
        if bool(server_ssl) is True:
            if server_ssl_cert and server_ssl_key:
                server_ssl_context = (server_ssl_cert, server_ssl_key)
            else:
                server_ssl_context = 'adhoc' 
        else:
            server_ssl_context = None

        app.run(host=server_host,
            port=server_port,
            ssl_context=server_ssl_context,
            debug=server_debug,
            threaded=True)
    except OSError as error:
        if error.errno == 98:
            print("\n\n\nAddress already in use, the defined port is: " + str(server_port))
        else:
            print(str(error))
