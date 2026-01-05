from panda3d.core import loadPrcFileData

# --- KONFIGURACJA DLA MACOS ---
# Próbujemy nowszego OpenGL 4.1 (M1/M2 to obsługują)
loadPrcFileData('', 'gl-version 4 1')
loadPrcFileData('', 'gl-profile core')
# Ukrywamy błędy "missing version", bo Core Profile jest czasem nadgorliwy
loadPrcFileData('', 'gl-ignore-no-source #t')

from ursina import *
from ursina.shaders import unlit_shader # Importujemy prosty shader
from ursina.prefabs.first_person_controller import FirstPersonController

# Inicjalizacja silnika
app = Ursina()

# --- FIX SHADERÓW ---
# Zamiast 'None' (co powoduje automagiczne generowanie wadliwych shaderów),
# używamy oficjalnego 'unlit_shader', który jest bardzo prosty.
Entity.default_shader = unlit_shader

# Ustawienia okna
window.title = 'Antigravity 3D Game'
window.borderless = False
window.exit_button.visible = False

# --- ŚWIAT GRY ---

# Podłoga
ground = Entity(
    model='plane',
    color=color.green,
    collider='box',
    scale=(100, 1, 100),
    position=(0, 0, 0),
    shader=None 
)

# Niebo
sky = Entity(
    model='sphere', 
    scale=500, 
    color=color.cyan, 
    double_sided=True, 
    shader=None
)

# Lewitujące kostki
for i in range(8):
    Entity(
        model='cube',
        color=color.hsv(30 * i, 1, 0.8),
        position=(random.randint(-10, 10), random.randint(2, 6), random.randint(-10, 10)),
        scale=(1, 1, 1),
        rotation=(random.randint(0,360), random.randint(0,360), 0),
        collider='box',
        shader=None
    )

# --- GRACZ ---
player = FirstPersonController()
player.cursor.visible = True
player.gravity = 1

# --- LOGIKA ---
def update():
    if held_keys['escape']:
        application.quit()
        
    if held_keys['g']:
        player.gravity = 0.1
    else:
        player.gravity = 1

if __name__ == '__main__':
    app.run()
