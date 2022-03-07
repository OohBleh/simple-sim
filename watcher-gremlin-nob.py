import random
import math
import queue
from enum import Enum
from itertools import product
from itertools import permutations
from itertools import combinations

#   NEW PLAN
#   Global manager:
#       turn, deck shuffle permutation
#       list of all queues
#   Current queues, next sets:
#       1 queue for each combination of:
#           current CardPositions (draw/hand/discard), 
#           WatcherState (stance, hasMiracle), 
#           and gnBuff
#           this is enough to compute how a sequence of card plays affects...
#               CardPositions, WatcherState, and CombatState
#       queue entries are current CombatStates (pHP, gnHP, gnBuff)
#       
#       1 set for each combination of:
#           next turn CardPositions, stance
#
#       process a queue at a time:
#           list possible moves
#           for each possible move, hash the following:
#               CardPositions for next turn, 
#               WatcherState for next turn, and 
#               change to CombatState

#           for each queue entry:
#               apply each possible move
#               try to add the result to the corresponding set
#               within this set, CardPositions and stances are all the same
#               compare CombatState and hasMiracle
#           
#       populate new queues from the sets that resulted, repeat    

#   CombatState:
#       (pHP, gnHP, gnBuff)
#   CardPositions:
#       (draw, hand, discard)
#   WatcherState:
#       (stance, hasMiracle)

#################  #################
class Card(Enum):
    NONE = 0
    STRIKE = 1
    DEFEND = 2
    ERUPTION = 3
    VIGILANCE = 4
    ASCENDERS_BANE = 5

START_DECK = tuple([Card.STRIKE, Card.DEFEND]*4+[Card.ERUPTION, Card.VIGILANCE, Card.ASCENDERS_BANE])
        

class CardPositions:
    def __init__(self, draw = [], hand = [], discard = START_DECK):
        self.draw = tuple(draw)
        self.hand = tuple(hand)
        self.discard = tuple(discard)
    
    # apply a permutation to get the next hand
    # length of sigma assumed to equal self.discard
    def nextPositions(self, sigma):
        newDraw = list(self.draw)
        if len(self.draw) < 5:
            newDraw += [self.discard[sigma[i]] for i in range(len(self.discard))]
            newDiscard = []
        else:
            newDiscard = self.discard
        newHand = newDraw[:5]
        newDraw = newDraw[5:]
        return CardPositions(newDraw, newHand, newDiscard)

class CombatState:
    def __init__(self, pHP = 61, gnHP = 106, gnBuff = 0):
        self.pHP = pHP
        self.gnHP = gnHP
        self.gnBuff = gnBuff

class Stance(Enum):
    NONE = 0
    NEUTRAL = 1
    WRATH = 2
    CALM = 3
STANCES = tuple([Stance.NEUTRAL, Stance.WRATH, Stance.CALM])

class WatcherState:
    def __init__(self, stance = Stance.NEUTRAL, hasMiracle = True):
        self.stance = stance
        self.hasMiracle = hasMiracle
WATCHER_STATES = []
for stance in STANCES:
    WATCHER_STATES.append(WatcherState(stance = stance, hasMiracle = True))
    WATCHER_STATES.append(WatcherState(stance = stance, hasMiracle = False))
WATCHER_STATES = tuple(WATCHER_STATES)

################# START OF PRE-COMPUTED DATA #################
# for each 5-card hand, store all playable card sequences
#   there are 4 sets -- starts in calm (T/F), has miracle (T/F)
# for each playable card sequences, store the "results"
#   e.g., damage dealt, ending stance, block, and changes to gnBuff

def playResult(cardSeq, watcherState):
    E = 3
    damage = 0
    block = 0
    buffGain = 0
    stance = watcherState.stance
    hasMiracle = watcherState.hasMiracle
    
    for card in cardSeq:
        if card is Card.STRIKE:
            if E < 1:
                if hasMiracle:
                    E += 1
                    hasMiracle = False
                else:
                    return
            E -= 1
            if stance == Stance.WRATH:
                damage += 12
            else:
                damage += 6
        
        elif card is Card.DEFEND:
            if E < 1:
                if hasMiracle:
                    E += 1
                    hasMiracle = False
                else:
                    return
            E -= 1
            block += 5
            buffGain = 3
        
        elif card is Card.ERUPTION:
            if E < 2:
                if hasMiracle:
                    E += 1
                    hasMiracle = False
                else:
                    return
            if E < 2:
                return
            E -= 2
            if stance == Stance.WRATH:
                damage += 18
            else:
                if stance == Stance.CALM:
                    E += 2
                damage += 9    
            stance = Stance.WRATH
        
        elif card is Card.VIGILANCE:
            if E < 2:
                if hasMiracle:
                    E += 1
                    hasMiracle = False
                else:
                    return
            if E < 2:
                return
            E -= 2
            block += 8
            stance = Stance.CALM
            buffGain += 3
    endWatcherState = WatcherState(stance = stance, hasMiracle = hasMiracle)
    return endWatcherState, damage, block, buffGain

PLAYABLE_CARDS = tuple([Card.STRIKE, Card.DEFEND, Card.ERUPTION, Card.VIGILANCE])
ALL_CARDS = tuple([Card.STRIKE, Card.DEFEND, Card.ERUPTION, Card.VIGILANCE, Card.ASCENDERS_BANE])
PC = PLAYABLE_CARDS
AC = ALL_CARDS

# key = sequence of card plays & WatcherStates
# value = 4-tuple with play results
PLAYS = dict()
for play in product(PC,PC,PC,PC,PC):
    for wstate in WATCHER_STATES:
        out = playResult(play, wstate)
        if out != None:
            PLAYS[(play, wstate)] = out

for play in product(PC,PC,PC,PC):
    for wstate in WATCHER_STATES:
        out = playResult(play, wstate)
        if out != None:
            PLAYS[(play, wstate)] = out

for play in product(PC,PC,PC):
    for wstate in WATCHER_STATES:
        out = playResult(play, wstate)
        if out != None:
            PLAYS[(play, wstate)] = out

for play in product(PC,PC):
    for wstate in WATCHER_STATES:
        out = playResult(play, wstate)
        if out != None:
            PLAYS[(play, wstate)] = out

for play in product(PC):
    for wstate in WATCHER_STATES:
        out = playResult(play, wstate)
        if out != None:
            PLAYS[(play, wstate)] = out

NULL_TUPLE = tuple()
for wstate in WATCHER_STATES:
    out = playResult(NULL_TUPLE, wstate)
    if out != None:
        PLAYS[(play, wstate)] = out

print("plays:", len(PLAYS))
dels = []
for p,w in PLAYS:
    nE,nV = 0,0
    for c in p:
        if c is Card.ERUPTION:
            nE += 1
        elif c is Card.VIGILANCE:
            nV += 1
    if nE > 1 or nV > 1:
        dels.append((p,w))
for p,w in dels:
    PLAYS.pop((p,w))
print("plays:", len(PLAYS))

# key = possible 5-card hands, WatcherStates
# value = all possible discard orders, play results (as above)


ctr = 0
for hand in combinations(START_DECK, 5):
    ctr += 1
print("ctr =", ctr)



HANDS = dict()
for hand in product(AC, AC, AC, AC, AC):
    nE = 0
    nV = 0
    nA = 0
    nS = 0
    nD = 0
    for c in hand:
        if c is Card.ERUPTION:
            nE += 1
        elif c is Card.VIGILANCE:
            nV += 1
        elif c is Card.ASCENDERS_BANE:
            nA += 1
        elif c is Card.STRIKE:
            nS += 1
        elif c is Card.DEFEND:
            nD += 1
    if nE < 2 and nV < 2 and nA < 2 and nS < 5 and nD < 5:
        for wstate in WATCHER_STATES:
            HANDS[(hand, wstate)] = set()
            for k in range(6):
                for sigma in permutations(range(5), k):
                    play = [hand[si] for si in sigma]
                    out = playResult(play, wstate)
                    if out != None:
                        # out = endWatcherState, damage, block, buffGain
                        discardOrder = tuple(play + [hand[i] for i in range(5) if not i in sigma])
                        HANDS[(hand, wstate)].add((discardOrder, out[0], out[1], out[2], out[3]))

ctr = 0
for hand in HANDS:
    ctr += len(HANDS[hand])
print("hands:", len(HANDS), ctr)
################# END OF PRE-COMPUTED DATA #################


class StateManager:
    def __init__(self, pHP = 61, gnHP = 106, startDeck = START_DECK):
        self.turn = 0
        shuffler = random.Random()
        sigma = range(len(startDeck))
        
        startPositions = CardPositions(discard = startDeck)
        startWatcher = WatcherState()
        startCombat = CombatState(pHP = pHP, gnHP = gnHP)
        
        self.StateQueue = queue.Queue()
        
#################  #################





