import bpy
import bmesh

classlist = []

# =============================================================================

def Items_Images(self, context):
    return [('0', '---', 'No Image')] + [
    (img.name, img.name, 'Use this image') for img in bpy.data.images
    ]

Items_RGBA = (
    ('R', 'R', 'Red'),
    ('G', 'G', 'Green'),
    ('B', 'B', 'Blue'),
    ('A', 'A', 'Alpha')
)

def ChannelSelect(self, i):
    if self.mutex:
        return
    self.mutex = True
    setattr(self, 'channel%d'%i, (True,True,True,True))
    self.mutex = False

# =============================================================================

class DMR_OT_ComposeImageValues(bpy.types.Operator):
    """Compose a value map image from existing images"""
    bl_idname = "dmr.compose_value_map_image"
    bl_label = "Compose Value Map Image from Images"
    
    ImageProp = lambda i: bpy.props.EnumProperty(name='Source', default=0, items=Items_Images,
        description='Image to sample values from')
    
    image : bpy.props.EnumProperty(name='Destination', default=0, items=Items_Images,
        description='Image to write to')
    
    channels : bpy.props.BoolVectorProperty(name='Target Channels',
        size=4, default=(True, True, True, True), subtype='COLOR')
    
    source0 : ImageProp(0)
    source1 : ImageProp(1)
    source2 : ImageProp(2)
    source3 : ImageProp(3)
    
    read0 : bpy.props.EnumProperty(name='Read Channel', items=Items_RGBA, default=0)
    read1 : bpy.props.EnumProperty(name='Read Channel', items=Items_RGBA, default=0)
    read2 : bpy.props.EnumProperty(name='Read Channel', items=Items_RGBA, default=0)
    read3 : bpy.props.EnumProperty(name='Read Channel', items=Items_RGBA, default=0)
    
    # ---------------------------------------------------------
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    # ---------------------------------------------------------
    
    def draw(self, context):
        layout = self.layout
        c = layout.column()
        c.prop(self, 'image')
        r = c.row()
        
        c = layout.column()
        c.label(text='Source Images')
        
        for i in range(0, 4):
            b = c.box()
            
            r = b.row()
            rr = r.row()
            rr.scale_x = 0.4
            rr.scale_y = 2.0
            #rr.label(text=("RGBA")[i])
            rr.prop(self, 'channels', index=i, text=("RGBA")[i], toggle=True)
            
            b = r.column(align=1)
            b.enabled = self.channels[i]
            
            r = b.row(align=1)
            r.prop(self, 'source%d'%i, text='')
            r = b.row()
            rr = r.row(align=1)
            rr.label(text="Read Channel:")
            rr = rr.row()
            rr.scale_x = 0.5
            rr.prop(self, 'read%d'%i, text='Read', expand=True, icon_only=False)
    
    # ---------------------------------------------------------
    
    def execute(self, context):
        blender_images = bpy.data.images
        range4 = range(0, 4)
        
        if self.image not in blender_images.keys():
            self.report({'ERROR', 'No image found with name "%s"' % self.image.name})
            return {'FINISHED'}
        
        image = blender_images[self.image]
        image.colorspace_settings.name = 'Linear'
        image.alpha_mode = 'STRAIGHT'
        
        channels = self.channels # Bool vector of enabled channels
        
        # List of images[4]
        src_images = [
            blender_images[getattr(self, 'source%d'%i)] if (getattr(self, 'source%d'%i) in blender_images.keys() and channels[i]) else image
            for i in range4
        ]
        
        # List of channels indices[4]
        readchannel = tuple([{'R':0, 'G':1, 'B':2, 'A':3}[getattr(self, 'read%d'%i)] if channels[i] else i for i in range4])
        
        pixels = image.pixels
        w, h = image.size
        n = w*h
        n4 = n*4
        
        print("channels: ", self.channels)
        print("read: ", readchannel)
        print("src_images: ", [x.name if x else "<None>" for x in src_images])
        
        sourcedata = tuple([tuple(src_images[i].pixels) for i in range4])
        
        print('> Writing...')
        
        # pixels = image[ writeindex ][ readindex ]
        image.pixels = tuple(
            sourcedata[ pi%4 ][ 4*(pi//4)+readchannel[pi%4] ]
            for pi in range(0, n4)
        )
        
        self.report({'INFO'}, "Composition Complete")
        
        return {'FINISHED'}
classlist.append(DMR_OT_ComposeImageValues)

# =============================================================================

class DMR_OT_NormalizeBWImage(bpy.types.Operator):
    """Normalize Image Values to 0-1 range"""
    bl_idname = "dmr.normalize_image"
    bl_label = "Normalize Black and White Image"
    
    image : bpy.props.EnumProperty(name='Destination', default=0, items=Items_Images,
        description='Image to write to')
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=240)
    
    def execute(self, context):
        if self.image not in bpy.data.images.keys():
            self.report({'ERROR', 'No image found with name "%s"' % self.image.name})
            return {'FINISHED'}
        
        image = bpy.data.images[self.image]
        pixels = tuple(image.pixels)
        values = tuple(pixels[i] for i in range(0, len(pixels), 4) if pixels[i] > 0.004)
        minvalue = min(values)
        maxvalue = max(values)
        multiplier = 1/(maxvalue-minvalue)
        
        image.pixels = tuple(
            ( (pixels[i]-minvalue)*multiplier )
            for i in range(0, len(pixels))
        )
        
        image.update()
        
        return {'FINISHED'}
classlist.append(DMR_OT_NormalizeBWImage)

# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
