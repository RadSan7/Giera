import sys
import math
import random
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

# Modules
import config
from config import WIDTH, HEIGHT, FOV, MOUSE_SENS, SPEED, FOOTSTEP_COOLDOWN, C_SKY, C_AMBIENT
from utils import load_texture, load_obj_display_list, load_sfx, draw_rect, draw_ui_text, sfx_sounds, display_lists, texture_ids
from world import get_height, shadow_projection, draw_ground
from entities import Player, Chest, Wolf, Spider, Mushroom, Rock
from inventory import draw_inventory, Item
from menu import Menu

# Initial Setup
pygame.init()
pygame.mixer.init()

# Display
screen = pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL | RESIZABLE)
pygame.display.set_caption("Giera | Refactored")
pygame.mouse.set_visible(False)
pygame.event.set_grab(True)

# OpenGL Init
glEnable(GL_DEPTH_TEST)
glEnable(GL_LIGHTING)
glEnable(GL_COLOR_MATERIAL)
glEnable(GL_NORMALIZE)
glShadeModel(GL_SMOOTH)

# Fog - lighter and farther
glEnable(GL_FOG)
glFogfv(GL_FOG_COLOR, C_SKY)
glFogi(GL_FOG_MODE, GL_LINEAR)
glFogf(GL_FOG_START, 50.0) 
glFogf(GL_FOG_END, 150.0)   # Increased view distance

# Lighting - brighter
glEnable(GL_LIGHT0)
glLightfv(GL_LIGHT0, GL_AMBIENT, (0.05, 0.05, 0.1, 1.0))  # Dark ambient
glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.2, 0.2, 0.3, 1.0)) # Pale Moonlight
glLightfv(GL_LIGHT0, GL_SPECULAR, (1.0, 1.0, 1.0, 1.0))
glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (0.4, 0.4, 0.45, 1.0))  # Global ambient

# States
STATE_MENU = 0
STATE_GAME = 1
STATE_INVENTORY = 2
game_state = STATE_MENU  # Start in menu
paused = False
show_settings = False
running = True
game_initialized = False  # Track if game world is generated

# Fonts
font = pygame.font.SysFont('arial', 24, bold=True)
big_font = pygame.font.SysFont('arial', 48, bold=True)

# System
clock = pygame.time.Clock()
last_footstep_time = 0
menu_system = None


def init_assets():
    # Textures
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
    
    # UI Textures (lazy load in draw_inventory usually, but preloading is fine)
    # Models - tree with material mapping for bark and leaves
    display_lists['tree'] = load_obj_display_list('fir.obj', 'tree_branch', {
        'Trunk_bark': 'tree_bark'
    })
    display_lists['chest'] = load_obj_display_list('chest.obj', 'chest')
    
    # Sound
    load_sfx('footstep', 'footstep.mp3')
    load_sfx('sword_swing', 'sword_swing.mp3')
    load_sfx('wolf_growl', 'wolf_growl.mp3')
    load_sfx('spider_hiss', 'spider_hiss.mp3')

# Entities
player = Player()
entities = []

def generate_world():
    global entities
    entities = []
    # Trees
    for i in range(50):
        x = random.uniform(-50, 50)
        z = random.uniform(-50, 50)
        if math.sqrt(x*x + z*z) < 5: continue
        # Trees draw directly? No class yet.
        # Let's add simple tree objects or draw loop?
        # Refactor note: Trees should be entities or world objects.
        # For now, store pos and draw in loop.
        entities.append({'type':'tree', 'x':x, 'z':z, 'y':get_height(x,z)})
        
    # Chests
    # Guaranteed chest right in front of spawn
    entities.append(Chest(0, -3))  # Directly in front of player
    
    for i in range(4):
        cx, cz = random.uniform(-40, 40), random.uniform(-40, 40)
        entities.append(Chest(cx, cz))
        
    # Mobs
    for i in range(3):
        entities.append(Wolf(random.uniform(-30,30), random.uniform(-30,30)))
    for i in range(3):
        entities.append(Spider(random.uniform(-30,30), random.uniform(-30,30)))

    # Props (Mushrooms and Rocks)
    for i in range(40):
        mx, mz = random.uniform(-50, 50), random.uniform(-50, 50)
        entities.append(Mushroom(mx, mz))
        
    for i in range(15):
        rx, rz = random.uniform(-50, 50), random.uniform(-50, 50)
        entities.append(Rock(rx, rz))

init_assets()
menu_system = Menu(font, big_font)
generate_world()

def draw_moon():
    glPushMatrix()
    # Light pos matches: [50, 100, 50, 0]
    glTranslatef(50, 100, 50)
    
    glDisable(GL_LIGHTING)
    glDisable(GL_FOG)
    glDisable(GL_TEXTURE_2D)
    
    glColor3f(1.0, 1.0, 0.6) # Yellowish
    
    # Draw simple sphere
    quad = gluNewQuadric()
    gluSphere(quad, 8.0, 16, 16)
    
    glEnable(GL_FOG)
    glEnable(GL_LIGHTING)
    glPopMatrix()

def draw_scene(shadow_pass=False):
    # World
    if not shadow_pass:
        draw_moon() # Draw before transparent items, but after clear
        draw_ground(texture_ids)
    
    # Collect entities by type for proper render order
    trees = []
    other_entities = []
    
    for ent in entities:
        if isinstance(ent, dict) and ent['type'] == 'tree':
            trees.append(ent)
        else:
            other_entities.append(ent)
    
    # Draw opaque entities first (chests, mobs)
    for ent in other_entities:
        if hasattr(ent, 'draw'):
            ent.draw(shadow_pass)
    
    # Draw trees with alpha - disable depth write for transparency
    tid_tree = display_lists.get('tree')
    
    if not shadow_pass:
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_ALPHA_TEST)
        glAlphaFunc(GL_GREATER, 0.5)  # Stricter alpha test
        glDepthMask(GL_FALSE)  # Don't write to depth buffer for transparent parts
    else:
        glDisable(GL_TEXTURE_2D)
    
    # Sort trees by distance from camera (back to front)
    trees_sorted = sorted(trees, key=lambda t: -(t['x']-player.pos[0])**2 - (t['z']-player.pos[2])**2)
    
    for ent in trees_sorted:
        glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_TRUE)
        glDisable(GL_CULL_FACE)
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0,0,0,1))
        
        glPushMatrix()
        glTranslatef(ent['x'], ent['y'], ent['z'])
        glScalef(2.5, 2.5, 2.5)
        
        if shadow_pass:
            glColor4f(0, 0, 0, 0.4)
        
        if tid_tree: 
            glCallList(tid_tree)
        
        glPopMatrix()
        
        glEnable(GL_CULL_FACE)
        glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_FALSE)
    
    if not shadow_pass:
        glDepthMask(GL_TRUE)  # Re-enable depth writing
        glDisable(GL_ALPHA_TEST)

# Menu button areas (will be set during drawing)
menu_buttons = {}

def start_new_game():
    global game_state, game_initialized, paused
    generate_world()
    player.pos = [0.0, 5.0, 0.0]
    player.rot = [0.0, 0.0]
    player.cam_h = 5.0
    game_state = STATE_GAME
    game_initialized = True
    paused = False
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)
    pygame.mouse.get_rel()  # Clear accumulated movement

# === MAIN LOOP ===
def main():
    global running, game_state, paused, show_settings, WIDTH, HEIGHT, last_footstep_time, menu_buttons, menu_system
    
    # Starting Items
    if not player.inventory.pockets[0]:
        player.inventory.add_item(Item("Miecz", "sword_metal", "weapon"))
    if not player.inventory.pockets[1]:
        player.inventory.add_item(Item("Chleb", "mushroom_cap", "misc")) # Placeholder icon/name

    
    while running:
        df = clock.tick(60) * 0.06
        if df > 2.0: df = 2.0
        
        # Events
        for e in pygame.event.get():
            if e.type == QUIT: running = False
            if e.type == VIDEORESIZE:
                WIDTH, HEIGHT = e.w, e.h
                config.WIDTH, config.HEIGHT = WIDTH, HEIGHT # Update config globals slightly hacky
                screen = pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL | RESIZABLE)
                glViewport(0, 0, WIDTH, HEIGHT)
            # Global Menu Handling (Mouse clicks from menu.py)
            if game_state == STATE_MENU:
                action = menu_system.handle_input(e)
                if action == 'new_game':
                    start_new_game()
                elif action == 'save_settings':
                    # Apply Settings
                    val_fov = menu_system.settings['fov']['val']
                    val_sens = menu_system.settings['sens']['val']
                    config.FOV = val_fov
                    config.MOUSE_SENS = val_sens
                    print(f"Settings Applied: FOV={val_fov}, Sens={val_sens}")
                elif action == 'quit':
                    running = False
            
            # Global Key Handling (Toggle Pause / Inventory)
            if e.type == KEYDOWN:
                if e.key == K_ESCAPE:
                    if game_state == STATE_GAME:
                        paused = not paused
                        pygame.mouse.set_visible(paused)
                        pygame.event.set_grab(not paused)
                    elif game_state == STATE_INVENTORY:
                        if player.inventory.opened_container:
                            player.inventory.opened_container.is_open = False
                            player.inventory.opened_container = None
                        game_state = STATE_GAME
                        pygame.mouse.set_visible(False)
                        pygame.event.set_grab(True)
                        pygame.mouse.get_rel()
                
                if e.key == K_s and paused:
                    show_settings = not show_settings

                if e.key == K_q and paused:
                    # Quit to Menu
                    game_state = STATE_MENU
                    pygame.mouse.set_visible(True)
                    pygame.event.set_grab(False)

                        
                if e.key == K_TAB and not paused:
                    if game_state == STATE_INVENTORY:
                        game_state = STATE_GAME
                        pygame.mouse.set_visible(False); pygame.event.set_grab(True)
                        pygame.mouse.get_rel()
                        if player.inventory.opened_container:
                            player.inventory.opened_container.is_open = False
                            player.inventory.opened_container = None
                    elif game_state == STATE_GAME:
                        game_state = STATE_INVENTORY
                        pygame.mouse.set_visible(True); pygame.event.set_grab(False)
                        
                if e.key == K_e and game_state == STATE_GAME and not paused:
                     # Raycast Interaction
                     rad = math.radians(player.rot[0])
                     pitch = math.radians(player.rot[1])
                     dx = math.sin(rad) * math.cos(pitch)
                     dy = -math.sin(pitch)
                     dz = -math.cos(rad) * math.cos(pitch)
                     ox, oy, oz = player.pos[0], player.cam_h, player.pos[2]
                     
                     target_chest = None
                     min_dist = 2.5
                     
                     for ent in entities:
                         if isinstance(ent, Chest):
                             dist_to_center = math.sqrt((ent.x - ox)**2 + (ent.y - oy)**2 + (ent.z - oz)**2)
                             if dist_to_center > min_dist + 1.5: continue
                             vx, vy, vz = ent.x - ox, ent.y + 0.5 - oy, ent.z - oz
                             dot = vx*dx + vy*dy + vz*dz
                             if dot < 0: continue
                             
                             cross_x = vy*dz - vz*dy
                             cross_y = vz*dx - vx*dz
                             cross_z = vx*dy - vy*dx
                             dist_from_ray = math.sqrt(cross_x**2 + cross_y**2 + cross_z**2)
                             
                             if dist_from_ray < 0.8:
                                 if dot < min_dist:
                                     target_chest = ent
                                     min_dist = dot
                                     
                     if target_chest:
                         target_chest.is_open = True
                         player.inventory.opened_container = target_chest
                         game_state = STATE_INVENTORY
                         paused = False
                         pygame.mouse.set_visible(True); pygame.event.set_grab(False)

                if e.key == K_1: player.active_slot = 1
                if e.key == K_2: player.active_slot = 2
                if e.key == K_3: player.active_slot = 3
                if e.key == K_4: player.active_slot = 4
                if e.key == K_5: player.active_slot = 5
                if e.key == K_6: player.active_slot = 6
                if e.key == K_7: player.active_slot = 7
                if e.key == K_8: player.active_slot = 8
                if e.key == K_9: player.active_slot = 9
                
            if e.type == MOUSEBUTTONDOWN:
                        
                if game_state == STATE_GAME and not paused and e.button == 1:
                    # active_slot is 1-indexed
                    idx = player.active_slot - 1
                    w = None
                    if 0 <= idx < len(player.inventory.pockets):
                        w = player.inventory.pockets[idx]
                    if w and w.type == 'weapon':
                        player.attacking = True
                        if 'sword_swing' in sfx_sounds: sfx_sounds['sword_swing'].play()

        # === UPDATE & DRAW ===
        
        # Clear Screen (Common)
        glEnable(GL_DEPTH_TEST)
        glClearColor(*C_SKY)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        if game_state == STATE_MENU:
            # --- MENU DRAW ---
            # --- MENU DRAW ---
            menu_system.draw_main_menu()

            
        elif game_state == STATE_GAME or game_state == STATE_INVENTORY:
            # --- GAME UPDATE ---
            if not paused and game_state == STATE_GAME:
                mdx, mdy = pygame.mouse.get_rel()
                player.rot[0] += mdx * MOUSE_SENS
                player.rot[1] = max(-89, min(89, player.rot[1] + mdy * MOUSE_SENS))
                
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
                player.pos[1] = get_height(player.pos[0], player.pos[2]) + 2.0
                
                # Sound
                if (dx!=0 or dz!=0) and 'footstep' in sfx_sounds:
                    now = pygame.time.get_ticks()
                    if now - last_footstep_time > FOOTSTEP_COOLDOWN:
                        last_footstep_time = now
                        sfx_sounds['footstep'].play()
                
                player.update(df)
                for ent in entities:
                    if not isinstance(ent, dict) and hasattr(ent, 'update'): ent.update(df)

            # --- GAME DRAW ---
            glEnable(GL_DEPTH_TEST)
            glEnable(GL_LIGHTING)
            glEnable(GL_FOG)
            
            glMatrixMode(GL_PROJECTION); glLoadIdentity()
            gluPerspective(config.FOV, WIDTH/HEIGHT, 0.1, 200.0) # Use config.FOV
            glMatrixMode(GL_MODELVIEW); glLoadIdentity()
            
            # Camera
            pch = math.radians(player.rot[1])
            rad = math.radians(player.rot[0])
            cy = player.cam_h
            lx = player.pos[0] + math.sin(rad)*math.cos(pch)
            lz = player.pos[2] - math.cos(rad)*math.cos(pch)
            ly = cy - math.sin(pch)
            gluLookAt(player.pos[0], cy, player.pos[2], lx, ly, lz, 0, 1, 0)
            
            # Lights
            # Lights
            # Moonlight Direction (High in sky)
            glLightfv(GL_LIGHT0, GL_POSITION, [50, 100, 50, 0])
            
            # Scene
            draw_scene(False)
            
            # UI Overlay
            glMatrixMode(GL_PROJECTION); glLoadIdentity()
            glOrtho(0, WIDTH, HEIGHT, 0, -1, 1)
            glMatrixMode(GL_MODELVIEW); glLoadIdentity()
            glDisable(GL_DEPTH_TEST)
            glDisable(GL_LIGHTING)
            glDisable(GL_FOG)       # CRITICAL FIX for UI visibility
            glDisable(GL_CULL_FACE) # CRITICAL FIX for UI visibility

            
            if game_state == STATE_GAME:
                if not paused: player.draw_hud()
                # HUD elements
                draw_rect(20, HEIGHT-40, 200, 20, (0.8, 0, 0, 1)) # Health
                # Hotbar
                start_x = WIDTH//2 - (9*(68))//2
                for i in range(9):
                    x = start_x + i*68
                    col = (0.2,0.2,0.2,0.8)
                    if i < 2 and player.active_slot == i+1: col = (0.4, 0.4, 0.2, 0.8)
                    draw_rect(x, HEIGHT-75, 60, 60, col)
                    item = player.inventory.pockets[i]
                    if item:
                        # Simple Item indicator
                        icol = (0.6,0.3,0.3,1) if item.type=='weapon' else (0.3,0.6,0.3,1)
                        draw_rect(x+5, HEIGHT-70, 50, 50, icol)

            if paused:
                menu_system.draw_pause_menu()

                
            if game_state == STATE_INVENTORY:
                draw_inventory(player, font)

        pygame.display.flip()
    
    pygame.quit()

if __name__ == "__main__":
    main()
