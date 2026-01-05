import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import random
import numpy as np

# === KONFIGURACJA ===
WIDTH, HEIGHT = 1280, 720
FOV = 60
SPEED = 0.15
MOUSE_SENS = 0.15

# === KOLORY ===
C_SKY = (0.2, 0.2, 0.25) # Dużo jaśniejsze niebo (szaro-niebieskie)
C_AMBIENT = (0.5, 0.5, 0.5) # Dużo jaśniejszy ambient (żeby coś widzieć)

# === STAN GRY ===
STATE_MENU = 0
STATE_GAME = 1
game_state = STATE_MENU

pos = [0.0, 5.0, 0.0]
rot = [0.0, 0.0]
vel_y = 0.0
on_ground = False
fullscreen = False

# === ŚWIAT ===
objects = [] # (type, x, y, z, scale)
texture_ids = {}

def load_texture(name, filename):
    try:
        surf = pygame.image.load(filename).convert_alpha()
        data = pygame.image.tostring(surf, "RGBA", 1)
        w, h = surf.get_size()
        
        tid = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tid)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glGenerateMipmap(GL_TEXTURE_2D)
        
        texture_ids[name] = tid
        print(f"Loaded texture {name} from {filename}")
    except Exception as e:
        print(f"Failed to load texture {filename}: {e}")
        # Fallback texture (szachownica)
        surf = pygame.Surface((64, 64))
        surf.fill((100, 0, 100))
        data = pygame.image.tostring(surf, "RGBA", 1)
        tid = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tid)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 64, 64, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        texture_ids[name] = tid

def init_world():
    # Las (Drzewa)
    for _ in range(30):
        radius = random.uniform(15, 40)
        angle = random.uniform(0, 6.28)
        objects.append(('tree', math.cos(angle)*radius, 0, math.sin(angle)*radius, random.uniform(0.8, 1.5)))
        
    # Ruiny (Kamienie)
    for _ in range(10):
        objects.append(('rock', random.uniform(-10, 10), 0, random.uniform(-10, 10), random.uniform(0.5, 1.2)))

# === AUDIO (Wyłączone - Cisza) ===
def init_audio():
    pass # Cisza, bo szum wkurzał
    # pygame.mixer.init(44100, -16, 2, 2048)
    # ...

# === RYSOWANIE GEOMETRII ===

def draw_cylinder(radius, height, tex):
    glBindTexture(GL_TEXTURE_2D, texture_ids[tex])
    quad = gluNewQuadric()
    gluQuadricTexture(quad, GL_TRUE)
    gluCylinder(quad, radius, radius*0.8, height, 12, 1)

def draw_cone(base, height, tex):
    glBindTexture(GL_TEXTURE_2D, texture_ids[tex])
    quad = gluNewQuadric()
    gluQuadricTexture(quad, GL_TRUE)
    gluCylinder(quad, base, 0, height, 12, 1)

def draw_tree(x, y, z, s):
    glPushMatrix()
    glTranslatef(x, y, z)
    glScalef(s, s, s)
    
    # Pień
    glPushMatrix()
    glRotatef(-90, 1, 0, 0) # Cylinder rysuje się wzdłuż Z
    glColor3f(0.6, 0.5, 0.4)
    draw_cylinder(0.4, 3, 'bark')
    glPopMatrix()
    
    # Korona
    glPushMatrix()
    glTranslatef(0, 2, 0)
    glRotatef(-90, 1, 0, 0)
    glColor3f(0.8, 0.9, 0.8)
    draw_cone(2.0, 4, 'grass') # Używamy trawy jako liści (wygląda jak mech)
    glPopMatrix()
    
    glPopMatrix()

def draw_rock(x, y, z, s):
    glPushMatrix()
    glTranslatef(x, y, z)
    glScalef(s, s*0.7, s) # Spłaszczony
    
    glBindTexture(GL_TEXTURE_2D, texture_ids['stone'])
    glColor3f(0.7, 0.7, 0.7)
    
    # Prosta bryła skalna (Icosahedron-like)
    glBegin(GL_TRIANGLES)
    coords = [
        (0,1,0), (1,0,1), (1,0,-1), (-1,0,-1), (-1,0,1), (0,-1,0)
    ]
    # Góra
    v = coords
    glTexCoord2f(0.5, 1); glVertex3fv(v[0])
    glTexCoord2f(1, 0); glVertex3fv(v[1])
    glTexCoord2f(0, 0); glVertex3fv(v[2])
    
    glTexCoord2f(0.5, 1); glVertex3fv(v[0])
    glTexCoord2f(1, 0); glVertex3fv(v[2])
    glTexCoord2f(0, 0); glVertex3fv(v[3])
    
    glTexCoord2f(0.5, 1); glVertex3fv(v[0])
    glTexCoord2f(1, 0); glVertex3fv(v[3])
    glTexCoord2f(0, 0); glVertex3fv(v[4])
    
    glTexCoord2f(0.5, 1); glVertex3fv(v[0])
    glTexCoord2f(1, 0); glVertex3fv(v[4])
    glTexCoord2f(0, 0); glVertex3fv(v[1])
    glEnd()
    
    glPopMatrix()

def draw_scene():
    # Podłoga (Trawa)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_ids['grass'])
    glColor3f(0.6, 0.6, 0.6) # Przyciemniona
    glBegin(GL_QUADS)
    glNormal3f(0, 1, 0)
    glTexCoord2f(0, 0); glVertex3f(-100, 0, -100)
    glTexCoord2f(20, 0); glVertex3f(100, 0, -100)
    glTexCoord2f(20, 20); glVertex3f(100, 0, 100)
    glTexCoord2f(0, 20); glVertex3f(-100, 0, 100)
    glEnd()
    
    for obj in objects:
        t, x, y, z, s = obj
        if t == 'tree': draw_tree(x, y, z, s)
        elif t == 'rock': draw_rock(x, y, z, s)

# === MENU ===
def draw_text(text, x, y, size=40):
    font = pygame.font.SysFont('Arial', size, bold=True)
    surf = font.render(text, True, (255, 255, 255))
    text_data = pygame.image.tostring(surf, "RGBA", 1)
    w, h = surf.get_size()
    
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glWindowPos2i(x, HEIGHT - y)
    glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
    glDisable(GL_BLEND)

def draw_menu():
    glClearColor(0.1, 0.1, 0.1, 1) # Lekko szare tło zamiast czarnego
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    glOrtho(0, WIDTH, 0, HEIGHT, -1, 1)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
    
    glDisable(GL_LIGHTING) # Ważne: tekst rysujemy bez oświetlenia!
    glDisable(GL_DEPTH_TEST)
    
    draw_text("ANTIGRAVITY: DARK SOULS", WIDTH//2 - 200, HEIGHT//2 + 50, 50)
    draw_text("Press ENTER", WIDTH//2 - 80, HEIGHT//2 - 50, 30)
    
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    
    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)
    pygame.display.flip()

# === MAIN ===
def main():
    global game_state, pos, rot, vel_y, fullscreen, WIDTH, HEIGHT
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL | RESIZABLE)
    pygame.display.set_caption("Antigravity HD")
    init_audio()
    
    # Setup GL
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0); glEnable(GL_LIGHT1)
    glEnable(GL_COLOR_MATERIAL)
    glEnable(GL_FOG)
    glFogfv(GL_FOG_COLOR, C_SKY + (1.0,))
    glFogi(GL_FOG_MODE, GL_LINEAR)
    glFogf(GL_FOG_START, 20.0); glFogf(GL_FOG_END, 80.0)
    
    # Init Assets
    load_texture('grass', 'grass.png')
    load_texture('bark', 'bark.png')
    load_texture('stone', 'stone.png')
    init_world()
    
    clock = pygame.time.Clock()
    
    while True:
        dt = clock.tick(60)
        
        for e in pygame.event.get():
            if e.type == QUIT: return
            if e.type == KEYDOWN:
                if e.key == K_ESCAPE:
                    if game_state == STATE_GAME: game_state = STATE_MENU; pygame.mouse.set_visible(True)
                    else: return
                if e.key == K_RETURN and game_state == STATE_MENU:
                    game_state = STATE_GAME; pygame.mouse.set_visible(False)
                if e.key == K_f: # Toggle Fullscreen
                    fullscreen = not fullscreen
                    if fullscreen: screen = pygame.display.set_mode((0, 0), DOUBLEBUF | OPENGL | FULLSCREEN)
                    else: screen = pygame.display.set_mode((1280, 720), DOUBLEBUF | OPENGL | RESIZABLE)
                    w, h = screen.get_size()
                    WIDTH, HEIGHT = w, h
                    glViewport(0, 0, w, h)
            if e.type == VIDEORESIZE and not fullscreen:
                WIDTH, HEIGHT = e.w, e.h
                glViewport(0, 0, WIDTH, HEIGHT)
                
        if game_state == STATE_MENU:
            draw_menu()
            continue
            
        # GAME LOOP
        if pygame.mouse.get_focused():
            mid_x, mid_y = WIDTH//2, HEIGHT//2
            mx, my = pygame.mouse.get_pos()
            dx, dy = mx-mid_x, my-mid_y
            if dx or dy:
                pygame.mouse.set_pos(mid_x, mid_y)
                rot[0] += dx * MOUSE_SENS
                rot[1] = max(-89, min(89, rot[1] + dy * MOUSE_SENS))
        
        # Fizyka i Ruch
        keys = pygame.key.get_pressed()
        yaw = math.radians(rot[0])
        fx, fz = math.sin(yaw), -math.cos(yaw)
        rx, rz = math.cos(yaw), math.sin(yaw)
        
        if keys[K_w]: pos[0] += fx*SPEED; pos[2] += fz*SPEED
        if keys[K_s]: pos[0] -= fx*SPEED; pos[2] -= fz*SPEED
        if keys[K_a]: pos[0] -= rx*SPEED; pos[2] -= rz*SPEED
        if keys[K_d]: pos[0] += rx*SPEED; pos[2] += rz*SPEED
        
        if keys[K_SPACE] and pos[1] <= 2.2: vel_y = 0.2
        if keys[K_g]: vel_y += 0.01; vel_y *= 0.95
        else: vel_y -= 0.01
        pos[1] += vel_y
        if pos[1] < 2.0: pos[1] = 2.0; vel_y = 0
        
        # Render
        glClearColor(*C_SKY, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_PROJECTION); glLoadIdentity(); gluPerspective(FOV, WIDTH/HEIGHT, 0.5, 200.0)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity()
        
        pch = math.radians(rot[1])
        gluLookAt(pos[0], pos[1], pos[2], 
                  pos[0] + fx*math.cos(pch), pos[1] - math.sin(pch), pos[2] + fz*math.cos(pch), 
                  0, 1, 0)
        
        # Światło
        glLightfv(GL_LIGHT0, GL_POSITION, (20, 100, 20, 0)) # Księżyc
        glLightfv(GL_LIGHT0, GL_AMBIENT, C_AMBIENT + (1,))
        glLightfv(GL_LIGHT1, GL_POSITION, (*pos, 1)) # Pochodnia
        
        draw_scene()
        pygame.display.flip()

if __name__ == "__main__":
    main()
