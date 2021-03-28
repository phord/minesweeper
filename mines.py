# Minesweeper solver

from random import randrange, seed

class Cell:
    def __init__(self):
        self.hidden = True
        self.marked = False
        self.mine = False
        self.value = 0
        self.detonated = False

    def reveal(self):
        if self.mine:
            self.detonated = True
        return self.mine

    def mark(self):
        self.marked = not self.marked
        return self.marked

    def getValue(self):
        return None if self.hidden else self.value

    def __str__(self):
        if self.marked:
            return '🚩'
        elif self.hidden:
            return '🔲'
        elif self.value:
            return chr(ord('０') + self.value)
        else:
            return '  '

    # Display cell after game end
    def xray(self):
        if self.detonated:
            return '🔥'
        if self.marked:
            if self.mine:
                return '🚩'
            else:
                return '⍉!'
        elif self.mine:
            return '💣'
        else:
            return '  '

    def dump(self):
        if self.detonated:
            return '🔥'
        elif self.marked:
            if self.mine:
                return '🚩'
            else:
                return '⍉!'
        elif self.mine:
            return '💣'
        elif self.value:
            return chr(ord('０') + self.value)
        else:
            return '  '

class Game:
    def __init__(self, width, height, mines):
        self.width = width
        self.height = height
        self.mines = mines
        self.createGame()

    def initGrid(self):
        return [ [ Cell() for x in range(self.width)] for y in range(self.height)]

    def display(self):
        for row in self.grid:
            if self.gameover:
                disp = [ cell.xray() for cell in row]
            else:
                disp = [ str(cell) for cell in row]
            print(''.join(disp))
        print('--')

    def dump(self):
        for row in self.grid:
            disp = [ cell.dump() for cell in row]
            print(''.join(disp))
        print('--')

    def xray(self):
        for row in self.grid:
            disp = [ cell.xray() for cell in row]
            print(''.join(disp))
        print('--')

    def end(self):
        self.gameover = True

    def createGame(self):
        self.gameover = False
        self.started = False
        self.grid = self.initGrid()

        mines = self.mines
        while mines:
            x = randrange(0, self.height)
            y = randrange(0, self.width)
            if self.placeMine(x, y):
                mines -= 1

    def placeMine(self, x, y):
        if self.grid[x][y].mine:
            return False
        self.grid[x][y].mine = True
        self.grid[x][y].value = 9  # Should never display except during debug
        for x,y in self.getNeighbors(x, y):
            self.grid[x][y].value += 1
        return True

    def findFreeNeighbors(self, x, y):
        new = set([(x,y)])
        found = set()

        while new:
            found |= new
            next = set()
            for x,y in new:
                if self.grid[x][y].hidden and self.grid[x][y].value==0:
                    next |= self.getNeighbors(x, y)
            next -= found
            new = next
        return found

    def floodReveal(self, x, y):
        neighbors = self.findFreeNeighbors(x, y)

        for x,y in neighbors:
            self.grid[x][y].hidden = False

        return neighbors

    def readCell(self, x, y):
        ''' Return the displayed value on a cell, or None if cell is hidden '''
        return self.grid[x][y].getValue()

    def getNeighbors(self, x, y):
        ''' Get the coordinates of all the cells adjacent to the given position. '''
        minx = max(0, x-1)
        miny = max(0, y-1)
        maxx = min(self.height, x+2)
        maxy = min(self.width, y+2)
        return set([(X,Y) for X in range(minx, maxx) for Y in range(miny, maxy) if (X-x or Y-y)])

    def mark(self, x, y):
        '''
        Mark a cell as "has a bomb" (or remove a mark if already marked). For display purposes only.
        returns True if the cell is now marked
        '''
        if not self.grid[x][y].hidden:
            return False
        return self.grid[x][y].mark()

    def reveal(self, x, y):
        '''
        Reveal the cell at position x,y.
        returns the set of new cells that were revealed
        '''
        if not self.grid[x][y].hidden:
            return set()

        exposed = self.floodReveal(x,y)
        if not self.started:
            while len(exposed) < 5 or self.grid[x][y].mine:
                # Give the player a fighting chance. Draw a new grid if he doesn't expose at least 5 cells.
                self.createGame()
                exposed = self.floodReveal(x,y)

            self.started = True

        if self.grid[x][y].reveal():
            print("BOOM!")
            self.end()
            # fixme: Display board and exit

        # Returns the set
        return exposed


def test():
    ## Beginner: 12, 18, 12  (5%)
    ## Easy: 10, 7, 10    (14%)
    ## Med: 18, 12, 40    (19%)
    ## Hard: 18, 32, 100  (17%)
    ## HUGE: 48, 27, 220   (17%)
    ## Extreme: 18, 32, 150  (17%)
    game = Game(32, 18, 100)

    while not game.gameover:
        x, y = randrange(game.height), randrange(game.width)
        if randrange(2) == 1:
            print(F"Reveal {x},{y}")
            game.reveal(x,y)
        else:
            print(F"Mark {x},{y}")
            game.mark(x,y)

        game.display()

    game.dump()

# test()