import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import random
import os

# === KONFIGURACJA ===
WIDTH, HEIGHT = 1280, 720
FOV = 60
SPEED = 0.15
MOUSE_SENS = 0.15

# === KOLORY ===
C_SKY = (0.1, 0.1, 0.12)
C_AMBIENT = (0.5, 0.5, 0.5)

# === STAN GRY ===
STATE_MENU = 0
STATE_GAME = 1
game_state = STATE_MENU

pos = [0.0, 5.0, 0.0]
rot = [0.0, 0.0]
vel_y = 0.0
fullscreen = False

objects = [] 
texture_ids = {}
display_lists = {}

# === OBJ LOADER (Z poprzedniego kroku, uproszczony) ===
def load_obj(filename, tex_key):
    vertices = []
    texcoords = []
    normals = []
    faces = []
    try:
        if not os.path.exists(filename): return None
        for line in open(filename, "r"):
            if line.startswith('#'): continue
            values = line.split()
            if not values: continue
            if values[0] == 'v': vertices.append(list(map(float, values[1:4])))
            elif values[0] == 'vt': texcoords.append(list(map(float, values[1:3])))
            elif values[0] == 'vn': normals.append(list(map(float, values[1:4])))
            elif values[0] == 'f':
                face_i = []
                for v in values[1:]:
                    w = v.split('/')
                    face_i.append((int(w[0])-1, int(w[1])-1 if len(w)>1 and w[1] else -1, int(w[2])-1 if len(w)>2 else -1))
                faces.append(face_i)
        
        list_id = glGenLists(1)
        glNewList(list_id, GL_COMPILE)
        if tex_key and tex_key in texture_ids:
            glEnable(GL_TEXTURE_2D); glBindTexture(GL_TEXTURE_2D, texture_ids[tex_key])
            # TRANSPARENCY
            glEnable(GL_ALPHA_TEST); glAlphaFunc(GL_GREATER, 0.5) 
        
        glBegin(GL_TRIANGLES); glColor3f(1,1,1)
        for face in faces:
            for i in range(1, len(face)-1):
                for idx in [face[0], face[i], face[i+1]]:
                    v, vt, vn = idx
                    if vn>=0: glNormal3fv(normals[vn])
                    if vt>=0: glTexCoord2fv(texcoords[vt])
                    glVertex3fv(vertices[v])
        glEnd()
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_ALPHA_TEST)
        glEndList()
        return list_id
    except: return None

# === ASSETS ===
def load_texture(name, filename):
    try:
        if not os.path.exists(filename): return
        surf = pygame.image.load(filename).convert_alpha()
        data = pygame.image.tostring(surf, "RGBA", 1)
        w, h = surf.get_size()
        tid = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tid)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        
        # ANISOTROPY (Max Quality)
        try:
            max_aniso = glGetFloatv(GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT)
            glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAX_ANISOTROPY_EXT, max_aniso)
        except: pass
        
        glGenerateMipmap(GL_TEXTURE_2D)
        texture_ids[name] = tid
        print(f"Loaded {name}")
    except Exception as e: print(f"Err {name}: {e}")

# === TERRAIN SYSTEM ===
TERRAIN_SIZE = 100
TERRAIN_RES = 1
terrain_heights = {}

def get_height(x, z):
    # Prosty noise oparty na sinusach
    x, z = int(x), int(z)
    if (x,z) in terrain_heights: return terrain_heights[(x,z)]
    
    # Generowanie wysokości
    val = math.sin(x * 0.1) * 1.5 + math.cos(z * 0.1) * 1.5
    val += math.sin(x * 0.3 + z * 0.2) * 0.5
    
    # "Dolina" na środku spawn
    dist = math.sqrt(x*x + z*z)
    if dist < 10: val *= (dist/10.0) # Flat at center
    
    terrain_heights[(x,z)] = val
    return val

def create_terrain_list():
    lid = glGenLists(1)
    glNewList(lid, GL_COMPILE)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_ids.get('grass', 0))
    glColor3f(0.8, 0.8, 0.8) # Trochę ciemniejsza trawa
    
    glBegin(GL_QUADS)
    glNormal3f(0, 1, 0)
    
    rng = 40 # Zasięg rysowania (-40 do 40)
    steps = 1
    
    for x in range(-rng, rng, steps):
        for z in range(-rng, rng, steps):
            x1, z1 = x, z
            x2, z2 = x+steps, z+steps
            
            y1 = get_height(x1, z1)
            y2 = get_height(x2, z1)
            y3 = get_height(x2, z2)
            y4 = get_height(x1, z2)
            
            # UV mapping (niepowtarzalny wzór + detal)
            sc = 0.2
            glTexCoord2f(x1*sc, z1*sc); glVertex3f(x1, y1, z1)
            glTexCoord2f(x2*sc, z1*sc); glVertex3f(x2, y2, z1)
            glTexCoord2f(x2*sc, z2*sc); glVertex3f(x2, y3, z2)
            glTexCoord2f(x1*sc, z2*sc); glVertex3f(x1, y4, z2)
            
    glEnd()
    glDisable(GL_TEXTURE_2D)
    glEndList()
    return lid

terrain_list = None

# === ENTITIES ===

class Wolf:
    def __init__(self, x, z):
        self.x, self.z = x, z
        self.y = get_height(x, z)
        self.rot = random.uniform(0, 360)
        self.speed = 0.05
        self.anim_timer = 0
    
    def update(self):
        if random.random() < 0.02: self.rot += random.uniform(-45, 45)
        rad = math.radians(self.rot)
        self.x += math.sin(rad) * self.speed
        self.z += math.cos(rad) * self.speed
        
        # Terrain follow
        target_y = get_height(self.x, self.z)
        self.y = target_y # Snap to ground
        
        if abs(self.x) > 40 or abs(self.z) > 40: self.rot += 180
        self.anim_timer += 0.2

    def draw(self):
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        glRotatef(self.rot, 0, 1, 0)
        
        glBindTexture(GL_TEXTURE_2D, texture_ids.get('fur', 0))
        glColor3f(1,1,1)
        
        # TORSO
        glPushMatrix(); glTranslatef(0, 0.8, 0); glScalef(0.6, 0.6, 1.2)
        quad = gluNewQuadric(); gluQuadricTexture(quad, GL_TRUE)
        gluSphere(quad, 1, 12, 12)
        glPopMatrix()
        # HEAD
        glPushMatrix(); glTranslatef(0, 1.4, 1.0); glScalef(0.5, 0.5, 0.6)
        gluSphere(quad, 1, 12, 12)
        glPopMatrix()
        # LEGS
        for i, px in enumerate([-0.3, 0.3]):
            for k, pz in enumerate([-0.6, 0.6]):
                glPushMatrix()
                angle = math.sin(self.anim_timer + (i+k)*3) * 20
                glTranslatef(px, 0.8, pz)
                glRotatef(angle, 1, 0, 0)
                glTranslatef(0, -0.6, 0)
                glScalef(0.15, 0.6, 0.15)
                gluSphere(quad, 1, 8, 8)
                glPopMatrix()
        glPopMatrix()

class Billboard:
    def __init__(self, tex, x, z, scale):
        self.tex = tex
        self.x, self.z = x, z
        self.y = get_height(x, z)
        self.scale = scale
        
    def draw(self, cam_rot_y):
        glPushMatrix()
        glTranslatef(self.x, self.y + self.scale, self.z) # Center pivot
        glRotatef(-cam_rot_y, 0, 1, 0) # Face camera
        glScalef(self.scale, self.scale, self.scale)
        
        glBindTexture(GL_TEXTURE_2D, texture_ids.get(self.tex, 0))
        glEnable(GL_ALPHA_TEST); glAlphaFunc(GL_GREATER, 0.5)
        glColor3f(1,1,1)
        
        glBegin(GL_QUADS)
        glNormal3f(0, 0, 1)
        glTexCoord2f(0, 0); glVertex3f(-1, -1, 0)
        glTexCoord2f(1, 0); glVertex3f(1, -1, 0)
        glTexCoord2f(1, 1); glVertex3f(1, 1, 0)
        glTexCoord2f(0, 1); glVertex3f(-1, 1, 0)
        glEnd()
        glDisable(GL_ALPHA_TEST)
        glPopMatrix()

class Chest:
    def __init__(self, x, z):
        self.x, self.z = x, z
        self.y = get_height(x, z)
        self.is_open = False
        self.lid_angle = 0
        
    def interact(self):
        self.is_open = not self.is_open
    
    def update(self):
        target = -110 if self.is_open else 0
        self.lid_angle += (target - self.lid_angle) * 0.1
        
    def draw(self):
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        glBindTexture(GL_TEXTURE_2D, texture_ids.get('chest', 0))
        glColor3f(1,1,1)
        
        # Base
        box_w, box_h, box_d = 1.0, 0.6, 0.6
        glPushMatrix()
        glTranslatef(0, box_h/2, 0)
        glScalef(box_w, box_h, box_d)
        
        # Simple box mapping
        for i in range(4): # Sides
            glPushMatrix(); glRotatef(90*i, 0, 1, 0); glTranslatef(0, 0, 0.5)
            glBegin(GL_QUADS); glNormal3f(0,0,1)
            glTexCoord2f(0,0); glVertex3f(-0.5,-0.5,0)
            glTexCoord2f(1,0); glVertex3f(0.5,-0.5,0)
            glTexCoord2f(1,1); glVertex3f(0.5,0.5,0)
            glTexCoord2f(0,1); glVertex3f(-0.5,0.5,0)
            glEnd(); glPopMatrix()
        glPopMatrix()
        
        # Lid
        glPushMatrix()
        glTranslatef(0, box_h, -box_d/2) # Hinge
        glRotatef(self.lid_angle, 1, 0, 0)
        glTranslatef(0, 0, box_d/2)
        
        glScalef(box_w, 0.2, box_d)
        glBegin(GL_QUADS); glNormal3f(0,1,0)
        # Top
        glTexCoord2f(0,0); glVertex3f(-0.5,0.5,0.5)
        glTexCoord2f(1,0); glVertex3f(0.5,0.5,0.5)
        glTexCoord2f(1,1); glVertex3f(0.5,0.5,-0.5)
        glTexCoord2f(0,1); glVertex3f(-0.5,0.5,-0.5)
        glEnd()
        glPopMatrix()
        
        glPopMatrix()

# === SYSTEM ===

wolves = []
plants = []
chests = []
trees = []

def init_game():
    global terrain_list
    load_texture('grass', 'grass.png')
    load_texture('stone', 'stone.png')
    load_texture('fur', 'fur.png')
    load_texture('mushroom', 'mushroom.png')
    load_texture('grass_tuft', 'grass_tuft.png')
    load_texture('chest', 'chest.png')
    
    # Trees
    load_texture('tree_bark', '4m7qrzwizbnk-fir/bark.jpg')
    load_texture('tree_branch', '4m7qrzwizbnk-fir/branch.png')
    display_lists['tree'] = load_obj('4m7qrzwizbnk-fir/fir.obj', 'tree_branch')
    
    terrain_list = create_terrain_list()
    
    # Spawn
    for _ in range(5): wolves.append(Wolf(random.uniform(-30, 30), random.uniform(-30, 30)))
    for _ in range(50): plants.append(Billboard('grass_tuft', random.uniform(-38, 38), random.uniform(-38, 38), 0.5))
    for _ in range(20): plants.append(Billboard('mushroom', random.uniform(-38, 38), random.uniform(-38, 38), 0.4))
    
    # Chest
    chests.append(Chest(0, -5)) # Przed spawnem (zakładając spawn 0,0)
    
    # Trees
    for _ in range(30):
        tx, tz = random.uniform(-35, 35), random.uniform(-35, 35)
        ty = get_height(tx, tz)
        trees.append((tx, ty, tz, random.uniform(1.0, 1.5)))

def draw_scene(cam_rot_y):
    # Terrain
    if terrain_list: glCallList(terrain_list)
    
    # Trees
    if 'tree' in display_lists:
        for t in trees:
            glPushMatrix()
            glTranslatef(t[0], t[1], t[2])
            glScalef(t[3], t[3], t[3])
            glCallList(display_lists['tree'])
            glPopMatrix()
    
    # Objects
    for w in wolves: w.draw()
    for p in plants: p.draw(cam_rot_y)
    for c in chests: c.draw()

def set_projection(w, h):
    if h == 0: h = 1
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(FOV, w/h, 0.5, 200.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

def main():
    global game_state, pos, rot, vel_y, fullscreen, WIDTH, HEIGHT
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL | RESIZABLE)
    pygame.display.set_caption("Antigravity: High-End")
    
    # FIX BLACK SCREEN ON START
    set_projection(WIDTH, HEIGHT)
    
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING); glEnable(GL_LIGHT0); glEnable(GL_LIGHT1)
    glLightfv(GL_LIGHT0, GL_POSITION, (20, 100, 20, 0))
    glLightfv(GL_LIGHT0, GL_AMBIENT, (*C_AMBIENT, 1))
    glEnable(GL_COLOR_MATERIAL)
    
    # Fog (Distance hide)
    glEnable(GL_FOG)
    glFogfv(GL_FOG_COLOR, C_SKY + (1.0,))
    glFogi(GL_FOG_MODE, GL_LINEAR)
    glFogf(GL_FOG_START, 20.0); glFogf(GL_FOG_END, 60.0) # Masking terrain edge
    
    init_game()
    clock = pygame.time.Clock()
    
    while True:
        clock.tick(60)
        
        for e in pygame.event.get():
            if e.type == QUIT: return
            if e.type == VIDEORESIZE and not fullscreen:
                 WIDTH, HEIGHT = e.w, e.h
                 screen = pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL | RESIZABLE)
                 set_projection(WIDTH, HEIGHT)
                 
            if e.type == MOUSEBUTTONDOWN and game_state == STATE_GAME:
                # Interaction
                if e.button == 1: # Left click
                     # Check chests
                     for c in chests:
                         dist = math.sqrt((pos[0]-c.x)**2 + (pos[2]-c.z)**2)
                         if dist < 4.0: c.interact()
                         
            if e.type == KEYDOWN:
                if e.key == K_ESCAPE:
                    game_state = STATE_MENU if game_state == STATE_GAME else STATE_MENU
                    pygame.mouse.set_visible(game_state == STATE_MENU)
                    # FIX MENU STATE
                    if game_state == STATE_MENU:
                        glDisable(GL_LIGHTING); glDisable(GL_FOG)
                    else:
                        glEnable(GL_LIGHTING); glEnable(GL_FOG)
                        
                if e.key == K_RETURN and game_state == STATE_MENU:
                    game_state = STATE_GAME; pygame.mouse.set_visible(False)
                    glEnable(GL_LIGHTING); glEnable(GL_FOG)
                    
                if e.key == K_f:
                    fullscreen = not fullscreen
                    if fullscreen:
                         info = pygame.display.Info()
                         screen = pygame.display.set_mode((info.current_w, info.current_h), DOUBLEBUF | OPENGL | FULLSCREEN)
                         WIDTH, HEIGHT = info.current_w, info.current_h
                    else:
                         WIDTH, HEIGHT = 1280, 720
                         screen = pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL | RESIZABLE)
                    set_projection(WIDTH, HEIGHT)

        # Logic
        if game_state == STATE_GAME:
            if pygame.mouse.get_focused():
                 cx, cy = WIDTH//2, HEIGHT//2
                 mx, my = pygame.mouse.get_pos()
                 dx, dy = mx-cx, my-cy
                 if dx or dy:
                     pygame.mouse.set_pos(cx, cy)
                     rot[0] += dx * MOUSE_SENS
                     rot[1] = max(-89, min(89, rot[1] + dy * MOUSE_SENS))
            
            keys = pygame.key.get_pressed()
            rad = math.radians(rot[0])
            s, c = math.sin(rad), math.cos(rad)
            if keys[K_w]: pos[0]+=s*SPEED; pos[2]-=c*SPEED
            if keys[K_s]: pos[0]-=s*SPEED; pos[2]+=c*SPEED
            if keys[K_a]: pos[0]-=c*SPEED; pos[2]-=s*SPEED
            if keys[K_d]: pos[0]+=c*SPEED; pos[2]+=s*SPEED
            
            # Physics (Terrain collision)
            ground_y = get_height(pos[0], pos[2]) + 2.0
            
            if keys[K_SPACE] and pos[1] <= ground_y + 0.2: vel_y = 0.2
            if keys[K_g]: vel_y += 0.01; vel_y *= 0.9
            else: vel_y -= 0.01
            
            pos[1] += vel_y
            if pos[1] < ground_y: pos[1] = ground_y; vel_y = 0
            
            for w in wolves: w.update()
            for c in chests: c.update()

        # Render
        glClearColor(*C_SKY, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        if game_state == STATE_MENU:
            glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
            glOrtho(0, WIDTH, 0, HEIGHT, -1, 1)
            glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
            
            # Fancy Menu
            glBegin(GL_QUADS); glColor3f(0.1, 0.1, 0.12)
            glVertex2f(0,0); glVertex2f(WIDTH,0); glVertex2f(WIDTH,HEIGHT); glVertex2f(0,HEIGHT)
            glEnd()
            
            glColor3f(1,1,1)
            glRectf(WIDTH//2-100, HEIGHT//2-20, WIDTH//2+100, HEIGHT//2+20) # Button placeholder
            
            glMatrixMode(GL_MODELVIEW); glPopMatrix()
            glMatrixMode(GL_PROJECTION); glPopMatrix()
            glMatrixMode(GL_MODELVIEW)
        else:
            pch = math.radians(rot[1])
            gluLookAt(pos[0], pos[1], pos[2], 
                      pos[0]+math.sin(rad)*math.cos(pch), pos[1]-math.sin(pch), pos[2]-math.cos(rad)*math.cos(pch),
                      0, 1, 0)
            
            # Torch Light
            glLightfv(GL_LIGHT1, GL_POSITION, (*pos, 1))
            
            draw_scene(rot[0])
            
        pygame.display.flip()

if __name__ == "__main__":
    main()
