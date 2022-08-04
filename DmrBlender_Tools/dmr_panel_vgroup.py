import bpy

classlist = []

# =============================================================================

class DMR_PT_3DViewVertexGroups(bpy.types.Panel): # ------------------------------
    bl_label = "Vertex Groups"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mesh" # Name of sidebar
    
    @classmethod 
    def poll(self, context):
        active = context.active_object
        return active and active.type == 'MESH'
    
    def draw(self, context):
        active = context.active_object
        
        group_select_mode = 'ALL'
        if active and 'ARMATURE' in [m.type for m in active.modifiers]:
            group_select_mode = 'BONE_DEFORM'
        
        isediting = active.mode in {'EDIT', 'WEIGHT_PAINT'}
        
        layout = self.layout
        
        if isediting:
            layout.operator('dmr.toggle_editmode_weights', icon = 'MOD_VERTEX_WEIGHT')
        
        r = layout.row(align=1)
        r.operator("dmr.vgroup_movetoend", icon='TRIA_UP_BAR', text="Move to Top").bottom=False
        r.operator("dmr.vgroup_movetoend", icon='TRIA_DOWN_BAR', text="Bottom").bottom=True
        
        # Vertex Group Bar
        bpy.types.DATA_PT_vertex_groups.draw(self, context)
        ob = active;
        group = ob.vertex_groups.active
        col = layout.column()
        
        rightexists = 0
        buttonname = 'Add Right Groups'
        for name in active.vertex_groups.keys():
            if name[-2:] == '_r' or name[-2:] == '.r':
                rightexists = 1
                buttonname = 'Remove Right Groups'
                break
        sub = layout.column(align=1)
        row = sub.row(align = 1)
        row.operator('dmr.add_missing_right_vertex_groups', text = "Add Right")
        row.operator('dmr.remove_right_vertex_groups', text = "Remove Right")
        
        row = sub.row(align = 1)
        r = row.row(align=1)
        op = r.operator('object.vertex_group_clean', text = "Clean")
        op.group_select_mode = group_select_mode
        op.limit = 0.025
        op.keep_single = True
        op = r.operator('object.vertex_group_limit_total', text = "Limit")
        op.group_select_mode = group_select_mode
        r.operator('object.vertex_group_remove_from', text="", icon='WORLD').use_all_groups = True
        
        r = sub.row(align=1)
        op = r.operator('object.vertex_group_normalize_all', text = "Normalize All")
        op.group_select_mode = group_select_mode
        op.lock_active = False
        r.operator('dmr.remove_empty_vertex_groups', text='Remove Empty')
        
        if isediting:
            row = layout.row()
            row.operator("dmr.remove_from_selected_bones", icon='BONE_DATA', text="Remove From Bones")

classlist.append(DMR_PT_3DViewVertexGroups)

# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
