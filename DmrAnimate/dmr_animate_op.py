import bpy

from bpy.types import Header, Menu, Panel, UIList, Operator
from rna_prop_ui import PropertyPanel

classlist = [];

# =============================================================================

class DMRANIM_OP_SetUpVCLayers(bpy.types.Operator): # ------------------------------
    bl_label = 'Set up VC Layers';
    bl_idname = 'dmr.set_up_vc_anim_layers';
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        def GetVCLayer(obj, name):
            vclayers = obj.data.vertex_colors;
            if name not in [x.name for x in vclayers]:
                vclayers.new(name=name);
            return vclayers[name];
        
        def ClearVCLayer(lyr, color):
            if len(color) < 4:
                color = [x for x in color];
                while len(color) < 4:
                    color += color;
                color[3] = 1.0;
            color = tuple(color[:4]);
            
            for vc in lyr.data:
                vc.color = color;
        
        def CheckVCLayer(obj, name, color):
            vclayers = obj.data.vertex_colors;
            if name not in [x.name for x in vclayers]:
                vclayers.new(name=name);
                print([obj.name, name, [x.name for x in vclayers]])
                ClearVCLayer(vclayers[name], color);
            return vclayers[name];
        
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                vclayers = obj.data.vertex_colors;
                
                oops = {
                    'Col': 'Color Base',
                    'Col_Alt': 'Color Alt',
                    '_shd_ao': 'Mat AO',
                    '_shd_threshold': 'Mat Threshold',
                    '_shd_roughness': 'Mat Spe Intensity',
                    '_shd_ao': 'Mat Spe Size',
                }
                
                for vc in vclayers:
                    for oldn,newn in oops.items():
                        if vc.name == oldn:
                            vc.name = newn;
                
                for vc in vclayers:
                    for n in ['Mat Cycles', 'Mat Threshold', 'Mat Spe Intensity', 'Mat Spe Size', 'Mat AO']:
                        if vc.name == n:
                            vclayers.remove(vc);
                            break;
                
                print(obj.name)
                
                # Shadow Color Layer
                CheckVCLayer(obj, 'Color Base', [1.0]);
                CheckVCLayer(obj, 'Color Shadow', [.5]);
                # R = Threshold
                # G = Spe Intensity
                # B = Spe Size
                # A = AO
                CheckVCLayer(obj, 'Mat Toon', [.5, 0, 0, 0]);
                # R = Metallic
                # G = Roughness
                # B = Specular
                # A = SSS
                CheckVCLayer(obj, 'Mat Cycles', [0, 0, 0, 0]);
                
                for vc in vclayers['Mat Toon'].data:
                    col = vc.color[:];
                    vc.color[1] = col[3];
                    vc.color[3] = col[1];
                
                name = 'Color Base';
                vclayers.active = vclayers[name];
                vclayers[name].active_render = True;
                vclayers.active_index = [x.name for x in vclayers].index(name);
                
        return {'FINISHED'}
classlist.append(DMRANIM_OP_SetUpVCLayers);

# ===================================================================================

class DMRANIM_OP_MakeControl(bpy.types.Operator):
    bl_label = "Set Up Control Armature"
    bl_idname = 'dmr.make_control_armature'
    bl_description = 'Takes selected mesh and armature to create bones to control shape keys in mesh';
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        print('> Making control armature...');
        selectedobjects = context.selected_objects;
        
        # Find Control Armature
        controlobj = [x for x in selectedobjects if x.type == 'ARMATURE'];
        if len(controlobj) == 0:
            self.report({'WARNING'}, 'No armature selected');
            return {'FINISHED'}
        controlobj = controlobj[0];
        bones = controlobj.data.bones;
        editbones = controlobj.data.edit_bones;
        posebones = controlobj.pose.bones;
        
        controlobj.show_in_front = True;
        controlobj.show_bounds = True;
        controlobj.display_type = 'WIRE';
        controlobj.data.display_type = 'ENVELOPE';
        controlobj.data.show_names = True;
        
        # Find Shape key objects
        meshobjects = [x for x in selectedobjects if (x.type == 'MESH' and x.data.shape_keys)];
        if len(meshobjects) == 0:
            self.report({'WARNING'}, 'No meshes selected');
            return {'FINISHED'}
        
        # Get shape key blocks from objects
        kbdata = []; # (obj, keyblock, shapekeys)
        keynames = [];
        
        print('> Finding shape key blocks...');
        for meshobj in meshobjects:
            shapekeys = meshobj.data.shape_keys;
            for kb in shapekeys.key_blocks[1:]:
                if kb.name[0] == '!':
                    continue;
                kbdata.append( (meshobj, kb, shapekeys) );
                keynames.append(kb.name);
        
        kbdata.reverse();
        keybone = [];
        
        # Delete non shapekey bones
        print('> Cleaning bones...');
        bpy.context.view_layer.objects.active = controlobj;
        lastmode = controlobj.mode;
        
        bpy.ops.object.mode_set(mode='EDIT');
        bpy.ops.armature.select_all(action='DESELECT');
        bpy.ops.object.mode_set(mode='OBJECT');
        for b in [b for b in bones if b.name not in keynames]:
            b.select = True;
        bpy.ops.object.mode_set(mode='OBJECT');
        bpy.ops.object.mode_set(mode='EDIT');
        bpy.ops.armature.delete();
        
        r = .1;
        
        def NewBone(name):
            if name not in [b.name for b in editbones]:
                bpy.ops.armature.bone_primitive_add();
                bone = editbones['Bone'];
                bone.name = name;
                bpy.ops.object.mode_set(mode='OBJECT');
                bpy.ops.object.mode_set(mode='EDIT');
        
        def SetXClampConstraint(object, bonename, min_x = 0.0, max_x = 1.0):
            pb = object.pose.bones[bonename];
            constraints = pb.constraints;
            
            pb.lock_location[1] = True;
            pb.lock_location[2] = True;
            
            # X Clamp
            cname = 'X Clamp';
            if cname not in [c.name for c in constraints]:
                constraints.new('LIMIT_LOCATION').name = cname;
                c = constraints[cname];
                
                c.use_min_x = True;
                c.min_x = min_x;
                c.use_max_x = True;
                c.max_x = max_x;
                c.owner_space = 'LOCAL';
                c.use_transform_limit = True;
        
        # Create bones
        print('> Creating bones...');
        z = r*2 if len(keynames) > 1 else r*4;
        for i, kbentry in enumerate(kbdata):
            meshobj = kbentry[0];
            kb = kbentry[1];
            shapekeys = kbentry[2];
            k = kb.name;
            
            if len([b for b in bones if b.name == k]) == 0:
                NewBone(k);
                
            bone = bones[k];
            ebone = editbones[k];
            ebone.head_radius = r;
            ebone.tail_radius = 0.01;
            ebone.head = (0.0, 0.0, z);
            ebone.tail = (0.0, r, z);
            pbone = posebones[k];
            pbone.location[0] = kb.value;
            
            z += r*2;
            if i == len(keynames) // 2 - 1:
                z += r*2;
            
            SetXClampConstraint(controlobj, k);
        
        # Bars
        def MakeBar(x, z):
            name = 'X = ' + str(x);
            NewBone(name);
            ebone = editbones[name];
            ebone.head = (x, 0.0, 0.0);
            ebone.tail = (x, 0.0, z);
            ebone.head_radius = 0.01;
            ebone.tail_radius = 0.01;
            ebone.lock = True;
            ebone.envelope_distance = 0.0;
            pb = posebones[name];
            pb.lock_location = (True, True, True);
            pb.lock_rotation = (True, True, True);
            pb.lock_scale = (True, True, True);
        
        MakeBar(0, z);
        MakeBar(1, z);
        MakeBar(-1, z);
        NewBone('X = 1');
        
        bpy.ops.object.mode_set(mode=lastmode);
        
        # Drivers
        print('> Setting up drivers...');
        
        for kbentry in kbdata: # Clear all drivers
            shapekeys = kbentry[2];
            if shapekeys.animation_data:
                for d in shapekeys.animation_data.drivers:
                    shapekeys.animation_data.drivers.remove(d);
        
        # Add new drivers
        for meshobj, kb, shapekeys in kbdata:
            key = kb.name;
            datapath = 'key_blocks["%s"].value' % key;
            
            d = shapekeys.driver_add(datapath).driver;
            v = d.variables.new();
            v.name = 'bone_x';
            v.type = 'TRANSFORMS';
            v.targets[0].id = controlobj;
            v.targets[0].data_path = datapath;
            v.targets[0].bone_target = key;
            v.targets[0].transform_space = 'LOCAL_SPACE';
            
            d.expression = 'bone_x';
        
        print('> Complete!\n');
        return {'FINISHED'}
classlist.append(DMRANIM_OP_MakeControl);

# =============================================================================

class DMRANIM_OP_QuickOutline(bpy.types.Operator):
    bl_label = "Quick Outline"
    bl_idname = 'dmr.quick_outline'
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod 
    def poll(self, context):
        return context.active_object;
    
    def execute(self, context):
        mname = '-OUTLINE-';
        outlinematerial = bpy.data.materials['outline'];
        vgname = '_outline';
        lastactive = bpy.context.view_layer.objects.active;
        
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue;
            if not obj.modifiers:
                continue;
            bpy.context.view_layer.objects.active = obj;
            
            # Vertex group
            vgroups = obj.vertex_groups;
            if vgname not in [x.name for x in vgroups]:
                vgroups.new(name = vgname);
                for v in obj.data.vertices:
                    vgroups[vgname].add([v.index], 1.0, 'REPLACE');
            
            # Modifier
            mods = obj.modifiers;
            outlinemod = [x for x in mods if x.name == mname];
            if not outlinemod:
                outlinemod = [mods.new(type='SOLIDIFY', name=mname)];
            outlinemod = outlinemod[0];
            outlinemod.offset = 1;
            outlinemod.thickness = 0.002;
            outlinemod.use_flip_normals = True;
            outlinemod.material_offset = -13;
            outlinemod.material_offset_rim = -13;
            outlinemod.vertex_group = vgname;
            
            # Material
            mats = obj.data.materials;
            if outlinematerial.name not in [x.name for x in mats]:
                bpy.ops.object.mode_set(mode='OBJECT');
                mats.append(outlinematerial);
                obj.active_material_index = len(mats)-1;
                for i in range(0, len(mats)):
                    bpy.ops.object.material_slot_move(direction='UP');
            
        bpy.context.view_layer.objects.active = lastactive;
        
        return {'FINISHED'}
classlist.append(DMRANIM_OP_QuickOutline);

# =============================================================================

class DMRANIM_OP_RemoveOutline(bpy.types.Operator):
    bl_label = "Remove Quick Outline"
    bl_idname = 'dmr.remove_quick_outline'
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod 
    def poll(self, context):
        active = context.active_object;
        return active and active.type == 'MESH';
    
    def execute(self, context):
        active = context.active_object;
        mname = '-OUTLINE-';
        outlinematerial = bpy.data.materials['outline'];
        vgname = '_outline';
        lastactive = bpy.context.view_layer.objects.active;
        
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                if outlinematerial.name in [x.name for x in obj.data.materials]:
                    obj.data.materials.pop(index=[x.name for x in obj.data.materials].index(outlinematerial.name));
                for m in obj.modifiers:
                    if m.name == mname:
                        obj.modifiers.remove(m);
                        break;
        
        return {'FINISHED'}
classlist.append(DMRANIM_OP_RemoveOutline);

# =============================================================================

class DMRANIM_OP_ToggleAlt(bpy.types.Operator):
    bl_label = "Toggle Alternate Vertex Colors"
    bl_idname = 'dmr.toggle_alt_colors'
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        targetsets = [];
        
        allAlts = True;
        
        vcnames = ['Color Base', 'Color Alt'];
        
        for obj in context.scene.objects:
            if obj.type != 'MESH':
                continue;
            vcs = obj.data.vertex_colors;
            if vcs:
                names = [x.name for x in vcs if x.name in vcnames];
                
                if vcnames[0] in names and vcnames[1] in names:
                    targetsets.append(vcs);
                    if vcs.active.name == vcnames[0]:
                        allAlts = False;
        
        for vcset in targetsets:
            if allAlts:
                vcset.active = [x for x in vcset if x.name == vcnames[0]][0];
            else:
                vcset.active = [x for x in vcset if x.name == vcnames[1]][0];
            vcset.active.active_render = True;
        
        self.report({'INFO'}, 'All vcs set to "%s"' % targetsets[0].active.name)
        
        return {'FINISHED'}
classlist.append(DMRANIM_OP_ToggleAlt);

# =============================================================================

class DMRANIM_OP_SetMaterialOutputByName(bpy.types.Operator):
    bl_label = "Set Material Output"
    bl_idname = 'dmr.set_material_output_by_name'
    bl_options = {'REGISTER', 'UNDO'}
    
    name : bpy.props.StringProperty(
        name="Output name", description="Name of output node");
    
    casesensitive : bpy.props.BoolProperty(
        name="Case Sensitive", description="Ignore case when comparing names", default = False);
    
    def execute(self, context):
        print('='*80)
        mat = bpy.data.materials['vc_master'];
        nodetree = mat.node_tree;
        name = self.name;
        if self.casesensitive:
            nodemap = {nd.label: nd for nd in nodetree.nodes};
        else:
            name = name.lower();
            nodemap = {nd.label.lower(): nd for nd in nodetree.nodes};
        
        for n, nd in nodemap.items():
            if n == name:
                for x in [x for x in nodetree.nodes if x.type == 'OUTPUT_MATERIAL']:
                    x.is_active_output = False;
                nd.is_active_output = True;
                nodetree.nodes.active = nd;
                nodetree.active_output = nodetree.nodes[:].index(nd);
                break;
            
        return {'FINISHED'}
classlist.append(DMRANIM_OP_SetMaterialOutputByName);

# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in classlist:
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
