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
C_SKY = (0.05, 0.05, 0.08) # Ciemniejsze niebo
C_AMBIENT = (0.3, 0.3, 0.35)

# === STAN GRY ===
STATE_MENU = 0
STATE_GAME = 1
game_state = STATE_MENU

pos = [0.0, 5.0, 0.0]
rot = [0.0, 0.0]
vel_y = 0.0
cam_y_smooth = 5.0 # Do interpolacji kamery
fullscreen = False
has_sword = False

objects = [] 
texture_ids = {}
display_lists = {}

def lerp(a, b, t): return a + (b - a) * t

# === OBJ LOADER ===
def load_obj(filename, tex_key):
    vertices = []
    texcoords = []
    normals = []
    faces = []
    if not os.path.exists(filename): return None
    try:
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
        glGenerateMipmap(GL_TEXTURE_2D)
        texture_ids[name] = tid
        print(f"Loaded {name}")
    except Exception as e: print(f"Err {name}: {e}")

# === TERRAIN SYSTEM ===
TERRAIN_SIZE = 40 # Limit mapy
terrain_heights = {}

def get_height(x, z):
    x_i, z_i = int(x), int(z)
    if (x_i,z_i) in terrain_heights: return terrain_heights[(x_i,z_i)]
    val = math.sin(x_i * 0.1) * 1.5 + math.cos(z_i * 0.1) * 1.5
    val += math.sin(x_i*0.3 + z_i*0.2) * 0.5
    dist = math.sqrt(x*x + z*z)
    if dist < 8: val *= (dist/8.0)
    terrain_heights[(x_i,z_i)] = val
    return val

def create_terrain_list():
    lid = glGenLists(1)
    glNewList(lid, GL_COMPILE)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_ids.get('grass', 0))
    glColor3f(0.7, 0.7, 0.7)
    
    glBegin(GL_QUADS); glNormal3f(0, 1, 0)
    rng = TERRAIN_SIZE
    for x in range(-rng, rng, 1):
        for z in range(-rng, rng, 1):
            y1 = get_height(x, z)
            y2 = get_height(x+1, z)
            y3 = get_height(x+1, z+1)
            y4 = get_height(x, z+1)
            
            sc = 0.2
            glTexCoord2f(x*sc, z*sc); glVertex3f(x, y1, z)
            glTexCoord2f((x+1)*sc, z*sc); glVertex3f(x+1, y2, z)
            glTexCoord2f((x+1)*sc, (z+1)*sc); glVertex3f(x+1, y3, z+1)
            glTexCoord2f(x*sc, (z+1)*sc); glVertex3f(x, y4, z+1)
    glEnd()
    
    # ROCK WALLS
    glBindTexture(GL_TEXTURE_2D, texture_ids.get('rock_wall', 0))
    glBegin(GL_QUADS)
    h_wall = 15
    # 4 Sciany
    for i in range(-rng, rng, 4):
        # North
        glTexCoord2f(0,0); glVertex3f(i, -5, -rng)
        glTexCoord2f(1,0); glVertex3f(i+4, -5, -rng)
        glTexCoord2f(1,1); glVertex3f(i+4, h_wall, -rng)
        glTexCoord2f(0,1); glVertex3f(i, h_wall, -rng)
        # South
        glTexCoord2f(0,0); glVertex3f(i, -5, rng)
        glTexCoord2f(1,0); glVertex3f(i+4, -5, rng)
        glTexCoord2f(1,1); glVertex3f(i+4, h_wall, rng)
        glTexCoord2f(0,1); glVertex3f(i, h_wall, rng)
        # West
        glTexCoord2f(0,0); glVertex3f(-rng, -5, i)
        glTexCoord2f(1,0); glVertex3f(-rng, -5, i+4)
        glTexCoord2f(1,1); glVertex3f(-rng, h_wall, i+4)
        glTexCoord2f(0,1); glVertex3f(-rng, h_wall, i)
        # East
        glTexCoord2f(0,0); glVertex3f(rng, -5, i)
        glTexCoord2f(1,0); glVertex3f(rng, -5, i+4)
        glTexCoord2f(1,1); glVertex3f(rng, h_wall, i+4)
        glTexCoord2f(0,1); glVertex3f(rng, h_wall, i)
        
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
        target_y = get_height(self.x, self.z)
        self.y = target_y 
        if abs(self.x) > TERRAIN_SIZE-2 or abs(self.z) > TERRAIN_SIZE-2: self.rot += 180
        self.anim_timer += 0.2

    def draw(self):
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        glRotatef(self.rot, 0, 1, 0)
        
        glEnable(GL_TEXTURE_2D)
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
        glDisable(GL_TEXTURE_2D)
        glPopMatrix()

class Mushroom3D:
    def __init__(self, x, z):
        self.x, self.z = x, z
        self.y = get_height(x, z)
        self.scale = random.uniform(0.5, 1.0)
        
    def draw(self):
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        glScalef(self.scale, self.scale, self.scale)
        glColor3f(1,1,1)
        
        # Stem
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, texture_ids.get('mushroom_stem', 0))
        quad = gluNewQuadric(); gluQuadricTexture(quad, GL_TRUE)
        glPushMatrix()
        glRotatef(-90, 1, 0, 0)
        gluCylinder(quad, 0.15, 0.1, 0.8, 8, 1)
        glPopMatrix()
        
        # Cap
        glBindTexture(GL_TEXTURE_2D, texture_ids.get('mushroom_cap', 0))
        glPushMatrix()
        glTranslatef(0, 0.8, 0)
        glScalef(1.0, 0.5, 1.0)
        glRotatef(-90, 1, 0, 0)
        gluSphere(quad, 0.6, 12, 12)
        glPopMatrix()
        
        glDisable(GL_TEXTURE_2D)
        glPopMatrix()

class Sword:
    def draw_in_hand(self):
        # Rysowanie miecza w "rece" (przy kamerze)
        glDisable(GL_DEPTH_TEST) # Zeby nie przenikal przez sciany
        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
        gluPerspective(60, WIDTH/HEIGHT, 0.1, 100)
        glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
        
        glTranslatef(0.3, -0.4, -0.8) # Pozycja w "rece"
        glRotatef(-10, 1, 0, 0)
        
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, texture_ids.get('sword_metal', 0))
        glColor3f(1,1,1)
        
        quad = gluNewQuadric(); gluQuadricTexture(quad, GL_TRUE)
        
        # Blade
        glPushMatrix()
        glScalef(0.08, 0.8, 0.02)
        gluSphere(quad, 1, 8, 8) # Uzywam sfery jako bazy bo latwiej
        glPopMatrix()
        
        # Guard
        glPushMatrix()
        glTranslatef(0, -0.6, 0)
        glScalef(0.3, 0.05, 0.05)
        gluSphere(quad, 1, 8, 8)
        glPopMatrix()
        
        # Handle
        glPushMatrix()
        glTranslatef(0, -0.8, 0)
        glScalef(0.05, 0.2, 0.05)
        gluSphere(quad, 1, 8, 8)
        glPopMatrix()

        glDisable(GL_TEXTURE_2D)
        
        glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)
        glEnable(GL_DEPTH_TEST)

class Chest:
    def __init__(self, x, z):
        self.x, self.z = x, z
        self.y = get_height(x, z)
        self.is_open = False
        self.lid_angle = 0
        self.has_item = True
        
    def interact(self):
        if not self.is_open:
            self.is_open = True
            return False
        elif self.is_open and self.has_item:
            self.has_item = False
            return True # Given sword
        return False
    
    def update(self):
        target = -110 if self.is_open else 0
        self.lid_angle += (target - self.lid_angle) * 0.1
        
    def draw(self):
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, texture_ids.get('chest', 0))
        glColor3f(1,1,1)
        
        # Base
        box_w, box_h, box_d = 1.0, 0.6, 0.6
        glPushMatrix()
        glTranslatef(0, box_h/2, 0)
        glScalef(box_w, box_h, box_d)
        
        for i in range(4): 
            glPushMatrix(); glRotatef(90*i, 0, 1, 0); glTranslatef(0, 0, 0.5)
            glBegin(GL_QUADS); glNormal3f(0,0,1)
            glTexCoord2f(0,0); glVertex3f(-0.5,-0.5,0); glTexCoord2f(1,0); glVertex3f(0.5,-0.5,0)
            glTexCoord2f(1,1); glVertex3f(0.5,0.5,0); glTexCoord2f(0,1); glVertex3f(-0.5,0.5,0)
            glEnd(); glPopMatrix()
        glPopMatrix()
        
        glPushMatrix()
        glTranslatef(0, box_h, -box_d/2)
        glRotatef(self.lid_angle, 1, 0, 0)
        glTranslatef(0, 0, box_d/2)
        glScalef(box_w, 0.2, box_d)
        glBegin(GL_QUADS)
        glTexCoord2f(0,0); glVertex3f(-0.5,0.5,0.5); glTexCoord2f(1,0); glVertex3f(0.5,0.5,0.5)
        glTexCoord2f(1,1); glVertex3f(0.5,0.5,-0.5); glTexCoord2f(0,1); glVertex3f(-0.5,0.5,-0.5)
        glEnd()
        glPopMatrix()
        
        glDisable(GL_TEXTURE_2D)
        glPopMatrix()

# === SYSTEM ===

wolves = []
mushrooms = []
chests = []
trees = []
sword_item = Sword()

def init_game():
    global terrain_list
    load_texture('grass', 'grass.png')
    load_texture('stone', 'stone.png')
    load_texture('fur', 'fur.png')
    # New Assets
    load_texture('mushroom_cap', 'mushroom_cap.png')
    load_texture('mushroom_stem', 'mushroom_stem.png')
    load_texture('chest', 'chest.png')
    load_texture('rock_wall', 'rock_wall.png')
    load_texture('sword_metal', 'sword_metal.png')
    
    # Trees
    load_texture('tree_bark', '4m7qrzwizbnk-fir/bark.jpg')
    load_texture('tree_branch', '4m7qrzwizbnk-fir/branch.png')
    display_lists['tree'] = load_obj('4m7qrzwizbnk-fir/fir.obj', 'tree_branch')
    
    terrain_list = create_terrain_list()
    
    for _ in range(5): wolves.append(Wolf(random.uniform(-30, 30), random.uniform(-30, 30)))
    for _ in range(30): mushrooms.append(Mushroom3D(random.uniform(-35, 35), random.uniform(-35, 35)))
    chests.append(Chest(0, -8)) # Before spawn
    
    for _ in range(40):
        tx, tz = random.uniform(-35, 35), random.uniform(-35, 35)
        ty = get_height(tx, tz)
        trees.append((tx, ty, tz, random.uniform(1.0, 1.5)))

def draw_scene():
    if terrain_list: glCallList(terrain_list)
    if 'tree' in display_lists:
        for t in trees:
            glPushMatrix()
            glTranslatef(t[0], t[1], t[2])
            glScalef(t[3], t[3], t[3])
            glCallList(display_lists['tree'])
            glPopMatrix()
    for w in wolves: w.draw()
    for m in mushrooms: m.draw()
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
    global game_state, pos, rot, vel_y, fullscreen, WIDTH, HEIGHT, has_sword, cam_y_smooth
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL | RESIZABLE)
    pygame.display.set_caption("Antigravity: Dark Fantasy RPG")
    pygame.mouse.set_visible(False) # Default hidden
    
    set_projection(WIDTH, HEIGHT)
    
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING); glEnable(GL_LIGHT0); glEnable(GL_LIGHT1)
    glLightfv(GL_LIGHT0, GL_POSITION, (20, 50, 20, 0))
    glLightfv(GL_LIGHT0, GL_AMBIENT, (*C_AMBIENT, 1))
    glEnable(GL_COLOR_MATERIAL)
    glEnable(GL_FOG)
    glFogfv(GL_FOG_COLOR, C_SKY + (1.0,))
    glFogi(GL_FOG_MODE, GL_EXP2); glFogf(GL_FOG_DENSITY, 0.02)
    
    # Init Game
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
                if e.button == 1:
                     # Check Chest
                     for c in chests:
                         dist = math.sqrt((pos[0]-c.x)**2 + (pos[2]-c.z)**2)
                         if dist < 5.0: 
                             got_item = c.interact()
                             if got_item: has_sword = True
                             
            if e.type == KEYDOWN:
                if e.key == K_ESCAPE:
                    game_state = STATE_MENU if game_state == STATE_GAME else STATE_MENU
                    pygame.mouse.set_visible(game_state == STATE_MENU)
                        
                if e.key == K_RETURN and game_state == STATE_MENU:
                    game_state = STATE_GAME; pygame.mouse.set_visible(False)
                    
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
            
            # Bound check with Walls
            if pos[0] > TERRAIN_SIZE-2: pos[0] = TERRAIN_SIZE-2
            if pos[0] < -(TERRAIN_SIZE-2): pos[0] = -(TERRAIN_SIZE-2)
            if pos[2] > TERRAIN_SIZE-2: pos[2] = TERRAIN_SIZE-2
            if pos[2] < -(TERRAIN_SIZE-2): pos[2] = -(TERRAIN_SIZE-2)
            
            # Physics & Camera Smooth
            target_ground = get_height(pos[0], pos[2]) + 2.0
            if keys[K_SPACE] and pos[1] <= target_ground + 0.5: vel_y = 0.2
            if keys[K_g]: vel_y += 0.01; vel_y *= 0.9 # Fly
            else: vel_y -= 0.01 # Gravity
            
            pos[1] += vel_y
            if pos[1] < target_ground: pos[1] = target_ground; vel_y = 0
            
            # Smooth Camera Y
            cam_y_smooth = lerp(cam_y_smooth, pos[1], 0.1)

            for w in wolves: w.update()
            for c in chests: c.update()

        # Render
        glClearColor(*C_SKY, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        if game_state == STATE_MENU:
            # Safe 2D Drawing
            glDisable(GL_LIGHTING); glDisable(GL_FOG); glDisable(GL_DEPTH_TEST); glDisable(GL_TEXTURE_2D)
            glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
            glOrtho(0, WIDTH, 0, HEIGHT, -1, 1)
            glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
            
            glColor3f(0.1, 0.1, 0.12)
            glRectf(0, 0, WIDTH, HEIGHT)
            
            glColor3f(0.8, 0.8, 0.8)
            # Simple UI elements (Boxes)
            glRectf(WIDTH//2-100, HEIGHT//2-20, WIDTH//2+100, HEIGHT//2+20) 
            
            glMatrixMode(GL_MODELVIEW); glPopMatrix()
            glMatrixMode(GL_PROJECTION); glPopMatrix()
            glMatrixMode(GL_MODELVIEW)
            glEnable(GL_DEPTH_TEST); glEnable(GL_LIGHTING); glEnable(GL_FOG)
        else:
            pch = math.radians(rot[1])
            # Use cam_y_smooth for smooth walking
            gluLookAt(pos[0], cam_y_smooth, pos[2], 
                      pos[0]+math.sin(rad)*math.cos(pch), cam_y_smooth-math.sin(pch), pos[2]-math.cos(rad)*math.cos(pch),
                      0, 1, 0)
            
            glLightfv(GL_LIGHT1, GL_POSITION, (pos[0], pos[1], pos[2], 1))
            
            draw_scene()
            if has_sword: sword_item.draw_in_hand()
            
        pygame.display.flip()

if __name__ == "__main__":
    main()
