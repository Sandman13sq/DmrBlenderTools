import bpy
import bl_ui

classlist = []

# =============================================================================

class DMR_UL_UVLayers(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        lyr = item
        layout.prop(lyr, "name", text="", emboss=False, icon='GROUP_UVS')
        
        r = layout.row(align=1)
        icon = 'RESTRICT_RENDER_OFF' if lyr.active_render else 'RESTRICT_RENDER_ON'
        r.prop(lyr, "active_render", text="", icon=icon, emboss=False)
        
        r = layout.row(align=1)
        
        op = r.operator('dmr.copy_uv_layer_loops', text="", icon='GREASEPENCIL')
        op.source = active_data.active.name
        op.target = item.name
        
        op = r.operator('dmr.copy_uv_layer_loops', text="", icon='COPYDOWN')
        op.source = item.name
        op.target = active_data.active.name
        
classlist.append(DMR_UL_UVLayers)

# =============================================================================

class DMR_PT_UVEditor(bpy.types.Panel):
    bl_label = "UV Layers"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Mesh" # Name of sidebar
    
    @classmethod 
    def poll(self, context):
        obj = context.active_object
        return obj and obj.type == 'MESH'
    
    def draw(self, context):
        layout = self.layout
classlist.append(DMR_PT_UVEditor)

# ------------------------------------------------------------------------------------------

class DMR_PT_UVEditor_Layers(bpy.types.Panel):
    bl_label = "Group Panel"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Mesh" # Name of sidebar
    bl_parent_id = 'DMR_PT_UVEditor'
    
    @classmethod 
    def poll(self, context):
        obj = context.active_object
        return obj and obj.type == 'MESH'
    
    def draw(self, context):
        obj = context.active_object
        
        layout = self.layout
        
        lyr = obj.data.uv_layers.active
        col = layout.column()
        
        r = col.row(align=1)
        r.template_list('DMR_UL_UVLayers', "", obj.data, 'uv_layers', obj.data.uv_layers, 'active_index', rows=3)
        
        cc = r.column(align=1)
        cc.operator('mesh.uv_texture_add', text="", icon='ADD')
        op = cc.operator('mesh.uv_texture_remove', text="", icon='REMOVE')
        
        if lyr:
            cc.separator()
            cc.operator("object.vertex_group_move", icon='TRIA_UP', text="").direction = 'UP'
            cc.operator("object.vertex_group_move", icon='TRIA_DOWN', text="").direction = 'DOWN'
        
        cc.separator()
        
        op = cc.operator("dmr.sync_mesh_data_layers", icon='FILE_REFRESH', text="")
        op.colors=False
        op.uvs=True
        
classlist.append(DMR_PT_UVEditor_Layers)

# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
