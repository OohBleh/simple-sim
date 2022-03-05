import random
import math
import queue

DRAW = [i for i in range(10)]
r = random.Random()
r.shuffle(DRAW)
print(DRAW)

################# END OF DECK AND STATE CLASS #################
class CardSet:
    def __init__(self, S, D, E, V, A):
        self.S = S
        self.D = D
        self.E = E
        self.V = V
        self.A = A

class State:
    def __init__(self, pHP, gnHP, M = True, stance = 'N', energy = 3, block = 0, turn = 1, nbuff = 0, cardSets = None):
        if cardSets == None:
            self.draw = CardSet(4, 4, 1, 1, 1)
            self.hand = CardSet(0, 0, 0, 0, 0)
            self.discard = CardSet(0, 0, 0, 0, 0)
        else:
            self.draw = (cardSets[0].S,cardSets[0].D,cardSets[0].E,cardSets[0].V,cardSets[0].A)
            self.hand = (cardSets[1].S,cardSets[1].D,cardSets[1].E,cardSets[1].V,cardSets[1].A)
            self.discard = (cardSets[2].S,cardSets[2].D,cardSets[2].E,cardSets[2].V,cardSets[2].A)
        
        self.M = M
        self.stance = stance
        self.energy = energy
        self.block = block
        self.turn = turn
        self.nbuff = nbuff
        
        self.pHP = pHP
        self.gnHP = gnHP
        
    
    def plays(self):
        out = ''
        if self.energy:
            # can play Strike & Defend w/o Miracle
            if self.hand.S:
                out += 'S'
            if self.hand.D:
                out += 'D'
            if self.energy > 1:
                # can play Eruption & Vigilance w/o Miracle
                if self.hand.E:
                    out += 'E'
                if self.hand.V:
                    out += 'V'
            elif self.M:
                # needs Miracle to play Eruption & Vigilance
                if self.hand.E:
                    out += 'e'
                if self.hand.V:
                    out += 'v'
        elif self.M:
            # needs Miracle to play Eruption & Vigilance
            if self.hand.S:
                out += 's'
            if self.hand.D:
                out += 'd'
        return out
    
    def show(self):
        out = 'HP: (' + str(self.pHP) + ',' + str(self.gnHP) + '), stance = ' + self.stance
        if self.M:
            out += ', hand: M'
        else:
            out += ', hand: '
        out += self.hand.S*'S'
        out += self.hand.D*'D'
        out += self.hand.E*'E'
        out += self.hand.V*'V'
        out += self.hand.A*'A'
        
        out += ', draw: '
        out += self.draw.S*'S'
        out += self.draw.D*'D'
        out += self.draw.E*'E'
        out += self.draw.V*'V'
        out += self.draw.A*'A'
        
        out += ', discard: '
        out += self.discard.S*'S'
        out += self.discard.D*'D'
        out += self.discard.E*'E'
        out += self.discard.V*'V'
        out += self.discard.A*'A'
        
        print (out)
    
    ################# START OF PLAYER ACTIONS #################
    # methods to create new states from single card plays
    def playS(self, needsMiracle = False):
        newDraw = CardSet(self.draw.S, self.draw.D, self.draw.E, self.draw.V, self.draw.A)
        newHand = CardSet(self.hand.S-1, self.hand.D, self.hand.E, self.hand.V, self.hand.A)
        newDiscard = CardSet(self.discard.S+1, self.discard.D, self.discard.E, self.discard.V, self.discard.A)

        newState = State(self.pHP, self.gnHP, M = self.M, stance = self.stance, 
        energy = self.energy-1, block = self.block, turn = self.turn, nbuff = self.nbuff, 
        cardSets = [newDraw, newHand, newDiscard])
        
        if newState.stance == 'W':
            newState.gnHP -= 6
        if needsMiracle:
            newState.M = False
            newState.energy += 1
            if newState.turn > 1:
                newState.nbuff += 3
        return newState
    
    def playD(self, needsMiracle = False):
        newDraw = CardSet(self.draw.S, self.draw.D, self.draw.E, self.draw.V, self.draw.A)
        newHand = CardSet(self.hand.S, self.hand.D-1, self.hand.E, self.hand.V, self.hand.A)
        newDiscard = CardSet(self.discard.S, self.discard.D+1, self.discard.E, self.discard.V, self.discard.A)
        
        newState = State(self.pHP, self.gnHP, M = self.M, stance = self.stance, 
        energy = self.energy-1, block = self.block+5, turn = self.turn, nbuff = self.nbuff, 
        cardSets = [newDraw, newHand, newDiscard])
        
        if newState.turn > 1:
            if needsMiracle:
                newState.M = False
                newState.energy += 1
                newState.nbuff += 6
            else:
                newState.nbuff += 3
        else:
            if needsMiracle:
                newState.M = False
                newState.energy += 1
        return newState
    
    def playE(self, needsMiracle = False):
        newDraw = CardSet(self.draw.S, self.draw.D, self.draw.E, self.draw.V, self.draw.A)
        newHand = CardSet(self.hand.S, self.hand.D, self.hand.E-1, self.hand.V, self.hand.A)
        newDiscard = CardSet(self.discard.S, self.discard.D, self.discard.E+1, self.discard.V, self.discard.A)
        
        newState = State(self.pHP, self.gnHP-9, M = self.M, stance = 'W', 
        energy = self.energy-2, block = self.block, turn = self.turn, nbuff = self.nbuff, 
        cardSets = [newDraw, newHand, newDiscard])
        
        if self.stance == 'W':
            newState.gnHP -= 9
        elif self.stance == 'C':
            newState.energy += 2
        if needsMiracle:
            newState.M = False
            newState.energy += 1
            if newState.turn > 1:
                newState.nbuff += 3
        return newState

    def playV(self, needsMiracle = False):
        newDraw = CardSet(self.draw.S, self.draw.D, self.draw.E, self.draw.V, self.draw.A)
        newHand = CardSet(self.hand.S, self.hand.D, self.hand.E, self.hand.V-1, self.hand.A)
        newDiscard = CardSet(self.discard.S, self.discard.D, self.discard.E, self.discard.V+1, self.discard.A)
        
        newState = State(self.pHP, self.gnHP, M = self.M, stance = 'C', 
        energy = self.energy-2, block = self.block+8, turn = self.turn, nbuff = self.nbuff, 
        cardSets = [newDraw, newHand, newDiscard])
        
        if newState.turn > 1:
            if needsMiracle:
                newState.M = False
                newState.energy += 1
                newState.nbuff += 6
            else:
                newState.nbuff += 3
        else:
            if needsMiracle:
                newState.M = False
                newState.energy += 1
        return newState
    
    # mutator method to end turn for the current state
    def end(self):
        # hand -> discard pile
        self.discard = CardSet(self.discard.S+self.hand.S, 
        self.discard.D+self.hand.D, 
        self.discard.E+self.hand.E, 
        self.discard.V+self.hand.V, 
        self.discard.A)
        self.hand = CardSet(0,0,0,0,0)
        
        # damage calculated
        dam = 0
        if self.turn % 3 == 2:
            dam = 8+self.nbuff
            if self.stance == 'W':
                dam *= 2
        elif self.turn > 1:
            dam = 16+self.nbuff
            if self.stance == 'W':
                dam *= 3
            else:
                dam = math.floor(1.5*dam)
        
        # block applied
        if dam > self.block:
            dam -= self.block
        else:
            dam = 0
        self.pHP -= dam
        self.block = 0
        return
    ################# END OF PLAYER ACTIONS #################
    
################# END OF DECK AND STATE CLASS #################

################# START OF GLOBAL MANAGEMENT #################
class StateManager:
    def __init__(self, pHP=61, gnHP=106):
        
        self.shuffler = random.Random()
        self.draw_pile = ['S' for i in range(4)] + ['D' for i in range(4)] + ['E', 'V', 'A']
        
        self.shuffler.shuffle(self.draw_pile)
        self.curr_hand = self.draw_pile[:5]
        self.draw_pile = self_draw_pile[5:]
        
        self.currStates = queue.Queue()
        currState = State(pHP, gnHP)
        self.currStates.put()
        self.endStates = set([])
        
        #### hmmmm
    
    
################# END OF GLOBAL MANAGEMENT #################


gs = State(61, 106)
print(gs.hand.S)
gs.show()


#gs2 = deepcopy(gs)
#print(gs2.draw.S)