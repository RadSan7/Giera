class Mushroom:
    def __init__(self, x, z):
        self.x, self.y, self.z = x, get_height(x, z), z
        # Randomize size
        self.scale = random.uniform(0.6, 1.2)
        
    def update(self, df):
        pass # Static
        
    def draw(self, shadow_pass=False):
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        glScalef(self.scale, self.scale, self.scale)
        
        quad = gluNewQuadric(); gluQuadricTexture(quad, GL_TRUE)
        
        if shadow_pass:
             glColor4f(0, 0, 0, 0.4)
             glDisable(GL_TEXTURE_2D)
        else:
             glColor3f(1,1,1)
             glEnable(GL_TEXTURE_2D)
             
        # Stem
        if not shadow_pass: glBindTexture(GL_TEXTURE_2D, texture_ids.get('mushroom_stem', 0))
        glPushMatrix()
        glRotatef(-90, 1, 0, 0)
        gluCylinder(quad, 0.1, 0.15, 0.4, 8, 2)
        glPopMatrix()
        
        # Cap
        if not shadow_pass: glBindTexture(GL_TEXTURE_2D, texture_ids.get('mushroom_cap', 0))
        glPushMatrix()
        glTranslatef(0, 0.4, 0)
        glRotatef(-90, 1, 0, 0)
        # Disk bottom
        gluDisk(quad, 0.1, 0.4, 10, 2)
        # Top
        glTranslatef(0, 0, 0) 
        # Half sphere or Cone
        # Let's do a squashed sphere
        glScalef(1, 1, 0.6)
        gluSphere(quad, 0.4, 10, 10)
        glPopMatrix()
        
        if not shadow_pass: glDisable(GL_TEXTURE_2D)
        glPopMatrix()

class Rock:
    def __init__(self, x, z):
        self.x, self.y, self.z = x, get_height(x, z), z
        self.scale = random.uniform(0.8, 1.5)
        self.rot = random.uniform(0, 360)
        # Generate random distortion for rock shape
        self.shape_seed = random.randint(0, 100)
        
    def update(self, df):
        pass
        
    def draw(self, shadow_pass=False):
        glPushMatrix()
        glTranslatef(self.x, self.y + 0.2*self.scale, self.z) # Sink slightly
        glRotatef(self.rot, 0, 1, 0)
        glScalef(self.scale, self.scale*0.7, self.scale)
        
        quad = gluNewQuadric(); gluQuadricTexture(quad, GL_TRUE)
        
        if shadow_pass:
             glColor4f(0, 0, 0, 0.4)
             glDisable(GL_TEXTURE_2D)
        else:
             # Darker grey
             glColor3f(0.6, 0.6, 0.65)
             glEnable(GL_TEXTURE_2D)
             glBindTexture(GL_TEXTURE_2D, texture_ids.get('rock_wall', 0))
             
        # Main body
        gluSphere(quad, 0.5, 8, 8)
        
        # Detail lumps
        random.seed(self.shape_seed)
        for i in range(3):
            glPushMatrix()
            rx, ry, rz = random.uniform(-0.3, 0.3), random.uniform(0, 0.3), random.uniform(-0.3, 0.3)
            glTranslatef(rx, ry, rz)
            s = random.uniform(0.2, 0.4)
            glScalef(s, s, s)
            gluSphere(quad, 0.5, 6, 6)
            glPopMatrix()
            
        if not shadow_pass: glDisable(GL_TEXTURE_2D)
        glPopMatrix()
