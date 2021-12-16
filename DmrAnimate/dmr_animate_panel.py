import bpy

from bpy.types import Header, Menu, Panel, UIList, Operator
from rna_prop_ui import PropertyPanel

classlist = [];

class DMR_PT_VCMaterialPanel(bpy.types.Panel): # ------------------------------
    bl_label = "VC Material"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Dmr Anim" # Name of sidebar
    
    @classmethod 
    def poll(self, context):
        return 'vc_master' in [x.name for x in bpy.data.materials];
    
    def draw(self, context):
        layout = self.layout;
        opname = 'dmr.set_material_output_by_name';
        
        s = layout.box().column(align=1);
        s.label(text='Toon Output', );
        s.operator(opname, text='Toon Combined').name = 'out toon combined';
        s.operator(opname, text='Toon Threshold').name = 'out toon threshold';
        s.operator(opname, text='Toon Spe Intensity').name = 'out toon spe intensity';
        s.operator(opname, text='Toon Spe Size').name = 'out toon spe size';
        s.operator(opname, text='Toon AO').name = 'out toon ao';
        
        s = layout.box().column(align=1);
        opname = 'dmr.set_material_output_by_name';
        s.label(text='Toon Output', );
        s.operator(opname, text='BSDF Combined').name = 'out bsdf combined';
        s.operator(opname, text='BSDF Threshold').name = 'out bsdf metallic';
        s.operator(opname, text='BSDF Spe Intensity').name = 'out bsdf spe intensity';
        s.operator(opname, text='BSDF Spe Size').name = 'out bsdf spe size';
        s.operator(opname, text='BSDF SSS').name = 'out bsdf sss';
        
        layout.prop(context.scene.render, "simplify_subdivision");
        
classlist.append(DMR_PT_VCMaterialPanel);

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in classlist:
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
