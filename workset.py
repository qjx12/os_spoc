#! /usr/bin/env python

import sys
from optparse import OptionParser
import random
import math

def hfunc(index):
    if index == -1:
        return 'MISS'
    else:
        return 'HIT '

def vfunc(victimset):
    if len(victimset) == 0:
        return '-'
    else:
        return str(victimset)

#
# main program
#
parser = OptionParser()
parser.add_option('-a', '--addresses', default='-1',   help='a set of comma-separated pages to access',  action='store', type='string', dest='addresses')
parser.add_option('-p', '--policy', default='WorkingSet',    help='replacement policy: WorkingSet',                action='store', type='string', dest='policy')
parser.add_option('-w', '--windowlength', default=3,      help='Window length for WorkingSet policy',                          action='store', type='int', dest='windowlength')
parser.add_option('-f', '--pageframesize', default=5,    help='size of the physical page frame, in pages',                         action='store', type='int', dest='pageframesize')
parser.add_option('-N', '--notrace', default=False,    help='do not print out a detailed trace',                                     action='store_true', dest='notrace')
parser.add_option('-c', '--compute', default=True,    help='compute answers for me',                                                action='store_true', dest='solve')

(options, args) = parser.parse_args()

print 'ARG addresses', options.addresses
print 'ARG policy', options.policy
print 'ARG windowlength', options.windowlength
print 'ARG pageframesize', options.pageframesize
print 'ARG notrace', options.notrace
print ''

addresses   = str(options.addresses)
pageframesize   = int(options.pageframesize)
policy      = str(options.policy)
notrace     = options.notrace
windowlength = int(options.windowlength)

addrList = []
addrList = addresses.split(',')

if options.solve == False:
    print 'Assuming a replacement policy of %s, and a physical page frame of size %d pages,' % (policy, pageframesize)
    print 'figure out whether each of the following page references hit or miss'

    for n in addrList:
        print 'Access: %d  Hit/Miss?  State of Memory?' % int(n)
    print ''

else:
    if notrace == False:
        print 'Solving...\n'

    # init memory structure
    memory = []
    victimset = []
    workingset = []
    hits = 0
    miss = 0

    if policy == 'WorkingSet':
        leftStr = 'LRU'
        riteStr = 'MRU'
    else:
        print 'Policy %s is not yet implemented' % policy
        exit(1)

    # need to generate addresses
    addrIndex = 0
    for nStr in addrList:
        # first, lookup
        n = int(nStr)
        victimset = []
        try:
            idx = memory.index(n)
            if len(workingset) == windowlength:
                del workingset[0]
            workingset.append(n)
            memory.remove(n)
            memory.append(n)
            hits = hits + 1
        except:
            idx = -1
            miss = miss + 1

        victim = -1        
        if idx == -1:
            # miss, replace?
            # print 'BUG count, pageframesize:', count, pageframesize
            if policy == 'WorkingSet':
                while len(memory):
                    m = memory[0]
                    try:
                        victim = workingset.index(m)
                        if len(memory) == pageframesize:
                            del memory[0] 
                            victimset.push(m)
                        break
                    except:
                        del memory[0]
                        victimset.append(m)
                memory.append(n)
                if len(workingset) == windowlength:
                    del workingset[0]
                workingset.append(n)

        if notrace == False:
            print str(workingset)
            print 'Access: %d  %s %s -> %12s <- %s Replaced:%s [Hits:%d Misses:%d]' % (n, hfunc(idx), leftStr, memory, riteStr, vfunc(victimset), hits, miss)
        addrIndex = addrIndex + 1
        
    print ''
    print 'FINALSTATS hits %d   misses %d   hitrate %.2f' % (hits, miss, (100.0*float(hits))/(float(hits)+float(miss)))
    print ''


