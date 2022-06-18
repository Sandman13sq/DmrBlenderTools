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

class DMR_OP_SyncActiveMaterial(bpy.types.Operator):
    bl_label = "Sync Active Material"
    bl_idname = 'dmr.sync_active_material'
    bl_description = "Sets active material for all selected objects to the active material of the active object"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return (context.active_object is not None)
    
    def execute(self, context):
        if context.active_object.material_slots:
            activemat = context.active_object.active_material
            print(activemat)
            for obj in context.selected_objects:
                try:
                    obj.active_material = activemat
                except:
                    continue
                        
        return {'FINISHED'}
classlist.append(DMR_OP_SyncActiveMaterial)

# =============================================================================

class DMR_OP_SyncUVLayers(bpy.types.Operator):
    bl_label = "Sync UV Layers by Name"
    bl_idname = 'dmr.sync_uv_name'
    bl_description = 'Matches active and selected uv layers of selected objects to active object by name'
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod 
    def poll(self, context):
        active = context.active_object
        return active and active.type == 'MESH' and active.data.uv_layers
    
    def execute(self, context):
        active = context.active_object
        selectname = active.data.uv_layers.active.name
        rendername = [x for x in active.data.uv_layers if x.active_render][0].name
        
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj.data.uv_layers:
                uvlayers = obj.data.uv_layers
                if rendername in [x.name for x in uvlayers]:
                    uvlayers[rendername].active_render = True
                if selectname in [x.name for x in uvlayers]:
                    uvlayers.active = uvlayers[selectname]
        
        return {'FINISHED'}
classlist.append(DMR_OP_SyncUVLayers)

# =============================================================================

class DMR_OP_SyncVCLayers(bpy.types.Operator):
    bl_label = "Sync Vertex Color Layers by Name"
    bl_idname = 'dmr.sync_vc_name'
    bl_description = 'Matches active and selected vertex color layers of selected objects to active object by name'
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod 
    def poll(self, context):
        active = context.active_object
        return active and active.type == 'MESH' and active.data.vertex_colors
    
    def execute(self, context):
        active = context.active_object
        selectname = active.data.vertex_colors.active.name
        rendername = [x for x in active.data.vertex_colors if x.active_render][0].name
        
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj.data.vertex_colors:
                vcolors = obj.data.vertex_colors
                if rendername in [x.name for x in vcolors]:
                    vcolors[rendername].active_render = True
                if selectname in [x.name for x in vcolors]:
                    vcolors.active = vcolors[selectname]
        
        return {'FINISHED'}
classlist.append(DMR_OP_SyncVCLayers)

# =============================================================================

class DMR_OP_NewUVLayerForSelected(bpy.types.Operator):
    bl_label = "Add UV Layer To Selected Objects"
    bl_idname = 'dmr.new_uv_to_selected'
    bl_description = 'Adds new UV layer to all selected objects'
    bl_options = {'REGISTER', 'UNDO'}
    
    name : bpy.props.StringProperty(name='Layer Name')
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=200)
    
    def execute(self, context):
        for mesh in set([obj.data for obj in context.selected_objects if obj.type == 'MESH']):
            mesh.uv_layers.new(name=self.name)
        
        return {'FINISHED'}
classlist.append(DMR_OP_NewUVLayerForSelected)

# =============================================================================

class DMR_OP_NewVCLayerForSelected(bpy.types.Operator):
    bl_label = "Add VC Layer To Selected Objects"
    bl_idname = 'dmr.new_vc_to_selected'
    bl_description = 'Adds new vertex color layer to all selected objects'
    bl_options = {'REGISTER', 'UNDO'}
    
    name : bpy.props.StringProperty(name='Layer Name')
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=200)
    
    def execute(self, context):
        for mesh in set([obj.data for obj in context.selected_objects if obj.type == 'MESH']):
            mesh.vertex_colors.new(name=self.name)
        
        return {'FINISHED'}
classlist.append(DMR_OP_NewVCLayerForSelected)

# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
