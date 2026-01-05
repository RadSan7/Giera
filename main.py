import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import random

# === KONFIGURACJA ===
WIDTH, HEIGHT = 1024, 768
FOV = 70
SPEED = 0.15
MOUSE_SENS = 0.15

# === STAN GRY ===
pos = [0.0, 1.7, 0.0]  # Pozycja gracza (wysokość oczu 1.7m)
rot = [0.0, 0.0]       # Yaw, Pitch
vel_y = 0.0

# === ŚWIAT ===
walls = []  # (x, z, width, depth)
cubes = []  # [x, y, z]

def init_world():
    # Ściany zewnętrzne
    walls.extend([
        (0, 25, 50, 1), (0, -25, 50, 1),
        (25, 0, 1, 50), (-25, 0, 1, 50)
    ])
    # Ściany wewnętrzne
    walls.extend([
        (-10, 10, 15, 1), (5, 5, 1, 10),
        (10, -5, 10, 1), (-5, -10, 1, 15)
    ])
    # Kostki do rzucania
    for i in range(6):
        cubes.append([
            random.uniform(-15, 15),
            1.0,
            random.uniform(-15, 15)
        ])

# === RYSOWANIE ===

def draw_box(x, y, z, sx, sy, sz, r, g, b):
    """Rysuje prostopadłościan"""
    glColor3f(r, g, b)
    glPushMatrix()
    glTranslatef(x, y, z)
    glScalef(sx, sy, sz)
    
    glBegin(GL_QUADS)
    # Przód
    glNormal3f(0, 0, 1)
    glVertex3f(-0.5, -0.5, 0.5)
    glVertex3f(0.5, -0.5, 0.5)
    glVertex3f(0.5, 0.5, 0.5)
    glVertex3f(-0.5, 0.5, 0.5)
    # Tył
    glNormal3f(0, 0, -1)
    glVertex3f(0.5, -0.5, -0.5)
    glVertex3f(-0.5, -0.5, -0.5)
    glVertex3f(-0.5, 0.5, -0.5)
    glVertex3f(0.5, 0.5, -0.5)
    # Lewo
    glNormal3f(-1, 0, 0)
    glVertex3f(-0.5, -0.5, -0.5)
    glVertex3f(-0.5, -0.5, 0.5)
    glVertex3f(-0.5, 0.5, 0.5)
    glVertex3f(-0.5, 0.5, -0.5)
    # Prawo
    glNormal3f(1, 0, 0)
    glVertex3f(0.5, -0.5, 0.5)
    glVertex3f(0.5, -0.5, -0.5)
    glVertex3f(0.5, 0.5, -0.5)
    glVertex3f(0.5, 0.5, 0.5)
    # Góra
    glNormal3f(0, 1, 0)
    glVertex3f(-0.5, 0.5, 0.5)
    glVertex3f(0.5, 0.5, 0.5)
    glVertex3f(0.5, 0.5, -0.5)
    glVertex3f(-0.5, 0.5, -0.5)
    # Dół
    glNormal3f(0, -1, 0)
    glVertex3f(-0.5, -0.5, -0.5)
    glVertex3f(0.5, -0.5, -0.5)
    glVertex3f(0.5, -0.5, 0.5)
    glVertex3f(-0.5, -0.5, 0.5)
    glEnd()
    glPopMatrix()

def draw_floor():
    """Rysuje podłogę - duży zielony kwadrat"""
    glColor3f(0.2, 0.5, 0.2)
    glBegin(GL_QUADS)
    glNormal3f(0, 1, 0)
    glVertex3f(-50, 0, -50)
    glVertex3f(50, 0, -50)
    glVertex3f(50, 0, 50)
    glVertex3f(-50, 0, 50)
    glEnd()

def draw_scene():
    # Podłoga
    draw_floor()
    
    # Ściany (szare)
    for w in walls:
        draw_box(w[0], 1.5, w[1], w[2], 3, w[3], 0.6, 0.6, 0.6)
    
    # Kostki (kolorowe)
    for i, c in enumerate(cubes):
        hue = i / len(cubes)
        r = abs(hue * 6 - 3) - 1
        g = 2 - abs(hue * 6 - 2)
        b = 2 - abs(hue * 6 - 4)
        r, g, b = max(0, min(1, r)), max(0, min(1, g)), max(0, min(1, b))
        draw_box(c[0], c[1], c[2], 0.6, 0.6, 0.6, r, g, b)

def draw_crosshair():
    """Celownik 2D"""
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, WIDTH, HEIGHT, 0, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    glDisable(GL_LIGHTING)
    glDisable(GL_DEPTH_TEST)
    glColor3f(1, 1, 1)
    
    cx, cy = WIDTH // 2, HEIGHT // 2
    glBegin(GL_LINES)
    glVertex2f(cx - 10, cy)
    glVertex2f(cx + 10, cy)
    glVertex2f(cx, cy - 10)
    glVertex2f(cx, cy + 10)
    glEnd()
    
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

# === GŁÓWNA PĘTLA ===

def main():
    global pos, rot, vel_y
    
    pygame.init()
    pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Antigravity 3D")
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)
    
    # OpenGL setup - MINIMALISTYCZNY
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    
    # Jedno białe światło z góry
    glLightfv(GL_LIGHT0, GL_POSITION, (0, 50, 0, 1))
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.4, 0.4, 0.4, 1))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.8, 0.8, 0.8, 1))
    
    # BRAK MGŁY, BRAK MODELU POSTACI, BRAK NICZEGO INNEGO
    
    init_world()
    clock = pygame.time.Clock()
    
    while True:
        clock.tick(60)
        
        # Events
        for e in pygame.event.get():
            if e.type == QUIT:
                pygame.quit()
                return
            if e.type == KEYDOWN and e.key == K_ESCAPE:
                pygame.quit()
                return
        
        # Mouse look
        if pygame.mouse.get_focused():
            cx, cy = WIDTH // 2, HEIGHT // 2
            mx, my = pygame.mouse.get_pos()
            dx, dy = mx - cx, my - cy
            if dx != 0 or dy != 0:
                pygame.mouse.set_pos(cx, cy)
                rot[0] += dx * MOUSE_SENS
                rot[1] = max(-89, min(89, rot[1] + dy * MOUSE_SENS))
        
        # Movement
        keys = pygame.key.get_pressed()
        yaw = math.radians(rot[0])
        fx, fz = math.sin(yaw), -math.cos(yaw)
        rx, rz = math.cos(yaw), math.sin(yaw)
        
        if keys[K_w]: pos[0] += fx * SPEED; pos[2] += fz * SPEED
        if keys[K_s]: pos[0] -= fx * SPEED; pos[2] -= fz * SPEED
        if keys[K_a]: pos[0] -= rx * SPEED; pos[2] -= rz * SPEED
        if keys[K_d]: pos[0] += rx * SPEED; pos[2] += rz * SPEED
        
        # Gravity & Jump
        if keys[K_SPACE] and pos[1] <= 1.7:
            vel_y = 0.2
        if keys[K_g]:
            vel_y += 0.01  # Antygrawitacja
        else:
            vel_y -= 0.01  # Grawitacja
        
        pos[1] += vel_y
        if pos[1] < 1.7:
            pos[1] = 1.7
            vel_y = 0
        
        # === RENDER ===
        glClearColor(0.3, 0.5, 0.8, 1)  # Niebieskie niebo
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        # Perspektywa
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(FOV, WIDTH / HEIGHT, 0.1, 500)  # Bardzo daleki zasięg
        
        # Kamera
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        pitch = math.radians(rot[1])
        yaw = math.radians(rot[0])
        look_x = pos[0] + math.sin(yaw) * math.cos(pitch)
        look_y = pos[1] - math.sin(pitch)
        look_z = pos[2] - math.cos(yaw) * math.cos(pitch)
        
        gluLookAt(pos[0], pos[1], pos[2], look_x, look_y, look_z, 0, 1, 0)
        
        # Rysowanie
        draw_scene()
        draw_crosshair()
        
        pygame.display.flip()

if __name__ == "__main__":
    main()
