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
START_DECK = tuple([Card.STRIKE]*4+[Card.STRIKE]*4+[Card.ERUPTION,Card.VIGILANCE,Card.ASCENDERS_BANE])

class CardPositions:
    def __init__(self, draw = [], hand = [], discard = START_DECK):
        self.draw = tuple(draw)
        self.hand = tuple(hand)
        self.discard = tuple(discard)
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
        self.pHP = pHP
        self.gnHP = gnHP
        self.gnBuff = gnBuff
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
        self.stance = stance
        self.hasMiracle = hasMiracle
    def __str__(self):
        if self.hasMiracle:
            return STANCE_NAMES[self.stance.value] + ', 1 miracle'
        else:
            return STANCE_NAMES[self.stance.value] + ', 0 miracle' 

#WATCHER_STATES = []
#for stance in STANCES[1:]:
#    WATCHER_STATES.append(WatcherState(stance = stance, hasMiracle = True))
#    WATCHER_STATES.append(WatcherState(stance = stance, hasMiracle = False))
#WATCHER_STATES = tuple(WATCHER_STATES)

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

#ctr = 0
#for hand in HANDS:
#    ctr += len(HANDS[hand])
#print("hands:", len(HANDS), ctr)

################# END OF PRE-COMPUTED DATA #################

def compareStates(state1, state2):
    ws1, gs1 = state1
    ws2, gs2 = state2
    
    if not ws1.stance is ws2.stance:
        lesser = ws1.stance is Stance.NEUTRAL and ws2.stance is Stance.CALM
        greater = ws2.stance is Stance.CALM and ws2.stance is Stance.NEUTRAL
    
    lesser = lesser and (ws2.hasMiracle or not ws1.hasMiracle)
    lesser = lesser and gs1.pHP <= gs2.pHP
    lesser = lesser and gs1.gnHP >= gs2.gnHP
    lesser = lesser and gs1.gnBuff >= gs2.gnBuff
    
    greater = greater and (ws1.hasMiracle or not ws2.hasMiracle)
    greater = greater and gs2.pHP <= gs1.pHP
    greater = greater and gs2.gnHP >= gs1.gnHP
    greater = greater and gs2.gnBuff >= gs1.gnBuff
    
    if lesser:
        return True
    if greater:
        return False
    return 

class StateManager:
    def __init__(self, pHP = 61, gnHP = 106, startDeck = START_DECK, verbose = False):
        self.turn = 0
        self.shuffler = random.Random()
        self.verbose = verbose
        self.winnable = None
        
        startPositions = CardPositions(discard = startDeck)
        startWatcher = WatcherState()
        startCombat = CombatState(pHP = pHP, gnHP = gnHP)
        self.drawPileSize = len(startPositions.draw)
        self.discardPileSize = len(startPositions.discard)
        
        # group CombatStates by CardPositions & stance
        self.stateDictionary = dict()
        self.stateDictionary[startPositions] = set([(startWatcher, startCombat)])
    
    def numStates(self):
        ctr = 0
        for elt in self.stateDictionary:
            ctr += len(self.stateDictionary[elt])
        return ctr
    
    def nextTurn(self):
        if len(self.stateDictionary) == 0:
            return 
        
        self.turn += 1
        
        if self.drawPileSize < 5:
            sigma = [i for i in range(self.discardPileSize)]
            self.shuffler.shuffle(sigma)
        else:
            sigma = None
        
        if self.verbose:
            print("turn", self.turn, "shuffle =", sigma)
        nextDict = dict()
        
        # the previous positions have hand = [] (discarded)
        for pos in self.stateDictionary:
            currPos = pos.nextPositions(sigma)
            if self.verbose:
                print(pos, "draws into", currPos)
            for (ws, cs) in self.stateDictionary[pos]:
                if self.verbose:
                    print("  ws =", ws, "; cs =", cs, "...")
                #if not (currPos.hand, ws) in HANDS:
                #    HANDS[(currPos.hand, ws)] = handResults(currPos.hand, ws)
                #for out in HANDS[(currPos.hand, ws)]:
                hr = handResults(currPos.hand, ws)
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
                        nextCS = CombatState(pHP = cs.pHP, gnHP = cs.gnHP - out[2])
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
                        gnHP = cs.gnHP - out[2], gnBuff = nextBuff)
                    
                    if self.verbose:
                        print("    results in:", nextPos, nextWS, nextCS)
                    
                    if nextCS.gnHP <= 0:
                        self.winnable = True
                    
                    if nextCS.pHP > 0:
                        nextState = (nextWS, nextCS)
                        if not nextPos in nextDict:
                            nextDict[nextPos] = set()
                        pops = []
                        less = False
                        for otherState in nextDict[nextPos]:
                            comp = compareStates(nextState, otherState)
                            if comp == True:
                                less = True
                            else:
                                if comp == False:
                                    pops.append(otherState)
                        if pops:
                            #print("nextState =", nextState[0].stance, nextState[0].hasMiracle, 
                            #nextState[1].pHP, nextState[1].gnHP, nextState[1].gnBuff, "beats...")
                            for otherState in pops:
                                nextDict[pos].remove(otherState)
                                #print("  otherState =", otherState[0].stance, otherState[0].hasMiracle, 
                                #otherState[1].pHP, otherState[1].gnHP, otherState[1].gnBuff)
                            
                            #print("popped!")
                            nextDict[nextPos].add(nextState)
                        else:
                            if less == False:
                                nextDict[nextPos].add(nextState)
                        self.drawPileSize = len(nextPos.draw)
                        self.discardPileSize = len(nextPos.discard)
        
        self.stateDictionary = nextDict
        if len(self.stateDictionary) == 0:
            if self.winnable == None:
                self.winnable = False
        if self.verbose:
            print("number of states:", self.numStates())
        
#################  #################

MY_DECK = tuple([Card.STRIKE]*4+[Card.STRIKE]*4+[Card.ERUPTION,Card.VIGILANCE,Card.ASCENDERS_BANE])

nWins = 0
nTotal = 0
while nTotal < 10000:
    sm = StateManager(gnHP = 106, verbose = False, startDeck = START_DECK)
    print("turn 0 states:", sm.numStates())
    i = 0
    while sm.numStates():
    #while i < 1:
        sm.nextTurn()
        i += 1
        print("turn", i, "states:", sm.numStates())
        print("won yet?", sm.winnable)
        print()
    if sm.winnable:
        nWins += 1
    nTotal += 100000
    
    if nTotal % 100 == 0:
        #print(nWins, "out of", nTotal, ":", nWins/nTotal, "HANDS:", len(HANDS))
        print(nWins, "out of", nTotal, ":", nWins/nTotal)

print(nWins, "out of", nTotal, ":", nWins/nTotal)

