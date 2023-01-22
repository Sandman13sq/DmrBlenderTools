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

class DMR_OT_SetActiveMaterialOutput(bpy.types.Operator):
    bl_idname = "dmr.set_active_material_output"
    bl_label = "Set Active Material Output"
    bl_options = {'REGISTER', 'UNDO'}
    
    node_name : bpy.props.StringProperty(name="Node Name")
    target : bpy.props.EnumProperty(name="Target", default='VISIBLE', items=(
        ('ACTIVE', "Active Object", ""),
        ('SELECTED', "Selected Objects", ""),
        ('VISIBLE', "Visible Objects", ""),
        ('ALL', "All Objects", ""),
        ('MATERIAL', "All Materials", "")
    ))
    case_sensitive : bpy.props.BoolProperty(name='Case Sensitive', default=False)
    
    @classmethod
    def poll(cls, context):
        return context.object and context.object.active_material

    def execute(self, context):
        objects = []
        
        if self.target == 'ACTIVE':
            objects = [context.object]
        elif self.target == 'SELECTED':
            objects = context.selected_objects
        elif self.target == 'VISIBLE':
            objects = [x for x in context.scene.objects if x.visible_get()]
        elif self.target == 'ALL':
            objects = [x for x in bpy.data.objects]
        
        objects = [x for x in objects if x.active_material]
        materials = list(set([slot.material for obj in objects for m in obj.materials_slots]))
        
        nodename = self.node_name
        
        for material in materials:
            outputnodes = [x for x in material.node_tree.nodes if x.type == 'OUTPUT_MATERIAL']
            
            # Use Name
            output = ([x for x in outputnodes if x.name.lower() == nodename.lower()]+[None])[0]
            
            # Check Label
            if not output:
                output = ([x for x in outputnodes if x.label.lower() == nodename.lower()]+[None])[0]
            
            if output:
                for nd in outputnodes:
                    nd.is_active_output = False
                output.is_active_output = True
        
        context.view_layer.update()
            
        return {'FINISHED'}
classlist.append(DMR_OT_SetActiveMaterialOutput)

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

class DMR_OP_SyncMeshDataLayers(bpy.types.Operator):
    bl_label = "Sync Vertex Color Layers by Name"
    bl_idname = 'dmr.sync_mesh_data_layers'
    bl_description = 'Matches active and selected mesh data layers of selected objects to active object by name'
    bl_options = {'REGISTER', 'UNDO'}
    
    colors : bpy.props.BoolProperty(name="Sync Colors", default=True)
    uvs : bpy.props.BoolProperty(name="Sync UVs", default=True)
    groups : bpy.props.BoolProperty(name="Sync Groups", default=False)
    
    @classmethod 
    def poll(self, context):
        active = context.active_object
        return active and active.type == 'MESH'
    
    def execute(self, context):
        # Active
        active = context.active_object
        
        if not active:
            active = context.object
        
        if self.colors:
            vcname = (
                active.data.color_attributes.active_color.name,
                active.data.color_attributes.active.name
            ) if bpy.app.version >= (3, 2, 2) else (
                active.data.vertex_colors.active.name,
                [x for x in active.data.vertex_colors if x.active_render][0].name
            )
        
        if self.uvs:
            uvname = (
                active.data.uv_layers.active.name,
                [x for x in active.data.uv_layers if x.active_render][0].name
            )
        
        groupname = active.vertex_groups.active.name if active.vertex_groups else ""
        
        # Selcted
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                # Group
                if self.groups:
                    if groupname in obj.vertex_groups.keys():
                        obj.vertex_groups.active = obj.vertex_groups[groupname]
                
                mesh = obj.data
                # Color
                if self.colors:
                    if bpy.app.version >= (3, 2, 2):
                        vcolors = mesh.color_attributes
                        if vcname[0] in vcolors.keys():
                            vcolors.active_color = vcolors[vcname[0]]
                        if vcname[1] in vcolors.keys():
                            vcolors.active = vcolors[vcname[1]]
                    
                    else:
                        vcolors = obj.data.vertex_colors
                        if vcname[0] in vcolors.keys():
                            vcolors.active = vcolors[vcname[0]]
                        if vcname[1] in vcolors.keys():
                            vcolors[vcname[1]].active_render = True
                
                # UVs
                if self.uvs:
                    uvlayers = obj.data.uv_layers
                    if uvname[0] in uvlayers.keys():
                        uvlayers.active = uvlayers[uvname[0]]
                    if uvname[1] in uvlayers.keys():
                        uvlayers[uvname[1]].active_render = True
        
        return {'FINISHED'}
classlist.append(DMR_OP_SyncMeshDataLayers)

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
            if self.name not in mesh.uv_layers.keys():
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
            if bpy.app.version >= (3, 2, 2):
                if self.name not in mesh.color_attributes.keys():
                    mesh.color_attributes.new(self.name, "BYTE_COLOR", 'CORNER')
            else:
                if self.name not in mesh.vertex_colors.keys():
                    mesh.vertex_colors.new(name=self.name)
        
        return {'FINISHED'}
classlist.append(DMR_OP_NewVCLayerForSelected)

# =============================================================================

class DMR_OP_NewVGroupForSelected(bpy.types.Operator):
    bl_label = "Add Vertex Group To Selected Objects"
    bl_idname = 'dmr.new_vgroup_to_selected'
    bl_description = 'Adds new vertex color layer to all selected objects'
    bl_options = {'REGISTER', 'UNDO'}
    
    name : bpy.props.StringProperty(name='Layer Name')
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=200)
    
    def execute(self, context):
        for obj in set([obj for obj in context.selected_objects if obj.type == 'MESH']):
            if self.name not in obj.vertex_groups.keys():
                obj.vertex_groups.new(name=self.name)
        
        return {'FINISHED'}
classlist.append(DMR_OP_NewVGroupForSelected)

# =============================================================================

class DMR_OP_QuickDataTransfer(bpy.types.Operator):
    bl_label = "Quick Data Transfer"
    bl_idname = 'dmr.quick_data_transfer'
    bl_description = 'Adds Data Transfer Modifier to selected objects with active as target'
    bl_options = {'REGISTER', 'UNDO'}
    
    vertex_groups : bpy.props.BoolProperty(name="Vertex Groups", default=True)
    vertex_colors : bpy.props.BoolProperty(name="Vertex Colors", default=False)
    uvs : bpy.props.BoolProperty(name="UVs", default=False)
    
    max_distance : bpy.props.FloatProperty(name="Max Distance", default=0)
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=200)
    
    def execute(self, context):
        active = context.active_object
        
        for obj in [obj for obj in context.selected_objects if obj != active]:
            m = obj.modifiers.new(name="Quick Data Transfer", type='DATA_TRANSFER')
            m.object = active
            
            if self.vertex_groups:
                m.use_vert_data = True
                m.data_types_verts = {'VGROUP_WEIGHTS'}
                m.vert_mapping = 'POLYINTERP_NEAREST'
            
            if self.max_distance > 0.0:
                m.use_max_distance = True
                m.max_distance = self.max_distance
        
        return {'FINISHED'}
classlist.append(DMR_OP_QuickDataTransfer)

# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in list(classlist)[::-1]:
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
