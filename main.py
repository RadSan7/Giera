import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import random
import numpy as np
import struct

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
    # Obeliski
    for x in range(-30, 31, 15):
        walls.append((x, 30, 4, 12))
        walls.append((x, -30, 4, 12))
    for z in range(-20, 21, 15):
        walls.append((-30, z, 4, 12))
        walls.append((30, z, 4, 12))
        
    walls.extend([
        (-10, 10, 2, 8), (10, 10, 2, 8),
        (-10, -10, 2, 8), (10, -10, 2, 8),
        (0, 15, 5, 18), (0, -15, 5, 18)
    ])

    for i in range(8):
        crystals.append([
            random.uniform(-15, 15),
            random.uniform(2.0, 4.0), # Wyżej, żeby było widać
            random.uniform(-15, 15)
        ])

# === PROCEDURALNE AUDIO (Dark Fantasy Drone) ===
def init_audio():
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    # Generowanie drona (niskie częstotliwości + szum)
    duration = 5.0 # sekundy
    sample_rate = 22050
    n_samples = int(duration * sample_rate)
    
    # Bufor drona
    buf = np.zeros((n_samples, 2), dtype=np.int16)
    
    # 1. Bass Drone (55Hz - A1)
    t = np.linspace(0, duration, n_samples, False)
    wave1 = np.sin(2 * np.pi * 55 * t) * 8000
    
    # 2. Detuned Overtone (112Hz)
    wave2 = np.sin(2 * np.pi * 112 * t) * 4000
    
    # 3. Noise (Wiatr)
    noise = np.random.uniform(-2000, 2000, n_samples)
    
    # Mix
    audio = (wave1 + wave2 + noise).astype(np.int16)
    
    # Stereo spreading
    buf[:, 0] = audio # L
    buf[:, 1] = audio # R
    
    sound = pygame.sndarray.make_sound(buf)
    sound.play(loops=-1, fade_ms=2000)

# === TEKSTURY (FIX NA CZARNY EKRAN) ===
def gen_checker_texture():
    """Fallback: Prosta szachownica RGBA jeśli numpy noise zawiedzie"""
    surface = pygame.Surface((256, 256))
    surface.fill((50, 50, 50))
    for y in range(0, 256, 32):
        for x in range(0, 256, 32):
            if (x//32 + y//32) % 2 == 0:
                pygame.draw.rect(surface, (80, 75, 70), (x, y, 32, 32)) # Brązowy kamień
                # Pęknięcie
                pygame.draw.line(surface, (30,30,30), (x+5, y+5), (x+25, y+25), 2)
    return pygame.image.tostring(surface, "RGBA", 1)

def create_textures():
    # Używamy prostszej metody generowania (Surface draw), która jest pewniejsza na Macu
    tex_data = gen_checker_texture()
    
    # Ustawienia wyrównania pamięci dla Textur
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
    
    tid = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tid)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 256, 256, 0, GL_RGBA, GL_UNSIGNED_BYTE, tex_data)
    
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR) # Tylko Linear, bez Mipmap (mniej błędów)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    
    texture_ids['stone'] = tid

# === RYSOWANIE ===
def draw_obelisk(x, z, scale, height):
    glPushMatrix()
    glTranslatef(x, 0, z)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_ids['stone'])
    glColor3f(0.8, 0.8, 0.8) # Lekko przyciemniamy biel
    
    top = scale * 0.5
    
    glBegin(GL_QUADS)
    # Przód
    glNormal3f(0, 0, 1)
    glTexCoord2f(0, 0); glVertex3f(-scale, 0, scale)
    glTexCoord2f(1, 0); glVertex3f(scale, 0, scale)
    glTexCoord2f(1, 1); glVertex3f(top, height, top)
    glTexCoord2f(0, 1); glVertex3f(-top, height, top)
    # Tył
    glNormal3f(0, 0, -1)
    glTexCoord2f(0, 0); glVertex3f(scale, 0, -scale)
    glTexCoord2f(1, 0); glVertex3f(-scale, 0, -scale)
    glTexCoord2f(1, 1); glVertex3f(-top, height, -top)
    glTexCoord2f(0, 1); glVertex3f(top, height, -top)
    # Lewo
    glNormal3f(-1, 0, 0)
    glTexCoord2f(0, 0); glVertex3f(-scale, 0, -scale)
    glTexCoord2f(1, 0); glVertex3f(-scale, 0, scale)
    glTexCoord2f(1, 1); glVertex3f(-top, height, top)
    glTexCoord2f(0, 1); glVertex3f(-top, height, -top)
    # Prawo
    glNormal3f(1, 0, 0)
    glTexCoord2f(0, 0); glVertex3f(scale, 0, scale)
    glTexCoord2f(1, 0); glVertex3f(scale, 0, -scale)
    glTexCoord2f(1, 1); glVertex3f(top, height, -top)
    glTexCoord2f(0, 1); glVertex3f(top, height, top)
    glEnd()
    glDisable(GL_TEXTURE_2D)
    glPopMatrix()

def draw_crystal(x, y, z):
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(pygame.time.get_ticks()*0.05, 0, 1, 0)
    
    glDisable(GL_LIGHTING)
    r = (math.sin(pygame.time.get_ticks()*0.003) + 1) * 0.2 + 0.3
    glColor3f(0.2, 0.5 + r, 1.0) # Pulsujący błękit
    
    s = 0.7
    glBegin(GL_TRIANGLES)
    # Octahedron
    glVertex3f(0, s, 0); glVertex3f(s, 0, 0); glVertex3f(0, 0, s)
    glVertex3f(0, s, 0); glVertex3f(0, 0, s); glVertex3f(-s, 0, 0)
    glVertex3f(0, s, 0); glVertex3f(-s, 0, 0); glVertex3f(0, 0, -s)
    glVertex3f(0, s, 0); glVertex3f(0, 0, -s); glVertex3f(s, 0, 0)
    glVertex3f(0, -s, 0); glVertex3f(0, 0, s); glVertex3f(s, 0, 0)
    glVertex3f(0, -s, 0); glVertex3f(-s, 0, 0); glVertex3f(0, 0, s)
    glVertex3f(0, -s, 0); glVertex3f(0, 0, -s); glVertex3f(-s, 0, 0)
    glVertex3f(0, -s, 0); glVertex3f(s, 0, 0); glVertex3f(0, 0, -s)
    glEnd()
    glEnable(GL_LIGHTING)
    glPopMatrix()

def main():
    global pos, rot, vel_y
    pygame.init()
    pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL)
    pygame.mouse.set_visible(False); pygame.event.set_grab(True)
    
    init_audio() # Start muzyki
    
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glLightfv(GL_LIGHT0, GL_POSITION, (0, 20, 0, 1))
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.1, 0.1, 0.15, 1))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.5, 0.4, 0.3, 1))
    
    glEnable(GL_LIGHT1) # Torch
    glLightf(GL_LIGHT1, GL_CONSTANT_ATTENUATION, 0.8)
    glLightf(GL_LIGHT1, GL_LINEAR_ATTENUATION, 0.1)
    
    create_textures()
    init_world()
    clock = pygame.time.Clock()
    
    while True:
        clock.tick(60)
        for e in pygame.event.get():
            if e.type == QUIT or (e.type == KEYDOWN and e.key == K_ESCAPE): return
        
        # Myszka
        if pygame.mouse.get_focused():
            cx, cy = WIDTH//2, HEIGHT//2
            mx, my = pygame.mouse.get_pos(); dx, dy = mx-cx, my-cy
            if dx or dy:
                pygame.mouse.set_pos(cx, cy)
                rot[0] += dx*MOUSE_SENS; rot[1] = max(-89, min(89, rot[1]+dy*MOUSE_SENS))
        
        # Ruch
        keys = pygame.key.get_pressed()
        yaw = math.radians(rot[0])
        fx, fz = math.sin(yaw), -math.cos(yaw)
        rx, rz = math.cos(yaw), math.sin(yaw)
        if keys[K_w]: pos[0]+=fx*SPEED; pos[2]+=fz*SPEED
        if keys[K_s]: pos[0]-=fx*SPEED; pos[2]-=fz*SPEED
        if keys[K_a]: pos[0]-=rx*SPEED; pos[2]-=rz*SPEED
        if keys[K_d]: pos[0]+=rx*SPEED; pos[2]+=rz*SPEED
        
        # Torch update
        glLightfv(GL_LIGHT1, GL_POSITION, (*pos, 1))
        glLightfv(GL_LIGHT1, GL_DIFFUSE, (0.8 + random.uniform(-0.1, 0.1), 0.5, 0.2, 1))
        
        # Render
        glClearColor(*C_SKY, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_PROJECTION); glLoadIdentity(); gluPerspective(FOV, WIDTH/HEIGHT, 0.5, 200)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity()
        
        pitch = math.radians(rot[1])
        look_y = pos[1] - math.sin(pitch)
        h = math.cos(pitch)
        gluLookAt(pos[0], pos[1], pos[2], pos[0]+math.sin(yaw)*h, look_y, pos[2]-math.cos(yaw)*h, 0, 1, 0)
        
        # Scene
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, texture_ids['stone'])
        glBegin(GL_QUADS) # Podłoga
        glNormal3f(0, 1, 0)
        glTexCoord2f(0,0); glVertex3f(-100, 0, -100)
        glTexCoord2f(20,0); glVertex3f(100, 0, -100)
        glTexCoord2f(20,20); glVertex3f(100, 0, 100)
        glTexCoord2f(0,20); glVertex3f(-100, 0, 100)
        glEnd()
        glDisable(GL_TEXTURE_2D)
        
        for w in walls: draw_obelisk(w[0], w[1], w[2], w[3])
        for c in crystals: draw_crystal(*c)
        
        pygame.display.flip()

if __name__ == "__main__":
    main()
