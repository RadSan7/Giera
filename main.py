import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import random
import numpy as np # Teraz mamy numpy!

# --- KONFIGURACJA ---
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
FOV = 60 # Lekko węższy FOV dla klimatu
MOVESPEED = 0.15 # Wolniej, bardziej ciężko
GRAVITY = 0.015
JUMP_STRENGTH = 0.25
MOUSE_SENSITIVITY = 0.15

# --- KOLORY (DARK FANTASY) ---
COLOR_STONE_LIGHT = (0.6, 0.6, 0.65) # Jaśniejsze kamienie
COLOR_STONE_DARK = (0.3, 0.3, 0.35)
COLOR_FLOOR_MAIN = (0.3, 0.3, 0.3)   # Jaśniejsza podłoga
COLOR_FLOOR_ACCENT = (0.25, 0.1, 0.1) # Krwawe akcenty
COLOR_SKY = (0.1, 0.1, 0.12) # Ciemnoszary (bezpieczniejszy niż fiolet)
COLOR_TORCH = (1.0, 0.6, 0.2) # Ogień
COLOR_CRYSTAL = (0.2, 0.8, 1.0) # Magiczny błękit

# --- STAN GRY ---
camera_pos = [0.0, 5.0, 0.0] # Spawn wysoko (5m), żeby spaść na ziemię
camera_rot = [0.0, -15.0] # Patrzymy lekko w dół, żeby widzieć podłogę
velocity_y = 0.0
on_ground = False
holding_object = None

# --- DANE ŚWIATA ---
pillars = [] # (x, z, radius, height)
crystals = [] # [x, y, z, r, g, b, vx, vy, vz, size]
texture_ids = {}

def create_level():
    global pillars, crystals
    
    # Tworzymy "Las Kolumn" zamiast ścian
    # Granice mapy (gęsto rozmieszczone kolumny)
    for x in range(-25, 26, 5):
        pillars.append((x, -25, 2, 8))
        pillars.append((x, 25, 2, 8))
    for z in range(-20, 21, 5):
        pillars.append((-25, z, 2, 8))
        pillars.append((25, z, 2, 8))
        
    # Labirynt z kolumn
    layout = [
        (-10, 10), (5, 10), (10, 5), (-5, 0),
        (0, -8), (-12, -5), (8, -5), (15, 0)
    ]
    for px, pz in layout:
         # Losowa wysokość i grubość dla organicznego wyglądu
        h = random.uniform(4, 7)
        r = random.uniform(1.5, 2.5)
        pillars.append((px, pz, r, h))

    # Magiczne kryształy (do rzucania)
    for _ in range(8):
        crystals.append([
            random.uniform(-15, 15), random.uniform(5, 8), random.uniform(-15, 15),
            0.5, 0.2, 0.8, # Fioletowy bazowy
            0, 0, 0,
            random.uniform(0.4, 0.7) # Rozmiar
        ])

# --- TEKSTURY (PROCEDURALNE KAMIENIE) ---

def create_texture(name, width, height, generator_func):
    surface = pygame.Surface((width, height))
    generator_func(surface)
    texture_data = pygame.image.tostring(surface, "RGB", 1)
    
    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, texture_data)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glGenerateMipmap(GL_TEXTURE_2D) # Ładniejsze oddalanie
    texture_ids[name] = tex_id

def gen_stone(surface):
    # Generuje teksturę kamienia z pęknięciami
    w, h = surface.get_size()
    # Tło
    surface.fill((50, 50, 60))
    # Szum
    arr = pygame.PixelArray(surface)
    for _ in range(2000):
        x, y = random.randint(0, w-1), random.randint(0, h-1)
        c = random.randint(30, 80)
        arr[x, y] = (c, c, c+10)
    # Pęknięcia
    for _ in range(10):
        x1, y1 = random.randint(0, w), random.randint(0, h)
        x2, y2 = x1 + random.randint(-20, 20), y1 + random.randint(-20, 20)
        pygame.draw.line(surface, (20, 20, 30), (x1, y1), (x2, y2), 1)
    del arr

def gen_floor_tiles(surface):
    w, h = surface.get_size()
    surface.fill((20, 20, 25))
    step = 64
    for y in range(0, h, step):
        for x in range(0, w, step):
            col = (40, 40, 50)
            if random.random() < 0.1: col = (60, 30, 30) # Krwawa płytka
            pygame.draw.rect(surface, col, (x+2, y+2, step-4, step-4))

def init_graphics():
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_CULL_FACE)
    glShadeModel(GL_SMOOTH) # Gładkie cieniowanie (Gouraud)
    
    # Mroczna mgła (poprawiona - startuje dalej)
    glEnable(GL_FOG)
    glFogfv(GL_FOG_COLOR, COLOR_SKY + (1.0,))
    glFogi(GL_FOG_MODE, GL_LINEAR)
    glFogf(GL_FOG_START, 10.0)  # Jeszcze dalej (10m)
    glFogf(GL_FOG_END, 40.0)
    
    # Oświetlenie (Jaśniejsze)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0) # Światło "Księżyca"
    glLightfv(GL_LIGHT0, GL_POSITION,  (20, 100, 20, 0.0))
    glLightfv(GL_LIGHT0, GL_AMBIENT,   (0.4, 0.4, 0.5, 1.0)) # Znacznie jaśniejszy ambient
    glLightfv(GL_LIGHT0, GL_DIFFUSE,   (0.7, 0.7, 0.8, 1.0)) # Jaśniejsze światło główne
    
    glEnable(GL_LIGHT1) # "Pochodnia gracza"
    glLightfv(GL_LIGHT1, GL_DIFFUSE,   (1.0, 0.8, 0.6, 1.0)) # Mocniejsza pochodnia
    glLightf(GL_LIGHT1, GL_CONSTANT_ATTENUATION, 0.8)
    glLightf(GL_LIGHT1, GL_LINEAR_ATTENUATION, 0.05) # Mniejsze tłumienie (dalej świeci)
    glLightf(GL_LIGHT1, GL_QUADRATIC_ATTENUATION, 0.005)
    
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT, GL_AMBIENT_AND_DIFFUSE)
    
    # Tekstury
    create_texture("stone", 256, 256, gen_stone)
    create_texture("floor", 256, 256, gen_floor_tiles)

# --- GEOMETRIA ---

def draw_pillar(x, z, r, h):
    glPushMatrix()
    glTranslatef(x, 0, z)
    
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_ids["stone"])
    glColor3f(1.0, 1.0, 1.0) # Biały modułuje teksturę
    
    # Rysowanie cylindra "z palca" (Quad strip)
    sides = 8 # Ośmiokątne kolumny (Dark Fantasy style)
    glBegin(GL_QUAD_STRIP)
    for i in range(sides + 1):
        angle = 2 * math.pi * i / sides
        nx, nz = math.cos(angle), math.sin(angle)
        
        glNormal3f(nx, 0, nz)
        glTexCoord2f(i / sides, 0); glVertex3f(nx*r, 0, nz*r)
        glTexCoord2f(i / sides, h/2); glVertex3f(nx*r, h, nz*r) # h/2 to powtarzanie tekstury
    glEnd()
    
    glDisable(GL_TEXTURE_2D)
    glPopMatrix()

def draw_crystal(x, y, z, size, color):
    glPushMatrix()
    glTranslatef(x, y, z)
    # Efekt pulsującego lewitowania
    scale = size + math.sin(pygame.time.get_ticks() * 0.005) * 0.05
    glScalef(scale, scale * 1.5, scale) # Wydłużony ostrosłup
    glRotatef(pygame.time.get_ticks() * 0.1, 0, 1, 0) # Obrót
    
    # Kryształ świeci
    glDisable(GL_LIGHTING) 
    glColor3fv(color)
    
    # Ostrosłup (2 piramidy złączone podstawami)
    glBegin(GL_TRIANGLES)
    # Góra
    glVertex3f(0, 1, 0); glVertex3f(1, 0, 1); glVertex3f(1, 0, -1)
    glVertex3f(0, 1, 0); glVertex3f(1, 0, -1); glVertex3f(-1, 0, -1)
    glVertex3f(0, 1, 0); glVertex3f(-1, 0, -1); glVertex3f(-1, 0, 1)
    glVertex3f(0, 1, 0); glVertex3f(-1, 0, 1); glVertex3f(1, 0, 1)
    # Dół
    glVertex3f(0, -1, 0); glVertex3f(1, 0, -1); glVertex3f(1, 0, 1)
    glVertex3f(0, -1, 0); glVertex3f(-1, 0, -1); glVertex3f(1, 0, -1)
    glVertex3f(0, -1, 0); glVertex3f(-1, 0, 1); glVertex3f(-1, 0, -1)
    glVertex3f(0, -1, 0); glVertex3f(1, 0, 1); glVertex3f(-1, 0, 1)
    glEnd()
    
    glEnable(GL_LIGHTING)
    glPopMatrix()
    
    # Magiczna poświata (prosty Point Light w miejscu kryształu)
    # (OpenGL Fixed function supportuje tylko 8 świateł, więc nie robimy tego dla wszystkich,
    # ale tu symulujemy to kolorem)

def draw_scene():
    # Podłoga
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_ids["floor"])
    glColor3f(1, 1, 1)
    glBegin(GL_QUADS)
    glNormal3f(0, 1, 0)
    glTexCoord2f(0, 0); glVertex3f(-50, 0, -50)
    glTexCoord2f(25, 0); glVertex3f(50, 0, -50)
    glTexCoord2f(25, 25); glVertex3f(50, 0, 50)
    glTexCoord2f(0, 25); glVertex3f(-50, 0, 50)
    glEnd()
    glDisable(GL_TEXTURE_2D)
    
    # Kolumny
    for p in pillars:
        draw_pillar(p[0], p[1], p[2], p[3])
        
    # Kryształy
    for c in crystals:
        draw_crystal(c[0], c[1], c[2], c[9], (c[3], c[4], c[5]))

# --- LOGIKA ---

def check_collisions(pos, r=0.5):
    if pos[1] < 1.0: pos[1]=1.0; return True, "floor"
    
    # Kolizja kołowa z kolumnami
    for px, pz, pr, ph in pillars:
        dx = pos[0] - px
        dz = pos[2] - pz
        dist = math.sqrt(dx*dx + dz*dz)
        min_dist = r + pr
        if dist < min_dist:
            # Wypychamy gracza
            push = min_dist - dist
            nx, nz = dx/dist, dz/dist
            pos[0] += nx * push
            pos[2] += nz * push
            return False, "wall"
            
    return False, None

def raycast_crystals():
    start = np.array(camera_pos)
    
    yaw_rad = math.radians(camera_rot[0])
    pitch_rad = math.radians(camera_rot[1])
    # Wektor patrzenia
    direction = np.array([
        math.sin(yaw_rad) * math.cos(pitch_rad),
        -math.sin(pitch_rad),
        -math.cos(yaw_rad) * math.cos(pitch_rad)
    ])
    
    best_dist = 8.0
    best_idx = None
    
    for i, c in enumerate(crystals):
        pos = np.array(c[:3])
        to_obj = pos - start
        dist = np.linalg.norm(to_obj)
        if dist > best_dist: continue
        
        to_obj_norm = to_obj / dist
        dot = np.dot(direction, to_obj_norm)
        if dot > 0.96: # Bardzo precyzyjne celowanie
            best_dist = dist
            best_idx = i
            
    return best_idx

def main():
    global camera_pos, camera_rot, velocity_y, holding_object, on_ground
    
    pygame.init()
    pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Antigravity - Dark Fantasy")
    pygame.event.set_grab(True)
    pygame.mouse.set_visible(False)
    
    create_level()
    init_graphics()
    
    clock = pygame.time.Clock()
    
    while True:
        dt = clock.tick(60)
        
        for event in pygame.event.get():
            if event.type == QUIT: pygame.quit(); return
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE: pygame.quit(); return
                if event.key == K_SPACE and on_ground: velocity_y = JUMP_STRENGTH
            if event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                    if holding_object is None:
                        idx = raycast_crystals()
                        if idx is not None: holding_object = idx
                    else:
                        # Rzut magicznym kryształem
                        yaw_rad = math.radians(camera_rot[0])
                        pitch_rad = math.radians(camera_rot[1])
                        dir_x = math.sin(yaw_rad) * math.cos(pitch_rad)
                        dir_y = -math.sin(pitch_rad)
                        dir_z = -math.cos(yaw_rad) * math.cos(pitch_rad)
                        
                        crystals[holding_object][6] = dir_x * 0.8
                        crystals[holding_object][7] = dir_y * 0.8
                        crystals[holding_object][8] = dir_z * 0.8
                        holding_object = None

        # --- UPDATE ---
        
        # Oświetlenie pochodni podąża za graczem
        glLightfv(GL_LIGHT1, GL_POSITION, (*camera_pos, 1.0))
        # Migotanie pochodni
        flicker = 1.0 + random.uniform(-0.1, 0.1)
        glLightf(GL_LIGHT1, GL_CONSTANT_ATTENUATION, 0.5 * flicker)
        
        # Myszka
        if pygame.mouse.get_focused():
            target_x, target_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
            mx, my = pygame.mouse.get_pos()
            diff_x, diff_y = mx - target_x, my - target_y
            if diff_x != 0 or diff_y != 0:
                pygame.mouse.set_pos((target_x, target_y))
                camera_rot[0] += diff_x * MOUSE_SENSITIVITY
                camera_rot[1] += diff_y * MOUSE_SENSITIVITY
                camera_rot[1] = max(-89, min(89, camera_rot[1]))
        
        # Klawisze
        keys = pygame.key.get_pressed()
        yaw_rad = math.radians(camera_rot[0])
        dx, dz = math.sin(yaw_rad), -math.cos(yaw_rad)
        sx, sz = math.cos(yaw_rad), math.sin(yaw_rad)
        speed = MOVESPEED * (1.8 if keys[K_LSHIFT] else 1)
        
        if keys[K_w]: camera_pos[0]+=dx*speed; camera_pos[2]+=dz*speed
        if keys[K_s]: camera_pos[0]-=dx*speed; camera_pos[2]-=dz*speed
        if keys[K_a]: camera_pos[0]-=sx*speed; camera_pos[2]-=sz*speed
        if keys[K_d]: camera_pos[0]+=sx*speed; camera_pos[2]+=sz*speed
        
        # Grawitacja
        grav = GRAVITY
        if keys[K_g]: grav = -0.01; velocity_y *= 0.95
        velocity_y -= grav
        camera_pos[1] += velocity_y
        
        is_hit, _ = check_collisions(camera_pos)
        if is_hit: velocity_y = 0; on_ground = True
        else: on_ground = False
        
        # Update kryształów
        yaw_rad = math.radians(camera_rot[0])
        pitch_rad = math.radians(camera_rot[1])
        dir_x = math.sin(yaw_rad) * math.cos(pitch_rad)
        dir_y = -math.sin(pitch_rad)
        dir_z = -math.cos(yaw_rad) * math.cos(pitch_rad)
        target = [camera_pos[0] + dir_x*3, camera_pos[1] + dir_y*3, camera_pos[2] + dir_z*3]
        
        for i, c in enumerate(crystals):
            if i == holding_object:
                # Lerp do ręki
                c[0] += (target[0]-c[0])*0.2
                c[1] += (target[1]-c[1])*0.2
                c[2] += (target[2]-c[2])*0.2
                c[6]=c[7]=c[8]=0
            else:
                if c[1] > 1.0: c[7] -= GRAVITY; c[0]+=c[6]; c[1]+=c[7]; c[2]+=c[8]
                else: c[1]=1.0; c[7]=-c[7]*0.6; c[6]*=0.9; c[8]*=0.9 # Odbicie

        # --- RENDER ---
        glClearColor(*COLOR_SKY, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        # Zwiększyłem near plane do 0.5 (bezpieczniej dla glębi)
        gluPerspective(FOV, (SCREEN_WIDTH/SCREEN_HEIGHT), 0.5, 100.0) 
        
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        gluLookAt(camera_pos[0], camera_pos[1], camera_pos[2],
                  camera_pos[0] + dir_x, camera_pos[1] + dir_y, camera_pos[2] + dir_z,
                  0, 1, 0)
                  
        draw_scene()
        pygame.display.flip()

if __name__ == "__main__":
    main()
