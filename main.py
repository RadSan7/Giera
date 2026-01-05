import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import random

# --- KONFIGURACJA ---
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
FOV = 70
MOVESPEED = 0.2
GRAVITY = 0.02
JUMP_STRENGTH = 0.3
MOUSE_SENSITIVITY = 0.2

# --- KOLORY ---
COLOR_WALL = (0.5, 0.5, 0.5)
COLOR_FLOOR = (0.2, 0.8, 0.2)
COLOR_SKY = (0.5, 0.8, 1.0)
COLOR_GOAL = (1.0, 0.0, 0.0)

# --- STAN GRY ---
camera_pos = [-15.0, 2.0, 15.0] # Start w rogu
camera_rot = [0.0, 0.0] # Yaw, Pitch
velocity_y = 0.0
on_ground = False
holding_cube = None # Indeks trzymanej kostki

# --- DANE ŚWIATA ---
walls = []        # Lista krotek (x, z, sx, sz) - środek, rozmiar
cubes = []        # Lista list [x, y, z, r, g, b, vx, vy, vz] - pozycja, kolor, prędkość

# Generator Labiryntu (Ręczny)
def create_level():
    global walls, cubes
    # Zewnętrzne ściany
    walls.append((0, 20, 40, 1))
    walls.append((0, -20, 40, 1))
    walls.append((20, 0, 1, 40))
    walls.append((-20, 0, 1, 40))
    
    # Wewnętrzne
    walls.append((-10, 10, 15, 1))
    walls.append((5, 10, 1, 10))
    walls.append((10, 5, 10, 1))
    walls.append((-5, 0, 1, 15))
    walls.append((0, -8, 12, 1))
    walls.append((-12, -5, 1, 12))
    walls.append((8, -5, 1, 10))
    walls.append((15, 0, 1, 8))

    # Kostki
    for _ in range(10):
        cubes.append([
            random.uniform(-15, 15), # x
            random.uniform(5, 10),   # y (spadną)
            random.uniform(-15, 15), # z
            random.random(), random.random(), random.random(), # kolor
            0, 0, 0 # velocity
        ])

# --- RYSOWANIE ---

def draw_box(x, y, z, sx, sy, sz, color):
    glPushMatrix()
    glTranslatef(x, y, z)
    glScalef(sx, sy, sz)
    glColor3fv(color)
    
    glBegin(GL_QUADS)
    # Przód
    glVertex3f(-0.5, -0.5, 0.5); glVertex3f(0.5, -0.5, 0.5)
    glVertex3f(0.5, 0.5, 0.5); glVertex3f(-0.5, 0.5, 0.5)
    # Tył
    glVertex3f(-0.5, -0.5, -0.5); glVertex3f(-0.5, 0.5, -0.5)
    glVertex3f(0.5, 0.5, -0.5); glVertex3f(0.5, -0.5, -0.5)
    # Lewo
    glVertex3f(-0.5, -0.5, -0.5); glVertex3f(-0.5, -0.5, 0.5)
    glVertex3f(-0.5, 0.5, 0.5); glVertex3f(-0.5, 0.5, -0.5)
    # Prawo
    glVertex3f(0.5, -0.5, -0.5); glVertex3f(0.5, 0.5, -0.5)
    glVertex3f(0.5, 0.5, 0.5); glVertex3f(0.5, -0.5, 0.5)
    # Góra
    glVertex3f(-0.5, 0.5, -0.5); glVertex3f(-0.5, 0.5, 0.5)
    glVertex3f(0.5, 0.5, 0.5); glVertex3f(0.5, 0.5, -0.5)
    # Dół
    glVertex3f(-0.5, -0.5, -0.5); glVertex3f(0.5, -0.5, -0.5)
    glVertex3f(0.5, -0.5, 0.5); glVertex3f(-0.5, -0.5, 0.5)
    glEnd()
    glPopMatrix()

def draw_scene():
    # Podłoga
    draw_box(0, -0.5, 0, 60, 1, 60, COLOR_FLOOR)
    
    # Ściany
    for w in walls:
        draw_box(w[0], 1.5, w[1], w[2], 3, w[3], COLOR_WALL)
        
    # Cel
    draw_box(15, 1, -15, 2, 2, 2, COLOR_GOAL)
    
    # Kostki
    for c in cubes:
        draw_box(c[0], c[1], c[2], 0.8, 0.8, 0.8, (c[3], c[4], c[5]))

# --- LOGIKA ---

def check_collision(pos, radius=0.5):
    # Kolizja z podłogą
    if pos[1] < 1.0: # Wysokość gracza/oczu
        pos[1] = 1.0
        return True, "floor"
        
    # Prosta kolizja ze ścianami (AABB)
    hit = False
    player_rect = pygame.Rect(pos[0]-radius, pos[2]-radius, radius*2, radius*2)
    
    for w in walls:
        # Konwersja ściany na Rect 2D (zaniedbujemy oś Y dla ścian bo są wysokie)
        wall_rect = pygame.Rect(w[0] - w[2]/2, w[1] - w[3]/2, w[2], w[3])
        if player_rect.colliderect(wall_rect):
            hit = True
            # Wypychanie (bardzo proste)
            dx = pos[0] - w[0]
            dz = pos[2] - w[1]
            if abs(dx/w[2]) > abs(dz/w[3]):
                if dx > 0: pos[0] = w[0] + w[2]/2 + radius + 0.01
                else: pos[0] = w[0] - w[2]/2 - radius - 0.01
            else:
                if dz > 0: pos[2] = w[1] + w[3]/2 + radius + 0.01
                else: pos[2] = w[1] - w[3]/2 - radius - 0.01
    return False, "air"

def get_sight_vector():
    yaw_rad = math.radians(camera_rot[0])
    pitch_rad = math.radians(camera_rot[1])
    dx = math.sin(yaw_rad) * math.cos(pitch_rad)
    dy = -math.sin(pitch_rad)
    dz = -math.cos(yaw_rad) * math.cos(pitch_rad)
    return [dx, dy, dz]

def raycast_cubes():
    # Prosty raycast
    start = camera_pos
    direction = get_sight_vector()
    best_dist = 10.0
    best_idx = None
    
    for i, c in enumerate(cubes):
        # Wektor do kostki
        vx = c[0] - start[0]
        vy = c[1] - start[1]
        vz = c[2] - start[2]
        dist = math.sqrt(vx*vx + vy*vy + vz*vz)
        
        # Jeśli za daleko, pomiń
        if dist > 10.0: continue
        
        # Iloczyn skalarny żeby sprawdzić czy patrzymy w stronę kostki
        dot = (vx*direction[0] + vy*direction[1] + vz*direction[2]) / dist
        if dot > 0.95: # Patrzymy prawie prosto na nią
            if dist < best_dist:
                best_dist = dist
                best_idx = i
    return best_idx

def main():
    global camera_pos, camera_rot, velocity_y, holding_cube, on_ground
    
    pygame.init()
    pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Antigravity 3D")
    
    # Zablokowanie myszki
    pygame.event.set_grab(True)
    pygame.mouse.set_visible(False)
    
    create_level()
    
    clock = pygame.time.Clock()
    
    while True:
        dt = clock.tick(60)
        
        # --- EVENETY ---
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                return
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    pygame.quit()
                    return
                if event.key == K_SPACE and on_ground:
                    velocity_y = JUMP_STRENGTH
                    
            if event.type == MOUSEBUTTONDOWN:
                if event.button == 1: # Lewy PM
                    if holding_cube is None:
                        # Próba złapania
                        idx = raycast_cubes()
                        if idx is not None:
                            holding_cube = idx
                    else:
                        # Rzut
                        # Nadajemy prędkość w kierunku patrzenia
                        sight = get_sight_vector()
                        cubes[holding_cube][6] = sight[0] * 0.5
                        cubes[holding_cube][7] = sight[1] * 0.5
                        cubes[holding_cube][8] = sight[2] * 0.5
                        holding_cube = None

        # --- UPDATE ---
        
        # Myszka
        mx, my = pygame.mouse.get_rel()
        camera_rot[0] += mx * MOUSE_SENSITIVITY
        camera_rot[1] += my * MOUSE_SENSITIVITY
        camera_rot[1] = max(-89, min(89, camera_rot[1]))
        
        # Klawiatura
        keys = pygame.key.get_pressed()
        
        yaw_rad = math.radians(camera_rot[0])
        dx = math.sin(yaw_rad)
        dz = -math.cos(yaw_rad)
        sx = math.cos(yaw_rad) # Strafe vector
        sz = math.sin(yaw_rad)
        
        current_speed = MOVESPEED
        if keys[K_LSHIFT]: current_speed *= 2
        
        if keys[K_w]:
            camera_pos[0] += dx * current_speed
            camera_pos[2] += dz * current_speed
        if keys[K_s]:
            camera_pos[0] -= dx * current_speed
            camera_pos[2] -= dz * current_speed
        if keys[K_a]:
            camera_pos[0] -= sx * current_speed
            camera_pos[2] -= sz * current_speed
        if keys[K_d]:
            camera_pos[0] += sx * current_speed
            camera_pos[2] += sz * current_speed
            
        # Antygrawitacja
        current_gravity = GRAVITY
        if keys[K_g]:
            current_gravity = -0.01 # Latanie
            velocity_y *= 0.95 # Tłumienie
            
        # Fizyka gracza
        velocity_y -= current_gravity
        camera_pos[1] += velocity_y
        
        # Kolizje gracza
        hit_ground, _ = check_collision(camera_pos)
        if hit_ground:
            velocity_y = 0
            on_ground = True
        else:
            on_ground = False
            
        # Fizyka kostek
        sight = get_sight_vector()
        target_pos = [
            camera_pos[0] + sight[0] * 3,
            camera_pos[1] + sight[1] * 3,
            camera_pos[2] + sight[2] * 3
        ]
        
        for i, c in enumerate(cubes):
            if i == holding_cube:
                # Lerp do pozycji przed kamerą
                c[0] += (target_pos[0] - c[0]) * 0.2
                c[1] += (target_pos[1] - c[1]) * 0.2
                c[2] += (target_pos[2] - c[2]) * 0.2
                c[6], c[7], c[8] = 0, 0, 0 # Zeruj pęd
            else:
                # Grawitacja kostki
                if c[1] > 0.4: # Jeśli nad ziemią
                    c[7] -= GRAVITY
                    c[0] += c[6]
                    c[1] += c[7]
                    c[2] += c[8]
                else: 
                    c[1] = 0.4
                    c[7] = 0 # Stop
                    c[6] *= 0.9 # Tarcie
                    c[8] *= 0.9

        # --- RENDER FRAME ---
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(FOV, (SCREEN_WIDTH/SCREEN_HEIGHT), 0.1, 100.0)
        
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        # Ustawienie kamery
        # gluLookAt(eyeX, eyeY, eyeZ, centerX, centerY, centerZ, upX, upY, upZ)
        target = [
            camera_pos[0] + sight[0],
            camera_pos[1] + sight[1],
            camera_pos[2] + sight[2]
        ]
        gluLookAt(camera_pos[0], camera_pos[1], camera_pos[2],
                  target[0], target[1], target[2],
                  0, 1, 0)
        
        glClearColor(*COLOR_SKY, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glEnable(GL_DEPTH_TEST)
        
        draw_scene()
        
        # Celownik (2D Overlay) - Poprawiona wersja
        # 1. Przełącz na projekcję ortogonalną (2D)
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, -1, 1)
        
        # 2. Reset ModelView dla rysowania 2D
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        # 3. Rysowanie
        glDisable(GL_DEPTH_TEST)
        glColor3f(1, 1, 1)
        cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        
        glBegin(GL_LINES)
        glVertex2f(cx - 10, cy); glVertex2f(cx + 10, cy) # Pozioma
        glVertex2f(cx, cy - 10); glVertex2f(cx, cy + 10) # Pionowa
        glEnd()
        
        glEnable(GL_DEPTH_TEST)

        # 4. Sprzątanie (Odwrotna kolejność)
        glPopMatrix() # Zdejmij ModelView
        
        glMatrixMode(GL_PROJECTION)
        glPopMatrix() # Zdejmij Projection
        
        glMatrixMode(GL_MODELVIEW) # Wróć do normalnego trybu
        
        pygame.display.flip()

if __name__ == "__main__":
    main()
