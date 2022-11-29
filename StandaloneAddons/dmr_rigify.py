bl_info = {
    'name': 'Rigify Helper Functions',
    'description': 'Panels and operators to make using rigify more efficient. (Not official)',
    'author': 'Dreamer13sq',
    'version': (1, 0),
    'blender': (3, 3, 1),
    'category': 'Animation',
    'support': 'COMMUNITY',
}

import bpy

classlist = []

# ======================================================================================

class DMR_OT_Rigify_FindLayerInfo(bpy.types.Operator):
    bl_idname = "dmr.rigify_find_layer_info"
    bl_label = "Find Rigify Layer Info"
    
    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'ARMATURE'

    def execute(self, context):
        outrig = context.active_object
        metarig = ([x for x in bpy.data.objects if x.type=='ARMATURE' and (x.data.rigify_rig_basename == outrig.name or x.data.rigify_target_rig == outrig)]+[None])[0]
        
        if metarig:
            layers = metarig.data.rigify_layers
            outrig.data['rigify_layer_data'] = [
                [lyr.row, lyr.group]
                for i, lyr in enumerate(metarig.data.rigify_layers) if lyr.name
            ]
            
            outrig.data['rigify_layer_data'][-1][0] = 28
            
            outrig.data['rigify_layer_name'] = [
                lyr.name 
                for i, lyr in enumerate(metarig.data.rigify_layers) if lyr.name
            ]
        else:
            self.report({'WARNING'}, 'No meta rig found that targets active object')
        
        return {'FINISHED'}
classlist.append(DMR_OT_Rigify_FindLayerInfo)

# --------------------------------------------------------------------------------

class DMR_OT_ArmatureSetLayerVisibility(bpy.types.Operator):
    bl_idname = "dmr.armature_layer_visibility"
    bl_label = "Set Layer Visibility"
    
    layers : bpy.props.BoolVectorProperty(name='Layers', size=32, default=[False]*32)
    
    def draw(self, context):
        []
    
    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'ARMATURE'

    def execute(self, context):
        context.active_object.data.layers = tuple(self.layers)
        return {'FINISHED'}
classlist.append(DMR_OT_ArmatureSetLayerVisibility)

# --------------------------------------------------------------------------------

class DMR_OT_ArmatureToggleLayerVisibility(bpy.types.Operator):
    bl_idname = "dmr.armature_layer_toggle"
    bl_label = "Toggle Layer Visibility"
    
    layers : bpy.props.BoolVectorProperty(name='Layers', size=32, default=[False]*32)
    
    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'ARMATURE'

    def execute(self, context):
        armlayers = context.active_object.data.layers
        targetlayers = self.layers
        layerpairs = list(zip(targetlayers, armlayers))
        
        alloff = sum([x==y for x,y in layerpairs if x]) == 0
        context.active_object.data.layers = tuple(y if not x else alloff for x,y in layerpairs)
        return {'FINISHED'}
classlist.append(DMR_OT_ArmatureToggleLayerVisibility)

# ---------------------------------------------------------------------------------

class DMR_OT_ArmatureSetBoneLayer(bpy.types.Operator):
    bl_idname = "dmr.armature_layer_assign"
    bl_label = "Set Bone Layer"
    
    layers : bpy.props.BoolVectorProperty(name='Layers', size=32, default=[False]*32)
    
    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'ARMATURE'

    def execute(self, context):
        for b in context.object.data.bones if context.object.mode != 'EDIT' else context.object.data.edit_bones:
            if b.select:
                b.layers = self.layers
        return {'FINISHED'}
classlist.append(DMR_OT_ArmatureSetBoneLayer)

# ---------------------------------------------------------------------------------

class DMR_OT_ArmatureSetBoneLayerIndex(bpy.types.Operator):
    bl_idname = "dmr.armature_layer_assign_index"
    bl_label = "Set Bone Layer Index"
    bl_options = {'REGISTER', 'UNDO'}
    
    layer : bpy.props.IntProperty(name='Layer Index', min=0, max=31)
    
    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'ARMATURE'

    def execute(self, context):
        for b in context.object.data.bones if context.object.mode != 'EDIT' else context.object.data.edit_bones:
            if b.select:
                b.layers = [x==self.layer for x in range(0, 32)]
        return {'FINISHED'}
classlist.append(DMR_OT_ArmatureSetBoneLayerIndex)

# ---------------------------------------------------------------------------------

class DMR_OT_MoveRigifyLayerRow(bpy.types.Operator):
    bl_idname = "dmr.rigify_mete_move_row"
    bl_label = "Move Rigify Row"
    
    row : bpy.props.IntProperty(name="Row")
    direction : bpy.props.EnumProperty(name="Direction", items=(
        ('DOWN', "Down", "Down"),
        ('UP', "Up", "Up")
    ))
    
    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'ARMATURE'

    def execute(self, context):
        rigifylayers = context.object.data.rigify_layers
        index = self.row
        newindex = max(0, min( (index+1) if self.direction == 'DOWN' else (index-1), len(rigifylayers)-1))
        
        lyrcurr = [lyr for lyr in rigifylayers if lyr.row == index]
        lyrnext = [lyr for lyr in rigifylayers if lyr.row == newindex]
        
        for lyr in lyrcurr:
            lyr.row = newindex
        for lyr in lyrnext:
            lyr.row = index
        return {'FINISHED'}
classlist.append(DMR_OT_MoveRigifyLayerRow)

# =============================================================================

class DMR_PT_Rigify_Pose(bpy.types.Panel):
    bl_label = "Rigify Layers"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Item" # Name of sidebar
    
    @classmethod
    def poll(self, context):
        obj = context.object
        return obj and obj.type == 'ARMATURE' and not obj.data.rigify_layers
    
    def draw(self, context):
        layout = self.layout
        outrig = context.object
        
        layout.operator('dmr.rigify_find_layer_info')
        
        if not outrig.data.get('rigify_layer_data', None):
            return
        
        names = outrig.data['rigify_layer_name']
        data = outrig.data['rigify_layer_data']
        
        layers = [ [names[i]] + list(data[i]) for i in range(0, len(data))]
        sortedlayers = layers[:-1]
        sortedlayers.sort(key=lambda x: x[1])
        sortedlayers.append(layers[-1])
        
        r = layout.row()
        indices = tuple([layers.index(x) for x in layers if x[0]])
        allon = outrig.data.layers[indices[0]]
        togglelayers = tuple([((x in indices and not allon)) or (x==28) for x in range(0, 32)])
        r.operator('dmr.armature_layer_visibility', text='All On' if not allon else 'All Off').layers = togglelayers
        r.operator('dmr.armature_layer_visibility', text='Deform').layers = tuple(x==29 for x in range(0, 32))
        
        # Draw Layer Toggles
        rc = layout.row(align=1)
        c = rc.column(align=1)
        c2 = rc.column(align=1)
        
        lastrow = -1
        rowlayers = []
        
        # Rows
        for i, lyrdata in enumerate(sortedlayers):
            if not lyrdata[0]:
                continue
            
            lyrrow = lyrdata[1]
            
            # New Row
            if lyrrow != lastrow:
                if len(rowlayers) > 1:
                    rowlayerbools = tuple([x in rowlayers for x in range(0, 32)])
                    r2 = c2.row(align=1)
                    r2.operator('dmr.armature_layer_visibility', text='', icon='ZOOM_PREVIOUS').layers = rowlayerbools
                    r2.operator('dmr.armature_layer_toggle', text='', icon='RESTRICT_SELECT_OFF').layers = rowlayerbools
                elif i > 0:
                    c2.label(text="", icon='BLANK1')
                
                if lyrrow - lastrow > 1:
                    c.separator()
                    c2.separator()
                
                r = c.row()
                lastrow = lyrrow
                rowlayers = []
            
            lyrindex = layers.index(lyrdata) if i < len(sortedlayers)-1 else 28
            rowlayers.append(lyrindex)
            
            # Operators
            rr = r.row(align=1)
            rr.prop(outrig.data, 'layers', index=lyrindex, text=lyrdata[0], toggle=1)
            #rr.prop(outrig.data, 'layers', index=lyrindex, text=str(lyrindex), toggle=1)
            rr.operator('dmr.armature_layer_visibility', text='', icon='VIEWZOOM').layers = [x==lyrindex for x in range(0, 32)]
classlist.append(DMR_PT_Rigify_Pose)

# =============================================================================

class DMR_PT_Rigify_Meta(bpy.types.Panel):
    bl_label = "Rigify Layers"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Item" # Name of sidebar
    
    @classmethod
    def poll(self, context):
        obj = context.object
        return obj and obj.type == 'ARMATURE' and obj.data.rigify_layers
    
    def draw(self, context):
        layout = self.layout
        metarig = context.object
        
        rigifylayers = list(metarig.data.rigify_layers)
        
        allon = metarig.data.layers[0]
        layout.operator('dmr.armature_layer_visibility', text='All On' if not allon else 'All Off').layers = tuple([not allon or (x==28) for x in range(0, 32)])
        
        # Draw Layer Toggles
        c = layout.column(align=1)
        lastrow = -1
        
        selectedlayers = [1]*32
        layernamemap = {i: x.name if x.name else "<Unused>" for i,x in enumerate(rigifylayers)}
        usedlayers = [x for x in layernamemap.values() if x != "<Unused>"]
        layerindexmap = {i: usedlayers.index(x) if x != "<Unused>" else -1 for i,x in enumerate(layernamemap.values())}
        
        if metarig.mode == 'EDIT':
            selectedlayers = [0]*32
            
            for b in metarig.data.edit_bones:
                if b.select:
                    for i, l in enumerate(b.layers):
                        selectedlayers[i] |= l
        
        if metarig.mode == 'POSE':
            selectedlayers = [0]*32
            
            for b in metarig.pose.bones:
                if b.bone.select:
                    for i, l in enumerate(b.bone.layers):
                        selectedlayers[i] |= l
        
        sortedlayers = rigifylayers[:-1]
        sortedlayers.sort(key=lambda x: x.row)
        sortedlayers.append(rigifylayers[-1])
        
        # Layers
        for i, lyrdata in enumerate(sortedlayers):
            if not lyrdata.name:
                continue
            
            lyrindex = rigifylayers.index(lyrdata)
            lyrrow = lyrdata.row
            
            # New Row
            if lyrrow != lastrow or (i == len(sortedlayers)-1):
                if lyrrow - lastrow > 1:
                    c.separator()
                
                r = c.row()
                lastrow = lyrrow
                rowcount = 0
            
            rr = r.row(align=1)
            rr.scale_x = 0.9
            
            # Operators
            rrr = rr.row(align=1)
            rrr.active = selectedlayers[lyrindex]
            rrr.prop(metarig.data, 'layers', index=lyrindex, text=str(lyrindex) + ": " + lyrdata.name, toggle=1)
            #rrr.prop(metarig.data, 'layers', index=i, text=str(i), toggle=1)
            rr.operator('dmr.armature_layer_visibility', text='', icon='VIEWZOOM').layers = [x==lyrindex for x in range(0, 32)]
            rr.operator('dmr.armature_layer_assign_index', text='', icon='GREASEPENCIL').layer = lyrindex
            
            cc = rr.column(align=1)
            cc.scale_y = 0.5
            op = cc.operator('dmr.rigify_mete_move_row', text='', icon='TRIA_UP')
            op.row = lyrdata.row
            op.direction = 'UP'
            op = cc.operator('dmr.rigify_mete_move_row', text='', icon='TRIA_DOWN')
            op.row = lyrdata.row
            op.direction = 'DOWN'
        
classlist.append(DMR_PT_Rigify_Meta)

# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
