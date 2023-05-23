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

COLORICON = (
    ( (0.7,0.0,0.0), 'SEQUENCE_COLOR_01', "RED" ),
    ( (0.7,0.5,0.0), 'SEQUENCE_COLOR_02', "ORANGE" ),
    ( (0.7,0.7,0.0), 'SEQUENCE_COLOR_03', "YELLOW" ),
    ( (0.0,1.0,0.0), 'SEQUENCE_COLOR_04', "GREEN" ),
    ( (0.0,0.0,0.7), 'SEQUENCE_COLOR_05', "BLUE" ),
    ( (0.5,0.0,1.0), 'SEQUENCE_COLOR_06', "PURPLE" ),
    ( (0.5,0.2,0.5), 'SEQUENCE_COLOR_07', "PINK" ),
    ( (0.2,0.1,0.0), 'SEQUENCE_COLOR_08', "BROWN" ),
    ( (0.0,0.0,0.0), 'SEQUENCE_COLOR_09', "BLACK" ),
)

def GetColorIcon(color):
    Sqr = lambda x: x*x
    dist = 10.0
    outicon = COLORICON[0][1]
    outname = "None"
    
    for c, icon, name in COLORICON:
        d = sum([Sqr(c[i]-color[i]) for i in range(0, 3)])
        if d < dist:
            dist = d
            outicon = icon
            outname = name
            
    return outicon

def IsRigifyArmature(obj):
    return obj and obj.type == 'ARMATURE' and not obj.data.rigify_layers

def IsRigifyMeta(obj):
    return obj and obj.type == 'ARMATURE' and obj.data.rigify_layers

classlist = []

'# ================================================================================'
'# PROPERTY GROUPS'
'# ================================================================================'

class DMR_Rigify_PropertyPin_Def(bpy.types.PropertyGroup):
    name : bpy.props.StringProperty(name="Bone")
    prop : bpy.props.StringProperty(name="Property")
    
    def CopyFromOther(self, other):
        self.name = other.name
        self.prop = other.prop
classlist.append(DMR_Rigify_PropertyPin_Def)

# ----------------------------------------------------------------------------

class DMR_Rigify_PropertyPin_Master(bpy.types.PropertyGroup):
    armature_object : bpy.props.PointerProperty(type=bpy.types.Object)
    
    size : bpy.props.IntProperty()
    items : bpy.props.CollectionProperty(type=DMR_Rigify_PropertyPin_Def)
    itemindex : bpy.props.IntProperty()
    
    update_mutex : bpy.props.BoolProperty(default=False)
    
    op_add_item : bpy.props.BoolProperty(default=False, update=lambda s,c: s.Update(c))
    op_remove_item : bpy.props.BoolProperty(default=False, update=lambda s,c: s.Update(c))
    op_move_up : bpy.props.BoolProperty(default=False, update=lambda s,c: s.Update(c))
    op_move_down : bpy.props.BoolProperty(default=False, update=lambda s,c: s.Update(c))
    
    def CopyFromOther(self, other, clear=True):
        if clear:
            [self.RemoveAt(len(self.items)-1) for x in self.items]
        
        for otheritem in other.items:
            self.Add().CopyFromOther(otheritem)
    
    def GetActive(self):
        return self.items[self.itemindex] if self.size > 0 else None
    
    def GetItem(self, index):
        return self.items[index] if self.size else None 
    
    def FindItem(self, name):
        return ([x for x in self.items if x.name == name]+[None])[0]
    
    def Add(self):
        item = self.items.add()
        self.size = len(self.items)
        return item
    
    def RemoveAt(self, index):
        if len(self.items) > 0:
            self.items.remove(index)
            self.size = len(self.items)
            
            self.itemindex = max(min(self.itemindex, self.size-1), 0)
    
    def MoveItem(self, index, move_down=True):
        newindex = index + (1 if move_down else -1)
        self.items.move(index, newindex)
    
    def Update(self, context):
        # Add
        if self.op_add_item:
            self.op_add_item = False
            self.Add()
            self.itemindex = self.size-1
        
        # Remove
        if self.op_remove_item:
            self.op_remove_item = False
            self.RemoveAt(self.itemindex)
        
        # Move
        if self.op_move_down:
            self.op_move_down = False
            self.items.move(self.itemindex, self.itemindex+1)
            self.itemindex = max(min(self.itemindex+1, self.size-1), 0)
        
        if self.op_move_up:
            self.op_move_up = False
            self.items.move(self.itemindex, self.itemindex-1)
            self.itemindex = max(min(self.itemindex-1, self.size-1), 0)
classlist.append(DMR_Rigify_PropertyPin_Master)

# ----------------------------------------------------------------------------

class DMR_UL_Rigify_PropertyPin_List(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        c = layout.column(align=1)
        
        r = c.row(align=1)
        
        bonename = item.name
        
        pbones = data.armature_object.pose.bones
        if bonename and item.prop and bonename in pbones.keys() and item.prop in pbones[bonename].keys():
            r.prop_search(item, 'name', data.armature_object.pose, 'bones', text="")
            r.prop(pbones[item.name], '["%s"]' % item.prop)
        else:
            r.prop_search(item, 'name', data.armature_object.pose, 'bones', text="")
            r.prop(item, 'prop', text="")
        
        rr = r.column(align=1)
        rr.scale_y = 0.5
        rr.prop(active_data, 'op_move_up', text="", index=index, icon_only=True, icon='TRIA_UP')
        rr.prop(active_data, 'op_move_down', text="", index=index, icon_only=True, icon='TRIA_DOWN')
        r.row().prop(active_data, 'op_remove_item', text="", index=index, icon_only=True, icon='REMOVE')
classlist.append(DMR_UL_Rigify_PropertyPin_List)

'# ================================================================================'
'# OPERATORS'
'# ================================================================================'

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
            
            layerdata = []
            groupcoloricon = {i+1: GetColorIcon(group.normal) for i,group in enumerate(metarig.data.rigify_colors)}
            
            outrig.data['rigify_layer_data'] = [
                [ 
                    lyr.row, 
                    i,
                    int(groupcoloricon[lyr.group][-1]) if (lyr.group in groupcoloricon.keys()) else 9
                ]
                for i, lyr in enumerate(metarig.data.rigify_layers) if lyr.name
            ]
            
            outrig.data['rigify_layer_data'][-1][0] = 28
            
            outrig.data['rigify_layer_name'] = [
                lyr.name
                for i, lyr in enumerate(metarig.data.rigify_layers) if lyr.name
            ]
            
            outrig.data.rigify_prop_pin.armature_object = outrig
        else:
            self.report({'WARNING'}, 'No meta rig found that targets active object')
        
        return {'FINISHED'}
classlist.append(DMR_OT_Rigify_FindLayerInfo)

# -------------------------------------------------------------------------------

class DMR_OT_Rigify_RetargetMetaDrivers(bpy.types.Operator):
    bl_idname = "dmr.rigify_retarget_drivers"
    bl_label = "Retarget Drivers"
    
    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'ARMATURE'

    def execute(self, context):
        print("> Retargeting Drivers...")
        rigobj =  bpy.context.active_object

        for obj in rigobj.children:
            if not obj.animation_data:
                continue
            
            for fc in obj.animation_data.drivers:
                for v in fc.driver.variables:
                    for t in v.targets:
                        meta = t.id
                        if meta and meta.type == 'ARMATURE' and meta.data.get('rigify_target_rig', None) == rigobj:
                            print("%s: %s -> %s" % (obj.name, t.id.name, rigobj.name))
                            t.id = rigobj
        
        return {'FINISHED'}
classlist.append(DMR_OT_Rigify_RetargetMetaDrivers)

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
    bl_idname = "dmr.armature_layer_set_index"
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

class DMR_OT_ArmatureToggleBoneLayerIndex(bpy.types.Operator):
    bl_idname = "dmr.armature_layer_toggle_index"
    bl_label = "Set Bone Layer Index"
    bl_options = {'REGISTER', 'UNDO'}
    
    layer : bpy.props.IntProperty(name='Layer Index', min=0, max=31)
    
    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'ARMATURE'

    def execute(self, context):
        bones = context.object.data.bones if context.object.mode != 'EDIT' else context.object.data.edit_bones
        bones = [b for b in bones if b.select]
        value = sum([x for b in bones for i,x in enumerate(b.layers) if i == self.layer]) == 0
        
        print("value=", value)
        for b in bones:
            b.layers = [value if (i==self.layer) else x for i,x in enumerate(b.layers)]
            print(b.name, "".join(["X" if x else "O" for x in b.layers]))
        return {'FINISHED'}
classlist.append(DMR_OT_ArmatureToggleBoneLayerIndex)

# ---------------------------------------------------------------------------------

class DMR_OT_MoveRigifyLayerRow(bpy.types.Operator):
    bl_idname = "dmr.rigify_meta_move_row"
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

# ---------------------------------------------------------------------------------

class DMR_OT_RigifyTransferBoneProperties(bpy.types.Operator):
    bl_label = "Move Rigify Row"
    bl_idname = "dmr.rigify_transfer_bone_properties"
    
    source : bpy.props.EnumProperty(name='Source Rig', items=lambda s,c: [
        (x.name, x.name, x.name) for x in bpy.data.objects if (IsRigifyArmature(x) and x.data.rigify_prop_pin.items)
        ])
    
    target : bpy.props.EnumProperty(name='Target Rig', items=lambda s,c: [
        (x.name, x.name, x.name) for x in bpy.data.objects if (IsRigifyArmature(x))
        ])
    
    prop : bpy.props.StringProperty(name="Prop")
    
    def invoke(self, context, event):
        if IsRigifyArmature(context.object):
            self.target = context.object.name
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'source')
        layout.prop(self, 'target')
        layout.prop_search(self, 'prop', bpy.data.objects[self.source].data.rigify_prop_pin, 'items')
    
    def execute(self, context):
        source = bpy.data.objects[self.source].data.rigify_prop_pin
        target = bpy.data.objects[self.target].data.rigify_prop_pin
        
        if self.prop == "":
            target.CopyFromOther(source)
            
            self.report({'INFO'}, "Copied prop pins to rig")
        else:
            target.Add().CopyFromOther(source.FindItem(self.prop))
            self.report({'INFO'}, "Copied prop pin to rig")
        
        return {'FINISHED'}
classlist.append(DMR_OT_RigifyTransferBoneProperties)

# ---------------------------------------------------------------------------------

class DMR_OT_QuickPoseBoneConstraint(bpy.types.Operator):
    bl_label = "Quick Pose Bone Constraint"
    bl_idname = "dmr.quick_pose_bone_constraint"
    
    target : bpy.props.StringProperty(name="Target")
    target_bone : bpy.props.StringProperty(name="Target Bone")
    type : bpy.props.EnumProperty(name="Constraint Type", items=(
        ('CHILD_OF', "Child Of", "Child Of"),
        #('TRACK_TO', "Track To", "Track To")
    ))
    
    @classmethod
    def poll(self, context):
        return context.object and IsRigifyArmature(context.object)
    
    def invoke(self, context, event):
        if IsRigifyArmature(context.object):
            self.target = context.object.name
            if "DEF-hip" in context.object.pose.bones.keys():
                self.target_bone = "DEF-hip"
            elif "DEF-spine" in context.object.pose.bones.keys():
                self.target_bone = "DEF-spine"
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        obj = context.object
        c = layout.column()
        
        c.prop(self, 'type')
        c.prop_search(self, 'target', bpy.data, 'objects')
        
        if self.target in bpy.data.objects.keys():
            obj = bpy.data.objects[self.target]
            if obj.type == 'ARMATURE':
                c.prop_search(self, 'target_bone', obj.pose, 'bones')
    
    def execute(self, context):
        obj = context.object
        for pb in obj.pose.bones:
            if pb.bone.select:
                c = pb.constraints.new(type=self.type)
                c.name += " - Bake"
                
                if self.type == 'CHILD_OF':
                    c.target = bpy.data.objects[self.target]
                    c.subtarget = self.target_bone
        
        return {'FINISHED'}
classlist.append(DMR_OT_QuickPoseBoneConstraint)

# ---------------------------------------------------------------------------------

class DMR_OT_RigifyMetaSetFKTweakLayers(bpy.types.Operator):
    bl_label = "Auto Set FK Tweak Layers"
    bl_idname = "dmr.rigify_meta_auto_sub_layers"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(self, context):
        return IsRigifyMeta(context.object) and context.object.mode == 'POSE'
    
    def execute(self, context):
        bpy.ops.object.mode_set(mode='OBJECT')
        
        for pb in context.object.pose.bones:
            if pb.bone.select:
                print(pb.name)
                pblayers = pb.bone.layers
                lyrindex = 0
                for i,x in enumerate(pblayers):
                    if x:
                        lyrindex = i
                        break
                
                
                pb.rigify_parameters.fk_layers = tuple([x==(lyrindex+1) for x in range(0, 32)])
                pb.rigify_parameters.tweak_layers = tuple([x==(lyrindex+2) for x in range(0, 32)])
                
                print(list(pb.rigify_parameters.fk_layers))
                print(list(pb.rigify_parameters.tweak_layers))
        
        bpy.ops.object.mode_set(mode='POSE')
        
        return {'FINISHED'}
classlist.append(DMR_OT_RigifyMetaSetFKTweakLayers)

# ---------------------------------------------------------------------------------


'# ================================================================================'
'# PANELS'
'# ================================================================================'

class DMR_PT_Rigify_Pose(bpy.types.Panel):
    bl_label = "Rigify Layers"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Item" # Name of sidebar
    
    @classmethod
    def poll(self, context):
        return IsRigifyArmature(context.object)
    
    def draw(self, context):
        layout = self.layout
        outrig = context.object
        
        r = layout.row()
        r.operator('dmr.rigify_find_layer_info')
        r.operator('dmr.rigify_retarget_drivers')
        
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
        allcontrol = tuple([((not allon) or (x==28)) and x < 28 for x in range(0, 32)])
        togglelayers = tuple([((not allon) or (x==28)) and x <= 28 for x in range(0, 32)])
        r.operator('dmr.armature_layer_visibility', text='All On' if not allon else 'All Off').layers = togglelayers
        r.operator('dmr.armature_layer_visibility', text='Deform').layers = tuple([x==29 for x in range(0, 32)])
        
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
            lyrindex = lyrdata[2]
            lyricon = lyrdata[3]
            
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
            
            
            rowlayers.append(lyrindex)
            
            # Operators
            rr = r.row(align=1)
            
            rr.prop(outrig.data, 'layers', index=lyrindex, text=lyrdata[0], toggle=1, icon='SEQUENCE_COLOR_0'+str(lyricon) if lyricon > 0 else 'BLANK1')
            #rr.prop(outrig.data, 'layers', index=lyrindex, text=str(lyrindex), toggle=1)
            rr.operator('dmr.armature_layer_visibility', text='', icon='VIEWZOOM').layers = [x==lyrindex for x in range(0, 32)]
classlist.append(DMR_PT_Rigify_Pose)

# ---------------------------------------------------------------------------------

class DMR_PT_Rigify_Pose_BoneProperties(bpy.types.Panel):
    bl_label = "Rigify Bone Properties"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Item" # Name of sidebar
    bl_parent_id = 'DMR_PT_Rigify_Pose'
    
    def draw(self, context):
        layout = self.layout
        outrig = context.object
        
        if not outrig.data.get('rigify_layer_data', None):
            layout.operator('dmr.rigify_find_layer_info')
            return
        
        # Property Pins
        if outrig.mode != 'EDIT':
            proppins = outrig.data.rigify_prop_pin
            
            if proppins.armature_object:
                r = layout.row()
                c = r.column(align=1)
                c.template_list(
                    "DMR_UL_Rigify_PropertyPin_List", "", 
                    proppins, "items", 
                    proppins, "itemindex", 
                    rows=3)
              
                c = r.column(align=1)
                c.prop(proppins, 'op_add_item', text="", icon='ADD')
                c.prop(proppins, 'op_remove_item', text="", icon='REMOVE')
                
                c.separator()
                
                c.operator('dmr.rigify_transfer_bone_properties', text="", icon='PASTEDOWN')
classlist.append(DMR_PT_Rigify_Pose_BoneProperties)

# ---------------------------------------------------------------------------------

class RigifyPanelSuper(bpy.types.Panel):
    bl_label = "Rigify Bone"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Item" # Name of sidebar
    
    @classmethod
    def poll(self, context):
        obj = context.object
        return obj and obj.type == 'ARMATURE' and obj.data.rigify_layers

class DMR_PT_Rigify_Meta(RigifyPanelSuper, bpy.types.Panel):
    bl_label = "Rigify Layers"
    
    @classmethod
    def poll(self, context):
        return IsRigifyMeta(context.object)
    
    def draw(self, context):
        layout = self.layout
        metarig = context.object
        
        rigifylayers = list(metarig.data.rigify_layers)
        
        allon = metarig.data.layers[0]
        
        r = layout.row()
        r.operator('dmr.armature_layer_visibility', text='All On' if not allon else 'All Off').layers = tuple([not allon or (x==28) for x in range(0, 32)])
        r.prop(context.scene, 'rigify_meta_layer_mode')
        
        # Draw Layer Toggles
        c = layout.column(align=1)
        lastrow = -1
        
        selectedlayers = [1]*32
        bonelayerindices = []
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
                        if l:
                            bonelayerindices.append(i)
        
        sortedlayers = rigifylayers[:-1]
        sortedlayers.sort(key=lambda x: x.row)
        sortedlayers.append(rigifylayers[-1])
        
        #editlayers = context.scene.rigify_meta_layer_mode;
        
        # Layers
        for i, lyrdata in enumerate(sortedlayers):
            if lyrdata.name == "":
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
            rr.scale_x = 0.8
            
            # Operators
            rrr = rr.row(align=1)
            rrr.active = selectedlayers[lyrindex]
            
            boolname = str(lyrindex) + ": " + lyrdata.name
            
            rrr.prop(metarig.data, 'layers', index=lyrindex, text=boolname, toggle=1)
            
            rr.operator('dmr.armature_layer_toggle_index', text="", icon='CHECKBOX_HLT' if (lyrindex in bonelayerindices) else 'CHECKBOX_DEHLT').layer = lyrindex
            
            rr.operator('dmr.armature_layer_visibility', text='', icon='VIEWZOOM').layers = [x==lyrindex for x in range(0, 32)]
            ##rr.operator('dmr.armature_layer_assign_index', text='', icon='GREASEPENCIL').layer = lyrindex
            
            cc = rr.column(align=1)
            cc.scale_y = 0.5
            op = cc.operator('dmr.rigify_meta_move_row', text='', icon='TRIA_UP')
            op.row = lyrdata.row
            op.direction = 'UP'
            op = cc.operator('dmr.rigify_meta_move_row', text='', icon='TRIA_DOWN')
            op.row = lyrdata.row
            op.direction = 'DOWN'
classlist.append(DMR_PT_Rigify_Meta)

# ---------------------------------------------------------------------------------

class DMR_PT_Rigify_Meta_Bone(RigifyPanelSuper, bpy.types.Panel):
    bl_label = "Rigify Bone"
    bl_parent_id = 'DMR_PT_Rigify_Meta'
    
    def draw(self, context):
        if context.object.mode == 'POSE':
            bpy.types.BONE_PT_rigify_buttons.draw(self, context)
classlist.append(DMR_PT_Rigify_Meta_Bone)

'# ================================================================================'
'# REGISTER'
'# ================================================================================'

def register():
    for c in classlist:
        bpy.utils.register_class(c)
    
    bpy.types.Armature.rigify_prop_pin = bpy.props.PointerProperty(type=DMR_Rigify_PropertyPin_Master)
    bpy.types.Scene.rigify_meta_layer_mode = bpy.props.BoolProperty(name="Edit Bone Layers", default=False)

def unregister():
    for c in classlist[::-1]:
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
