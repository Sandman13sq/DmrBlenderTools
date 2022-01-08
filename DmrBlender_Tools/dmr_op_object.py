import bpy
import bmesh

classlist = []

# =============================================================================

class DMR_OP_QuickAutoSmooth(bpy.types.Operator):
    bl_label = "Quick Auto Smooth"
    bl_idname = 'dmr.quick_auto_smooth'
    bl_description = "Turns on auto smooth and sets angle to 180 degrees for selected objects"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return (context.object is not None)
    
    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                obj.data.use_auto_smooth = 1
                obj.data.auto_smooth_angle = 3.14159
                for p in obj.data.polygons:
                    p.use_smooth = 1
                        
        return {'FINISHED'}
classlist.append(DMR_OP_QuickAutoSmooth)

# =============================================================================

class DMR_OP_SelectObjectByMaterial(bpy.types.Operator):
    bl_label = "Select Objects by shared Material"
    bl_idname = 'dmr.select_object_by_material'
    bl_description = "Selects objects that contain the same material as the active object's active material"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return (context.object is not None and
                context.object.type == 'MESH' and
                context.object.data.is_editmode)
    
    def execute(self, context):
        active = bpy.context.view_layer.objects.active
        if active:
            targetmat = active.active_material
            if targetmat:
                for obj in bpy.data.objects:
                    if obj.type == 'MESH':
                        if not (obj.hide_viewport or obj.hide_select):
                            for m in obj.data.materials:
                                if m == targetmat:
                                    obj.select_set(1)
                                    break
        return {'FINISHED'}
classlist.append(DMR_OP_SelectObjectByMaterial)

# =============================================================================

class DMR_OP_ToggleSubSurfOptimalDisplay(bpy.types.Operator):
    bl_label = "Toggle Optimal Display"
    bl_idname = 'dmr.toggle_sss_optimal_display'
    bl_description = "Toggles optimal display for objects"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return (context.object is not None)
    
    def execute(self, context):
        for obj in bpy.data.objects:
            if obj.hide_viewport:
                continue
            if obj.type == 'MESH':
                if obj.modifiers:
                    for m in obj.modifiers:
                        if m.type == 'SUBSURF':
                            m.show_only_control_edges = not m.show_only_control_edges
        return {'FINISHED'}
classlist.append(DMR_OP_ToggleSubSurfOptimalDisplay)

# =============================================================================

class DMR_OP_ToggleMirror(bpy.types.Operator):
    bl_label = "Toggle Mirror Modifier"
    bl_idname = 'dmr.toggle_mirror_modifier'
    bl_description = "Toggles viewport visibility for all mirror modifiers"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return (context.object is not None)
    
    def execute(self, context):
        for obj in bpy.data.objects:
            if obj.hide_viewport:
                continue
            if obj.type == 'MESH':
                if obj.modifiers:
                    for m in obj.modifiers:
                        if m.type == 'MIRROR':
                            m.show_viewport = not m.show_viewport
                    
                        
        return {'FINISHED'}
classlist.append(DMR_OP_ToggleMirror)

# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
