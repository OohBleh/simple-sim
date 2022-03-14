import random
import math
import queue
from enum import Enum
from itertools import product
from itertools import permutations
from itertools import combinations

#   Global manager:
#       turn, deck shuffle permutation, 
#       current set of "states"
#   Current sets:
#       organized in dictionary by:
#           stance & current CardPositions (draw/hand/discard)
#           sets elements are pairs of: 
#               WatcherState (stance, nMiracles, nProtects, etc)
#               & CombatState (pHP, gnHP, gnBuff)
#           together, this determines all possible combinations of 
#               CardPositions, WatcherState, and CombatState @ end of turn
#
#   CombatState:
#       (pHP, gnHP, gnBuff)
#   CardPositions:
#       (draw, hand, discard)
#   WatcherState:
#       (stance, nMiracles, nProtects, etc)

#################  #################
class Card(Enum):
    NONE = 0
    STRIKE = 1
    DEFEND = 2
    ERUPTION = 3
    VIGILANCE = 4
    ASCENDERS_BANE = 5
    HALT = 6
    EMPTY_BODY = 7
    PROTECT = 8
    DECEIVE_REALITY = 9
    SAFETY = 10

ALL_CARDS = [Card.NONE, Card.STRIKE, Card.DEFEND, Card.ERUPTION, Card.VIGILANCE, Card.ASCENDERS_BANE, 
Card.HALT, Card.EMPTY_BODY, Card.PROTECT, Card.DECEIVE_REALITY, Card.SAFETY]
CARD_NAMES = ['none', 'S', 'D', 'E', 'V', 'A', 
'H', 'Eb', 'Pr', 'Dr', 'Sf']

UNPLAYABLES = set([Card.NONE, Card.ASCENDERS_BANE])
ETHEREALS = set([Card.ASCENDERS_BANE])
EXHAUSTS = set([Card.SAFETY])
RETAINS = set([Card.PROTECT, Card.SAFETY])

COSTS = dict()
for card in [Card.HALT]:
    COSTS[card] = 0
for card in [Card.STRIKE, Card.DEFEND, 
Card.EMPTY_BODY, Card.DECEIVE_REALITY, Card.SAFETY]:
    COSTS[card] = 1
for card in [Card.ERUPTION, Card.VIGILANCE, Card.PROTECT]:
    COSTS[card] = 2
ATTACKS = set([Card.STRIKE, Card.ERUPTION])

SKILLS = set([Card.DEFEND, Card.VIGILANCE, 
Card.HALT, Card.EMPTY_BODY, Card.PROTECT, Card.DECEIVE_REALITY, Card.SAFETY])

BLOCKS = dict()
BLOCKS[Card.DEFEND] = 5
BLOCKS[Card.VIGILANCE] = 8
BLOCKS[Card.HALT] = 3
BLOCKS[Card.EMPTY_BODY] = 7
BLOCKS[Card.PROTECT] = 12
BLOCKS[Card.DECEIVE_REALITY] = 4
BLOCKS[Card.SAFETY] = 12

POWERS = set([])

START_DECK = tuple([Card.ASCENDERS_BANE]+[Card.STRIKE]*4+[Card.DEFEND]*4+[Card.ERUPTION,Card.VIGILANCE])

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
        if self.draw != other.draw:
            return False
        if self.hand != other.hand:
            return False
        if self.discard != other.discard:
            return False
        return True
    
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
    
    # +
    def __add__(self, other):
        return CombatState(pHP = self.pHP + other.pHP, 
        gnHP = self.gnHP + other.gnHP, 
        gnBuff = self.gnBuff + other.gnBuff)
    
    # <=
    def __le__(self, other):
        if self.pHP > other.pHP:
            return False
        if self.gnHP < other.gnHP:
            return False
        if self.gnBuff < other.gnBuff:
            return False
        return True
    # >=
    def __ge__(self, other):
        return other <= self
    
    # ==
    def __eq__(self, other):
        if self.pHP != other.pHP:
            return False
        if self.gnHP != other.gnHP:
            return False
        if self._gnBuff != other._gnBuff:
            return False
        return True
    # !=
    def __ne__(self, other):
        return not (self == other)
    
    # <
    def __lt__(self, other):
        return self <= other and self != other
    # >
    def __gt__(self, other):
        return other < self
    
    
    def __hash__(self):
        return hash((self.pHP, self.gnHP, self.gnBuff))
    
    def __str__(self):
        return f'pHP = {self.pHP}, gnHP = {self.gnHP}, gnBuff = {self.gnBuff}'

class Stance(Enum):
    NONE = 0
    NEUTRAL = 1
    WRATH = 2
    CALM = 3
    DIVINITY = 4
STANCES = [Stance.NONE, Stance.NEUTRAL, Stance.WRATH, Stance.CALM]#, Stance.DIVINITY]
STANCE_NAMES = ['none', 'neutral', 'wrath', 'calm', 'divinity']

class WatcherState:
    def __init__(self, stance = Stance.NEUTRAL, nMiracles = 1, 
    nProtects = 0, nSafeties = 0):
        self._stance = stance
        self._nMiracles = nMiracles
        self._nProtects = nProtects
        self._nSafeties = nSafeties
    
    @property
    def stance(self):
        return self._stance
    @property
    def nMiracles(self):
        return self._nMiracles
    @property
    def nProtects(self):
        return self._nProtects
    @property
    def nSafeties(self):
        return self._nSafeties
    
    def retainCards(self):
        return [Card.PROTECT]*self.nProtects
    
    # for comparisons...
    # true comparison --> True
    # false comparison --> False
    # incomparable --> False
    
    # <=
    def __le__(self, other):
        # same stance required for comparability
        if self.stance == other.stance:
            # must have fewer of each retainable (incl. Miracle)
            if self.nMiracles > other.nMiracles:
                return False
            if self.nProtects > other.nProtects:
                return False
            if self.nSafeties > other.nSafeties:
                return False
            return True
        else:
            return False
    # >=
    def __ge__(self, other):
        return other <= self
    
    # ==
    def __eq__(self, other):
        if self.stance != other.stance:
            return False
        else:
            if self.nMiracles != other.nMiracles:
                return False
            if self.nProtects != other.nProtects:
                return False
            if self.nSafeties != other.nSafeties:
                return False
            return True
    # !=
    def __ne__(self, other):
        return not (self == other)
    
    # <
    def __lt__(self, other):
        return self <= other and self != other
    # >
    def __gt__(self, other):
        return other < self
    
    def __hash__(self):
        return hash((self.stance, self.nMiracles, self.nProtects, self.nSafeties))
    def __str__(self):
        out = STANCE_NAMES[self.stance.value]
        if self.nMiracles:
            out += ',' + str(self.nMiracles) + ' miracle(s)'
        if self.nProtects:
            out += ',' + str(self.nProtects) + ' protects(s)'
        if self.nSafeties:
            out += ',' + str(self.nSafeties) + ' safet(y/ies)'
        return out

#ws1 = WatcherState()
#ws2 = WatcherState()
#wset = set([(Card.STRIKE, ws1)])
#print("hashed correctly?", (Card.STRIKE, ws2) in wset)

# only the "base" Watcher states
WATCHER_STATES = []
for stance in STANCES[1:]:
    WATCHER_STATES.append(WatcherState(stance = stance, nMiracles = 1))
    WATCHER_STATES.append(WatcherState(stance = stance, nMiracles = 0))
WATCHER_STATES = tuple(WATCHER_STATES)

################# START OF PRE-COMPUTED DATA #################
# for each 5-card hand, store all playable card sequences
#   there are 6 WatcherStates -- starting stance, has miracle (T/F)
# for each playable card sequences, store the "results"
#   e.g., order added to discard pile, damage dealt, ending stance, 
#   block, and changes to gnBuff


## better organization for results from playing a sequence of cards ##
## ... work in progress... ###
class PlayResult:
    # pass in startWatcherState, hand, permutation, etc
    # return object with:
    #   order that cards get added to discard, 
    #   endWatcherState, 
    #   net change to CombatState (block, damage, buffGain)
    #   also store the permutation, but don't use it in comparisons
    # assumes that hand is padded with nProtects copies of Protect
    # same for all retaining cards
    # additionally, hand is padded with one Safety for each Deceive Reailty drawn
    
    def __init__(self, startWatcher, hand, playSeq):
        stance = startWatcher.stance
        nMiracles = startWatcher.nMiracles
        nProtects = startWatcher.nProtects
        nSafeties = startWatcher.nSafeties
        
        block = 0
        damage = 0
        buffGain = 0
        
        E = 3
        self._valid = None
        
        for i in playSeq:
            card = hand[i]
            if card in UNPLAYABLES:
                self._valid = False
                return 
            
            while E < COSTS[card]:
                if nMiracles:
                    E += 1
                    buffGain += 3
                    nMiracles -= 1
                else:
                    self._valid = False
                    return
            
            E -= COSTS[card]
            
            if card in SKILLS:
                buffGain += 3
            if card in BLOCKS:
                block += BLOCKS[card]
            
            if card == Card.STRIKE:
                if stance == Stance.WRATH:
                    damage += 12
                else:
                    damage += 6
            
            #elif card == Card.DEFEND:
            #    block += 5
            
            elif card == Card.ERUPTION:
                if stance == Stance.WRATH:
                    damage += 18
                else:
                    if stance == Stance.CALM:
                        E += 2
                    damage += 9    
                stance = Stance.WRATH
            
            elif card == Card.VIGILANCE:
                #block += 8
                stance = Stance.CALM
            
            elif card == Card.HALT:
                if stance == Stance.WRATH:
                    block += 9
            
            elif card == Card.EMPTY_BODY:
                #block += 7
                if stance == Stance.CALM:
                    E += 2
                stance = Stance.NEUTRAL
            elif card == Card.DECEIVE_REALITY:
                nSafeties += 1
            elif card == Card.SAFETY:
                if nSafeties:
                    nSafeties -= 1
                else:
                    self._valid = False
                    return 
        
        self._valid = True
        self._endWatcher = WatcherState(stance = stance, nMiracles = nMiracles, 
        nProtects = nProtects, nSafeties = nSafeties)
        
        self._block = block
        self._damage = damage
        self._buffGain = buffGain
        
        playDiscard = [hand[i] for i in playSeq 
        if not hand[i] in POWERS and not hand[i] in EXHAUSTS]
        discardOrder = [hand[i] for i in range(len(hand)) if not i in playSeq 
        and not hand[i] in ETHEREALS and not hand[i] in RETAINS]
        discardOrder.reverse()
        self._discardOrder = tuple(playDiscard + discardOrder)
        self._playOrder = playSeq
    
    @property
    def endWatcher(self):
        return self._endWatcher
    @property
    def block(self):
        return self._block
    @property
    def damage(self):
        return self._damage
    @property
    def buffGain(self):
        return self._buffGain
    @property
    def discardOrder(self):
        return self._discardOrder
    @property
    def playOrder(self):
        return self._playOrder
    @property
    def valid(self):
        return self._valid
    
    def __hash__(self):
        return hash((self.endWatcher, self.discardOrder,
        self.block, self.damage, self.buffGain))
    
    def __str__(self):
        out = str(self.endWatcher)
        out += ', ' + str(self.discardOrder)
        out += ', block = ' + self.block
        out += ', damage = ' + self.damage
        out += ', buffGain = ' + self.buffGain
    
    
    # for comparisons, 
    # True if comparison is valid
    # False if comparison is false (incl. incomparability)
    
    # <= 
    def __le__(self, other):
        if self.discardOrder == other.discardOrder:
            if self.endWatcher <= other.endWatcher:
                if self.block > other.block:
                    return False
                if self.damage > other.damage:
                    return False
                if self.buffGain < other.buffGain:
                    return False
                return True
            return False
        return False
    # >=
    def __ge__(self, other):
        return other <= self
    
    # == 
    def __eq__(self, other):
        if self.discardOrder == other.discardOrder:
            if self.endWatcher == other.endWatcher:
                if self.block != other.block:
                    return False
                if self.damage != other.damage:
                    return False
                if self.buffGain != other.buffGain:
                    return False
                return True
            return False
        return False
    # !=
    def __ne__(self, other):
        return not (self == other)
    
    # <
    def __lt__(self, other):
        return (self <= other) and (self != other)
    # >
    def __gt__(self, other):
        return (self >= other) and (self != other)

def handResults(hand, wstate):
    results = set()
    
    # account for retain cards & Deceive creating a Safety
    handList = list(hand) + wstate.nProtects*[Card.PROTECT] + wstate.nSafeties*[Card.SAFETY]
    handList += [Card.SAFETY for card in hand if card == Card.DECEIVE_REALITY]
    hlen = len(handList)
    
    # k = # cards played
    for k in range(hlen+1):
        for sigma in permutations(range(hlen), k):
            res = PlayResult(wstate, handList, sigma)
            if res.valid:
                # out has properties:
                #   endWatcher
                #   block, damage, buffGain
                #   discardOrder (cards added to discard pile)
                #   playOrder (permutation of card order played)
                
                # attempt to add it by comparing it to others
                pops = []
                less = False
                for otherRes in results:
                    if otherRes < res:
                        pops.append(otherRes)
                    elif res <= otherRes:
                        less = True
                        break
                if not less:
                    for otherRes in pops:
                        results.remove(otherRes)
                    results.add(res)
    #print("dealt with hand =", hand, wstate)
    return results

def memorizeHands(myDeck = START_DECK):
    HANDS = dict()
    for hand in permutations(myDeck, 5):
        for wstate in WATCHER_STATES:
            if not (hand, wstate) in HANDS:
                HANDS[(hand, wstate)] = handResults(hand, wstate)
    return HANDS
                        

#STANCE_COMPARE = dict()
#def setStanceCompare():
#    for stance in STANCES:
#        STANCE_COMPARE[(stance, stance)] = (True, True)
#        if not (stance is Stance.WRATH):
#            STANCE_COMPARE[(Stance.WRATH, stance)] = None
#            STANCE_COMPARE[(stance, Stance.WRATH)] = None
#    STANCE_COMPARE[(Stance.NEUTRAL, Stance.CALM)] = (True, False)
#    STANCE_COMPARE[(Stance.CALM, Stance.NEUTRAL)] = (False, True)
#setStanceCompare()

#WATCHER_STATE_COMPARE = dict()
#def setWatcherStateCompare():    
#    for ws1 in WATCHER_STATES:
#        for ws2 in WATCHER_STATES:
#            out = STANCE_COMPARE[(ws1.stance, ws2.stance)]
#            if out is None:
#                WATCHER_STATE_COMPARE[(ws1, ws2)] = None
#            else:
#                lesser, greater = out
#                lesser = lesser and ( ws1.nMiracles <= ws2.nMiracles)
#                greater = greater and (not ws2.nMiracles <= ws1.nMiracles)
#                if lesser or greater:
#                    WATCHER_STATE_COMPARE[(ws1, ws2)] = (lesser, greater)
#                else:
#                    WATCHER_STATE_COMPARE[(ws1, ws2)] = None
#setWatcherStateCompare()

#def washHands():
#    for hand in HANDS:
#        pops = set()
#        for res1 in HANDS[hand]:
#            do1, ws1, dam1, block1, buff1 = res1
#            for res2 in HANDS[hand]:
#                if res1 != res2:
#                    # out = discardOrder, endWatcherState, damage, block, buffGain
#                    do2, ws2, dam2, block2, buff2 = res2
#                    if do1 == do2 and dam1 <= dam2 and block1 <= block2 and buff1 >= buff2:
#                        comp = WATCHER_STATE_COMPARE[(ws1, ws2)]
#                        if not comp is None and comp[0] is True:
#                            pops.add(res1)
#                            #print("res1 =", res1)
#                            #print("<")
#                            #print("res2 =", res2)
#                            #print()
#        for res in pops:
#            HANDS[hand].remove(res)

################# END OF PRE-COMPUTED DATA #################

class FullState:
    def __init__(self, cardPositions = CardPositions(), watcherState = WatcherState(), 
    combatState = CombatState(), turn = 0, nShuffles = 0):
        self._cardPositions = cardPositions
        self._watcherState = watcherState
        self._combatState = combatState
        self._turn = turn
        self._nShuffles = nShuffles
        
    @property
    def cardPositions(self):
        return self._cardPositions
    @property
    def watcherState(self):
        return self._watcherState
    @property
    def combatState(self):
        return self._combatState
    @property
    def turn(self):
        return self._turn
    @property
    def nShuffles(self):
        return self._nShuffles
    
    def __eq__(self, other):
        if isinstance(other, FullState) and self.turn == other.turn and self.cardPositions == other.cardPositions:
            if self.watcherState == other.watcherState and self.combatState == other.combatState:
                return True
        return False
    def __hash__(self):
        return hash((self.cardPositions, self.watcherState, self.combatState, self.turn))
    
    def __str__(self):
        return f'turn = {self.turn}, combatState = {self.combatState}, cardPositions = {self.cardPositions}, watcherState = {self.watcherState}'

# None: states incomparable
# True: state1 <= state2
# False: state1 > state2
#def compareStates(state1, state2):
#    ws1, gs1 = state1
#    ws2, gs2 = state2
#    
#    out = WATCHER_STATE_COMPARE[(ws1, ws2)]
#    if out is None:
#        return
#    
#    lesser = out[0] and (gs1.pHP <= gs2.pHP) and (gs1.gnHP >= gs2.gnHP) and (gs1.gnBuff >= gs2.gnBuff)
#    if lesser:
#        return True
#    
#    greater = out[1] and (gs2.pHP <= gs1.pHP) and (gs2.gnHP >= gs1.gnHP) and (gs2.gnBuff >= gs1.gnBuff)
#    if greater:
#        return False
#    return 

class SparseDigraph:
    def __init__(self):
        self._outward = dict()
        self._inward = dict()
    @property
    def outward(self):
        return self._outward
    @property
    def inward(self):
        return self._inward
    def addArc(self, fs1, fs2):
        if fs1 in self.outward:
            self.outward[fs1].add(fs2)
        else:
            self.outward[fs1] = set([fs2])
        if fs2 in self.inward:
            self.inward[fs2].add(fs1)
        else:
            self.inward[fs2] = set([fs1])
    def maximalPath(self, endNode):
        currNode = endNode
        path = []
        while currNode in self.inward:
            path.append(currNode)
            currNode = list(self.inward[currNode])[0]
        path.append(currNode)
        return path
    
class StateManager:
    def __init__(self, pHP = 61, gnHP = 106, startDeck = START_DECK, verbose = False, shuffles = None, makeGraph = False):
        self._turn = 0
        self._makeGraph = makeGraph
        self._winStates = dict()
        self._winStats = set()
        
        if shuffles is None:
            #self._shuffler = random.Random()
            self._shuffles = []
            shuffler = random.Random()
            shuffles = []
            
            for i in range(17): # permutation length
                shuffs = []
                for j in range(5): #number of permutations
                    sigma = [k for k in range(i)]
                    #self._shuffler.shuffle(sigma)
                    shuffler.shuffle(sigma)
                    shuffs.append(sigma)
                self._shuffles.append(shuffs)
        else:
            self._shuffles = shuffles
        
        if self._makeGraph:
            self._digraph = SparseDigraph()
        else:
            self._digraph = None
        self._winningLine = None
        
        self._verbose = verbose
        self._winnable = None
        self._nShuffles = 0
        
        startPositions = CardPositions(discard = startDeck)
        startWatcher = WatcherState()
        startCombat = CombatState(pHP = pHP, gnHP = gnHP)
        
        # group CombatStates by CardPositions & stance
        self._stateDictionary = dict()
        self._stateDictionary[(startPositions, 0)] = set([(startWatcher, startCombat)])
    
    @property
    def winStates(self):
        return self._winStates
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
    def winStats(self):
        return self._winStats
    
    @property
    def winStates(self):
        return self._winStates
    
    def setWinnable(self, value):
        self._winnable = value
    def updateWins(self, winState):
        
        self.setWinnable(True)
        self._winStates[winState] = True
        
        pHP1, gnHP1 = winState.combatState.pHP, winState.combatState.gnHP
        for otherWinState in self._winStates:
            if self._winStates[otherWinState]:
                pHP2, gnHP2 = otherWinState.combatState.pHP, otherWinState.combatState.gnHP
                if pHP1 >= pHP2 and gnHP1 < gnHP2:
                    self._winStates[otherWinState] = False
                if pHP1 > pHP2 and gnHP1 <= gnHP2:
                    self._winStates[otherWinState] = False
                if pHP1 <= pHP2 and gnHP1 > gnHP2:
                    self._winStates[winState] = False
                if pHP1 < pHP2 and gnHP1 >= gnHP2:
                    self._winStates[winState] = False
    
    def updateWinStats(self):
        self._winStats = set()
        for winState in self._winStates:
            if self._winStates[winState]:
                self._winStats.add((winState.combatState.pHP, winState.combatState.gnHP))
    
    def getWinPath(self):
        if self.winnable and self._makeGraph:
            maxHP = max([winState.combatState.pHP for winState in self.winStates])
            for winState in self.winStates:
                if maxHP == winState.combatState.pHP:
                    return self._digraph.maximalPath(winState)
    
    def nextTurn(self):
        self._turn += 1
        
        if self._verbose:
            print("turn", self.turn, "shuffle =", sigma)
        nextDict = dict()
        
        for (pos, nShuffles) in self.stateDictionary:
            nextNShuffles = nShuffles
            if len(pos.draw) < 5:
                #sigma = [i for i in range(self._discardPileSize)]
                #self._shuffler.shuffle(sigma)
                sigma = self._shuffles[len(pos.discard)][nShuffles]
                nextNShuffles += 1
            else:
                sigma = None
            currPos = pos.nextPositions(sigma)
            
            if self._verbose:
                print(pos, "draws into", currPos)
            for (ws, cs) in self.stateDictionary[(pos, nShuffles)]:
                if self._verbose:
                    print("  ws =", ws, "; cs =", cs, "...")
                
                if self._makeGraph:
                    prevFS = FullState(cardPositions = pos, watcherState = ws, combatState = cs, turn = self.turn-1, nShuffles = nShuffles)
                    currFS = FullState(cardPositions = currPos, watcherState = ws, combatState = cs, turn = self.turn, nShuffles = nextNShuffles)
                    self._digraph.addArc(prevFS, currFS)
                
                if (currPos.hand, ws) in HANDS:
                    hr = HANDS[(currPos.hand, ws)]
                else:
                    hr = handResults(currPos.hand, ws)
                    print("new hand =", currPos.hand, ws)
                    HANDS[(currPos.hand, ws)] = hr
                
                for out in hr:
                    
                    # out has properties:
                    #   endWatcher
                    #   block, damage, buffGain
                    #   discardOrder (cards added to discard pile)
                    #   playOrder (permutation of card order played)
                    
                    if self._verbose:
                        discardString = ''
                        for card in out.discardOrder:
                            discardString += CARD_NAMES[card.value]
                        print("    result =", discardString, out.endWatcher, 
                        (out.block, out.damage, out.buffGain), out.playOrder, "...")
                    
                    # out = (discardOrder, endWatcherState, damage, block, buffGain)
                    nextPos = CardPositions(draw = currPos.draw, hand = [], 
                    discard = currPos.discard + out.discardOrder)
                    nextWS = out.endWatcher
                    newGNHP = cs.gnHP - out.damage
                    
                    if self.turn == 1:
                        nextCS = CombatState(pHP = cs.pHP, gnHP = newGNHP)
                    else:
                        nextBuff = cs.gnBuff + out.buffGain
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
                            lostHP -= out.block
                            if lostHP < 0:
                                lostHP = 0
                        nextCS = CombatState(pHP = cs.pHP - lostHP, 
                        gnHP = newGNHP, gnBuff = nextBuff)
                    
                    if self._verbose:
                        print("    results in:", nextPos, nextWS, nextCS)
                    
                    nextFS = FullState(cardPositions = nextPos, watcherState = nextWS, combatState = nextCS, 
                    turn = self.turn, nShuffles = nextNShuffles)
                    if self._makeGraph:
                        self._digraph.addArc(currFS, nextFS)
                    
                    if nextCS.gnHP <= 0:
                        
                        wonCS = CombatState(pHP = cs.pHP, gnHP = nextCS.gnHP, gnBuff = nextCS.gnBuff)
                        wonFS = FullState(cardPositions = nextPos, watcherState = nextWS, combatState = wonCS, turn = self.turn, nShuffles = nextNShuffles)
                        
                        self.updateWins(wonFS)
                        
                        if self._makeGraph:
                            self._digraph.addArc(currFS, wonFS)
                        
                    if nextCS.pHP > 0:
                        nextState = (nextWS, nextCS)
                        if not (nextPos, nShuffles) in nextDict:
                            nextDict[(nextPos, nShuffles)] = set()
                        pops = []
                        less = False
                        for otherState in nextDict[(nextPos, nShuffles)]:
                            #comp = compareStates(nextState, otherState)
                            # otherState = (ws2, cs2)
                            if nextWS <= otherState[0] and nextCS <= otherState[1]:
                                less = True
                                break
                            else:
                                if nextWS >= otherState[0] and nextCS >= otherState[1]:
                                    pops.append(otherState)
                        if pops:
                            #print("nextState =", nextState[0].stance, nextState[0].nMiracles, 
                            #nextState[1].pHP, nextState[1].gnHP, nextState[1].gnBuff, "beats...")
                            for otherState in pops:
                                nextDict[(nextPos, nShuffles)].remove(otherState)
                                #print("  otherState =", otherState[0].stance, otherState[0].nMiracles, 
                                #otherState[1].pHP, otherState[1].gnHP, otherState[1].gnBuff)
                            
                            nextDict[(nextPos, nShuffles)].add(nextState)
                        else:
                            if not less:
                                nextDict[(nextPos, nShuffles)].add(nextState)
        
        self._stateDictionary = nextDict
        if len(self._stateDictionary) == 0:
            if self.winnable is None:
                self.setWinnable(False)
        if self._verbose:
            print("number of states:", self.numStates)
        
        #print("actually setting winStats...")
        self.updateWinStats()
        #print("set!")
        
#################  #################

MY_DECK = tuple([Card.ASCENDERS_BANE]*1+[Card.STRIKE]*4+[Card.DEFEND]*4
+[Card.ERUPTION,Card.VIGILANCE]
+[Card.NONE]*0
+[Card.HALT]*0
+[Card.EMPTY_BODY]*0
+[Card.DECEIVE_REALITY]*1
)
#HANDS = memorizeHands(myDeck = START_DECK)
HANDS = memorizeHands(myDeck = MY_DECK)
#hsize = 0

#for hand in HANDS:
#    hsize += len(HANDS[hand])
print("len(HANDS) =", len(HANDS), "size =", sum([len(HANDS[hand]) for hand in HANDS]))

#washHands()
#hsize = 0
#for hand in HANDS:
#    hsize += len(HANDS[hand])
#print("len(HANDS) =", len(HANDS), "size =", hsize)

#HANDS = dict()

def testShuffle(shuffles, pHP = 61, gnHP = 106, startDeck = MY_DECK):
    sm = StateManager(pHP = pHP, gnHP = gnHP, verbose = False, startDeck = startDeck, 
    makeGraph = True, shuffles = shuffles)
    while sm.numStates:
        sm.nextTurn()
    if sm.winnable:
        out = list(sm.winStats)
        out.sort()
        out = tuple(out)
        print("sm.winStates =")
        for winState in sm.winStates:
            if sm.winStates[winState]:
                print("\t", winState)
        print("out =", out, "sm.winStats =", sm.winStats)
        myPath = sm.getWinPath()
        for elt in myPath:
            print('\t', elt)	

def sampleSim(nTrials = 100, pHP = 61, gnHP = 106, verbose = False, startDeck = MY_DECK):
    nWins = 0
    curr = 0
    winStats = dict()
    while curr < nTrials:
        sm = StateManager(pHP = pHP, gnHP = gnHP, verbose = verbose, startDeck = startDeck, makeGraph = False)
        #print("turn 0 states:", sm.numStates)
        i = 0
        while sm.numStates:
        #while i < 1:
            sm.nextTurn()
            i += 1
            #print("turn", i, "states:", sm.numStates)
        if sm.winnable:
            nWins += 1
            out = list(sm.winStats)
            out.sort()
            out = tuple(out)
            #print("sm.winStates =")
            #for winState in sm.winStates:
            #    if sm.winStates[winState]:
            #        print("\t", winState)
            #print("out =", out, "sm.winStats =", sm.winStats)
            if out in winStats:
                winStats[out] += 1
            else:
                winStats[out] = 1
            
            #maxHP = max([mult[0] for mult in out])
            myPath = sm.getWinPath()
            if not (myPath is None):
                for elt in myPath:
                    print(elt)
            
        curr += 1
        
        if curr % 10 == 0:
            print(nWins, "out of", curr, ":", nWins/curr, "; win stats =")
            for winStat in winStats:
                print("\t", winStats[winStat], "times", winStat)
            print("len/size of HANDS =", len(HANDS), sum([len(HANDS[hand]) for hand in HANDS]))
    
    print()
    return nWins

if True:
    NTRIALS = 1000
    conditions = [(NTRIALS, 61, 106)] #, (NTRIALS, 56, 106)]

    results = dict()
    print()
    for condition in conditions:
        results[condition] = sampleSim(nTrials = condition[0], pHP = condition[1], gnHP = condition[2])

    for condition in conditions:
        print("conditions =", condition, "\tresults:", 
        results[condition], "/", condition[0], "=", results[condition]/condition[0])