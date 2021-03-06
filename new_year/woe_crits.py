#!/usr/bin/env python
#-*- coding: utf-8 -*-

import sys, os
import math
import json
import xml.etree.ElementTree as ET

from optparse import OptionParser

from utils import *

import pprint
import matplotlib.pyplot as plt
import matplotlib

import random

import scipy.stats

att_keys = ['price', 'manufacturer', 'operating_system',
            'battery_life', 'display_size', 'hard_drive_capacity',
            'installed_memory', 'processor_class', 'processor_speed',
            'weight']

value_keys = ["price",  "battery_life",
        "display_size", "hard_drive_capacity", "installed_memory",
        "processor_speed", "weight"]

def load_prds(filepath, att_filepath):
    # print att_filepath
    atts = json.load(open(att_filepath, 'r'))
    prd_container = {}
    tree = ET.parse(filepath)
    # for dirname, dirnames, filenames in os.walk(container_path):
    #         for filename in filenames:
    #             file_path = os.path.join(dirname, filename)
    #             tree = ET.parse(file_path)
    #             root = tree.getroot()
    root = tree.getroot()

    for child in root:
        prd = {}
        for item in child:
            tag = item.tag
            if tag == 'id':
                prd['id'] = item.text
            elif tag == 'price':
                prd['price'] = float(item.text)
            elif tag == 'brand':
                prd['name'] = item.text
            elif tag == 'manufacturer':
                prd['manufacturer'] = item.text
            elif tag == 'operating_system':
                prd['operating_system'] = item.text
            elif tag == 'battery_life':

                if item.text is None:
                    prd['battery_life'] = atts[tag]['default']
                else:
                    prd['battery_life'] = float(item.text)
            elif tag == 'display_size':
                prd['display_size'] = float(item.text)
            elif tag == 'hard_drive_capacity':
                if item.text is None:
                    prd['hard_drive_capacity'] = atts[tag]['default']
                else:
                    prd['hard_drive_capacity'] = float(item.text)
            elif tag == 'installed_memory':
                prd['installed_memory'] = float(item.text)
            elif tag == "processor_class":
                prd['processor_class'] = item.text
            elif tag == "processor_speed":
                prd['processor_speed'] = float(item.text)
            elif tag == "weight":
                if item.text is None:
                    prd['weight'] = atts[tag]['default']
                else:
                    prd['weight'] = float(item.text)

        prd_container[prd['id']] = prd

    return prd_container

def zip(a):
    list = []
    for i, x in enumerate(a):
        for j, y in enumerate(a):
            if i == j: continue
            list.append((x, y))
    return list

def parse_session(session, pdb, sid, sname, woe, crit_counts):
    if sid in [9, 19, 73, 89, 90]:
        return False
    # print '%d,%s' % (sid, sname),

    stype = 1
    if sid in [7, 9, 11, 14, 17, 19, 23, 27, 31, 33,
                37, 39, 50, 53, 55, 60, 64, 66, 67,
                68, 70, 71, 73, 74, 88, 89, 90, 93]:
        stype = 3


    viewed_pids = []
    critiqued_pid = session[-1][31] # the last one
    displayed_pids = []

    fix_freqs = {}
    fix_ds = {}
    for k in att_keys:
        fix_freqs[k] = 0
        fix_ds[k] = 0

    cts = {}
    cts_types = {}

    for i, items in enumerate(session):
        if i == 0:
            displayed_pids = items[-1].split('::')
            new_disps = []
            for pid in displayed_pids:
                if pid == '100':
                    pid = '81'

                new_disps.append(pid)
            displayed_pids = new_disps

        pid = items[2]
        if pid == '100':
            pid = '81'
        if pid not in viewed_pids:

            viewed_pids.append(pid)

        # fixation data
        att_fixated = items[5:15]
        d = float(items[17]) # duration

        if '1' in att_fixated:
            fi = att_fixated.index('1')
            ak = att_keys[fi]

            if ak not in fix_freqs:
                fix_freqs[ak] = 1.0
                fix_ds[ak] = d
            else:
                fix_freqs[ak] += 1.0
                fix_ds[ak] += d

        # critiques
        critique_pid = items[31]
        if len(critique_pid) > 0: # the last line
            critiques = items[19:29]
            for ci, c in enumerate(critiques):
                ck = att_keys[ci]
                cts[ck] = c

                ctype = '='

                if stype == 1:
                    if c.startswith("<>"):
                        ctype = '+'
                    elif c.startswith("any"):
                        ctype = 'a'

                    elif c.startswith('>'):
                        if ck in ['price', 'weight']:
                            ctype = '-'
                        else:
                            ctype = '+'
                    elif c.startswith('<'):
                        if ck in ['price', 'weight']:
                            ctype = '+'
                        else:
                            ctype = '-'
                    else:
                        ctype = '='

                else:
                    if c.startswith('>') or c.startswith('<'):
                        ctype = '+'
                    elif c.startswith('any'):
                        ctype = 'a'
                    else:
                        ctype = '='

                if ctype == 'a':
                    ctype = '-'

                cts_types[ck] = ctype
            break

    # value levels
    top = pdb[critique_pid]
    prds = [pdb[pid] for pid in viewed_pids if len(pid)> 0]

    # print ',%s,' % critique_pid,

    v_levels = {}

    cates = ['manufacturer', 'operating_system',
                        'processor_class'
                    ]
    for k in att_keys:
        value_levels = [0, 0, 0]
        av = top[k]

        if k in cates:
            v_level = 4
            v_levels[k] = v_level
            continue

        if k not in ['price', 'weight']:
            for v in [p[k] for p in prds]:
                if av >= v:
                    value_levels[0] += 1

                if av <= v:
                    value_levels[2] += 1
        else:
            for v in [p[k] for p in prds]:
                if av <= v:
                    value_levels[0] += 1

                if av >= v:
                    value_levels[2] += 1

        if value_levels[0] == len(prds):
            v_level = 1
        elif value_levels[2] == len(prds):
            v_level = 3
        else:
            v_level = 2


        v_levels[k] = v_level

    # fix_freqs = fix_ds
    # fix_levels = group_levels(fix_freqs, 3)
    fix_levels = group_2levels(fix_freqs, 2)

    # print '%s,' % ','.join(['%d' % int(fix_freqs[k]) for k in att_keys]),
    # print '%s,' % ','.join(['%d' % int(fix_ds[k]) for k in att_keys]),
    # print '%s,' % '::'.join(viewed_pids)

    cts = []
    for k in att_keys:

        cl = v_levels[k]
        ct = cts_types[k]
        fl = fix_levels[k]

        if ct not in cts:
            cts.append(ct)
            crit_counts[ct] += 1

    for x, y in zip(cts):
        woe[x][y] += 1.0

    return True

def main():
    usage = "usage prog [options] arg"
    parser = OptionParser(usage=usage)
    parser.add_option("-i", "--input", dest="input",
        help="the input file")
    parser.add_option("-p", "--prd", dest="prd", help="the prd file")
    parser.add_option("-a", "--att", dest="att", help="the att file")

    parser.add_option("-o", "--output", dest="output",
                  help="write out to DIR")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose")
    parser.add_option("-q", "--quiet", action="store_false", dest="verbose")

    (options, remainder) = parser.parse_args()

    input = open(options.input, 'r')

    index = 0
    session = []
    sname = ''

    pdb = load_prds(options.prd, options.att)

    id = 0
    hit = False

    woe = {}
    for cx, cy in zip(['=', '+', '-']):
        if cx not in woe:
            woe[cx] = {}
        woe[cx][cy] = 0.0

    crit_counts = {}

    for ct in ['=', '+', '-']:
        crit_counts[ct] = 0.0

    for line in input:
        line = line.strip()
        if index == 0: # header
            index += 1
            # print line
            continue

        items = line.strip().split(',')
        if items[0].startswith("Session"): # session begin

            if len(items[-1]) > 5:
                cpids = items[-1].split('::')
                hit = True

            else:
                hit =False

            if len(session) > 0: # WARNING: 1st session
                # process session
                sid = int(sname[8:])

                id += 1
                if not parse_session(session, pdb, sid, sname, woe, crit_counts):
                    id -= 1



            if hit:
                session = [items] # append the first record for the next sesssion
                sname = items[0]
            else:
                session = []

        if hit:
            if not items[0].startswith("Session"):
                session.append(items)


    print 'WOE'

    for cx, cy in zip(['=', '+', '-']):
        ph = crit_counts[cx]/38.0
        oh = ph / (1.0 - ph)

        phe = woe[cx][cy]/crit_counts[cy]

        if (1.0 - phe) < 0.0001:
            print 'woe(%s | %s) = %s' % (cx, cy, '+++')
            continue
        ohe = phe / (1.0 - phe)

        w = math.log(ohe/oh)
        print 'woe(%s | %s) = %.3f, %.3f (h=%d, he=%d)' % (cx, cy, phe, w, crit_counts[cx], woe[cx][cy])





if __name__ == '__main__':
    main()
