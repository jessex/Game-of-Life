import random, pygame, math, csv, time
import threading, tkFileDialog, tkSimpleDialog
from Tkinter import *
from pygame.locals import *

generation = 0              #current generation of the game
population = 0              #current amount of living cells
cells = []                  #2-D array of cells in the game
game_state = "paused"       #current state of game - paused or running

cell_size =   10            #pixel size of one side of a cell
bezel_size =  30            #padding size allocated for buttons on top/bottom
width =      500            #width of the game surface
height =     500            #height of the game surface

speed = 2                   #speed of the game
occupancy = 0.25            #percentage of cells to occupy in random board

new_game = False            #whether to initialize an entirely new game
wrap_around = 0             #whether to wrap around the edges (1=yes, 0=no)
root = Tk()                 #root window surface

#cell colors
color_dead =  (255, 255, 255)
color_alive = (000, 000, 205)
#button colors
on_color =    (000, 191, 255)
off_color =   (211, 211, 211)
#window colors
line_color =  (000, 000, 000)
back_color =  (255, 255, 255)
text_color =  (000, 000, 000)

#rule sets which can be selected in settings (Life is default)
rule_sets = [ ["Life (Standard) - B3/S23", (3,), (2,3)],
              ["Life without Death - B3/S012345678", (3,), (0,1,2,3,4,5,6,7,8)],
              ["Maze - B3/S12345", (3,), (1,2,3,4,5)],
              ["Amoeba - B357/S1358", (3,5,7), (1,3,5,8)],
              ["HighLife - B36/S23", (3,6), (2,3)],
              ["Day & Night - B3678/S34678", (3,6,7,8), (3,4,6,7,8)],
              ["Walled Cities - B45678/S2345", (4,5,6,7,8), (2,3,4,5)],
              ["Gnarl - B1/S1", (1,), (1,)],
              ["Seeds - B2/S", (2,), ()] ]
active_rule = 0             #index of the active rule set in rule_sets

"""

************************************* GUI **************************************

"""

#Represents a single button on the main window of the game
class Button:

    def __init__(self, text, x_co, y_co, x_size, y_size):
        self.text = text
        self.x_co = x_co
        self.y_co = y_co
        self.x_size = x_size
        self.y_size = y_size
        self.status = False

    #determine if the button was clicked on
    def check_pressed(self, event):
        if event.type == MOUSEBUTTONDOWN:
            (y_m, x_m) = pygame.mouse.get_pos()
            if (y_m >= self.y_co and y_m <= self.y_co+self.y_size) and (x_m >= self.x_co and x_m <= self.x_co+self.x_size):
                if self.status == True:
                    self.status = False
                elif self.status == False:
                    self.status = True

    #draw the button with its text and shape
    def draw(self):
        if self.status == True:
            color = on_color
        elif self.status == False:
            color = off_color
       
        pygame.draw.rect(screen, color, (self.y_co, self.x_co, 
        self.y_size, self.x_size), 0)
        
        draw_text(self.text, 15, self.y_co+(self.y_size/2), 
        self.x_co+(self.x_size/2), (0, 0, 0))

#draws given text with provided color and coordinates (used for button text)
def draw_text(text, size, x_co, y_co, color):
    font = pygame.font.Font(None, size)
    text = font.render((text), 1, color)
    if x_co == -1:
        x = width/2
    else:
        x = x_co
    if y_co == -1:
        y = height/2
    else:
        y = y_co
    position = text.get_rect(centerx = x, centery = y)
    screen.blit(text, position)

#draws the generation label at the bottom left
def draw_gen():
    gen_str = "Generations: %d" % generation
    font = pygame.font.Font(None,12)
    text = font.render((gen_str), 1, text_color)
    position = text.get_rect(topleft=(5,(height+bezel_size+11)))
    screen.blit(text,position)

#draws the population label at the bottom left
def draw_pop():
    pop_str = "Population: %d" % population
    font = pygame.font.Font(None,12)
    text = font.render((pop_str), 1, text_color)
    position = text.get_rect(topleft=(104,(height+bezel_size+11)))
    screen.blit(text,position)

#draws the grid to show the cells in
def draw_grid(width, height, size):
    for cell in range(int(x_dim+1)):
        pygame.draw.line(screen, line_color, (0, (cell*size)+bezel_size), 
        (width, (cell*size)+bezel_size))
    for cell in range(int(y_dim-1)):
        pygame.draw.line(screen, line_color, ((cell*size)+size, bezel_size), 
        ((cell*size)+size, height))

#Represents a newly created settings dialog window
class SettingsDialog(tkSimpleDialog.Dialog):

    def body(self, master):
        #static labels
        Label(master, text="Cell Size:").grid(row=0, sticky="E")
        Label(master, text="Pixels").grid(row=0, column=2, sticky="W")
        Label(master, text="Cell Count:").grid(row=1, sticky="E")
        Label(master, text="Per Row").grid(row=1, column=2, sticky="W")
        Label(master, text="Random Ratio:").grid(row=2, sticky="E")
        Label(master, text="Rule Set:").grid(row=4, sticky="W")

        #scale label (dynamic)
        self.v = StringVar()
        self.scale_label = Label(master, textvariable=self.v)
        self.v.set(str(occupancy))
        self.scale_label.grid(row=2, sticky="W", column=2)

        #cell size text entry
        self.e = StringVar()
        self.size_e = Entry(master, width=16, textvariable=self.e)
        self.e.set(str(cell_size))
        self.size_e.grid(row=0, column=1)

        #cell count (per row) text entry
        self.c = StringVar()
        self.count_e = Entry(master, width=16, textvariable=self.c)
        self.c.set(str(int(x_dim)))
        self.count_e.grid(row=1, column=1)

        #random ratio scale
        self.occ_scale = Scale(master, from_=0, to=1, resolution = 0.05, 
        orient=HORIZONTAL, showvalue=0, sliderrelief=GROOVE, length=120,
        command=self.update_scale_label)
        self.occ_scale.set(occupancy)
        self.occ_scale.grid(row=2, column=1)

        #edge wrap around checkbutton
        self.w = IntVar()
        self.wrap = Checkbutton(master, text="Wrap Around Edges", 
        variable=self.w)
        self.w.set(int(wrap_around))
        self.wrap.grid(row=3, column=1, columnspan=2, sticky="W")

        #vertical scrollbar for rule set listbox
        self.y_scroll = Scrollbar(master, orient=VERTICAL)
        self.y_scroll.grid(row=5, column=3, sticky="N,S")

        #rule set listbox
        self.rule_list = Listbox(master, width=35, height=4, 
        activestyle="dotbox", yscrollcommand=self.y_scroll.set)
        self.rule_list.grid(row=5, column=0, columnspan=3, sticky="W")
        for rule in rule_sets:
            self.rule_list.insert(END, rule[0])

        self.y_scroll["command"] = self.rule_list.yview
        self.rule_list.selection_set(first=active_rule)
        
        return self.size_e #initial focus goes to cell size text entry

    #work-around to get a scale label on the side of a horizontal scale widget
    def update_scale_label(self, value):
        self.v.set(str(value))

    #return settings data on "OK" or "Cancel" click
    def apply(self):
        try:
            size = int(self.size_e.get())
            count = int(self.count_e.get())
            occ = float(self.occ_scale.get())
            wrap = int(self.w.get())
            rule = map(int, self.rule_list.curselection())
            self.result = size, count, occ, wrap, rule
        except:
            self.result == None

"""

************************************* LIFE *************************************

"""

#Represents an individual cell in the board
class Cell:

    def __init__(self, x, y, size):
        self.x = x
        self.y = y
        self.size = size
        self.state = False
        self.living = False
        self.neighbors = 0

    #counts the amount of currently living cells in the given cell's neighborhood
    def check_neighborhood(self):
        self.neighbors = 0
        
        try:
            for y in range(self.y-1, self.y+2): 
                try:  
                    for x in range(self.x-1, self.x+2):
                        if not (x >= x_dim or x < 0 or y >= y_dim or y < 0):
                            if (cells[y][x].living == True) and (self.x != x or self.y != y):
                                self.neighbors += 1
                        else: #cell on edge, neighborhood goes out of universe
                            if wrap_around == 1: #edge wrap around is on
                                if x >= x_dim:
                                    x = 0
                                elif x < 0:
                                    x = int(x_dim-1)
                                if y >= y_dim:
                                    y = 0
                                elif y < 0:
                                    y = int(x_dim-1)
                                if (cells[y][x].living == True) and (self.x != x or self.y != y):
                                    self.neighbors += 1
                        """
                            if wrap_around == 1: #wrap around is on
                            #sort of an ugly way to handle the edge wrap around
                            #and it has a bit of a performance effect, but it 
                            #works for now
                                y_check = y
                                x_check = x
                                if y < 0 and x < 0: #top left
                                    y_check = y_dim-1
                                    x_check = x_dim-1
                                elif y < 0 and x >= 0 and x <= x_dim-1: #top
                                    y_check = y_dim-1
                                elif y < 0 and x > x_dim-1: #top right
                                    y_check = y_dim-1
                                    x_check = 0
                                elif x > x_dim-1 and y >= 0 and y <= y_dim-1: #right
                                    x_check = 0
                                elif x > x_dim-1 and y > y_dim-1: #bottom right
                                    x_check = 0
                                    y_check = 0
                                elif y > y_dim-1 and x >= 0 and x <= x_dim-1: #bottom
                                    y_check = 0
                                elif y > y_dim-1 and x < 0: #bottom left
                                    y_check = 0
                                    x_check = x_dim-1
                                elif x < 0 and y >= 0 and y <= y_dim-1: #left
                                    x_check = x_dim-1

                                if (cells[int(y_check)][int(x_check)].living == True):
                                    self.neighbors += 1
                            """
                except: 
                    pass    
        except: 
            pass

    #outer loop to mark cell state for update in inner loop
    def check_state(self):
        global population
        self.check_neighborhood()

        if self.living == True: #check survival (is alive now)
            if self.neighbors in rule_sets[active_rule][2]: #not surviving
                self.state = True
            else: #surviving
                self.state = False
                population -= 1
        else: #check birth (is dead now)
            if self.neighbors in rule_sets[active_rule][1]: #being born
                self.state = True
                population += 1
            else:
                self.state = False

    #inner loop to update cell state based on outer loop
    def change_state(self):
        if self.state == True or self.state == "True":
            self.living = True
            screen.fill(color_alive, (self.x*cell_size,
            self.y*cell_size+bezel_size, cell_size, cell_size), 0)
        elif self.state == False or self.state == "False":
            self.living = False

    #draws cell if living by filling in its designated square
    def draw(self):
        if self.living == True:
            screen.fill(color_alive, (self.x*cell_size,
            self.y*cell_size+bezel_size, cell_size, cell_size), 0)
        
        
    #determine if cell was clicked and flip its state
    def click(self, event):
        global population
        if event.type == MOUSEBUTTONDOWN:
            (x_m, y_m) = pygame.mouse.get_pos()
            get_block(x_m, y_m)
            if y_block == self.y and x_block == self.x:
                if self.living == False:
                    self.state = True
                    population += 1
                else:
                    self.state = False
                    population -= 1

"""

************************************* GAME *************************************

"""

#Represents the entire game state (instantiate to initialize/start the game)
class Game:

    def __init__(self, wid, hgt, cel, title):
        global run_button, step_button, load_button, save_button, clear_button
        global quit_button, random_button, settings_button

        #calculate variables for button sizing and placement
        btn_xpad = 6
        btn_length = (wid - (4*btn_xpad) - 10)/5
        btn = btn_length+btn_xpad
        btn_width = bezel_size / 3 * 2
        btn_ypad = (bezel_size - btn_width) / 2
        bottom_y = hgt+bezel_size+btn_ypad
        
        run_button = Button("Play", btn_ypad, 5, btn_width, btn_length)
        step_button = Button("Step", btn_ypad, 5+btn, btn_width, btn_length)
        random_button = Button("Randomize", btn_ypad, 5+2*btn, btn_width, btn_length)
        clear_button = Button("Clear", btn_ypad, 5+3*btn, btn_width, btn_length)
        settings_button = Button("Settings", btn_ypad, 5+4*btn, btn_width, btn_length)
        load_button = Button("Load", bottom_y, 5+2*btn, btn_width, btn_length)
        save_button = Button("Save", bottom_y, 5+3*btn, btn_width, btn_length)
        quit_button = Button("Quit", bottom_y, 5+4*btn, btn_width, btn_length)

        #initialize and set up the window and its associated vars
        global screen, clock, root
        pygame.init()
        pygame.font.init()
        screen = pygame.display.set_mode((wid, hgt+bezel_size+bezel_size))
        pygame.display.set_caption(title)
        clock = pygame.time.Clock()
        root.withdraw()
        init_board(wid, hgt, cel)

        global width, height, cell_size
        width = wid
        height = hgt
        cell_size = cel

        global new_game
        new_game = False
        
        game_loop()

#initialize the game board with the given size specifications
def init_board(width, height, size):
    global x_dim, y_dim, cells, population
    
    x_dim = math.floor(width/size)
    y_dim = math.floor(height/size)

    cells = []
    for i in range(int(y_dim)):
        row = []
        for j in range(int(x_dim)):
            cell = Cell(j,i,size)
            row.append(cell)

        cells.append(row)

    population = 0


#initializes random board configuration with pre-set occupancy ratio
def randomize_board(width, height, size):
    global x_dim, y_dim, generation, cells, population
    
    x_dim = math.floor(width/size)
    y_dim = math.floor(height/size)

    cells = []
    for i in range(int(y_dim)):
        row = []
        for j in range(int(x_dim)):
            cell = Cell(j,i,cell_size)
            if random.random() < occupancy:
                cell.state = True
                population += 1
            row.append(cell)
        cells.append(row)

    generation = 0

#clear and reset the board
def clear_board():
    global cells, generation, population
    generation = population = 0
    for row in cells:
        for cell in row:
            cell.state = False

#returns the cell coordinate for the passed coordinates
def get_block(x, y):
    global y_block
    global x_block
    y_block = math.floor((y-bezel_size)/cell_size)
    x_block = math.floor(x/cell_size)

        
#main game structure, loops indefinitely, until game is told to stop running
def game_loop():
    global game_state, generation
    
    running = True
    stepping = False
    clearing = False
    game_state = "paused"
    
    while running: 
        screen.fill(back_color)
        
        if game_state == "running": #While Running
        
            generation += 1
            
            #check rules for survival for each cell
            for row in cells:
                for cell in row:
                    cell.check_state()

            #update and draw each cell on board (maintains pseudo-simultaneity)
            for row in cells:
                for cell in row:
                    cell.change_state()
                    #cell.draw()

            #process any mouse events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == MOUSEBUTTONDOWN:
                    run_button.check_pressed(event) #check if game was paused

            #if the run button was switched off, pause game
            if run_button.status == False:
                game_state = "paused"
                run_button.text = "Play"

            #finish the current step (if stepping)
            if stepping == True:
                game_state = "paused"
                stepping = False
                step_button.status = False

        elif game_state == "paused": #While Paused

            #change any outstanding cells and draw change
            for row in cells:
                for cell in row:
                    cell.change_state()
                    cell.draw()

            #check for any button presses
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == MOUSEBUTTONDOWN:
                    run_button.check_pressed(event)
                    step_button.check_pressed(event)
                    load_button.check_pressed(event)
                    save_button.check_pressed(event)
                    clear_button.check_pressed(event)
                    quit_button.check_pressed(event)
                    random_button.check_pressed(event)
                    settings_button.check_pressed(event)
                    for row in cells:
                        for cell in row:
                            cell.click(event)

            #process any button presses
            if run_button.status == True: #Pressed Play/Pause
                game_state = "running"
                run_button.text = "Pause"
            elif step_button.status == True: #Pressed Step
                game_state = "running"
                stepping = True
            elif load_button.status == True: #Pressed Load
                readCSV(tkFileDialog.askopenfilename(filetypes=[('CSV Files','.csv'), ('All Files','*')]))
                load_button.status = False
            elif save_button.status == True: #Pressed Save
                writeCSV(tkFileDialog.asksaveasfilename(defaultextension='.csv',filetypes=[('CSV Files','.csv')]))
                save_button.status = False
            elif settings_button.status == True: #Pressed Settings
                dia = SettingsDialog(root, "Game Settings")
                if dia.result != None:
                    settings_button.status = not process_settings(dia.result)
                else:
                    settings_button.status = False
                if new_game == True:
                    running = False
            elif clearing == True: #In the midst of clearing the board
                clear_button.status = False
                clearing = False   
            elif clear_button.status == True: #Pressed Clear
                clear_board()
                clearing = True         
            elif random_button.status == True: #Pressed Randomize
                clear_board()
                randomize_board(width, height, cell_size)
                random_button.status = False
            elif quit_button.status == True: #Pressed Quit
                running = False

        #redraw window
        run_button.draw()
        step_button.draw()
        load_button.draw()
        save_button.draw()
        clear_button.draw()
        quit_button.draw()
        random_button.draw()
        settings_button.draw()
        draw_grid(width, height+bezel_size, cell_size)
        draw_gen()
        draw_pop()
        pygame.display.flip()
        


"""

*********************************** UTILITY ************************************

"""

#change game settings based on results from dialog which were returned as tuple
#ordered as (cell_size, x_dim, occupancy, wrap_around, [active_rule])
def process_settings(results):
    global occupancy, cell_size, width, height, wrap_around, active_rule
    global new_game, new_width, new_height, new_cell_size

    prev_cs = cell_size
    prev_width = width

    try:
        active_rule = results[4][0]
        wrap_around = results[3]
        occupancy = results[2]
        cell_size = results[0]
        width = results[1] * cell_size
        height = width
    except:
        return False

    if cell_size != prev_cs or width != prev_width:
        new_game = True
        new_width = width
        new_height = height
        new_cell_size = cell_size
        
    return True

#read in a pattern saved as a .csv file and load the board
def readCSV(file):
    global cells, generation, population
    try:
        reader = csv.reader(open(file), delimiter=',', quotechar='|')
        x = y = 0
        population = 0
        for row in reader:
            for field in row:
                if field == "True" or field == "true":
                    try:
                        cells[y][x].state = True
                        population += 1
                    except: #if we read past the boundaries of our board
                        pass
                elif field == "False" or field == "false":
                    try:
                        cells[y][x].state = False
                    except:
                        pass
                x += 1
            y += 1
            x = 0
        generation = 0
    except: 
        pass

#write the current board state to a .csv file
def writeCSV(file):
    try:
        writer = csv.writer(open(file, 'w'), delimiter=',', quotechar='|')
        for y in range(int(y_dim)):
            row=[]
            for x in range(int(x_dim)):
                if (cells[y][x].state == True):
                    row.append(True)
                else:
                    row.append(False)
            writer.writerow(row)
    except: 
        pass

"""

************************************* MAIN *************************************

"""

if __name__ == "__main__":
    Game(width, height, cell_size, "Game of Life")
    while new_game == True:
        Game(new_width, new_height, new_cell_size, "Game of Life")




