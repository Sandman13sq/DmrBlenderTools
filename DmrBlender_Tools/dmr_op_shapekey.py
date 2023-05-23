import bpy
import mathutils

classlist = []

# =============================================================================

class DMR_OP_BlendAllShapeKeys(bpy.types.Operator):
    bl_label = "Blend Shape to All"
    bl_idname = 'dmr.blend_from_shape_all'
    bl_description = 'Blends selected shape to all other shapes'
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod 
    def poll(self, context):
        active = context.active_object
        return active and active.type == 'MESH' and active.mode == 'EDIT' and active.data.shape_keys
    
    def execute(self, context):
        object = context.active_object
        shapekeys = object.data.shape_keys
        
        keyblocks = shapekeys.key_blocks
        targetindex = object.active_shape_key_index
        targetkey = object.active_shape_key
        
        for i, kb in enumerate(keyblocks):
            if i == targetindex:
                continue
            
            object.active_shape_key_index = i
            bpy.ops.mesh.blend_from_shape(shape=targetkey.name, blend=1.0, add=False)
        
        object.active_shape_key_index = targetindex
        
        return {'FINISHED'}
classlist.append(DMR_OP_BlendAllShapeKeys)

# =============================================================================

class DMR_OP_ResetShapeKeyVertex(bpy.types.Operator):
    bl_label = "Reset Vertex Shape Keys"
    bl_idname = 'dmr.reset_vertex_shape_keys'
    bl_description = 'Sets shape key positions of selected vertices to "Basis" for all keys'
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod 
    def poll(self, context):
        active = context.active_object
        return active and active.type == 'MESH' and active.mode == 'EDIT' and active.data.shape_keys
    
    def execute(self, context):
        oldactive = context.active_object
        
        if len(context.selected_objects) == 0:
            self.report({'WARNING'}, "No objects selected")
            return {'FINISHED'}
        
        for obj in context.selected_objects:
            if obj.type == "MESH":
                # No Shape Keys exist for object
                if obj.data.shape_keys == None: continue
                shape_keys = obj.data.shape_keys.key_blocks
                if len(shape_keys) == 0: continue
                
                keyindex = {}
                basis = shape_keys[0]
                bpy.context.view_layer.objects.active = obj
                oldactivekey = obj.active_shape_key_index
                
                for i in range(0, len(shape_keys)):
                    keyindex[ shape_keys[i].name ] = i
                
                # For all keys...
                for sk in shape_keys:
                    obj.active_shape_key_index = keyindex[sk.name]
                    bpy.ops.mesh.blend_from_shape(shape = basis.name, add = False)
                
                obj.active_shape_key_index = oldactivekey
                
        bpy.context.view_layer.objects.active = oldactive
            
        return {'FINISHED'}
classlist.append(DMR_OP_ResetShapeKeyVertex)

# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in classlist[::-1]:
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
