import pygame
from OpenGL.GL import *
from config import WIDTH, HEIGHT
from utils import draw_rect, draw_textured_rect, draw_ui_text, texture_ids, load_texture

class Item:
    def __init__(self, name, icon_texture, item_type="misc"):
        self.name = name
        self.icon = icon_texture
        self.type = item_type # 'weapon', 'misc'

class Inventory:
    def __init__(self):
        # 4.0 Data Structure
        self.armor = [None] * 4    # 4 armor slots
        self.backpack = [None] * 8 # 8 slots (2x4)
        self.pockets = [None] * 9  # 9 hotbar slots
        # equipped dict removed, strictly using pockets list now
        # Let's keep existing logic: pockets 0,1 are weapons
        
        self.drag_item = None
        self.drag_source = None # ('pocket', 0)
        self.drag_offset = (0,0)
        
        self.opened_container = None # For chests
        
    def add_item(self, item):
        # 1. Try Pockets (Slots 2-8, skip weapons 0-1)
        # Prioritize hotbar access
        for i in range(2, 9):
            if self.pockets[i] is None:
                self.pockets[i] = item
                return True
        
        # 2. Try Backpack (8 slots)
        for i in range(len(self.backpack)):
            if self.backpack[i] is None:
                self.backpack[i] = item
                return True
                
        return False

# UI Drawing Logic
def draw_inventory(player, font):
    # Consume mouse rel to avoid drift
    pygame.mouse.get_rel() 
    
    # Load Textures
    if 'ui_inventory_bg' not in texture_ids:
        load_texture('ui_inventory_bg', 'ui_inventory_bg.png')
    if 'ui_inventory_slot' not in texture_ids:
        load_texture('ui_inventory_slot', 'ui_inventory_slot.png')
    if 'icon_sword' not in texture_ids:
        load_texture('icon_sword', 'icon_sword.png')
    if 'icon_bread' not in texture_ids:
        load_texture('icon_bread', 'icon_bread.png')
        
    tid_bg = texture_ids.get('ui_inventory_bg', 0)
    tid_slot = texture_ids.get('ui_inventory_slot', 0)
    
    # Dim BG
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    draw_rect(0, 0, WIDTH, HEIGHT, (0, 0, 0, 0.85))
    
    # Scaling
    ui_scale = HEIGHT / 1080.0
    ui_scale = max(0.6, min(ui_scale, 1.5))
    def s(val): return int(val * ui_scale)
    
    inv = player.inventory
    mx, my = pygame.mouse.get_pos()
    cx, cy = WIDTH//2, HEIGHT//2
    
    # Panel Size
    p_w, p_h = s(800), s(800)
    px, py = cx - p_w//2, cy - p_h//2
    
    # Draw Background (The Zoned Panel V2)
    if tid_bg:
        draw_textured_rect(px, py, p_w, p_h, tid_bg, (1,1,1,1))
    else:
        draw_rect(px, py, p_w, p_h, (0.2,0.2,0.2,1))
        
    # --- MODULAR SLOT CONFIGURATION (4.0) ---
    slot_size = s(75) 
    slot_gap_x = s(10)
    slot_gap_y = s(10)
    
    armor_start_x = px + s(170) 
    armor_start_y = py + s(100)
    
    backpack_start_x = px + s(550)
    backpack_start_y = py + s(100)
    
    hotbar_start_x = px + s(55)
    hotbar_start_y = py + p_h - s(120)
    
    def draw_modular_slot(x, y, size, item, is_drag_src, slot_tex_id):
        # 1. Draw Frame
        if slot_tex_id:
            draw_textured_rect(x, y, size, size, slot_tex_id)
        else:
            draw_rect(x, y, size, size, (0.3, 0.3, 0.3, 1))
            
        # 2. Draw Interaction Highlight
        hover = x < mx < x+size and y < my < y+size
        if hover:
            draw_rect(x+s(5), y+s(5), size-s(10), size-s(10), (1, 1, 0.5, 0.1))
            
        # 3. Draw Item
        if item and not is_drag_src:
             # Draw Icon
            icon_id = 0
            if item.type == 'weapon' and 'icon_sword' in texture_ids: icon_id = texture_ids['icon_sword']
            elif item.name == 'Bread' and 'icon_bread' in texture_ids: icon_id = texture_ids['icon_bread']
            
            if icon_id:
                draw_textured_rect(x+s(10), y+s(10), size-s(20), size-s(20), icon_id)
            else:
                 col = (0.8, 0.2, 0.2, 1) if item.type == 'weapon' else (0.2, 0.8, 0.2, 1)
                 draw_rect(x+10, y+10, size-20, size-20, col)
                 draw_ui_text(font, item.name[:3], x+s(15), y+size//2, (255,255,255))
        return hover
        
    # Check if Chest is open
    has_chest = inv.opened_container and inv.opened_container.is_open

    # 1. ARMOR SLOTS (4) - Vertical Column (1x4)
    for i in range(4):
        col = 0
        row = i
        sx = armor_start_x + col*(slot_size + slot_gap_x)
        sy = armor_start_y + row*(slot_size + slot_gap_y)
        
        item = inv.armor[i]
        is_src = (inv.drag_item and inv.drag_source == ('armor', i))
        
        if draw_modular_slot(sx, sy, slot_size, item, is_src, tid_slot):
            if pygame.mouse.get_pressed()[0] and not inv.drag_item and item:
                inv.drag_item = item
                inv.drag_source = ('armor', i)
                inv.armor[i] = None

    # 2. BACKPACK SLOTS (8) - 2 Cols x 4 Rows
    for i in range(8):
        col = i % 2
        row = i // 2
        sx = backpack_start_x + col*(slot_size + slot_gap_x)
        sy = backpack_start_y + row*(slot_size + slot_gap_y)
        
        item = inv.backpack[i]
        is_src = (inv.drag_item and inv.drag_source == ('backpack', i))
        
        if draw_modular_slot(sx, sy, slot_size, item, is_src, tid_slot):
            if pygame.mouse.get_pressed()[0] and not inv.drag_item and item:
                inv.drag_item = item
                inv.drag_source = ('backpack', i)
                inv.backpack[i] = None
                inv.drag_source = ('backpack', i)
                inv.backpack[i] = None
                inv.drag_offset = (mx - sx, my - sy)

    # 3. HOTBAR SLOTS (9) - 1 Row
    for i in range(9):
        sx = hotbar_start_x + i*(slot_size + s(5)) 
        sy = hotbar_start_y
        
        item = inv.pockets[i]
        is_src = (inv.drag_item and inv.drag_source == ('pocket', i))
        
        if draw_modular_slot(sx, sy, slot_size, item, is_src, tid_slot):
            if pygame.mouse.get_pressed()[0] and not inv.drag_item and item:
                inv.drag_item = item
                inv.drag_source = ('pocket', i)
                inv.pockets[i] = None

    # === CHEST PANEL (If Open) ===
    if has_chest:
        chest_x = px + p_w + s(30)
        chest_y = py
        
        # Draw Chest Panel BG (Fallback Dark)
        draw_rect(chest_x+s(5), chest_y-s(5), p_w, p_h, (0,0,0,0.5)) # Shadow
        draw_rect(chest_x, chest_y, p_w, p_h, (0.1, 0.08, 0.08, 0.95))
        draw_ui_text(font, "CHEST", chest_x+s(20), chest_y+p_h-s(35), (200, 180, 150))
        
        c_items = inv.opened_container.items
        
        for i in range(15):
             col = i % 5
             row = i // 5
             sx = chest_x + s(60) + col*(slot_size+s(10))
             sy = chest_y + s(100) + row*(slot_size+s(10))
             
             item = c_items[i] if i < len(c_items) else None
             is_src = (inv.drag_item and inv.drag_source == ('chest', i))
             
             # Draw Slot BG
             draw_rect(sx, sy, slot_size, slot_size, (0.2, 0.15, 0.1, 1))
             
             if sx < mx < sx+slot_size and sy < my < sy+slot_size:
                 draw_rect(sx, sy, slot_size, slot_size, (1, 1, 0.5, 0.1))
                 if pygame.mouse.get_pressed()[0] and not inv.drag_item and item:
                     inv.drag_item = item
                     inv.drag_source = ('chest', i)
                     inv.opened_container.items[i] = None # Or remove from list logic if handling sparse array
                     # Simplify: just set to None here, but list logic might need care (pop vs None). 
                     # Current impl uses list of objects.
                     # Actually, original list was growing/shrinking? 
                     # Let's assume fixed slots for chest for now or careful index handling.
                     
             if item and not is_src:
                 # Draw Icon
                icon_id = 0
                if item.type == 'weapon' and 'icon_sword' in texture_ids: icon_id = texture_ids['icon_sword']
                elif item.name == 'Bread' and 'icon_bread' in texture_ids: icon_id = texture_ids['icon_bread']
                
                if icon_id:
                    draw_textured_rect(sx+s(5), sy+s(5), slot_size-s(10), slot_size-s(10), icon_id)
                else:
                     draw_rect(sx+5, sy+5, slot_size-10, slot_size-10, (100, 100, 100))
                     draw_ui_text(font, item.name[:3], sx+s(10), sy+size//2, (255,255,255))

    # --- DRAG & DROP ITEM DRAWING & LOGIC ---
    if inv.drag_item:
        # Draw Floating Item
        draw_rect(mx-s(35), my-s(35), s(70), s(70), (0.5, 0.5, 0.6, 0.5))
        # Icon
        icon_id = 0
        if inv.drag_item.type == 'weapon' and 'icon_sword' in texture_ids: icon_id = texture_ids['icon_sword']
        elif inv.drag_item.name == 'Bread' and 'icon_bread' in texture_ids: icon_id = texture_ids['icon_bread']
        if icon_id:
            draw_textured_rect(mx-s(35), my-s(35), s(70), s(70), icon_id)
        
        # DROP HANDLER
        if not pygame.mouse.get_pressed()[0]:
            dropped = False
            src_type, src_idx = inv.drag_source
            
            def return_source(item):
                if src_type == 'pocket': inv.pockets[src_idx] = item; 
                elif src_type == 'backpack': inv.backpack[src_idx] = item
                elif src_type == 'armor': inv.armor[src_idx] = item
                elif src_type == 'chest' and inv.opened_container:
                     # Put back in chest
                     if src_idx < len(inv.opened_container.items):
                         inv.opened_container.items[src_idx] = item
                     else:
                         inv.opened_container.items.append(item)
            
            # Check collisions with all slots
            # 1. Hotbar (Pockets) - 1 Row
            for i in range(9):
                sx = hotbar_start_x + i*(slot_size + s(5))
                sy = hotbar_start_y
                if sx < mx < sx+slot_size and sy < my < sy+slot_size:
                     # Restriction: First 2 slots (0, 1) are WEAPON ONLY
                     if i < 2 and inv.drag_item.type != 'weapon':
                         break # Reject drop

                     target = inv.pockets[i]
                     inv.pockets[i] = inv.drag_item
                     
                     if target: return_source(target)
                     if src_type == 'chest' and inv.opened_container: # Handle chest properly source remove
                         pass # Already set to None in drag start
                     dropped = True; break
            
            # 2. Backpack - 2 Cols x 4 Rows
            if not dropped:
                for i in range(8):
                    col = i % 2; row = i // 2
                    sx = backpack_start_x + col*(slot_size + slot_gap_x)
                    sy = backpack_start_y + row*(slot_size + slot_gap_y)
                    if sx < mx < sx+slot_size and sy < my < sy+slot_size:
                        target = inv.backpack[i]
                        inv.backpack[i] = inv.drag_item
                        if target: return_source(target)
                        dropped = True; break
            
            # 3. Armor - Vertical 1x4 (Strict Type Check)
            if not dropped:
                for i in range(4):
                    col = 0; row = i
                    sx = armor_start_x + col*(slot_size + slot_gap_x)
                    sy = armor_start_y + row*(slot_size + slot_gap_y)
                    if sx < mx < sx+slot_size and sy < my < sy+slot_size:
                         # STRICT CHECK: No weapons in armor slots
                         if inv.drag_item.type == 'weapon':
                             break 
                             
                         target = inv.armor[i]
                         inv.armor[i] = inv.drag_item
                         if target: return_source(target)
                         dropped = True; break
            
            # Cancel
            if not dropped:
                return_source(inv.drag_item)
            
            inv.drag_item = None
