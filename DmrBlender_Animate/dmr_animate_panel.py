import bpy

from bpy.types import Header, Menu, Panel, UIList, Operator
from rna_prop_ui import PropertyPanel

classlist = []

class DMR_PT_VCMaterialPanel(bpy.types.Panel): # ------------------------------
    bl_label = "VC Material"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Dmr Anim" # Name of sidebar
    
    @classmethod 
    def poll(self, context):
        return 1
    
    def draw(self, context):
        layout = self.layout
        
        if 'vc_master' not in [x.name for x in bpy.data.materials]:
            layout.label(text='No "vc_master" material found')
            return
        
        opname = 'dmr.set_material_output_by_name'
        
        s = layout.box().column(align=1)
        s.label(text='Toon Output', )
        s.operator(opname, text='Toon Combined').name = 'out toon combined'
        s.operator(opname, text='Toon Threshold').name = 'out toon threshold'
        s.operator(opname, text='Toon Spe Intensity').name = 'out toon spe intensity'
        s.operator(opname, text='Toon Spe Size').name = 'out toon spe size'
        s.operator(opname, text='Toon AO').name = 'out toon ao'
        
        s = layout.box().column(align=1)
        opname = 'dmr.set_material_output_by_name'
        s.label(text='Toon Output', )
        s.operator(opname, text='BSDF Combined').name = 'out bsdf combined'
        s.operator(opname, text='BSDF Threshold').name = 'out bsdf metallic'
        s.operator(opname, text='BSDF Spe Intensity').name = 'out bsdf spe intensity'
        s.operator(opname, text='BSDF Spe Size').name = 'out bsdf spe size'
        s.operator(opname, text='BSDF SSS').name = 'out bsdf sss'
        
        layout.prop(context.scene.render, "simplify_subdivision")
        
        layout.operator('dmr.set_up_vc_anim_layers')
        
classlist.append(DMR_PT_VCMaterialPanel)

# =====================================================================

class DMR_PT_Anim_General(bpy.types.Panel): # ------------------------------
    bl_label = "Dmr Animate"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Dmr Anim" # Name of sidebar
    
    @classmethod 
    def poll(self, context):
        active = context.active_object;
        if active:
            return 1;
        return None;
    
    def draw(self, context):
        active = context.active_object;
        layout = self.layout;
        
        if active.type == 'ARMATURE':
            layout.row().prop(active.data, "pose_position", expand=True)
        layout.operator('dmr.make_control_armature');
        layout.operator('dmr.set_up_vc_anim_layers');
        layout.operator('dmr.toggle_alt_colors');
        
classlist.append(DMR_PT_Anim_General);

# =====================================================================

class DMR_PT_Anim_ShapeKeyPanel(bpy.types.Panel): # ------------------------------
    bl_label = "Shape Keys"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Dmr Anim" # Name of sidebar
    
    @classmethod 
    def poll(self, context):
        active = context.active_object;
        if active:
            if active.type == 'MESH' and active.mode == 'EDIT':
                return 1;
        return None;
    
    def draw(self, context):
        active = context.active_object;
        layout = self.layout;
        
        shapekeys = active.data.shape_keys;
        if not shapekeys:
            return;
        
        keyblocks = active.data.shape_keys.key_blocks;
        
        r = layout.row(align=1);
        r.operator('mesh.blend_from_shape');
        r = r.row(align=1);
        op = r.operator('mesh.blend_from_shape', text = '', icon = 'BOLD');
        op.shape = keyblocks[0].name;
        op.blend = 1;
        op.add = False;
        op = r.operator('dmr.blend_from_shape_all', text = '', icon = 'WORLD');
        
classlist.append(DMR_PT_Anim_ShapeKeyPanel);

# =====================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
