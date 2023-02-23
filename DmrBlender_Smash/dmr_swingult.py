bl_info = {
    'name': 'Smush Swing Editor',
    'description': 'An interface to open and edit swing xml files for Smush modding.\nPRC to XML converter by BenHall-7 can be found here: https://github.com/BenHall-7/paracobNET/releases',
    'author': 'Dreamer13sq',
    'version': (0, 2),
    'blender': (3, 0, 0),
    'category': 'User Interface',
    'support': 'COMMUNITY',
    'doc_url': 'https://github.com/Dreamer13sq/DmrBlenderTools/wiki/Swing-Params-Editor'
}

import bpy
import xml.etree.ElementTree as ET
import csv
import math
import mathutils
import bmesh

from bpy_extras.io_utils import ImportHelper, ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

"""
    Shape Key Displacement
        x -> y
        y -> x
        z -> z
    
    Hashes must be a valid string in ParamLabels.csv
    
    Swing Bone Entries with more params than bones in chain will crash the game
    
    Swing Bones in armature NEED a "null" bone at the end
    
    Swing Bones matter in bone order. Keep all original bones from vanilla mesh
    
    Swing Bones in the label list that have a "__swing" suffix counterpart may break swing physics in game
"""

print("="*80)

classlist = []

SUBPANELLABELSPACE = "    ^ "
TABSTRING = "  "
VISUALSHAPESCALE = 10

STRUCTTYPENAMES = (
    'BONE', 'SPHERE', 'OVAL', 'ELLIPSOID', 'CAPSULE', 'PLANE', 'CONNECTION', 'GROUP'
)

SHAPENAMES = (
    'SPHERE', 'OVAL', 'ELLIPSOID', 'CAPSULE', 'PLANE'
)

STRUCTICONS = {
    'BONE': 'BONE_DATA',
    'SPHERE': 'MESH_UVSPHERE',
    'OVAL': 'META_BALL',
    'ELLIPSOID': 'META_ELLIPSOID',
    'CAPSULE': 'MESH_CAPSULE',
    'PLANE': 'MESH_PLANE',
    'CONNECTION': 'OUTLINER_DATA_CURVE',
    'GROUP': 'GROUP',
}

Items_MoveDirection = tuple([
    ('DOWN', "Down", "Move Down"),
    ('UP', "Up", "Move Up"),
    ('BOTTOM', "Bottom", "Move to End of List"),
    ('TOP', "Top", "Move to Top of List")
])

Items_StructType = tuple([
    (x, x[0] + x[1:].lower(), x.lower())
    for x in STRUCTTYPENAMES
])

def SwingEditItems_Active(self, context):
    return (
        [(x.name, x.name + " (Active)", x.name) for x in context.scene.swing_ultimate.data if x == context.scene.swing_ultimate.GetActiveData()] + 
        [(x.name, x.name, x.name) for x in context.scene.swing_ultimate.data if x != context.scene.swing_ultimate.GetActiveData()]
    )

def SwingSceneNames(self=None, context=bpy.context):
    return [
        (str(i), x.name, x.name) for i,x in enumerate(context.scene.swing_ultimate.data)
    ]

"========================================================================================================="

def SerializeValue(vartype, attribname, attribvalue, value, tabs=0):
    return TABSTRING*tabs + '<{0} {1}="{2}">{3}</{0}>'.format(vartype, attribname, attribvalue, value) + "\n"

def SerializeFloat(hash, value, tabs=0):
    return SerializeValue('float', "hash", hash, value, tabs)

def SerializeSbyte(hash, value, tabs=0):
    return SerializeValue('sbyte', "hash", hash, value, tabs)

def SerializeInt(hash, value, tabs=0):
    return SerializeValue('int', "hash", hash, value, tabs)

def SerializeString(hash, value, tabs=0):
    return SerializeValue('hash40', "hash", hash, value, tabs)

def SerializeList(hash, collectionprop, tabs=0):
    if len(collectionprop) > 0:
        return (
            TABSTRING*tabs + '<list size="{0}" hash="{1}">\n'.format(len(collectionprop), hash) +
            "".join([ x.Serialize(tabs+1, i) for i,x in enumerate(collectionprop) ]) +
            TABSTRING*tabs + '</list>\n'
            )
    else:
        return TABSTRING*tabs + '<list size="{0}" hash="{1}" />\n'.format(len(collectionprop), hash)
    
def SerializeListOfStructs(hash, collectionprop, tabs=0):
    if len(collectionprop) > 0:
        return (
            TABSTRING*tabs + '<list size="{0}" hash="{1}">\n'.format(len(collectionprop), hash) +
            "".join([ SerializeStruct(x, tabs+1, i) for i,x in enumerate(collectionprop) ]) +
            TABSTRING*tabs + '</list>\n'
            )
    else:
        return TABSTRING*tabs + '<list size="{0}" hash="{1}" />\n'.format(len(collectionprop), hash)

def SerializeStruct(structentry, tabs=0, index=-1):
    return (
        TABSTRING*tabs + "<struct" + (' index="{0}"'.format(index) if index>=0 else "") + ">\n" +
        structentry.Serialize(tabs+1) +
        TABSTRING*tabs + "</struct>\n"
    )

"========================================================================================================="

def DrawStructUIList(layout, active_prc, type, list_pt, collectionprop_name, index_name):
    r = layout.row(align=True)
    swing_ultimate = bpy.context.scene.swing_ultimate
    
    r.template_list(list_pt, "", active_prc, collectionprop_name, active_prc, index_name, rows=5)
    
    c = r.column(align=True)
    c.operator('swingult.struct_add', text="", icon='ADD').type = type
    c.operator('swingult.struct_remove', text="", icon='REMOVE').type = type
    
    c.separator()
    op = c.operator('swingult.struct_move', text="", icon='TRIA_UP')
    op.type = type
    op.direction = 'UP'
    op = c.operator('swingult.struct_move', text="", icon='TRIA_DOWN')
    op.type = type
    op.direction = 'DOWN'
    
    c.separator()
    op = c.operator('swingult.struct_transfer', text="", icon='PASTEDOWN')
    op.type = type

"========================================================================================================="

def XMLValue(element, typename, hashname):
    for el in element.findall(typename):
        if el.get("hash") == hashname:
            return el.text

def XMLValueAny(element, hashname):
    for typename in ['int', 'sbyte', 'byte', 'float', 'hash40']:
        for el in element.findall(typename):
            if el.get("hash") == hashname:
                return el.text
    print("WARNING: No value found for \"%s\"" % hashname)
    return 0

def XMLValueByHash(element, hashname):
    for el in element.findall('hash40')+element.findall('float'):
        if el.attrib["hash"] == hashname:
            return el.text

def XMLElement(element, typename, hashname):
    for el in element.findall(typename):
        if el.get("hash") == hashname:
            return el

def XMLToSwingEdit(self, context, path):
    xml = ET.parse(path)
    
    armatureobject = context.object
    collection = bpy.context.collection
    
    prc = context.scene.swing_ultimate.GetActiveData()
    prc.Clear()
    swingmap = {}
    
    for el in xml.getroot():
        # Swing Bones
        if el.attrib["hash"] == "swingbones":
            for struct_def in el.findall("struct"):
                entry = prc.AddStruct('BONE')
                entry.name = XMLValue(struct_def, 'hash40', "name")
                entry.start_bonename = XMLValue(struct_def, 'hash40', "start_bonename")
                entry.end_bonename = XMLValue(struct_def, 'hash40', "end_bonename")
                entry.isskirt = int(XMLValueAny(struct_def, "isskirt"))
                entry.rotateorder = int(XMLValueAny(struct_def, "rotateorder"))
                entry.curverotatex = int(XMLValueAny(struct_def, "curverotatex"))
                unknown_0x0f7316a113 = XMLValueAny(struct_def, "0x0f7316a113")
                
                if unknown_0x0f7316a113:
                    entry.unknown_0x0f7316a113 = int(unknown_0x0f7316a113)
                
                for param_def in XMLElement(struct_def, "list", "params"):
                    paramentry = entry.AddParams()
                    
                    paramentry.airresistance = float(XMLValue(param_def, 'float', "airresistance"))
                    paramentry.waterresistance = float(XMLValue(param_def, 'float', "waterresistance"))
                    paramentry.minanglez = float(XMLValue(param_def, 'float', "minanglez"))
                    paramentry.maxanglez = float(XMLValue(param_def, 'float', "maxanglez"))
                    paramentry.minangley = float(XMLValue(param_def, 'float', "minangley"))
                    paramentry.maxangley = float(XMLValue(param_def, 'float', "maxangley"))
                    paramentry.collisionsizetip = float(XMLValue(param_def, 'float', "collisionsizetip"))
                    paramentry.collisionsizeroot = float(XMLValue(param_def, 'float', "collisionsizeroot"))
                    paramentry.frictionrate = float(XMLValue(param_def, 'float', "frictionrate"))
                    paramentry.goalstrength = float(XMLValue(param_def, 'float', "goalstrength"))
                    unknown_0x0cc10e5d3a = XMLValue(param_def, 'float', "0x0cc10e5d3a")
                    if unknown_0x0cc10e5d3a:
                        paramentry.unknown_0x0cc10e5d3a = float(unknown_0x0cc10e5d3a)
                    paramentry.localgravity = float(XMLValue(param_def, 'float', "localgravity"))
                    paramentry.fallspeedscale = float(XMLValue(param_def, 'float', "fallspeedscale"))
                    paramentry.groundhit = int(XMLValue(param_def, 'sbyte', "groundhit"))
                    paramentry.windaffect = float(XMLValue(param_def, 'float', "windaffect"))
                    
                    for collision_def in XMLElement(param_def, "list", "collisions"):
                        paramentry.AddCollision( collision_def.text )
                
        # Spheres
        elif el.attrib["hash"] == "spheres":
            for struct_def in el.findall("struct"):
                entry = prc.AddStruct('SPHERE')
                entry.name = XMLValue(struct_def, 'hash40', "name")
                entry.bonename = XMLValue(struct_def, 'hash40', "bonename")
                entry.cx = float(XMLValue(struct_def, 'float', "cx"))
                entry.cy = float(XMLValue(struct_def, 'float', "cy"))
                entry.cz = float(XMLValue(struct_def, 'float', "cz"))
                entry.radius = float(XMLValue(struct_def, 'float', "radius"))
                
                
        
        # Ovals
        elif el.attrib["hash"] == "ovals":
            for struct_def in el.findall("struct"):
                entry = prc.AddStruct('OVAL')
                entry.name = XMLValue(struct_def, 'hash40', "name")
                entry.bonename = XMLValue(struct_def, 'hash40', "bonename")
                entry.cx = float(XMLValue(struct_def, 'float', "cx"))
                entry.cy = float(XMLValue(struct_def, 'float', "cy"))
                entry.cz = float(XMLValue(struct_def, 'float', "cz"))
                entry.radius = float(XMLValue(struct_def, 'float', "radius"))
        
        # Ellipsoids
        elif el.attrib["hash"] == "ellipsoids":
            for struct_def in el.findall("struct"):
                entry = prc.AddStruct('ELLIPSOID')
                entry.name = XMLValue(struct_def, 'hash40', "name")
                entry.bonename = XMLValue(struct_def, 'hash40', "bonename")
                entry.cx = float(XMLValue(struct_def, 'float', "cx"))
                entry.cy = float(XMLValue(struct_def, 'float', "cy"))
                entry.cz = float(XMLValue(struct_def, 'float', "cz"))
                entry.rx = float(XMLValue(struct_def, 'float', "rx"))
                entry.ry = float(XMLValue(struct_def, 'float', "ry"))
                entry.rz = float(XMLValue(struct_def, 'float', "rz"))
                entry.sx = float(XMLValue(struct_def, 'float', "sx"))
                entry.sy = float(XMLValue(struct_def, 'float', "sy"))
                entry.sz = float(XMLValue(struct_def, 'float', "sz"))
        
        # Capsules
        elif el.attrib["hash"] == "capsules":
            for struct_def in el.findall("struct"):
                entry = prc.AddStruct('CAPSULE')
                entry.name = XMLValue(struct_def, 'hash40', "name")
                entry.start_bonename = XMLValue(struct_def, 'hash40', "start_bonename")
                entry.end_bonename = XMLValue(struct_def, 'hash40', "end_bonename")
                entry.start_offset_x = float(XMLValue(struct_def, 'float', "start_offset_x"))
                entry.start_offset_y = float(XMLValue(struct_def, 'float', "start_offset_y"))
                entry.start_offset_z = float(XMLValue(struct_def, 'float', "start_offset_z"))
                entry.end_offset_x = float(XMLValue(struct_def, 'float', "end_offset_x"))
                entry.end_offset_y = float(XMLValue(struct_def, 'float', "end_offset_y"))
                entry.end_offset_z = float(XMLValue(struct_def, 'float', "end_offset_z"))
                entry.start_radius = float(XMLValue(struct_def, 'float', "start_radius"))
                entry.end_radius = float(XMLValue(struct_def, 'float', "end_radius"))
        
        # Planes
        elif el.attrib["hash"] == "planes":
            for struct_def in el.findall("struct"):
                entry = prc.AddStruct('PLANE')
                entry.name = XMLValue(struct_def, 'hash40', "name")
                entry.bonename = XMLValue(struct_def, 'hash40', "bonename")
                entry.nx = float(XMLValue(struct_def, 'float', "nx"))
                entry.ny = float(XMLValue(struct_def, 'float', "ny"))
                entry.nz = float(XMLValue(struct_def, 'float', "nz"))
                entry.distance = float(XMLValue(struct_def, 'float', "distance"))
        
        # Connections
        elif el.attrib["hash"] == "connections":
            for struct_def in el.findall("struct"):
                entry = prc.AddStruct('CONNECTION')
                entry.start_bonename = XMLValue(struct_def, 'hash40', "start_bonename")
                entry.end_bonename = XMLValue(struct_def, 'hash40', "end_bonename")
                entry.radius = float(XMLValue(struct_def, 'float', "radius"))
                entry.length = float(XMLValue(struct_def, 'float', "length"))
        
        # Groups
        else:
            entry = prc.AddStruct('GROUP')
            entry.name = el.attrib["hash"]
            
            for group_def in el:
                entry.Add( group_def.text )

"========================================================================================================="

def DriverPropertyVariable(id, data_path, var_name, target_type, target, prop_path, expression):
    if not id.animation_data:
        id.animation_data_create()
    
    d = id.animation_data.drivers.new(data_path).driver
    v = d.variables.new()
    v.name = var_name
    v.type = 'SINGLE_PROP'
    v.targets[0].id_type = target_type
    v.targets[0].id = target
    v.targets[0].data_path = prop_path
    
    d.type = 'SCRIPTED'
    d.expression = expression
    return d
    
def CreateVisualArc(name):
    # Collection
    dataname = "SWINGULT Visuals"
    if dataname not in bpy.data.collections.keys():
        bpy.data.collections.new(name=dataname)
    collection = bpy.data.collections[dataname]
    
    if dataname not in bpy.context.scene.collection.children.keys():
        bpy.context.scene.collection.children.link(collection)
    
    # Curve
    dataname = "SWINGULT_arc"
    
    if name not in bpy.data.curves.keys():
        data = bpy.data.curves.new(type='CURVE', name=dataname)
        data.splines.clear()
        data.resolution_u = 1
        data.bevel_resolution = 0
        spline = data.splines.new('POLY')
        
        n = 16
        spline.use_cyclic_u = False
        spline.points.add(n-len(spline.points)+1)
        
        anglestart = -math.pi/2
        angle = anglestart
        
        for i,p in enumerate(spline.points):
            p.co = (math.cos(angle), math.sin(angle), 0, 1)
            angle += (2*math.pi) / n
        
        spline.points[0].co = (math.cos(anglestart-0.1), math.sin(anglestart-0.1), 0, 1)
        spline.points[-1].co = (math.cos(anglestart+0.1), math.sin(anglestart+0.1), 0, 1)
        
        data.bevel_depth = 1
    
    data = bpy.data.curves[dataname]
    
    # Create Object
    data = bpy.data.curves["SWINGULT_arc"]
    obj = bpy.data.objects.new(name="SWINGULT_arc"+'-'+name, object_data=data.copy())
    collection.objects.link(obj)
    
    obj.show_in_front = True
    obj.display_type = 'WIRE'
    obj.scale[2] = 0
    
    return obj

def CreateVisualShape(name, type):
    # Collection
    dataname = "SWINGULT Visuals"
    if dataname not in bpy.data.collections.keys():
        bpy.data.collections.new(name=dataname)
    collection = bpy.data.collections[dataname]
    
    if dataname not in bpy.context.scene.collection.children.keys():
        bpy.context.scene.collection.children.link(collection)
    
    # Mesh
    dataname = "SWINGULT_" + type
    
    if type in {'SPHERE', 'ELLIPSOID', 'CAPSULE'}:
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(
            bm, 
            u_segments=8, 
            v_segments=8, 
            radius=0.01,
            matrix=mathutils.Matrix.Rotation(math.radians(90.0), 4, 'X'), 
            calc_uvs=False
            )
        mesh = bpy.data.meshes.new(name=dataname)
        bm.to_mesh(mesh)
        bm.free()
    elif type == 'PLANE':
        bm = bmesh.new()
        bmesh.ops.create_grid(
            bm,
            x_segments=1, 
            y_segments=1, 
            size=1,
            calc_uvs=False
            )
        mesh = bpy.data.meshes.new(name=dataname)
        bm.to_mesh(mesh)
        bm.free()
    
    # Create Object
    obj = bpy.data.objects.new(name=dataname+'-'+name, object_data=mesh.copy())
    collection.objects.link(obj)
    
    obj.show_in_front = True
    obj.display_type = 'WIRE'
    
    coindex = [1,0,2]
    cosign = [1,1,1]
    
    # Keys
    if type == 'SPHERE':
        obj.shape_key_add(name='Basis', from_mix=False)
        for v in obj.shape_key_add(name='radius', from_mix=False).data:
            v.co *= 100 * VISUALSHAPESCALE
        for i,c in enumerate('xyz'): # Position
            for v in obj.shape_key_add(name="c"+c, from_mix=False).data:
                v.co[coindex[i]] += 1 * cosign[i] * VISUALSHAPESCALE
    
    elif type == 'ELLIPSOID':
        obj.shape_key_add(name='Basis', from_mix=False)
        for i,c in enumerate('xyz'): # Position
            for v in obj.shape_key_add(name="c"+c, from_mix=False).data:
                v.co[coindex[i]] += 1 * cosign[i] * VISUALSHAPESCALE
        for i,c in enumerate('xyz'): # Rotation (TODO)
            for v in obj.shape_key_add(name="r"+c, from_mix=False).data:
                v.co[coindex[i]] *= 1 * cosign[i] * VISUALSHAPESCALE
        for i,c in enumerate('xyz'): # Scale
            for v in obj.shape_key_add(name="s"+c, from_mix=False).data:
                v.co[coindex[i]] *= 100 * VISUALSHAPESCALE
    
    elif type == 'CAPSULE':
        vertsides = (
            [v.index for v in mesh.vertices if v.co[1] <= 0.001], 
            [v.index for v in mesh.vertices if v.co[1] > 0.001]
        )
        obj.shape_key_add(name='Basis', from_mix=False)
        
        sk = obj.shape_key_add(name="length", from_mix=False).data
        for vi in vertsides[1]:
            sk[vi].co[1] += 1 * VISUALSHAPESCALE
        
        for i,c in enumerate('xyz'): # Start Offset
            sk = obj.shape_key_add(name="start_offset_"+c, from_mix=False).data
            for vi in vertsides[0]:
                sk[vi].co[coindex[i]] += 1 * cosign[i] * VISUALSHAPESCALE
        
        for i,c in enumerate('xyz'): # End Offset
            sk = obj.shape_key_add(name="end_offset_"+c, from_mix=False).data
            for vi in vertsides[1]:
                sk[vi].co[coindex[i]] += 1 * cosign[i] * VISUALSHAPESCALE
        
        sk = obj.shape_key_add(name="start_radius", from_mix=False).data
        for vi in vertsides[0]:
            sk[vi].co *= 100 * VISUALSHAPESCALE
        
        sk = obj.shape_key_add(name="end_radius", from_mix=False).data
        for vi in vertsides[1]:
            sk[vi].co *= 100 * VISUALSHAPESCALE
    
    elif type == 'PLANE':
        obj.shape_key_add(name='Basis', from_mix=False)
        for v in obj.shape_key_add(name='radius', from_mix=False).data:
            v.co *= 100
        for v in obj.shape_key_add(name="distance", from_mix=False).data:
            v.co[coindex[2]] += 1 * cosign[2] * VISUALSHAPESCALE
    
    for key in obj.data.shape_keys.key_blocks:
        key.slider_min = -10
        key.slider_max = 10
        
    return obj

def FlipSmashName(name):
    sidepos = [i for i,c in enumerate(name) if c not in "0123456789_"][-1]
    sidechar = name[sidepos]
    if sidechar in "lrLR":
        return name[:sidepos] + {k:v for k,v in zip("lrLR", "rlRL")}[sidechar] + name[sidepos+1:]
    return name

"================================================================================================"
"SWING DATA CLASSES"
"================================================================================================"

class SwingData_Label(bpy.types.PropertyGroup): # ---------------------------------
    name : bpy.props.StringProperty()
    hex : bpy.props.StringProperty()
classlist.append(SwingData_Label)

class SwingData_Hash40(bpy.types.PropertyGroup): # ---------------------------------
    hash40 : bpy.props.StringProperty()
    
    def Serialize(self, tabs=0, index=0):
        return SerializeValue('hash40', "index", index, self.hash40, tabs)
classlist.append(SwingData_Hash40)

class SwingData_Hash40List(bpy.types.PropertyGroup): # ---------------------------------------
    name : bpy.props.StringProperty()
    data : bpy.props.CollectionProperty(type=SwingData_Hash40)
    active_index : bpy.props.IntProperty()
    size : bpy.props.IntProperty()
    
    def Clear(self):
        self.data.clear()
        self.size = len(self.data)
    
    def Add(self, hashstring):
        entry = self.data.add()
        entry.hash40 = hashstring
        self.size = len(self.data)
        return entry
    
    def Remove(self, index):
        self.data.remove(index)
        self.size = len(self.data)
        self.active_index = max(0, min(self.active_index, self.size-1))
    
    def CopyFromOther(self, other):
        self.Clear()
        for entry in other:
            self.Add(entry.hash40)
    
    def Serialize(self, tabs=0, index=0):
        return SerializeList(self.name, self.data, tabs)
classlist.append(SwingData_Hash40List)

"------------------------------------------------------------------------------------------------"

class SwingData_Swing_Bone_Params(bpy.types.PropertyGroup): # ---------------------------------
    airresistance : bpy.props.FloatProperty()
    waterresistance : bpy.props.FloatProperty()
    minanglez : bpy.props.FloatProperty()
    maxanglez : bpy.props.FloatProperty()
    minangley : bpy.props.FloatProperty()
    maxangley : bpy.props.FloatProperty()
    collisionsizetip : bpy.props.FloatProperty()
    collisionsizeroot : bpy.props.FloatProperty()
    frictionrate : bpy.props.FloatProperty()
    goalstrength : bpy.props.FloatProperty()
    unknown_0x0cc10e5d3a : bpy.props.FloatProperty()
    localgravity : bpy.props.FloatProperty(precision=4)
    fallspeedscale : bpy.props.FloatProperty()
    groundhit : bpy.props.IntProperty() # sbyte
    windaffect : bpy.props.FloatProperty()
    collisions : bpy.props.CollectionProperty(type=SwingData_Hash40)
    
    index_collision : bpy.props.IntProperty()
    
    show_visuals : bpy.props.BoolProperty(name="Show Visuals", default=True)
    object_minanglez : bpy.props.PointerProperty(type=bpy.types.Object)
    object_minangley : bpy.props.PointerProperty(type=bpy.types.Object)
    
    def CreateVisualObjects(self, armature_object, bone_name, prc, swing_bone):
        context = bpy.context
        
        prcindex = list(context.scene.swing_ultimate.data).index(prc)
        sboneindex = list(prc.GetStructList('BONE')).index(swing_bone)
        paramindex = list(swing_bone.params).index(self)
        pose_bone = armature_object.pose.bones[bone_name]
        
        self.RemoveVisualObjects()
        
        for i in (0,1):
            if [self.object_minanglez, self.object_minangley][i]:
                bpy.data.objects.remove([self.object_minanglez, self.object_minangley][i], do_unlink=True)
            
            obj = CreateVisualArc(bone_name)
            if i == 0:
                self.object_minanglez = obj
            else:
                self.object_minangley = obj
            
            obj.name += "_"+"ZY"[i]
            obj["swingname"] = swing_bone.name
            obj["swingbone"] = pose_bone.name
            obj["swingparam"] = paramindex
            
            curve = obj.data
            if i == 1:
                obj.rotation_euler[1] = math.pi / 2.0
            obj.scale *= 1.1
            obj.scale[2] = 0.01
            
            # Drivers
            data_path_start = 'swing_ultimate.data[%d].swingbones[%d].params[%d]' % (prcindex, sboneindex, paramindex)
            
            DriverPropertyVariable(curve, 'bevel_factor_start', "x", "SCENE", context.scene, 
                data_path_start+'.minangle'+'zy'[i],
                '0.5 + x / 360.0'
                )
            DriverPropertyVariable(curve, 'bevel_factor_end', "x", "SCENE", context.scene, 
                data_path_start+'.maxangle'+'zy'[i],
                '0.5 + x / 360.0'
                )
            
            c = obj.constraints.new(type='COPY_TRANSFORMS')
            c.target = armature_object
            c.subtarget = bone_name
            c.mix_mode = 'BEFORE_FULL'
        
    def RemoveVisualObjects(self):
        if self.object_minanglez:
            bpy.data.objects.remove(self.object_minanglez, do_unlink=True)
        if self.object_minangley:
            bpy.data.objects.remove(self.object_minangley, do_unlink=True)
    
    def AddCollision(self, hash=""):
        entry = self.collisions.add()
        entry.hash40 = hash if hash else ""
        return entry
    
    def RemoveCollision(self, index=None):
        if index == None:
            index = self.index_collision
        self.collisions.remove(index)
        
        # Game Crashes at 0 Collisions
        if len(self.collisions) == 0:
            print("> %s has 0 Collisions!" % "Params")
        
        self.index_collision = max(0, min(self.index_collision, len(self.collisions)-1))
    
    def MoveCollision(self, direction):
        structlist = self.collisions
        structindex = self.index_collision
        n = len(structlist)
        
        if n > 1:
            newindex = structindex
            if direction == 'DOWN':
                newindex = (structindex+1) % n
            elif direction == 'UP':
                newindex = (structindex-1) % n
            elif direction == 'BOTTOM':
                newindex = n-1
            elif direction == 'TOP':
                newindex = 0
            
            structlist.move(structindex, newindex)
            self.index_collision = newindex
    
    def CopyFromOther(self, other, values=True, collisions=True):
        if values:
            self.airresistance = other.airresistance
            self.waterresistance = other.waterresistance
            self.minanglez = other.minanglez
            self.maxanglez = other.maxanglez
            self.minangley = other.minangley
            self.maxangley = other.maxangley
            self.collisionsizetip = other.collisionsizetip
            self.collisionsizeroot = other.collisionsizeroot
            self.frictionrate = other.frictionrate
            self.goalstrength = other.goalstrength
            self.unknown_0x0cc10e5d3a = other.unknown_0x0cc10e5d3a
            self.localgravity = other.localgravity
            self.fallspeedscale = other.fallspeedscale
            self.groundhit = other.groundhit
            self.windaffect = other.windaffect
        
        if collisions:
            self.collisions.clear()
            for c in other.collisions:
                self.AddCollision(c.hash40)
    
    def Serialize(self, tabs=0, index=0):
        out = ""
        out += SerializeFloat("airresistance", self.airresistance, tabs)
        out += SerializeFloat("waterresistance", self.waterresistance, tabs)
        out += SerializeFloat("minanglez", self.minanglez, tabs)
        out += SerializeFloat("maxanglez", self.maxanglez, tabs)
        out += SerializeFloat("minangley", self.minangley, tabs)
        out += SerializeFloat("maxangley", self.maxangley, tabs)
        out += SerializeFloat("collisionsizetip", self.collisionsizetip, tabs)
        out += SerializeFloat("collisionsizeroot", self.collisionsizeroot, tabs)
        out += SerializeFloat("frictionrate", self.frictionrate, tabs)
        out += SerializeFloat("goalstrength", self.goalstrength, tabs)
        out += SerializeFloat("0x0cc10e5d3a", self.unknown_0x0cc10e5d3a, tabs)
        out += SerializeFloat("localgravity", self.localgravity, tabs)
        out += SerializeFloat("fallspeedscale", self.fallspeedscale, tabs)
        out += SerializeSbyte("groundhit", self.groundhit, tabs)
        out += SerializeFloat("windaffect", self.windaffect, tabs)
        out += SerializeList("collisions", self.collisions, tabs)
        return out

    def DrawPanel(self, layout, draw_collisions=True):
        c = layout.column(align=True)
        c.prop(self, 'airresistance')
        c.prop(self, 'waterresistance')
        r = c.row(align=True)
        r.prop(self, 'minanglez')
        r.prop(self, 'maxanglez')
        r = c.row(align=True)
        r.prop(self, 'minangley')
        r.prop(self, 'maxangley')
        c.prop(self, 'collisionsizetip')
        c.prop(self, 'collisionsizeroot')
        c.prop(self, 'frictionrate')
        c.prop(self, 'goalstrength')
        c.prop(self, 'unknown_0x0cc10e5d3a')
        c.prop(self, 'localgravity', expand=True)
        c.prop(self, 'fallspeedscale')
        c.prop(self, 'groundhit')
        c.prop(self, 'windaffect')
        
        if draw_collisions:
            b = layout.box().column()
            r = b.row()
            r.alignment = 'CENTER'
            r.label(text="== Collisions ==")
            
            r = b.row(align=True)
            
            r.template_list(
                "SWINGULT_UL_SwingData_SwingBone_Params_Collisions", "", self, "collisions", self, "index_collision", rows=3)
            
            c = r.column(align=True)
            c.scale_y = 0.95
            c.operator('swingult.swing_bone_params_collision_add', text="", icon='ADD')
            c.operator('swingult.swing_bone_params_collision_remove', text="", icon='REMOVE')
            c.separator()
            c.operator('swingult.swing_bone_params_collision_move', text="", icon='TRIA_UP').direction = 'UP'
            c.operator('swingult.swing_bone_params_collision_move', text="", icon='TRIA_DOWN').direction = 'DOWN'
classlist.append(SwingData_Swing_Bone_Params)

class SwingData_Swing_Bone(bpy.types.PropertyGroup): # ---------------------------------
    name : bpy.props.StringProperty()
    start_bonename : bpy.props.StringProperty()
    end_bonename : bpy.props.StringProperty()
    params : bpy.props.CollectionProperty(type=SwingData_Swing_Bone_Params)
    isskirt : bpy.props.IntProperty() # sbyte
    rotateorder : bpy.props.IntProperty()
    curverotatex : bpy.props.IntProperty() # sbyte
    unknown_0x0f7316a113 : bpy.props.IntProperty()
    
    index_param : bpy.props.IntProperty()
    
    def CreateVisualObjects(self, armature_object, bone_name, prc):
        for i, p in enumerate(self.params):
            p.CreateVisualObjects(armature_object, bone_name, prc, self)
    
    def RemoveVisualObjects(self):
        for p in self.params:
            p.RemoveVisualObjects()
    
    def AddParams(self, copy_active=False):
        p = self.params.add()
        if copy_active and len(self.params) > 0:
            p.CopyFromOther(self.params[self.index_param])
        self.index_param = len(self.params)-1
        return p
    
    def RemoveParams(self, index=None):
        if index == None:
            index = self.index_param
        self.params[index].RemoveVisualObjects()
        self.params.remove(index)
        self.index_param = max(0, min(len(self.params)-1, self.index_param))
    
    def MoveParams(self, direction):
        structlist = self.params
        structindex = self.index_param
        n = len(structlist)
        
        if n > 1:
            newindex = structindex
            if direction == 'DOWN':
                newindex = (structindex+1) % n
            elif direction == 'UP':
                newindex = (structindex-1) % n
            elif direction == 'BOTTOM':
                newindex = n-1
            elif direction == 'TOP':
                newindex = 0
            
            structlist.move(structindex, newindex)
            self.index_param = newindex
    
    def ClearParams(self):
        [self.RemoveParams(0) for i in range(0, len(self.params))]
        self.index_param = 0
    
    def GetParamsActive(self):
        return self.params[self.index_param]
    
    # Returns list of bone names from param indices
    def CalcParamNames(self):
        bonename = self.start_bonename
        if self.start_bonename[-1] in "0123456789":
            boneindexstart = int(self.start_bonename[-1])
            return [bonename[:-1] + str(i+boneindexstart) for i,p in enumerate(self.params)]
        else:
            return list(set(self.start_bonename, self.end_bonename))
    
    # Returns true if bone name is in param chain
    def BoneNameInChain(self, name):
        bonenames = [x.lower() for x in self.CalcParamNames()]
        return name.lower() in bonenames
    
    def CopyFromOther(self, other):
        if self == other or not other:
            return self
        
        self.name = other.name
        self.start_bonename = other.start_bonename
        self.end_bonename = other.end_bonename
        
        self.params.clear()
        for p in other.params:
            self.AddParams().CopyFromOther(p)
        
        self.isskirt = other.isskirt
        self.rotateorder = other.rotateorder
        self.curverotatex = other.curverotatex
        self.unknown_0x0f7316a113 = other.unknown_0x0f7316a113
        
        return self
    
    def Serialize(self, tabs=0, index=0):
        out = ""
        out += SerializeString("name", self.name, tabs)
        out += SerializeString("start_bonename", self.start_bonename, tabs)
        out += SerializeString("end_bonename", self.end_bonename, tabs)
        out += SerializeListOfStructs("params", self.params, tabs)
        out += SerializeSbyte("isskirt", self.isskirt, tabs)
        out += SerializeInt("rotateorder", self.rotateorder, tabs)
        out += SerializeSbyte("curverotatex", self.curverotatex, tabs)
        out += SerializeSbyte("0x0f7316a113", self.unknown_0x0f7316a113, tabs)
        return out

    def DrawPanel(self, layout):
        b = layout.box().column(align=True)
        swing_ultimate = bpy.context.scene.swing_ultimate
        
        if swing_ultimate.show_search:
            b.prop_search(self, 'name', swing_ultimate, 'prc_labels_bonename')
            b.prop_search(self, 'start_bonename', swing_ultimate, 'prc_labels_swingbone', icon='BONE_DATA')
            b.prop_search(self, 'end_bonename', swing_ultimate, 'prc_labels_swingbone', icon='BONE_DATA')
        else:
            b.prop(self, 'name')
            b.prop(self, 'start_bonename', icon='BONE_DATA')
            b.prop(self, 'end_bonename', icon='BONE_DATA')
        
        c = b.column(align=True)
        c.prop(self, 'isskirt')
        c.prop(self, 'rotateorder')
        c.prop(self, 'curverotatex')
        c.prop(self, 'unknown_0x0f7316a113')
classlist.append(SwingData_Swing_Bone)

"------------------------------------------------------------------------------------------------"

class SwingData_Swing_CollisionSphere(bpy.types.PropertyGroup): # ---------------------------------
    type = 'SPHERE'
    
    name : bpy.props.StringProperty()
    bonename : bpy.props.StringProperty()
    cx : bpy.props.FloatProperty()
    cy : bpy.props.FloatProperty()
    cz : bpy.props.FloatProperty()
    radius : bpy.props.FloatProperty()
    
    visual_object : bpy.props.PointerProperty(type=bpy.types.Object)
    
    def CreateVisualObjects(self, armature_object, prc):
        bone_name = ([b.name for b in armature_object.data.bones if b.name.lower() == self.bonename.lower()]+[""])[0]
        if bone_name == "":
            print("> No bone named %s for %s %s" % (self.bonename, self.type, self.name))
            return
        
        self.RemoveVisualObjects()
        context = bpy.context
        prcindex = list(context.scene.swing_ultimate.data).index(prc)
        shapeindex = list(prc.GetStructList(self.type)).index(self)
        obj = CreateVisualShape(self.name, self.type)
        self.visual_object = obj
        
        sk = obj.data.shape_keys
        key_blocks = sk.key_blocks
        key_blocks['radius'].value = self.radius
        key_blocks['cx'].value = self.cx
        key_blocks['cy'].value = self.cy
        key_blocks['cz'].value = self.cz
        
        dpath = 'swing_ultimate.data[%d].spheres[%d]' % (prcindex, shapeindex)
        
        DriverPropertyVariable(sk, 'key_blocks["radius"].value', "x", "SCENE", context.scene, dpath+'.radius', 'x/%.2f' % VISUALSHAPESCALE)
        DriverPropertyVariable(sk, 'key_blocks["cx"].value', "x", "SCENE", context.scene, dpath+'.cx', 'x/%.2f' % VISUALSHAPESCALE)
        DriverPropertyVariable(sk, 'key_blocks["cy"].value', "x", "SCENE", context.scene, dpath+'.cy', 'x/%.2f' % VISUALSHAPESCALE)
        DriverPropertyVariable(sk, 'key_blocks["cz"].value', "x", "SCENE", context.scene, dpath+'.cz', 'x/%.2f' % VISUALSHAPESCALE)
        
        c = obj.constraints.new(type='COPY_LOCATION')
        c.target = armature_object
        c.subtarget = bone_name
        
        c = obj.constraints.new(type='COPY_ROTATION')
        c.target = armature_object
        c.subtarget = bone_name
    
    def RemoveVisualObjects(self):
        if self.visual_object:
            bpy.data.objects.remove(self.visual_object, do_unlink=True)
    
    def CopyFromOther(self, other):
        self.name = other.name
        self.bonename = other.bonename
        self.cx = other.cx
        self.cy = other.cy
        self.cz = other.cz
        self.radius = other.radius
    
    def Serialize(self, tabs=0, index=0):
        out = ""
        out += SerializeString("name", self.name, tabs)
        out += SerializeString("bonename", self.bonename, tabs)
        out += SerializeFloat("cx", self.cx, tabs)
        out += SerializeFloat("cy", self.cy, tabs)
        out += SerializeFloat("cz", self.cz, tabs)
        out += SerializeFloat("radius", self.radius, tabs)
        return out

    def DrawPanel(self, layout):
        b = layout.box().column(align=False)
        swing_ultimate = bpy.context.scene.swing_ultimate
        
        c = b.column(align=True)
        if swing_ultimate.show_search:
            c.prop_search(self, 'name', swing_ultimate, 'prc_labels_collisions', icon=STRUCTICONS[self.type])
            c.prop_search(self, 'bonename', swing_ultimate, 'prc_labels_bonename', icon='BONE_DATA')
        else:
            c.prop(self, 'name')
            c.prop(self, 'bonename', icon='BONE_DATA')
        
        c = b.column(align=True)
        r = c.row(align=True)
        r.label(text="Offset:")
        r.prop(self, 'cx', text="")
        r.prop(self, 'cy', text="")
        r.prop(self, 'cz', text="")
        c.prop(self, 'radius')
classlist.append(SwingData_Swing_CollisionSphere)

class SwingData_Swing_CollisionOval(bpy.types.PropertyGroup): # ---------------------------------
    type = 'OVAL'
    
    name : bpy.props.StringProperty()
    bonename : bpy.props.StringProperty()
    cx : bpy.props.FloatProperty()
    cy : bpy.props.FloatProperty()
    cz : bpy.props.FloatProperty()
    radius : bpy.props.FloatProperty()
    
    visual_object : bpy.props.PointerProperty(type=bpy.types.Object)
    
    def CopyFromOther(self, other):
        self.name = other.name
        self.bonename = other.bonename
        self.cx = other.cx
        self.cy = other.cy
        self.cz = other.cz
        self.radius = other.radius
    
    def Serialize(self, tabs=0, index=0):
        out = ""
        out += SerializeString("name", self.name, tabs)
        out += SerializeString("bonename", self.bonename, tabs)
        out += SerializeFloat("cx", self.cx, tabs)
        out += SerializeFloat("cy", self.cy, tabs)
        out += SerializeFloat("cz", self.cz, tabs)
        out += SerializeFloat("radius", self.radius, tabs)
        return out
classlist.append(SwingData_Swing_CollisionOval)

class SwingData_Swing_CollisionEllipsoid(bpy.types.PropertyGroup): # ---------------------------------
    type = 'ELLIPSOID'
    
    name : bpy.props.StringProperty()
    bonename : bpy.props.StringProperty()
    cx : bpy.props.FloatProperty()
    cy : bpy.props.FloatProperty()
    cz : bpy.props.FloatProperty()
    rx : bpy.props.FloatProperty()
    ry : bpy.props.FloatProperty()
    rz : bpy.props.FloatProperty()
    sx : bpy.props.FloatProperty()
    sy : bpy.props.FloatProperty()
    sz : bpy.props.FloatProperty()
    
    visual_object : bpy.props.PointerProperty(type=bpy.types.Object)
    
    def CreateVisualObjects(self, armature_object, prc):
        bone_name = ([b.name for b in armature_object.data.bones if b.name.lower() == self.bonename.lower()]+[""])[0]
        if bone_name == "":
            print("> No bone named %s for %s %s" % (self.bonename, self.type, self.name))
            return
        
        self.RemoveVisualObjects()
        context = bpy.context
        prcindex = list(context.scene.swing_ultimate.data).index(prc)
        shapeindex = list(prc.GetStructList(self.type)).index(self)
        obj = CreateVisualShape(self.name, self.type)
        self.visual_object = obj
        
        sk = obj.data.shape_keys
        key_blocks = sk.key_blocks
        key_blocks['cx'].value = self.cx
        key_blocks['cy'].value = self.cy
        key_blocks['cz'].value = self.cz
        key_blocks['rx'].value = self.rx
        key_blocks['ry'].value = self.ry
        key_blocks['rz'].value = self.rz
        key_blocks['sx'].value = self.sx
        key_blocks['sy'].value = self.sy
        key_blocks['sz'].value = self.sz
        
        dpath = 'swing_ultimate.data[%d].ellipsoids[%d]' % (prcindex, shapeindex)
        DriverPropertyVariable(sk, 'key_blocks["cx"].value', "x", "SCENE", context.scene, dpath+'.cx', 'x/%.2f' % VISUALSHAPESCALE)
        DriverPropertyVariable(sk, 'key_blocks["cy"].value', "x", "SCENE", context.scene, dpath+'.cy', 'x/%.2f' % VISUALSHAPESCALE)
        DriverPropertyVariable(sk, 'key_blocks["cz"].value', "x", "SCENE", context.scene, dpath+'.cz', 'x/%.2f' % VISUALSHAPESCALE)
        
        DriverPropertyVariable(sk, 'key_blocks["sx"].value', "x", "SCENE", context.scene, dpath+'.sx', 'x/%.2f' % VISUALSHAPESCALE)
        DriverPropertyVariable(sk, 'key_blocks["sy"].value', "x", "SCENE", context.scene, dpath+'.sy', 'x/%.2f' % VISUALSHAPESCALE)
        DriverPropertyVariable(sk, 'key_blocks["sz"].value', "x", "SCENE", context.scene, dpath+'.sz', 'x/%.2f' % VISUALSHAPESCALE)
        
        c = obj.constraints.new(type='COPY_LOCATION')
        c.target = armature_object
        c.subtarget = bone_name
        
        c = obj.constraints.new(type='COPY_ROTATION')
        c.target = armature_object
        c.subtarget = bone_name
    
    def RemoveVisualObjects(self):
        if self.visual_object:
            bpy.data.objects.remove(self.visual_object, do_unlink=True)
    
    def CopyFromOther(self, other):
        self.name = other.name
        self.bonename = other.bonename
        self.cx = other.cx
        self.cy = other.cy
        self.cz = other.cz
        self.rx = other.rx
        self.ry = other.ry
        self.rz = other.rz
        self.sx = other.sx
        self.sy = other.sy
        self.sz = other.sz
    
    def Serialize(self, tabs=0, index=0):
        out = ""
        out += SerializeString("name", self.name, tabs)
        out += SerializeString("bonename", self.bonename, tabs)
        out += SerializeFloat("cx", self.cx, tabs)
        out += SerializeFloat("cy", self.cy, tabs)
        out += SerializeFloat("cz", self.cz, tabs)
        out += SerializeFloat("rx", self.rx, tabs)
        out += SerializeFloat("ry", self.ry, tabs)
        out += SerializeFloat("rz", self.rz, tabs)
        out += SerializeFloat("sx", self.sx, tabs)
        out += SerializeFloat("sy", self.sy, tabs)
        out += SerializeFloat("sz", self.sz, tabs)
        return out

    def DrawPanel(self, layout):
        b = layout.box().column(align=False)
        swing_ultimate = bpy.context.scene.swing_ultimate
        
        c = b.column(align=True)
        if swing_ultimate.show_search:
            c.prop_search(self, 'name', swing_ultimate, 'prc_labels_collisions', icon=STRUCTICONS['ELLIPSOID'])
            c.prop_search(self, 'bonename', swing_ultimate, 'prc_labels_bonename', icon='BONE_DATA')
        else:
            c.prop(self, 'name', icon=STRUCTICONS['ELLIPSOID'])
            c.prop(self, 'bonename', icon='BONE_DATA')
        
        c = b.column(align=False)
        
        r = c.row(align=True)
        r.label(text="Offset:")
        r.prop(self, 'cx', text="")
        r.prop(self, 'cy', text="")
        r.prop(self, 'cz', text="")
        
        r = c.row(align=True)
        r.label(text="Rotation:")
        r.prop(self, 'rx', text="")
        r.prop(self, 'ry', text="")
        r.prop(self, 'rz', text="")
        
        r = c.row(align=True)
        r.label(text="Scale:")
        r.prop(self, 'sx', text="")
        r.prop(self, 'sy', text="")
        r.prop(self, 'sz', text="")        
classlist.append(SwingData_Swing_CollisionEllipsoid)

class SwingData_Swing_CollisionCapsule(bpy.types.PropertyGroup): # ---------------------------------
    type = 'CAPSULE'
    
    name : bpy.props.StringProperty()
    start_bonename : bpy.props.StringProperty()
    end_bonename : bpy.props.StringProperty()
    start_offset_x : bpy.props.FloatProperty()
    start_offset_y : bpy.props.FloatProperty()
    start_offset_z : bpy.props.FloatProperty()
    end_offset_x : bpy.props.FloatProperty()
    end_offset_y : bpy.props.FloatProperty()
    end_offset_z : bpy.props.FloatProperty()
    start_radius : bpy.props.FloatProperty()
    end_radius : bpy.props.FloatProperty()
    
    visual_object : bpy.props.PointerProperty(type=bpy.types.Object)
    
    def CreateVisualObjects(self, armature_object, prc):
        bone_name = ([b.name for b in armature_object.data.bones if b.name.lower() == self.start_bonename.lower()]+[""])[0]
        if bone_name == "":
            print("> No bone named %s for %s %s" % (self.start_bonename, self.type, self.name))
            return
        
        endpbone = ([pb for pb in armature_object.data.bones if pb.name.lower() == self.end_bonename]+[None])[0]
        
        self.RemoveVisualObjects()
        context = bpy.context
        prcindex = list(context.scene.swing_ultimate.data).index(prc)
        shapeindex = list(prc.GetStructList(self.type)).index(self)
        obj = CreateVisualShape(self.name, self.type)
        self.visual_object = obj
        
        sk = obj.data.shape_keys
        key_blocks = sk.key_blocks
        key_blocks['start_offset_x'].value = self.start_offset_x
        key_blocks['start_offset_y'].value = self.start_offset_y
        key_blocks['start_offset_z'].value = self.start_offset_z
        key_blocks['end_offset_x'].value = self.end_offset_x
        key_blocks['end_offset_y'].value = self.end_offset_y
        key_blocks['end_offset_z'].value = self.end_offset_z
        key_blocks['start_radius'].value = self.start_radius
        key_blocks['end_radius'].value = self.end_radius
        
        dpath = 'swing_ultimate.data[%d].capsules[%d]' % (prcindex, shapeindex)
        DriverPropertyVariable(sk, 'key_blocks["start_offset_x"].value', "x", "SCENE", context.scene, dpath+'.start_offset_x', 'x/%.2f' % VISUALSHAPESCALE)
        DriverPropertyVariable(sk, 'key_blocks["start_offset_y"].value', "x", "SCENE", context.scene, dpath+'.start_offset_y', 'x/%.2f' % VISUALSHAPESCALE)
        DriverPropertyVariable(sk, 'key_blocks["start_offset_z"].value', "x", "SCENE", context.scene, dpath+'.start_offset_z', 'x/%.2f' % VISUALSHAPESCALE)
        
        DriverPropertyVariable(sk, 'key_blocks["end_offset_x"].value', "x", "SCENE", context.scene, dpath+'.end_offset_x', 'x/%.2f' % VISUALSHAPESCALE)
        DriverPropertyVariable(sk, 'key_blocks["end_offset_y"].value', "x", "SCENE", context.scene, dpath+'.end_offset_y', 'x/%.2f' % VISUALSHAPESCALE)
        DriverPropertyVariable(sk, 'key_blocks["end_offset_z"].value', "x", "SCENE", context.scene, dpath+'.end_offset_z', 'x/%.2f' % VISUALSHAPESCALE)
        
        DriverPropertyVariable(sk, 'key_blocks["start_radius"].value', "x", "SCENE", context.scene, dpath+'.start_radius', 'x/%.2f' % VISUALSHAPESCALE)
        DriverPropertyVariable(sk, 'key_blocks["end_radius"].value', "x", "SCENE", context.scene, dpath+'.end_radius', 'x/%.2f' % VISUALSHAPESCALE)
        
        c = obj.constraints.new(type='COPY_LOCATION')
        c.target = armature_object
        c.subtarget = bone_name
    
        if endpbone:
            c = obj.constraints.new(type='TRACK_TO')
            c.target = armature_object
            c.subtarget = endpbone.name
            c.track_axis = 'TRACK_Y'
            c.up_axis = 'UP_Z'
            
            # Stretch to bone length
            d = sk.animation_data.drivers.new('key_blocks["length"].value').driver
            
            v = d.variables.new()
            v.name = "x"
            v.type = 'LOC_DIFF'
            v.targets[0].id = armature_object
            v.targets[0].bone_target = bone_name
            
            v.targets[1].id = armature_object
            v.targets[1].bone_target = endpbone.name
            
            d.type = 'SCRIPTED'
            d.expression = 'x/%.2f' % VISUALSHAPESCALE
        else:
            c = obj.constraints.new(type='TRACK_TO')
            c.target = armature_object
            c.subtarget = bone_name
            c.head_tail = 1.0
            c.track_axis = 'TRACK_Y'
            c.up_axis = 'UP_Z'
    
    def RemoveVisualObjects(self):
        if self.visual_object:
            bpy.data.objects.remove(self.visual_object, do_unlink=True)
    
    def CopyFromOther(self, other):
        self.name = other.name
        self.start_bonename = other.start_bonename
        self.end_bonename = other.end_bonename
        self.start_offset_x = other.start_offset_x
        self.start_offset_y = other.start_offset_y
        self.start_offset_z = other.start_offset_z
        self.end_offset_x = other.end_offset_x
        self.end_offset_y = other.end_offset_y
        self.end_offset_z = other.end_offset_z
        self.start_radius = other.start_radius
        self.end_radius = other.end_radius
    
    def Serialize(self, tabs=0, index=0):
        out = ""
        out += SerializeString("name", self.name, tabs)
        out += SerializeString("start_bonename", self.start_bonename, tabs)
        out += SerializeString("end_bonename", self.end_bonename, tabs)
        out += SerializeFloat("start_offset_x", self.start_offset_x, tabs)
        out += SerializeFloat("start_offset_y", self.start_offset_y, tabs)
        out += SerializeFloat("start_offset_z", self.start_offset_z, tabs)
        out += SerializeFloat("end_offset_x", self.end_offset_x, tabs)
        out += SerializeFloat("end_offset_y", self.end_offset_y, tabs)
        out += SerializeFloat("end_offset_z", self.end_offset_z, tabs)
        out += SerializeFloat("start_radius", self.start_radius, tabs)
        out += SerializeFloat("end_radius", self.end_radius, tabs)
        return out

    def DrawPanel(self, layout):
        b = layout.box().column(align=False)
        swing_ultimate = bpy.context.scene.swing_ultimate
        
        c = b.column(align=True)
        if swing_ultimate.show_search:
            c.prop_search(self, 'name', swing_ultimate, 'prc_labels_collisions', icon=STRUCTICONS['CAPSULE'])
            c.prop_search(self, 'start_bonename', swing_ultimate, 'prc_labels_bonename', icon='BONE_DATA')
            c.prop_search(self, 'end_bonename', swing_ultimate, 'prc_labels_bonename', icon='BONE_DATA')
        else:
            c.prop(self, 'name', icon=STRUCTICONS['CAPSULE'])
            c.prop(self, 'start_bonename', icon='BONE_DATA')
            c.prop(self, 'end_bonename', icon='BONE_DATA')
        
        c = b.column(align=True)
        
        r = c.row(align=True)
        r.label(text="Start Offset:")
        r.prop(self, 'start_offset_x', text="")
        r.prop(self, 'start_offset_y', text="")
        r.prop(self, 'start_offset_z', text="")
        
        r = c.row(align=True)
        r.label(text="End Offset:")
        r.prop(self, 'end_offset_x', text="")
        r.prop(self, 'end_offset_y', text="")
        r.prop(self, 'end_offset_z', text="")
        
        c.prop(self, 'start_radius', text="Start Radius")
        c.prop(self, 'end_radius', text="End Radius")
classlist.append(SwingData_Swing_CollisionCapsule)

class SwingData_Swing_CollisionPlane(bpy.types.PropertyGroup): # ---------------------------------
    type = 'PLANE'
    
    name : bpy.props.StringProperty()
    bonename : bpy.props.StringProperty()
    nx : bpy.props.FloatProperty()
    ny : bpy.props.FloatProperty()
    nz : bpy.props.FloatProperty()
    distance : bpy.props.FloatProperty()
    
    visual_object : bpy.props.PointerProperty(type=bpy.types.Object)
    
    def CreateVisualObjects(self, armature_object, prc):
        bone_name = ([b.name for b in armature_object.data.bones if b.name.lower() == self.bonename.lower()]+[""])[0]
        if bone_name == "":
            print("> No bone named %s for %s %s" % (self.bonename, self.type, self.name))
            return
        
        self.RemoveVisualObjects()
        context = bpy.context
        prcindex = list(context.scene.swing_ultimate.data).index(prc)
        shapeindex = list(prc.GetStructList(self.type)).index(self)
        obj = CreateVisualShape(self.name, self.type)
        self.visual_object = obj
        
        sk = obj.data.shape_keys
        key_blocks = sk.key_blocks
        key_blocks['distance'].value = self.distance
        
        dpath = 'swing_ultimate.data[%d].planes[%d]' % (prcindex, shapeindex)
        
        DriverPropertyVariable(sk, 'key_blocks["distance"].value', "x", "SCENE", context.scene, dpath+'.distance', 'x/%.2f' % VISUALSHAPESCALE)
        
        c = obj.constraints.new(type='COPY_LOCATION')
        c.target = armature_object
        c.subtarget = bone_name
        
        c = obj.constraints.new(type='COPY_ROTATION')
        c.target = armature_object
        c.subtarget = bone_name
    
    def RemoveVisualObjects(self):
        if self.visual_object:
            bpy.data.objects.remove(self.visual_object, do_unlink=True)
    
    def CopyFromOther(self, other):
        self.name = other.name
        self.bonename = other.bonename
        self.nx = other.nx
        self.ny = other.ny
        self.nz = other.nz
        self.distance = other.distance
    
    def Serialize(self, tabs=0, index=0):
        out = ""
        out += SerializeString("name", self.name, tabs)
        out += SerializeString("bonename", self.bonename, tabs)
        out += SerializeFloat("nx", self.nx, tabs)
        out += SerializeFloat("ny", self.ny, tabs)
        out += SerializeFloat("nz", self.nz, tabs)
        out += SerializeFloat("distance", self.distance, tabs)
        return out

    def DrawPanel(self, layout):
        b = layout.box().column(align=False)
        swing_ultimate = bpy.context.scene.swing_ultimate
        
        c = b.column(align=True)
        if swing_ultimate.show_search:
            c.prop_search(self, 'name', swing_ultimate, 'prc_labels_collisions', icon=STRUCTICONS['PLANE'])
            c.prop_search(self, 'bonename', swing_ultimate, 'prc_labels_bonename', icon='BONE_DATA')
        else:
            c.prop(self, 'name', icon=STRUCTICONS['PLANE'])
            c.prop(self, 'bonename', icon='BONE_DATA')
        
        c = b.column(align=True)
        r = c.row(align=True)
        r.label(text="Normal:")
        r.prop(self, 'nx')
        r.prop(self, 'ny')
        r.prop(self, 'nz')
        c.prop(self, 'distance')
classlist.append(SwingData_Swing_CollisionPlane)

class SwingData_Swing_Connection(bpy.types.PropertyGroup): # ---------------------------------
    type = 'CONNECTION'
    
    start_bonename : bpy.props.StringProperty()
    end_bonename : bpy.props.StringProperty()
    radius : bpy.props.FloatProperty()
    length : bpy.props.FloatProperty()
    
    def CopyFromOther(self, other):
        self.start_bonename = other.start_bonename
        self.end_bonename = other.end_bonename
        self.radius = other.radius
        self.length = other.length
    
    def Serialize(self, tabs=0, index=0):
        out = ""
        out += SerializeString("start_bonename", self.start_bonename, tabs)
        out += SerializeString("end_bonename", self.end_bonename, tabs)
        out += SerializeFloat("radius", self.radius, tabs)
        out += SerializeFloat("length", self.length, tabs)
        return out

    def DrawPanel(self, layout):
        b = layout.box().column(align=True)
        
        swing_ultimate = bpy.context.scene.swing_ultimate
        
        if swing_ultimate.show_search:
            b.prop_search(self, 'start_bonename', swing_ultimate, 'prc_labels_swingbone', icon='BONE_DATA')
            b.prop_search(self, 'end_bonename', swing_ultimate, 'prc_labels_swingbone', icon='BONE_DATA')
        else:
            b.prop(self, 'start_bonename', icon='BONE_DATA')
            b.prop(self, 'end_bonename', icon='BONE_DATA')
        
        c = b.column(align=True)
        c.prop(self, 'radius')
        c.prop(self, 'length')
classlist.append(SwingData_Swing_Connection)

"------------------------------------------------------------------------------------------------"

class SwingData(bpy.types.PropertyGroup):
    name : bpy.props.StringProperty(name=" Name")
    index : bpy.props.IntProperty(name="Scene Index")
    
    swingbones : bpy.props.CollectionProperty(type=SwingData_Swing_Bone)
    spheres : bpy.props.CollectionProperty(type=SwingData_Swing_CollisionSphere)
    ovals : bpy.props.CollectionProperty(type=SwingData_Swing_CollisionOval)
    ellipsoids : bpy.props.CollectionProperty(type=SwingData_Swing_CollisionEllipsoid)
    capsules : bpy.props.CollectionProperty(type=SwingData_Swing_CollisionCapsule)
    planes : bpy.props.CollectionProperty(type=SwingData_Swing_CollisionPlane)
    connections : bpy.props.CollectionProperty(type=SwingData_Swing_Connection)
    groups : bpy.props.CollectionProperty(type=SwingData_Hash40List)
    
    index_bone : bpy.props.IntProperty()
    index_sphere : bpy.props.IntProperty()
    index_oval : bpy.props.IntProperty()
    index_ellipsoid : bpy.props.IntProperty()
    index_capsule : bpy.props.IntProperty()
    index_plane : bpy.props.IntProperty()
    index_connection : bpy.props.IntProperty()
    index_group : bpy.props.IntProperty()
    
    # Returns list of structs for given type
    def GetStructList(self, type):
        return {
            'BONE' : self.swingbones,
            'SPHERE' : self.spheres,
            'OVAL' : self.ovals,
            'ELLIPSOID' : self.ellipsoids,
            'CAPSULE' : self.capsules,
            'PLANE' : self.planes,
            'CONNECTION' : self.connections,
            'GROUP' : self.groups,
        }[type]
    
    # Returns list of all shape structs
    def GetShapeList(self):
        return (
            list(self.GetStructList('SPHERE')) + 
            list(self.GetStructList('OVAL')) + 
            list(self.GetStructList('ELLIPSOID')) + 
            list(self.GetStructList('CAPSULE')) + 
            list(self.GetStructList('PLANE'))
        )
    
    # Returns struct of type at index
    def GetStruct(self, type, index):
        datalist = self.GetStructList(type)
        return datalist[index] if len(datalist) > 0 else None
    
    # Returns struct by name
    def FindStruct(self, type, name, case_sensitive=False):
        structlist = self.GetStructList(type)
        if case_sensitive:
            return ([x for x in structlist if x.name == name]+[None])[0]
        else:
            return ([x for x in structlist if x.name.lower() == name.lower()]+[None])[0]
    
    # Returns size of struct list
    def GetStructListSize(self, type):
        return len(self.GetStructList(type))
    
    # Returns total number of shapes
    def GetShapeCount(self):
        return len(self.spheres) + len(self.ovals) + len(self.ellipsoids) + len(self.capsules) + len(self.planes)
    
    # Returns active index for struct type
    def GetStructActiveIndex(self, type):
        return {
            'BONE' : self.index_bone,
            'SPHERE' : self.index_sphere,
            'OVAL' : self.index_oval,
            'ELLIPSOID' : self.index_ellipsoid,
            'CAPSULE' : self.index_capsule,
            'PLANE' : self.index_plane,
            'CONNECTION' : self.index_connection,
            'GROUP' : self.index_group,
        }[type]
    
    # Sets the active struct index for type
    def SetStructActiveIndex(self, type, index):
        if type == 'BONE':
            self.index_bone = index
        elif type == 'SHPERE':
            self.index_sphere = index
        elif type == 'OVAL':
            self.index_oval = index
        elif type == 'ELLIPSOID':
            self.index_ellipsoid = index
        elif type == 'CAPSULE':
            self.index_capsule = index
        elif type == 'PLANE':
            self.index_plane = index
        elif type == 'CONNECTION':
            self.index_connection = index
        elif type == 'GROUP':
            self.index_group = index
        self.Update()
    
    # Returns active struct for type
    def GetStructActive(self, type):
        return self.GetStruct(type, self.GetStructActiveIndex(type))
        return None
    
    # Returns (swingbone, params) if bone name is in swing bone chain, (None, None) if not found
    def FindBoneParamsByName(self, bonename):
        if bonename[-1] in "0123456789":
            for sb in self.swingbones:
                if sb.start_bonename[-1] in "0123456789":
                    boneindexstart = int(sb.start_bonename[-1])
                    for i, p in enumerate(sb.params):
                        paramname = sb.start_bonename[:-1] + str(boneindexstart+i)
                        if paramname.lower() == bonename.lower():
                            return (sb, p)
        else:
            for sb in self.swingbones:
                if sb.start_bonename.lower() == bonename.lower():
                    return (sb, sb.params[0] if sb.params else None)
        return (None, None)
    
    # Updates and clamps struct indices
    def Update(self):
        self.index_bone = max(0, min(len(self.GetStructList('BONE'))-1, self.index_bone))
        self.index_sphere = max(0, min(len(self.GetStructList('SPHERE'))-1, self.index_sphere))
        self.index_oval = max(0, min(len(self.GetStructList('OVAL'))-1, self.index_oval))
        self.index_ellipsoid = max(0, min(len(self.GetStructList('ELLIPSOID'))-1, self.index_ellipsoid))
        self.index_capsule = max(0, min(len(self.GetStructList('CAPSULE'))-1, self.index_capsule))
        self.index_plane = max(0, min(len(self.GetStructList('PLANE'))-1, self.index_plane))
        self.index_connection = max(0, min(len(self.GetStructList('CONNECTION'))-1, self.index_connection))
        self.index_group = max(0, min(len(self.GetStructList('GROUP'))-1, self.index_group))
    
    # Adds and returns new struct of type
    def AddStruct(self, type, copy_active=False):
        active = self.GetStructActive(type)
        entry = self.GetStructList(type).add()
        
        if copy_active and active and (type in ['BONE', 'SPHERE', 'OVAL', 'ELLIPSOID', 'CAPSULE', 'PLANE', 'CONNECTION']):
            entry.CopyFromOther( active )
            entry.name = active.name
            self.GetStructList(type).move(len(self.GetStructList(type))-1, self.GetStructActiveIndex(type)+1)
        self.Update()
        return entry
    
    # Removes struct of type at index
    def RemoveStruct(self, type, index=None):
        if index == None:
            index = self.GetStructActiveIndex(type)
        if type in SHAPENAMES:
            self.GetStructActive(type).RemoveVisualObjects()
        self.GetStructList(type).remove(index)
        self.Update()
    
    # Removes given struct from swing data
    def RemoveStructEntry(self, structentry):
        if structentry:
            type = structentry.type
            structlist = list(self.GetStructList(type))
            if structentry in structlist:
                index = list(self.GetStructList(type)).index(structentry)
                self.RemoveStruct(type, index)
    
    # Moves active struct in struct list of given type
    def MoveStruct(self, type, direction):
        structlist = self.GetStructList(type)
        structindex = self.GetStructActiveIndex(type)
        n = len(structlist)
        
        if n > 1:
            newindex = structindex
            if direction == 'DOWN':
                
                newindex = (structindex+1) % n
            elif direction == 'UP':
                newindex = (structindex-1) % n
            elif direction == 'BOTTOM':
                newindex = n-1
            elif direction == 'TOP':
                newindex = 0
            
            structlist.move(structindex, newindex)
            self.SetStructActiveIndex(type, newindex)
    
    # Copies the parameters of one swing bone struct to another
    def CopyBoneParams(self, bonenamesource, bonenamedest):
        b1 = self.FindStruct('BONE', bonenamesource)
        b2 = self.FindStruct('BONE', bonenamedest)
        if not b1:
            print("CopyBoneParams: bone \"%s\" not found" % bonenamesource)
            return False
        if not b2:
            print("CopyBoneParams: bone \"%s\" not found" % bonenamedest)
            return False
        if b1 == b2:
            return True
        
        b2.ClearParams()
        for p in b1.params:
            b2.AddParams().CopyFromOther(p)
        return True
    
    # Adds new struct and copies data from reference struct
    def TransferStruct(self, other, type, structindex):
        otherstruct = other.GetStruct(type, structindex)
        newstruct = self.AddStruct(type)
        newstruct.CopyFromOther(otherstruct)
        return newstruct
    
    # Adds new swing bone struct and copies relevant data from refrence swing bone
    def TransferSwingBone(self, other, swingname, transfer_shapes=True):
        otherswing = ([x for x in other.GetStructList('BONE') if x.name == swingname]+[None])[0]
        
        if not otherswing:
            print("> Swing bone \"%d\" not found" % swingname)
            return False
        
        if transfer_shapes:
            print("> Transfering Shapes")
            targetcollisionnames = [x.hash40 for group in self.GetStructList('GROUP') for x in group.data]
            targetgroupnames = [x.name for x in self.GetStructList('GROUP')]
            targetshapenames = [x.name for x in self.GetShapeList()]
            
            otherbones = (otherswing.start_bonename, otherswing.end_bonename)
            othercollisionnames = [x.hash40 for params in otherswing.params for x in params.collisions]
            
            othercollisions = []
            othergroups = []
            shapemap = {x.name: x for x in other.GetShapeList()}
            
            for group in other.GetStructList('GROUP'):
                for collision in group.data:
                    if collision.hash40 in othercollisionnames:
                        othergroups.append(group)
            
            othergroups = list(set(othergroups))
            othershapes = [shapemap[hash40] for hash40 in list(set([c.hash40 for g in othergroups for c in g.data]))]
            
            for othergroup in othergroups:
                print(othergroup.name)
                if othergroup.name not in targetgroupnames:
                    group = self.AddStruct('GROUP')
                    group.name = othergroup.name
                    for collision in othergroup.data:
                        group.Add(collision.hash40)
                    print('> New Group "%s" (%s)' % (group.name, len(group.data)))
            
            for othershape in othershapes:
                if othershape.name not in targetshapenames:
                    self.AddStruct(othershape.type).CopyFromOther(othershape)
                    print('> New Shape "%s" [%s]' % (othershape.name, othershape.type))
        
        # Create new swing bone with name
        if swingname not in [x.name for x in self.GetStructList('BONE')]:
            b = self.AddStruct('BONE')
            b.name = swingname
        
        # Copy parameters
        [x for x in self.GetStructList('BONE') if x.name == swingname][0].CopyFromOther(otherswing)
    
    # Adds connection and transfers relevant data from other connection
    def TransferConnection(self, other, other_connectionindex):
        otherconnection = other.GetStructList('CONNECTION')[other_connectionindex]
        connectionkeys = [
            ("%s=%s" % (connection.start_bonename, connection.end_bonename)) 
            for connection in self.GetStructList('CONNECTION')
            ]
        otherconnectionkey = ("%s=%s" % (otherconnection.start_bonename, otherconnection.end_bonename))
        
        if otherconnectionkey not in connectionkeys:
            connection = self.AddStruct('CONNECTION')
            connection.CopyFromOther(otherconnection)
            print("> New Connection (%s -> %s)" % (connection.start_bonename, connection.end_bonename))
        else:
            print("> Connection Exists (%s -> %s)" % (otherconnection.start_bonename, otherconnection.end_bonename))
    
    # Adds connections from other swing data if the given string is in the other connection
    def TransferConnectionPattern(self, other, pattern_string, check_start=True, check_end=False):
        for i, otherconnection in enumerate(other.GetStructList('CONNECTION')):
            if(
                (check_start and pattern_string in otherconnection.start_bonename) or
                (check_end and pattern_string in otherconnection.end_bonename)
                ):
                self.TransferConnection(other, i)
    
    # Applies swing data from XML file
    def FromXML(self, xmlpath):
        XMLToSwingEdit(self, bpy.context, xmlpath)
    
    # Returns XML string of swing data
    def Serialize(self, tabs=0, index=0):
        out = ""
        
        #out += "ï»¿"
        out += '<?xml version="1.0" encoding="utf-8"?>\n'
        out += '<struct>\n'
        
        tabs += 1
        out += SerializeListOfStructs("swingbones", self.swingbones, tabs)
        out += SerializeListOfStructs("spheres", self.spheres, tabs)
        out += SerializeListOfStructs("ovals", self.ovals, tabs)
        out += SerializeListOfStructs("ellipsoids", self.ellipsoids, tabs)
        out += SerializeListOfStructs("capsules", self.capsules, tabs)
        out += SerializeListOfStructs("planes", self.planes, tabs)
        out += SerializeListOfStructs("connections", self.connections, tabs)
        
        for i, group in enumerate(self.groups):
            out += group.Serialize(tabs)
        tabs -= 1
        
        out += '</struct>\n'
        
        return out
    
    # Checks all hashes against labels
    def Validate(self):
        labels = bpy.context.scene.swing_ultimate.prc_labels_string.split()
        
        if len(labels) == 0:
            print("> No labels loaded. Use the \"Update Labels\" button to read ParamLabels.csv")
            return None
        
        labels += [""]
        conflicts = []
        
        def CheckMemberVariable(type, id, varname, index=-1, varname2="", index2=-1, varname3=""):
            if index == -1:
                return (
                    (type, id.name + "." + varname, getattr(id, varname)) 
                    if (getattr(id, varname) not in labels) else 0
                    )
            elif index2 == -1:
                return (
                    (type, "%s.%s[%d].%s" % (id.name, varname, index, varname2), getattr(getattr(id, varname)[index], varname2)) 
                    if (getattr(getattr(id, varname)[index], varname2) not in labels) else 0
                    )
            else:
                return (
                    (type, "%s.%s[%d].%s[%d].%s" % (id.name, varname, index, varname2, index2, varname3), getattr(getattr(getattr(id, varname)[index], varname2)[index2], varname3)) 
                    if (getattr(getattr(getattr(id, varname)[index], varname2)[index2], varname3) not in labels) else 0
                    )
        # Bone
        for b in self.GetStructList('BONE'):
            conflicts += [
                CheckMemberVariable('BONE', b, "name"),
                CheckMemberVariable('BONE', b, "start_bonename"),
                CheckMemberVariable('BONE', b, "end_bonename"),
            ]
            
            for pi, p in enumerate(b.params):
                for ci, c in enumerate(p.collisions):
                    conflicts += [
                        CheckMemberVariable('BONE', b, "params", pi, "collisions", ci, "hash40")
                    ]
        
        # Shapes
        for shape in self.GetStructList('SPHERE'):
            conflicts += [
                CheckMemberVariable('SPHERE', shape, "name"),
                CheckMemberVariable('SPHERE', shape, "bonename"),
            ]
        
        for shape in self.GetStructList('OVAL'):
            conflicts += [
                CheckMemberVariable('OVAL', shape, "name"),
                CheckMemberVariable('OVAL', shape, "bonename"),
            ]
        
        for shape in self.GetStructList('ELLIPSOID'):
            conflicts += [
                CheckMemberVariable('ELLIPSOID', shape, "name"),
                CheckMemberVariable('ELLIPSOID', shape, "bonename"),
            ]
        
        for shape in self.GetStructList('CAPSULE'):
            conflicts += [
                CheckMemberVariable('CAPSULE', shape, "name"),
                CheckMemberVariable('CAPSULE', shape, "start_bonename"),
                CheckMemberVariable('CAPSULE', shape, "end_bonename"),
            ]
        
        for shape in self.GetStructList('PLANE'):
            conflicts += [
                CheckMemberVariable('PLANE', shape, "name"),
                CheckMemberVariable('PLANE', shape, "bonename"),
            ]
        
        # Connections
        for connection in self.GetStructList('CONNECTION'):
            conflicts += [
                CheckMemberVariable('CONNECTION', connection, "start_bonename"),
                CheckMemberVariable('CONNECTION', connection, "end_bonename"),
            ]
        
        # Groups
        for group in self.GetStructList('GROUP'):
            conflicts += [
                CheckMemberVariable('GROUP', group, "name")
            ]
            
            for i, c in enumerate(group.data):
                conflicts += [
                    CheckMemberVariable('GROUP', group, "data", i, "hash40")
                ]
        
        conflicts = [c for c in conflicts if c]
        
        print("> %d Conflicts:" % len(conflicts))
        for c in conflicts:
            print(c)
        
        return conflicts
    
    # Removes unused data from PRC
    def Clean(self, armatureobject):
        print('> Cleaning PRC "%s" ---------' % self.name)
        
        bonenameslower = [b.name.lower() for b in armatureobject.data.bones]
        
        # Shapes
        for entry in [x for x in self.GetStructList('SPHERE') if x.bonename not in bonenameslower][::-1]:
            print("> Removing %s %s" % (entry.type, entry.name))
            self.RemoveStructEntry(entry)
        
        for entry in [x for x in self.GetStructList('OVAL') if x.bonename not in bonenameslower][::-1]:
            print("> Removing %s %s" % (entry.type, entry.name))
            self.RemoveStructEntry(entry)
        
        for entry in [x for x in self.GetStructList('ELLIPSOID') if x.bonename not in bonenameslower][::-1]:
            print("> Removing %s %s" % (entry.type, entry.name))
            self.RemoveStructEntry(entry)
        
        for entry in [x for x in self.GetStructList('PLANE') if x.bonename not in bonenameslower][::-1]:
            print("> Removing %s %s" % (entry.type, entry.name))
            self.RemoveStructEntry(entry)
        
        for entry in [x for x in self.GetStructList('CAPSULE') if (x.start_bonename not in bonenameslower or x.end_bonename not in bonenameslower)][::-1]:
            print("> Removing %s %s" % (entry.type, entry.name))
            self.RemoveStructEntry(entry)
        
        self.Update()
        
        # Groups
        shapenames = [x.name for x in self.GetShapeList()] + [""]
        
        for groupindex, group in list(enumerate(self.GetStructList('GROUP')))[::-1]:
            for i, entry in list(enumerate(group.data))[::-1]:
                if entry.hash40 not in shapenames:
                    print('> Removing "%s" from group "%s"' % (entry.hash40, group.name))
                    group.Remove(i)
            if len(group.data) == 0:
                print("> Removing %s %s" % ('GROUP', group.name))
                self.RemoveStruct('GROUP', groupindex)
        
        # Params
        for swingbone in self.GetStructList('BONE'):
            for paramindex, params in enumerate(swingbone.params):
                for i,c in list(enumerate(params.collisions))[::-1]:
                    if c.hash40 not in shapenames:
                        print('> Removing "%s" from params[%d] of Swing Bone "%s"' % (c.hash40, paramindex, swingbone.name))
                        params.RemoveCollision(i)
    
    # Clears struct list of type
    def ClearStructList(self, type):
        self.GetStructList(type).clear()
        self.Update()
    
    # Clears all data from all lists
    def Clear(self):
        for type in STRUCTTYPENAMES:
            self.ClearStructList(type)
    
    # Print all locations of given string
    def PrintReferences(self, name):
        print("=== References of \"%s\" in %s ===" % (name, self.name))
        for bi, b in enumerate(self.GetStructList('BONE')):
            if b.name == name:
                print("[BONE][%d %s].name: %s" % (bi, b.name, name))
            if b.start_bonename == name:
                print("[BONE][%d %s].start_bonename = %s" % (bi, b.name, name))
            if b.end_bonename == name:
                print("[BONE][%d %s].end_bonename = %s" % (bi, b.name, name))
            for pi, p in enumerate(b.params):
                for ci, c in enumerate(p.collisions):
                    if c.hash40 == name:
                        print("[BONE][%d %s].params[%d].collisions[%d].hash40 = %s" % (bi, b.name, pi, ci, name))
        
        for structtype in "SPHERE PLANE ELLIPSOID".split():
            for si, s in enumerate(self.GetStructList(structtype)):
                if s.name == name:
                    print("[%s][%d %s].name = %s" % (structtype, si, s.name, name))
                if s.bonename == name:
                    print("[%s][%d %s].bonename = %s" % (structtype, si, s.name, name))
        
        for si, s in enumerate(self.GetStructList('CAPSULE')):
            if s.name == name:
                print("[%s][%d %s].name = %s" % ('CAPSULE', si, s.name, name))
            if b.start_bonename == name:
                print("[%s][%d %s].start_bonename = %s" % ('CAPSULE', si, s.name, name))
            if b.end_bonename == name:
                print("[%s][%d %s].end_bonename = %s" % ('CAPSULE', si, s.name, name))
        
        print()
    
    # Generate collision groups from bones
    def GenerateCollisionGroups(self, validate=True):
        self.ClearStructList('GROUP')
        
        swing_ultimate = bpy.context.scene.swing_ultimate
        validgroups = swing_ultimate.prc_labels_collisions
        if len(validgroups) == 0:
            validate = False
        
        invalidgroups = [] # (groupname, param)
        
        for b in self.GetStructList('BONE'):
            for i, p in enumerate(b.params):
                groupname =  (
                    b.start_bonename if b.start_bonename == b.end_bonename else
                    b.start_bonename[:-1] + str(i+1)
                ) + "col"
                
                if (validate and groupname not in validgroups):
                    invalidgroups.append((groupname, p))
                    continue
                
                print("> Group \"%s\"" % groupname)
                group = self.AddStruct('GROUP')
                group.name = groupname
                
                for c in p.collisions:
                    if c.hash40:
                        group.Add(c.hash40)
        
        for groupname, p in invalidgroups:
            groupname = swing_ultimate.GetActiveData().FindClosestGroupLabel(groupname)[0]
            print("> Group \"%s\"" % groupname)
            group = self.AddStruct('GROUP')
            group.name = groupname
            
            for c in p.collisions:
                if c.hash40:
                    group.Add(c.hash40)
    
    # Returns label lose enough to given string
    def FindClosestGroupLabel(self, label, print_count=8):
        usedlabels = [g.name for g in self.groups]
        targetlabels = [x.name for x in bpy.context.scene.swing_ultimate.prc_labels_collisions if x.name not in usedlabels]
        
        Sqr = lambda x: x*x
        Abs = lambda x: x if x >= 0 else -x
        labeln = len(label)
        
        targetlabels.sort(key=lambda x: sum([ Abs(ord(c1)-ord(c2)) for c1,c2 in zip(label, x)] ) + Sqr(len(x)-labeln) )
        return targetlabels[:print_count]

classlist.append(SwingData)

Items_SwingData_Properties_UIView = (
    ('BONE', "Swing Bone", "", STRUCTICONS['BONE'], 0),
    ('SHAPE', "Shape", "", 'PHYSICS', 1),
    ('CONNECTION', "Connection", "", STRUCTICONS['CONNECTION'], 2),
    ('GROUP', "Group", "", STRUCTICONS['GROUP'], 3),
)

Items_SwingData_Properties_UISwing = (
    ('BONE', "Swing Bone", ""),
    ('PARAM', "Parameters", ""),
    ('BOTH', "BOTH", ""),
)

Items_SwingData_Properties_UIShape = (
    ('SPHERE', "Sphere", "", STRUCTICONS['SPHERE'], 0),
    ('OVAL', "Oval", "", STRUCTICONS['OVAL'], 1),
    ('ELLIPSOID', "Ellipsoid", "", STRUCTICONS['ELLIPSOID'], 2),
    ('CAPSULE', "Capsule", "", STRUCTICONS['CAPSULE'], 3),
    ('PLANE', "Plane", "", STRUCTICONS['PLANE'], 4),
)

class SwingSceneData(bpy.types.PropertyGroup):
    data : bpy.props.CollectionProperty(type=SwingData)
    index : bpy.props.EnumProperty(name="Active Swing Data", default=0, items=SwingSceneNames)
    count : bpy.props.IntProperty()
    
    prc_labels_string : bpy.props.StringProperty(default="")
    prc_labels_roots : bpy.props.StringProperty(default="")
    
    prc_labels_bonename : bpy.props.CollectionProperty(type=SwingData_Label)
    prc_labels_swingbone : bpy.props.CollectionProperty(type=SwingData_Label)
    prc_labels_collisions : bpy.props.CollectionProperty(type=SwingData_Label)
    
    show_search : bpy.props.BoolProperty(name="Show Label Search", default=False)
    
    ui_view_left : bpy.props.EnumProperty(items=Items_SwingData_Properties_UIView)
    ui_swing_left : bpy.props.EnumProperty(items=Items_SwingData_Properties_UISwing)
    ui_shape_left : bpy.props.EnumProperty(items=Items_SwingData_Properties_UIShape)
    
    ui_view_right : bpy.props.EnumProperty(items=Items_SwingData_Properties_UIView)
    ui_swing_right : bpy.props.EnumProperty(items=Items_SwingData_Properties_UISwing)
    ui_shape_right : bpy.props.EnumProperty(items=Items_SwingData_Properties_UIShape)
    
    properties_split_view : bpy.props.BoolProperty(name="Split View", default=False)
    
    def FindPRCIndex(self, name):
        return [x.index for x in self.data if x.name == name][0]
    
    # Returns swing data by name
    def FindData(self, name):
        for prc in self.data:
            if prc.name == name:
                return prc
        return None
    
    # Returns index of active data
    def GetActiveIndex(self):
        return int(self.index)
    
    # Returns active swing data
    def GetActiveData(self):
        return self.data[int(self.index)] if self.count > 0 else None
    
    # Adds and returns new swing data
    def Add(self, name="New Swing Data"):
        prc = self.data.add()
        prc.name = name + " %d" % self.count
        self.UpdateIndex()
        self.index = str(prc.index)
        return prc
    
    # Removes swing data at index
    def Remove(self, index):
        if self.count > 0:
            self.data.remove(index)
            self.UpdateIndex()
    
    # Updates indices of swing data entries
    def UpdateIndex(self, update_enum=True):
        self.count = len(self.data)
        if self.count > 0:
            for i, prc in enumerate(self.data):
                prc.index = i
            self.index = str(max(0, min(len(self.data), int(self.index if self.index else self.count-1))))
    
    # Updates labels from CSV file
    def UpdateLabels(self, path):
        print("> Parsing Labels...")
        with open(path, 'r') as csvfile:
            csvreader = csv.reader(csvfile)
            fields = next(csvreader)
            
            labels = [r for r in csvreader]
            labels.sort(key=lambda x: x[1])
            
            self.prc_labels_string = "".join(
                r[1] + " "
                for r in labels if sum([1 for x in r[1] if x.upper() in "QWERTYUIOPASDFGHJKLZXCVBNM"])
            )
            
            self.prc_labels_bonename.clear()
            self.prc_labels_swingbone.clear()
            self.prc_labels_collisions.clear()
            
            # Generate String Lists ---------------------------------
            nextlabels = []
            swingnames = []
            
            # Swing
            for hex, label in labels:
                if label[:2] == 's_' and label[-3:] != 'col':
                    self.prc_labels_swingbone.add().name = label
                    swingnames.append(label)
                else:
                    nextlabels.append(label)
            
            # Bone
            for label in nextlabels:
                if label[-3:] == 'col':
                    self.prc_labels_collisions.add().name = label
                elif sum([1 for x in swingnames if 's_'+(label) == x]):
                    self.prc_labels_bonename.add().name = label
                
        
        print("> Labels updated. Count = %d" % len(labels))
        print("> %d Swing Names" % len(self.prc_labels_bonename))
        print("> %d Swing Bones" % len(self.prc_labels_swingbone))
        print("> %d Swing Collisions" % len(self.prc_labels_collisions))
        
        return True
    
    # Returns label matching or close enough to given string
    def FindClosestLabel(self, label, print_count=8):
        targetlabels = self.prc_labels_string.split()
        
        Sqr = lambda x: x*x
        Abs = lambda x: x if x >= 0 else -x
        labeln = len(label)
        
        targetlabels.sort(key=lambda x: sum([ Abs(ord(c1)-ord(c2)) for c1,c2 in zip(label, x)] ) + Sqr(len(x)-labeln) )
        return targetlabels[:print_count]
    
    # Refreshes drivers for visuals
    def UpdateVisuals(self):
        for prc in self.data:
            for sbone in prc.swingbones:
                for param in sbone.params:
                    objs = []
                    if param.object_minangley:
                        objs.append(param.object_minangley)
                    if param.object_minanglez:
                        objs.append(param.object_minanglez)
                    for obj in objs:
                        if obj.animation_data:
                            for fc in obj.animation_data.drivers:
                                fc.driver.expression = fc.driver.expression
classlist.append(SwingSceneData)

"================================================================================================"
"OPERATORS"
"================================================================================================"

# ----------------------------------------------------------------------------------------
class SWINGULT_OP_UpdateLabels(bpy.types.Operator, ImportHelper):
    """Reads and stores parameter labels from CSV file"""
    bl_idname = "swingult.update_labels"
    bl_label = "Update Labels"
    
    filename_ext = ".csv"
    filter_glob: bpy.props.StringProperty(default="*.csv", options={'HIDDEN'}, maxlen=255)
    
    def execute(self, context):
        context.scene.swing_ultimate.UpdateLabels(self.filepath)
        self.report({'INFO'}, "Labels parsed")
        return {'FINISHED'}
classlist.append(SWINGULT_OP_UpdateLabels)

# ----------------------------------------------------------------------------------------
class SWINGULT_OP_RemoveLabels(bpy.types.Operator):
    """Removes stored labels. (Use if render panel crashes Blender)"""
    bl_idname = "swingult.clear_labels"
    bl_label = "Clear Labels"
    
    def execute(self, context):
        context.scene.swing_ultimate.prc_labels_string = ""
        return {'FINISHED'}
classlist.append(SWINGULT_OP_RemoveLabels)

# ----------------------------------------------------------------------------------------
class SWINGULT_OP_SwingData_New(bpy.types.Operator):
    bl_idname = "swingult.new"
    bl_label = "New Swing Data"
    bl_description = "Adds new swing data"
    bl_options = {'REGISTER', 'UNDO'}
    
    name : bpy.props.StringProperty(name="Entry Name", default="New Swing Data")
    
    def execute(self, context):
        context.scene.swing_ultimate.Add(self.name)
        return {'FINISHED'}
classlist.append(SWINGULT_OP_SwingData_New)

# ----------------------------------------------------------------------------------------
class SWINGULT_OP_SwingData_Remove(bpy.types.Operator):
    bl_idname = "swingult.remove"
    bl_label = "New Swing Data"
    bl_description = "Adds new swing data"
    bl_options = {'REGISTER', 'UNDO'}
    
    index : bpy.props.IntProperty()
    
    def execute(self, context):
        context.scene.swing_ultimate.Remove(self.index)
        return {'FINISHED'}
classlist.append(SWINGULT_OP_SwingData_Remove)

# ----------------------------------------------------------------------------------------
class SWINGULT_OP_SwingData_FromXML(bpy.types.Operator, ImportHelper):
    bl_idname = "swingult.xml_read"
    bl_label = "Import Some Data"
    bl_description = "Reads and applies swing data from XML file"
    
    filename_ext = ".xml"
    filter_glob: bpy.props.StringProperty(default="*.xml", options={'HIDDEN'}, maxlen=255)
    
    def execute(self, context):
        context.scene.swing_ultimate.GetActiveData().FromXML(self.filepath)
        return {'FINISHED'}
classlist.append(SWINGULT_OP_SwingData_FromXML)

# ----------------------------------------------------------------------------------------
class SWINGULT_OP_SwingData_ToXML(bpy.types.Operator, ExportHelper):
    bl_idname = "swingult.xml_save"
    bl_label = "Serialize Swing Data"
    bl_description = "Exports swing data to XML file"
    
    filename_ext = ".xml"
    filter_glob: bpy.props.StringProperty(default="*.xml", options={'HIDDEN'}, maxlen=255)
    
    def execute(self, context):
        out = context.scene.swing_ultimate.GetActiveData().Serialize()
        file = open(self.filepath, "w")
        file.write(out)
        file.close()
        return {'FINISHED'}
classlist.append(SWINGULT_OP_SwingData_ToXML)

# ----------------------------------------------------------------------------------------
class SWINGULT_OP_SwingData_Clean(bpy.types.Operator):
    bl_idname = "swingult.clean"
    bl_label = "Clean Swing Data (BETA)"
    bl_description = "Removes unused/unlinked data from swing data"
    bl_options = {'REGISTER', 'UNDO'}
    
    armature_object : bpy.props.EnumProperty(name="Reference Armature", items = lambda s,c: (
        (x.name, x.name, x.name) for x in bpy.data.objects if x.type == 'ARMATURE'
    ))
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        context.scene.swing_ultimate.GetActiveData().Clean(bpy.data.objects[self.armature_object])
        return {'FINISHED'}
classlist.append(SWINGULT_OP_SwingData_Clean)

# ----------------------------------------------------------------------------------------
class SWINGULT_OP_SwingData_Validate(bpy.types.Operator):
    """Checks hashes against stored labels"""
    bl_idname = "swingult.validate"
    bl_label = "Validate Hashes"
    
    def execute(self, context):
        swing_ultimate = context.scene.swing_ultimate
        active = swing_ultimate.GetActiveData()
        conflicts = active.Validate()
        
        if conflicts == None:
            self.report({'INFO'}, "No labels loaded to reference. Use \"Update Labels\" to load from ParamLabels.csv on disk")
        
        elif len(conflicts) > 0:
            self.report({'INFO'}, "%d Conflicts. First is %s. Suggestions: %s" % (len(conflicts), conflicts[0], " ".join(active.FindClosestGroupLabel(conflicts[0][2], 4))) )
        else:
            self.report({'INFO'}, "No conflicts found")
        return {'FINISHED'}
classlist.append(SWINGULT_OP_SwingData_Validate)

"# ========================================================================================================="

class SWINGULT_OP_SwingDataStruct_New(bpy.types.Operator): 
    bl_idname = "swingult.struct_add"
    bl_label = "New Swing Data Struct"
    bl_description = "Adds new entry to target struct"
    bl_options = {'REGISTER', 'UNDO'}
    
    copy_active : bpy.props.BoolProperty(name="Copy Active", default=True)
    
    type : bpy.props.EnumProperty(name="Entry Name", items=Items_StructType)
    
    def execute(self, context):
        context.scene.swing_ultimate.GetActiveData().AddStruct(self.type, self.copy_active)
        return {'FINISHED'}
classlist.append(SWINGULT_OP_SwingDataStruct_New)

# ----------------------------------------------------------------------------------------
class SWINGULT_OP_SwingDataStruct_Remove(bpy.types.Operator): 
    bl_idname = "swingult.struct_remove"
    bl_label = "Remove Active Struct"
    bl_description = "Removes active entry"
    bl_options = {'REGISTER', 'UNDO'}
    
    type : bpy.props.EnumProperty(name="Entry Name", items=Items_StructType)
    
    def execute(self, context):
        context.scene.swing_ultimate.GetActiveData().RemoveStruct(self.type)
        return {'FINISHED'}
classlist.append(SWINGULT_OP_SwingDataStruct_Remove)

# ----------------------------------------------------------------------------------------
class SWINGULT_OP_SwingDataStruct_Move(bpy.types.Operator): 
    bl_idname = "swingult.struct_move"
    bl_label = "Move Struct"
    bl_description = "Moves active entry in struct list"
    bl_options = {'REGISTER', 'UNDO'}
    
    type : bpy.props.EnumProperty(name="Struct Type", items=Items_StructType)
    direction : bpy.props.EnumProperty(name="Direction", items=Items_MoveDirection)
    
    def execute(self, context):
        context.scene.swing_ultimate.GetActiveData().MoveStruct(self.type, self.direction)
        return {'FINISHED'}
classlist.append(SWINGULT_OP_SwingDataStruct_Move)

"# ========================================================================================================="

class SWINGULT_OP_SwingBone_Transfer(bpy.types.Operator): 
    bl_idname = "swingult.swing_bone_transfer"
    bl_label = "Transfer Swing Bone"
    bl_description = "Adds Swing Bone and relevant data from other swing data"
    bl_options = {'REGISTER', 'UNDO'}
    
    source_prc : bpy.props.EnumProperty(name="Source PRC (From)", items = SwingEditItems_Active)
    target_prc : bpy.props.EnumProperty(name="Target PRC (To)", items = SwingEditItems_Active)
    
    bonename : bpy.props.EnumProperty(
        name="Swing Bone",
        items = lambda self,context,: [(x.name, x.name, x.name) for x in context.scene.swing_ultimate.FindData(self.source_prc).GetStructList('BONE')]
    )
    
    transfer_shapes : bpy.props.BoolProperty(name="Transfer Shapes", default=False)
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        swing_ultimate = context.scene.swing_ultimate
        swing_ultimate.FindData(self.target_prc).TransferSwingBone(swing_ultimate.FindData(self.source_prc), self.bonename, self.transfer_shapes)
        return {'FINISHED'}
classlist.append(SWINGULT_OP_SwingBone_Transfer)

# ----------------------------------------------------------------------------------------
class SWINGULT_OP_SwingBoneParams_Add(bpy.types.Operator): 
    bl_idname = "swingult.swing_bone_params_add"
    bl_label = "New Swing Bone Params"
    bl_description = "Adds parameter entry"
    bl_options = {'REGISTER', 'UNDO'}
    
    copy_active : bpy.props.BoolProperty(name="Copy Active", default=True)
    
    def execute(self, context):
        prc = context.scene.swing_ultimate.GetActiveData()
        prc.GetStructActive('BONE').AddParams(self.copy_active)
        return {'FINISHED'}
classlist.append(SWINGULT_OP_SwingBoneParams_Add)

# ----------------------------------------------------------------------------------------
class SWINGULT_OP_SwingBoneParams_Remove(bpy.types.Operator): 
    bl_idname = "swingult.swing_bone_params_remove"
    bl_label = "New Swing Bone Params"
    bl_description = "Adds parameter entry"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        context.scene.swing_ultimate.GetActiveData().GetStructActive('BONE').RemoveParams()
        return {'FINISHED'}
classlist.append(SWINGULT_OP_SwingBoneParams_Remove)

# ----------------------------------------------------------------------------------------
class SWINGULT_OP_SwingBoneParams_Move(bpy.types.Operator): 
    bl_idname = "swingult.swing_bone_params_move"
    bl_label = "Move Param Entry"
    bl_description = "Moves active parameter entry"
    bl_options = {'REGISTER', 'UNDO'}
    
    direction : bpy.props.EnumProperty(name="Direction", items=Items_MoveDirection)
    
    def execute(self, context):
        context.scene.swing_ultimate.GetActiveData().GetStructActive('BONE').MoveParams(self.direction)
        return {'FINISHED'}
classlist.append(SWINGULT_OP_SwingBoneParams_Move)

# ----------------------------------------------------------------------------------------
class SWINGULT_OP_SwingBoneParamsCollision_Add(bpy.types.Operator): 
    bl_idname = "swingult.swing_bone_params_collision_add"
    bl_label = "New Swing Bone Params Collision"
    bl_description = "Adds collision entry to params"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        context.scene.swing_ultimate.GetActiveData().GetStructActive('BONE').GetParamsActive().AddCollision()
        return {'FINISHED'}
classlist.append(SWINGULT_OP_SwingBoneParamsCollision_Add)

# ----------------------------------------------------------------------------------------
class SWINGULT_OP_SwingBoneParamsCollision_Remove(bpy.types.Operator): 
    bl_idname = "swingult.swing_bone_params_collision_remove"
    bl_label = "Remove Swing Bone Params Collision"
    bl_description = "Removes active entry from params"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        context.scene.swing_ultimate.GetActiveData().GetStructActive('BONE').GetParamsActive().RemoveCollision()
        return {'FINISHED'}
classlist.append(SWINGULT_OP_SwingBoneParamsCollision_Remove)

# ----------------------------------------------------------------------------------------
class SWINGULT_OP_SwingBoneParamsCollision_Move(bpy.types.Operator): 
    bl_idname = "swingult.swing_bone_params_collision_move"
    bl_label = "Move Collision Entry"
    bl_description = "Moves active collision entry"
    bl_options = {'REGISTER', 'UNDO'}
    
    direction : bpy.props.EnumProperty(name="Direction", items=Items_MoveDirection)
    
    def execute(self, context):
        context.scene.swing_ultimate.GetActiveData().GetStructActive('BONE').GetParamsActive().MoveCollision(self.direction)
        return {'FINISHED'}
classlist.append(SWINGULT_OP_SwingBoneParamsCollision_Move)

"# ========================================================================================================="

class SWINGULT_OP_Struct_Transfer(bpy.types.Operator): 
    bl_idname = "swingult.struct_transfer"
    bl_label = "Transfer Struct"
    bl_description = "Adds struct from other PRC"
    bl_options = {'REGISTER', 'UNDO'}
    
    source_prc : bpy.props.EnumProperty(name="Source PRC (From)", items = SwingEditItems_Active)
    target_prc : bpy.props.EnumProperty(name="Target PRC (To)", items = SwingEditItems_Active)
    
    type : bpy.props.EnumProperty(name="Struct Type", items=Items_StructType)
    
    structindex : bpy.props.EnumProperty(
        name="Struct Index",
        items = lambda self,context,: [(str(i), x.name, x.name) for i,x in enumerate(context.scene.swing_ultimate.FindData(self.source_prc).GetStructList(self.type))]
    )
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        swing_ultimate = context.scene.swing_ultimate
        swing_ultimate.FindData(self.target_prc).TransferStruct(
            swing_ultimate.FindData(self.source_prc),
            self.type,
            int(self.structindex)
            )
        return {'FINISHED'}
classlist.append(SWINGULT_OP_Struct_Transfer)

# ----------------------------------------------------------------------------------------
class SWINGULT_OP_Connection_Transfer(bpy.types.Operator): 
    bl_idname = "swingult.connections_transfer"
    bl_label = "Transfer Connection"
    bl_description = "Adds connection from other PRC data"
    bl_options = {'REGISTER', 'UNDO'}
    
    source_prc : bpy.props.EnumProperty(name="Source PRC (From)", items = SwingEditItems_Active)
    target_prc : bpy.props.EnumProperty(name="Target PRC (To)", items = SwingEditItems_Active)
    
    connection_index : bpy.props.EnumProperty(
        name="Connection",
        items = lambda self,context,: [
            (str(i), "[%d] (%s) ... (%s)" % (i, x.start_bonename, x.end_bonename), str(i), 'BLANK', i) 
            for i,x in enumerate(context.scene.swing_ultimate.FindData(self.source_prc).GetStructList('CONNECTION'))
            ]
    )
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        swing_ultimate = context.scene.swing_ultimate
        swing_ultimate.FindData(self.target_prc).TransferConnection(swing_ultimate.FindData(self.source_prc), int(self.connection_index))
        return {'FINISHED'}
classlist.append(SWINGULT_OP_Connection_Transfer)

# ----------------------------------------------------------------------------------------
class SWINGULT_OP_Connection_Transfer_Pattern(bpy.types.Operator): 
    bl_idname = "swingult.connections_transfer_pattern"
    bl_label = "Transfer Connection by Pattern"
    bl_description = "Adds connections from other PRC data that contains the given string"
    bl_options = {'REGISTER', 'UNDO'}
    
    source_prc : bpy.props.EnumProperty(name="Source PRC (From)", items = SwingEditItems_Active)
    target_prc : bpy.props.EnumProperty(name="Target PRC (To)", items = SwingEditItems_Active)
    
    pattern : bpy.props.StringProperty(name="Pattern String", default="s_hair")
    
    check_start : bpy.props.BoolProperty(name="Check Start Bone", default=True)
    check_end : bpy.props.BoolProperty(name="Check End Bone", default=False)
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        swing_ultimate = context.scene.swing_ultimate
        swing_ultimate.FindData(self.target_prc).TransferConnectionPattern(
            swing_ultimate.FindData(self.source_prc),
            self.pattern,
            self.check_start,
            self.check_end
            )
        return {'FINISHED'}
classlist.append(SWINGULT_OP_Connection_Transfer_Pattern)

# ----------------------------------------------------------------------------------------
class SWINGULT_OP_SwingData_PrintReferences(bpy.types.Operator): 
    bl_idname = "swingult.print_references"
    bl_label = "Print String References"
    bl_description = "Prints all instances of given string in swing data"
    bl_options = {'REGISTER', 'UNDO'}
    
    name : bpy.props.StringProperty(name="String", default="s_hair")
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        context.scene.swing_ultimate.GetActiveData().PrintReferences(self.name)
        return {'FINISHED'}
classlist.append(SWINGULT_OP_SwingData_PrintReferences)

# ----------------------------------------------------------------------------------------
class SWINGULT_OP_SwingData_GenerateCollisionGroups(bpy.types.Operator): 
    bl_idname = "swingult.generate_collision_groups"
    bl_label = "Generate Collision Groups"
    bl_description = "Creates collision groups using parameter bone names for each swing bone"
    bl_options = {'REGISTER', 'UNDO'}
    
    validate : bpy.props.BoolProperty(
        name="Validate",
        description="Groups are only created if generated name is in loaded labels",
        default=True
        )
        
    @classmethod
    def poll(self, context):
        return context.scene.swing_ultimate.data
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        context.scene.swing_ultimate.GetActiveData().GenerateCollisionGroups(self.validate)
        return {'FINISHED'}
classlist.append(SWINGULT_OP_SwingData_GenerateCollisionGroups)

"# ========================================================================================================="

# ----------------------------------------------------------------------------------------
class SWINGULT_OP_Armature_CreateParamVisuals(bpy.types.Operator): 
    bl_idname = "swingult.create_parameter_visuals"
    bl_label = "Create Swing Bone Parameter Visuals"
    bl_description = "Creates rotation visuals for selected pose bones"
    bl_options = {'REGISTER', 'UNDO'}
    
    prc : bpy.props.StringProperty(name="Swing PRC")
    foundbones = []
    
    @classmethod
    def poll(self, context):
        return context.object and context.object.type == 'ARMATURE' and context.scene.swing_ultimate.GetActiveData()
    
    def invoke(self, context, event):
        prc = context.scene.swing_ultimate.GetActiveData()
        self.prc = prc.name
        self.bone_name = context.active_pose_bone.name if context.active_pose_bone else ""
        
        self.foundbones = []
        
        for pb in context.object.pose.bones:
            if pb.bone.select:
                sbone, param = prc.FindBoneParamsByName(pb.name)
                if param:
                    self.foundbones.append(pb.name)
        self.foundbones = list(set(self.foundbones))
        
        return context.window_manager.invoke_props_dialog(self, width=400)
    
    def draw(self, context):
        layout = self.layout
        layout.prop_search(self, 'prc', context.scene.swing_ultimate, 'data')
        c = layout.column()
        r = c.row()
        r.alignment = 'CENTER'
        r.label(text="== Selected Swing Bones ==")
        g = c.column_flow(columns=3)
        for b in self.foundbones:
            g.label(text=b, icon=STRUCTICONS['BONE'])
    
    def execute(self, context):
        prc = context.scene.swing_ultimate.GetActiveData()
        
        for pb in context.object.pose.bones:
            if pb.bone.select:
                sbone, param = prc.FindBoneParamsByName(pb.name)
                if param:
                    sbone, param = prc.FindBoneParamsByName(pb.name)
                    print("> Creating visuals for %s" % pb.name)
                    param.CreateVisualObjects(context.object, pb.name, prc, sbone)
                    
        
        return {'FINISHED'}
classlist.append(SWINGULT_OP_Armature_CreateParamVisuals)

# ----------------------------------------------------------------------------------------
class SWINGULT_OP_Armature_CreateShapeVisuals(bpy.types.Operator): 
    bl_idname = "swingult.create_shape_visuals"
    bl_label = "Create Swing Shape Visuals"
    bl_description = "Creates visuals for collision shapes"
    bl_options = {'REGISTER', 'UNDO'}
    
    prc : bpy.props.StringProperty(name="Swing PRC")
    
    @classmethod
    def poll(self, context):
        return context.object and context.object.type == 'ARMATURE' and context.scene.swing_ultimate.GetActiveData()
    
    def invoke(self, context, event):
        prc = context.scene.swing_ultimate.GetActiveData()
        self.prc = prc.name
        return context.window_manager.invoke_props_dialog(self, width=400)
    
    def draw(self, context):
        layout = self.layout
        layout.prop_search(self, 'prc', context.scene.swing_ultimate, 'data')
        layout.label(text="Armature: " + str(context.object.name), icon='ARMATURE_DATA')
    
    def execute(self, context):
        prc = context.scene.swing_ultimate.GetActiveData()
        
        for shape in prc.GetShapeList():
            print("> Creating visuals for %s %s" % (shape.type, shape.name))
            shape.CreateVisualObjects(context.object, prc)
        
        return {'FINISHED'}
classlist.append(SWINGULT_OP_Armature_CreateShapeVisuals)

# ----------------------------------------------------------------------------------------
class SWINGULT_OP_Armature_SymmetrizeParams(bpy.types.Operator): 
    bl_idname = "swingult.symmetrize_parameters"
    bl_label = "Symmetrize Parameters"
    bl_description = "Copies parameters of selected swing bones to mirrored bone on X-Axis"
    bl_options = {'REGISTER', 'UNDO'}
    
    values : bpy.props.BoolProperty(name="Copy Values", default=True)
    collisions : bpy.props.BoolProperty(name="Copy Collisions", default=False)
    
    flip_z : bpy.props.BoolProperty(name="Flip Z", default=False)
    flip_y : bpy.props.BoolProperty(name="Flip Y", default=False)
    
    @classmethod
    def poll(self, context):
        obj = context.object
        return obj and obj.type == 'ARMATURE' and obj.mode == 'POSE' and context.active_pose_bone and context.scene.swing_ultimate.GetActiveData()
    
    def execute(self, context):
        bpy.ops.object.mode_set(mode='OBJECT')
        
        prc = context.scene.swing_ultimate.GetActiveData()
        shapenames = [x.name for x in prc.GetShapeList()]
        
        for pb in context.object.pose.bones:
            if pb.bone.select:
                sbone, param = prc.FindBoneParamsByName(pb.name)
                if param:
                    flipname = FlipSmashName(pb.name)
                    
                    if flipname != pb.name:
                        sbone2, param2 = prc.FindBoneParamsByName(flipname)
                        if param2:
                            print("> %s -> %s" % (pb.name, flipname) )
                            param2.CopyFromOther(param, self.values, self.collisions)
                            
                            if self.values:
                                if self.flip_z:
                                    pair = (param2.minanglez, param2.maxanglez)
                                    param2.minanglez = -pair[0]
                                    param2.maxanglez = -pair[1]
                                if self.flip_y:
                                    pair = (param2.minangley, param2.maxangley)
                                    param2.minangley = -pair[0]
                                    param2.maxangley = -pair[1]
        
        bpy.ops.object.mode_set(mode='POSE')
        
        return {'FINISHED'}
classlist.append(SWINGULT_OP_Armature_SymmetrizeParams)

# ----------------------------------------------------------------------------------------
class SWINGULT_OP_Armature_CopyParamsToSelected(bpy.types.Operator): 
    bl_idname = "swingult.active_params_to_selected"
    bl_label = "Copy Active Params To Selected"
    bl_description = "Copies parameters of active swing bones to selected bones"
    bl_options = {'REGISTER', 'UNDO'}
    
    copy_chain : bpy.props.BoolProperty(
        name="Copy Chain",
        description="Copy parameter values by index in bone chain",
        default=True,
        )
    values : bpy.props.BoolProperty(name="Copy Values", default=True)
    collisions : bpy.props.BoolProperty(name="Copy Collisions", default=False)
    
    flip_z : bpy.props.BoolProperty(name="Flip Z", default=False)
    flip_y : bpy.props.BoolProperty(name="Flip Y", default=False)
    
    @classmethod
    def poll(self, context):
        obj = context.object
        return obj and obj.type == 'ARMATURE' and obj.mode == 'POSE' and context.active_pose_bone and context.scene.swing_ultimate.GetActiveData()
    
    def execute(self, context):
        pbactive = context.active_pose_bone
        bpy.ops.object.mode_set(mode='OBJECT')
        
        prc = context.scene.swing_ultimate.GetActiveData()
        
        sboneactive, paramactive = prc.FindBoneParamsByName(pbactive.name)
        
        print(self.copy_chain)
        
        # Respect indices
        if self.copy_chain:
            print("> Copy Chain:")
            
            posebones = tuple(context.object.pose.bones)
            
            selectednames = [pb.name.lower() for pb in posebones if pb.bone.select]
            paramnames = [x.lower() for x in sboneactive.CalcParamNames()]
            chainindices = [i for i,x in enumerate(paramnames) if x.lower() in selectednames]
            
            for pb in context.object.pose.bones:
                if pb.name.lower() in paramnames:
                    continue
                
                if pb.bone.select:
                    sbone, param = prc.FindBoneParamsByName(pb.name)
                    if param:
                        paramindex = list(sbone.params).index(param)
                        
                        if paramindex in chainindices:
                            print("> %s -> %s" % (paramnames[paramindex], pb.name) )
                            
                            param.CopyFromOther(sboneactive.params[paramindex], self.values, self.collisions)
                            
                            if self.values:
                                if self.flip_z:
                                    pair = (param.minanglez, param.maxanglez)
                                    param.minanglez = -pair[0]
                                    param.maxanglez = -pair[1]
                                if self.flip_y:
                                    pair = (param.minangley, param.maxangley)
                                    param.minangley = -pair[0]
                                    param.maxangley = -pair[1]
        # Active to selected
        else:
            print("> Copy Active:")
            for pb in context.object.pose.bones:
                if pb == pbactive:
                    continue
                
                if pb.bone.select:
                    sbone, param = prc.FindBoneParamsByName(pb.name)
                    if param:
                        print("> %s -> %s" % (pbactive.name, pb.name) )
                        param.CopyFromOther(paramactive, self.values, self.collisions)
                        
                        if self.values:
                            if self.flip_z:
                                pair = (param.minanglez, param.maxanglez)
                                param.minanglez = -pair[0]
                                param.maxanglez = -pair[1]
                            if self.flip_y:
                                pair = (param.minangley, param.maxangley)
                                param.minangley = -pair[0]
                                param.maxangley = -pair[1]
        
        bpy.ops.object.mode_set(mode='POSE')
        
        return {'FINISHED'}
classlist.append(SWINGULT_OP_Armature_CopyParamsToSelected)

# ----------------------------------------------------------------------------------------
class SWINGULT_OP_Armature_ToggleVisualObjects(bpy.types.Operator): 
    bl_idname = "swingult.visual_toggle_swing_objects"
    bl_label = "Toggle Visual Bone Objects"
    bl_description = "Toggles visibility of visual swing bone objects"
    bl_options = {'REGISTER', 'UNDO'}
    
    selected_only : bpy.props.BoolProperty(name="Selected Only", default=True)
    
    @classmethod
    def poll(self, context):
        obj = context.object
        return obj and obj.type == 'ARMATURE' and obj.mode == 'POSE' and context.active_pose_bone and context.scene.swing_ultimate.GetActiveData()
    
    def execute(self, context):
        visobjects = [
            x
            for sbone in context.scene.swing_ultimate.GetActiveData().swingbones
            for param in sbone.params
            for x in (param.object_minangley, param.object_minanglez)
        ]
        
        if self.selected_only:
            selectedpbonenames = tuple([pb.name.lower() for pb in context.object.pose.bones if pb.bone.select])
            visobjects = []
            
            for sbone in context.scene.swing_ultimate.GetActiveData().swingbones:
                paramnames = [x.lower() for x in sbone.CalcParamNames()]
                visobjects += [
                    x
                    for i,param in enumerate(sbone.params) if paramnames[i] in selectedpbonenames
                    for x in (param.object_minangley, param.object_minanglez)
                ]
        else:
            visobjects = [
                x
                for sbone in context.scene.swing_ultimate.GetActiveData().swingbones
                for param in sbone.params
                for x in (param.object_minangley, param.object_minanglez)
            ]
        
        allon = sum([(not obj.hide_viewport) for obj in visobjects]) == len(visobjects)
        for obj in visobjects:
            obj.hide_viewport = allon
        
        # Update Dependencies
        context.scene.swing_ultimate.UpdateVisuals()
            
        return {'FINISHED'}
classlist.append(SWINGULT_OP_Armature_ToggleVisualObjects)

# ----------------------------------------------------------------------------------------
class SWINGULT_OP_Armature_IsloateSwingBoneVisibility(bpy.types.Operator): 
    bl_idname = "swingult.isolate_swing_bones_visibility"
    bl_label = "Isolate Swing Pose Bones"
    bl_description = "Hides/unhides pose bones without \"s_\" prefix"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(self, context):
        return context.object and context.object.type == 'ARMATURE' and context.object.mode == 'POSE' and context.scene.swing_ultimate.GetActiveData()
    
    def execute(self, context):
        bpy.ops.object.mode_set(mode='OBJECT')
        
        pbones = tuple(context.object.pose.bones)
        swingbones = [pb for pb in pbones if pb.name[:2].lower() == "s_"]
        nonswingbones = [pb for pb in pbones if pb.name[:2].lower() != "s_"]
        
        # Unhide other bones if all swing bones are visible
        if sum([pb.bone.hide for pb in nonswingbones]) == len(nonswingbones):
            print("Revealing")
            for pb in nonswingbones:
                pb.bone.hide = False
        else:
            print("Hiding")
            for pb in nonswingbones:
                pb.bone.hide = True
        
        # Update Dependencies
        context.scene.swing_ultimate.UpdateVisuals()
        
        bpy.ops.object.mode_set(mode='POSE')
        
        return {'FINISHED'}
classlist.append(SWINGULT_OP_Armature_IsloateSwingBoneVisibility)

"================================================================================================"
"UI LIST"
"================================================================================================"

class SWINGULT_UL_SwingEdit(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        r = layout.row(align=True)
        r.label(text='[%d] %s' % (index, item.name))
classlist.append(SWINGULT_UL_SwingEdit)

# --------------------------------------------------------------------------
class SWINGULT_UL_SwingData_SwingBone(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        r = layout.row(align=True)
        r.prop(item, 'name', text='[%d]' % index, emboss=False)
        rr = r.row()
        rr.scale_x = 0.8
        rr.label(text="(Size %d)" % len(item.params))
classlist.append(SWINGULT_UL_SwingData_SwingBone)

# --------------------------------------------------------------------------
class SWINGULT_UL_SwingData_SwingBone_Params(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        r = layout.row(align=True)
        r.label(text='Bone {0}: ({1} Collisions)'.format(index, len(item.collisions)), icon='PROPERTIES')
classlist.append(SWINGULT_UL_SwingData_SwingBone_Params)

# --------------------------------------------------------------------------
class SWINGULT_UL_SwingData_SwingBone_Params_Collisions(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        r = layout.row(align=True)
        swing_ultimate = context.scene.swing_ultimate
        if swing_ultimate.show_search:
            r.prop_search(item, 'hash40', swing_ultimate, 'prc_labels_collisions', text='[%d]' % index, icon='PHYSICS')
        else:
            r.prop(item, 'hash40', text='[%d]:' % index, icon='PHYSICS')
classlist.append(SWINGULT_UL_SwingData_SwingBone_Params_Collisions)

# --------------------------------------------------------------------------
class SWINGULT_UL_SwingData_CollisionStruct(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        r = layout.row(align=True)
        r.label(text='[%d] %s' % (index, item.name), icon=STRUCTICONS[item.type])
        r = r.row()
        r.scale_x = 0.9
        if item.type == 'CAPSULE':
            r.label(text="| %s - %s" % (item.start_bonename, item.end_bonename))
        else:
            r.label(text=item.bonename, icon='BONE_DATA')
classlist.append(SWINGULT_UL_SwingData_CollisionStruct)

# --------------------------------------------------------------------------
class SWINGULT_UL_SwingData_Connection(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        r = layout.row(align=True)
        r.label(text='[%d]: (%s) ... (%s)' % (index, item.start_bonename, item.end_bonename), icon=STRUCTICONS['CONNECTION'])
classlist.append(SWINGULT_UL_SwingData_Connection)

# --------------------------------------------------------------------------
class SWINGULT_UL_SwingData_Group(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        r = layout.row(align=True)
        r.label(text='[%d]: %s (%s)' % (index, item.name, item.size), icon=STRUCTICONS['GROUP'])
classlist.append(SWINGULT_UL_SwingData_Group)

"================================================================================================"
"PANELS"
"================================================================================================"

# =========================================================================================================
class SWINGULT_PT_SwingData_Scene(bpy.types.Panel):
    bl_label = 'Swing Scene'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SwingUlt" # Name of sidebar
    
    def draw(self, context):
        layout = self.layout
        
        swing_ultimate = context.scene.swing_ultimate
        prc = swing_ultimate.GetActiveData()
        
        if not prc:
            layout.operator('swingult.new', icon='ADD', text="New List")
        else:
            c = layout.column(align=True)
            r = c.row(align=True)
            r.prop(swing_ultimate, 'index', text='', icon='PRESET', icon_only=1)
            r.prop(swing_ultimate.GetActiveData(), 'name', text="")
            r = r.row(align=True)
            r.operator('swingult.new', icon='ADD', text="")
            r.operator('swingult.remove', icon='REMOVE', text="").index = swing_ultimate.GetActiveIndex()
            
            r = c.row(align=True)
            r.operator('swingult.update_labels', text="Update Labels")
            #r.prop(swing_ultimate, 'show_search', text="Show Search", toggle=True)
            r.operator('swingult.clear_labels', text="", icon='X')
            r = c.row(align=True)
            r.prop(swing_ultimate, 'show_search', text="Show Search For Strings")
classlist.append(SWINGULT_PT_SwingData_Scene)

# ---------------------------------------------------------------------------------------
class SWINGULT_PT_SwingData_3DView(bpy.types.Panel):
    bl_label = "Active Swing Data"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SwingUlt" # Name of sidebar
    
    def draw(self, context):
        layout = self.layout
        obj = context.object
        
        swing_ultimate = context.scene.swing_ultimate
        prc = swing_ultimate.GetActiveData()
        
        if not prc:
            layout.operator('swingult.new', icon='ADD', text="New List")
        else:
            c = layout.column()
            
            c.prop(prc, 'name')
            
            col = layout.column()
            
            r = col.row()
            r.operator('swingult.xml_read', icon='IMPORT', text="From XML")
            r.operator('swingult.xml_save', icon='EXPORT', text="To XML")
            #r.operator('swingult.visualize', icon='MESH_UVSPHERE', text="Visualize")
            
            r = col.row()
            #r.operator('swingult.clean', icon='FILE_REFRESH', text="Clean")
            r.operator('swingult.validate', icon='LINENUMBERS_ON', text="Validate")
            r.operator('swingult.print_references', icon='ZOOM_ALL', text="Find References")
            
            col.operator('swingult.generate_collision_groups', icon='SYSTEM', text="Generate Collision Groups")
            
            # Draw sizes
            c = layout.column(align=True)
            r = c.box().row(align=True)
            r.scale_y = 0.6
            for type in ['BONE', 'CONNECTION', 'GROUP']:
                r.label(text=str(prc.GetStructListSize(type)), icon=STRUCTICONS[type])
            
            r.label(text=str(prc.GetShapeCount()), icon='PHYSICS')
            
            r = c.box().row(align=True)
            r.scale_y = 0.6
            
            shapetypes = ['SPHERE', 'ELLIPSOID', 'CAPSULE', 'PLANE']
            shapetypes = ['SPHERE', 'OVAL', 'ELLIPSOID', 'CAPSULE', 'PLANE']
            
            for type in shapetypes:
                rr = r.row()
                rr.scale_x = 0.5
                rr.label(text=str(prc.GetStructListSize(type)), icon=STRUCTICONS[type])
classlist.append(SWINGULT_PT_SwingData_3DView)

# ---------------------------------------------------------------------------------------
class SWINGULT_PT_PoseMode_3DView(bpy.types.Panel): 
    bl_label = "Active Armature"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SwingUlt" # Name of sidebar
    bl_options = {'DEFAULT_CLOSED'}
    
    def DrawLayout(self, context, layout):
        c = layout.column()
        c.operator('swingult.create_shape_visuals', icon='PHYSICS', text="Create Shape Visuals")
        
        c.separator()
        
        c.operator('swingult.create_parameter_visuals', icon='BONE_DATA', text="Create Param Visuals")
        r = c.row().split(factor=0.8, align=1)
        r.operator('swingult.visual_toggle_swing_objects', icon='RESTRICT_SELECT_OFF').selected_only = True
        r.operator('swingult.visual_toggle_swing_objects', text="All", icon='WORLD').selected_only = False
        c.operator('swingult.symmetrize_parameters')
        c.operator('swingult.active_params_to_selected')
        c.operator('swingult.isolate_swing_bones_visibility')
        
        if context.object and context.object.type == 'ARMATURE':
            pb = context.active_pose_bone
            if pb:
                swing_ultimate = context.scene.swing_ultimate
                prc = swing_ultimate.GetActiveData()
                
                if prc:
                    sbone, param = prc.FindBoneParamsByName(pb.name)
                    if sbone:
                        sbone.DrawPanel(layout)
                        
                        if param:
                            layout.label(text=pb.name + " = %s.params[%d]" % (sbone.name, list(sbone.params).index(param)))
                            r = layout.row()
                            r.operator('swingult.create_parameter_visuals', text="Create Visuals")
                            
                            rr = r.row(align=True)
                            rr.scale_x = 0.8
                            if param.object_minangley:
                                rr.prop(param.object_minangley, 'hide_viewport', invert_checkbox=True, text="Show Y")
                            if param.object_minanglez:
                                rr.prop(param.object_minanglez, 'hide_viewport', invert_checkbox=True, text="Show Z")
                            
                            param.DrawPanel(layout)
    
    def draw(self, context):
        self.DrawLayout(context, self.layout)
classlist.append(SWINGULT_PT_PoseMode_3DView)
"========================================================================================================="

class StructPanelSuper(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SwingUlt" # Name of sidebar
    bl_parent_id = 'SWINGULT_PT_SwingData_3DView'
    bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(cls, context):
        return context.scene.swing_ultimate.GetActiveData()

# ---------------------------------------------------------------------------------------
class SWINGULT_PT_SwingData_3DView_SwingBoneHeader(StructPanelSuper): 
    bl_label = "Swing Bones"
    
    def DrawLayout(self, context, layout):
        type = 'BONE'
        col = layout
        prc = context.scene.swing_ultimate.GetActiveData()
        entry = prc.GetStructActive(type)
        
        if not entry:
            col.operator('swingult.struct_add', text="New Swing Bone").type = type
        else:
            r = col.row(align=True)
            r.template_list(
                "SWINGULT_UL_SwingData_SwingBone", "", prc, "swingbones", prc, "index_bone", rows=5)
            
            c = r.column(align=True)
            
            c.operator('swingult.struct_add', text="", icon='ADD').type = type
            c.operator('swingult.struct_remove', text="", icon='REMOVE').type = type
            
            c.separator()
            op = c.operator('swingult.struct_move', text="", icon='TRIA_UP')
            op.type = type
            op.direction = 'UP'
            op = c.operator('swingult.struct_move', text="", icon='TRIA_DOWN')
            op.type = type
            op.direction = 'DOWN'
            
            c.separator()
            c.operator('swingult.swing_bone_transfer', text="", icon='PASTEDOWN').target_prc = prc.name
    
    def draw(self, context):
        self.DrawLayout(context, self.layout)
classlist.append(SWINGULT_PT_SwingData_3DView_SwingBoneHeader)

# ---------------------------------------------------------------------------------------
class SWINGULT_PT_SwingData_3DView_SwingBone(StructPanelSuper): 
    bl_label = SUBPANELLABELSPACE + "Properties"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SwingUlt" # Name of sidebar
    bl_parent_id = 'SWINGULT_PT_SwingData_3DView_SwingBoneHeader'
    bl_options = {'DEFAULT_CLOSED'}
    
    def DrawLayout(self, context, layout):
        col = layout
        type = 'BONE'
        swing_ultimate = context.scene.swing_ultimate
        prc = swing_ultimate.GetActiveData()
        entry = prc.GetStructActive(type)
        
        if entry:
            entry.DrawPanel(layout)
    
    def draw(self, context):
        self.DrawLayout(context, self.layout)
classlist.append(SWINGULT_PT_SwingData_3DView_SwingBone)

# ---------------------------------------------------------------------------------------
class SWINGULT_PT_SwingData_3DView_SwingBone_Params(bpy.types.Panel):
    bl_label = SUBPANELLABELSPACE + "Params"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SwingUlt" # Name of sidebar
    bl_parent_id = 'SWINGULT_PT_SwingData_3DView_SwingBoneHeader'
    bl_options = {'DEFAULT_CLOSED'}
    
    def DrawLayout(self, context, layout):
        layout = layout.column(align=False)
        prc = context.scene.swing_ultimate.GetActiveData()
        swingbone = prc.GetStructActive('BONE')
        
        if swingbone:
            layout.prop(swingbone, 'name', text="", emboss=False, icon=STRUCTICONS['BONE'])
            
            r = layout.row(align=True)
            r.template_list(
                "SWINGULT_UL_SwingData_SwingBone_Params", "", swingbone, "params", swingbone, "index_param", rows=3)
            
            c = r.column(align=True)
            c.scale_y = 0.95
            c.operator('swingult.swing_bone_params_add', text="", icon='ADD')
            c.operator('swingult.swing_bone_params_remove', text="", icon='REMOVE')
            c.separator()
            c.operator('swingult.swing_bone_params_move', text="", icon='TRIA_UP').direction = 'UP'
            c.operator('swingult.swing_bone_params_move', text="", icon='TRIA_DOWN').direction = 'DOWN'
            
            if swingbone.params:
                entry = swingbone.params[swingbone.index_param]
                entry.DrawPanel(layout)
    
    def draw(self, context):
        self.DrawLayout(context, self.layout)
classlist.append(SWINGULT_PT_SwingData_3DView_SwingBone_Params)

# ---------------------------------------------------------------------------------------
class SWINGULT_PT_SwingData_3DView_CollisionShapeHeader(StructPanelSuper): 
    bl_label = "Collision Shapes"
    
    def draw(self, context):
        layout = self.layout
classlist.append(SWINGULT_PT_SwingData_3DView_CollisionShapeHeader)

# ---------------------------------------------------------------------------------------
class SWINGULT_PT_SwingData_3DView_Spheres(StructPanelSuper):
    bl_label = SUBPANELLABELSPACE + "Spheres"
    bl_parent_id = 'SWINGULT_PT_SwingData_3DView_CollisionShapeHeader'
    
    def DrawLayout(self, context, layout):
        type = 'SPHERE'
        col = layout
        prc = context.scene.swing_ultimate.GetActiveData()
        entry = prc.GetStructActive('SPHERE')
        
        DrawStructUIList(layout, prc, 'SPHERE', 'SWINGULT_UL_SwingData_CollisionStruct', "spheres", "index_sphere")
        
        if not entry:
            col.operator('swingult.struct_add', text="New Sphere").type = type
        else:
            entry.DrawPanel(layout)
    
    def draw(self, context):
        self.DrawLayout(context, self.layout)
classlist.append(SWINGULT_PT_SwingData_3DView_Spheres)

# ---------------------------------------------------------------------------------------
class SWINGULT_PT_SwingData_3DView_Ovals(StructPanelSuper):
    bl_label = SUBPANELLABELSPACE + "Ovals"
    bl_parent_id = 'SWINGULT_PT_SwingData_3DView_CollisionShapeHeader'
    
    def DrawLayout(self, context, layout):
        type = 'OVAL'
        col = self.layout
        prc = context.scene.swing_ultimate.GetActiveData()
        entry = prc.GetStructActive('OVAL')
        
        DrawStructUIList(layout, prc, 'OVAL', 'SWINGULT_UL_SwingData_CollisionStruct', "ovals", "index_oval")
        
        if not entry:
            col.operator('swingult.struct_add', text="New Oval").type = type
        else:
            entry.DrawPanel(layout)
    
    def draw(self, context):
        self.DrawLayout(context, self.layout)
classlist.append(SWINGULT_PT_SwingData_3DView_Ovals)

# ---------------------------------------------------------------------------------------
class SWINGULT_PT_SwingData_3DView_Ellipsoids(StructPanelSuper):
    bl_label = SUBPANELLABELSPACE + "Ellipsoids"
    bl_parent_id = 'SWINGULT_PT_SwingData_3DView_CollisionShapeHeader'
    
    def DrawLayout(self, context, layout):
        type = 'ELLIPSOID'
        prc = context.scene.swing_ultimate.GetActiveData()
        entry = prc.GetStructActive('ELLIPSOID')
        
        DrawStructUIList(layout, prc, type, 'SWINGULT_UL_SwingData_CollisionStruct', "ellipsoids", "index_ellipsoid")
        
        if not entry:
            layout.operator('swingult.struct_add', text="New Ellipsoid").type = type
        else:
            entry.DrawPanel(layout)
        
    def draw(self, context):
        self.DrawLayout(context, self.layout)
classlist.append(SWINGULT_PT_SwingData_3DView_Ellipsoids)

# ---------------------------------------------------------------------------------------
class SWINGULT_PT_SwingData_3DView_Capsules(StructPanelSuper):
    bl_label = SUBPANELLABELSPACE + "Capsules"
    bl_parent_id = 'SWINGULT_PT_SwingData_3DView_CollisionShapeHeader'
    
    def DrawLayout(self, context, layout):
        type = 'CAPSULE'
        prc = context.scene.swing_ultimate.GetActiveData()
        entry = prc.GetStructActive('CAPSULE')
        
        DrawStructUIList(layout, prc, 'CAPSULE', 'SWINGULT_UL_SwingData_CollisionStruct', "capsules", "index_capsule")
        
        if not entry:
            layout.operator('swingult.struct_add', text="New Capsule").type = type
        else:
            entry.DrawPanel(layout)
    
    def draw(self, context):
        self.DrawLayout(context, self.layout)
classlist.append(SWINGULT_PT_SwingData_3DView_Capsules)

# ---------------------------------------------------------------------------------------
class SWINGULT_PT_SwingData_3DView_Planes(StructPanelSuper):
    bl_label = SUBPANELLABELSPACE + "Planes"
    bl_parent_id = 'SWINGULT_PT_SwingData_3DView_CollisionShapeHeader'
    
    def DrawLayout(self, context, layout):
        type = 'PLANE'
        prc = context.scene.swing_ultimate.GetActiveData()
        entry = prc.GetStructActive('PLANE')
        
        DrawStructUIList(layout, prc, type, 'SWINGULT_UL_SwingData_CollisionStruct', "planes", "index_plane")
        
        if not entry:
            col.operator('swingult.struct_add', text="New Plane").type = type
        else:
            entry.DrawPanel(layout)
    
    def draw(self, context):
        self.DrawLayout(context, self.layout)
classlist.append(SWINGULT_PT_SwingData_3DView_Planes)

# ---------------------------------------------------------------------------------------
class SWINGULT_PT_SwingData_3DView_Connections(StructPanelSuper):
    bl_label = "Connections"
    
    def DrawLayout(self, context, layout):
        type = 'CONNECTION'
        prc = context.scene.swing_ultimate.GetActiveData()
        entry = prc.GetStructActive('CONNECTION')
        
        r = layout.row(align=True)
        
        r.template_list(
            "SWINGULT_UL_SwingData_Connection", "", prc, "connections", prc, "index_connection", rows=6)
        
        c = r.column(align=True)
        c.operator('swingult.struct_add', text="", icon='ADD').type = type
        c.operator('swingult.struct_remove', text="", icon='REMOVE').type = type
        
        c.separator()
        op = c.operator('swingult.struct_move', text="", icon='TRIA_UP')
        op.type = 'CONNECTION'
        op.direction = 'UP'
        op = c.operator('swingult.struct_move', text="", icon='TRIA_DOWN')
        op.type = 'CONNECTION'
        op.direction = 'DOWN'
        
        c.separator()
        c.operator('swingult.connections_transfer', text="", icon='PASTEDOWN').target_prc = prc.name
        c.operator('swingult.connections_transfer_pattern', text="", icon='BORDERMOVE').target_prc = prc.name
        
        if not entry:
            layout.operator('swingult.struct_add', text="New Connection").type = type
        else:
            entry.DrawPanel(layout)
    
    def draw(self, context):
        self.DrawLayout(context, self.layout)
classlist.append(SWINGULT_PT_SwingData_3DView_Connections)

# ---------------------------------------------------------------------------------------
class SWINGULT_PT_SwingData_3DView_Groups(StructPanelSuper):
    bl_label = "Groups"
    
    def DrawLayout(self, context, layout):
        type = 'GROUP'
        prc = context.scene.swing_ultimate.GetActiveData()
        entry = prc.GetStructActive(type)
        
        r = layout.row(align=True)
        
        r.template_list(
            "SWINGULT_UL_SwingData_Group", "", prc, "groups", prc, "index_group", rows=5)
        
        c = r.column(align=True)
        c.operator('swingult.struct_add', text="", icon='ADD').type = type
        c.operator('swingult.struct_remove', text="", icon='REMOVE').type = type
        c.separator()
        op = c.operator('swingult.struct_move', text="", icon='TRIA_UP')
        op.type = type
        op.direction = 'UP'
        op = c.operator('swingult.struct_move', text="", icon='TRIA_DOWN')
        op.type = type
        op.direction = 'DOWN'
        
        if not entry:
            layout.operator('swingult.struct_add', text="New Group").type = type
        else:
            
            b = layout.box().column(align=True)
            if context.scene.swing_ultimate.show_search:
                b.prop_search(entry, 'name', context.scene.swing_ultimate, 'prc_labels_collisions')
            else:
                b.prop(entry, 'name')
            
            activegroup = prc.groups[prc.index_group]
            
            layout.template_list(
                "SWINGULT_UL_SwingData_SwingBone_Params_Collisions", "", activegroup, "data", activegroup, "active_index", rows=5)
    
    def draw(self, context):
        self.DrawLayout(context, self.layout)
classlist.append(SWINGULT_PT_SwingData_3DView_Groups)

"========================================================================================================="

# ---------------------------------------------------------------------------------------
class SWINGULT_PT_SwingData_Properties(bpy.types.Panel):
    bl_label = "Swing Data"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'scene'
    
    def draw(self, context):
        layout = self.layout
        
        SWINGULT_PT_SwingData_Scene.draw(self, context)
        SWINGULT_PT_SwingData_3DView.draw(self, context)
        
        swing_ultimate = context.scene.swing_ultimate
        
        row = layout.row()
classlist.append(SWINGULT_PT_SwingData_Properties)

# ---------------------------------------------------------------------------------------
class SWINGULT_PT_SwingData_Properties_Data(bpy.types.Panel):
    bl_label = "Swing Data"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'scene'
    bl_parent_id = 'SWINGULT_PT_SwingData_Properties'
    bl_options = {'DEFAULT_CLOSED'}
    
    def DrawLayout(self, context, layout):
        layout = self.layout
        
        swing_ultimate = context.scene.swing_ultimate
        
        layout.prop(swing_ultimate, 'properties_split_view')
        
        row = layout.row(align=True)
        
        splitview = swing_ultimate.properties_split_view
        if splitview:
            rowcolumns = [row.box().column(), row.box().column()]
        else:
            rowcolumns = [row.column()]
        
        
        c = rowcolumns[0].column()
        c.row().prop_tabs_enum(swing_ultimate, "ui_view_left")
        if swing_ultimate.ui_view_left == 'BONE':
            c.row().prop_tabs_enum(swing_ultimate, "ui_swing_left")
        elif swing_ultimate.ui_view_left == 'SHAPE':
            c.row().prop_tabs_enum(swing_ultimate, "ui_shape_left")
        
        viewmeta = [(swing_ultimate.ui_view_left, swing_ultimate.ui_swing_left, swing_ultimate.ui_shape_left)]
        
        if splitview:
            c = rowcolumns[1].column()
            c.row().prop_tabs_enum(swing_ultimate, "ui_view_right")
            if swing_ultimate.ui_view_right == 'BONE':
                c.row().prop_tabs_enum(swing_ultimate, "ui_swing_right")
            elif swing_ultimate.ui_view_right == 'SHAPE':
                c.row().prop_tabs_enum(swing_ultimate, "ui_shape_right")
            
            viewmeta.append((swing_ultimate.ui_view_right, swing_ultimate.ui_swing_right, swing_ultimate.ui_shape_right))
        
        rparent = layout.row(align=False)
        
        cindex = 0
        for view, swingtype, shapetype in viewmeta:
            c = rowcolumns[cindex].column()
            
            # Bone
            if view == 'BONE':
                r = c.row()
                if swingtype == 'BONE' or swingtype == 'BOTH':
                    c = r.column()
                    
                    c.label(text="Swing Bones")
                    SWINGULT_PT_SwingData_3DView_SwingBoneHeader.DrawLayout(self, context, c)
                    SWINGULT_PT_SwingData_3DView_SwingBone.DrawLayout(self, context, c)
                
                if swingtype == 'PARAM' or swingtype == 'BOTH':
                    c = r.column()
                    c.scale_x = 0.9
                    r = c.row()
                    r.label(text="Swing Params")
                    SWINGULT_PT_SwingData_3DView_SwingBone_Params.DrawLayout(self, context, c)
            
            # Shapes
            elif view == 'SHAPE':
                if shapetype == 'SPHERE':
                    c.label(text="Collision Spheres")
                    SWINGULT_PT_SwingData_3DView_Spheres.DrawLayout(self, context, c)
                
                if shapetype == 'OVAL':
                    c.label(text="Collision Ovals")
                    SWINGULT_PT_SwingData_3DView_Ovals.DrawLayout(self, context, c)
                
                if shapetype == 'ELLIPSOID':
                    c.label(text="Collision Ellipsoids")
                    SWINGULT_PT_SwingData_3DView_Ellipsoids.DrawLayout(self, context, c)
                
                if shapetype == 'CAPSULE':
                    c.label(text="Collision Capsules")
                    SWINGULT_PT_SwingData_3DView_Capsules.DrawLayout(self, context, c)
                
                if shapetype == 'PLANE':
                    c.label(text="Collision Planes")
                    SWINGULT_PT_SwingData_3DView_Planes.DrawLayout(self, context, c)
            
            # Connections
            elif view == 'CONNECTION':
                SWINGULT_PT_SwingData_3DView_Connections.DrawLayout(self, context, c)
            
            # Groups
            elif view == 'GROUP':
                SWINGULT_PT_SwingData_3DView_Groups.DrawLayout(self, context, c)
            
            cindex += 1
        
        self.bl_label = "Swing Data"
    
    def draw(self, context):
        self.DrawLayout(context, self.layout)
classlist.append(SWINGULT_PT_SwingData_Properties_Data)

"========================================================================================================="

# Register and add to the "object" menu (required to also use F3 search "Simple Object Operator" for quick access).
def register():
    for c in classlist:
        bpy.utils.register_class(c)
    
    bpy.types.Scene.swing_ultimate = bpy.props.PointerProperty(name="Swing Data", type=SwingSceneData)
    bpy.types.PoseBone.swing_ultimate_show_visuals = bpy.props.BoolProperty(name="Show Visuals", default=True)

def unregister():
    for c in classlist[::-1]:
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
