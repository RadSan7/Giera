import math
from OpenGL.GL import *

def get_height(x, z):
    # Procedural terrain
    val = math.sin(x * 0.1) * 1.5 + math.cos(z * 0.1) * 1.5
    val += math.sin(x*0.3 + z*0.2) * 0.5
    dist = math.sqrt(x*x + z*z)
    # Flatten near spawn (0,0)
    if dist < 8: val *= (dist/8.0)
    return val
    
def shadow_projection(light_pos, ground_y=0.1):
    lx, ly, lz, lw = light_pos
    mat = [0]*16
    
    # Simple Planar Projection onto Y=ground_y
    # This matrix flattens geometry onto the plane
    mat[0] = ly; mat[4] = -lx; mat[8] = 0;  mat[12] = 0
    mat[1] = 0;  mat[5] = 0;   mat[9] = 0;  mat[13] = 0 # Flatten Y
    mat[2] = 0;  mat[6] = -lz; mat[10]= ly; mat[14]= 0
    mat[3] = 0;  mat[7] = -1;  mat[11]= 0;  mat[15]= ly
    
    glPushMatrix()
    glTranslatef(0, ground_y+0.05, 0) # Raise slightly to avoid z-fight
    glMultMatrixf(mat)
    
ground_list = None

def draw_ground(texture_ids):
    global ground_list
    
    # Enforce opaque rendering
    glDisable(GL_BLEND)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_TEXTURE_2D)
    glEnable(GL_LIGHTING)
    
    glBindTexture(GL_TEXTURE_2D, texture_ids.get('grass', 0))
    glColor3f(1, 1, 1) # Pure white for texture
    
    # Configure texture wrapping repeat
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    
    # Generate display list if not exists
    if ground_list is None:
        ground_list = glGenLists(1)
        glNewList(ground_list, GL_COMPILE)
        
        step = 2.0
        size = 60
        
        glBegin(GL_QUADS)
        glNormal3f(0, 1, 0)
        
        for x in range(-size, size, int(step)):
            for z in range(-size, size, int(step)):
                # Calculate vertices
                x1, z1 = x, z
                x2, z2 = x + step, z + step
                
                h_11 = get_height(x1, z1)
                h_12 = get_height(x1, z2)
                h_22 = get_height(x2, z2)
                h_21 = get_height(x2, z1)
                
                # Tex Coords (scaling allows repeat)
                s = 5.0 
                
                glTexCoord2f(x1/s, z1/s); glVertex3f(x1, h_11, z1)
                glTexCoord2f(x1/s, z2/s); glVertex3f(x1, h_12, z2)
                glTexCoord2f(x2/s, z2/s); glVertex3f(x2, h_22, z2)
                glTexCoord2f(x2/s, z1/s); glVertex3f(x2, h_21, z1)
                
        glEnd()
        glEndList()
        
    # Draw the list
    glCallList(ground_list)
    glDisable(GL_TEXTURE_2D)
