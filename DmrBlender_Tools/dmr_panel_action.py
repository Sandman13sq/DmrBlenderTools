import bpy

classlist = []

# =============================================================================

class DMR_PT_ActionOperators_Graph(bpy.types.Panel): # ------------------------------
    bl_label = "Action Operators"
    bl_space_type = 'GRAPH_EDITOR'
    bl_region_type = 'UI'
    bl_category = "View" # Name of sidebar
    
    @classmethod 
    def poll(self, context):
        return (
            context.object and 
            context.object.animation_data and
            context.object.animation_data.action
            )
    
    def draw(self, context):
        layout = self.layout
        layout.operator('dmr.add_selected_bones_to_keying_set')
        layout.operator('dmr.add_action_channels_to_keying_set')
        layout.operator('dmr.group_channels_by_path')
        
classlist.append(DMR_PT_ActionOperators_Graph)

# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in classlist[::-1]:
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
