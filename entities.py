import math
import random
import pygame
from OpenGL.GL import *
from OpenGL.GLU import *
from config import WIDTH, HEIGHT
from world import get_height
from inventory import Inventory, Item
from utils import texture_ids, display_lists, sfx_sounds

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
        self.active_slot = 1 # 1 or 2 for weapon slots
    
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
        # Get currently active weapon
        # active_slot is 1-indexed (1-9), pockets is 0-indexed
        idx = self.active_slot - 1
        weapon = None
        if 0 <= idx < len(self.inventory.pockets):
            weapon = self.inventory.pockets[idx]
        
        # Always draw weapon in hand if equipped (idle or attacking)
        if weapon and weapon.type == 'weapon':
            glLoadIdentity()
            glDisable(GL_DEPTH_TEST); glDisable(GL_LIGHTING); glDisable(GL_TEXTURE_2D)
            
            # Use 3D projection for weapon in hand
            glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
            gluPerspective(60, WIDTH/HEIGHT, 0.1, 100)
            glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
            
            glEnable(GL_LIGHTING); glEnable(GL_LIGHT0)
            glEnable(GL_TEXTURE_2D); glBindTexture(GL_TEXTURE_2D, texture_ids.get('sword_metal', 0))
            
            # Swing animation or idle bob
            if self.attacking:
                swing = math.sin(self.anim_t) * 2.0
                glTranslatef(0.4 - swing*0.2, -0.4, -0.8 + swing*0.1) 
                glRotatef(-10 + swing*40, 1, 0, 0)
                glRotatef(-swing*30, 0, 1, 0) 
            else:
                # Idle bob
                bob = math.sin(pygame.time.get_ticks() * 0.003) * 0.02
                glTranslatef(0.45, -0.5 + bob, -0.7)
                glRotatef(-15, 1, 0, 0)
                glRotatef(10, 0, 1, 0)
            
            # Draw Sword Model (Procedural)
            quad = gluNewQuadric(); gluQuadricTexture(quad, GL_TRUE)
            glColor3f(0.8, 0.8, 0.9) # Metallic
            
            # Blade
            glPushMatrix(); glScalef(0.06, 0.7, 0.015); gluSphere(quad, 1, 10, 10); glPopMatrix()
            # Guard
            glColor3f(0.4, 0.3, 0.2) # Bronze
            glPushMatrix(); glTranslatef(0, -0.5, 0); glScalef(0.25, 0.04, 0.04); gluSphere(quad, 1, 8, 8); glPopMatrix()
            # Handle
            glColor3f(0.3, 0.2, 0.1) # Wood
            glPushMatrix(); glTranslatef(0, -0.7, 0); glScalef(0.04, 0.18, 0.04); gluSphere(quad, 1, 8, 8); glPopMatrix()
            # Pommel
            glColor3f(0.5, 0.4, 0.3)
            glPushMatrix(); glTranslatef(0, -0.85, 0); glScalef(0.06, 0.06, 0.06); gluSphere(quad, 1, 6, 6); glPopMatrix()

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
        # We can implement lid animation logic here if needed, but Chest.draw might handle it visually
        # or we just rely on state.
        pass
        
    def draw(self, shadow_pass=False):
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        
        lid = display_lists.get('chest')
        if lid:
            if shadow_pass:
                glColor4f(0, 0, 0, 0.4)
                glDisable(GL_TEXTURE_2D)
                glDisable(GL_LIGHTING)
            else:
                # Material and texture is baked into display list
                glEnable(GL_TEXTURE_2D)
                
            glDisable(GL_CULL_FACE)
            glScalef(0.6, 0.6, 0.6)  # Slightly bigger
            glCallList(lid)
            glEnable(GL_CULL_FACE)
        
        glPopMatrix()

class Wolf:
    def __init__(self, x, z):
        self.x, self.z = x, z
        self.y = get_height(x, z)
        self.rot = random.uniform(0, 360)
        self.anim = 0
        self.sound_cooldown = random.randint(3000, 8000)
        self.last_sound_time = pygame.time.get_ticks()
        
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
        glRotatef(angle - 45, 1, 0, 0)
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
        self.sound_cooldown = random.randint(4000, 10000)
        self.last_sound_time = pygame.time.get_ticks()
        
    def update(self, df):
        self.anim += 0.15 * df
        self.x += math.sin(math.radians(self.rot)) * 0.05 * df
        self.z += math.cos(math.radians(self.rot)) * 0.05 * df
        self.y = get_height(self.x, self.z)
        
        if random.random() < 0.02 * df:
             self.rot += random.uniform(-45, 45)

    def draw(self, shadow_pass=False):
        glPushMatrix()
        glTranslatef(self.x, self.y + 0.5, self.z) 
        glRotatef(self.rot, 0, 1, 0)
        
        if not shadow_pass:
             glColor3f(0.1, 0.1, 0.1) 
        else:
             glColor4f(0,0,0, 0.4)
             
        quad = gluNewQuadric()
        glPushMatrix(); glScalef(0.4, 0.3, 0.5); gluSphere(quad, 1, 8, 8); glPopMatrix() # Abdomen
        glPushMatrix(); glTranslatef(0, 0.1, 0.4); glScalef(0.2, 0.15, 0.2); gluSphere(quad, 1, 8, 8); glPopMatrix() # Head
        
        for side in [-1, 1]:
            for i in range(4):
                glPushMatrix()
                offset_z = 0.2 - i*0.15
                glTranslatef(side*0.3, 0, offset_z)
                lift = math.sin(self.anim + side*i + i*2) * 0.2
                glRotate(side * 40 - i*10, 0, 1, 0) 
                glRotate(-30 + lift*30, 0, 0, 1) 
                glPushMatrix(); glScalef(0.3, 0.05, 0.05); gluSphere(quad, 1, 4, 4); glPopMatrix()
                glTranslatef(0.3, -0.1, 0)
                glRotate(side * 60, 0, 0, 1) 
                glPushMatrix(); glScalef(0.4, 0.05, 0.05); gluSphere(quad, 1, 4, 4); glPopMatrix()
                glPopMatrix()
                
        if not shadow_pass: glDisable(GL_TEXTURE_2D)
        glPopMatrix()

class Mushroom:
    def __init__(self, x, z):
        self.x, self.y, self.z = x, get_height(x, z), z
        # Randomize size
        self.scale = random.uniform(0.6, 1.2)
        
    def update(self, df):
        pass # Static
        
    def draw(self, shadow_pass=False):
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        glScalef(self.scale, self.scale, self.scale)
        
        quad = gluNewQuadric(); gluQuadricTexture(quad, GL_TRUE)
        
        if shadow_pass:
             glColor4f(0, 0, 0, 0.4)
             glDisable(GL_TEXTURE_2D)
        else:
             glColor3f(1,1,1)
             glEnable(GL_TEXTURE_2D)
             
        # Stem
        if not shadow_pass: glBindTexture(GL_TEXTURE_2D, texture_ids.get('mushroom_stem', 0))
        glPushMatrix()
        glRotatef(-90, 1, 0, 0)
        gluCylinder(quad, 0.1, 0.15, 0.4, 8, 2)
        glPopMatrix()
        
        # Cap
        if not shadow_pass: glBindTexture(GL_TEXTURE_2D, texture_ids.get('mushroom_cap', 0))
        glPushMatrix()
        glTranslatef(0, 0.4, 0)
        glRotatef(-90, 1, 0, 0)
        # Disk bottom
        gluDisk(quad, 0.1, 0.4, 10, 2)
        # Top
        glTranslatef(0, 0, 0) 
        # Half sphere or Cone
        # Let's do a squashed sphere
        glScalef(1, 1, 0.6)
        gluSphere(quad, 0.4, 10, 10)
        glPopMatrix()
        
        if not shadow_pass: glDisable(GL_TEXTURE_2D)
        glPopMatrix()

class Rock:
    def __init__(self, x, z):
        self.x, self.z = x, z
        self.y = get_height(x, z), z
        self.y = get_height(x, z)
        self.scale = random.uniform(0.8, 1.5)
        self.rot = random.uniform(0, 360)
        # Generate random distortion for rock shape
        self.shape_seed = random.randint(0, 100)
        
    def update(self, df):
        pass
        
    def draw(self, shadow_pass=False):
        glPushMatrix()
        glTranslatef(self.x, self.y + 0.2*self.scale, self.z) # Sink slightly
        glRotatef(self.rot, 0, 1, 0)
        glScalef(self.scale, self.scale*0.7, self.scale)
        
        quad = gluNewQuadric(); gluQuadricTexture(quad, GL_TRUE)
        
        if shadow_pass:
             glColor4f(0, 0, 0, 0.4)
             glDisable(GL_TEXTURE_2D)
        else:
             # Darker grey
             glColor3f(0.6, 0.6, 0.65)
             glEnable(GL_TEXTURE_2D)
             glBindTexture(GL_TEXTURE_2D, texture_ids.get('rock_wall', 0))
             
        # Main body
        gluSphere(quad, 0.5, 8, 8)
        
        # Detail lumps
        random.seed(self.shape_seed)
        for i in range(3):
            glPushMatrix()
            rx, ry, rz = random.uniform(-0.3, 0.3), random.uniform(0, 0.3), random.uniform(-0.3, 0.3)
            glTranslatef(rx, ry, rz)
            s = random.uniform(0.2, 0.4)
            glScalef(s, s, s)
            gluSphere(quad, 0.5, 6, 6)
            glPopMatrix()
            
        if not shadow_pass: glDisable(GL_TEXTURE_2D)
        glPopMatrix()