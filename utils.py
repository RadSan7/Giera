import os
import pygame
from OpenGL.GL import *
from OpenGL.GLU import *
from config import TEX_DIR, MDL_DIR, SFX_DIR

texture_ids = {}
display_lists = {} # Shared display lists (OBJ)
sfx_sounds = {}

def load_sfx(name, filename):
    path = os.path.join(SFX_DIR, filename)
    if os.path.exists(path):
        try:
            sfx_sounds[name] = pygame.mixer.Sound(path)
            print(f"Loaded SFX: {name}")
        except Exception as e:
            print(f"SFX Error loading {name}: {e}")
    else:
        print(f"SFX not found: {path}")

def load_texture(name, filename, aniso_level=4.0):
    path = os.path.join(TEX_DIR, filename)
    if not os.path.exists(path):
        print(f"Warning: Texture {path} not found.")
        return 0
    try:
        surf = pygame.image.load(path).convert_alpha()
        data = pygame.image.tostring(surf, "RGBA", False)
        w, h = surf.get_size()
        tid = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tid)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        glGenerateMipmap(GL_TEXTURE_2D)
        
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        
        try:
             if glInitTextureFilterAnisotropicEXT():
                max_aniso = glGetFloatv(GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT)
                amount = min(aniso_level, max_aniso)
                glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAX_ANISOTROPY_EXT, amount)
        except: pass
            
        texture_ids[name] = tid
        return tid
    except Exception as e:
        print(f"Error loading texture {name}: {e}")
        return 0

def load_obj_display_list(filename, tex_key, material_textures=None):
    """
    Load OBJ model with support for multiple materials.
    material_textures: dict mapping material names to texture keys, e.g. {'Trunk_bark': 'tree_bark', 'Leaves': 'tree_branch'}
    """
    path = os.path.join(MDL_DIR, filename)
    if not os.path.exists(path): return None
    
    vertices, texcoords, normals = [], [], []
    # Store faces per material
    material_faces = {}  # material_name -> list of faces
    current_material = None
    
    try:
        for line in open(path, "r", encoding='utf-8', errors='ignore'):
            if line.startswith('#'): continue
            vals = line.split()
            if not vals: continue
            if vals[0] == 'v': vertices.append(list(map(float, vals[1:4])))
            elif vals[0] == 'vt': texcoords.append(list(map(float, vals[1:3])))
            elif vals[0] == 'vn': normals.append(list(map(float, vals[1:4])))
            elif vals[0] == 'usemtl':
                current_material = vals[1] if len(vals) > 1 else 'default'
                if current_material not in material_faces:
                    material_faces[current_material] = []
            elif vals[0] == 'f':
                face = []
                for v in vals[1:]:
                    w = v.split('/')
                    idx_v = int(w[0])-1
                    idx_vt = int(w[1])-1 if len(w)>1 and w[1] else -1
                    idx_vn = int(w[2])-1 if len(w)>2 else -1
                    face.append((idx_v, idx_vt, idx_vn))
                mat_key = current_material if current_material else 'default'
                if mat_key not in material_faces:
                    material_faces[mat_key] = []
                material_faces[mat_key].append(face)
            
        lid = glGenLists(1)
        glNewList(lid, GL_COMPILE)
        
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_ALPHA_TEST)
        glAlphaFunc(GL_GREATER, 0.4)
        
        # Draw each material group with its texture
        for mat_name, faces in material_faces.items():
            # Determine texture for this material
            if material_textures and mat_name in material_textures:
                tex_id = texture_ids.get(material_textures[mat_name], 0)
            else:
                tex_id = texture_ids.get(tex_key, 0)
            
            glBindTexture(GL_TEXTURE_2D, tex_id)
            
            # Set color based on material (brown for bark)
            if 'bark' in mat_name.lower() or 'trunk' in mat_name.lower():
                glColor3f(0.6, 0.4, 0.25)  # Brown for trunk
            else:
                glColor3f(1, 1, 1)  # White for leaves (use texture color)
            
            glBegin(GL_TRIANGLES)
            for face in faces:
                for i in range(1, len(face)-1):
                    v_indices = [face[0], face[i], face[i+1]]
                    for idx in v_indices:
                        v, vt, vn = idx
                        if vn >= 0 and vn < len(normals): glNormal3fv(normals[vn])
                        if vt >= 0 and vt < len(texcoords): glTexCoord2fv(texcoords[vt])
                        glVertex3fv(vertices[v])
            glEnd()
        
        glColor3f(1, 1, 1)  # Reset color
        glDisable(GL_ALPHA_TEST)
        glDisable(GL_TEXTURE_2D)
        glEndList()
        return lid
    except Exception as e:
        print(f"OBJ Error {filename}: {e}")
        return None

# UI HELPERS
def draw_rect(x, y, w, h, color):
    # Enable blending for transparency
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glDisable(GL_TEXTURE_2D)
    glDisable(GL_LIGHTING)
    glColor4f(*color)
    glBegin(GL_QUADS)
    glVertex2f(x, y); glVertex2f(x+w, y)
    glVertex2f(x+w, y+h); glVertex2f(x, y+h)
    glEnd()

def draw_textured_rect(x, y, w, h, tid, color=(1,1,1,1)):
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, tid)
    glColor4f(*color)
    glBegin(GL_QUADS)
    glTexCoord2f(0, 0); glVertex2f(x, y)
    glTexCoord2f(1, 0); glVertex2f(x+w, y)
    glTexCoord2f(1, 1); glVertex2f(x+w, y+h)
    glTexCoord2f(0, 1); glVertex2f(x, y+h)
    glEnd()
    glDisable(GL_TEXTURE_2D)

def draw_ui_text(font, text, x, y, color=(255, 255, 255)):
    surf = font.render(text, True, color)
    data = pygame.image.tostring(surf, "RGBA", False)
    w, h = surf.get_size()
    
    glEnable(GL_TEXTURE_2D)
    tid = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tid)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
    
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor3f(1,1,1)
    
    glBegin(GL_QUADS)
    glTexCoord2f(0, 0); glVertex2f(x, y)
    glTexCoord2f(1, 0); glVertex2f(x+w, y)
    glTexCoord2f(1, 1); glVertex2f(x+w, y+h)
    glTexCoord2f(0, 1); glVertex2f(x, y+h)
    glEnd()
    
    glDeleteTextures([tid])
    glDisable(GL_TEXTURE_2D)
