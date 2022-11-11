import bpy
import bl_ui

classlist = []

# =============================================================================

class DMR_UL_VertexGroups(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        vgroup = item
        layout.prop(vgroup, "name", text="", emboss=False, icon_value=icon)
        
        r = layout.row(align=1)
        icon = 'LOCKED' if vgroup.lock_weight else 'UNLOCKED'
        r.prop(vgroup, "lock_weight", text="", icon=icon, emboss=False)
        op = r.operator('dmr.vertex_group_new', text="", icon='GREASEPENCIL')
        op.group_name = item.name
        op.assign_selected = True
        op.weight = context.tool_settings.vertex_group_weight
        op = r.operator('dmr.vertex_group_remove_vertices', text="", icon='X')
        op.group_name = item.name
classlist.append(DMR_UL_VertexGroups)

# =============================================================================

class DMR_PT_3DViewVertexGroups(bpy.types.Panel):
    bl_label = "Vertex Groups"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mesh" # Name of sidebar
    
    @classmethod 
    def poll(self, context):
        obj = context.active_object
        return obj and obj.type == 'MESH'
    
    def draw(self, context):
        obj = context.active_object
        armobj = obj.find_armature()
        
        group_select_mode = 'ALL'
        if obj and armobj:
            group_select_mode = 'BONE_DEFORM'
        
        isediting = obj.mode in {'EDIT', 'WEIGHT_PAINT'}
        
        layout = self.layout
        
        if isediting:
            layout.operator('dmr.toggle_editmode_weights', icon = 'MOD_VERTEX_WEIGHT')
        
        r = layout.row(align=1)
        r.operator("dmr.vgroup_movetoend", icon='TRIA_UP_BAR', text="Move to Top").bottom=False
        r.operator("dmr.vgroup_movetoend", icon='TRIA_DOWN_BAR', text="Bottom").bottom=True
        
        # Vertex Group Bar
        #bpy.types.DATA_PT_vertex_groups.draw(self, context)
        group = obj.vertex_groups.active
        col = layout.column()
        
        r = col.row()
        r.template_list('DMR_UL_VertexGroups', "", obj, 'vertex_groups', obj.vertex_groups, 'active_index', rows=3)
        
        cc = r.column(align=1)
        cc.operator('dmr.vertex_group_new', text="", icon='ADD')
        op = cc.operator('object.vertex_group_remove', text="", icon='REMOVE')
        op.all = False
        op.all_unlocked = False
        
        cc.separator()
        cc.menu("MESH_MT_vertex_group_context_menu", icon='DOWNARROW_HLT', text="")
        
        if group:
            cc.separator()
            cc.operator("object.vertex_group_move", icon='TRIA_UP', text="").direction = 'UP'
            cc.operator("object.vertex_group_move", icon='TRIA_DOWN', text="").direction = 'DOWN'
        
        # After List
        rr = layout.row()
        sub = rr.row(align=True)
        sub.operator("object.vertex_group_assign", text="Assign")
        sub.operator("object.vertex_group_remove_from", text="Remove")

        sub = rr.row(align=True)
        sub.operator("object.vertex_group_select", text="Select")
        sub.operator("object.vertex_group_deselect", text="Deselect")
        
        layout.prop(context.tool_settings, "vertex_group_weight", text="Weight")
        
        rightexists = 0
        buttonname = 'Add Right Groups'
        for name in obj.vertex_groups.keys():
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
        r.operator('dmr.remove_unused_vertex_groups', text='Remove Empty')
        
        if isediting:
            row = layout.row()
            row.operator("dmr.remove_from_selected_bones", icon='BONE_DATA', text="Remove From Bones")
classlist.append(DMR_PT_3DViewVertexGroups)

# ------------------------------------------------------------------------------------------

class DMR_PT_3DViewVertexGroups_Active(bpy.types.Panel):
    bl_label = "Active Vertex"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mesh" # Name of sidebar
    bl_parent_id = 'DMR_PT_3DViewVertexGroups'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        if context.object and context.object.type == 'MESH' and context.object.mode == 'EDIT':
            []
            #bpy.types.VIEW3D_PT_overlay_edit_mesh.draw(self, context)
            #bl_ui.space_view3d.VIEW3D_PT_context_properties.draw(self, context)
            
classlist.append(DMR_PT_3DViewVertexGroups_Active)

# ------------------------------------------------------------------------------------------

class DMR_PT_3DViewVertexGroups_UnusedDeforms(bpy.types.Panel):
    bl_label = "Unused Deforms"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mesh" # Name of sidebar
    bl_parent_id = 'DMR_PT_3DViewVertexGroups'
    bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod 
    def poll(self, context):
        obj = context.active_object
        return obj and obj.type == 'MESH'
    
    def draw(self, context):
        obj = context.active_object
        armobj = obj.find_armature()
        
        layout = self.layout
        
        if not armobj:
            layout.label(text="No Linked Armature")
        else:
            c = layout.column(align=1)
            vgroups = obj.vertex_groups
            bones = armobj.data.bones
            unused = [b.name for b in bones if (b.name not in vgroups and b.use_deform)]
            
            c.scale_y = 0.9
            
            for name in unused:
                r = c.box().row(align=1)
                r.label(text=name)
                rr = r.row(align=1)
                rr.scale_x = 0.8
                op = rr.operator('dmr.vertex_group_new', text="Add", icon='ADD')
                op.group_name = name
                op.assign_selected = False
                op = rr.operator('dmr.vertex_group_new', text="Assign", icon='GREASEPENCIL')
                op.group_name = name
                op.assign_selected = True
            
classlist.append(DMR_PT_3DViewVertexGroups_UnusedDeforms)

# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
