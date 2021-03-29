# Solve minesweeper
import sys
import argparse
from random import randrange, seed
from mines import Game
from itertools import combinations
from time import time

class Knowledge:
    ''' Things I know about a cell'''
    def __init__(self, x, y, value, neighbors, marked, exposed):
        self.x = x
        self.y = y
        self.value = value - len(neighbors & marked)
        self.neighbors = neighbors
        self.strangers = neighbors - exposed - marked

    def getBombs(self):
        ''' blame our neighbors if we know they have a bomb'''
        if self.value == len(self.strangers):
            return self.strangers
        else:
            return set()

    def getSafes(self):
        '''absolve our neighbors if we know they're good'''
        if self.value == 0:
            return self.strangers
        else:
            return set()

class Solve:
    def __init__(self):
        self.width=32
        self.height=18
        mines=100

        self.memo_neighbors = {}
        self.exposed = set()
        self.marked = set()
        self.frontier = set()
        self.board=frozenset([(x,y) for x in range(self.height) for y in range(self.width)])
        self.know = {}

        self.game = Game(self.width, self.height, mines)
        self.reveal(self.height // 2, self.width // 2)

        self.game.display()

    def mark(self, x, y):
        print(F"Mark {x},{y}")
        if self.game.mark(x,y):
            self.marked.add((x,y))
        else:
            self.marked -= set([(x,y)])

        self.updateGraph(set([(x,y)]))
        self.display()

    def getNeighbors(self, cell):
        if cell not in self.memo_neighbors:
            self.memo_neighbors[cell] = self.game.getNeighbors(*cell)
        return self.memo_neighbors[cell]

    # Update our knowledge graph for cells we recently got new info about
    def updateGraph(self, cells):
        touched = set(cells)

        # find all the neighbors of new-info cells
        for cell in cells:
            touched |= self.getNeighbors(cell)

        # Find all the neighbors of those neighbors (we need to update them, too)
        bacon = set()
        for cell in touched:
            bacon |= self.getNeighbors(cell)
        touched |= bacon

        dropped = 0
        updated = 0
        added = 0

        # Update our knowledge about those cells
        for cell in touched:
            v = self.game.readCell(*cell)
            if not v:
                if cell in self.know:
                    self.know.pop(cell)
                    dropped += 1
                continue

            nb = self.getNeighbors(cell)
            newk = Knowledge(*cell, v, nb, self.marked, self.exposed)
            if not newk.strangers:
                if cell in self.know:
                    self.know.pop(cell)
                    dropped += 1
                continue

            if cell in self.know:
                updated += 1
            else:
                added += 1

            nb = self.getNeighbors(cell)
            self.know[cell] = newk

        print(F"Graph update: Touched {len(touched)} cells, dropped {dropped}, added {added}, updated {updated}")


    def collaborate(self):
        '''
            Attempt to get more information from the knowledge graph by combining inputs from multiple
            sources.  For example, in this game we can't tell what's in the second row by looking
            at clues individually.

                +---+---+---+---+---+
                | 1 | 2 | . | . | . |
                +---+---+---+---+---+
                | A | B | C | D | E |
                +---+---+---+---+---+

            But we know that the '2' sees at most two bombs and the '1' to the left of it sees only
            one bomb. That is,
                L1. There is one bomb in {A, B}
                L2. There are two bombs in {A, B, C}

            Let's combine these to find more information.
            L1 is about {A, B}. What can I find out about {A, B} from L2?

            From L2:
                If C has a bomb, then {A, B} has one bomb.
                If C does not have a bomb, then {A, B} has two bombs.

            But L1 tells us that {A, B} has one bomb.  Therefore, we know that {C} must contain one bomb.

            We can do a little better by generalizing this.

            From L1:
                {A,B} has at least one bomb
                {A,B} has at most one bomb

            From L2:
                {A,B} has at least one bomb
                {A,B} has at most two bombs

            When we combine these we find that L1 limits our upper bound to 1 bomb in {A, B}.
            Let's call this new finding L3:

            From L1+L2:
                L3. {A,B} has at most one bomb

            Now, we can reapply this knowledge to our original graph to find out what's in C.

                L2. {A,B,C} has at least two bombs
                L3. {A,B} has at most one bomb

                    {A,B,C} - {A,B} = {C} = 2 - 1 = 1 bomb

                L4. {C} has at least one bomb
        '''

        # Build a graph of everything we know from our kgraph
        changed = False
        kg = {} # knowledgeGraph
        class MinMax:
            def __init__(self, mn, mx):
                self.least = mn
                self.most = mx

            def update(self, mn, mx):
                orig = (self.least, self.most)

                # Apply new limits to what we know about this set already
                self.least = max(mn, self.least)
                self.most = min(mx, self.most)

                return orig != (self.least, self.most)

            def __repr__(self):
                return "MinMax"+str(self)

            def __str__(self):
                return F"({self.least},{self.most})"

        def add(subset, mn, mx):
            nonlocal changed
            if mn > len(subset):
                raise "Error Crossed the streams"
            if mx > len(subset):
                raise "Error Crossed the streams"
            if mn > mx:
                raise "Error Crossed the streams"
            if subset not in kg:
                kg[subset] = MinMax(mn, mx)
                chg = True
            else:
                chg = kg[subset].update(mn, mx)
            changed = changed or chg

            ks = kg[subset]
            if ks.least == 0 and ks.most == len(subset):
                # This is not news
                chg = False

            if ks.least > ks.most:
                raise "Error Crossed the streams"

            return chg

        # Add what we know about all the remaining mines if not many cells remaining
        remaining = self.board - self.exposed - self.marked
        mines = self.game.mines - len(self.marked)
        if mines < 5 and len(remaining) < 30:
            add(tuple(sorted(remaining)), mines, mines)

        safes = set()
        marks = set()
        # Compile knowledge of limits (min max) in every proper subset
        for cell, info in self.know.items():
            v = info.value
            s = tuple(sorted(info.strangers))
            add(s, v, v)

        while changed:
            changed = False

            print("  Subset by 1:")
            # Apply compiled knowledge against all subsets
            # e.g. [A,B,C,D]: min=2, max=3
            #      ==>   [A,B,C]: min=1, max=3  (max is constrained only by set size)
            #      ==>   [A,B]: min=0, max=2
            #      ==>   [A]: min=0, max=1
            for subset, kk in kg.copy().items():
                v = len(subset)-1
                if v and kk.least > 1:
                    for subset2 in combinations(subset, v):
                        sp = tuple(sorted(subset2))
                        add(sp, kk.least-1, v)

            # Atmost can be limited by atleast[{subsets}]
            # e.g. [A, B, C, D].most=2 & [A, B].least=1 ==>  [C, D].most=(2-1)
            # Atleast can be limited by atmost[{subsets}]
            # e.g. [A, B, C, D].least=3 & [A, B, C].most=2 ==>  [D].least=(3-2)
            for subset, kk in kg.copy().items():
                for i in range(1,len(subset)):
                    for subset2 in combinations(subset, len(subset)-i):
                        if subset2 in kg:
                            s = tuple(sorted(set(subset) - set(subset2)))
                            ks = kg[subset2]
                            mn = max(kk.least - ks.most, 0)
                            mx = min(kk.most - ks.least, len(s))
                            add(s, mn, mx)

        for subset, kk in kg.items():
            if kk.least == len(subset):
                marks |= set(subset)

            if kk.most > len(subset):
                raise "Error Crossed the streams"
            if kk.most == 0:
                safes |= set(subset)

        print(F"Collaboration found {len(marks)} marks and {len(safes)} safes")
        return (marks, safes)


    def reveal(self, x, y):
        print(F"Reveal {x},{y}")
        expo = self.game.reveal(x,y)
        self.exposed |= expo
        self.frontier |= expo
        self.frontier = set([cell for cell in self.frontier if self.game.readCell(*cell)])
        self.updateGraph(expo)
        self.display()

    def display(self):
        print(F"Revealed: {len(self.exposed)}   Marked: {len(self.marked)}    Frontier: {len(self.frontier)}")
        self.game.display()

    def test(self):
        while not self.game.gameover:
            x, y = randrange(self.game.height), randrange(self.game.width)
            if randrange(2) == 1:
                self.reveal(x,y)
            else:
                self.mark(x,y)

    def findNewMarks(self):
        ''' Walk the frontier set and find spots that I know have a bomb. '''
        bombs = set()
        for cell, info in self.know.items():
            bombs |= info.getBombs()
        return bombs

    def findNewSafes(self):
        ''' Walk the frontier set and find spots that I know have a bomb. '''
        safes = set()
        for cell, info in self.know.items():
            safes |= info.getSafes()
        return safes


    def play(self):
        while not self.game.gameover:
            # TODO: limit search to updated graph entries
            marks = self.findNewMarks()
            safes = self.findNewSafes()
            print(F"Found: {len(marks)} bombs and {len(safes)} safes")

            if not marks and not safes:
                # Try to collaborate between cells
                marks, safes = self.collaborate()


            for cell in marks:
                self.mark(*cell)

            for cell in safes:
                self.reveal(*cell)

            if not safes and not marks:
                break

        print("="*60)
        self.game.xray()

        if len(self.marked) == self.game.mines:
            self.game.end()
            print("I WON!  "*10)
        else:
            print ("HELP!!  "*10)
            print("FAILED.  I failed to solve this game. The only way forward I can see is to guess.")

def main():

    randseed = int(time())

    parser = argparse.ArgumentParser(description='Solving minesweeper.')
    parser.add_argument('-s', '--seed', type=int, default=int(time()),
                        help='a value to seed the random generator to replay specific games')

    # TODO: --width, --height, --mines, --easy, --hard, --medium, --quiet
    args = parser.parse_args()

    # seed the RNG
    randseed = args.seed
    seed(randseed)

    # Solve the game
    solver = Solve()
    solver.play()

    print(F"You can run this same game again by using {sys.argv[0]} --seed {randseed}")


main()