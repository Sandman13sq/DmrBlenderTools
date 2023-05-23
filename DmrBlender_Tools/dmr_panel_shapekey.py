import bpy

classlist = []

# =============================================================================

class DMR_PT_3DViewShapeKeys(bpy.types.Panel): # ------------------------------
    bl_label = "Shape Keys"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Edit" # Name of sidebar
    
    @classmethod 
    def poll(self, context):
        active = context.active_object
        return active and active.type == 'MESH'
    
    def draw(self, context):
        active = context.active_object
        layout = self.layout
        
        bpy.types.DATA_PT_shape_keys.draw(self, context)
        
        shapekeys = active.data.shape_keys
        if shapekeys:
            keyblocks = active.data.shape_keys.key_blocks
            
            r = layout.row(align=1)
            r.operator('mesh.blend_from_shape')
            r = r.row(align=1)
            op = r.operator('mesh.blend_from_shape', text = '', icon = 'BOLD')  
            if active and active.mode == 'EDIT':
                op.shape = keyblocks[0].name
                op.blend = 1
                op.add = False
            
            op = r.operator('dmr.blend_from_shape_all', text = '', icon = 'WORLD')
        
classlist.append(DMR_PT_3DViewShapeKeys)

# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in classlist[::-1]:
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
