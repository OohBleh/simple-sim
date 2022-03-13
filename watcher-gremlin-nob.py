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

CARDS = [Card.NONE, Card.STRIKE, Card.DEFEND, Card.ERUPTION, Card.VIGILANCE, Card.ASCENDERS_BANE, 
Card.HALT, Card.EMPTY_BODY, Card.PROTECT]
CARD_NAMES = ['none', 'S', 'D', 'E', 'V', 'A', 
'H', 'Eb', 'Pr']
UNPLAYABLES = set([Card.NONE, Card.ASCENDERS_BANE])
ETHEREALS = set([Card.ASCENDERS_BANE])
RETAINS = dict()
RETAINS[Card.PROTECT] = Card.PROTECT

COSTS = dict()
for card in [Card.HALT]:
    COSTS[card] = 0
for card in [Card.STRIKE, Card.DEFEND, Card.EMPTY_BODY]:
    COSTS[card] = 1
for card in [Card.ERUPTION, Card.VIGILANCE, Card.PROTECT]:
    COSTS[card] = 2
ATTACKS = set([Card.STRIKE, Card.ERUPTION])
SKILLS = set([Card.DEFEND, Card.VIGILANCE, 
Card.HALT, Card.EMPTY_BODY, Card.PROTECT])
POWERS = set([])

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
    nProtects = 0):
        self._stance = stance
        self._nMiracles = nMiracles
        self._nProtects = nProtects
    
    @property
    def stance(self):
        return self._stance
    @property
    def nMiracles(self):
        return self._nMiracles
    @property
    def nProtects(self):
        return self._nProtects
    
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
        return hash((self.stance, self.nMiracles, self.nProtects))
    def __str__(self):
        out = STANCE_NAMES[self.stance.value]
        if self.nMiracles:
            out += ',' + self.nMiracles + 'miracle(s)'
        if self.nProtects:
            out += ',' + self.nProtects + 'protects(s)'
        return out

#ws1 = WatcherState()
#ws2 = WatcherState()
#wset = set([(Card.STRIKE, ws1)])
#print("hashed correctly?", (Card.STRIKE, ws2) in wset)

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
    def __init__(endWatcherState = WatcherState(), damage = 0, 
    block = 0, buffGain = 0, discardOrder = tuple()):
        self._endWatcherState = endWatcherState
        self._damage = damage
        self._block = block
        self._buffGain = buffGain
        self._discardOrder = discardOrder
    
    @property
    def endWatcherState(self):
        return self._endWatcherState
    @property
    def damage(self):
        return self._damage
    @property
    def block(self):
        return self._block
    @property
    def buffGain(self):
        return self._buffGain
    @property
    def discardOrder(self):
        return self._discardOrder
    
    # tests if self <= other
    # none if incomparable
    # true if self <= other
    # false if self > other
    def compare(self, other):
        if isinstance(other, PlayResult) and other.discardOrder == self.discardOrder:
            
            # incomparable stances --> incomparable results
            if WATCHER_STATE_COMPARE[(self.watcherState, other.watcherState)] is None:
                return None
            
            # self.stance <= other.stance...
            if WATCHER_STATE_COMPARE[(self.watcherState, other.watcherState)][0]:
                if self.damage > other.damage or self.block > other.block or self.buffGain < other.buffGain:
                    return None
                return True
            else:
                # self.stance > other.stance
                return False
        else:
            return None
            
    
        

def playResult(cardSeq, watcherState, E = 3):
    damage = 0
    block = 0
    buffGain = 0
    stance = watcherState.stance
    nMiracles = watcherState.nMiracles
    
    for card in cardSeq:
        if card in UNPLAYABLES:
            return 
        
        while E < COSTS[card]:
            if nMiracles:
                E += 1
                buffGain += 3
                nMiracles -= 1
            else:
                return
        
        E -= COSTS[card]
        
        if card in SKILLS:
            buffGain += 3
        
        if card == Card.STRIKE:
            if stance == Stance.WRATH:
                damage += 12
            else:
                damage += 6
        
        elif card == Card.DEFEND:
            block += 5
        
        elif card == Card.ERUPTION:
            if stance == Stance.WRATH:
                damage += 18
            else:
                if stance == Stance.CALM:
                    E += 2
                damage += 9    
            stance = Stance.WRATH
        
        elif card == Card.VIGILANCE:
            block += 8
            stance = Stance.CALM
        
        elif card == Card.HALT:
            if stance == Stance.WRATH:
                block += 12
            else:
                block += 3
        
        elif card == Card.EMPTY_BODY:
            block += 7
            if stance == Stance.CALM:
                E += 2
            stance = Stance.NEUTRAL
        
    endWatcherState = WatcherState(stance = stance, nMiracles = nMiracles)
    return endWatcherState, damage, block, buffGain

def handResults(hand, wstate):
    results = set()
    for k in range(6):
        for sigma in permutations(range(5), k):
            play = [hand[si] for si in sigma]
            out = playResult(play, wstate)
            if out != None:
                # out = endWatcherState, damage, block, buffGain
                discardOrder = [hand[i] for i in range(5) if not i in sigma
                and not hand[i] in ETHEREALS]
                discardOrder.reverse()
                discardOrder = tuple(play + discardOrder)
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
                lesser = lesser and ( ws1.nMiracles <= ws2.nMiracles)
                greater = greater and (not ws2.nMiracles <= ws1.nMiracles)
                if lesser or greater:
                    WATCHER_STATE_COMPARE[(ws1, ws2)] = (lesser, greater)
                else:
                    WATCHER_STATE_COMPARE[(ws1, ws2)] = None
setWatcherStateCompare()

def washHands():
    for hand in HANDS:
        pops = set()
        for res1 in HANDS[hand]:
            do1, ws1, dam1, block1, buff1 = res1
            for res2 in HANDS[hand]:
                if res1 != res2:
                    # out = discardOrder, endWatcherState, damage, block, buffGain
                    do2, ws2, dam2, block2, buff2 = res2
                    if do1 == do2 and dam1 <= dam2 and block1 <= block2 and buff1 >= buff2:
                        comp = WATCHER_STATE_COMPARE[(ws1, ws2)]
                        if not comp is None and comp[0] is True:
                            pops.add(res1)
                            #print("res1 =", res1)
                            #print("<")
                            #print("res2 =", res2)
                            #print()
        for res in pops:
            HANDS[hand].remove(res)

################# END OF PRE-COMPUTED DATA #################

class FullState:
    def __init__(self, cardPositions = CardPositions(), watcherState = WatcherState(), 
    combatState = CombatState(), turn = 0):
        self._cardPositions = cardPositions
        self._watcherState = watcherState
        self._combatState = combatState
        self._turn = turn
        
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
        self._drawPileSize = len(startPositions.draw)
        self._discardPileSize = len(startPositions.discard)
        
        # group CombatStates by CardPositions & stance
        self._stateDictionary = dict()
        self._stateDictionary[startPositions] = set([(startWatcher, startCombat)])
    
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
        
        if self._drawPileSize < 5:
            #sigma = [i for i in range(self._discardPileSize)]
            #self._shuffler.shuffle(sigma)
            sigma = self._shuffles[self._discardPileSize][self._nShuffles]
            self._nShuffles += 1
        else:
            sigma = None
        
        if self._verbose:
            print("turn", self.turn, "shuffle =", sigma)
        nextDict = dict()
        
        for pos in self.stateDictionary:
            
            currPos = pos.nextPositions(sigma)
            if self._verbose:
                print(pos, "draws into", currPos)
            for (ws, cs) in self.stateDictionary[pos]:
                if self._verbose:
                    print("  ws =", ws, "; cs =", cs, "...")
                
                if self._makeGraph:
                    prevFS = FullState(cardPositions = pos, watcherState = ws, combatState = cs, turn = self.turn-1)
                    currFS = FullState(cardPositions = currPos, watcherState = ws, combatState = cs, turn = self.turn)
                    self._digraph.addArc(prevFS, currFS)
                
                hr = HANDS[(currPos.hand, ws)]
                for out in hr:
                    if self._verbose:
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
                    
                    if self._verbose:
                        print("    results in:", nextPos, nextWS, nextCS)
                    
                    nextFS = FullState(cardPositions = nextPos, watcherState = nextWS, combatState = nextCS, turn = self.turn)
                    if self._makeGraph:
                        self._digraph.addArc(currFS, nextFS)
                    
                    if nextCS.gnHP <= 0:
                        
                        wonCS = CombatState(pHP = cs.pHP, gnHP = nextCS.gnHP, gnBuff = nextCS.gnBuff)
                        wonFS = FullState(cardPositions = nextPos, watcherState = nextWS, combatState = wonCS, turn = self.turn)
                        
                        self.updateWins(wonFS)
                        
                        if self._makeGraph:
                            self._digraph.addArc(currFS, wonFS)
                        
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
                            #print("nextState =", nextState[0].stance, nextState[0].nMiracles, 
                            #nextState[1].pHP, nextState[1].gnHP, nextState[1].gnBuff, "beats...")
                            for otherState in pops:
                                nextDict[nextPos].remove(otherState)
                                #print("  otherState =", otherState[0].stance, otherState[0].nMiracles, 
                                #otherState[1].pHP, otherState[1].gnHP, otherState[1].gnBuff)
                            
                            nextDict[nextPos].add(nextState)
                        else:
                            if less is False:
                                nextDict[nextPos].add(nextState)
                        self._drawPileSize = len(nextPos.draw)
                        self._discardPileSize = len(nextPos.discard)
        
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
+[Card.NONE]*1
+[Card.HALT]*0
+[Card.EMPTY_BODY]*0
)
HANDS = memorizeHands(myDeck = MY_DECK)
hsize = 0

for hand in HANDS:
    hsize += len(HANDS[hand])
print("len(HANDS) =", len(HANDS), "size =", hsize)
washHands()
hsize = 0
for hand in HANDS:
    hsize += len(HANDS[hand])
print("len(HANDS) =", len(HANDS), "size =", hsize)

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
    
    print()
    return nWins

if True:
    NTRIALS = 10000
    conditions = [(NTRIALS, 61, 106)] #, (NTRIALS, 56, 106)]

    results = dict()
    print()
    for condition in conditions:
        results[condition] = sampleSim(nTrials = condition[0], pHP = condition[1], gnHP = condition[2])

    for condition in conditions:
        print("conditions =", condition, "\tresults:", 
        results[condition], "/", condition[0], "=", results[condition]/condition[0])