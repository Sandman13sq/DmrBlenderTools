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

def register():
    for c in classlist:
        bpy.utils.register_class(c)
    
def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
