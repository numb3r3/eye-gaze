#!/usr/bin/env python
#-*- coding: utf-8 -*-

'''
Copyright (c) 2014 Feng Wang <wangfelix87@gmail.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
'''

import sys, os

import numpy as np

from optparse import OptionParser

from utils import *
from data import *

from constraint import *


def filter_skyline(pid, pids, pdb):
    new_pids = []
    prd = pdb[pid]
    for id in pids:
        id = id.strip()
        if len(id) == 0: continue
        cp = pdb[id.strip()]
        for k in value_keys:
            if k in ['price', 'weight']:
                if cp[k] > prd[k]:
                    new_pids.append(id)
                    break
            else:
                if cp[k] < prd[k]:
                    new_pids.append(id)
                    break

    return new_pids

def main():
    usage = "usage prog [options] arg"
    parser = OptionParser(usage=usage)
    parser.add_option("-s", "--session", dest="session_file",
        help="the input file")
    parser.add_option("-p", "--prds", dest="prds_file",
        help="the product file")
    parser.add_option("-a", "--att", dest="atts_file",
        help="the att file")
    parser.add_option('-c', "--cmd", dest="cmd", help="the compaired prds")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose")
    parser.add_option("-q", "--quiet", action="store_false", dest="verbose")

    (options, remainder) = parser.parse_args()

    atts = load_atts(options.atts_file)
    print 'att: %d' % len(atts)

    prds = load_prds(options.prds_file, atts)
    print 'prds: %d' % len(prds)

    for k in value_keys:
        at = atts[k]
        at['max'] = 0.0
        at['min'] = 10000

    for pid, prd in prds.items():
        for k in value_keys:
            v = prd[k]
            at = atts[k]
            if v > at['max']:
                at['max'] = v
            if v < at['min']:
                at['min'] = v
    for k in value_keys:
        at = atts[k]
        at['range'] = at['max'] - at['min']

    # pprint.pprint(atts)

    cmd = options.cmd
    output = open('crit_perform_%s.txt' % cmd, 'w')

    hits = {}
    ground_hits = {}
    pred_hits = {}

    valids = 0

    for line in open(options.session_file, 'r'):
        items = line.strip().split(',')
        crit_pid = items[2]
        viewed_pids = items[23].split('::')
        disp_pids = items[-4].split('::')


        crits = items[24:34]
        new_crits = []
        for i, k in enumerate(att_keys):
            if k in value_keys:
                new_crits.append(crits[i].strip())
        crits = new_crits


        cmd = options.cmd
        if cmd == 'disp':
            for i in disp_pids:
                if i not in viewed_pids:
                    viewed_pids.append(i)


        prd = prds[crit_pid]
        cs = prd_scores(prd, atts)

        # cm_prds = [prds[pid.strip()] for pid in viewed_pids]
        print 'o: %d, ' % len(viewed_pids),
        cm_pids = filter_skyline(crit_pid, viewed_pids, prds)
        print 'n: %d' % len(cm_pids)

        cm_prds = [prds[pid.strip()] for pid in cm_pids]


        prob = Problem()
        prob.addVariable("w0", range(1, 6))
        prob.addVariable("w1", range(1, 6))
        prob.addVariable("w2", range(1, 6))
        prob.addVariable("w3", range(1, 6))
        prob.addVariable("w4", range(1, 6))
        prob.addVariable("w5", range(1, 6))
        prob.addVariable("w6", range(1, 6))

        for p in cm_prds:
            vs = prd_scores(p, atts)
            df = np.array(cs) - np.array(vs)
            prob.addConstraint(lambda w0, w1, w2, w3, w4, w5, w6: w0 * df[0] + w1*df[1] + w2*df[2] + w3*df[3] + w4*df[4] + w5*df[5] + w6*df[6] > 0)
        solutions = prob.getSolutions()
        print 'len: %d'% len(solutions)

        if len(solutions) == 0:
            print 'Oops'
            continue

        valids += 1
        # print solutions[0]

        # Borda rank aggregation
        rank = {}
        for s in prob.getSolutions():
            # o = order_dict(s)
            ws = np.array([v for k, v in s.items()])
            for wk, wv in s.items():
                if wk not in rank:
                    rank[wk] = sum(ws < wv)
                else:
                    rank[wk] += sum(ws < wv)

        ats = order_dict(rank)[::-1]
        print ats
        preds = ['='] * 7
        for i, a in enumerate(ats):
            ai = int(a[-1])
            # ak = value_keys[ai]
            #
            # ow.append(ak)
            if i <= 1:
                preds[ai] = '='
            elif i >= 5:
                preds[ai] = '-'
            else:
                preds[ai] = '+'

        auc = 0
        for i in range(len(crits)):
            gt = crits[i]
            pt = preds[i]
            if crits[i] == preds[i]:
                auc += 1
                if gt not in hits: hits[gt] = 0.0
                hits[gt] += 1.0
            if gt not in ground_hits: ground_hits[gt] = 0.0
            if pt not in pred_hits: pred_hits[pt] = 0.0

            ground_hits[gt] += 1.0
            pred_hits[pt] += 1
            output.write('(%s|%s) ' % (crits[i], preds[i]))
            print '(%s|%s) ' % (crits[i], preds[i]),
        print ' %d' % auc
        output.write(' %d\n' % auc)

    tp = 0.0
    tr = 0.0
    tf = 0.0

    for t in ['=', '+', '-']:
        p = hits[t]/pred_hits[t]
        r = hits[t]/ground_hits[t]
        f = 2 * (p * r) / (p + r)

        tp += p
        tr += r
        tf += f

        print '%s: p: %.3f, r: %.3f, f1: %.3f' % (t, p, r, f)
        output.write('%s: p: %.3f, r: %.3f, f1: %.3f\n' % (t, p, r, f))
    tp = tp / 3.0
    tr = tr / 3.0
    print 'p: %.3f, r: %.3f, f1: %.3f' % (tp, tr, 2 * (tp * tr) / (tp + tr))
    output.write('p: %.3f, r: %.3f, f1: %.3f\n' % (tp, tr, 2 * (tp * tr) / (tp + tr)))
    hit_ratio = sum([hits[t] for t in ['=', '+', '-']]) / (valids * 7 + 0.0)
    print 'Session: %d' % valids
    print 'Hit Ratio: %.3f' % hit_ratio

    output.write('Session: %d, hit ratio: %.3f' % (valids, hit_ratio))
    output.close()

if __name__ == '__main__':
    main()
