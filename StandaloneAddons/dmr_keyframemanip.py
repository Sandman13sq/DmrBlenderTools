bl_info = {
    'name': 'Keyframe Manip',
    'description': 'Operators to manipulate keyframes, such as offsetting bone keyframes to create a wave effect on a tail.',
    'author': 'Dreamer13sq',
    'version': (1, 0),
    'blender': (3, 0, 0),
    'category': 'Animation',
    'support': 'COMMUNITY',
    'doc_url': 'https://github.com/Dreamer13sq/DmrBlenderTools/wiki/Keyframe-Manip'
}

import bpy
import random
import mathutils
import math

def GetChainRoot(b):
    return GetChainRoot(b.parent) if (b.parent and b.parent.select and b.use_connect) else b
def GetBoneChain(b):
    for c in b.children:
        if c.select:
            return [b] + GetBoneChain(c)
    return [b]

classlist = []

'# =========================================================================================================================='
'# OPERATORS'
'# =========================================================================================================================='

class DMR_OP_KeyframeManip_Wave(bpy.types.Operator):
    bl_label = "Keyframe Manip - Wave"
    bl_idname = 'dmr.keyframe_manip_wave'
    bl_description = 'Offsets Keyframes by order of bone chain';
    bl_options = {'REGISTER', 'UNDO'}
    
    channel_shift: bpy.props.IntProperty(
        name="Chain Shift", default=1,
        description="Number of frames to shift by chain index",
    )
    
    position_shift: bpy.props.IntProperty(
        name="Keyframe Shift", default=1,
        description="Number of frames to shift by down the chain",
    )
    
    overwrite : bpy.props.BoolProperty(
        name="Overwrite", default=False,
        description="Anchors values to lowest keyframe before changing wave",
    )
    
    def execute(self, context):
        obj = context.object
        armature = obj.data
        bones = obj.data.bones
        pbones = obj.pose.bones
        
        obj.update_from_editmode()
        
        # Find chains
        chains = [
            [bones[b.name] for b in c.bones if bones[b.name].select]
            for c in armature.bone_chains
        ]
        
        usedbones = [bones[b.name] for c in chains for b in c]
        targets = [c[0] for c in chains if len(c)]
        
        for b in bones:
            if b not in usedbones:
                if b.select:
                    rootbone = GetChainRoot(b)
                    chain = GetBoneChain(rootbone)
                    
                    if rootbone not in usedbones:
                        targets.append(rootbone.name)
                        usedbones += chain
                        chains += [chain]
        
        chains = [c for c in chains if len(c)]
        
        # Find curves
        action = obj.animation_data.action
        fcurves = tuple(action.fcurves)
        
        fcurvebundles = {
            b.name: tuple([fc for fc in fcurves if '"'+b.name+'"' in fc.data_path if (not fc.hide and not fc.lock)])
            for b in usedbones
        }
        
        channel_shift = self.channel_shift
        position_shift = self.position_shift
        
        foffset = 0
        if self.overwrite:
            foffset += min([k.co_ui[0] for bundle in fcurvebundles.values() for fc in bundle for k in fc.keyframe_points])
        
        # Set keyframe values
        for chainindex,chain in enumerate(chains):
            bonelink = [pbones[b.name] for b in chain]
            print([b.name for b in bonelink])
            
            for chainpos,b in enumerate(bonelink):
                for fc in fcurvebundles[b.name]:
                    kpoints = tuple([k for k in fc.keyframe_points if k.select_control_point])
                    k0 = kpoints[0]
                    
                    if self.overwrite:
                        for k in kpoints[::-1]:
                            k.co_ui[0] -= k0.co_ui[0]
                    
                    for k in kpoints:
                        k.co_ui[0] += foffset + channel_shift*chainindex + chainpos*position_shift
        
        return {'FINISHED'}
classlist.append(DMR_OP_KeyframeManip_Wave)

# =============================================================================

class DMR_OP_KeyframeManip_WaveCreate(bpy.types.Operator):
    bl_label = "Keyframe Manip - Create Wave"
    bl_idname = 'dmr.keyframe_manip_wave_create'
    bl_description = 'Offsets Keyframes by order of bone chain';
    bl_options = {'REGISTER', 'UNDO'}
    
    overwrite : bpy.props.BoolProperty(
        name="Overwrite", default=True,
        description="Overwrite current transform of bones before keyframing",
    )
    
    frame_offset : bpy.props.FloatProperty(
        name="Frame Offset", default=0, step=1,
        description="Total offset of wave",
    )
    
    chain_offset : bpy.props.FloatProperty(
        name="Chain Offset", default=1,
        description="Offset per chain",
    )
    
    bone_offset : bpy.props.FloatProperty(
        name="Bone Offset", default=4,
        description="Offset per bone in chain",
    )
    
    frequency : bpy.props.IntProperty(
        name="Frequency", default=1, min=1,
        description="Number of times wave occurs in action",
    )
    
    translation_enabled : bpy.props.BoolProperty(name="Translation Enabled", default=True)
    
    rotation : bpy.props.FloatVectorProperty(name="Rotation Angles", size=6, default=[0.0]*6, subtype='EULER')
    rotation_toggle : bpy.props.BoolVectorProperty(name="Rotation Toggle", size=6, default=[True]*6)
    rotation_enabled : bpy.props.BoolProperty(name="Rotation Enabled", default=True)
    
    scale : bpy.props.FloatVectorProperty(name="Scale", size=6, default=[1.0]*6)
    scale_toggle : bpy.props.BoolVectorProperty(name="Scale Toggle", size=6, default=[True]*6)
    scale_enabled : bpy.props.BoolProperty(name="Scale Enabled", default=True)
    
    # Update --------------------------------------------------------------------------------
    mutex : bpy.props.BoolProperty(default=False)
    
    def Update(self, context):
        if self.mutex:
            return
        
        self.mutex = True
        
        if self.op_peak_to_trough:
            self.op_peak_to_trough = False
            r1 = (3,6)
            r2 = (0,3)
            self.rotation[r1[0]:r1[1]] = self.rotation[r2[0]:r2[1]]
            self.rotation_toggle[r1[0]:r1[1]] = self.rotation_toggle[r2[0]:r2[1]]
            
            self.scale[r1[0]:r1[1]] = self.scale[r2[0]:r2[1]]
            self.scale_toggle[r1[0]:r1[1]] = self.scale_toggle[r2[0]:r2[1]]
        
        if self.op_trough_to_peak:
            self.op_trough_to_peak = False
            r1 = (0,3)
            r2 = (3,6)
            self.rotation[r1[0]:r1[1]] = self.rotation[r2[0]:r2[1]]
            self.rotation_toggle[r1[0]:r1[1]] = self.rotation_toggle[r2[0]:r2[1]]
            
            self.scale[r1[0]:r1[1]] = self.scale[r2[0]:r2[1]]
            self.scale_toggle[r1[0]:r1[1]] = self.scale_toggle[r2[0]:r2[1]]
        
        if self.op_swap_arcs:
            self.op_swap_arcs = False
            indices = (3,4,5,0,1,2)
            
            self.rotation = [self.rotation[i] for i in indices]
            self.rotation_toggle = [self.rotation_toggle[i] for i in indices]
            
            self.scale = [self.scale[i] for i in indices]
            self.scale_toggle = [self.scale_toggle[i] for i in indices]
        
        self.mutex = False
    
    op_peak_to_trough : bpy.props.BoolProperty(default=False, update=Update)
    op_trough_to_peak : bpy.props.BoolProperty(default=False, update=Update)
    op_swap_arcs : bpy.props.BoolProperty(default=False, update=Update)
    
    # ----------------------------------------------------------------------------------------
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'overwrite')
        layout.prop(self, 'frequency')
        
        r = layout.row(align=1)
        r.prop(self, 'frame_offset')
        r.prop(self, 'chain_offset')
        r.prop(self, 'bone_offset')
        
        r = layout.row(align=1)
        r.prop(self, 'translation_enabled', text="Loc", toggle=True)
        r.prop(self, 'rotation_enabled', text="Rot", toggle=True)
        r.prop(self, 'scale_enabled', text="Scale", toggle=True)
        
        # Peak
        for header, indices in (("Peak", (0,1,2)), ("Trough", (3,4,5))):
            b = layout.box().column(align=1)
            
            r = b.row()
            r.label(text="== %s ==" % header)
            if indices[0] == 0:
                r.prop(self, 'op_peak_to_trough', text="Copy To Trough", icon='TRIA_DOWN')
            else:
                r.prop(self, 'op_trough_to_peak', text="Copy To Peak", icon='TRIA_UP')
            
            r.prop(self, 'op_swap_arcs', text="", icon='UV_SYNC_SELECT')
            
            r = b.row(align=1)
            r.enabled = self.rotation_enabled
            r.label(text="Rot:")
            for i in indices:
                r.prop(self, 'rotation', text="", index=i)
            
            r = b.row(align=0)
            r.enabled = self.scale_enabled
            r.label(text="Scale:")
            for i in indices:
                rr = r.row(align=1)
                rrr = rr.row(align=1)
                rrr.scale_x = 0.3
                rrr.prop(self, 'scale_toggle', text="XYZ"[i%3], index=i, toggle=True)
                rr.prop(self, 'scale', text="", index=i)
    
    def execute(self, context):
        sc = context.scene
        obj = context.object
        action = obj.animation_data.action
        fcurves = action.fcurves
        frame_range = list(action.frame_range)
        
        frameoffset = self.frame_offset
        framechainoffset = self.chain_offset
        frameboneoffset = self.bone_offset
        
        frame_range[1] /= self.frequency
        
        angles = (10, 0, 0)
        rot = mathutils.Euler(((x) for x in self.rotation[0:3]), 'XYZ')
        
        transformrotation = [
            mathutils.Euler((self.rotation[0:3]), 'XYZ'),
            mathutils.Euler((self.rotation[3:6]), 'XYZ'),
        ]
        
        transformscale = (
            self.scale[0:3],
            self.scale[3:6]
        )
        
        def GetBoneChain(b, out=[]):
            out.append(b)
            for c in b.children:
                GetBoneChain(c, out)
            return out
        
        targetbones = [pb for pb in obj.pose.bones if pb.bone.select]
        rootbones = [pb for pb in targetbones if (not pb.parent or not pb.parent.bone.select)]
        chains = [GetBoneChain(pb, []) for pb in rootbones]
        
        pbscale = {pb: (1,1,1) if self.overwrite else pb.scale for pb in targetbones}
        pbquat = {pb: (1,0,0,0) if self.overwrite else pb.rotation_quaternion for pb in targetbones}
        pbeuler = {pb: (0,0,0) if self.overwrite else pb.rotation_euler for pb in targetbones}
        
        # Set Rotation and Keyframes
        for chainindex, chain in enumerate(chains):
            for boneindex, pb in enumerate(chain):
                # Insert Keyframes
                netoffset = int(
                    framechainoffset * chainindex + 
                    frameboneoffset * boneindex + 
                    frameoffset
                    )
                
                targetframes = [ 
                    [int(frame_range[0]) + netoffset, int(frame_range[1]) + netoffset], 
                    [int(frame_range[0]+frame_range[1]) // 2 + netoffset] 
                ]
                
                # Rotation
                if self.rotation_enabled:
                    use_quaternion = pb.rotation_mode == 'QUATERNION'
                    varstring = 'rotation_quaternion' if use_quaternion else 'rotation_euler'
                    
                    # Find Fcurves
                    curves = [
                        fcurves.find(pb.path_from_id(varstring), index=i)
                        for i in range(0, 4)
                        ]
                    
                    # Create missing Fcurves
                    curves = [
                        fc if fc else fcurves.new(pb.path_from_id(varstring), index=i, action_group=pb.name)
                        for i, fc in enumerate(curves)
                    ]
                    
                    # Make Cyclic
                    if 1:
                        [fc.modifiers.new('CYCLES') for fc in curves if 'CYCLES' not in [m.type for m in fc.modifiers]]
                    
                    # Clear previous keyframes
                    for fc in curves:
                        fc.keyframe_points.clear()
                    
                    # Insert Quaternion
                    if use_quaternion:
                        for transformindex, flist in enumerate(targetframes):
                            pb.rotation_quaternion = pbquat[pb]
                            pb.rotation_quaternion.rotate(transformrotation[transformindex])
                            for f in flist:
                                pb.keyframe_insert(varstring, frame=f)
                    
                    # Insert Euler
                    else:
                        for transformindex, flist in enumerate(targetframes):
                            pb.rotation_euler = pbeuler[pb]
                            pb.rotation_euler.rotate(transformrotation[transformindex])
                            
                            for f in flist:
                                for i in [i for i in range(0, 3) if self.rotation_toggle[i] ]:
                                    pb.keyframe_insert(varstring, frame=f, index=i)
                    
                # Scale
                if self.scale_enabled:
                    varstring = 'scale'
                    
                    # Find Fcurves
                    curves = [
                        fcurves.find(pb.path_from_id(varstring), index=i)
                        for i in range(0, 3)
                        ]
                    
                    # Create missing Fcurves
                    curves = [
                        fc if fc else fcurves.new(pb.path_from_id(varstring), index=i, action_group=pb.name)
                        for i, fc in enumerate(curves)
                    ]
                    
                    # Make Cyclic
                    if 1:
                        [fc.modifiers.new('CYCLES') for fc in curves if 'CYCLES' not in [m.type for m in fc.modifiers]]
                    
                    # Clear previous keyframes
                    for fc in curves:
                        fc.keyframe_points.clear()
                    
                    # Insert Keyframes
                    for transformindex, flist in enumerate(targetframes):
                        pb.scale = [x*y for x,y in zip(pbscale[pb], transformscale[transformindex])]
                        
                        for f in flist:
                            for i in [i for i in ((0,1,2),(3,4,5))[transformindex] if self.scale_toggle[i] ]:
                                pb.keyframe_insert(varstring, frame=f, index=i%3)
        
        return {'FINISHED'}
classlist.append(DMR_OP_KeyframeManip_WaveCreate)

# =============================================================================

class DMR_OP_KeyframeManip_RandomFrame(bpy.types.Operator):
    bl_label = "Keyframe Manip - Random Frame"
    bl_idname = 'dmr.keyframe_manip_random_frame'
    bl_description = 'Offsets selected keyframe positions randomly';
    bl_options = {'REGISTER', 'UNDO'}
    
    seed: bpy.props.IntProperty(
        name="Random Seed", default=0,
        description="Seed to use for shuffling keyframe positions",
    )
    
    strength: bpy.props.FloatProperty(
        name='Strength', default=3.0,
        description='Amount to move keyframes'
    )
    
    split_channel_index: bpy.props.BoolProperty(
        name='Split Channel Index', default=False,
        description='Calculate different values per channel index'
    )
    
    ignore_end_keyframes: bpy.props.BoolProperty(
        name='Ignore End Keyframes', default=True,
        description='Skips starting and ending keyframes of channels'
    )
    
    snap_positions: bpy.props.BoolProperty(
        name='Snap Positions', default=True,
        description='Round new positions to nearest whole number'
    )
    
    def execute(self, context):
        # Settings
        strength = self.strength
        doround = self.snap_positions
        dosplit = self.split_channel_index
        skipends = self.ignore_end_keyframes
        
        random.seed(self.seed)
        
        obj = context.object
        armature = obj.data
        bones = obj.data.bones
        
        obj.update_from_editmode()
        
        action = obj.animation_data.action
        selectedbonenames = [b.name for b in bones if b.select]
        groupedcurves = {}
        
        # Group curves by datapath
        for fc in action.fcurves:
            if not fc.hide and not fc.lock:
                dp = fc.data_path
                name = dp[dp.find('"')+1:dp.rfind('"')]
                if name in selectedbonenames:
                    if dp not in groupedcurves:
                        groupedcurves[dp] = []
                    groupedcurves[dp].append(fc)
        
        # Consistent Channel indices
        if not dosplit:
            for dp, g in groupedcurves.items():
                rmap = {}
                for fc in g:
                    kend = len(fc.keyframe_points)-1
                    for i, k in enumerate(fc.keyframe_points):
                        if skipends and (i == 0 or i == kend):
                            continue
                        if k.select_control_point:
                            if k.co[0] not in rmap:
                                rmap[k.co[0]] = (random.random()*2.0-1.0)*strength
                            k.co[0] += rmap[k.co[0]]
                            if doround:
                                k.co[0] = round(k.co[0])
        # Split channel indices
        else:
            for fc in [x for g in groupedcurves.values() for x in g]:
                kend = len(fc.keyframe_points)-1
                for i, k in enumerate(fc.keyframe_points):
                    if skipends and (i == 0 or i == kend):
                        continue
                    if k.select_control_point:
                        r = (random.random()*2.0-1.0) * strength
                        k.co[0] += r
                        if doround:
                            k.co[0] = round(k.co[0])
                            
        return {'FINISHED'}
classlist.append(DMR_OP_KeyframeManip_RandomFrame)

# =============================================================================

class DMR_OP_KeyframeManip_AdjustWave(bpy.types.Operator):
    bl_label = "Keyframe Manip - Adjust Wave Amplitude"
    bl_idname = 'dmr.keyframe_manip_adjust_wave'
    bl_description = '';
    bl_options = {'REGISTER', 'UNDO'}
    
    midpoint : bpy.props.FloatProperty(name="Midpoint", default=0.5, min=0.0, max=1.0)
    
    def execute(self, context):
        action = obj.animation_data.action
        selectedbonenames = [b.name for b in bones if b.select]
        
        midpoint = self.midpoint
        
        for fc in tuple(action.fcurves):
            if len(fc.keyframe_points) == 3:
                k = tuple(keyframe_points)
                k[1].co_ui[0] = k[0].co_ui[0]+(k[0].co_ui[1]-k[0].co_ui[0])*midpoint
classlist.append(DMR_OP_KeyframeManip_AdjustWave)

# =============================================================================

class DMR_OP_BoneChainMove(bpy.types.Operator):
    bl_idname = "dmr.bone_chain_move"
    bl_label = "Move Bone Chain"
    bl_description = "Moves bone chain up or down on list"
    bl_options = {'REGISTER', 'UNDO'}
    
    direction : bpy.props.EnumProperty(
        name="Direction",
        description='Direction to move layer',
        items=(
            ('UP', 'Up', 'Move vertex color layer up'),
            ('DOWN', 'Down', 'Move vertex color layer down'),
            ('TOP', 'Top', 'Move vertex color layer to top of list'),
            ('BOTTOM', 'Bottom', 'Move vertex color layer to bottom of list'),
        )
    )
    
    @classmethod
    def poll(self, context):
        return context.object and context.object.type == 'ARMATURE'
    
    def execute(self, context):
        armature = context.armature
        bonechains = armature.bone_chains
        index = armature.bone_chains_index
        newindex = index
        n = len(bonechains)
        
        if self.direction == 'UP':
            newindex = index-1 if index > 0 else n
        elif self.direction == 'DOWN':
            newindex = index+1 if index < n-1 else 0
        elif self.direction == 'TOP':
            newindex = 0
        elif self.direction == 'BOTTOM':
            newindex = n-1
        bonechains.move(index, newindex)
        armature.bone_chains_index = newindex
        
        return {'FINISHED'}
bpy.utils.register_class(DMR_OP_BoneChainMove)

# ---------------------------------------------------------------------------

class DMR_OP_BoneChainAdd(bpy.types.Operator):
    bl_idname = "dmr.bone_chain_add"
    bl_label = "Add Bone Chain"
    bl_description = "Adds new bone chain"
    bl_options = {'REGISTER', 'UNDO'}
    
    chainname : bpy.props.StringProperty(
        name="Chain Name", default='New Chain',
        description='Name of new chain',
    )
    
    @classmethod
    def poll(self, context):
        return context.object and context.object.type == 'ARMATURE'
    
    def execute(self, context):
        context.object.data.bone_chains.add().name = self.chainname
        
        return {'FINISHED'}
bpy.utils.register_class(DMR_OP_BoneChainAdd)

# ---------------------------------------------------------------------------

class DMR_OP_BoneChainRemove(bpy.types.Operator):
    bl_idname = "dmr.bone_chain_remove"
    bl_label = "Remove Bone Chain"
    bl_description = "Removes selected bone chain"
    bl_options = {'REGISTER', 'UNDO'}
    
    chainindex : bpy.props.IntProperty(
        name="Chain Index", default=0,
        description='Index of chain to remove',
    )
    
    @classmethod
    def poll(self, context):
        return context.object and context.object.type == 'ARMATURE'
    
    def invoke(self, context, event):
        self.chainindex = context.object.data.bone_chains_index
        return self.execute(context)
    
    def execute(self, context):
        bonechains = context.armature.bone_chains
        if self.chainindex in range(0, len(bonechains)):
            bonechains.remove(self.chainindex)
        context.armature.bone_chains_index = max(0, min(context.armature.bone_chains_index, len(bonechains)-1))
        
        return {'FINISHED'}
bpy.utils.register_class(DMR_OP_BoneChainRemove)

# ---------------------------------------------------------------------------

class DMR_OP_BoneChainFromSelection(bpy.types.Operator):
    bl_idname = "dmr.bone_chain_from_selection"
    bl_label = "Bone Chain From Selection"
    bl_description = "Adds new bone chain(s) from selection"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(self, context):
        o = context.object
        return o and o.type == 'ARMATURE' and o.mode in {'EDIT', 'POSE'}
    
    def execute(self, context):
        def GetChainRoot(b):
            print(b.name)
            return GetChainRoot(b.parent) if (b.parent and b.use_connect) else b
        def GetBoneChain(b):
            return ([b] + GetBoneChain(b.children[0])) if b.children else [b]
        
        obj = context.object
        obj.update_from_editmode()
        armature = obj.data
        
        bones = armature.bones
        usedbones = []
        for b in bones:
            if b not in usedbones:
                if b.select:
                    root = GetChainRoot(b)
                    chainlist = GetBoneChain(b)
                    usedbones += chainlist
                    
                    chainnames = [x.name for x in chainlist]
                    
                    if [1 for c in armature.bone_chains if str(chainnames) == str([x.name for x in c.bones])]:
                        continue
                    
                    newchain = armature.bone_chains.add()
                    newchain.name = root.name
                    
                    for chainbone in chainlist:
                        chainentry = newchain.bones.add()
                        chainentry.name = chainbone.name
                        chainentry.id = 0
        
        return {'FINISHED'}
bpy.utils.register_class(DMR_OP_BoneChainFromSelection)

# ---------------------------------------------------------------------------

class DMR_OP_BoneChainAddBone(bpy.types.Operator):
    bl_idname = "dmr.bone_chain_add_bone"
    bl_label = "Add Bone to Bone Chain"
    bl_description = "Adds active bone to bone chain"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(self, context):
        return context.object and context.object.type == 'ARMATURE'
    
    def execute(self, context):
        b = context.object.data.bones.active
        bonechain = context.armature.bone_chains[context.object.data.bone_chains_index]
        boneentry = bonechain.bones.add()
        boneentry.name = b.name
        boneentry.id = len(bonechain.bones)-1
        
        return {'FINISHED'}
bpy.utils.register_class(DMR_OP_BoneChainAddBone)

'# =========================================================================================================================='
'# PANELS'
'# =========================================================================================================================='

class DMR_PT_BoneChains(bpy.types.Panel):
    bl_label = "Bone Chains"
    bl_options = {'DEFAULT_CLOSED'}
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"

    @classmethod
    def poll(cls, context):
        return context.armature

    def draw(self, context):
        layout = self.layout
        
        ob = context.object
        armature = ob.data
        
        # Bone Chain List
        row = layout.row()
        row.template_list("OBJECT_UL_BoneChainList", "", armature, "bone_chains", armature, "bone_chains_index", rows=5)
        layout.operator("dmr.bone_chain_from_selection")
        
        col = row.column(align=True)

        col.operator("dmr.bone_chain_add", icon='ADD', text="")
        props = col.operator("dmr.bone_chain_remove", icon='REMOVE', text="")
        
        col.separator()
        col.operator("dmr.bone_chain_move", icon='TRIA_UP', text="").direction = 'UP'
        col.operator("dmr.bone_chain_move", icon='TRIA_DOWN', text="").direction = 'DOWN'
        
        # Bone Chain Bones
        box = layout.box()
        box.label(text='Chain Bones')
        
        chainindex = armature.bone_chains_index
        chaincount = len(armature.bone_chains)
        activechain = armature.bone_chains[armature.bone_chains_index] if (armature.bone_chains and chainindex < chaincount) else None
        
        if activechain:
            row = box.row()
            row.template_list("OBJECT_UL_BoneChainBones", "", activechain, "bones", armature, "bone_chains_bone_index", rows=5)
            c = row.column()
            c.operator('dmr.bone_chain_add_bone', text='', icon='ADD')
        
classlist.append(DMR_PT_BoneChains)

# ---------------------------------------------------------------------------
class BoneChainBone(bpy.types.PropertyGroup):
    id : bpy.props.IntProperty()
classlist.append(BoneChainBone)

# ---------------------------------------------------------------------------
class BoneChain(bpy.types.PropertyGroup):
    bones : bpy.props.CollectionProperty(type=BoneChainBone)
classlist.append(BoneChain)

# ---------------------------------------------------------------------------
class OBJECT_UL_BoneChainList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        r = layout.row()
        r.prop(item, "name", text="", emboss=False, translate=False, icon='LINKED')
classlist.append(OBJECT_UL_BoneChainList)

# ---------------------------------------------------------------------------
class OBJECT_UL_BoneChainBones(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        r = layout.row()
        r.prop(item, "name", text="", emboss=False, translate=False, icon='BONE_DATA')
classlist.append(OBJECT_UL_BoneChainBones)

# =============================================================================

class DMR_PT_KeyframeManip(bpy.types.Menu):
    bl_label = "Keyframe Manip"

    def draw(self, context):
        layout = self.layout
        
        layout.operator("dmr.keyframe_manip_wave")
        layout.operator("dmr.keyframe_manip_random_frame")
#classlist.append(DMR_PT_KeyframeManip)

def keymanip_menu(self, context):
    layout = self.layout
    layout.operator("dmr.keyframe_manip_wave")
    layout.operator("dmr.keyframe_manip_random_frame")

# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)
    
    try:
        bpy.types.VIEW3D_MT_pose_context_menu.remove(keymanip_menu)
    except:
        bpy.types.VIEW3D_MT_pose_context_menu.prepend(keymanip_menu)
    
    bpy.types.Armature.bone_chains = bpy.props.CollectionProperty(type=BoneChain)
    bpy.types.Armature.bone_chains_index = bpy.props.IntProperty()
    bpy.types.Armature.bone_chains_bone_index = bpy.props.IntProperty()
    
def unregister():
    bpy.types.VIEW3D_MT_pose_context_menu.remove(keymanip_menu)
    
    for c in reverse(classlist):
        bpy.utils.unregister_class(c)
    del bpy.types.Object.bone_chains

if __name__ == "__main__":
    register()

