#!/usr/bin/env python3.5

import os, sys, json
import datetime, time
import redis
import configparser

import util
import contributor_helper

ONE_DAY = 60*60*24
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
CHANNEL_LASTAWARDS = cfg.get('RedisLog', 'channelLastAwards')

chelper = contributor_helper.Contributor_helper(serv_redis_db, cfg)

def publish_log(zmq_name, name, content, channel):
    to_send = { 'name': name, 'data': json.dumps(content), 'zmqName': zmq_name }
    serv_log.publish(channel, json.dumps(to_send))

def printOrgInfo(org):
    org_pnts = chelper.getOrgContributionTotalPoints(org)
    org_c_rank = chelper.getOrgContributionRank(org)
    org_c_status = chelper.getCurrentContributionStatus(org)
    org_honor_badge = chelper.getOrgHonorBadges(org)
    org_trophy = chelper.getOrgTrophies(org)

    os.system('clear')
    print()
    print("Organisation points: {}".format(org_pnts))
    print("Organisation contribution rank: {}".format(org_c_status['rank']))
    print('''
Organisation contribution rank:
-------------------------------''')
    for rank in range(1, chelper.org_rank_maxLevel+1):
        acq = 'x' if org_c_status['status'][rank] == 1 else ' '
        print("{}.\t[{}]\t{}\t{}".format(rank, acq, chelper.org_rank_requirement_pnts[rank], chelper.org_rank_requirement_text[rank]))

    print()
    print('''
Organisation honor badges:
--------------------------''')
    for badgeNum, text in chelper.org_honor_badge_title.items():
        acq = 'x' if badgeNum in org_honor_badge else ' '
        print("{}.\t[{}]\t{}".format(badgeNum, acq, text))

    print()
    print('''
Organisation trophy:
--------------------------''')
    for dic in org_trophy:
        categ = dic['categ']
        trophyRank = dic['trophy_true_rank']
        trophyPnts = dic['trophy_points']
        print("{}\t{} [{}]".format(categ, trophyRank, trophyPnts))
    print()

def main():
    if len(sys.argv) > 1:
        org = sys.argv[1]
    else:
        org = input('Enter the organisation name: ')

    printOrgInfo(org)

    ContributionStatus = chelper.getCurrentContributionStatus(org)
    OLD_org_c_status = ContributionStatus['status']
    OLD_org_honor_badge = chelper.getOrgHonorBadges(org)
    OLD_org_trophy = chelper.getOrgTrophies(org)

    # ranks
    while True:
        org_pnts = chelper.getOrgContributionTotalPoints(org)
        org_c_rank = chelper.getOrgContributionRank(org)
        org_c_status = chelper.getCurrentContributionStatus(org)
        org_honor_badge = chelper.getOrgHonorBadges(org)
        org_trophy = chelper.getOrgTrophies(org)

        userRep = input("Enter the organisation RANK to give/remove to {} (<ENTER> to finish): ".format(org))
        if userRep == '':
            break
        else:
            # validate input
            try: #not int
                rankNum = int(userRep)
            except:
                print('Not an integer')
                continue
            if rankNum < 1 or rankNum > chelper.org_rank_maxLevel:
                print('Not a valid rank')
                continue

            if org_c_status['status'][rankNum] == 1: #remove rank
                chelper.removeContribRankFromOrg(org, rankNum)
            else:
                chelper.giveContribRankToOrg(org, rankNum)

            printOrgInfo(org)

    # badges
    while True:
        org_pnts = chelper.getOrgContributionTotalPoints(org)
        org_c_rank = chelper.getOrgContributionRank(org)
        org_c_status = chelper.getCurrentContributionStatus(org)
        org_honor_badge = chelper.getOrgHonorBadges(org)
        org_trophy = chelper.getOrgTrophies(org)

        userRep = input("Enter the organisation BADGE to give/remove to {} (<ENTER> to finish): ".format(org))
        if userRep == '':
            break
        else:
            # validate input
            try: #not int
                badgeNum = int(userRep)
            except:
                print('Not an integer')
                continue
            if badgeNum < 1 and badgeNum > chelper.honorBadgeNum:
                print('Not a valid rank')
                continue

            if badgeNum in org_honor_badge: #remove badge
                chelper.removeBadgeFromOrg(org, badgeNum)
            else:
                chelper.giveBadgeToOrg(org, badgeNum)

            printOrgInfo(org)

    # trophy
    while True:
        org_pnts = chelper.getOrgContributionTotalPoints(org)
        org_c_rank = chelper.getOrgContributionRank(org)
        org_c_status = chelper.getCurrentContributionStatus(org)
        org_honor_badge = chelper.getOrgHonorBadges(org)
        org_trophy = chelper.getOrgTrophies(org)

        print()
        for i, categ in enumerate(chelper.categories_in_trophy):
            print("{}. {}".format(i, categ))
        userCateg = input("Enter the CATEGORY in which to add/remove trophy points: ")
        if userCateg == '':
            break
        try: #not int
            userCateg = int(userCateg)
        except:
            print('Not an integer')
            continue
        if userCateg < 1 and userCateg > len(chelper.categories_in_trophy):
            print('Not a valid rank')
            continue

        categ = chelper.categories_in_trophy[userCateg]
        userRep = input("Enter the TROPHY POINTS to give/remove to {} (<ENTER> to finish) in {}: ".format(org, categ))
        if userRep == '':
            break
        else:
            # validate input
            try: #not int
                trophyPnts = int(userRep)
            except:
                print('Not an integer')
                continue

            chelper.giveTrophyPointsToOrg(org, categ, trophyPnts)

            printOrgInfo(org)


    now = datetime.datetime.now()
    nowSec = int(time.time())
    ContributionStatus = chelper.getCurrentContributionStatus(org)
    NEW_org_c_status = ContributionStatus['status']
    NEW_org_honor_badge = chelper.getOrgHonorBadges(org)
    NEW_org_trophy = chelper.getOrgTrophies(org)
    awards_given = []

    for i in NEW_org_c_status.keys():
        if OLD_org_c_status[i] < NEW_org_c_status[i] and i != ContributionStatus['rank']:
            awards_given.append(['contribution_status', ContributionStatus['rank']])

    for badgeNum in NEW_org_honor_badge:
        if badgeNum not in  OLD_org_honor_badge:
            awards_given.append(['badge', badgeNum])

    temp = {}
    for item in OLD_org_trophy:
        categ = item['categ']
        rank = item['trophy_true_rank']
        temp[categ] = rank

    for item in NEW_org_trophy:
        categ = item['categ']
        rank = item['trophy_true_rank']
        if rank > temp[categ]:
            awards_given.append(['trophy', [categ, rank]])

    for award in awards_given:
        # update awards given
        serv_redis_db.zadd('CONTRIB_LAST_AWARDS:'+util.getDateStrFormat(now), nowSec, json.dumps({'org': org, 'award': award, 'epoch': nowSec }))
        serv_redis_db.expire('CONTRIB_LAST_AWARDS:'+util.getDateStrFormat(now), ONE_DAY*7) #expire after 7 day
        # publish
        publish_log('GIVE_HONOR_ZMQ', 'CONTRIBUTION', {'org': org, 'award': award, 'epoch': nowSec }, CHANNEL_LASTAWARDS)

if __name__ == '__main__':
    main()
