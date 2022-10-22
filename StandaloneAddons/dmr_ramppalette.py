import bpy

from bpy_extras.io_utils import ExportHelper, ImportHelper

classlist = []

# =====================================================================================

class RampPalette_NodeGroup(bpy.types.PropertyGroup):
    name : bpy.props.StringProperty()
    node_tree : bpy.props.PointerProperty(type=bpy.types.NodeTree)
    index : bpy.props.IntProperty(name='Active Color Index')
    ramp_index : bpy.props.IntProperty(name='Active Ramp Index', update=lambda s,c: s.UpdateRampIndex())
    width : bpy.props.IntProperty(name='Width', default=8, min=2, max=32, update=lambda s,c: s.UpdateRamps())
    height : bpy.props.IntProperty(name='Height', default=4, min=1, max=8, update=lambda s,c: s.UpdateRamps())
    gamma_correct : bpy.props.BoolProperty( name='Gamma Correct', update=lambda s,c: s.UpdateGamma() )
    
    def UpdateGamma(self):
        self.node_tree.nodes['gamma'].inputs[1].default_value = 2.2 if self.gamma_correct else 1.0
    
    def UpdateGamma(self):
        self.node_tree.nodes['gamma'].inputs[1].default_value = 2.2 if self.gamma_correct else 1.0
    
    def NewNode(self, type, label, location):
        nd = self.node_tree.nodes.new(type=type)
        nd.location = location
        nd.label, nd.name = [label]*2
        return nd
    
    def LinkNodes(self, n1, output_index, n2, input_index):
        return self.node_tree.links.new(
            (self.node_tree.nodes[n1] if isinstance(n1, str) else n1).outputs[output_index], 
            (self.node_tree.nodes[n2] if isinstance(n2, str) else n2).inputs[input_index]
            )
    
    def Init(self):
        self.node_tree = bpy.data.node_groups.new(name='Ramp Palette', type='ShaderNodeTree')
        self.node_tree.use_fake_user = True
        
        self.NewNode('NodeGroupInput', "input", (-500, 0))
        self.NewNode('ShaderNodeGamma', "gamma", (300, 0))
        self.NewNode('NodeGroupOutput', "output", (500, 0))
        
        nd = self.NewNode('ShaderNodeMath', "modulo", (-300, 0))
        nd.operation = 'MODULO'
        nd.inputs[1].default_value = 1.0
        
        self.UpdateRamps()
        return self
    
    def Cleanup(self):
        bpy.data.node_groups.remove(self.node_tree)
    
    def AddRamp(self):
        self.height += 1
    
    def RemoveRamp(self, index):
        self.node_tree.nodes.remove( self.GetColorRamps()[index] )
        self.height = max(1, self.height-1)
    
    def GetRampNodes(self):
        nodes = [nd for nd in self.node_tree.nodes if nd.type == 'VALTORGB']
        nodes.sort(key=lambda x: x.name)
        return nodes
    
    def GetColorRamps(self):
        return [nd.color_ramp for nd in self.GetRampNodes()]
    
    def GetColorRamp(self, index):
        return self.node_tree.nodes["c%d"%index]
    
    def GetActiveElements(self):
        return [nd.color_ramp.elements[self.index] for nd in self.GetRampNodes()]
    
    def Resize(self, width=0, height=0):
        if height > 0:
            self.height = height
        if width > 0:
            self.width = width
    
    def ShiftElement(self, index, shift=1):
        i = self.index if index == None else index
        for ramp in self.GetColorRamps():
            elements = list(ramp.elements)
            e1, e2 = (elements[i], elements[(i+shift) % self.width])
            p = e1.color
            e1.color = e2.color
            e2.color = p
        
        if index == None:
            self.index = (i+shift) % self.width
    
    def UpdateRamps(self):
        ramps = self.GetRampNodes()
        
        # Height
        if len(ramps) < self.height:
            for i in range(len(ramps), self.height):
                self.NewNode('ShaderNodeValToRGB', "", (0, -10000 - i*10))
        elif len(ramps) > self.height:
            for nd in ramps[::-1][:len(ramps)-self.height]:
                self.node_tree.nodes.remove(nd)
        
        # Width
        for i, nd in enumerate(self.GetRampNodes()):
            ramp = nd.color_ramp
            nd.name = 'c%d' % i
            nd.location = (0, -i*100)
            
            while len(ramp.elements) < self.width:
                ramp.elements.new(1.0)
            while len(ramp.elements) > self.width:
                ramp.elements.remove(ramp.elements[-1])
            for j, e in enumerate(ramp.elements):
                e.position = (j+0.5)/(self.width)
        
        self.index = max(0, min(self.width-1, self.index))
        self.ramp_index = max(0, min(self.height-1, self.ramp_index))
        
    def UpdateRampIndex(self):
        ramps = self.GetRampNodes()
        self.LinkNodes('input', 0, 'modulo', 0)
        self.LinkNodes('modulo', 0, ramps[self.ramp_index], 0)
        self.LinkNodes(ramps[self.ramp_index], 0, 'gamma', 0)
        self.LinkNodes('gamma', 0, 'output', 0)
    
    def FromImage(self, image):
        self.width, self.height = image.size
        pixels = tuple(image.pixels)
        rows = tuple( pixels[py*self.width*4:(py+1)*self.width*4] for py in range(0, self.height) )
        rows = rows[::-1]
        
        for ramp, row in zip(self.GetColorRamps(), rows):
            for i, e in enumerate(ramp.elements):
                print(row[i*4: (i+1)*4])
                e.color = row[i*4: (i+1)*4]
    
classlist.append(RampPalette_NodeGroup)

# -------------------------------------------------------------------

class RampPalette_Master(bpy.types.PropertyGroup):
    data : bpy.props.CollectionProperty(type=RampPalette_NodeGroup)
    data_index : bpy.props.IntProperty(name='Index')
    
    def Add(self):
        return self.data.add().Init()
    
    def Remove(self, index):
        self.data[index].Cleanup()
        self.data.remove(index)
        self.data_index = max(0, min(self.data_index, len(self.data)-1))
    
    def Active(self):
        return self.data[self.data_index] if self.data else None
        
classlist.append(RampPalette_Master)

# =====================================================================================

class RampPalette_OP(bpy.types.Operator):
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return 1

# -------------------------------------------------------------------
class RAMPPALETTE_OP_Palette_Add(RampPalette_OP): 
    """Adds new palette to list"""
    bl_idname = "ramppalette.palette_add"
    bl_label = "Add Palette"
    
    def execute(self, context):
        context.scene.ramp_palettes.Add()
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_Palette_Add)

# -------------------------------------------------------------------
class RAMPPALETTE_OP_Palette_Remove(RampPalette_OP): 
    """Removes Palette from list"""
    bl_idname = "ramppalette.palette_remove"
    bl_label = "Remove Palette"
    index : bpy.props.IntProperty()
    
    def execute(self, context):
        context.scene.ramp_palettes.Remove(self.index)
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_Palette_Remove)

# -------------------------------------------------------------------
class RAMPPALETTE_OP_Ramp_Add(RampPalette_OP): 
    """Adds new ramp to palette"""
    bl_idname = "ramppalette.ramp_add"
    bl_label = "Add Ramp"
    
    def execute(self, context):
        context.scene.ramp_palettes.Active().AddRamp()
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_Ramp_Add)

# -------------------------------------------------------------------
class RAMPPALETTE_OP_Ramp_Remove(RampPalette_OP): 
    """Removes ramp from palette"""
    bl_idname = "ramppalette.ramp_remove"
    bl_label = "Remove Ramp"
    index : bpy.props.IntProperty()
    
    def execute(self, context):
        context.scene.ramp_palettes.Active().RemoveRamp(self.index)
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_Ramp_Remove)

# -------------------------------------------------------------------
class RAMPPALETTE_OP_Color_Shift(RampPalette_OP): 
    """Moves color of all ramps"""
    bl_idname = "ramppalette.color_shift"
    bl_label = "Shift Element"
    index : bpy.props.IntProperty()
    shift : bpy.props.IntProperty(default=1)
    
    def execute(self, context):
        context.scene.ramp_palettes.Active().ShiftElement(None, self.shift)
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_Color_Shift)

# ----------------------------------------------------------------------------------
class RAMPPALETTE_OP_Import(bpy.types.Operator, ImportHelper):
    """Tooltip"""
    bl_idname = "ramppalette.import"
    bl_label = "Import Palette from File"
    bl_options = {'REGISTER', 'UNDO'}
    
    filename_ext = ".png"
    filter_glob: bpy.props.StringProperty(default="*"+filename_ext, options={'HIDDEN'}, maxlen=255)
    
    @classmethod
    def poll(self, context):
        return context.scene.ramp_palettes.Active()
    
    def execute(self, context):
        image = bpy.data.images.load(self.filepath, check_existing=False)
        image.colorspace_settings.name = 'sRGB'
        context.scene.ramp_palettes.Active().FromImage(image)
        bpy.data.images.remove(image)
        self.report({'INFO'}, 'Palette read from "%s"' % self.filepath)
        
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_Import)

# =====================================================================================

class RAMPPALLETTE_UL_PaletteList(bpy.types.UIList):
    def draw_item(self, _context, layout, _data, item, icon, _active_data_, _active_propname, _index):
        r = layout.row()
        r.prop(item.node_tree, "name", text="", emboss=False, icon_value=icon)
        r.operator('ramppalette.palette_remove', text="", icon='REMOVE').index=_index
classlist.append(RAMPPALLETTE_UL_PaletteList)

# -------------------------------------------------------------------

class RAMPPALETTE_PT_RampPalettePanel(bpy.types.Panel):
    bl_label = "Ramp Palette"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Edit" # Name of sidebar
    
    def draw(self, context):
        master = context.scene.ramp_palettes
        layout = self.layout
        
        r = layout.row()
        r.operator('ramppalette.palette_add', icon='ADD')
        
        # Palette List
        layout.template_list("RAMPPALLETTE_UL_PaletteList", "", master, 'data', master, "data_index", rows=4)
        
        # Ramp list
        b = layout.box().column(align=1)
        ramppalette = master.Active()
        
        if ramppalette:
            r = b.row()
            r.prop(ramppalette, 'ramp_index')
            r.operator('ramppalette.import')
            r.prop(ramppalette, 'gamma_correct', text="", icon='CON_TRANSLIKE', toggle=1)
            
            r = b.row()
            rr = r.row(align=1)
            rr.prop(ramppalette, 'width')
            rr.prop(ramppalette, 'height')
            
            r = b.row()
            rr = r.row(align=1)
            rr.prop(ramppalette, 'index', text='X')
            rr.operator('ramppalette.color_shift', text="", icon='TRIA_LEFT').shift = -1
            rr.operator('ramppalette.color_shift', text="", icon='TRIA_RIGHT').shift = 1
            r.operator('ramppalette.ramp_add', icon='ADD')
            
            # Draw Active Elements
            elements = ramppalette.GetActiveElements()
            bb = b.box().row(align=1)
            
            for e in elements:
                bb.prop(e, 'color', text='')
            
            
classlist.append(RAMPPALETTE_PT_RampPalettePanel)

# -------------------------------------------------------------------

class RAMPPALETTE_PT_RampPalettePanel_Ramps(bpy.types.Panel):
    bl_label = "Color Ramps"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Edit" # Name of sidebar
    bl_parent_id = 'RAMPPALETTE_PT_RampPalettePanel'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        master = context.scene.ramp_palettes
        layout = self.layout
        ramppalette = master.Active()
        
        if ramppalette:
            # Draw ramps
            rampnodes = ramppalette.GetRampNodes()
            cc = layout.column(align=1)
            cc.scale_y = 0.7
            for nd in rampnodes:
                rr = cc.row(align=0)
                rr.column().template_color_ramp(nd, "color_ramp", expand=True)
                rr.operator('ramppalette.ramp_remove', text="", icon='REMOVE')
    
classlist.append(RAMPPALETTE_PT_RampPalettePanel_Ramps)

# =====================================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)
    
    bpy.types.Scene.ramp_palettes = bpy.props.PointerProperty(name='Ramp Palette Master', type=RampPalette_Master)

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
