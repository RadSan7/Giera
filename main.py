import pygame
import sys

# Inicjalizacja Pygame
pygame.init()

# Konfiguracja ekranu
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Projekt AI - Giera")

# Kolory
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (50, 50, 50)
LIGHT_GRAY = (100, 100, 100)
GREEN = (0, 200, 0)
RED = (200, 0, 0)
HOVER_COLOR = (150, 150, 150)

# Czcionki
font = pygame.font.SysFont('Arial', 40)
small_font = pygame.font.SysFont('Arial', 20)

class Button:
    def __init__(self, text, x, y, width, height, color, hover_color, action=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.action = action

    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        if self.rect.collidepoint(mouse_pos):
            pygame.draw.rect(surface, self.hover_color, self.rect, border_radius=12)
        else:
            pygame.draw.rect(surface, self.color, self.rect, border_radius=12)

        text_surf = font.render(self.text, True, WHITE)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def check_click(self):
        mouse_pos = pygame.mouse.get_pos()
        if self.rect.collidepoint(mouse_pos):
            if self.action:
                self.action()

def start_new_game():
    print("Rozpoczynanie nowej gry...")
    # Tutaj w przyszłości będzie logika gry
    game_loop()

def quit_game():
    pygame.quit()
    sys.exit()

def game_loop():
    """Prosta pętla gry (placeholder)"""
    running = True
    while running:
        screen.fill(BLACK)
        
        text = font.render("Tu będzie Twoja gra!", True, WHITE)
        text_rect = text.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2))
        screen.blit(text, text_rect)
        
        back_text = small_font.render("Naciśnij ESC, aby wrócić", True, LIGHT_GRAY)
        back_rect = back_text.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2 + 50))
        screen.blit(back_text, back_rect)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_game()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
        
        pygame.display.flip()

def main_menu():
    # Tworzenie przycisków
    # Wyśrodkowanie przycisków
    button_width = 300
    button_height = 80
    center_x = (SCREEN_WIDTH - button_width) // 2
    
    start_btn = Button("Nowa Gra", center_x, 200, button_width, button_height, GREEN, (0, 255, 0), start_new_game)
    exit_btn = Button("Wyjście", center_x, 350, button_width, button_height, RED, (255, 0, 0), quit_game)
    
    buttons = [start_btn, exit_btn]

    while True:
        screen.fill(GRAY)
        
        # Tytuł
        title_surf = font.render("MENU GŁÓWNE", True, WHITE)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH/2, 100))
        screen.blit(title_surf, title_rect)

        # Rysowanie przycisków
        for btn in buttons:
            btn.draw(screen)

        # Obsługa zdarzeń
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_game()
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Lewy przycisk myszy
                    for btn in buttons:
                        btn.check_click()

        pygame.display.flip()

if __name__ == "__main__":
    main_menu()
