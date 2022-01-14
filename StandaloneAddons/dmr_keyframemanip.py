import bpy

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
        
        def GetChainRoot(b):
            return GetChainRoot(b) if (b.parent and b.parent.select and b.use_connect) else b
        def GetBoneChain(b):
            return ([b] + GetBoneChain(b.children[0])) if (b.children and b.children[0].select) else [b]
        
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
                    if not fc.hide:
                        for k in fc.keyframe_points:
                            if k.select_control_point:
                                k.co_ui[0] += channelshift*chainindex + chainpos*posshift
        
        return {'FINISHED'}
classlist.append(DMR_OP_KeyframeManip_Wave)

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
            return GetChainRoot(b) if (b.parent and b.use_connect) else b
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
            row.template_list("OBJECT_UL_BoneChainBones", "", activechain, "bones", ob, "bone_chains_bone_index", rows=5)
        
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
print('='*100)

def register():
    for c in classlist:
        bpy.utils.register_class(c)
    
    bpy.types.Armature.bone_chains = bpy.props.CollectionProperty(type=BoneChain)
    bpy.types.Armature.bone_chains_index = bpy.props.IntProperty()
    bpy.types.Armature.bone_chains_bone_index = bpy.props.IntProperty()
    
def unregister():
    for c in reverse(classlist):
        bpy.utils.unregister_class(c)
    del bpy.types.Object.bone_chains

if __name__ == "__main__":
    register()

