import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

def draw_cube():
    # Rysowanie kostki - każda ściana w innym kolorze
    glBegin(GL_QUADS)
    
    # Kolory (RGB)
    colors = [
        (1, 0, 0), (0, 1, 0), (0, 0, 1),
        (1, 1, 0), (1, 0, 1), (0, 1, 1)
    ]
    
    # Wierzchołki kostki
    vertices = [
        (1, -1, -1), (1, 1, -1), (-1, 1, -1), (-1, -1, -1),  # Tył
        (1, -1, 1), (1, 1, 1), (-1, 1, 1), (-1, -1, 1),      # Przód
        (1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1),      # Prawo
        (-1, -1, -1), (-1, 1, -1), (-1, 1, 1), (-1, -1, 1),  # Lewo
        (1, 1, 1), (1, 1, -1), (-1, 1, -1), (-1, 1, 1),      # Góra
        (1, -1, 1), (1, -1, -1), (-1, -1, -1), (-1, -1, 1)   # Dół
    ]
    
    # Indeksy ścian (które wierzchołki tworzą ścianę)
    surfaces = [
        (0, 1, 2, 3), # Tył
        (4, 5, 6, 7), # Przód
        (8, 9, 10, 11), # Prawo
        (12, 13, 14, 15), # Lewo
        (16, 17, 18, 19), # Góra
        (20, 21, 22, 23)  # Dół
    ]

    for i, surface in enumerate(surfaces):
        glColor3fv(colors[i]) # Ustaw kolor
        for vertex in surface:
            glVertex3fv(vertices[vertex]) # Narysuj wierzchołek
            
    glEnd()

def main():
    pygame.init()
    display = (800, 600)
    # Konfiguracja okna pod OpenGL
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Test OpenGL na Macu")

    # Ustawienie perspektywy (Kamera)
    gluPerspective(45, (display[0]/display[1]), 0.1, 50.0)
    # Cofnięcie kamery o 5 jednostek
    glTranslatef(0.0, 0.0, -5)

    rot_x = 0
    rot_y = 0

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    pygame.quit()
                    quit()

        # Obsługa obrotu strzałkami
        keys = pygame.key.get_pressed()
        if keys[K_LEFT]: rot_y -= 1
        if keys[K_RIGHT]: rot_y += 1
        if keys[K_UP]: rot_x -= 1
        if keys[K_DOWN]: rot_x += 1

        # Renderowanie
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT) # Wyczyść ekran
        
        glPushMatrix() # Zapamiętaj pozycję
        glRotatef(rot_x, 1, 0, 0) # Obróć X
        glRotatef(rot_y, 0, 1, 0) # Obróć Y
        
        draw_cube() # Narysuj kostkę
        
        glPopMatrix() # Przywróć pozycję

        pygame.display.flip() # Wyświetl klatkę
        pygame.time.wait(10) # Czekaj 10ms (ok. 60 FPS)

if __name__ == "__main__":
    main()
