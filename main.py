from panda3d.core import loadPrcFileData
# Konfiguracja dla macOS - wymuszenie OpenGL 3.2 Core Profile
loadPrcFileData('', 'gl-version 3 2')

from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController

# Inicjalizacja silnika
app = Ursina()

# Ustawienia okna
window.title = 'Antigravity 3D Game'
window.borderless = False
window.fullscreen = False
window.exit_button.visible = False
window.fps_counter.enabled = True

# --- ŚWIAT GRY ---

# Podłoga
ground = Entity(
    model='plane',
    color=color.green,
    collider='box',
    scale=(100, 1, 100),
    position=(0, 0, 0)
)

# Niebo
Sky()

# Jakieś lewitujące kostki (klimat Antigravity)
for i in range(8):
    Entity(
        model='cube',
        color=color.hsv(30 * i, 1, 0.8),
        position=(random.randint(-10, 10), random.randint(2, 6), random.randint(-10, 10)),
        scale=(1, 1, 1),
        rotation=(random.randint(0,360), random.randint(0,360), 0),
        collider='box'
    )

# --- GRACZ ---
player = FirstPersonController()
# Dostosowanie gracza
player.cursor.visible = True
player.gravity = 1 # Domyślna grawitacja (można zmieniać!)

# --- LOGIKA ---
def update():
    # Przykład interakcji: Wyjście ESC
    if held_keys['escape']:
        application.quit()
        
    # Przykład "anty-grawitacji" po wciśnięciu Spacji (latanie)
    if held_keys['g']:
        player.gravity = 0.1
        print("Anty-grawitacja ON")
    else:
        player.gravity = 1

# Uruchomienie
app.run()
