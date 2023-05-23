import bpy
import bmesh

classlist = []

# ==========================================================================

class DMR_OP_SculptMaskFromVGroup(bpy.types.Operator):
    bl_label = "Mask from Vertex Group"
    bl_idname = 'dmr.sculpt_mask_from_vgroup'
    bl_description = 'Masks out vertices in vertex group'
    bl_options = {'REGISTER', 'UNDO'}
    
    clearbefore: bpy.props.BoolProperty(
        name="Clear Before Mask",
        description="Clear present mask before masking group",
        default=True,
    )
    
    insidegroup: bpy.props.BoolProperty(
        name="Mask Group",
        description="Mask vertices inside of group to focus on those outside",
        default=False,
    )
    
    def execute(self, context):
        lastobjectmode = bpy.context.active_object.mode
        bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
        
        obj = context.object
        mesh = obj.data
        verts = mesh.vertices
        vgroups = obj.vertex_groups
        vgroupindex = vgroups.active.index
        
        bm = bmesh.new()
        bm.from_mesh(mesh)
        
        if not bm.verts.layers.paint_mask:
            bm.verts.layers.paint_mask.new()
        masklayer = bm.verts.layers.paint_mask[0]
        
        maskvalue = 1.0 if self.insidegroup else 0.0
        
        for bmvert, v in zip(bm.verts, verts):
            if vgroupindex in [g.group for g in v.groups]:
                bmvert[masklayer] = maskvalue
            elif self.clearbefore:
                bmvert[masklayer] = 1.0 - maskvalue
        
        bm.to_mesh(mesh)
        bm.clear()
        mesh.update()
        
        bpy.ops.object.mode_set(mode = lastobjectmode) # Return to last mode
        if lastobjectmode == 'SCULPT':
            bpy.context.scene.tool_settings.sculpt.show_mask = True
        return {'FINISHED'}
classlist.append(DMR_OP_SculptMaskFromVGroup)

# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in classlist[::-1]:
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
