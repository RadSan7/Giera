import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import random
import numpy as np

# === KONFIGURACJA ===
WIDTH, HEIGHT = 1024, 768
FOV = 65
SPEED = 0.12
MOUSE_SENS = 0.15

# === KOLORY ===
C_SKY = (0.05, 0.05, 0.07)
C_AMBIENT = (0.1, 0.1, 0.15)

# === STAN GRY ===
pos = [0.0, 1.7, 0.0]
rot = [0.0, 0.0]
vel_y = 0.0

# === ŚWIAT ===
walls = []
crystals = []
texture_ids = {}

def init_world():
    # Obeliski (x, z, scale_xz, height)
    # Zewnętrzne granice
    for x in range(-30, 31, 10):
        walls.append((x, 30, 3, 12))
        walls.append((x, -30, 3, 12))
    for z in range(-20, 21, 10):
        walls.append((-30, z, 3, 12))
        walls.append((30, z, 3, 12))
        
    # Wewnętrzne ruiny
    walls.extend([
        (-10, 10, 2, 8), (10, 10, 2, 8),
        (-10, -10, 2, 8), (10, -10, 2, 8),
        (0, 15, 4, 15), (0, -15, 4, 15) # Wielkie wieże
    ])

    # Kryształy (x, y, z)
    for i in range(8):
        crystals.append([
            random.uniform(-15, 15),
            random.uniform(1.5, 3.0),
            random.uniform(-15, 15)
        ])

# === GEOMETRIA & TEKSTURY ===

def gen_noise_texture(size, dark=True):
    arr = np.random.normal(0.5, 0.1, (size, size, 3))
    if dark: base = np.array([0.25, 0.22, 0.22])
    else: base = np.array([0.4, 0.4, 0.42])
    
    arr = base + (arr - 0.5) * 0.15
    arr = np.clip(arr, 0, 1)
    
    img = (arr * 255).astype(np.uint8)
    surface = pygame.surfarray.make_surface(img)
    
    # Rysy i pęknięcia
    col = (30, 30, 35)
    for _ in range(40):
        x, y = random.randint(0, size), random.randint(0, size)
        pygame.draw.line(surface, col, (x, y), (x+random.randint(-20,20), y+random.randint(-20,20)), 1)
        
    return pygame.image.tostring(surface, "RGB", 1)

def create_textures():
    # Ściana
    tid_wall = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tid_wall)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, 512, 512, 0, GL_RGB, GL_UNSIGNED_BYTE, gen_noise_texture(512, True))
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glGenerateMipmap(GL_TEXTURE_2D)
    texture_ids['wall'] = tid_wall
    
    # Podłoga
    tid_floor = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tid_floor)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, 512, 512, 0, GL_RGB, GL_UNSIGNED_BYTE, gen_noise_texture(512, False))
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glGenerateMipmap(GL_TEXTURE_2D)
    texture_ids['floor'] = tid_floor

def draw_obelisk(x, z, scale, height):
    """Rysuje zwężający się obelisk (Obelisk)"""
    glPushMatrix()
    glTranslatef(x, 0, z)
    
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_ids['wall'])
    glColor3f(1, 1, 1) # White modulation
    
    top_scale = scale * 0.6 # Zwęża się ku górze
    
    glBegin(GL_QUADS)
    # Przód
    glNormal3f(0, 0, 1)
    glTexCoord2f(0, 0); glVertex3f(-scale/2, 0, scale/2)
    glTexCoord2f(1, 0); glVertex3f(scale/2, 0, scale/2)
    glTexCoord2f(1, 1); glVertex3f(top_scale/2, height, top_scale/2)
    glTexCoord2f(0, 1); glVertex3f(-top_scale/2, height, top_scale/2)
    # Tył
    glNormal3f(0, 0, -1)
    glTexCoord2f(0, 0); glVertex3f(scale/2, 0, -scale/2)
    glTexCoord2f(1, 0); glVertex3f(-scale/2, 0, -scale/2)
    glTexCoord2f(1, 1); glVertex3f(-top_scale/2, height, -top_scale/2)
    glTexCoord2f(0, 1); glVertex3f(top_scale/2, height, -top_scale/2)
    # Lewo
    glNormal3f(-1, 0, 0)
    glTexCoord2f(0, 0); glVertex3f(-scale/2, 0, -scale/2)
    glTexCoord2f(1, 0); glVertex3f(-scale/2, 0, scale/2)
    glTexCoord2f(1, 1); glVertex3f(-top_scale/2, height, top_scale/2)
    glTexCoord2f(0, 1); glVertex3f(-top_scale/2, height, -top_scale/2)
    # Prawo
    glNormal3f(1, 0, 0)
    glTexCoord2f(0, 0); glVertex3f(scale/2, 0, scale/2)
    glTexCoord2f(1, 0); glVertex3f(scale/2, 0, -scale/2)
    glTexCoord2f(1, 1); glVertex3f(top_scale/2, height, -top_scale/2)
    glTexCoord2f(0, 1); glVertex3f(top_scale/2, height, top_scale/2)
    # Góra (zamknięcie)
    glNormal3f(0, 1, 0)
    glTexCoord2f(0, 0); glVertex3f(-top_scale/2, height, top_scale/2)
    glTexCoord2f(1, 0); glVertex3f(top_scale/2, height, top_scale/2)
    glTexCoord2f(1, 1); glVertex3f(top_scale/2, height, -top_scale/2)
    glTexCoord2f(0, 1); glVertex3f(-top_scale/2, height, -top_scale/2)
    glEnd()
    
    glDisable(GL_TEXTURE_2D)
    glPopMatrix()

def draw_crystal_gem(x, y, z):
    """Rysuje Ośmiościan (Octahedron) - Kryształ dusz"""
    glPushMatrix()
    glTranslatef(x, y, z)
    
    # Animacja lewitacji i obrotu
    t = pygame.time.get_ticks() * 0.002
    glRotatef(t * 30, 0, 1, 0)
    glRotatef(math.sin(t)*20, 1, 0, 0)
    
    glDisable(GL_TEXTURE_2D)
    # Kolor: Jasny błękit/biel, świecący
    glMaterialfv(GL_FRONT, GL_EMISSION, (0.2, 0.4, 0.5, 1.0)) # Świeci sam z siebie
    glColor3f(0.6, 0.8, 1.0)
    
    scale = 0.6
    
    glBegin(GL_TRIANGLES)
    # 8 ścian ośmiościanu
    # Góra (y+)
    glNormal3f(0, 1, 1); glVertex3f(0, scale, 0); glVertex3f(scale, 0, 0); glVertex3f(0, 0, scale)
    glNormal3f(0, 1, -1); glVertex3f(0, scale, 0); glVertex3f(0, 0, -scale); glVertex3f(scale, 0, 0)
    glNormal3f(-1, 1, -1); glVertex3f(0, scale, 0); glVertex3f(-scale, 0, 0); glVertex3f(0, 0, -scale)
    glNormal3f(-1, 1, 1); glVertex3f(0, scale, 0); glVertex3f(0, 0, scale); glVertex3f(-scale, 0, 0)
    # Dół (y-)
    glNormal3f(0, -1, 1); glVertex3f(0, -scale, 0); glVertex3f(0, 0, scale); glVertex3f(scale, 0, 0)
    glNormal3f(0, -1, -1); glVertex3f(0, -scale, 0); glVertex3f(scale, 0, 0); glVertex3f(0, 0, -scale)
    glNormal3f(-1, -1, -1); glVertex3f(0, -scale, 0); glVertex3f(0, 0, -scale); glVertex3f(-scale, 0, 0)
    glNormal3f(-1, -1, 1); glVertex3f(0, -scale, 0); glVertex3f(-scale, 0, 0); glVertex3f(0, 0, scale)
    glEnd()
    
    # Reset Emission
    glMaterialfv(GL_FRONT, GL_EMISSION, (0, 0, 0, 1))
    glPopMatrix()

def draw_scene():
    # Podłoga
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_ids['floor'])
    glBegin(GL_QUADS)
    glNormal3f(0, 1, 0)
    glTexCoord2f(0, 0); glVertex3f(-60, 0, -60)
    glTexCoord2f(12, 0); glVertex3f(60, 0, -60)
    glTexCoord2f(12, 12); glVertex3f(60, 0, 60)
    glTexCoord2f(0, 12); glVertex3f(-60, 0, 60)
    glEnd()
    glDisable(GL_TEXTURE_2D)
    
    # Obeliski
    for w in walls:
        draw_obelisk(w[0], w[1], w[2], w[3])
        
    # Kryształy
    for c in crystals:
        draw_crystal_gem(c[0], c[1], c[2])

def main():
    global pos, rot, vel_y
    
    pygame.init()
    pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Antigravity - Ruins")
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)
    
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    
    # Mroczne oświetlenie
    glLightModelfv(GL_LIGHT_MODEL_AMBIENT, C_AMBIENT)
    
    # 0: Księżyc
    glEnable(GL_LIGHT0)
    glLightfv(GL_LIGHT0, GL_POSITION, (30, 60, 30, 0)) 
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.25, 0.25, 0.35, 1.0)) # Niebieskawy
    
    # 1: Ogień gracza
    glEnable(GL_LIGHT1)
    glLightfv(GL_LIGHT1, GL_DIFFUSE, (0.8, 0.5, 0.2, 1.0))
    glLightf(GL_LIGHT1, GL_CONSTANT_ATTENUATION, 0.5)
    glLightf(GL_LIGHT1, GL_LINEAR_ATTENUATION, 0.08)
    glLightf(GL_LIGHT1, GL_QUADRATIC_ATTENUATION, 0.01)
    
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT, GL_AMBIENT_AND_DIFFUSE)
    
    # Mgła
    glEnable(GL_FOG)
    glFogfv(GL_FOG_COLOR, C_SKY + (1.0,))
    glFogi(GL_FOG_MODE, GL_LINEAR)
    glFogf(GL_FOG_START, 10.0)
    glFogf(GL_FOG_END, 50.0)
    
    create_textures()
    init_world()
    clock = pygame.time.Clock()
    
    while True:
        clock.tick(60)
        for e in pygame.event.get():
            if e.type == QUIT or (e.type == KEYDOWN and e.key == K_ESCAPE): return
            
        # Myszka
        if pygame.mouse.get_focused():
            cx, cy = WIDTH // 2, HEIGHT // 2
            mx, my = pygame.mouse.get_pos()
            dx, dy = mx - cx, my - cy
            if dx or dy:
                pygame.mouse.set_pos(cx, cy)
                rot[0] += dx * MOUSE_SENS
                rot[1] = max(-89, min(89, rot[1] + dy * MOUSE_SENS))
                
        # Ruch
        keys = pygame.key.get_pressed()
        yaw = math.radians(rot[0])
        fx, fz = math.sin(yaw), -math.cos(yaw)
        rx, rz = math.cos(yaw), math.sin(yaw)
        
        if keys[K_w]: pos[0] += fx * SPEED; pos[2] += fz * SPEED
        if keys[K_s]: pos[0] -= fx * SPEED; pos[2] -= fz * SPEED
        if keys[K_a]: pos[0] -= rx * SPEED; pos[2] -= rz * SPEED
        if keys[K_d]: pos[0] += rx * SPEED; pos[2] += rz * SPEED
        
        # Fizyka
        if keys[K_SPACE] and pos[1] <= 1.8: vel_y = 0.15
        if keys[K_g]: vel_y += 0.01; vel_y *= 0.95
        else: vel_y -= 0.01
        pos[1] += vel_y
        if pos[1] < 1.7: pos[1] = 1.7; vel_y = 0
        
        # Światło
        glLightfv(GL_LIGHT1, GL_POSITION, (*pos, 1.0))
        glLightf(GL_LIGHT1, GL_CONSTANT_ATTENUATION, 0.5 + random.uniform(-0.05, 0.05))

        # Render
        glClearColor(*C_SKY, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        gluLookAt(pos[0], pos[1], pos[2],
                  pos[0] + math.sin(yaw), pos[1] - math.sin(math.radians(rot[1])), pos[2] - math.cos(yaw),
                  0, 1, 0)
                  
        draw_scene()
        pygame.display.flip()

if __name__ == "__main__":
    main()
