bl_info = {
    'name': 'Action Marker Panel',
    'description': 'Access action markers through panel in graph and dopesheet editors.',
    'author': 'Dreamer13sq',
    'version': (1, 0),
    'blender': (3, 0, 0),
    'category': 'Animation',
    'support': 'COMMUNITY',
    'doc_url': 'https://github.com/Dreamer13sq/DmrBlenderTools/wiki/Action-Marker-Panel'
}

import bpy

classlist = []

# =============================================================================

class DMR_OP_ActionAddMarker(bpy.types.Operator):
    bl_label = "Add Action Marker"
    bl_idname = 'dmr.action_add_marker'
    bl_description = "Add marker to action"
    bl_options = {'REGISTER', 'UNDO'}
    
    name : bpy.props.StringProperty(
        name='Name', default='New Marker',
        description='Name of new marker'
    )
    
    frame : bpy.props.IntProperty(
        name='Frame', default=0,
        description='Frame to place marker'
    )
    
    @classmethod
    def poll(self, context):
        return context.object and context.object.animation_data and context.object.animation_data.action
    
    def invoke(self, context, event):
        self.frame = context.scene.frame_current
        self.name = 'F ' + str(context.scene.frame_current)
        return self.execute(context)
    
    def execute(self, context):
        context.object.animation_data.action.pose_markers.new(name=self.name).frame=self.frame         
        return {'FINISHED'}
classlist.append(DMR_OP_ActionAddMarker)

# --------------------------------------------------------------------------

class DMR_OP_ActionRemoveMarker(bpy.types.Operator):
    bl_label = "Remove Action Marker"
    bl_idname = 'dmr.action_remove_marker'
    bl_description = "Add marker to action"
    bl_options = {'REGISTER', 'UNDO'}
    
    mode : bpy.props.EnumProperty(
        name='Mode', default='INDEX', items=(
            ('INDEX', 'Index', 'Remove marker by index'),
            ('NAME', 'Name', 'Remove marker(s) by name'),
            ('FRAME', 'Frame', 'Remove marker(s) by frame'),
        ),
        description='Method to delete markers'
    )
    
    name : bpy.props.StringProperty(
        name='Name', default='',
        description='Name of marker(s) to remove'
    )
    
    index : bpy.props.IntProperty(
        name='Index', default=0,
        description='Index of marker to remove'
    )
    
    frame : bpy.props.IntProperty(
        name='Frame', default=0,
        description='Frame of marker(s) to remove'
    )
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'mode')
        if self.mode == 'INDEX':
            layout.prop(self, 'index')
        elif self.mode == 'NAME':
            layout.prop(self, 'name')
        elif self.mode == 'FRAME':
            layout.prop(self, 'frame')
    
    @classmethod
    def poll(self, context):
        return context.object and context.object.animation_data and context.object.animation_data.action
    
    def execute(self, context):
        markers = context.object.animation_data.action.pose_markers
        oldlen = len(markers)
        if oldlen > 0:
            if self.mode == 'INDEX':
                if self.index in range(0, len(markers)):
                    markers.remove([x for x in markers][self.index])
            elif self.mode == 'NAME':
                for m in markers:
                    if m and m.name == self.name:
                        markers.remove(m)
            elif self.mode == 'FRAME':
                for m in markers:
                    if m and m.frame == self.frame:
                        markers.remove(m)
        
        markers.active_index = max(0, min(markers.active_index, len(markers)-1))
        count = oldlen-len(markers)
        if count > 0:
            self.report({'INFO'}, 'Deleted {} markers'.format(count))
        else:
            self.report({'INFO'}, 'No markers deleted')
        return {'FINISHED'}
classlist.append(DMR_OP_ActionRemoveMarker)

# --------------------------------------------------------------------------

class DMR_OP_ActionMoveMarker(bpy.types.Operator):
    bl_label = "Move Action Marker"
    bl_idname = 'dmr.action_move_marker'
    bl_description = "Moves active action marker's internal position"
    bl_options = {'REGISTER', 'UNDO'}
    
    direction : bpy.props.EnumProperty(
        name="Direction",
        description='Direction to move marker',
        items=(
            ('UP', 'Up', 'Move marker up'),
            ('DOWN', 'Down', 'Move marker down'),
            ('TOP', 'Top', 'Move marker to top of list'),
            ('BOTTOM', 'Bottom', 'Move marker to bottom of list'),
        )
    )
    
    @classmethod
    def poll(self, context):
        return (
            context.object and 
            context.object.animation_data and 
            context.object.animation_data.action and
            context.object.animation_data.action.pose_markers
            )
    
    def execute(self, context):
        def DataSave(d):
            return (d.camera, d.name, d.frame, d.select)
        def DataRestore(d, saveddata):
            d.camera, d.name, d.frame, d.select = saveddata
        
        datacollection = context.object.animation_data.action.pose_markers
        
        count = len(datacollection)
        active = datacollection.active
        oldindex = datacollection.active_index
        newindex = oldindex
        
        if count > 0:
            direction = self.direction
            
            if direction == 'UP':
                newindex = (oldindex-1) % count
            elif direction == 'DOWN':
                newindex = (oldindex+1) % count
            elif direction == 'TOP':
                newindex = 0
            elif direction == 'BOTTOM':
                newindex = count-1
            
            if newindex != oldindex:
                newdata = [DataSave(x) for x in datacollection if x != active]
                newdata.insert(newindex, DataSave(active))
                
                for m in datacollection:
                    if m:
                        datacollection.remove(m)
                for x in newdata:
                    DataRestore(datacollection.new(''), x)
                datacollection.active_index = newindex
             
        return {'FINISHED'}
classlist.append(DMR_OP_ActionMoveMarker)

# --------------------------------------------------------------------------

class DMR_OP_SetSceneFrame(bpy.types.Operator):
    bl_label = "Set Scene Frame"
    bl_idname = 'dmr.set_scene_frame'
    bl_description = "Sets frame of scene to given value"
    bl_options = {'REGISTER', 'UNDO'}
    
    frame : bpy.props.IntProperty(
        name='Frame', default=0,
        description='Frame to jump to'
    )
    
    subframe : bpy.props.FloatProperty(
        name='Subframe', default=0.0,
        description='Subframe to jump to'
    )
    
    def execute(self, context):
        context.scene.frame_set(self.frame, subframe=self.subframe);           
        return {'FINISHED'}
classlist.append(DMR_OP_SetSceneFrame)

# --------------------------------------------------------------------------

class DMR_OP_SyncRangeToMarkers(bpy.types.Operator):
    bl_label = "Sync Frame Range to Markers"
    bl_idname = 'dmr.sync_frame_range_to_markers'
    bl_description = "Sets frame range of scene to min and max frames of markers"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(self, context):
        return (
            context.object and 
            context.object.animation_data and 
            context.object.animation_data.action and
            context.object.animation_data.action.pose_markers
            )
    
    def execute(self, context):
        sc = context.scene
        markerframes = [x.frame for x in context.object.animation_data.action.pose_markers]
        sc.frame_start = min(markerframes)
        sc.frame_end = max(markerframes)
        return {'FINISHED'}
classlist.append(DMR_OP_SyncRangeToMarkers)

# --------------------------------------------------------------------------

class DMR_OP_ActionMarkers_SelectAction(bpy.types.Operator):
    bl_label = "Select Action and Sync Markers"
    bl_idname = 'dmr.markers_select_action'
    bl_description = 'Sets action of all objects to match active';
    bl_options = {'REGISTER', 'UNDO'}
    
    actionname: bpy.props.StringProperty(name="Action Name",)
    
    @classmethod
    def poll(self, context):
        return context.object
    
    def execute(self, context):
        action = bpy.data.actions[self.actionname]
        
        if action:
            context.object.animation_data.action = action;
            bpy.ops.dmr.sync_frame_range_to_markers()
        return {'FINISHED'}
classlist.append(DMR_OP_ActionMarkers_SelectAction);

# =====================================================================================

class DMR_UL_ActionMarkers(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        r = layout.row(align=1)
        r = [r.row(align=1) for x in (0, 1, 2, 3)]
        r[0].scale_x = 0.3
        r[1].scale_x = 1
        r[2].scale_x = 0.77
        
        r[0].label(text=' '+str(index))
        r[1].operator('dmr.set_scene_frame', text='', icon='PLAY', emboss=context.scene.frame_current!=item.frame).frame=item.frame
        r[2].prop(item, 'frame', text='')
        r[3].prop(item, 'name', text='', event=0)
classlist.append(DMR_UL_ActionMarkers)

# =============================================================================

def DrawMarkerUIList(self, context):
    if context.object.animation_data:
        layout = self.layout
        action = context.object.animation_data.action
        markers = action.pose_markers
        sc = context.scene
        
        if markers:
            row = layout.row(align=0)
            row.template_list(
                "DMR_UL_ActionMarkers", "", 
                action, "pose_markers", 
                markers, "active_index", 
                rows=5)
            
            col = row.column(align=1)
            col.operator('dmr.action_add_marker', icon='ADD', text='').frame = sc.frame_current
            op = col.operator('dmr.action_remove_marker', icon='REMOVE', text='')
            op.mode = 'INDEX'
            op.index = markers.active_index
            col.operator('dmr.action_move_marker', icon='TRIA_UP', text='').direction='UP'
            col.operator('dmr.action_move_marker', icon='TRIA_DOWN', text='').direction='DOWN'
        else:
            layout.operator('dmr.action_add_marker', icon='ADD').frame = sc.frame_current

# --------------------------------------------------------------------------
class DMR_PT_ActionMarkers(bpy.types.Panel):
    bl_label = "Markers"
    bl_space_type = 'DOPESHEET_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Markers" # Name of sidebar
    
    @classmethod 
    def poll(self, context):
        return (
            context.object and 
            context.object.animation_data and
            context.object.animation_data.action
            )
    
    def draw(self, context):
        layout = self.layout
        layout.prop(context.space_data, 'show_pose_markers')
        layout.operator('dmr.sync_frame_range_to_markers')
        DrawMarkerUIList(self, context)
classlist.append(DMR_PT_ActionMarkers)

# --------------------------------------------------------------------------
class DMR_PT_ActionMarkers_Graph(bpy.types.Panel):
    bl_label = "Markers"
    bl_space_type = 'GRAPH_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Markers" # Name of sidebar
    
    @classmethod 
    def poll(self, context):
        return (
            context.object and 
            context.object.animation_data and
            context.object.animation_data.action
            )
    
    def draw(self, context):
        layout = self.layout
        layout.operator('dmr.sync_frame_range_to_markers')
        DrawMarkerUIList(self, context)
classlist.append(DMR_PT_ActionMarkers_Graph)

# =============================================================================

class DMR_UL_ActionMarkers_SelectAction(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        r = layout.row(align=1)
        r = [r.row(align=1) for x in (0, 1)]
        r[0].scale_x = 0.3
        r[1].scale_x = 1
        r[0].label(text=' '+str(index))
        r[1].operator('dmr.set_scene_frame', text='', icon='PLAY', emboss=context.scene.frame_current!=item.frame).frame=item.frame
classlist.append(DMR_UL_ActionMarkers_SelectAction)

# --------------------------------------------------------------------------
class DMR_PT_ActionMarkers_ActionSelect(bpy.types.Panel):
    bl_label = "Action Select"
    bl_space_type = 'GRAPH_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Markers" # Name of sidebar
    
    @classmethod 
    def poll(self, context):
        return (
            context.object and 
            context.object.animation_data and
            context.object.animation_data.action
            )
    
    def draw(self, context):
        layout = self.layout
        c = layout.column(align=1)
        for a in bpy.data.actions:
            c.operator('dmr.markers_select_action', text = a.name).actionname = a.name
classlist.append(DMR_PT_ActionMarkers_ActionSelect)

# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
