import bpy

classlist = [];

class DMR_PT_ShapeKeyPanel(bpy.types.Panel): # ------------------------------
    bl_label = "Shape Keys"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Dmr Edit" # Name of sidebar
    
    @classmethod 
    def poll(self, context):
        active = context.active_object;
        if active:
            if active.type == 'MESH' and active.mode == 'EDIT':
                return 1;
        return None;
    
    def draw(self, context):
        active = context.active_object;
        layout = self.layout;
        
        shapekeys = active.data.shape_keys;
        if not shapekeys:
            return;
        
        keyblocks = active.data.shape_keys.key_blocks;
        
        r = layout.row(align=1);
        r.operator('mesh.blend_from_shape');
        r = r.row(align=1);
        op = r.operator('mesh.blend_from_shape', text = '', icon = 'BOLD');
        op.shape = keyblocks[0].name;
        op.blend = 1;
        op.add = False;
        op = r.operator('dmr.blend_from_shape_all', text = '', icon = 'WORLD');
        
classlist.append(DMR_PT_ShapeKeyPanel);

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in classlist:
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
