"""
Sky rendering module - Moon, stars, and night atmosphere
"""
import math
from OpenGL.GL import *
from OpenGL.GLU import *

# Moon configuration
MOON_DIRECTION = (0.5, 0.8, 0.3)  # Normalized direction TO the moon
MOON_DISTANCE = 150  # How far to render the moon billboard
MOON_SIZE = 15  # Visual size of moon

# Colors
MOON_COLOR = (0.9, 0.92, 1.0)  # Slightly blue-white
MOON_GLOW = (0.4, 0.45, 0.6, 0.3)  # Glow halo
NIGHT_SKY = (0.01, 0.01, 0.04, 1.0)  # Very dark blue
MOONLIGHT_DIFFUSE = (0.25, 0.28, 0.4, 1.0)  # Pale blue moonlight
MOONLIGHT_AMBIENT = (0.02, 0.02, 0.05, 1.0)  # Very dark ambient

def normalize(v):
    length = math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
    if length == 0: return (0, 1, 0)
    return (v[0]/length, v[1]/length, v[2]/length)

def get_moon_light_position():
    """Returns light position for OpenGL (w=0 for directional)"""
    d = normalize(MOON_DIRECTION)
    return (d[0]*100, d[1]*100, d[2]*100, 0.0)  # w=0 = directional light

def setup_moonlight():
    """Configure GL_LIGHT0 as moonlight"""
    glEnable(GL_LIGHT0)
    
    # Directional light from moon
    glLightfv(GL_LIGHT0, GL_POSITION, get_moon_light_position())
    glLightfv(GL_LIGHT0, GL_DIFFUSE, MOONLIGHT_DIFFUSE)
    glLightfv(GL_LIGHT0, GL_AMBIENT, MOONLIGHT_AMBIENT)
    glLightfv(GL_LIGHT0, GL_SPECULAR, (0.3, 0.3, 0.4, 1.0))
    
    # Global ambient (very dark night)
    glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (0.03, 0.03, 0.05, 1.0))

def draw_moon(camera_pos):
    """Draw the moon as a billboard facing the camera"""
    d = normalize(MOON_DIRECTION)
    
    # Moon world position (far from camera but in consistent direction)
    moon_x = camera_pos[0] + d[0] * MOON_DISTANCE
    moon_y = camera_pos[1] + d[1] * MOON_DISTANCE
    moon_z = camera_pos[2] + d[2] * MOON_DISTANCE
    
    glPushMatrix()
    glTranslatef(moon_x, moon_y, moon_z)
    
    # Billboard - face camera (get current modelview and extract rotation)
    modelview = glGetFloatv(GL_MODELVIEW_MATRIX)
    
    # Reset rotation part of matrix (keep translation)
    for i in range(3):
        for j in range(3):
            if i == j:
                modelview[i][j] = 1.0
            else:
                modelview[i][j] = 0.0
    
    # Disable lighting for emissive moon
    glDisable(GL_LIGHTING)
    glDisable(GL_FOG)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE)  # Additive for glow
    
    # Draw glow halo (larger, transparent)
    glColor4f(*MOON_GLOW)
    quad = gluNewQuadric()
    gluDisk(quad, 0, MOON_SIZE * 2, 32, 1)
    
    # Draw moon disc (solid)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor3f(*MOON_COLOR)
    gluDisk(quad, 0, MOON_SIZE, 32, 1)
    
    # Restore state
    glDisable(GL_BLEND)
    glEnable(GL_FOG)
    glEnable(GL_LIGHTING)
    
    glPopMatrix()

def draw_stars(camera_pos, seed=42):
    """Draw simple star points"""
    import random
    random.seed(seed)
    
    glDisable(GL_LIGHTING)
    glDisable(GL_FOG)
    glDisable(GL_DEPTH_TEST)
    
    glPointSize(2.0)
    glBegin(GL_POINTS)
    
    for _ in range(200):
        # Random direction on hemisphere
        theta = random.uniform(0, 2 * math.pi)
        phi = random.uniform(0, math.pi / 2)  # Upper hemisphere
        
        r = 180  # Far distance
        x = camera_pos[0] + r * math.sin(phi) * math.cos(theta)
        y = camera_pos[1] + r * math.cos(phi) + 20  # Above horizon
        z = camera_pos[2] + r * math.sin(phi) * math.sin(theta)
        
        brightness = random.uniform(0.3, 1.0)
        glColor3f(brightness, brightness, brightness * 1.1)
        glVertex3f(x, y, z)
    
    glEnd()
    
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_FOG)
    glEnable(GL_LIGHTING)

def get_night_fog_color():
    """Returns fog color matching night sky"""
    return NIGHT_SKY

def get_night_sky_color():
    """Returns clear color for night sky"""
    return NIGHT_SKY
