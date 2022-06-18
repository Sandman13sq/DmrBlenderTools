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

class DMR_OT_CombineImageValues(bpy.types.Operator):
    """Compose a value map image from existing images"""
    bl_idname = "dmr.compose_value_map_image"
    bl_label = "Compose Value Map Image from Images"
    
    ImageProp = lambda i: bpy.props.EnumProperty(name='Source', default=0, items=Items_Images,
        description='Image to sample values from')
    
    image : bpy.props.EnumProperty(name='Destination', default=0, items=Items_Images,
        description='Image to write to')
    
    channels : bpy.props.BoolVectorProperty(name='Target Channels',
        size=4, default=(True, True, True, True), subtype='COLOR')
    
    source_image_0 : ImageProp(0)
    source_image_1 : ImageProp(1)
    source_image_2 : ImageProp(2)
    source_image_3 : ImageProp(3)
    
    source_read_channel_0 : bpy.props.EnumProperty(name='Read Channel', items=Items_RGBA, default=0)
    source_read_channel_1 : bpy.props.EnumProperty(name='Read Channel', items=Items_RGBA, default=0)
    source_read_channel_2 : bpy.props.EnumProperty(name='Read Channel', items=Items_RGBA, default=0)
    source_read_channel_3 : bpy.props.EnumProperty(name='Read Channel', items=Items_RGBA, default=0)
    
    source_write_channel_0 : bpy.props.EnumProperty(name='Write Channel', items=Items_RGBA, default=0)
    source_write_channel_1 : bpy.props.EnumProperty(name='Write Channel', items=Items_RGBA, default=1)
    source_write_channel_2 : bpy.props.EnumProperty(name='Write Channel', items=Items_RGBA, default=2)
    source_write_channel_3 : bpy.props.EnumProperty(name='Write Channel', items=Items_RGBA, default=3)
    
    # ---------------------------------------------------------
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=240)
    
    # ---------------------------------------------------------
    
    def draw(self, context):
        layout = self.layout
        c = layout.column()
        c.prop(self, 'image')
        r = c.row()
        r.prop(self, 'channels', text='Target Channels', expand=True)
        
        c = layout.column()
        c.label(text='Source Images')
        
        for i in range(0, 4):
            b = c.box().column(align=1)
            b.enabled = self.channels[i]
            r = b.row(align=1)
            r.prop(self, 'source_image_%d'%i, text='')
            r = b.row()
            rr = r.row(align=1)
            rr.label(text='Read')
            rr.prop(self, 'source_read_channel_%d'%i, text='Read', expand=True, icon_only=False)
            rr = r.row(align=1)
            rr.label(text='Write')
            rr.prop(self, 'source_write_channel_%d'%i, text='Write', expand=True, icon_only=False)
    
    # ---------------------------------------------------------
    
    def execute(self, context):
        blender_images = bpy.data.images
        range4 = range(0, 4)
        
        if self.image not in blender_images.keys():
            self.report({'ERROR', 'No image found with name "%s"' % self.image.name})
            return {'FINISHED'}
        
        image = blender_images[self.image]
        image.colorspace_settings.name = 'Non-Color'
        image.alpha_mode = 'STRAIGHT'
        
        src_images = [
            blender_images[getattr(self, 'source_image_%d'%i)] if getattr(self, 'source_image_%d'%i) in blender_images.keys() else None
            for i in range4
        ]
        
        readchannel = tuple([{'R':0, 'G':1, 'B':2, 'A':3}[getattr(self, 'source_read_channel_%d'%i)] for i in range4])
        writechannel = tuple([{'R':0, 'G':1, 'B':2, 'A':3}[getattr(self, 'source_write_channel_%d'%i)] for i in range4])
        
        pixels = image.pixels
        w, h = image.size
        n = w*h
        n4 = n*4
        
        sourcedata = tuple([
            tuple(pixels) if not self.channels[i] else
            tuple(src_images[i].pixels) if src_images[i] else (0,0,0,0)*n
            for i in range4
        ])
        
        print('> Writing...')
        
        image.pixels = tuple(
            sourcedata[writechannel[pi%4]][4*(pi//4)+readchannel[pi%4]]
            for pi in range(0, n4)
        )
        
        return {'FINISHED'}
classlist.append(DMR_OT_CombineImageValues)

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
