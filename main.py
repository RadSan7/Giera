from panda3d.core import loadPrcFileData

# --- KONFIGURACJA DLA MACOS ---
# Musimy używać Core Profile (GL 3.2+), aby mieć dostęp do nowszych funkcji,
# ALE musimy też dostarczyć shadery w wersji 150, bo domyślne 130 są odrzucane.
loadPrcFileData('', 'gl-version 3 2')
loadPrcFileData('', 'gl-profile core')
loadPrcFileData('', 'gl-ignore-no-source #t')

from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController

# Inicjalizacja silnika
app = Ursina()

# --- CUSTOM MACOS SHADER ---
# Ręcznie napisany shader w wersji 150 (kompatybilny z macOS Core Profile).
# Zastępuje on domyślne shadery, które powodują błąd "version 130 not supported".
macos_shader = Shader(language=Shader.GLSL, vertex='''
#version 150
uniform mat4 p3d_ModelViewProjectionMatrix;
in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
out vec2 texcoord;
void main() {
  gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
  texcoord = p3d_MultiTexCoord0;
}
''', fragment='''
#version 150
uniform vec4 p3d_ColorScale;
in vec2 texcoord;
out vec4 p3d_FragColor;
void main() {
  // Prosty kolor bez tekstur (unlit)
  p3d_FragColor = p3d_ColorScale;
}
''')

# Ustawiamy ten shader jako domyślny dla wszystkich obiektów
Entity.default_shader = macos_shader

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
