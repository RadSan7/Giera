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
COLOR_WALL = (0.7, 0.7, 0.7)
COLOR_FLOOR = (1.0, 1.0, 1.0) # Biały bo modulujemy teksturą
COLOR_SKY = (0.5, 0.7, 1.0)
COLOR_GOAL = (1.0, 0.0, 0.0)

# --- STAN GRY ---
camera_pos = [-15.0, 2.0, 15.0]
camera_rot = [0.0, 0.0]
velocity_y = 0.0
on_ground = False
holding_cube = None

# --- DANE ŚWIATA ---
walls = []
cubes = []
texture_ids = {}

def create_level():
    global walls, cubes
    # Zewnętrzne
    walls.append((0, 20, 40, 1))
    walls.append((0, -20, 40, 1))
    walls.append((20, 0, 1, 40))
    walls.append((-20, 0, 1, 40))
    # Labirynt
    walls.append((-10, 10, 15, 1)); walls.append((5, 10, 1, 10))
    walls.append((10, 5, 10, 1)); walls.append((-5, 0, 1, 15))
    walls.append((0, -8, 12, 1)); walls.append((-12, -5, 1, 12))
    walls.append((8, -5, 1, 10)); walls.append((15, 0, 1, 8))

    for _ in range(10):
        cubes.append([
            random.uniform(-15, 15), random.uniform(5, 10), random.uniform(-15, 15),
            random.random(), random.random(), random.random(), 
            0, 0, 0
        ])

# --- TEKSTURY I OŚWIETLENIE ---

def create_texture(name, width, height, generator_func):
    surface = pygame.Surface((width, height))
    generator_func(surface)
    texture_data = pygame.image.tostring(surface, "RGB", 1)
    
    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, texture_data)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST) # Retro pixel look
    texture_ids[name] = tex_id

def gen_checkerboard(surface):
    w, h = surface.get_size()
    surface.fill((200, 200, 200)) # Jasny
    for y in range(0, h, 32):
        for x in range(0, w, 32):
            if (x//32 + y//32) % 2 == 0:
                pygame.draw.rect(surface, (100, 150, 100), (x, y, 32, 32)) # Zielony ciemny

def gen_noise(surface):
    w, h = surface.get_size()
    px = pygame.PixelArray(surface)
    for y in range(h):
        for x in range(w):
            c = random.randint(100, 160)
            px[x, y] = (c, c, c)
    del px

def init_graphics():
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_CULL_FACE) # Optymalizacja (nie rysuje tyłu ścian)
    
    # Oświetlenie
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL) # Kolory obiektów działają z oświetleniem
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    
    glLightfv(GL_LIGHT0, GL_POSITION,  (20, 50, 20, 1.0)) # Słońce z góry
    glLightfv(GL_LIGHT0, GL_AMBIENT,   (0.3, 0.3, 0.3, 1.0)) # Jasne cienie
    glLightfv(GL_LIGHT0, GL_DIFFUSE,   (0.9, 0.9, 0.8, 1.0)) # Ciepłe światło
    
    # Mgła (ukrywa koniec mapy)
    glEnable(GL_FOG)
    glFogfv(GL_FOG_COLOR, COLOR_SKY + (1.0,))
    glFogi(GL_FOG_MODE, GL_LINEAR)
    glFogf(GL_FOG_START, 20.0)
    glFogf(GL_FOG_END, 60.0)
    
    # Generowanie tekstur
    create_texture("floor", 256, 256, gen_checkerboard)
    create_texture("wall", 128, 128, gen_noise)

# --- RYSOWANIE ---

def draw_box(x, y, z, sx, sy, sz, color, tex_name=None):
    glPushMatrix()
    glTranslatef(x, y, z)
    glScalef(sx, sy, sz)
    glColor3fv(color)
    
    if tex_name:
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, texture_ids[tex_name])
    else:
        glDisable(GL_TEXTURE_2D)
    
    glBegin(GL_QUADS)
    
    # Przód
    glNormal3f(0, 0, 1)
    glTexCoord2f(0, 0); glVertex3f(-0.5, -0.5, 0.5)
    glTexCoord2f(1, 0); glVertex3f(0.5, -0.5, 0.5)
    glTexCoord2f(1, 1); glVertex3f(0.5, 0.5, 0.5)
    glTexCoord2f(0, 1); glVertex3f(-0.5, 0.5, 0.5)
    # Tył
    glNormal3f(0, 0, -1)
    glTexCoord2f(0, 0); glVertex3f(0.5, -0.5, -0.5)
    glTexCoord2f(1, 0); glVertex3f(-0.5, -0.5, -0.5)
    glTexCoord2f(1, 1); glVertex3f(-0.5, 0.5, -0.5)
    glTexCoord2f(0, 1); glVertex3f(0.5, 0.5, -0.5)
    # Prawo
    glNormal3f(1, 0, 0)
    glTexCoord2f(0, 0); glVertex3f(0.5, -0.5, 0.5)
    glTexCoord2f(1, 0); glVertex3f(0.5, -0.5, -0.5)
    glTexCoord2f(1, 1); glVertex3f(0.5, 0.5, -0.5)
    glTexCoord2f(0, 1); glVertex3f(0.5, 0.5, 0.5)
    # Lewo
    glNormal3f(-1, 0, 0)
    glTexCoord2f(0, 0); glVertex3f(-0.5, -0.5, -0.5)
    glTexCoord2f(1, 0); glVertex3f(-0.5, -0.5, 0.5)
    glTexCoord2f(1, 1); glVertex3f(-0.5, 0.5, 0.5)
    glTexCoord2f(0, 1); glVertex3f(-0.5, 0.5, -0.5)
    # Góra
    glNormal3f(0, 1, 0)
    glTexCoord2f(0, 0); glVertex3f(-0.5, 0.5, 0.5)
    glTexCoord2f(sx, 0); glVertex3f(0.5, 0.5, 0.5) # Powtarzanie textury na górze
    glTexCoord2f(sx, sz); glVertex3f(0.5, 0.5, -0.5)
    glTexCoord2f(0, sz); glVertex3f(-0.5, 0.5, -0.5)
    # Dół
    glNormal3f(0, -1, 0)
    glVertex3f(-0.5, -0.5, -0.5); glVertex3f(0.5, -0.5, -0.5)
    glVertex3f(0.5, -0.5, 0.5); glVertex3f(-0.5, -0.5, 0.5)
    
    glEnd()
    glPopMatrix()
    
def draw_shadow(x, y, z, scale):
    """Rysuje prosty cień (bloba) pod obiektem"""
    glDisable(GL_LIGHTING) # Cień nie świeci
    glDisable(GL_TEXTURE_2D)
    glEnable(GL_BLEND) # Przezroczystość
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glDepthMask(GL_FALSE) # Nie psuj bufora głębokości (żeby nie przenikał podłogi)
    
    glPushMatrix()
    glTranslatef(x, 0.01, z) # Ciut nad podłogą
    glScalef(scale, 1, scale)
    
    glBegin(GL_QUADS)
    glColor4f(0, 0, 0, 0.4) # Czarny, 40% widoczności
    glVertex3f(-0.5, 0, 0.5); glVertex3f(0.5, 0, 0.5)
    glVertex3f(0.5, 0, -0.5); glVertex3f(-0.5, 0, -0.5)
    glEnd()
    
    glPopMatrix()
    
    glDepthMask(GL_TRUE)
    glDisable(GL_BLEND)
    glEnable(GL_LIGHTING)

def draw_scene():
    # Podłoga (Teksturowana, powtarzana 10 razy)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_ids["floor"])
    glColor3f(1, 1, 1)
    
    glBegin(GL_QUADS)
    glNormal3f(0, 1, 0)
    glTexCoord2f(0, 0); glVertex3f(-30, 0, -30)
    glTexCoord2f(20, 0); glVertex3f(30, 0, -30) # 20 powtórzeń tekstury
    glTexCoord2f(20, 20); glVertex3f(30, 0, 30)
    glTexCoord2f(0, 20); glVertex3f(-30, 0, 30)
    glEnd()
    
    # Ściany
    for w in walls:
        draw_box(w[0], 1.5, w[1], w[2], 3, w[3], COLOR_WALL, "wall")
        
    # Cel
    draw_box(15, 1, -15, 2, 2, 2, COLOR_GOAL)
    
    # Kostki i Cienie
    for c in cubes:
        # Cień (im wyżej tym mniejszy i bardziej przezroczysty)
        shadow_scale = 0.8 * (1.0 / max(1.0, c[1]))
        draw_shadow(c[0], c[1], c[2], shadow_scale)
        # Kostka
        draw_box(c[0], c[1], c[2], 0.8, 0.8, 0.8, (c[3], c[4], c[5]))
        
# --- LOGIKA ---
def check_collision(pos, radius=0.5):
    if pos[1] < 1.0: 
        pos[1] = 1.0
        return True, "floor"
    hit = False
    player_rect = pygame.Rect(pos[0]-radius, pos[2]-radius, radius*2, radius*2)
    for w in walls:
        wall_rect = pygame.Rect(w[0] - w[2]/2, w[1] - w[3]/2, w[2], w[3])
        if player_rect.colliderect(wall_rect):
            hit = True
            dx = pos[0] - w[0]; dz = pos[2] - w[1]
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
    start = camera_pos
    direction = get_sight_vector()
    best_dist = 10.0
    best_idx = None
    for i, c in enumerate(cubes):
        vx = c[0] - start[0]; vy = c[1] - start[1]; vz = c[2] - start[2]
        dist = math.sqrt(vx*vx + vy*vy + vz*vz)
        if dist > 10.0: continue
        dot = (vx*direction[0] + vy*direction[1] + vz*direction[2]) / dist
        if dot > 0.95 and dist < best_dist:
            best_dist = dist
            best_idx = i
    return best_idx

def main():
    global camera_pos, camera_rot, velocity_y, holding_cube, on_ground
    
    pygame.init()
    pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Antigravity 3D - Textures & Lighting")
    pygame.event.set_grab(True)
    pygame.mouse.set_visible(False)
    
    create_level()
    init_graphics() # Inicjalizacja tekstur i świateł
    
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
                    if holding_cube is None:
                        idx = raycast_cubes()
                        if idx is not None: holding_cube = idx
                    else:
                        sight = get_sight_vector()
                        cubes[holding_cube][6], cubes[holding_cube][7], cubes[holding_cube][8] = sight[0]*0.5, sight[1]*0.5, sight[2]*0.5
                        holding_cube = None

        # Myszka (blokowanie kursor na środku)
        if pygame.mouse.get_focused():
            target_x, target_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
            mx, my = pygame.mouse.get_pos()
            diff_x, diff_y = mx - target_x, my - target_y
            if diff_x != 0 or diff_y != 0:
                pygame.mouse.set_pos((target_x, target_y))
                camera_rot[0] += diff_x * MOUSE_SENSITIVITY
                camera_rot[1] += diff_y * MOUSE_SENSITIVITY
                camera_rot[1] = max(-89, min(89, camera_rot[1]))
        
        # Ruch
        keys = pygame.key.get_pressed()
        yaw_rad = math.radians(camera_rot[0])
        dx, dz = math.sin(yaw_rad), -math.cos(yaw_rad)
        sx, sz = math.cos(yaw_rad), math.sin(yaw_rad)
        
        speed = MOVESPEED * (2 if keys[K_LSHIFT] else 1)
        if keys[K_w]: camera_pos[0] += dx * speed; camera_pos[2] += dz * speed
        if keys[K_s]: camera_pos[0] -= dx * speed; camera_pos[2] -= dz * speed
        if keys[K_a]: camera_pos[0] -= sx * speed; camera_pos[2] -= sz * speed
        if keys[K_d]: camera_pos[0] += sx * speed; camera_pos[2] += sz * speed
            
        # Grawitacja
        current_gravity = GRAVITY
        if keys[K_g]: current_gravity = -0.01; velocity_y *= 0.95
        velocity_y -= current_gravity
        camera_pos[1] += velocity_y
        
        if check_collision(camera_pos)[0]: velocity_y = 0; on_ground = True
        else: on_ground = False
            
        # Fizyka kostek
        sight = get_sight_vector()
        target_pos = [camera_pos[0] + sight[0]*3, camera_pos[1] + sight[1]*3, camera_pos[2] + sight[2]*3]
        for i, c in enumerate(cubes):
            if i == holding_cube:
                c[0] += (target_pos[0]-c[0])*0.2; c[1] += (target_pos[1]-c[1])*0.2; c[2] += (target_pos[2]-c[2])*0.2
                c[6]=c[7]=c[8]=0
            else:
                if c[1] > 0.4: c[7] -= GRAVITY; c[0]+=c[6]; c[1]+=c[7]; c[2]+=c[8]
                else: c[1] = 0.4; c[7] = 0; c[6]*=0.9; c[8]*=0.9

        # Render
        glMatrixMode(GL_PROJECTION); glLoadIdentity(); gluPerspective(FOV, (SCREEN_WIDTH/SCREEN_HEIGHT), 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity()
        
        # Shake kamery przy bieganiu
        bob_y = math.sin(pygame.time.get_ticks() * 0.01) * 0.05 if (keys[K_w] or keys[K_s] or keys[K_a] or keys[K_d]) and on_ground else 0
        
        target = [camera_pos[0] + sight[0], camera_pos[1] + sight[1], camera_pos[2] + sight[2]]
        gluLookAt(camera_pos[0], camera_pos[1] + bob_y, camera_pos[2], target[0], target[1] + bob_y, target[2], 0, 1, 0)
        
        glClearColor(*COLOR_SKY, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        draw_scene()
        
        # Celownik
        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
        glOrtho(0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
        glDisable(GL_DEPTH_TEST); glDisable(GL_LIGHTING); glDisable(GL_TEXTURE_2D) # Wyłączamy efekty dla UI
        glColor3f(1, 1, 1)
        cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        glBegin(GL_LINES)
        glVertex2f(cx-10, cy); glVertex2f(cx+10, cy)
        glVertex2f(cx, cy-10); glVertex2f(cx, cy+10)
        glEnd()
        glEnable(GL_LIGHTING); glEnable(GL_DEPTH_TEST)
        glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)
        
        pygame.display.flip()

if __name__ == "__main__":
    main()
