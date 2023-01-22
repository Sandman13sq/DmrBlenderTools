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
        layout = self.layout.column()
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
        
        r = row.column(align=1).row(align=1)
        r.column().operator('dmr.toggle_mirror_modifier', icon = 'MOD_MIRROR', text = '')
        if obj:
            if obj.mode == 'EDIT':
                if obj.type == 'MESH':
                    m = ([m for m in obj.modifiers if m.type == 'MIRROR']+[None])[0]
                    if m:
                        r.prop(m, 'use_clip', text="", icon='NODE_SIDE')
        
        # Toggles
        row = layout.row(align = 1)
        row.scale_x = 4.0
        row.scale_y = 1.0
        row.alignment = 'CENTER'
        row.column().prop(rd, "use_simplify", icon_only=True, icon='MOD_SUBSURF')
        row.column().prop(bpy.context.space_data.overlay, 'show_split_normals', icon_only=True, icon='NORMALS_VERTEX_FACE')
        if obj:
            row.column().prop(obj, "show_wire", icon_only=True, icon='MOD_LATTICE')
        row.column().operator('dmr.toggle_sss_optimal_display', text='', icon='SHADING_WIRE')
        
        row.prop(context.tool_settings, "use_keyframe_insert_auto", text="", toggle=True)
        
        # Action
        if obj:
            if obj.mode == 'EDIT':
                layout.prop(bpy.context.scene.tool_settings, 'proportional_size')
            
            for armobj in [obj, obj.find_armature()]:
                if armobj and armobj.animation_data != None:
                    r = layout.row(align=1)
                    
                    r.label(text="", icon=armobj.type+"_DATA")
                    
                    if not armobj.animation_data or not armobj.animation_data.action:
                        rr = r.row(align=1)
                        rr.scale_x = 1.5
                        rr.prop(armobj, 'active_action', text="", icon="ACTION", icon_only=True)
                        r.operator('action.new')
                    else:
                        rr = r.row(align=1)
                        rr.scale_x = 1.5
                        rr.prop(armobj.animation_data, 'action', text="", icon="ACTION", icon_only=True)
                        r.prop(armobj.animation_data.action, 'name', text="")
                        r.prop(armobj.animation_data.action, 'use_fake_user', text="")
                        r.prop(armobj, 'op_scene_range_from_action', text='', toggle=True, icon='PREVIEW_RANGE')
                    
        
classlist.append(DMR_PT_HotMenu)

# =============================================================================

def ActionChange(self, context):
    action = self.active_action
    self.animation_data.action = action

def SceneRangeFromAction(self, context):
    if self.op_scene_range_from_action:
        action = self.animation_data.action
        context.scene.frame_start = action.frame_start
        context.scene.frame_end = action.frame_end
        self.op_scene_range_from_action = False

def ActionChangeSync(self, context):
    if self.op_active_action_sync:
        self.animation_data.action = self.active_action
        self.op_active_action_sync = False

def register():
    for c in classlist:
        bpy.utils.register_class(c)
    
    bpy.types.Object.active_action = bpy.props.PointerProperty(
        name="Action", type=bpy.types.Action, update=ActionChange
    )
    
    bpy.types.Object.op_scene_range_from_action = bpy.props.BoolProperty(
        name="Set Scene Range From Action", default=False, update=SceneRangeFromAction
    )
    
    bpy.types.Scene.sync_action_frame_range = bpy.props.BoolProperty(
        name="Sync Action Frame Range", default=True
    )

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
