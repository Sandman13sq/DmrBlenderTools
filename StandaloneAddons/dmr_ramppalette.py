import bpy
import mathutils
import math

from bpy_extras.io_utils import ExportHelper, ImportHelper

RAMPPALETTESIGNATURE = "<RAMP_PALETTE>"

# ----------------------------------------------------------------

def NewNode(ndtree, type, label, location):
    if type[:6] == 'Shader' and ndtree.type == 'COMPOSITING':
        if type == 'ShaderNodeTexImage':
            type = 'CompositorNodeImage'
        else:
            type = "Compositor" + type[6:]
    elif type[:10] == 'Compositor' and ndtree.type == 'SHADER':
        type = "Shader" + type[10:]
    
    nd = ndtree.nodes.new(type=type)
    nd.location = location
    nd.label, nd.name = [label]*2
    return nd

# ----------------------------------------------------------------

def LinkNodes(ndtree, n1, output_index, n2, input_index):
    return ndtree.links.new(
        (ndtree.nodes[n1] if isinstance(n1, str) else n1).outputs[output_index], 
        (ndtree.nodes[n2] if isinstance(n2, str) else n2).inputs[input_index]
        )

classlist = []

# =====================================================================================

class RampPalette_SlotColor(bpy.types.PropertyGroup):
    def UpdateColor(self, context):
        if self.image:
            i = 4*(self.image.size[0] * self.xy[1] + self.xy[0])
            self.image.pixels[i:i+4] = self.color
            self.image.update()
    
    color : bpy.props.FloatVectorProperty(name="Color", size=4, default=(1,1,1,1), subtype='COLOR', update=UpdateColor, min=0, max=1)
    xy : bpy.props.IntVectorProperty(name="Position", size=2, default=(0,0))
    image : bpy.props.PointerProperty(name="Image", type=bpy.types.Image)
classlist.append(RampPalette_SlotColor)

# =====================================================================================

class RampPalette_SlotRow(bpy.types.PropertyGroup):
    colors : bpy.props.CollectionProperty(name="Colors", type=RampPalette_SlotColor)
classlist.append(RampPalette_SlotRow)
    
# =====================================================================================

class RampPalette_NodeGroup(bpy.types.PropertyGroup):
    def UpdateName(self, context):
        self.node_tree.name = self.name + " - Material"
        self.compositor_tree.name = self.name + " - Compositor"
        if self.image:
            self.image.name = self.name + " - Image"
    
    name : bpy.props.StringProperty(name="Name", default="Ramp Palette", update=UpdateName)
    node_tree : bpy.props.PointerProperty(type=bpy.types.NodeTree)
    compositor_tree : bpy.props.PointerProperty(type=bpy.types.NodeTree)
    collection : bpy.props.PointerProperty(type=bpy.types.Collection)
    
    slots : bpy.props.CollectionProperty(name='Slots', type=RampPalette_SlotRow)
    image : bpy.props.PointerProperty(name='Image', type=bpy.types.Image)
    
    color_index : bpy.props.IntProperty(name='Active Color Index')
    ramp_index : bpy.props.IntProperty(name='Active Ramp Index', update=lambda s,c: s.UpdateRampIndex())
    width : bpy.props.IntProperty(name='Width', default=8, min=2, max=32, update=lambda s,c: s.DrawImage())
    height : bpy.props.IntProperty(name='Height', default=4, min=1, max=32, update=lambda s,c: s.DrawImage())
    gamma_correct : bpy.props.BoolProperty( name='Gamma Correct', update=lambda s,c: s.UpdateGamma() )
    
    def CopyFromOther(self, other):
        self.width = other.width
        self.height = other.height
        
        for y,slot in enumerate(other.slots):
            for x,color in enumerate(slot):
                self.slots[y].colors[x].color = color
    
    def GetObjects(self):
        if self.collection:
            return [obj for obj in self.collection.all_objects if obj.type == 'MESH']
        return bpy.context.selected_objects
    
    def UpdateGamma(self):
        self.node_tree.nodes['gamma'].inputs[1].default_value = 2.2 if self.gamma_correct else 1.0
    
    def Init(self, node_tree=None, compositor_tree=None):
        if node_tree:
            self.node_tree = node_tree
        if compositor_tree:
            self.compositor_tree = compositor_tree
        
        if not self.node_tree:
            self.node_tree = bpy.data.node_groups.new(name=self.name + " - Material", type='ShaderNodeTree')
        if not self.compositor_tree:
            self.compositor_tree = bpy.data.node_groups.new(name=self.name + " - Compositor", type='CompositorNodeTree')
        
        for ndtree in [self.node_tree, self.compositor_tree]:
            [ndtree.nodes.remove(nd) for nd in list(ndtree.nodes)[::-1]]
            
            ndtree.inputs.new('NodeSocketFloat', "Palette Float")
            ndtree.inputs.new('NodeSocketFloat', "Palette Int")
            ndtree.outputs.new('NodeSocketColor', "Color")
            
            NewNode(ndtree, 'NodeFrame', RAMPPALETTESIGNATURE, (0, 400))
            
            NewNode(ndtree, 'NodeGroupInput', "input", (-1000, 0))
            NewNode(ndtree, 'ShaderNodeGamma', "gamma", (300, 0))
            NewNode(ndtree, 'NodeGroupOutput', "output", (500, 0))
            
            nd = NewNode(ndtree, 'ShaderNodeMath', "gt", (-800, 0))
            nd.operation = 'GREATER_THAN'
            nd.inputs[1].default_value = 0.0
            
            nd = NewNode(ndtree, 'ShaderNodeMath', "mul", (-600, 0))
            nd.operation = 'MULTIPLY'
            
            nd = NewNode(ndtree, 'ShaderNodeMath', "madd", (-800, -200))
            nd.operation = 'MULTIPLY_ADD'
            nd.inputs[1].default_value = 1/self.width
            nd.inputs[2].default_value = 0.5/self.width
            
            nd = NewNode(ndtree, 'ShaderNodeMath', "add", (-400, 0))
            nd.operation = 'ADD'
            nd.inputs[1].default_value = 1.0
            
            nd = NewNode(ndtree, 'ShaderNodeMath', "modulo", (-200, 0))
            nd.operation = 'MODULO'
            nd.inputs[1].default_value = 1.0
            
            nd = NewNode(ndtree, 'ShaderNodeCombineXYZ', 'combxyz', (-100, 200))
            
            nd = NewNode(ndtree, 'ShaderNodeTexImage', 'image', (0,200))
            
            LinkNodes(ndtree, "input", 1, "madd", 0)
            LinkNodes(ndtree, "input", 1, "gt", 0)
            LinkNodes(ndtree, "gt", 0, "mul", 0)
            
            LinkNodes(ndtree, "input", 0, "add", 1)
            LinkNodes(ndtree, "madd", 0, "mul", 1)
            LinkNodes(ndtree, "mul", 0, "add", 0)
            
            LinkNodes(ndtree, "add", 0, "modulo", 0)
            
            LinkNodes(ndtree, "modulo", 0, "combxyz", 0)
            LinkNodes(ndtree, 'gamma', 0, 'output', 0)
            LinkNodes(ndtree, 'image', 0, 'gamma', 0)
            
            if ndtree.type != 'COMPOSITING':
                LinkNodes(ndtree, "combxyz", 0, "image", 0)
            
        self.UpdateRamps()
        return self
    
    def Cleanup(self):
        if self.node_tree:
            bpy.data.node_groups.remove(self.node_tree)
        if self.compositor_tree:
            bpy.data.node_groups.remove(self.compositor_tree)
        if self.image:
            bpy.data.images.remove(self.image)
    
    # Slot Data
    def GetSlot(self, index):
        return self.slots[index] if self.slots else None
    
    def ActiveSlot(self):
        return self.slots[self.ramp_index] if self.slots else None
    
    def CopySlotIndex(self, source_index, target_index):
        slot1 = self.slots[source_index]
        slot2 = self.slots[target_index]
        
        self.CopySlot(slot1, slot2)
    
    def CopySlot(self, source_slot, target_slot):
        for x, e in enumerate(target_slot.colors):
            e.color = source_slot.colors[x].color
    
    def AddSlot(self):
        active = self.ActiveSlot()
        self.height += 1
        
        if active:
            self.CopySlot(active, self.slots[-1])
    
    def RemoveSlot(self, index):
        if self.height > 0:
            ser = [[tuple(e.color) for e in s.colors] for s in self.slots]
            
            self.slots.remove(index)
            self.height -= 1
            self.DrawImage()
            
            for y, slot in enumerate(self.slots):
                for x, e in enumerate(slot.colors):
                    e.color = ser[y][x]
    
    def MoveSlot(self, index, offset):
        slot1 = self.slots[index]
        slot2 = self.slots[(index+offset) % self.height]
        
        e1 = [tuple(e.color) for e in slot1.colors]
        e2 = [tuple(e.color) for e in slot2.colors]
        
        for i in range(0, self.width):
            slot1.colors[i].color = e2[i]
            slot2.colors[i].color = e1[i]
        
        labels = (slot1.name, slot2.name)
        slot1.name = labels[1]
        slot2.name = labels[0]
    
    def Resize(self, width=0, height=0):
        if height > 0:
            self.height = height
        if width > 0:
            self.width = width
    
    def ShiftElement(self, index, shift=1):
        i = self.color_index if index == None else index
        
        for slot in self.slots:
            elements = list(slot.colors)
            e1, e2 = (elements[i], elements[(i+shift) % self.width])
            p = tuple(e1.color)
            e1.color = e2.color
            e2.color = p
        
        if index == None:
            self.color_index = (i+shift) % self.width
    
    def UpdateRamps(self, context=None):
        if self.slots:
            lastwidth = len(self.slots[0].colors)
            lastheight = len(self.slots)
        else:
            lastwidth = 0
            lastheight = 0
        
        # Image
        if not self.image:
            image = bpy.data.images.new(self.name, self.width, self.height, alpha=True)
            image.colorspace_settings.name = 'Linear'
            image.file_format = 'PNG'
            #image.extension = 'EXTEND'
            image.update()
            
            self.image = image
            self.node_tree.nodes['image'].image = self.image
        
        if self.image.size[0] != self.width or self.image.size[1] != self.height:
            self.image.scale(self.width, self.height)
            self.DrawImage()
        
        # Fix height
        while len(self.slots) < self.height:
            slots = self.slots.add()
            self.CopySlot(self.slots[lastheight-1], self.slots[-1])
        while len(self.slots) > self.height:
            self.slots.remove(len(self.slots)-1)
        
        # Fix width
        for y, slot in enumerate(self.slots):
            while len(slot.colors) < self.width:
                slot.colors.add()
            while len(slot.colors) > self.width:
                slot.colors.remove(len(slot.colors)-1)
            
            for x,color in enumerate(slot.colors):
                color.xy = (x,y)
                color.image = self.image
        
        self.color_index = max(0, min(self.width-1, self.color_index))
        self.ramp_index = max(0, min(self.height-1, self.ramp_index))
        
        for index, ndtree in enumerate([self.node_tree, self.compositor_tree]):
            if ndtree:
                nd = ndtree.nodes['madd']
                nd.inputs[1].default_value = 1/self.width
                nd.inputs[2].default_value = 0.5/self.width
                ndtree.nodes['combxyz'].inputs[1].default_value = (0.5 + self.ramp_index)/self.height
        
        # Resize UVS
        if self.collection and (lastwidth > 0 and lastheight > 0) and (lastwidth != self.width or lastheight != self.height):
            xdiv = float(lastwidth) / float(self.width)
            ydiv = float(lastheight) / float(self.height)
            
            for obj in self.collection.all_objects:
                if obj.type != 'MESH':
                    continue
                if 'palette' not in obj.data.uv_layers.keys():
                    continue
                
                uvlyr = obj.data.uv_layers['palette']
                
                if not uvlyr.data:
                    continue
                
                lastuv = tuple(uvlyr.data[0].uv)
                
                break
                
                for uv in uvlyr.data:
                    uv.uv = (
                        (uv.uv[0] * xdiv),
                        (uv.uv[1] * ydiv)
                    )
                print(obj.name, lastuv, tuple(uvlyr.data[0].uv))
            print(((lastwidth, lastheight), (self.width, self.height)))
        
    def UpdateRampIndex(self):
        if self.height > 0:
            index = self.ramp_index % self.height
            if index != self.ramp_index:
                self.ramp_index = index
            for compositor, ndtree in enumerate([self.node_tree, self.compositor_tree]):
                ndtree.nodes['combxyz'].inputs[1].default_value = (0.5 + self.ramp_index)/self.height
    
    def FromImage(self, image):
        self.width = image.size[0]
        self.height = image.size[1]
        n = self.width * self.height
        
        pixels = tuple(image.pixels)
        
        rows = [
            [
                tuple(pixels[ (cy*self.width + cx) * 4: (cy*self.width + (cx+1)) * 4 ])
                for cx in range(0, self.width)
            ]
            for cy in range(0, self.height)
        ]
        
        rows = [
            [
                list(mathutils.Color(color[:3]).from_srgb_to_scene_linear())+[color[3]]
                #list(mathutils.Color(color[:3]))+[color[3]]
                for color in r
            ]
            for r in rows
        ][::-1]
        
        # Write to colors
        for r, slot in enumerate(self.slots):
            for c,color in enumerate(slot.colors):
                color.color = rows[r][c]
    
    def ToImage(self, image):
        image.scale(self.width, self.height)
        image.pixels = tuple(
            x
            for ramp in list(self.slots)[::-1]
            for e in ramp.colors
            for x in e.color
        )
    
    def DrawImage(self, do_update=True):
        if do_update:
            self.UpdateRamps()
        for slot in self.slots:
            for color in slot.colors:
                color.color = color.color
    
    def WriteToColors(self, objects):
        objects = list(set(objects))
        
        mode = bpy.context.object.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        for obj in objects:
            if obj.type == 'MESH':
                if obj.data.color_attributes and 'palette' in list(obj.data.uv_layers.keys()):
                    lyr = obj.data.color_attributes.active_color
                    uvlyr = obj.data.uv_layers['palette']
                    
                    targetvertices = tuple([v.index for v in obj.data.vertices if v.select])
                    targetloops = [l for p in obj.data.polygons if (p.select and not p.hide) for l in p.loop_indices]
                    targetloops += [l.index for l in obj.data.loops if l.vertex_index in targetvertices]
                    
                    for l in targetloops:
                        lyr.data[l].color = self.EvaluateColor(uvlyr.data[l].uv[0])
        
        bpy.ops.object.mode_set(mode=mode)
        
    def EvaluateColor(self, x, slot_index=None):
        if slot_index == None:
            slot_index = self.ramp_index
        
        pos = (x * self.width - 0.5)
        pos = max(0, min(pos, self.width-1))
        
        amt = pos - int(pos)
        col1 = self.slots[slot_index].colors[math.floor(pos)].color
        col2 = self.slots[slot_index].colors[math.ceil(pos)].color
        
        return mathutils.Vector(col1).lerp(col2, amt)
    
    def FindColorIndex(self, colorvec):
        colorvec = mathutils.Vector(colorvec)
        vecsize = len(colorvec)
        slotcolors = [(i, mathutils.Vector(element.color)) for i,element in enumerate(self.ActiveSlot().colors)]
        slotcolors.sort(key=lambda x: (mathutils.Vector(x[1][:vecsize])-colorvec).length_squared)
        
        return slotcolors[0][0]
    
    def BuildFromObjects(self, objects, use_polygons=True):
        objects = [obj for obj in objects if obj.type == 'MESH']
        
        allcolors = [
            mathutils.Vector(vc.color[:3])
            for obj in objects if obj.data.color_attributes.active_color
            for vc in obj.data.color_attributes.active_color.data
        ]
        
        for c in allcolors:
            c.freeze()
        
        uniquecolors = list(set(allcolors))
        uniquecolors.sort(key=lambda vc: -allcolors.count(vc))
        
        print([allcolors.count(vc) for vc in uniquecolors][:20])
        
        for i, element in enumerate(self.ActiveSlot().colors[:min(self.width, len(uniquecolors))]):
            element.color = list(uniquecolors[i]) + [1]*(4-len(uniquecolors[i]))
    
    def VCToUVs(self, objects):
        objects = [obj for obj in objects if obj.type == 'MESH']
        
        for obj in objects:
            uvlayers = obj.data.uv_layers
            if "palette" not in uvlayers.keys():
                uvlayers.new(name="palette")
                for uv in uvlayers.data:
                    uv.uv = (0, 0)
            uvlyr = uvlayers["palette"].data
            vclyr = obj.data.color_attributes.active_color.data
            
            for l in range(0, len(uvlyr)):
                uvlyr[l].uv[0] = (self.FindColorIndex(vclyr[l].color[:3]) + 0.5) / self.width
        
classlist.append(RampPalette_NodeGroup)

# -------------------------------------------------------------------

class RampPalette_Master(bpy.types.PropertyGroup):
    data : bpy.props.CollectionProperty(type=RampPalette_NodeGroup)
    data_index : bpy.props.IntProperty(name='Index')
    display_mode : bpy.props.EnumProperty(name='Display Mode', 
        items=(
            ('RAMP', "Active Ramp", "Show all colors for active slot"),
            ('COLOR', "Active Color", "Show all ramp colors for active color index")
    ))
    
    def Add(self):
        return self.data.add().Init()
    
    def Remove(self, index):
        self.data[index].Cleanup()
        self.data.remove(index)
        self.data_index = max(0, min(self.data_index, len(self.data)-1))
    
    def Active(self):
        return self.data[self.data_index] if self.data else None
    
    def SearchNodeGroups(self):
        for ng in bpy.data.node_groups:
            if ng not in [x.node_tree for x in self.data]:
                if sum([1 for nd in ng.nodes if nd.label == '<RAMP_PALETTE>']):
                    image = None
                    for nd in ng.nodes:
                        if nd.type == 'TEX_IMAGE':
                            if nd.image:
                                image = nd.image
                                break
                                
                    entry = self.data.add()
                    
                    entry.Init(node_tree=ng)
                    entry.name = ng.name
                    
                    if image:
                        entry.FromImage(image)
                    
        
classlist.append(RampPalette_Master)

"# ============================================================================================"
"# OPERATORS"
"# ============================================================================================"

class RampPalette_OP(bpy.types.Operator):
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return 1

# -------------------------------------------------------------------
class RAMPPALETTE_OP_Palette_Init(RampPalette_OP): 
    """Initialize palette to default"""
    bl_idname = "ramppalette.palette_init"
    bl_label = "Initialize Palette"
    
    def execute(self, context):
        context.scene.ramp_palettes.Active().Init()
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_Palette_Init)

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
    bl_label = "Add Slot"
    
    def execute(self, context):
        context.scene.ramp_palettes.Active().AddSlot()
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_Ramp_Add)

# -------------------------------------------------------------------
class RAMPPALETTE_OP_Ramp_Remove(RampPalette_OP): 
    """Removes ramp from palette"""
    bl_idname = "ramppalette.ramp_remove"
    bl_label = "Remove Slot"
    index : bpy.props.IntProperty()
    
    def execute(self, context):
        context.scene.ramp_palettes.Active().RemoveSlot(self.index)
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_Ramp_Remove)

# -------------------------------------------------------------------
class RAMPPALETTE_OP_Ramp_Move(RampPalette_OP): 
    """Moves ramp"""
    bl_idname = "ramppalette.ramp_move"
    bl_label = "Move Slot"
    index : bpy.props.IntProperty()
    offset : bpy.props.IntProperty()
    
    def execute(self, context):
        context.scene.ramp_palettes.Active().MoveSlot(self.index, self.offset)
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_Ramp_Move)

# -------------------------------------------------------------------
class RAMPPALETTE_OP_Ramp_DrawImage(RampPalette_OP): 
    """Recalculates internal values and redraw images"""
    bl_idname = "ramppalette.ramp_draw_image"
    bl_label = "Refresh Palette"
    
    def execute(self, context):
        context.scene.ramp_palettes.Active().DrawImage()
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_Ramp_DrawImage)

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

# -------------------------------------------------------------------
class RAMPPALETTE_OP_Set_UV(RampPalette_OP): 
    """Sets palette index"""
    bl_idname = "ramppalette.set_uv"
    bl_label = "Set Palette Color"
    bl_options = {'REGISTER', 'UNDO'}
    
    index : bpy.props.FloatProperty(name="Index", step=100, precision=2, min=0, max=32)
    coordinate : bpy.props.EnumProperty(name="Coordinate", default='X', items=(
        ('X', 'X', 'Set UV X coordinate'),
        ('Y', 'Y', 'Set UV Y coordinate'),
    ))
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'index')
        r = layout.row()
        r.label(text="Coordinate")
        r.prop(self, 'coordinate', expand=True)
    
    def execute(self, context):
        mode = context.object.mode
        bpy.ops.object.mode_set(mode="OBJECT")
        
        active = context.scene.ramp_palettes.Active()
        palvalue = (self.index + 0.5) / active.width
        
        for obj in list(set(list(context.selected_objects) + [context.object])):
            if obj.type != 'MESH':
                continue
            if "palette" not in obj.data.uv_layers:
                lyr = obj.data.uv_layers.new(name="palette")
                for uv in lyr.data:
                    uv.uv = (0, 0)
            lyrdata = obj.data.uv_layers['palette'].data
            
            vertices = tuple(obj.data.vertices)
            loops = tuple(obj.data.loops)
            
            looppool = [l for p in obj.data.polygons if (not p.hide) for l in p.loop_indices]
            targetpolys = tuple([p for p in obj.data.polygons if (p.select and not p.hide)])
            usedvertices = tuple([v for p in targetpolys for v in p.vertices])
            targetloops = [l for p in targetpolys for l in p.loop_indices]
            targetloops += [l.index for l in loops if (vertices[l.vertex_index].select and l.vertex_index not in usedvertices)]
            
            targetloops = [l for l in targetloops if l in looppool]
            
            print(len(targetloops))
            
            if self.coordinate == 'X':
                for l in tuple(targetloops):
                    lyrdata[l].uv[0] = palvalue
            else:
                for l in tuple(targetloops):
                    lyrdata[l].uv[1] = palvalue
        
        bpy.ops.object.mode_set(mode=mode)
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_Set_UV)

# ----------------------------------------------------------------------------------
class RAMPPALETTE_OP_UVFromProperty(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "ramppalette.uv_from_object_property"
    bl_label = "Palette Color From Object Property"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        mode = context.object.mode
        bpy.ops.object.mode_set(mode="OBJECT")
        
        active = context.scene.ramp_palettes.Active()
        
        for obj in context.selected_objects:
            print(obj.name)
            for k in obj.keys():
                if k.lower() == 'palette':
                    uv = ( (obj[k] + 0.5) / active.width, 0.0 )
                    
                    if "palette" not in obj.data.uv_layers:
                        obj.data.uv_layers.new(name="palette")
                    lyrdata = obj.data.uv_layers['palette'].data
                    
                    for l in lyrdata:
                        l.uv = uv
                    break
        
        bpy.ops.object.mode_set(mode=mode)
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_UVFromProperty)

# -------------------------------------------------------------------
class RAMPPALETTE_OP_MoveColor(RampPalette_OP): 
    """Sets palette index"""
    bl_idname = "ramppalette.move_color"
    bl_label = "Set Palette Color"
    bl_options = {'REGISTER', 'UNDO'}
    
    index : bpy.props.IntProperty()
    offset : bpy.props.IntProperty(default=1)
    all_ramps : bpy.props.BoolProperty(default=True)
    
    def execute(self, context):
        mode = context.object.mode
        bpy.ops.object.mode_set(mode="OBJECT")
        
        active = context.scene.ramp_palettes.Active()
        active.ShiftElement(self.index, self.offset)
        
        uvx1 = (self.index + 0.5) / active.width
        uvx2 = (self.index + self.offset + 0.5) / active.width
        uvw = 1/active.width
        
        for obj in active.GetObjects():
            if "palette" not in obj.data.uv_layers:
                obj.data.uv_layers.new(name="palette")
            
            for uv in obj.data.uv_layers['palette'].data:
                if uv.uv[0] == uvx1:
                    uv.uv[0] = uvx2
                elif uv.uv[0] == uvx2:
                    uv.uv[0] = uvx1
        
        bpy.ops.object.mode_set(mode=mode)
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_MoveColor)

# ----------------------------------------------------------------------------------
class RAMPPALETTE_OP_FromImage(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "ramppalette.from_image"
    bl_label = "Import Palette From Image"
    bl_options = {'REGISTER', 'UNDO'}
    
    image : bpy.props.StringProperty(name="Image")
    
    @classmethod
    def poll(self, context):
        return context.scene.ramp_palettes.Active()
        
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        
        c = layout.column()
        c.prop_search(self, 'image', bpy.data, 'images')
    
    def execute(self, context):
        image = bpy.data.images[self.image]
        context.scene.ramp_palettes.Active().FromImage(image)
        self.report({'INFO'}, 'Palette read from "%s"' % image.name)
        
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_FromImage)

# ----------------------------------------------------------------------------------
class RAMPPALETTE_OP_Import(bpy.types.Operator, ImportHelper):
    """Tooltip"""
    bl_idname = "ramppalette.import"
    bl_label = "Import Palette from File"
    bl_options = {'REGISTER', 'UNDO'}
    
    filename_ext = ".png"
    filter_glob: bpy.props.StringProperty(default="*"+filename_ext, options={'HIDDEN'}, maxlen=255)
    
    gamma_correct : bpy.props.BoolProperty(name="Gamma Corrected", default=True)
    
    @classmethod
    def poll(self, context):
        return context.scene.ramp_palettes.Active()
    
    def execute(self, context):
        image = bpy.data.images.load(self.filepath, check_existing=False)
        image.colorspace_settings.name = 'sRGB' if self.gamma_correct else 'Linear'
        context.scene.ramp_palettes.Active().FromImage(image)
        bpy.data.images.remove(image)
        self.report({'INFO'}, 'Palette read from "%s"' % self.filepath)
        
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_Import)

# ----------------------------------------------------------------------------------
class RAMPPALETTE_OP_Export(bpy.types.Operator, ExportHelper):
    """Tooltip"""
    bl_idname = "ramppalette.export"
    bl_label = "Export Palette to File"
    bl_options = {'REGISTER', 'UNDO'}
    
    filename_ext = ".png"
    filter_glob: bpy.props.StringProperty(default="*"+filename_ext, options={'HIDDEN'}, maxlen=255)
    
    @classmethod
    def poll(self, context):
        return context.scene.ramp_palettes.Active()
    
    def execute(self, context):
        palette = context.scene.ramp_palettes.Active()
        
        image = bpy.data.images.new("__temp_ramppalette", palette.width, palette.height, alpha=True)
        image.colorspace_settings.name = 'sRGB' if palette.gamma_correct else 'Linear'
        image.filepath = self.filepath
        image.file_format = 'PNG'
        image.update()
        context.scene.ramp_palettes.Active().ToImage(image)
        image.save()
        bpy.data.images.remove(image)
        self.report({'INFO'}, 'Palette saved to "%s"' % self.filepath)
        
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_Export)

# ----------------------------------------------------------------------------------
class RAMPPALETTE_OP_SearchNodeGroups(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "ramppalette.search_node_groups"
    bl_label = "Search Node Groups"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        context.scene.ramp_palettes.SearchNodeGroups()
        
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_SearchNodeGroups)

# ----------------------------------------------------------------------------------
class RAMPPALETTE_OP_WriteToVC(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "ramppalette.write_to_vcolors"
    bl_label = "Write To Vertex Colors"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        context.scene.ramp_palettes.Active().WriteToColors(context.selected_objects)
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_WriteToVC)

# ----------------------------------------------------------------------------------
class RAMPPALETTE_OP_BuildFromVC(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "ramppalette.build_from_vc"
    bl_label = "Build Slot From VC"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        context.scene.ramp_palettes.Active().BuildFromObjects(context.selected_objects)
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_BuildFromVC)

# ----------------------------------------------------------------------------------
class RAMPPALETTE_OP_VCToUVs(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "ramppalette.vc_to_uvs"
    bl_label = "Vertex Colors to Palette UVs"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        context.scene.ramp_palettes.Active().VCToUVs(context.selected_objects)
        return {'FINISHED'}
classlist.append(RAMPPALETTE_OP_VCToUVs)

'# ================================================================================================================='
'# PANELS'
'# ================================================================================================================='

class RAMPPALLETTE_UL_PaletteList(bpy.types.UIList):
    def draw_item(self, _context, layout, _data, item, icon, _active_data_, _active_propname, _index):
        r = layout.row()
        r.prop(item, "name", text="", emboss=False, icon_value=icon)
        r.operator('ramppalette.palette_remove', text="", icon='REMOVE').index=_index
classlist.append(RAMPPALLETTE_UL_PaletteList)

# -------------------------------------------------------------------

class RAMPPALETTE_PT_RampPalettePanel(bpy.types.Panel):
    bl_label = "Ramp Palettes"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Edit" # Name of sidebar
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        master = context.scene.ramp_palettes
        layout = self.layout
        
classlist.append(RAMPPALETTE_PT_RampPalettePanel)

# -------------------------------------------------------------------

class RAMPPALETTE_PT_RampPalettePanel_Characters(bpy.types.Panel):
    bl_label = "Node Groups"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Edit" # Name of sidebar
    bl_parent_id = 'RAMPPALETTE_PT_RampPalettePanel'
    
    def draw(self, context):
        master = context.scene.ramp_palettes
        layout = self.layout
        
        r = layout.row()
        r.operator('ramppalette.palette_add', icon='ADD')
        r.operator('ramppalette.search_node_groups', icon='ZOOM_SELECTED', text="")
        
        # Palette List
        layout.template_list("RAMPPALLETTE_UL_PaletteList", "", master, 'data', master, "data_index", rows=4)
    
classlist.append(RAMPPALETTE_PT_RampPalettePanel_Characters)

# -------------------------------------------------------------------

class RAMPPALETTE_PT_RampPalettePanel_ActiveCharacter(bpy.types.Panel):
    bl_label = "Active Palette"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Edit" # Name of sidebar
    bl_parent_id = 'RAMPPALETTE_PT_RampPalettePanel'
    
    def draw(self, context):
        master = context.scene.ramp_palettes
        layout = self.layout
        
        # Ramp list
        b = layout.column()
        ramppalette = master.Active()
        
        if ramppalette:
            b.prop(ramppalette, 'collection', text="")
            
            c = b.column()
            
            r = c.row()
            r.operator('ramppalette.from_image', text="From Image")
            r.operator('ramppalette.import', text="Import Image")
            r.operator('ramppalette.export', text="Export Image")
            
            r = c.row()
            rr = r.row(align=1)
            rr.prop(ramppalette, 'width')
            rr.prop(ramppalette, 'height')
            r.prop(ramppalette, 'gamma_correct', text="", icon='CON_TRANSLIKE', toggle=1)
            r.operator('ramppalette.ramp_draw_image', text="", icon='FILE_REFRESH')
            
            r = c.row()
            r.operator('ramppalette.ramp_add', icon='ADD')
            
            # Draw Active Elements
            b = layout.box()
            
            c = b.column()
            active = ramppalette.ActiveSlot()
            
            if active:
                r = c.row(align=0)
                r.prop(ramppalette, 'ramp_index', text="")
                r = r.row(align=1)
                r.scale_x = 2
                r.prop(active, 'name', text="")
                
                bb = b.box().column(align=1)
                
                c = r.column(align=0)
                
                for i, e in enumerate(active.colors):
                    if (i % 8) == 0:
                        r = bb.row(align=1)
                    c = r.column(align=0)
                    
                    rr = c.row(align=1)
                    rr.prop(e, 'color', text="")
                    rr.operator('ramppalette.set_uv', text='', icon='BRUSH_DATA').index=i
                    
                    rr = c.row(align=1)
                    rr.scale_y = 0.5
                    op = rr.operator('ramppalette.move_color', text='', icon='TRIA_LEFT')
                    op.index = i
                    op.offset = -1
                    op = rr.operator('ramppalette.move_color', text='', icon='TRIA_RIGHT')
                    op.index = i
                    op.offset = 1
            
classlist.append(RAMPPALETTE_PT_RampPalettePanel_ActiveCharacter)

# ------------------------------------------------------------------------------------------

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
            
            for i, slot in enumerate(ramppalette.slots):
                c = layout.column(align=1)
                
                r = c.row(align=0)
                rr = r.row(align=1)
                rr.prop(slot, "name", text="")
                
                rr = r.row(align=1)
                rr.operator('ramppalette.ramp_remove', text="", icon='REMOVE').index = i
                
                cc = rr.column(align=1)
                cc.scale_y=0.5
                
                op = cc.operator('ramppalette.ramp_move', text="", icon='TRIA_UP')
                op.index = i
                op.offset = -1
                op = cc.operator('ramppalette.ramp_move', text="", icon='TRIA_DOWN')
                op.index = i
                op.offset = 1
                
                cc = c.column(align=1)
                cc.scale_y = 0.7
                
                rr = cc.row(align=1)
                
                for e in slot.colors:
                    rr.prop(e, 'color', text="")
    
classlist.append(RAMPPALETTE_PT_RampPalettePanel_Ramps)

'# ================================================================================================================='
'# REGISTER'
'# ================================================================================================================='

def register():
    for c in classlist:
        bpy.utils.register_class(c)
    
    bpy.types.Scene.ramp_palettes = bpy.props.PointerProperty(name='Ramp Palette Master', type=RampPalette_Master)

def unregister():
    for c in classlist[::-1]:
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()

# Run on file start
bpy.data.texts[__file__[__file__.rfind("\\")+1:]].use_module = True


for palette in bpy.context.scene.ramp_palettes.data:
    palette.DrawImage()
