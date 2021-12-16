import bpy
import mathutils

classlist = [];

# =============================================================================

class DMR_OP_BlendAllShapeKeys(bpy.types.Operator):
    bl_label = "Blend Shape to All"
    bl_idname = 'dmr.blend_from_shape_all'
    bl_description = 'Blends selected shape to all other shapes';
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod 
    def poll(self, context):
        active = context.active_object;
        if active:
            if active.type == 'MESH' and active.mode == 'EDIT':
                return 1;
        return None;
    
    def execute(self, context):
        object = context.active_object;
        shapekeys = object.data.shape_keys;
        if not shapekeys:
            return;
        
        keyblocks = shapekeys.key_blocks;
        targetindex = object.active_shape_key_index;
        targetkey = object.active_shape_key;
        
        for i, kb in enumerate(keyblocks):
            if i == targetindex:
                continue;
            
            object.active_shape_key_index = i;
            bpy.ops.mesh.blend_from_shape(shape=targetkey.name, blend=1.0, add=False);
        
        object.active_shape_key_index = targetindex;
        
        return {'FINISHED'}
classlist.append(DMR_OP_BlendAllShapeKeys);

# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in classlist:
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
