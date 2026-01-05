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

# === OBJ LOADER ===
def load_obj(filename, tex_key):
    vertices = []
    texcoords = []
    normals = []
    faces = []
    
    try:
        for line in open(filename, "r"):
            if line.startswith('#'): continue
            values = line.split()
            if not values: continue
            
            if values[0] == 'v':
                vertices.append(list(map(float, values[1:4])))
            elif values[0] == 'vt':
                texcoords.append(list(map(float, values[1:3])))
            elif values[0] == 'vn':
                normals.append(list(map(float, values[1:4])))
            elif values[0] == 'f':
                face_i = []
                for v in values[1:]:
                    w = v.split('/')
                    face_i.append((int(w[0])-1, int(w[1])-1 if len(w)>1 and w[1] else -1, int(w[2])-1 if len(w)>2 else -1))
                faces.append(face_i)
        
        # Compile to List
        list_id = glGenLists(1)
        glNewList(list_id, GL_COMPILE)
        if tex_key and tex_key in texture_ids:
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, texture_ids[tex_key])
        
        glBegin(GL_TRIANGLES)
        for face in faces:
            # Triangulacja polygonów
            for i in range(1, len(face)-1):
                p_indices = [face[0], face[i], face[i+1]]
                for idx in p_indices:
                    v_idx, vt_idx, vn_idx = idx
                    if vn_idx >= 0: glNormal3fv(normals[vn_idx])
                    if vt_idx >= 0: glTexCoord2fv(texcoords[vt_idx])
                    glVertex3fv(vertices[v_idx])
        glEnd()
        glDisable(GL_TEXTURE_2D)
        glEndList()
        return list_id
    except Exception as e:
        print(f"Failed to load OBJ {filename}: {e}")
        return None

# === ASSETS ===
def load_texture(name, filename):
    try:
        if not os.path.exists(filename):
            print(f"texture not found: {filename}")
            return
        surf = pygame.image.load(filename).convert_alpha()
        data = pygame.image.tostring(surf, "RGBA", 1)
        w, h = surf.get_size()
        tid = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tid)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        texture_ids[name] = tid
        print(f"Loaded {name}")
    except Exception as e:
        print(f"Err loading tex {name}: {e}")

# === ENTITIES ===

class Wolf:
    def __init__(self, x, z):
        self.x, self.y, self.z = x, 0, z
        self.rot = random.uniform(0, 360)
        self.speed = 0.05
        self.state = 'walk'
        self.anim_timer = 0
    
    def update(self):
        # AI: idź prosto, czasem skręć
        if random.random() < 0.02:
            self.rot += random.uniform(-45, 45)
            
        rad = math.radians(self.rot)
        self.x += math.sin(rad) * self.speed
        self.z += math.cos(rad) * self.speed
        
        # Odbijanie od ścian
        if abs(self.x) > 45 or abs(self.z) > 45:
            self.rot += 180
            
        self.anim_timer += 0.2

    def draw(self):
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        glRotatef(self.rot, 0, 1, 0)
        
        glBindTexture(GL_TEXTURE_2D, texture_ids.get('fur', 0))
        glColor3f(0.6, 0.6, 0.6)
        
        # TORSO
        glPushMatrix()
        glTranslatef(0, 0.8, 0)
        glScalef(0.6, 0.6, 1.2)
        quad = gluNewQuadric()
        gluQuadricTexture(quad, GL_TRUE)
        gluSphere(quad, 1, 12, 12)
        glPopMatrix()
        
        # HEAD
        glPushMatrix()
        glTranslatef(0, 1.4, 1.0)
        glScalef(0.5, 0.5, 0.6)
        gluSphere(quad, 1, 12, 12)
        glPopMatrix()
        
        # LEGS (Animated)
        for i, pos_x in enumerate([-0.3, 0.3]):
            for k, pos_z in enumerate([-0.6, 0.6]):
                glPushMatrix()
                angle = math.sin(self.anim_timer + (i+k)*3) * 20
                glTranslatef(pos_x, 0.8, pos_z)
                glRotatef(angle, 1, 0, 0)
                glTranslatef(0, -0.6, 0)
                glScalef(0.15, 0.6, 0.15)
                gluSphere(quad, 1, 8, 8)
                glPopMatrix()
        
        glPopMatrix()

# === SYSTEM ===

wolves = []

def init_game():
    load_texture('grass', 'grass.png')
    load_texture('stone', 'stone.png')
    load_texture('fur', 'fur.png')
    
    # Load Tree Assets
    load_texture('tree_bark', '4m7qrzwizbnk-fir/bark.jpg')
    load_texture('tree_branch', '4m7qrzwizbnk-fir/branch.png')
    
    # Load Tree Model
    display_lists['tree'] = load_obj('4m7qrzwizbnk-fir/fir.obj', 'tree_branch') # Używamy branch jako domyślnej textury
    
    # Spawn Wolves
    for _ in range(5):
        wolves.append(Wolf(random.uniform(-20, 20), random.uniform(-20, 20)))
        
    # Spawn Trees (Positions)
    for _ in range(40):
        objects.append(('tree', random.uniform(-40, 40), 0, random.uniform(-40, 40), random.uniform(1.0, 1.5)))

def draw_scene():
    # Floor
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_ids.get('grass', 0))
    glBegin(GL_QUADS)
    glNormal3f(0,1,0); glTexCoord2f(0,0); glVertex3f(-100,0,-100)
    glTexCoord2f(20,0); glVertex3f(100,0,-100)
    glTexCoord2f(20,20); glVertex3f(100,0,100)
    glTexCoord2f(0,20); glVertex3f(-100,0,100)
    glEnd()
    
    # Trees
    if 'tree' in display_lists:
        for obj in objects:
            if obj[0] == 'tree':
                glPushMatrix()
                glTranslatef(obj[1], obj[2], obj[3])
                glScalef(obj[4], obj[4], obj[4])
                glCallList(display_lists['tree'])
                glPopMatrix()
                
    # Wolves
    for w in wolves:
        w.draw()

def set_projection(w, h):
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(FOV, w/h, 0.5, 200.0)
    glMatrixMode(GL_MODELVIEW)

def main():
    global game_state, pos, rot, vel_y, fullscreen, WIDTH, HEIGHT
    pygame.init()
    
    # Domyślny tryb okienkowy na starcie
    screen = pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL | RESIZABLE)
    pygame.display.set_caption("Antigravity: Wolves Update")
    
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING); glEnable(GL_LIGHT0)
    glLightfv(GL_LIGHT0, GL_POSITION, (10, 50, 10, 0))
    glLightfv(GL_LIGHT0, GL_AMBIENT, (*C_AMBIENT, 1))
    
    glEnable(GL_COLOR_MATERIAL)
    
    init_game()
    clock = pygame.time.Clock()
    
    while True:
        clock.tick(60)
        
        for e in pygame.event.get():
            if e.type == QUIT: return
            if e.type == KEYDOWN:
                if e.key == K_ESCAPE:
                    game_state = STATE_MENU if game_state == STATE_GAME else STATE_MENU # Toggle logic can be improved
                    if game_state == STATE_MENU: pygame.mouse.set_visible(True)
                if e.key == K_RETURN and game_state == STATE_MENU:
                    game_state = STATE_GAME; pygame.mouse.set_visible(False)
                if e.key == K_f:
                    fullscreen = not fullscreen
                    if fullscreen:
                        # Pobieramy natywną rozdzielczość monitora
                        info = pygame.display.Info()
                        w, h = info.current_w, info.current_h
                        screen = pygame.display.set_mode((w, h), DOUBLEBUF | OPENGL | FULLSCREEN)
                    else:
                        w, h = 1280, 720
                        screen = pygame.display.set_mode((w, h), DOUBLEBUF | OPENGL | RESIZABLE)
                    WIDTH, HEIGHT = w, h
                    set_projection(WIDTH, HEIGHT) # FORCE UPDATE PROJECTION
                    
            if e.type == VIDEORESIZE and not fullscreen:
                WIDTH, HEIGHT = e.w, e.h
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
            
            # Move
            keys = pygame.key.get_pressed()
            rad = math.radians(rot[0])
            s, c = math.sin(rad), math.cos(rad)
            if keys[K_w]: pos[0]+=s*SPEED; pos[2]-=c*SPEED
            if keys[K_s]: pos[0]-=s*SPEED; pos[2]+=c*SPEED
            if keys[K_a]: pos[0]-=c*SPEED; pos[2]-=s*SPEED
            if keys[K_d]: pos[0]+=c*SPEED; pos[2]+=s*SPEED
            
            # Physics
            if keys[K_SPACE] and pos[1] <= 2.2: vel_y = 0.2
            if keys[K_g]: vel_y += 0.01
            else: vel_y -= 0.01
            pos[1] += vel_y
            if pos[1] < 2.0: pos[1] = 2.0; vel_y = 0
            
            # Wolves Update
            for w in wolves: w.update()

        # Render
        glClearColor(*C_SKY, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        if game_state == STATE_MENU:
            glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
            glOrtho(0, WIDTH, 0, HEIGHT, -1, 1)
            glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
            glDisable(GL_LIGHTING)
            # Simple text (draw white quad as indicator if text fails)
            glColor3f(1, 1, 1)
            glRectf(WIDTH//2-50, HEIGHT//2-10, WIDTH//2+50, HEIGHT//2+10)
            glEnable(GL_LIGHTING)
            glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)
        else:
            pch = math.radians(rot[1])
            gluLookAt(pos[0], pos[1], pos[2], 
                      pos[0]+math.sin(rad)*math.cos(pch), pos[1]-math.sin(pch), pos[2]-math.cos(rad)*math.cos(pch),
                      0, 1, 0)
            draw_scene()
            
        pygame.display.flip()

if __name__ == "__main__":
    main()
