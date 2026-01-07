import pygame
from OpenGL.GL import *
from config import WIDTH, HEIGHT
from utils import draw_rect, draw_ui_text

class Menu:
    def __init__(self, font, big_font):
        self.font = font
        self.big_font = big_font
        self.state = 'main' # main, settings
        
        # Style Constants
        self.COLOR_BG = (0.05, 0.05, 0.08, 1)
        self.COLOR_BTN_NORMAL = (0.15, 0.15, 0.2, 0.9)
        self.COLOR_BTN_HOVER = (0.25, 0.25, 0.35, 1.0)
        self.COLOR_TEXT = (220, 220, 230)
        self.COLOR_ACCENT = (100, 200, 255)
        
        # Settings (Placeholder values, linked to main manually for now)
        self.settings = {
            'fov': {'val': 70, 'min': 50, 'max': 110, 'step': 5},
            'sens': {'val': 0.15, 'min': 0.05, 'max': 0.5, 'step': 0.01}
        }
        
    def draw_main_menu(self):
        self._setup_view()
        
        # Background Gradient simulation
        draw_rect(0, 0, WIDTH, HEIGHT, self.COLOR_BG)
        
        if self.state == 'main':
            self._draw_main_buttons()
        elif self.state == 'settings':
            self._draw_settings_menu()
            
    def _setup_view(self):
        glMatrixMode(GL_PROJECTION); glLoadIdentity()
        glOrtho(0, WIDTH, HEIGHT, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity()
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        glDisable(GL_FOG)
        glDisable(GL_CULL_FACE)
        glEnable(GL_BLEND)
        
    def _draw_main_buttons(self):
        # Title
        title = "GIERA"
        # Shadow
        draw_ui_text(self.big_font, title, WIDTH//2 - 80, 104, (0, 0, 0))
        draw_ui_text(self.big_font, title, WIDTH//2 - 82, 100, self.COLOR_ACCENT)
        
        mx, my = pygame.mouse.get_pos()
        
        buttons = [
            ('NOWA GRA', 'new_game'),
            ('USTAWIENIA', 'settings_view'),
            ('WYJSCIE', 'quit')
        ]
        
        btn_w, btn_h = 320, 60
        start_y = 300
        gap = 80
        
        for i, (text, action) in enumerate(buttons):
            bx = WIDTH//2 - btn_w//2
            by = start_y + i*gap
            hover = bx < mx < bx+btn_w and by < my < by+btn_h
            
            # Glow on hover
            if hover:
                draw_rect(bx-2, by-2, btn_w+4, btn_h+4, (0.3, 0.5, 0.8, 0.5))
            
            # Button BG
            col = self.COLOR_BTN_HOVER if hover else self.COLOR_BTN_NORMAL
            draw_rect(bx, by, btn_w, btn_h, col)
            
            # Text
            # Centering hack (approximate)
            tw = len(text) * 12 # Rough estimate
            draw_ui_text(self.font, text, bx + btn_w//2 - tw, by + 18, self.COLOR_TEXT)
            
        # Footer
        draw_ui_text(self.font, "v1.0 Refactored", WIDTH - 180, HEIGHT - 40, (80, 80, 80))

    def _draw_settings_menu(self):
        # Header
        draw_ui_text(self.big_font, "USTAWIENIA", WIDTH//2 - 120, 80, self.COLOR_TEXT)
        
        mx, my = pygame.mouse.get_pos()
        
        # Settings List
        start_y = 250
        gap = 70
        
        # FOV
        self._draw_setting_row("FOV (Pole Widzenia)", self.settings['fov']['val'], start_y, mx, my, 'fov')
        
        # SENS
        self._draw_setting_row("Czułość Myszy", f"{self.settings['sens']['val']:.2f}", start_y + gap, mx, my, 'sens')
        
        # Back Button
        btn_w, btn_h = 200, 50
        bx = WIDTH//2 - btn_w//2
        by = HEIGHT - 150
        hover = bx < mx < bx+btn_w and by < my < by+btn_h
        col = self.COLOR_BTN_HOVER if hover else self.COLOR_BTN_NORMAL
        draw_rect(bx, by, btn_w, btn_h, col)
        draw_ui_text(self.font, "POWRÓT", bx + 60, by + 15, self.COLOR_TEXT)

    def _draw_setting_row(self, label, value_display, y, mx, my, key):
        # Label
        draw_ui_text(self.font, label, WIDTH//2 - 250, y+10, self.COLOR_TEXT)
        
        # Controls area
        cx = WIDTH//2 + 50
        
        # - Button
        btn_size = 40
        b1_x = cx
        hover1 = b1_x < mx < b1_x+btn_size and y < my < y+btn_size
        col1 = self.COLOR_BTN_HOVER if hover1 else self.COLOR_BTN_NORMAL
        draw_rect(b1_x, y, btn_size, btn_size, col1)
        draw_ui_text(self.font, "-", b1_x+13, y+8, self.COLOR_TEXT)
        
        # Value
        draw_ui_text(self.font, str(value_display), cx + 60, y+10, self.COLOR_ACCENT)
        
        # + Button
        b2_x = cx + 120
        hover2 = b2_x < mx < b2_x+btn_size and y < my < y+btn_size
        col2 = self.COLOR_BTN_HOVER if hover2 else self.COLOR_BTN_NORMAL
        draw_rect(b2_x, y, btn_size, btn_size, col2)
        draw_ui_text(self.font, "+", b2_x+11, y+8, self.COLOR_TEXT)

    def handle_input(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = pygame.mouse.get_pos()
            
            if self.state == 'main':
                btn_w, btn_h = 320, 60
                start_y = 300
                gap = 80
                
                # Check Main Buttons
                buttons = ['new_game', 'settings_view', 'quit']
                for i, action in enumerate(buttons):
                    bx = WIDTH//2 - btn_w//2
                    by = start_y + i*gap
                    if bx < mx < bx+btn_w and by < my < by+btn_h:
                        if action == 'settings_view':
                            self.state = 'settings'
                            return None
                        return action
                        
            elif self.state == 'settings':
                # Back Button
                btn_w, btn_h = 200, 50
                bx = WIDTH//2 - btn_w//2
                by = HEIGHT - 150
                if bx < mx < bx+btn_w and by < my < by+btn_h:
                    self.state = 'main'
                    return 'save_settings' # Signal to apply changes
                
                # Settings Controls
                start_y = 250
                gap = 70
                
                # Helper to check +/- clicks
                def check_click(y, key):
                    cx = WIDTH//2 + 50
                    btn_size = 40
                    # Minus
                    if cx < mx < cx+btn_size and y < my < y+btn_size:
                        self.update_setting(key, -1)
                    # Plus
                    if cx+120 < mx < cx+120+btn_size and y < my < y+btn_size:
                        self.update_setting(key, 1)
                        
                check_click(start_y, 'fov')
                check_click(start_y + gap, 'sens')
                
        return None

    def update_setting(self, key, direction):
        s = self.settings[key]
        s['val'] += s['step'] * direction
        s['val'] = max(s['min'], min(s['max'], s['val']))
        # Round for float drift
        if isinstance(s['val'], float):
             s['val'] = round(s['val'], 2)

    def draw_pause_menu(self):
        # Overlay
        draw_rect(0, 0, WIDTH, HEIGHT, (0, 0, 0, 0.8))
        
        cx, cy = WIDTH//2, HEIGHT//2
        pw, ph = 400, 300
        px, py = cx - pw//2, cy - ph//2
        
        # Modern Panel Gradient simulation
        draw_rect(px, py, pw, ph, self.COLOR_BG) 
        # Border glow
        draw_rect(px-2, py-2, pw+4, ph+4, (0.2, 0.2, 0.3, 0.3))
        
        # Header
        draw_rect(px, py, pw, 60, (0.1, 0.1, 0.15, 1)) 
        draw_ui_text(self.big_font, "PAUZA", px + 120, py + 15, self.COLOR_TEXT)
        
        # Content
        col_text = (180, 180, 200)
        start_y = py + 100
        gap = 50
        
        draw_ui_text(self.font, "Stan Gry Zatrzymany", px + 90, start_y, col_text)
        
        # Instructions / Buttons (Visual only for now for Pause)
        draw_ui_text(self.font, "[ESC] Wznowienie", px + 100, start_y + gap*2, self.COLOR_ACCENT)
        draw_ui_text(self.font, "[Q] Wyjscie do Menu", px + 95, start_y + gap*3, (200, 100, 100))
