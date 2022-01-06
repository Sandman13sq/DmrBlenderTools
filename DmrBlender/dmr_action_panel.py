import bpy
import sys

classlist = [];

def ActionNavDraw(self, context):
    layout = self.layout
    
    box = layout.box()
    box.scale_y = 1.5
    box.operator('dmr.object_sync_action')
    
    action = None
    if self.bl_space_type == 'DOPESHEET_EDITOR':
        st = context.space_data
        layout.template_ID(st, "action", new="action.new", unlink="action.unlink")
        if st.mode in {'ACTION', 'SHAPEKEY'}:
            action = st.action
    else:
        if context.object:
            if context.object.animation_data:
                action = context.object.animation_data.action
    
    scene = context.scene
    tool_settings = context.tool_settings
    dosync = scene.syncactionframerange
    
    if action:
        fstart = action.get('frame_start', scene.frame_start)
        fend = action.get('frame_end', scene.frame_end)
        
        s = layout.box().row()
        s.label(text='[%s, %s]' % (fstart, fend))
        s.label(text='Duration: %s' % (fend-fstart))
        s.prop(scene, 'syncactionframerange', icon_only=True, icon='FILE_REFRESH')
        
        row = layout.row(align=1)
        if "frame_start" in action:
            row.prop(scene, "frame_start", text='Start')
            row.prop(scene, "frame_end", text='End')
        else:
            row.prop(scene, "frame_start", text='Start*')
            row.prop(scene, "frame_end", text='End*')
        
        row = layout.row(align=0)
        row.operator('dmr.frame_range_store', text='Save')
        row.operator('dmr.frame_range_restore', text='Restore')


class DMR_PT_ActionNav(bpy.types.Panel): # ------------------------------
    bl_label = "Action Navigation"
    bl_space_type = 'DOPESHEET_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Pose" # Name of sidebar
    draw = ActionNavDraw
classlist.append(DMR_PT_ActionNav);

class DMR_PT_ActionNav_Graph(bpy.types.Panel): # ------------------------------
    bl_label = "Action Navigation"
    bl_space_type = 'GRAPH_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Pose" # Name of sidebar
    draw = ActionNavDraw
classlist.append(DMR_PT_ActionNav_Graph);

# ==========================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)
    
    bpy.types.Scene.syncactionframerange = bpy.props.BoolProperty(
        name="Sync Action Frame Range", default=False,
    );

def unregister():
    for c in reverse(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
