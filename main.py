from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController

# Inicjalizacja
app = Ursina(development_mode=False)

# Ustawienia okna
window.title = 'Antigravity 3D - Labirynt'
window.borderless = False
window.exit_button.visible = False

# --- ŚWIAT GRY ---

# Podłoga
ground = Entity(
    model='plane',
    color=color.lime,
    collider='box',
    scale=(60, 1, 60),
)

# Niebo
sky = Entity(
    model='sphere',
    scale=200,
    color=color.azure,
    double_sided=True,
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
    )

# Zewnętrzne ściany
walls = [
    create_wall(0, 20, 40, 1),    # Północ
    create_wall(0, -20, 40, 1),   # Południe
    create_wall(20, 0, 1, 40),    # Wschód
    create_wall(-20, 0, 1, 40),   # Zachód
]

# Wewnętrzne ściany labiryntu
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

# Kolorowe ściany (pomarańczowe) - dodatkowe przeszkody
for w in inner_walls:
    w.color = color.orange

# Cel - czerwona kula
goal = Entity(
    model='sphere',
    color=color.red,
    position=(15, 1, -15),
    scale=2,
    collider='sphere',
)

# Lewitujące kostki (do chwytania)
cubes = []
for i in range(10):
    cube = Entity(
        model='cube',
        color=color.hsv(36 * i, 1, 1),  # Kolorowe
        position=(random.uniform(-15, 15), 2, random.uniform(-15, 15)),
        scale=0.8,
        collider='box',
    )
    cubes.append(cube)

# --- GRACZ ---
player = FirstPersonController()
player.position = (-15, 2, 15)  # Start w rogu
player.cursor.visible = False
player.gravity = 1

# Celownik
crosshair = Entity(parent=camera.ui, model='quad', color=color.white, scale=.012, rotation_z=45)

# Broń
gun = Entity(parent=camera, position=(.4, -.2, .5), scale=(.2, .15, .6), model='cube', color=color.dark_gray)

held_entity = None

# --- LOGIKA ---
def update():
    global held_entity

    if held_keys['escape']:
        application.quit()
        
    # Anty-grawitacja
    if held_keys['g']:
        player.gravity = 0.05
    else:
        player.gravity = 1

    # Trzymanie obiektu
    if held_entity:
        target_position = camera.world_position + camera.forward * 3
        held_entity.position = lerp(held_entity.position, target_position, time.dt * 10)

    # Chwytanie / Upuszczanie
    if held_keys['left mouse']:
        if held_entity:
            held_entity = None
        else:
            hit_info = raycast(camera.world_position, camera.forward, distance=10)
            if hit_info.hit and hit_info.entity in cubes:
                held_entity = hit_info.entity

    if held_keys['right mouse'] and held_entity:
        held_entity = None
    
    # Sprawdzenie celu
    if player.intersects(goal).hit:
        print("🎉 WYGRAŁEŚ! Dotarłeś do celu!")
        goal.color = color.green


if __name__ == '__main__':
    app.run()
