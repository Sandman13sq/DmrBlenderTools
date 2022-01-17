import bpy
import random

def GetChainRoot(b):
    return GetChainRoot(b.parent) if (b.parent and b.parent.select and b.use_connect) else b
def GetBoneChain(b):
    for c in b.children:
        if c.select:
            return [b] + GetBoneChain(c)
    return [b]

classlist = []

# =============================================================================

class DMR_OP_KeyframeManip_Wave(bpy.types.Operator):
    bl_label = "Key Manip - Wave"
    bl_idname = 'dmr.keyframe_manip_wave'
    bl_description = 'Offsets Keyframes by order of bone chain';
    bl_options = {'REGISTER', 'UNDO'}
    
    channelshift: bpy.props.IntProperty(
        name="Channel Shift", default=1,
        description="Number of frames to shift by chain index",
    )
    
    posshift: bpy.props.IntProperty(
        name="Position Shift", default=1,
        description="Number of frames to shift down the chain",
    )
    
    def execute(self, context):
        obj = context.object
        armature = obj.data
        bones = obj.data.bones
        pbones = obj.pose.bones
        
        obj.update_from_editmode()
        
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
        
        action = obj.animation_data.action
        fcurves = action.fcurves
        fcurvemap = {}
        
        for fc in fcurves:
            name = fc.data_path
            name = name[name.find('"')+1: name.rfind('"')]
            if name not in fcurvemap:
                fcurvemap[name] = []
            fcurvemap[name].append(fc)
        
        channelshift = self.channelshift
        posshift = self.posshift
        
        for chainindex,chain in enumerate(chains):
            bonelink = [pbones[b.name] for b in chain]
            print([b.name for b in bonelink])
            
            for chainpos,b in enumerate(bonelink):
                fcurves = fcurvemap[b.name]
                
                for fc in fcurves:
                    if not fc.hide and not fc.lock:
                        for k in fc.keyframe_points:
                            if k.select_control_point:
                                k.co_ui[0] += channelshift*chainindex + chainpos*posshift
        
        return {'FINISHED'}
classlist.append(DMR_OP_KeyframeManip_Wave)

# =============================================================================

class DMR_OP_KeyframeManip_RandomFrame(bpy.types.Operator):
    bl_label = "Key Manip - Random Frame"
    bl_idname = 'dmr.keyframe_manip_random_frame'
    bl_description = 'Offsets selected keyframe positions randomly';
    bl_options = {'REGISTER', 'UNDO'}
    
    seed: bpy.props.IntProperty(
        name="Random Seed", default=0,
        description="Seed to use for suffling keyframe positions",
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

# =============================================================================

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

# =============================================================================

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

# =============================================================================

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

# =============================================================================

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
        
classlist.append(DMR_PT_BoneChains)

# =============================================================================

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

