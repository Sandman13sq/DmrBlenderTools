import bpy

classlist = []

# =============================================================================

class DMR_PT_HotMenu(bpy.types.Panel): # ------------------------------
    bl_label = "Dmr Hot Menu"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Item" # Name of sidebar
    
    def draw(self, context):
        active = bpy.context.active_object
        obj = context.object
        layout = self.layout
        rd = context.scene.render
        row = layout.row(align = 0)
        row.scale_x = 2.0
        row.scale_y = 1.0
        row.alignment = 'CENTER'
        row.column().operator(
            'dmr.toggle_editmode_weights', icon = 'MOD_VERTEX_WEIGHT', text = '', 
            emboss=active.mode=='EDIT' if active else 0)
        
        c = row.row(align = 1)
        c.operator('dmr.reset_3d_cursor', icon = 'PIVOT_CURSOR', text = '')
        c = c.column(align = 1)
        c.operator('dmr.reset_3d_cursor_x', text = 'x')
        c.scale_x = 0.05
        
        row.column().operator('dmr.toggle_pose_all', icon = 'ARMATURE_DATA', text = '')
        
        row.column().operator('dmr.image_reload', icon = 'IMAGE_DATA', text = '')
        
        row.column().operator('dmr.toggle_mirror_modifier', icon = 'MOD_MIRROR', text = '')
        
        row = layout.row(align = 1)
        row.scale_x = 4.0
        row.scale_y = 1.0
        row.alignment = 'CENTER'
        row.column().prop(rd, "use_simplify", icon_only=True, icon='MOD_SUBSURF')
        row.column().prop(bpy.context.space_data.overlay, 'show_split_normals', icon_only=True, icon='NORMALS_VERTEX_FACE')
        if obj:
            row.column().prop(obj, "show_wire", icon_only=True, icon='MOD_LATTICE')
        if obj and obj.mode == 'EDIT':
            layout.prop(bpy.context.scene.tool_settings, 'proportional_size')
        
        row = layout.row(align=1)
        row.scale_x = 2.0
        row.scale_y = 1.0
        row.alignment = 'CENTER'
        
        row.column().operator('dmr.toggle_sss_optimal_display', icon = 'SHADING_WIRE')
        
classlist.append(DMR_PT_HotMenu)

# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
