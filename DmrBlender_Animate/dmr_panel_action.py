import bpy
import sys

classlist = []

def ActionRange_Update(self, context):
    o = context.object
    if o and o.animation_data and o.animation_data.action:
        if o.animation_data.action == self:
            context.scene.frame_start = self.frame_start
            context.scene.frame_end = self.frame_end

# =============================================================================

class ActionSelectPanel(bpy.types.Panel): # ------------------------------
    bl_label = "Action Select"
    bl_region_type = 'UI'
    bl_category = "Action" # Name of sidebar
    
    @classmethod
    def poll(self, context):
        return bpy.data.actions
    
    def draw(self, context):
        layout = self.layout
        c = layout.box().column(align=1)
        
        action = None
        try:
            action = context.object.animation_data.action
        except:
            action = None
        
        for i,a in enumerate(bpy.data.actions):
            r = c.row(align=1)
            lc = r.column()
            lc.scale_x = 0.3
            lc.label(text=str(i))
            r.operator('dmr.select_action', text='%s %s' % (a.name, [a.frame_start, a.frame_end]), 
                emboss=a!=action).actionname = a.name

class DMR_PT_ActionSelect_Graph(ActionSelectPanel, bpy.types.Panel): # ------------------------------
    bl_space_type = 'GRAPH_EDITOR'
classlist.append(DMR_PT_ActionSelect_Graph)

class DMR_PT_ActionSelect_3DView(ActionSelectPanel, bpy.types.Panel): # ------------------------------
    bl_space_type = 'VIEW_3D'
classlist.append(DMR_PT_ActionSelect_3DView)

# =============================================================================

class DMR_PT_ActionProperties(bpy.types.Panel): # ------------------------------
    bl_label = "Action Properties"
    bl_space_type = 'DOPESHEET_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Action" # Name of sidebar
    
    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
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
        
        if action:
            fstart = action.get('frame_start', scene.frame_start)
            fend = action.get('frame_end', scene.frame_end)
            
            s = layout.box().row()
            s.label(text='[%s, %s]' % (fstart, fend))
            s.label(text='Duration: %s' % (fend-fstart))
            
            row = layout.row(align=1)
            if 1:
                row.prop(action, "frame_start", text='Start')
                row.prop(action, "frame_end", text='End')
            else:
                row.prop(scene, "frame_start", text='Start*')
                row.prop(scene, "frame_end", text='End*')
            
            row = layout.row(align=0)
            row.operator('dmr.frame_range_store', text='Save').action = action.name
            row.operator('dmr.frame_range_restore', text='Restore').action = action.name
classlist.append(DMR_PT_ActionProperties)

class DMR_PT_ActionProperties_Graph(DMR_PT_ActionProperties, bpy.types.Panel): # ------------------------------
    bl_space_type = 'GRAPH_EDITOR'
classlist.append(DMR_PT_ActionProperties_Graph)

class DMR_PT_ActionProperties_3DView(DMR_PT_ActionProperties, bpy.types.Panel): # ------------------------------
    bl_space_type = 'VIEW_3D'
classlist.append(DMR_PT_ActionProperties_3DView)

# ==========================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)
    
    bpy.types.Action.frame_start = bpy.props.IntProperty(
        name='Frame Start', default=1, update=ActionRange_Update
    )
    bpy.types.Action.frame_end = bpy.props.IntProperty(
        name='Frame End', default=250, update=ActionRange_Update
    )
    bpy.types.Action.fps = bpy.props.IntProperty(
        name='Frame Rate', default=60
    )
    

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
