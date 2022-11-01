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
            
            outrig.data['rigify_layer_data'][-1][0] = 32
            
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
    
    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'ARMATURE'

    def execute(self, context):
        context.active_object.data.layers = tuple(self.layers)
        return {'FINISHED'}
classlist.append(DMR_OT_ArmatureSetLayerVisibility)

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

# =============================================================================

class DMR_PT_Rigify_Pose(bpy.types.Panel):
    bl_label = "Rigify Layers"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Item" # Name of sidebar
    
    @classmethod
    def poll(self, context):
        obj = context.object
        return obj and obj.type == 'ARMATURE' and obj.data.get('rigify_layer_data', None)
    
    def draw(self, context):
        layout = self.layout
        outrig = context.object
        
        names = outrig.data['rigify_layer_name']
        data = outrig.data['rigify_layer_data']
        
        layers = [ [names[i]] + list(data[i]) for i in range(0, len(data))]
        sortedlayers = layers[:]
        sortedlayers.sort(key=lambda x: x[1])
        
        allon = outrig.data.layers[0]
        layout.operator('dmr.armature_layer_visibility', text='All On' if not allon else 'All Off').layers = tuple([not allon or (x==28) for x in range(0, 32)])
        
        # Draw Layer Toggles
        c = layout.column(align=1)
        lastrow = -1
        
        for i, lyrdata in enumerate(sortedlayers):
            if not lyrdata[0]:
                continue
            
            lyrindex = layers.index(lyrdata)
            
            if lyrdata[1] != lastrow:
                r = c.row()
                lastrow = lyrdata[1]
            
            rr = r.row(align=1)
            rr.prop(outrig.data, 'layers', index=lyrindex, text=lyrdata[0], toggle=1)
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
        
        sortedlayers = rigifylayers[:]
        sortedlayers.sort(key=lambda x: x.row)
        
        for i, lyrdata in enumerate(sortedlayers[:-1]):
            if not lyrdata.name:
                continue
            lyrindex = rigifylayers.index(lyrdata)
            
            if lyrdata.row != lastrow or (i == len(rigifylayers)-1):
                r = c.row()
                lastrow = lyrdata.row
            
            rr = r.row(align=1)
            rr.scale_x = 0.9
            
            rrr = rr.row(align=1)
            rrr.active = selectedlayers[lyrindex]
            rrr.prop(metarig.data, 'layers', index=lyrindex, text=str(lyrindex) + ": " + lyrdata.name, toggle=1)
            #rrr.prop(metarig.data, 'layers', index=i, text=str(i), toggle=1)
            rr.operator('dmr.armature_layer_visibility', text='', icon='VIEWZOOM').layers = [x==lyrindex for x in range(0, 32)]
            rr.operator('dmr.armature_layer_assign_index', text='', icon='GREASEPENCIL').layer = lyrindex
        
        # Active Bone
        
        pb = None
        if context.active_pose_bone:
            pb = context.active_pose_bone
        elif context.active_bone:
            pb = metarig.pose.bones[context.active_bone.name]
        
        if pb:
            c = layout.box().column(align=1)
            c.label(text=pb.name, icon='BONE_DATA')
            
            for i,l in enumerate(pb.bone.layers):
                if l:
                    c.operator('dmr.armature_layer_assign_index', text=str(layerindexmap[i])+": "+layernamemap[i], icon='GREASEPENCIL').layer = i
            
            if pb.rigify_parameters.fk_layers_extra:
                if sum(pb.rigify_parameters.fk_layers):
                    i = [i for i,l in enumerate(pb.rigify_parameters.fk_layers) if l][0]
                    c.prop(pb.rigify_parameters, 'fk_layers', text="FK | "+str(layerindexmap[i])+": "+layernamemap[i])
                else:
                    c.prop(pb.rigify_parameters, 'fk_layers', text="FK | (None)")
            
            if pb.rigify_parameters.tweak_layers_extra:
                if sum(pb.rigify_parameters.tweak_layers):
                    i = [i for i,l in enumerate(pb.rigify_parameters.tweak_layers) if l][0]
                    c.prop(pb.rigify_parameters, 'tweak_layers', text="Tweak | "+str(layerindexmap[i])+": "+layernamemap[i])
                else:
                    c.prop(pb.rigify_parameters, 'tweak_layers', text="Tweak | (None)")
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
