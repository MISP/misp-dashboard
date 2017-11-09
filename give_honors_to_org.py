#!/usr/bin/env python3.5

import os, sys
import redis
import configparser

import contributor_helper

configfile = os.path.join(os.environ['DASH_CONFIG'], 'config.cfg')
cfg = configparser.ConfigParser()
cfg.read(configfile)
serv_redis_db = redis.StrictRedis(
        host=cfg.get('RedisGlobal', 'host'),
        port=cfg.getint('RedisGlobal', 'port'),
        db=cfg.getint('RedisDB', 'db'))

chelper = contributor_helper.Contributor_helper(serv_redis_db, cfg)

def printOrgInfo(org):
    org_pnts = chelper.getOrgContributionTotalPoints(org)
    org_c_rank = chelper.getOrgContributionRank(org)
    org_c_status = chelper.getCurrentContributionStatus(org)
    org_honor_badge = chelper.getOrgHonorBadges(org)

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


def main():
    if len(sys.argv) > 1:
        org = sys.argv[1]
    else:
        org = input('Enter the organisation name: ')
    
    printOrgInfo(org)

    # ranks
    while True:
        org_pnts = chelper.getOrgContributionTotalPoints(org)
        org_c_rank = chelper.getOrgContributionRank(org)
        org_c_status = chelper.getCurrentContributionStatus(org)
        org_honor_badge = chelper.getOrgHonorBadges(org)

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
            if rankNum < 1 and rankNum > chelper.org_rank_maxLevel:
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

if __name__ == '__main__':
    main()

