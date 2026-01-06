import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GL.EXT.texture_filter_anisotropic import *
import math
import random
import os
import ctypes

# === CONFIGURATION ===
WIDTH, HEIGHT = 1920, 1080
FOV = 60
SPEED = 0.15
MOUSE_SENS = 0.1
TERRAIN_SIZE = 40

# === COLORS ===
C_SKY = (0.05, 0.05, 0.08, 1.0)
C_AMBIENT = (0.3, 0.3, 0.35, 1.0)

# === GAME STATES ===
STATE_MENU = 0
STATE_GAME = 1
STATE_PAUSE = 2
STATE_INVENTORY = 3

# === GLOBAL STATE ===
game_state = STATE_MENU
fullscreen = False
paused = False
show_settings = False
msaa_level = 4
aniso_level = 16.0
shadows_enabled = True
hdr_enabled = True

# FPS Settings
fps_limit = 60 # placeholder, will init to native
fps_slider_val = 0.5 # 0.0-1.0 range for UI
music_volume = 0.4 # Default volume

# === ASSET PATHS ===
ASSET_DIR = "assets"
TEX_DIR = os.path.join(ASSET_DIR, "textures")
MDL_DIR = os.path.join(ASSET_DIR, "models")

texture_ids = {}
display_lists = {}

def load_texture(name, filename):
    path = os.path.join(TEX_DIR, filename)
    if not os.path.exists(path):
        print(f"Warning: Texture {path} not found.")
        return 0
    try:
        surf = pygame.image.load(path).convert_alpha()
        data = pygame.image.tostring(surf, "RGBA", 1)
        w, h = surf.get_size()
        tid = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tid)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        glGenerateMipmap(GL_TEXTURE_2D)
        
        # Default Trilinear
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        
        # Apply Anisotropy
        if glInitTextureFilterAnisotropicEXT():
            max_aniso = glGetFloatv(GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT)
            amount = min(aniso_level, max_aniso)
            glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAX_ANISOTROPY_EXT, amount)
            
        texture_ids[name] = tid
        return tid
    except Exception as e:
        print(f"Error loading texture {name}: {e}")
        return 0

def load_obj_display_list(filename, tex_key):
    path = os.path.join(MDL_DIR, filename)
    if not os.path.exists(path): return None
    
    vertices, texcoords, normals, faces = [], [], [], []
    try:
        for line in open(path, "r"):
            if line.startswith('#'): continue
            vals = line.split()
            if not vals: continue
            if vals[0] == 'v': vertices.append(list(map(float, vals[1:4])))
            elif vals[0] == 'vt': texcoords.append(list(map(float, vals[1:3])))
            elif vals[0] == 'vn': normals.append(list(map(float, vals[1:4])))
            elif vals[0] == 'f':
                face = []
                for v in vals[1:]:
                    w = v.split('/')
                    face.append((int(w[0])-1, int(w[1])-1 if len(w)>1 and w[1] else -1, int(w[2])-1 if len(w)>2 else -1))
                faces.append(face)
            
        lid = glGenLists(1)
        glNewList(lid, GL_COMPILE)
        if tex_key and tex_key in texture_ids:
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, texture_ids[tex_key])
            # Transparency Fix
            glEnable(GL_ALPHA_TEST)
            glAlphaFunc(GL_GREATER, 0.4)
            
        glBegin(GL_TRIANGLES)
        glColor3f(1,1,1)
        for face in faces:
            for idx in [face[0], face[1], face[2]]: # Assume triangulated
                v, vt, vn = idx
                if vn >= 0 and vn < len(normals): glNormal3fv(normals[vn])
                if vt >= 0 and vt < len(texcoords): glTexCoord2fv(texcoords[vt])
                glVertex3fv(vertices[v])
        glEnd()
        glDisable(GL_ALPHA_TEST) # Disable after drawing
        glDisable(GL_TEXTURE_2D)
        glEndList()
        return lid
    except Exception as e:
        print(f"OBJ Error: {e}")
        return None

# === SHADOW SYSTEM ===
# Projected Shadow Matrix (Shadows from Sun)
def shadow_projection(light_pos, ground_y=0.1):
    lx, ly, lz, lw = light_pos
    mat = [0]*16
    
    # Simple Planar Projection onto Y=ground_y
    # This matrix flattens geometry onto the plane
    mat[0] = ly; mat[4] = -lx; mat[8] = 0;  mat[12] = 0
    mat[1] = 0;  mat[5] = 0;   mat[9] = 0;  mat[13] = 0 # Flatten Y
    mat[2] = 0;  mat[6] = -lz; mat[10]= ly; mat[14]= 0
    mat[3] = 0;  mat[7] = -1;  mat[11]= 0;  mat[15]= ly
    
    glPushMatrix()
    glTranslatef(0, ground_y+0.05, 0) # Raise slightly to avoid z-fight
    glMultMatrixf(mat)

def draw_blob_shadow(x, y, z, scale):
    # Blob shadows removed as requested
    pass

# === INVENTORY & ITEMS ===
class Item:
    def __init__(self, name, icon_tex, type="misc"):
        self.name = name
        self.icon = icon_tex # Texture ID or name
        self.type = type # weapon, misc

class Inventory:
    def __init__(self):
        self.slots = [None] * 10
        self.equipped = {1: None, 2: None} # '1', '2' keys
        self.drag_item = None
        self.drag_offset = (0,0)
        self.drag_source = None # ('inv', index) or ('equip', slot)
        self.opened_container = None # Reference to Chest
        
    def add_item(self, item):
        for i in range(len(self.slots)):
            if self.slots[i] is None:
                self.slots[i] = item
                return True
        return False

# === ENTITIES ===

def get_height(x, z):
    # Sinewave terrain
    val = math.sin(x * 0.1) * 1.5 + math.cos(z * 0.1) * 1.5
    val += math.sin(x*0.3 + z*0.2) * 0.5
    dist = math.sqrt(x*x + z*z)
    if dist < 8: val *= (dist/8.0)
    return val

class Player:
    def __init__(self):
        self.pos = [0.0, 5.0, 0.0]
        self.rot = [0.0, 0.0]
        self.vel = [0.0, 0.0, 0.0]
        self.cam_h = 5.0
        self.inventory = Inventory()
        
        # Combat
        self.attacking = False
        self.anim_t = 0.0
    
    def update(self, df):
        # Physics implemented in main loop for now
        # Camera smoothing
        self.cam_h += (self.pos[1] - self.cam_h) * 0.1 * df
        
        if self.attacking:
            self.anim_t += 0.2 * df
            if self.anim_t > math.pi: 
                self.attacking = False
                self.anim_t = 0

    def draw_hud(self):
        # Draw sword swing if attacking
        if self.attacking:
            # Weapon Animation
            glLoadIdentity()
            glDisable(GL_DEPTH_TEST); glDisable(GL_LIGHTING); glDisable(GL_TEXTURE_2D)
            # Use 3D projection for sword in hand
            glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
            gluPerspective(60, WIDTH/HEIGHT, 0.1, 100)
            glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
            
            enable_lighting = True
            if enable_lighting: glEnable(GL_LIGHTING); glEnable(GL_LIGHT0)
            
            glEnable(GL_TEXTURE_2D); glBindTexture(GL_TEXTURE_2D, texture_ids.get('sword_metal', 0))
            
            # Swing Math
            swing = math.sin(self.anim_t) * 2.0
            
            glTranslatef(0.4 - swing*0.2, -0.4, -0.8 + swing*0.1) 
            glRotatef(-10 + swing*40, 1, 0, 0)
            glRotatef(-swing*30, 0, 1, 0) 
            
            # Draw Sword Model (Procedural)
            quad = gluNewQuadric(); gluQuadricTexture(quad, GL_TRUE)
            glColor3f(1, 1, 1)
            
            # Blade
            glPushMatrix(); glScalef(0.08, 0.8, 0.02); gluSphere(quad, 1, 8, 8); glPopMatrix()
            # Guard
            glPushMatrix(); glTranslatef(0, -0.6, 0); glScalef(0.3, 0.05, 0.05); gluSphere(quad, 1, 8, 8); glPopMatrix()
            # Handle
            glPushMatrix(); glTranslatef(0, -0.8, 0); glScalef(0.05, 0.2, 0.05); gluSphere(quad, 1, 8, 8); glPopMatrix()

            glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW); glPopMatrix()
            glEnable(GL_DEPTH_TEST)

class Chest:
    def __init__(self, x, z, loot=None):
        self.x, self.z = x, z
        self.y = get_height(x, z)
        self.is_open = False
        self.lid_angle = 0
        self.items = loot if loot is not None else [Item("Iron Sword", "sword_metal", "weapon"), Item("Potion", "mushroom_cap", "misc")]
        
    def update(self, df):
        t = -110 if self.is_open else 0
        self.lid_angle += (t - self.lid_angle) * 0.1 * df
        
    def draw(self, shadow_pass=False):
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        if shadows_enabled:
             # Shadow Pass logic handled by main loop projection
             pass
        else:
             pass

        
        # Base
        box_w, box_h, box_d = 1.0, 0.6, 0.6
        glPushMatrix(); glTranslatef(0, box_h/2, 0); glScalef(box_w, box_h, box_d)
        for i in range(4): 
            glPushMatrix(); glRotatef(90*i, 0, 1, 0); glTranslatef(0, 0, 0.5)
            glBegin(GL_QUADS); glNormal3f(0,0,1)
            glTexCoord2f(0,0); glVertex3f(-0.5,-0.5,0); glTexCoord2f(1,0); glVertex3f(0.5,-0.5,0)
            glTexCoord2f(1,1); glVertex3f(0.5,0.5,0); glTexCoord2f(0,1); glVertex3f(-0.5,0.5,0)
            glEnd(); glPopMatrix()
        glPopMatrix()
        
        # Lid
        glPushMatrix(); glTranslatef(0, box_h, -box_d/2); glRotatef(self.lid_angle, 1, 0, 0)
        glTranslatef(0, 0, box_d/2); glScalef(box_w, 0.2, box_d)
        glBegin(GL_QUADS)
        glTexCoord2f(0,0); glVertex3f(-0.5,0.5,0.5); glTexCoord2f(1,0); glVertex3f(0.5,0.5,0.5)
        glTexCoord2f(1,1); glVertex3f(0.5,0.5,-0.5); glTexCoord2f(0,1); glVertex3f(-0.5,0.5,-0.5)
        glEnd(); glPopMatrix()
        
        if not shadow_pass: glDisable(GL_TEXTURE_2D)
        glPopMatrix()

class Wolf:
    def __init__(self, x, z):
        self.x, self.z = x, z
        self.y = get_height(x, z)
        self.rot = random.uniform(0, 360)
        self.anim = 0
        
    def update(self, df):
        self.anim += 0.1 * df
        self.rot += 0.5 * df
        
    def draw(self, shadow_pass=False):
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        
        if not shadow_pass:
             glEnable(GL_TEXTURE_2D); glBindTexture(GL_TEXTURE_2D, texture_ids.get('fur', 0))
             glColor3f(1,1,1)
        else:
             glColor4f(0,0,0, 0.4)
             
        glRotatef(self.rot, 0, 1, 0)
        
        quad = gluNewQuadric(); gluQuadricTexture(quad, GL_TRUE)
        
        # Body
        glPushMatrix(); glTranslatef(0, 0.8, 0); glScalef(0.5, 0.5, 1.0); gluSphere(quad, 1, 10, 10); glPopMatrix()
        # Head
        glPushMatrix(); glTranslatef(0, 1.3, 0.8); glScalef(0.35, 0.35, 0.4); gluSphere(quad, 1, 10, 10); glPopMatrix()
        # Snout
        glPushMatrix(); glTranslatef(0, 1.25, 1.15); glScalef(0.15, 0.15, 0.3); gluSphere(quad, 1, 8, 8); glPopMatrix()
        
        # Legs
        for x in [-0.3, 0.3]:
            for z in [-0.6, 0.6]:
                glPushMatrix()
                angle = math.sin(self.anim + (x+z)*5) * 20
                glTranslatef(x, 0.8, z)
                glRotatef(angle, 1, 0, 0)
                glTranslatef(0, -0.4, 0)
                glScalef(0.12, 0.4, 0.12)
                gluSphere(quad, 1, 6, 6)
                glPopMatrix()
                
        # Tail
        glPushMatrix()
        angle = math.sin(self.anim) * 10
        glTranslatef(0, 0.9, -0.9)
        glRotatef(angle - 45, 1, 0, 0) # Hanging down
        glScalef(0.1, 0.1, 0.6)
        gluSphere(quad, 1, 6, 6)
        glPopMatrix()
        
        if not shadow_pass: glDisable(GL_TEXTURE_2D)
        glPopMatrix()


class Spider:
    def __init__(self, x, z):
        self.x, self.z = x, z
        self.y = get_height(x, z)
        self.rot = random.uniform(0, 360)
        self.anim = 0
        
    def update(self, df):
        self.anim += 0.15 * df
        # Skittery movement
        self.x += math.sin(math.radians(self.rot)) * 0.05 * df
        self.z += math.cos(math.radians(self.rot)) * 0.05 * df
        self.y = get_height(self.x, self.z)
        
        # Turn randomly
        if random.random() < 0.02 * df:
             self.rot += random.uniform(-45, 45)

    def draw(self, shadow_pass=False):
        glPushMatrix()
        glTranslatef(self.x, self.y + 0.5, self.z) # Center of body
        glRotatef(self.rot, 0, 1, 0)
        
        if not shadow_pass:
             # Removed blobs
             glColor3f(0.1, 0.1, 0.1) # Black/Grey spider
        else:
             glColor4f(0,0,0, 0.4)
             
        quad = gluNewQuadric()
        
        # Abdomen
        glPushMatrix(); glScalef(0.4, 0.3, 0.5); gluSphere(quad, 1, 8, 8); glPopMatrix()
        # Head
        glPushMatrix(); glTranslatef(0, 0.1, 0.4); glScalef(0.2, 0.15, 0.2); gluSphere(quad, 1, 8, 8); glPopMatrix()
        
        # Legs (8)
        for side in [-1, 1]:
            for i in range(4):
                glPushMatrix()
                # Initial pos on body
                offset_z = 0.2 - i*0.15
                glTranslatef(side*0.3, 0, offset_z)
                
                # Leg movement
                lift = math.sin(self.anim + side*i + i*2) * 0.2
                glRotate(side * 40 - i*10, 0, 1, 0) # Leg spread
                glRotate(-30 + lift*30, 0, 0, 1) # Arch shape
                
                # Upper leg
                glPushMatrix(); glScalef(0.3, 0.05, 0.05); gluSphere(quad, 1, 4, 4); glPopMatrix()
                
                # Lower leg
                glTranslatef(0.3, -0.1, 0)
                glRotate(side * 60, 0, 0, 1) # Bend down
                glPushMatrix(); glScalef(0.4, 0.05, 0.05); gluSphere(quad, 1, 4, 4); glPopMatrix()
                
                glPopMatrix()
                
        if not shadow_pass: glDisable(GL_TEXTURE_2D)
        glPopMatrix()

# === SYSTEM ===
player = Player()
entities = []
terrain_list = None

def init():
    global terrain_list
    load_texture('grass', 'grass.png')
    load_texture('stone', 'stone.png')
    load_texture('fur', 'fur.png')
    load_texture('mushroom_cap', 'mushroom_cap.png')
    load_texture('mushroom_stem', 'mushroom_stem.png')
    load_texture('chest', 'chest.png')
    load_texture('rock_wall', 'rock_wall.png')
    load_texture('sword_metal', 'sword_metal.png')
    load_texture('shadow_blob', 'shadow_blob.png')
    load_texture('tree_bark', 'bark.jpg')
    load_texture('tree_branch', 'branch.png')
    
    display_lists['tree'] = load_obj_display_list('fir.obj', 'tree_branch')
    
    # Generate Terrain
    terrain_list = glGenLists(1)
    glNewList(terrain_list, GL_COMPILE)
    glEnable(GL_TEXTURE_2D); glBindTexture(GL_TEXTURE_2D, texture_ids.get('grass', 0))
    glColor3f(1,1,1) # Neutral
    glBegin(GL_QUADS); glNormal3f(0,1,0)
    for x in range(-TERRAIN_SIZE, TERRAIN_SIZE):
        for z in range(-TERRAIN_SIZE, TERRAIN_SIZE):
            y1 = get_height(x, z); y2 = get_height(x+1, z)
            y3 = get_height(x+1, z+1); y4 = get_height(x, z+1)
            t = 0.25
            glTexCoord2f(x*t, z*t); glVertex3f(x, y1, z)
            glTexCoord2f((x+1)*t, z*t); glVertex3f(x+1, y2, z)
            glTexCoord2f((x+1)*t, (z+1)*t); glVertex3f(x+1, y3, z+1)
            glTexCoord2f(x*t, (z+1)*t); glVertex3f(x, y4, z+1)
    glEnd()
    glDisable(GL_TEXTURE_2D)
    glEndList()
    
    # Spawn
    # Spawn
    for _ in range(3): entities.append(Wolf(random.uniform(-10, 10), random.uniform(-10, 10)))
    for _ in range(3): entities.append(Spider(random.uniform(-15, 15), random.uniform(-15, 15)))
    
    # Specific Chest with Sword
    chest_loot = [Item("Iron Sword", "sword_metal", "weapon"), Item("Bread", "mushroom_stem", "misc")]
    entities.append(Chest(5, 5, loot=chest_loot))

def draw_ui_text(font, text, x, y, color=(255,255,255)):
    surf = font.render(text, True, color)
    data = pygame.image.tostring(surf, "RGBA", 1)
    w, h = surf.get_size()
    
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glEnable(GL_TEXTURE_2D)
    tid = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tid)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
    
    glColor3f(1,1,1)
    glBegin(GL_QUADS)
    glTexCoord2f(0,0); glVertex2f(x, y)
    glTexCoord2f(1,0); glVertex2f(x+w, y)
    glTexCoord2f(1,1); glVertex2f(x+w, y+h)
    glTexCoord2f(0,1); glVertex2f(x, y+h)
    glEnd()
    
    glDeleteTextures([tid])
    glDisable(GL_TEXTURE_2D); glDisable(GL_BLEND)

def draw_rect(x, y, w, h, color):
    glDisable(GL_TEXTURE_2D)
    glColor4f(*color) # expects float 0-1
    glRectf(x, y, x+w, y+h)

def draw_inventory(font):
    # Dim background
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    draw_rect(0, 0, WIDTH, HEIGHT, (0,0,0,0.7))
    
    # Inventory Box
    cx, cy = WIDTH//2, HEIGHT//2
    w, h = 600, 400
    draw_rect(cx-w/2, cy-h/2, w, h, (0.1, 0.1, 0.1, 0.95))
    draw_ui_text(font, "INVENTORY", cx-100, cy-h/2+20)
    
    # Drag State
    mx, my = pygame.mouse.get_pos()
    gl_my = HEIGHT - my
    
    inv = player.inventory
    
    # Helper to check hover
    def is_hover(bx, by, bs):
        return bx < mx < bx+bs and by < gl_my < by+bs

    # --- Draw Items & Logic ---
    slot_size = 64
    pad = 10
    start_x = cx - (5 * (slot_size+pad))/2
    start_y = cy - 50
    
    # 1. Main Inventory Slots
    for i in range(10):
        sx = start_x + (i % 5) * (slot_size + pad)
        sy = start_y - (i // 5) * (slot_size + pad)
        
        col = (0.2, 0.2, 0.2, 1)
        item = inv.slots[i]
        
        # Draw Slot
        if is_hover(sx, sy, slot_size):
            col = (0.3, 0.3, 0.3, 1)
            # Drag Start Logic
            if pygame.mouse.get_pressed()[0] and item and not inv.drag_item:
                inv.drag_item = item
                inv.drag_source = ('inv', i)
                inv.slots[i] = None # Remove temp
                inv.drag_offset = (mx - sx, gl_my - sy)
        
        draw_rect(sx, sy, slot_size, slot_size, col)
        if item and item != inv.drag_item:
             draw_rect(sx+5, sy+5, slot_size-10, slot_size-10, (0.5, 0.5, 0.5, 1))
             draw_ui_text(font, item.name[:4], sx+5, sy+20, (0,0,0))
             
    # 2. Equipment Slots
    eq_x = cx - 200; eq_y = cy + 100
    
    # Weapon 1
    draw_ui_text(font, "WEAPON 1 [1]", eq_x, eq_y+70)
    col1 = (0.4, 0.2, 0.2, 1) if inv.equipped[1] else (0.2, 0.1, 0.1, 1)
    if is_hover(eq_x, eq_y, slot_size):
        if pygame.mouse.get_pressed()[0] and inv.equipped[1] and not inv.drag_item:
             inv.drag_item = inv.equipped[1]
             inv.drag_source = ('equip', 1)
             inv.equipped[1] = None
    
    draw_rect(eq_x, eq_y, slot_size, slot_size, col1)
    if inv.equipped[1]:
        draw_rect(eq_x+5, eq_y+5, slot_size-10, slot_size-10, (0.6, 0.3, 0.3, 1))
        draw_ui_text(font, inv.equipped[1].name[:4], eq_x+5, eq_y+20)

    # Weapon 2
    eq_x2 = cx + 100
    draw_ui_text(font, "WEAPON 2 [2]", eq_x2, eq_y+70)
    col2 = (0.4, 0.2, 0.2, 1) if inv.equipped[2] else (0.2, 0.1, 0.1, 1)
    if is_hover(eq_x2, eq_y, slot_size):
        if pygame.mouse.get_pressed()[0] and inv.equipped[2] and not inv.drag_item:
             inv.drag_item = inv.equipped[2]
             inv.drag_source = ('equip', 2)
             inv.equipped[2] = None

    draw_rect(eq_x2, eq_y, slot_size, slot_size, col2)
    if inv.equipped[2]:
        draw_rect(eq_x2+5, eq_y+5, slot_size-10, slot_size-10, (0.6, 0.3, 0.3, 1))
        draw_ui_text(font, inv.equipped[2].name[:4], eq_x2+5, eq_y+20)

    # 3. Chest Container (Drag from chest)
    if inv.opened_container and inv.opened_container.is_open:
        c_x = cx + w/2 + 20
        draw_rect(c_x, cy-h/2, 200, h, (0.15, 0.12, 0.1, 0.95))
        draw_ui_text(font, "CHEST", c_x+70, cy-h/2+20)
        c_items = inv.opened_container.items
        
        for i, item in enumerate(c_items):
            iy = cy + 100 - i*70
            h_col = (0.2, 0.2, 0.2, 1)
            
            # Simple Click to loot (Drag from chest logic is complex with list shifting, simplify to click-to-loot or drag start)
            if c_x+20 < mx < c_x+20+slot_size and iy < gl_my < iy+slot_size:
                 h_col = (0.4, 0.4, 0.4, 1)
                 if pygame.mouse.get_pressed()[0] and not inv.drag_item:
                     # Start dragging from Chest?
                     # Ideally we remove from chest and put on mouse
                     inv.drag_item = item
                     inv.drag_source = ('chest', i)
                     c_items.pop(i)
                     break
            
            draw_rect(c_x+20, iy, slot_size, slot_size, h_col)
            draw_rect(c_x+25, iy+5, slot_size-10, slot_size-10, (0.5,0.5,0.5,1))
            draw_ui_text(font, item.name[:4], c_x+25, iy+20, (0,0,0))

    # --- DRAG RENDER & DROP LOGIC ---
    if inv.drag_item:
        # Draw floating item
        draw_rect(mx - 32, gl_my - 32, 64, 64, (0.7, 0.7, 0.7, 0.8))
        draw_ui_text(font, inv.drag_item.name[:4], mx-20, gl_my-10, (0,0,0))
        
        # Check Drop (Mouse Up)
        if not pygame.mouse.get_pressed()[0]:
            # Find Drop Target
            dropped = False
            
            # 1. Main Slots
            for i in range(10):
                sx = start_x + (i % 5) * (slot_size + pad)
                sy = start_y - (i // 5) * (slot_size + pad)
                if is_hover(sx, sy, slot_size):
                    # Swap
                    existing = inv.slots[i]
                    inv.slots[i] = inv.drag_item
                    if existing:
                        # Return existing to source or swap to cursor? 
                        # Simple: If source was 'inv', put existing there.
                        if inv.drag_source[0] == 'inv': inv.slots[inv.drag_source[1]] = existing
                        elif inv.drag_source[0] == 'equip': inv.equipped[inv.drag_source[1]] = existing
                        elif inv.drag_source[0] == 'chest': inv.opened_container.items.append(existing)
                    dropped = True
                    break
            
            # 2. Equip Slots
            if not dropped:
                # Check W1
                if is_hover(eq_x, eq_y, slot_size) and inv.drag_item.type == 'weapon':
                    existing = inv.equipped[1]
                    inv.equipped[1] = inv.drag_item
                    if existing:
                         if inv.drag_source[0] == 'inv': inv.slots[inv.drag_source[1]] = existing
                         elif inv.drag_source[0] == 'equip': inv.equipped[inv.drag_source[1]] = existing
                         elif inv.drag_source[0] == 'chest': inv.opened_container.items.append(existing)
                    dropped = True
                # Check W2
                elif is_hover(eq_x2, eq_y, slot_size) and inv.drag_item.type == 'weapon':
                    existing = inv.equipped[2]
                    inv.equipped[2] = inv.drag_item
                    if existing:
                        if inv.drag_source[0] == 'inv': inv.slots[inv.drag_source[1]] = existing
                        elif inv.drag_source[0] == 'equip': inv.equipped[inv.drag_source[1]] = existing
                        elif inv.drag_source[0] == 'chest': inv.opened_container.items.append(existing)
                    dropped = True

            # Cancel / Return if not dropped or invalid
            if not dropped:
                if inv.drag_source[0] == 'inv': inv.slots[inv.drag_source[1]] = inv.drag_item
                elif inv.drag_source[0] == 'equip': inv.equipped[inv.drag_source[1]] = inv.drag_item
                elif inv.drag_source[0] == 'chest': inv.opened_container.items.append(inv.drag_item)
            
            inv.drag_item = None
    glDisable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    draw_rect(0, 0, WIDTH, HEIGHT, (0, 0, 0, 0.8))
    
    cx, cy = WIDTH//2, HEIGHT//2
    
    if not show_settings:
        draw_ui_text(font, "PAUSED", cx-50, cy+100)
        
        opts = ["RESUME", "SETTINGS", "EXIT"]
        mx, my = pygame.mouse.get_pos()
        gl_my = HEIGHT - my
        
        for i, opt in enumerate(opts):
            y = cy - i*60
            w = 200
            x = cx - w/2
            
            hover = x < mx < x+w and y < gl_my < y+50
            col = (0.4, 0.4, 0.4, 1) if hover else (0.2, 0.2, 0.2, 1)
            draw_rect(x, y, w, 50, col)
            draw_ui_text(font, opt, x+60, y+15)
            
            if hover and pygame.mouse.get_pressed()[0]:
                return opt
    else:
        draw_settings(font)
        
    return None

def draw_settings(font):
    global msaa_level, aniso_level, shadows_enabled, show_settings, fps_limit, fps_slider_val, music_volume
    cx, cy = WIDTH//2, HEIGHT//2
    # Shifted Everything Down by ~100px to avoid click overlap
    offset_y = -100 
    
    draw_ui_text(font, "SETTINGS", cx-60, cy+220 + offset_y)
    
    mx, my = pygame.mouse.get_pos(); gl_my = HEIGHT - my
    x = cx - 150; w = 300
    
    # helper for buttons
    def draw_button(bx, by, bw, bh, text, active=False):
        hover = bx < mx < bx+bw and by < gl_my < by+bh
        col = (0.4, 0.4, 0.5, 1) if active else ((0.3, 0.3, 0.4, 1) if hover else (0.1, 0.1, 0.1, 1))
        draw_rect(bx, by, bw, bh, col)
        draw_ui_text(font, text, bx + 20, by + 12)
        return hover and pygame.mouse.get_pressed()[0]

    # 1. Shadows
    if draw_button(x, cy+140 + offset_y, w, 40, f"Shadows: {'ON' if shadows_enabled else 'OFF'}"):
        shadows_enabled = not shadows_enabled
        pygame.time.wait(200)

    # 2. Aniso
    if draw_button(x, cy+90 + offset_y, w, 40, f"Anisotropy: {int(aniso_level)}x"):
        aniso_level = 16.0 if aniso_level == 1.0 else 1.0
        pygame.time.wait(200)
        
    # 3. MSAA (Anti-Aliasing)
    if draw_button(x, cy+40 + offset_y, w, 40, f"MSAA: {msaa_level}x"):
        msaa_level = 8 if msaa_level == 4 else (4 if msaa_level == 2 else 2)
        pygame.time.wait(200)

    # 3.5 Music Volume
    y_music = cy - 20 + offset_y
    draw_ui_text(font, f"Music Vol: {int(music_volume*100)}%", x, y_music+25)
    draw_rect(x, y_music, w, 10, (0.5, 0.5, 0.5, 1))
    
    m_knob_x = x + (music_volume * w)
    draw_rect(m_knob_x-10, y_music-5, 20, 20, (0.8, 0.8, 0.8, 1))
    
    if x-10 < mx < x+w+10 and y_music-10 < gl_my < y_music+30:
        if pygame.mouse.get_pressed()[0]:
            music_volume = max(0.0, min(1.0, (mx - x) / w))
            pygame.mixer.music.set_volume(music_volume)

    # 4. FPS Slider
    y_slider = cy - 80 + offset_y
    draw_ui_text(font, f"Max FPS: {'Unlimited' if fps_limit==0 else fps_limit}", x, y_slider+30)
    draw_rect(x, y_slider, w, 10, (0.5, 0.5, 0.5, 1))
    
    knob_x = x + (fps_slider_val * w)
    draw_rect(knob_x-10, y_slider-5, 20, 20, (0.8, 0.8, 0.8, 1))
    
    if x-10 < mx < x+w+10 and y_slider-10 < gl_my < y_slider+40:
        if pygame.mouse.get_pressed()[0]:
             fps_slider_val = max(0.0, min(1.0, (mx - x) / w))
             if fps_slider_val > 0.98: fps_limit = 0
             else: fps_limit = int(30 + fps_slider_val * 210)
             
    # FPS Presets
    if draw_button(x, cy-140 + offset_y, 90, 35, "60"): fps_limit = 60; fps_slider_val = (60-30)/210
    if draw_button(x+105, cy-140 + offset_y, 90, 35, "144"): fps_limit = 144; fps_slider_val = (144-30)/210
    if draw_button(x+210, cy-140 + offset_y, 90, 35, "MAX"): fps_limit = 0; fps_slider_val = 1.0

    # 5. Back
    if draw_button(x, cy-220 + offset_y, w, 50, "BACK"):
        show_settings = False
        pygame.time.wait(200)

def draw_title_menu(font):
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    # Darken background slightly
    draw_rect(0, 0, WIDTH, HEIGHT, (0, 0, 0, 0.4))
    
    cx, cy = WIDTH//2, HEIGHT//2
    
    # Title
    title_font = pygame.font.SysFont("times new roman", 80, bold=True)
    draw_ui_text(title_font, "ANTIGRAVITY", cx-240, cy+150, (1.0, 0.9, 0.8))
    draw_ui_text(font, "Dark Fantasy RPG", cx-80, cy+110, (0.7, 0.7, 0.7))
    
    opts = ["NEW GAME", "EXIT"]
    mx, my = pygame.mouse.get_pos(); gl_my = HEIGHT - my
    
    for i, opt in enumerate(opts):
        y = cy - 50 - i*70
        w = 300
        x = cx - w/2
        
        hover = x < mx < x+w and y < gl_my < y+50
        col = (0.5, 0.4, 0.3, 1) if hover else (0.2, 0.15, 0.1, 1) # Brownish theme
        
        draw_rect(x, y, w, 50, col)
        # Center text roughly
        draw_ui_text(font, opt, x + (100 if i==0 else 125), y+15)
        
        if hover and pygame.mouse.get_pressed()[0]:
            return opt
    return None

def draw_scene(shadow_pass=False):
    if terrain_list: glCallList(terrain_list)
    if 'tree' in display_lists:
        glColor3f(1,1,1) if not shadow_pass else glColor3f(0,0,0)
        for i in range(20):
            r1 = math.sin(i*123)*30
            r2 = math.cos(i*321)*30
            glPushMatrix()
            glTranslatef(r1, get_height(r1, r2), r2)
            glScalef(1.5, 1.5, 1.5)
            # Trees don't cast projected shadows in this simple mode
            if not shadow_pass: glCallList(display_lists['tree'])
            glPopMatrix()
            
    for ent in entities: ent.draw(shadow_pass)

def main():
    global WIDTH, HEIGHT, paused, show_settings, game_state, player, shadows_enabled, fps_limit, fps_slider_val
    
    pygame.init()
    
    # === AUDIO ===
    try:
        # Try finding a music file
        music_files = ["music.mp3", "music.wav", "dark_fantasy.mp3", "dark_fantasy.wav"]
        music_path = None
        for f in music_files:
            path = os.path.join("assets", "music", f)
            if os.path.exists(path):
                music_path = path
                break
                
        if music_path:
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.play(-1, fade_ms=3000)
            pygame.mixer.music.set_volume(0.4)
            print(f"Loaded music: {music_path}")
        else:
            print("No music file found in assets/music/. Please add 'music.mp3' or 'music.wav'.")
            
    except Exception as e:
        print(f"Audio Error: {e}")

    # GL Attributes for Quality
    pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
    pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 4) # MSAA
    pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)
    
    screen = pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL | RESIZABLE)
    pygame.display.set_caption("Antigravity RPG")
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)
    
    # GPU CHECK
    try:
        renderer = glGetString(GL_RENDERER).decode()
        vendor = glGetString(GL_VENDOR).decode()
        print(f"GPU Renderer: {renderer} ({vendor})")
    except: pass
    
    # FPS Defaults
    fps_limit = 60 
    fps_slider_val = 0.25
    
    init()
    
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 24, bold=True)
    
    current_msaa = 4 
    running = True

    while running:
        dt = clock.tick(fps_limit)
        df = min(dt / 16.666, 3.0) # Delta factor normalized to 60 FPS, cap at 3.0
        
        # ... MSAA Logic ...
        if msaa_level != current_msaa:
             current_msaa = msaa_level
             pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, current_msaa)
             screen = pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL | RESIZABLE)
             # Re-init textures might be needed if context lost
             init() 
        
        # Events
        for e in pygame.event.get():
             if e.type == QUIT: running = False
             if e.type == VIDEORESIZE:
                 WIDTH, HEIGHT = e.w, e.h
                 screen = pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL | RESIZABLE)
                 glViewport(0, 0, WIDTH, HEIGHT)
                 
             if e.type == KEYDOWN:
                if e.key == K_ESCAPE:
                    if show_settings: show_settings = False
                    elif player.inventory.opened_container:
                        player.inventory.opened_container.is_open = False
                        player.inventory.opened_container = None
                        pygame.mouse.set_visible(False)
                        pygame.event.set_grab(True)
                    elif game_state == STATE_GAME: # Pause only in game
                        paused = not paused
                        pygame.mouse.set_visible(paused)
                        pygame.event.set_grab(not paused)
                        
                if e.key == K_TAB and not paused and (game_state==STATE_GAME or game_state==STATE_INVENTORY):
                    if game_state == STATE_INVENTORY:
                         game_state = STATE_GAME
                         pygame.mouse.set_visible(False); pygame.event.set_grab(True)
                         if player.inventory.opened_container:
                             player.inventory.opened_container.is_open = False
                             player.inventory.opened_container = None
                    else:
                         game_state = STATE_INVENTORY
                         pygame.mouse.set_visible(True); pygame.event.set_grab(False)
                         
                if e.key == K_e and game_state == STATE_GAME:
                     # Interact
                     closest = None
                     min_d = 5.0
                     for ent in entities:
                         if isinstance(ent, Chest):
                             d = math.sqrt((player.pos[0]-ent.x)**2 + (player.pos[2]-ent.z)**2)
                             if d < min_d: closest=ent; min_d=d
                     
                     if closest:
                         closest.is_open = True
                         player.inventory.opened_container = closest
                         game_state = STATE_INVENTORY
                         pygame.mouse.set_visible(True); pygame.event.set_grab(False)
                         pygame.event.clear(MOUSEBUTTONDOWN) # Clear any erroneous clicks
                         pygame.event.clear(MOUSEBUTTONUP)
                         
             if e.type == MOUSEBUTTONDOWN and game_state == STATE_GAME and not paused:
                 if e.button == 1: 
                     # Attack if Sword Equipped
                     if player.inventory.equipped[1] and player.inventory.equipped[1].type == 'weapon':
                         player.attacking = True
        
        # Update
        if not paused and game_state == STATE_GAME:
            mdx, mdy = pygame.mouse.get_rel()
            player.rot[0] += mdx * MOUSE_SENS
            player.rot[1] = max(-89, min(89, player.rot[1] + mdy * MOUSE_SENS))
            
            # Move
            keys = pygame.key.get_pressed()
            rad = math.radians(player.rot[0])
            s, c = math.sin(rad), math.cos(rad)
            dx, dz = 0, 0
            if keys[K_w]: dx+=s; dz-=c
            if keys[K_s]: dx-=s; dz+=c
            if keys[K_a]: dx-=c; dz-=s
            if keys[K_d]: dx+=c; dz+=s
            
            player.pos[0] += dx * SPEED * df
            player.pos[2] += dz * SPEED * df
            
            # Ground clamp
            gy = get_height(player.pos[0], player.pos[2])
            player.pos[1] = gy + 2.0 
            player.update(df)
            
            for ent in entities: ent.update(df)
        
        elif game_state == STATE_MENU:
             # Live Background Rotation
             player.rot[0] += 0.1 * df
             player.pos[1] = get_height(player.pos[0], player.pos[2]) + 10.0 # Fly high
             pygame.mouse.set_visible(True)

        # Render 3D
        glClearColor(*C_SKY)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        glMatrixMode(GL_PROJECTION); glLoadIdentity()
        gluPerspective(FOV, WIDTH/HEIGHT, 0.1, 200.0)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity()
        
        # Camera Transform
        pch = math.radians(player.rot[1])
        rad = math.radians(player.rot[0])
        cy = player.cam_h
        
        lx = player.pos[0] + math.sin(rad)*math.cos(pch)
        lz = player.pos[2] - math.cos(rad)*math.cos(pch)
        ly = cy - math.sin(pch)
        
        gluLookAt(player.pos[0], cy, player.pos[2], lx, ly, lz, 0, 1, 0)
        
        # LIGHTING SETUP
        # Adjusted for better shadow angle (Sun position)
        light_pos = [80, 120, 60, 1] 
        glEnable(GL_LIGHTING); glEnable(GL_LIGHT0); glEnable(GL_DEPTH_TEST)
        glLightfv(GL_LIGHT0, GL_POSITION, light_pos)
        glLightfv(GL_LIGHT0, GL_AMBIENT, C_AMBIENT)
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.8, 0.8, 0.7, 1))
        glEnable(GL_COLOR_MATERIAL)
        
        # === 1. Shadow Pass (Projected) ===
        if shadows_enabled:
            glDisable(GL_LIGHTING); glDisable(GL_TEXTURE_2D)
            glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            # Use Polygon Offset to avoid Z-Fighting with ground
            glEnable(GL_POLYGON_OFFSET_FILL)
            glPolygonOffset(-1.0, -1.0)
            
            shadow_projection(light_pos, ground_y=0) 
            
            # Only draw entities in shadow pass
            for ent in entities: ent.draw(shadow_pass=True)
            
            glPopMatrix() # Pop shadow matrix
            
            glDisable(GL_POLYGON_OFFSET_FILL)
            glDisable(GL_BLEND); glEnable(GL_LIGHTING)
            
            # Restore Matrix (Not needed strictly if we popped, but safer to re-lookAt)
            glLoadIdentity()
            gluLookAt(player.pos[0], cy, player.pos[2], lx, ly, lz, 0, 1, 0)

        # === 2. Normal Pass ===
        draw_scene(shadow_pass=False)
        
        # HUD / UI Overlay
        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST) # Ensure UI is on top
        
        # Player Hands/Weapon (3D HUD)
        if game_state == STATE_GAME:
            player.draw_hud()

        # UI Projection
        glMatrixMode(GL_PROJECTION); glLoadIdentity()
        glOrtho(0, WIDTH, 0, HEIGHT, -1, 1)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity()
        
        if paused:
            res = draw_pause_menu(font)
            if res == "RESUME": paused = False; pygame.mouse.set_visible(False); pygame.event.set_grab(True)
            elif res == "SETTINGS": show_settings = True
            elif res == "EXIT": running = False
        
        elif game_state == STATE_MENU:
            if not show_settings:
                res = draw_title_menu(font)
                if res == "NEW GAME":
                     # Reset Player
                     player.pos = [0, 5, 0]
                     game_state = STATE_GAME
                     pygame.mouse.set_visible(False); pygame.event.set_grab(True)
                elif res == "EXIT": running = False
            else:
                draw_settings(font)
            
        elif game_state == STATE_INVENTORY:
            draw_inventory(font)
            
        # Draw HUD Bars and Hotbar in Game
        if game_state == STATE_GAME and not paused:
             # HP Bar
             draw_rect(20, HEIGHT-40, 200, 20, (0.2, 0, 0, 1))
             draw_rect(20, HEIGHT-40, 200, 20, (0.8, 0, 0, 1)) # Full HP placeholder
             draw_ui_text(font, "HEALTH", 25, HEIGHT-38, (255,255,255))
             
             # Energy Bar
             draw_rect(20, HEIGHT-70, 200, 20, (0.2, 0.2, 0, 1))
             draw_rect(20, HEIGHT-70, 150, 20, (0.8, 0.8, 0, 1)) # 75% Energy
             draw_ui_text(font, "ENERGY", 25, HEIGHT-68, (255,255,255))
             
             # Hotbar (Items 0-9)
             slot_w = 50
             pad = 5
             start_x = WIDTH//2 - (10*(slot_w+pad)) // 2
             for i in range(10):
                 x = start_x + i*(slot_w+pad)
                 y = 10
                 draw_rect(x, y, slot_w, slot_w, (0.1, 0.1, 0.1, 0.8))
                 # Highlight equipped?
                 item = player.inventory.slots[i]
                 if item: 
                     draw_rect(x+2, y+2, slot_w-4, slot_w-4, (0.5, 0.5, 0.5, 1))
                     
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
