import os

# DIMENSIONS
WIDTH, HEIGHT = 1200, 800
FOV = 70

# SETTINGS
MOUSE_SENS = 0.2
SPEED = 0.15
FOOTSTEP_COOLDOWN = 350
SHADOW_RES = 1024

# PATHS
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
TEX_DIR = os.path.join(ASSETS_DIR, "textures")
MDL_DIR = os.path.join(ASSETS_DIR, "models")
SFX_DIR = os.path.join(ASSETS_DIR, "sfx")

# COLORS
C_SKY = (0.05, 0.05, 0.15, 1.0) # Night Sky
C_AMBIENT = (0.2, 0.2, 0.25, 1.0) # Moonlight Ambient
