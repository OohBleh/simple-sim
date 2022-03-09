import random
import math
import queue
from enum import Enum
from itertools import product
from itertools import permutations
from itertools import combinations

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

CARDS = [Card.NONE, Card.STRIKE, Card.DEFEND, Card.ERUPTION, Card.VIGILANCE, Card.ASCENDERS_BANE]
CARD_NAMES = ['none', 'S', 'D', 'E', 'V', 'A']
START_DECK = tuple([Card.STRIKE]*4+[Card.DEFEND]*4+[Card.ERUPTION,Card.VIGILANCE,Card.ASCENDERS_BANE])

class CardPositions:
    def __init__(self, draw = [], hand = [], discard = START_DECK):
        self._draw = tuple(draw)
        self._hand = tuple(hand)
        self._discard = tuple(discard)
    
    @property
    def draw(self):
        return self._draw
    @property
    def hand(self):
        return self._hand
    @property
    def discard(self):
        return self._discard
    
    def __eq__(self, other):
        return isinstance(other, CardPositions) and self._draw == other._draw and self._hand == other._hand and self._discard == other._discard
    def __hash__(self):
        return hash((self.draw, self.hand, self.discard))
    
    def __str__(self):
        out = ''
        for card in self.draw:
            out += CARD_NAMES[card.value]
        out += '|'
        for card in self.hand:
            out += CARD_NAMES[card.value]
        out += '|'
        for card in self.discard:
            out += CARD_NAMES[card.value]
        return out
    
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
        self._pHP = pHP
        self._gnHP = gnHP
        self._gnBuff = gnBuff
    @property
    def pHP(self):
        return self._pHP
    @property
    def gnHP(self):
        return self._gnHP
    @property
    def gnBuff(self):
        return self._gnBuff
    
    def __eq__(self, other):
        return isinstance(other, CombatState) and self.pHP == other.pHP and self.gnHP == other.gnHP and self._gnBuff == other._gnBuff
    def __hash__(self):
        return hash((self.pHP, self.gnHP, self.gnBuff))
    
    def __str__(self):
        return f'pHP = {self.pHP}, gnHP = {self.gnHP}, gnBuff = {self.gnBuff}'

class Stance(Enum):
    NONE = 0
    NEUTRAL = 1
    WRATH = 2
    CALM = 3
STANCES = [Stance.NONE, Stance.NEUTRAL, Stance.WRATH, Stance.CALM]
STANCE_NAMES = ['none', 'neutral', 'wrath', 'calm']

class WatcherState:
    def __init__(self, stance = Stance.NEUTRAL, hasMiracle = True):
        self._stance = stance
        self._hasMiracle = hasMiracle
    
    @property
    def stance(self):
        return self._stance
    @property
    def hasMiracle(self):
        return self._hasMiracle
    
    def __eq__(self, other):
        return isinstance(other, WatcherState) and self.stance is other.stance and self.hasMiracle is other.hasMiracle
    def __hash__(self):
        return hash((self.stance, self.hasMiracle))
    def __str__(self):
        if self.hasMiracle:
            return STANCE_NAMES[self.stance.value] + ', 1 miracle'
        else:
            return STANCE_NAMES[self.stance.value] + ', 0 miracle' 



#ws1 = WatcherState()
#ws2 = WatcherState()
#wset = set([(Card.STRIKE, ws1)])
#print("hashed correctly?", (Card.STRIKE, ws2) in wset)

WATCHER_STATES = []
for stance in STANCES[1:]:
    WATCHER_STATES.append(WatcherState(stance = stance, hasMiracle = True))
    WATCHER_STATES.append(WatcherState(stance = stance, hasMiracle = False))
WATCHER_STATES = tuple(WATCHER_STATES)

################# START OF PRE-COMPUTED DATA #################
# for each 5-card hand, store all playable card sequences
#   there are 6 WatcherStates -- starting stance, has miracle (T/F)
# for each playable card sequences, store the "results"
#   e.g., order added to discard pile, damage dealt, ending stance, 
#   block, and changes to gnBuff

def playResult(cardSeq, watcherState):
    E = 3
    damage = 0
    block = 0
    buffGain = 0
    stance = watcherState.stance
    hasMiracle = watcherState.hasMiracle
    
    for card in cardSeq:
        if card is Card.ASCENDERS_BANE:
            return 
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

def handResults(hand, wstate):
    results = set()
    for k in range(6):
        for sigma in permutations(range(5), k):
            play = [hand[si] for si in sigma]
            out = playResult(play, wstate)
            if out != None:
                # out = endWatcherState, damage, block, buffGain
                discardOrder = tuple(play + [hand[i] for i in range(5) if not i in sigma
                and not hand[i] is Card.ASCENDERS_BANE])
                results.add(tuple([discardOrder]) + out)
    return results

def memorizeHands(myDeck = START_DECK):
    HANDS = dict()
    for hand in permutations(myDeck, 5):
        for wstate in WATCHER_STATES:
            if not (hand, wstate) in HANDS:
                HANDS[(hand, wstate)] = handResults(hand, wstate)
    return HANDS

STANCE_COMPARE = dict()
def setStanceCompare():
    for stance in STANCES:
        STANCE_COMPARE[(stance, stance)] = (True, True)
        if not (stance is Stance.WRATH):
            STANCE_COMPARE[(Stance.WRATH, stance)] = None
            STANCE_COMPARE[(stance, Stance.WRATH)] = None
    STANCE_COMPARE[(Stance.NEUTRAL, Stance.CALM)] = (True, False)
    STANCE_COMPARE[(Stance.CALM, Stance.NEUTRAL)] = (False, True)
setStanceCompare()

WATCHER_STATE_COMPARE = dict()
def setWatcherStateCompare():    
    for ws1 in WATCHER_STATES:
        for ws2 in WATCHER_STATES:
            out = STANCE_COMPARE[(ws1.stance, ws2.stance)]
            if out is None:
                WATCHER_STATE_COMPARE[(ws1, ws2)] = None
            else:
                lesser, greater = out
                lesser = lesser and ((not ws1.hasMiracle) or ws2.hasMiracle)
                greater = greater and ((not ws2.hasMiracle) or ws1.hasMiracle)
                if lesser or greater:
                    WATCHER_STATE_COMPARE[(ws1, ws2)] = (lesser, greater)
                else:
                    WATCHER_STATE_COMPARE[(ws1, ws2)] = None
setWatcherStateCompare()
################# END OF PRE-COMPUTED DATA #################

# None: states incomparable
# True: state1 <= state2
# False: state1 > state2
def compareStates(state1, state2):
    ws1, gs1 = state1
    ws2, gs2 = state2
    
    out = WATCHER_STATE_COMPARE[(ws1, ws2)]
    if out is None:
        return
    
    lesser = out[0] and (gs1.pHP <= gs2.pHP) and (gs1.gnHP >= gs2.gnHP) and (gs1.gnBuff >= gs2.gnBuff)
    if lesser:
        return True
    
    greater = out[1] and (gs2.pHP <= gs1.pHP) and (gs2.gnHP >= gs1.gnHP) and (gs2.gnBuff >= gs1.gnBuff)
    if greater:
        return False
    return 

# 

class StateManager:
    def __init__(self, pHP = 61, gnHP = 106, startDeck = START_DECK, verbose = False):
        self._turn = 0
        self._shuffler = random.Random()
        self._verbose = verbose
        self._winnable = None
        
        startPositions = CardPositions(discard = startDeck)
        startWatcher = WatcherState()
        startCombat = CombatState(pHP = pHP, gnHP = gnHP)
        self.drawPileSize = len(startPositions.draw)
        self.discardPileSize = len(startPositions.discard)
        
        # group CombatStates by CardPositions & stance
        self._stateDictionary = dict()
        self._stateDictionary[startPositions] = set([(startWatcher, startCombat)])
    
    @property
    def numStates(self):
        ctr = 0
        for elt in self.stateDictionary:
            ctr += len(self.stateDictionary[elt])
        return ctr
    @property
    def stateDictionary(self):
        return self._stateDictionary
    @property
    def winnable(self):
        return self._winnable
    @property
    def turn(self):
        return self._turn
    @property
    def verbose(self):
        return self._verbose
    
    def setWinnable(self, value):
        self._winnable = value
    def nextTurn(self):
        if len(self.stateDictionary) == 0:
            return 
        
        self._turn += 1
        
        if self.drawPileSize < 5:
            sigma = [i for i in range(self.discardPileSize)]
            self._shuffler.shuffle(sigma)
        else:
            sigma = None
        
        if self.verbose:
            print("turn", self.turn, "shuffle =", sigma)
        nextDict = dict()
        
        for pos in self.stateDictionary:
            currPos = pos.nextPositions(sigma)
            if self.verbose:
                print(pos, "draws into", currPos)
            for (ws, cs) in self.stateDictionary[pos]:
                if self.verbose:
                    print("  ws =", ws, "; cs =", cs, "...")
                
                hr = HANDS[(currPos.hand, ws)]
                for out in hr:
                    if self.verbose:
                        discardString = ''
                        for card in out[0]:
                            discardString += CARD_NAMES[card.value]
                        print("    result =", discardString, out[1], 
                        out[2:], "...")
                    
                    # out = (discardOrder, endWatcherState, damage, block, buffGain)
                    nextPos = CardPositions(draw = currPos.draw, hand = [], 
                    discard = currPos.discard + out[0])
                    nextWS = out[1]
                    newGNHP = cs.gnHP - out[2]
                    
                    if self.turn == 1:
                        nextCS = CombatState(pHP = cs.pHP, gnHP = newGNHP)
                    else:
                        nextBuff = cs.gnBuff + out[4]
                        if self.turn % 3 == 2:
                            lostHP = 8 + nextBuff
                            if nextWS.stance is Stance.WRATH:
                                lostHP *= 2
                        else:
                            lostHP = 16 + nextBuff
                            if nextWS.stance is Stance.WRATH:
                                lostHP *= 3
                            else:
                                lostHP = int(1.5*lostHP)
                            lostHP -= out[3]
                            if lostHP < 0:
                                lostHP = 0
                        nextCS = CombatState(pHP = cs.pHP - lostHP, 
                        gnHP = newGNHP, gnBuff = nextBuff)
                    
                    if self.verbose:
                        print("    results in:", nextPos, nextWS, nextCS)
                    
                    if nextCS.gnHP <= 0:
                        self.setWinnable(True)
                        
                    if nextCS.pHP > 0:
                        nextState = (nextWS, nextCS)
                        if not nextPos in nextDict:
                            nextDict[nextPos] = set()
                        pops = []
                        less = False
                        for otherState in nextDict[nextPos]:
                            comp = compareStates(nextState, otherState)
                            if comp is True:
                                less = True
                            else:
                                if comp is False:
                                    pops.append(otherState)
                        if pops:
                            #print("nextState =", nextState[0].stance, nextState[0].hasMiracle, 
                            #nextState[1].pHP, nextState[1].gnHP, nextState[1].gnBuff, "beats...")
                            for otherState in pops:
                                nextDict[nextPos].remove(otherState)
                                #print("  otherState =", otherState[0].stance, otherState[0].hasMiracle, 
                                #otherState[1].pHP, otherState[1].gnHP, otherState[1].gnBuff)
                            
                            nextDict[nextPos].add(nextState)
                        else:
                            if less is False:
                                nextDict[nextPos].add(nextState)
                        self.drawPileSize = len(nextPos.draw)
                        self.discardPileSize = len(nextPos.discard)
        
        self._stateDictionary = nextDict
        if len(self._stateDictionary) == 0:
            if self.winnable is None:
                self.setWinnable(False)
        if self.verbose:
            print("number of states:", self.numStates)
        
#################  #################

MY_DECK = tuple([Card.STRIKE]*4+[Card.DEFEND]*4+[Card.ERUPTION,Card.VIGILANCE,Card.ASCENDERS_BANE])
HANDS = memorizeHands(myDeck = MY_DECK)
print("len(HANDS) =", len(HANDS))

def sampleSim(nTrials = 100, pHP = 61, gnHP = 106, verbose = False, startDeck = MY_DECK):
    nWins = 0
    curr = 0
    while curr < nTrials:
        sm = StateManager(pHP = pHP, gnHP = gnHP, verbose = verbose, startDeck = startDeck)
        #print("turn 0 states:", sm.numStates)
        i = 0
        while sm.numStates:
        #while i < 1:
            sm.nextTurn()
            i += 1
            #print("turn", i, "states:", sm.numStates)
        if sm.winnable:
            nWins += 1
            #print("won!")
        curr += 1
        
        if curr % 10 == 0:
            print(nWins, "out of", curr, ":", nWins/curr)
        
        #print()
    
    print(nWins, "out of", nTrials, ":", nWins/nTrials)
    return nWins

NTRIALS = 100
conditions = [(NTRIALS, 61, 106), (NTRIALS, 56, 106), (NTRIALS, 61, 112), (NTRIALS, 56, 112)]

results = dict()
for condition in conditions:
    results[condition] = sampleSim(nTrials = condition[0], pHP = condition[1], gnHP = condition[2])

for condition in conditions:
    print("conditions =", condition, "\tresults:", 
    results[condition], "/", condition[0], "=", results[condition]/condition[0])