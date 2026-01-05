from panda3d.core import loadPrcFileData

# --- KONFIGURACJA DLA MACOS ---
# Wymuszamy Core Profile (GL 3.2+), jedyny "nowoczesny" tryb na Macu
loadPrcFileData('', 'gl-version 3 2')
loadPrcFileData('', 'gl-profile core')
loadPrcFileData('', 'gl-ignore-no-source #t')

from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController

# Inicjalizacja
app = Ursina(development_mode=False)

# --- CUSTOM SHADER 150 (MACOS FIX) ---
# Shader, który działa na macOS Core Profile (zamiast błędnego 130)
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
    // DEBUG: Wymuszamy jaskrawy czerwony kolor, żeby sprawdzić czy cokolwiek widać
    p3d_FragColor = vec4(1.0, 0.0, 0.0, 1.0);
}
''')

# Ustawiamy ten shader jako domyślny
Entity.default_shader = macos_shader

# Ustawienia okna
window.title = 'Antigravity 3D - Labirynt'
window.borderless = False
window.exit_button.visible = False
window.fps_counter.enabled = False
window.cog_button.enabled = False

# --- ŚWIAT GRY ---

# Podłoga
ground = Entity(
    model='plane',
    color=color.lime,
    collider='box',
    scale=(60, 1, 60),
    shader=macos_shader 
)

# Niebo
sky = Entity(
    model='sphere',
    scale=200,
    color=color.azure,
    double_sided=True,
    shader=macos_shader
)

# --- LABIRYNT ---
wall_height = 3
wall_color = color.gray

def create_wall(x, z, sx, sz):
    return Entity(
        model='cube',
        color=wall_color,
        position=(x, wall_height/2, z),
        scale=(sx, wall_height, sz),
        collider='box',
        shader=macos_shader
    )

# Zewnętrzne ściany
walls = [
    create_wall(0, 20, 40, 1),
    create_wall(0, -20, 40, 1),
    create_wall(20, 0, 1, 40),
    create_wall(-20, 0, 1, 40),
]

# Wewnętrzne ściany
inner_walls = [
    create_wall(-10, 10, 15, 1),
    create_wall(5, 10, 1, 10),
    create_wall(10, 5, 10, 1),
    create_wall(-5, 0, 1, 15),
    create_wall(0, -8, 12, 1),
    create_wall(-12, -5, 1, 12),
    create_wall(8, -5, 1, 10),
    create_wall(15, 0, 1, 8),
]
for w in inner_walls:
    w.color = color.orange

# Cel
goal = Entity(
    model='sphere',
    color=color.red,
    position=(15, 1, -15),
    scale=2,
    collider='sphere',
    shader=macos_shader
)

# Lewitujące kostki
cubes = []
for i in range(10):
    cube = Entity(
        model='cube',
        color=color.hsv(36 * i, 1, 1),
        position=(random.uniform(-15, 15), 2, random.uniform(-15, 15)),
        scale=0.8,
        collider='box',
        shader=macos_shader
    )
    cubes.append(cube)

# --- GRACZ ---
player = FirstPersonController()
player.position = (-15, 2, 15)
player.cursor.visible = False
player.gravity = 1

# Celownik (Quad 2D - UI shader zwykle działa ok, ale jakby co przypiszemy też nasz, choć może być problem z UV)
crosshair = Entity(parent=camera.ui, model='quad', color=color.white, scale=.012, rotation_z=45, shader=None) # UI often manages without shaders or specific ones

# Broń
gun = Entity(parent=camera, position=(.4, -.2, .5), scale=(.2, .15, .6), model='cube', color=color.dark_gray, shader=macos_shader)

held_entity = None

# --- LOGIKA ---
def update():
    global held_entity

    if held_keys['escape']:
        application.quit()
        
    if held_keys['g']:
        player.gravity = 0.05
    else:
        player.gravity = 1

    if held_entity:
        target_position = camera.world_position + camera.forward * 3
        held_entity.position = lerp(held_entity.position, target_position, time.dt * 10)

    if held_keys['left mouse']:
        if held_entity:
            held_entity = None
        else:
            hit_info = raycast(camera.world_position, camera.forward, distance=10)
            if hit_info.hit and hit_info.entity in cubes:
                held_entity = hit_info.entity

    if held_keys['right mouse'] and held_entity:
        held_entity = None
    
    if player.intersects(goal).hit:
        print("🎉 WYGRAŁEŚ! Dotarłeś do celu!")
        goal.color = color.green

if __name__ == '__main__':
    app.run()
