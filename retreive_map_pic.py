#!/usr/bin/env python3.5
import redis
import requests
import shutil
import json
import math
import sys, os
import time
from subprocess import PIPE, Popen
import shlex

URL_OPEN_MAP = "http://tile.openstreetmap.org/{zoom}/{x}/{y}.png"
MAP_DIR = "static/maps/"
ZOOM = 17
dlat = 2
dlon = 2
serv = redis.StrictRedis('localhost', 6250, 2)
channel_proc = "CoordToProcess"
channel_disp = "PicToDisplay"


def lon2tile(lon, zoom):
    return (math.floor((lon+180)/360*math.pow(2,zoom)))

def lat2tile(lat, zoom):
    return (math.floor((1-math.log(math.tan(lat*math.pi/180) + 1/math.cos(lat*math.pi/180))/math.pi)/2 *math.pow(2,zoom)))


def main():
    pubsub = serv.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(channel_proc)

    while True:
        for d in pubsub.listen():
            #data = json.loads(d.decode('utf8'))
            download_maps(d['data'])

def create_box_around_coord(lon,lat):
    pics = []
    for dx in range(-1,2,1):
        for dy in range(-1,2,1):
            pics.append(URL_OPEN_MAP.format(x=lon+dx, y=lat+dy, zoom=ZOOM))
    return pics

def download_and_merge(url_list, coord):
    to_process = b""
    for i, url in enumerate(url_list):
        to_process += (str(i+1)+' '+url+'\n').encode('utf8')

    map_name = "map_{lon}-{lat}.png".format(lon=coord['lon'], lat=coord['lat'])
    path = os.path.join(MAP_DIR, map_name)
    cmd1 = "parallel --colsep ' ' wget -O maps/{1} {2}"
    cmd2 = "montage -geometry +0+0 maps/1 maps/4 maps/7 maps/2 maps/5 maps/8 maps/3 maps/6 maps/9  "+path

    # Donwload tiles
    p = Popen(shlex.split(cmd1), stdout=PIPE, stdin=PIPE)
    p.communicate(input=to_process)

    # Combine tiles
    p = Popen(shlex.split(cmd2), stdout=PIPE, stdin=PIPE)

    return map_name

def download_maps(coord):
    coord = json.loads(coord.decode('utf8'))
    print(str(coord))
    lat = lat2tile(coord['lat'], ZOOM)
    lon = lon2tile(coord['lon'], ZOOM)

    urls = create_box_around_coord(lon, lat)
    map_name = download_and_merge(urls, coord)
    print(map_name)
    serv.publish(channel_disp, json.dumps({ "path": map_name, "coord": coord }))

if __name__ == '__main__':
    main()
