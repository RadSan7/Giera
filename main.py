from panda3d.core import loadPrcFileData

# --- KONFIGURACJA DLA MACOS ---
# macOS obsługuje max OpenGL 4.1, więc wymuszamy tę wersję
loadPrcFileData('', 'gl-version 4 1')

from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import ursina.shader as shader_module

# --- NADPISUJEMY DOMYŚLNE SHADERY URSINY ---
# Ursina używa GLSL 430, ale macOS obsługuje max GLSL 410.
# Dlatego musimy nadpisać te wartości PRZED utworzeniem jakichkolwiek obiektów.
shader_module.default_vertex_shader = '''
#version 410
uniform mat4 p3d_ModelViewProjectionMatrix;
in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
out vec2 uv;
void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    uv = p3d_MultiTexCoord0;
}
'''

shader_module.default_fragment_shader = '''
#version 410
uniform sampler2D tex;
uniform vec4 p3d_ColorScale;
in vec2 uv;
out vec4 color;
void main() {
    color = p3d_ColorScale;
}
'''

# Inicjalizacja silnika
app = Ursina()

# Wyłączamy domyślne shadery na Entity, żeby używało fixed-function lub naszych nadpisanych
Entity.default_shader = None

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
)

# Niebo
sky = Entity(
    model='sphere', 
    scale=500, 
    color=color.cyan, 
    double_sided=True, 
)

# Lewitujące kostki
cubes = []
for i in range(8):
    cube = Entity(
        model='cube',
        color=color.hsv(30 * i, 1, 0.8),
        position=(random.randint(-10, 10), random.randint(2, 6), random.randint(-10, 10)),
        scale=(1, 1, 1),
        rotation=(random.randint(0,360), random.randint(0,360), 0),
        collider='box',
    )
    cubes.append(cube)

# --- GRACZ ---
player = FirstPersonController()
player.cursor.visible = False
player.gravity = 1

# Celownik
crosshair = Entity(parent=camera.ui, model='quad', color=color.red, scale=.015, rotation_z=45)

# Broń
gun = Entity(parent=camera, position=(.5, -.25, .5), scale=(.3, .2, 1), model='cube', color=color.gray)

# Zmienna do trzymania obiektu
held_entity = None

# --- LOGIKA ---
def update():
    global held_entity

    if held_keys['escape']:
        application.quit()
        
    if held_keys['g']:
        player.gravity = 0.1
    else:
        player.gravity = 1

    # Trzymanie obiektu
    if held_entity:
        target_position = camera.world_position + camera.forward * 3
        held_entity.position = lerp(held_entity.position, target_position, time.dt * 10)
        held_entity.rotation = lerp(held_entity.rotation, camera.rotation, time.dt * 5)

    # Chwytanie / Upuszczanie
    if held_keys['left mouse']:
        if held_entity:
            held_entity = None
        else:
            hit_info = raycast(camera.world_position, camera.forward, distance=10)
            if hit_info.hit:
                if hit_info.entity != ground:
                    held_entity = hit_info.entity

    if held_keys['right mouse'] and held_entity:
        held_entity = None


if __name__ == '__main__':
    app.run()
