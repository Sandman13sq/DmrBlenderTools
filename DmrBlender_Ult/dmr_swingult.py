bl_info = {
    'name': 'Smush Swing Editor',
    'description': 'An interface to open and edit swing xml files for Smush modding.\nPRC to XML converter by BenHall-7 can be found here: https://github.com/BenHall-7/paracobNET/releases',
    'author': 'Dreamer13sq',
    'version': (0, 1),
    'blender': (3, 0, 0),
    'category': 'User Interface',
    'support': 'COMMUNITY',
    'doc_url': 'https://github.com/Dreamer13sq/DmrBlenderTools/wiki/Keyframe-Manip'
}

import bpy
import xml.etree.ElementTree as ET
import csv

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
SMASHUNIT = 0.25
STRUCTTYPENAMES = (
    'BONE', 'SPHERE', 'OVAL', 'ELLIPSOID', 'CAPSULE', 'PLANE', 'CONNECTION', 'GROUP'
)

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

# =============================================================================

def NewVisualObject(sourceobject, sourcearmature, bonename, end_bonename=""):
    bonelower = {b.name.lower(): b.name for b in sourcearmature.data.bones}
    
    obj = sourceobject.copy()
    obj.data = sourceobject.data.copy()
    bpy.context.scene.collection.objects.link(obj)
    
    obj.show_name = True
    obj.show_in_front = True
    obj.display_type = 'WIRE'
    
    for sk in obj.data.shape_keys.key_blocks:
        sk.value = 0.0
        sk.slider_min = -100
        sk.slider_max = 100
    
    obj.constraints["bone"].target = sourcearmature
    
    if bonename in bonelower.keys():
        obj.constraints["bone"].subtarget = bonelower[bonename.lower()]
    else:
        obj.constraints["bone"].subtarget = ""
    
    if "track" in obj.constraints.keys():
        obj.constraints["track"].target = sourcearmature
        if bonename in bonelower.keys():
            obj.constraints["track"].subtarget = bonelower[end_bonename.lower()]
        obj.constraints["track"].enabled = bonename != end_bonename and end_bonename != ""
    return obj

# =============================================================================

def XMLValue(element, typename, hashname):
    for el in element.findall(typename):
        if el.get("hash") == hashname:
            return el.text

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
                entry.isskirt = int(XMLValue(struct_def, 'sbyte', "isskirt"))
                entry.rotateorder = int(XMLValue(struct_def, 'int', "rotateorder"))
                entry.curverotatex = int(XMLValue(struct_def, 'sbyte', "curverotatex"))
                unknown_0x0f7316a113 = XMLValue(struct_def, 'sbyte', "0x0f7316a113")
                
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
            print("> %s has 0 Collisions!" % params)
        
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
    
    def CopyFromOther(self, other):
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
    
    def AddParams(self, copy_active=False):
        p = self.params.add()
        if copy_active:
            p.CopyFromOther(self.params[self.index_param])
        self.index_param = len(self.params)-1
        return p
    
    def RemoveParams(self, index=None):
        if index == None:
            index = self.index_param
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
    
    def GetParamsActive(self):
        return self.params[self.index_param]
    
    def CopyFromOther(self, other):
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
        
        print(other.Serialize())
        
        print("Swing Copy")
    
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
classlist.append(SwingData_Swing_Bone)

class SwingData_Swing_CollisionSphere(bpy.types.PropertyGroup): # ---------------------------------
    type = 'SPHERE'
    
    name : bpy.props.StringProperty()
    bonename : bpy.props.StringProperty()
    cx : bpy.props.FloatProperty()
    cy : bpy.props.FloatProperty()
    cz : bpy.props.FloatProperty()
    radius : bpy.props.FloatProperty()
    
    object : bpy.props.PointerProperty(type=bpy.types.Object)
    
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
classlist.append(SwingData_Swing_CollisionSphere)

class SwingData_Swing_CollisionOval(bpy.types.PropertyGroup): # ---------------------------------
    type = 'OVAL'
    
    name : bpy.props.StringProperty()
    bonename : bpy.props.StringProperty()
    cx : bpy.props.FloatProperty()
    cy : bpy.props.FloatProperty()
    cz : bpy.props.FloatProperty()
    radius : bpy.props.FloatProperty()
    
    object : bpy.props.PointerProperty(type=bpy.types.Object)
    
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
    
    object : bpy.props.PointerProperty(type=bpy.types.Object)
    
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
    
    object_start : bpy.props.PointerProperty(type=bpy.types.Object)
    object_end : bpy.props.PointerProperty(type=bpy.types.Object)
    
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
classlist.append(SwingData_Swing_CollisionCapsule)

class SwingData_Swing_CollisionPlane(bpy.types.PropertyGroup): # ---------------------------------
    type = 'PLANE'
    
    name : bpy.props.StringProperty()
    bonename : bpy.props.StringProperty()
    nx : bpy.props.FloatProperty()
    ny : bpy.props.FloatProperty()
    nz : bpy.props.FloatProperty()
    distance : bpy.props.FloatProperty()
    
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
classlist.append(SwingData_Swing_CollisionPlane)

class SwingData_Swing_Connection(bpy.types.PropertyGroup): # ---------------------------------
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
classlist.append(SwingData_Swing_Connection)

"================================================================================================"

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
    def FindStruct(self, type, name):
        structlist = self.GetStructList(type)
        return ([x for x in structlist if x.name == name]+[None])[0]
    
    # Returns size of struct list
    def GetStructListSize(self, type):
        return len(self.GetStructList(type))
    
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
        
        if copy_active and (type in ['BONE', 'SPHERE', 'OVAL', 'ELLIPSOID', 'CAPSULE', 'PLANE', 'CONNECTION']):
            entry.CopyFromOther( active )
            entry.name = active.name
            self.GetStructList(type).move(len(self.GetStructList(type))-1, self.GetStructActiveIndex(type)+1)
        self.Update()
        return entry
    
    # Removes struct of type at index
    def RemoveStruct(self, type, index=None):
        if index == None:
            index = self.GetStructActiveIndex(type)
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
    
    # Clears struct list of type
    def ClearStructList(self, type):
        self.GetStructList(type).clear()
        self.Update()
    
    # Clears all data from all lists
    def Clear(self):
        for type in STRUCTTYPENAMES:
            self.ClearStructList(type)
    
    # Creates visual objects for collision shapes (BETA)
    def CreateVisuals(self, armatureobject):
        lowernames = {b.name.lower(): b for b in armatureobject.pose.bones}
        
        # Sphere
        sourceobject = bpy.data.objects['swingprc_sphere']
        [bpy.data.objects.remove(x) for x in bpy.data.objects if (x != sourceobject and sourceobject.name in x.name)]
        
        for entry in self.GetStructList('SPHERE'):
            obj = NewVisualObject(sourceobject, armatureobject, entry.bonename)
            obj.name = obj.name + entry.name
            
            obj.data.shape_keys.key_blocks["cx"].value = entry.cx
            obj.data.shape_keys.key_blocks["cy"].value = entry.cy
            obj.data.shape_keys.key_blocks["cz"].value = entry.cz
            obj.data.shape_keys.key_blocks["radius"].value = entry.radius
        
        # Ellipsoid
        sourceobject = bpy.data.objects['swingprc_ellipsoid']
        [bpy.data.objects.remove(x) for x in bpy.data.objects if (x != sourceobject and sourceobject.name in x.name)]
        
        for entry in self.GetStructList('ELLIPSOID'):
            obj = NewVisualObject(sourceobject, armatureobject, entry.bonename)
            obj.name = obj.name + entry.name
            
            obj.data.shape_keys.key_blocks["cx"].value = entry.cx
            obj.data.shape_keys.key_blocks["cy"].value = entry.cy
            obj.data.shape_keys.key_blocks["cz"].value = entry.cz
            obj.data.shape_keys.key_blocks["sx"].value = entry.sx
            obj.data.shape_keys.key_blocks["sy"].value = entry.sy
            obj.data.shape_keys.key_blocks["sz"].value = entry.sz
        
        # Capsule
        sourceobject = bpy.data.objects['swingprc_capsule']
        [bpy.data.objects.remove(x) for x in bpy.data.objects if (x != sourceobject and sourceobject.name in x.name)]
        
        for entry in self.GetStructList('CAPSULE'):
            obj = NewVisualObject(sourceobject, armatureobject, entry.start_bonename, entry.end_bonename)
            obj.name = obj.name + entry.name
            
            obj.data.shape_keys.key_blocks["start_radius"].value = entry.start_radius
            obj.data.shape_keys.key_blocks["end_radius"].value = entry.end_radius
            obj.data.shape_keys.key_blocks["start_offset_x"].value = entry.start_offset_x
            obj.data.shape_keys.key_blocks["start_offset_y"].value = entry.start_offset_y
            obj.data.shape_keys.key_blocks["start_offset_z"].value = entry.start_offset_z
            obj.data.shape_keys.key_blocks["end_offset_x"].value = entry.end_offset_x
            obj.data.shape_keys.key_blocks["end_offset_y"].value = entry.end_offset_y
            obj.data.shape_keys.key_blocks["end_offset_z"].value = entry.end_offset_z
            
            if entry.start_bonename.lower() in lowernames:
                obj.data.shape_keys.key_blocks["length"].value = bonemap[entry.start_bonename].length
    
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
        
        if swingname not in [x.name for x in self.GetStructList('BONE')]:
            b = self.AddStruct('BONE')
            b.name = swingname
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
            print("> Connection Exists (%s -> %s)" % (connection.start_bonename, connection.end_bonename))
    
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
    
    # Checks all hashes against labels
    def Validate(self):
        prc_labels = bpy.context.scene.swing_ultimate.prc_labels
        labels = [l.name for l in prc_labels]
        
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
classlist.append(SwingData)

class SwingSceneData(bpy.types.PropertyGroup):
    data : bpy.props.CollectionProperty(type=SwingData)
    #index : bpy.props.IntProperty(name="Active Swing Data", default=0)
    index : bpy.props.EnumProperty(name="Active Swing Data", default=0, items=SwingSceneNames)
    count : bpy.props.IntProperty()
    
    prc_labels : bpy.props.CollectionProperty(type=SwingData_Label)
    
    ui_view_left : bpy.props.EnumProperty(items = (
        ('BONE', "Swing Bone", ""),
        ('SHAPE', "Collision Shape", ""),
        ('CONNECTION', "Connection", ""),
        ('GROUP', "Group", ""),
    ))
    
    ui_swing_left : bpy.props.EnumProperty(items = (
        ('BONE', "Swing Bone", ""),
        ('PARAM', "Parameters", ""),
        ('BOTH', "BOTH", ""),
    ))
    
    ui_shape_left : bpy.props.EnumProperty(items = (
        ('SPHERE', "Sphere", ""),
        ('OVAL', "Oval", ""),
        ('ELLIPSOID', "Ellipsoid", ""),
        ('CAPSULE', "Capsule", ""),
        ('PLANE', "Plane", ""),
    ))
    
    ui_view_right : bpy.props.EnumProperty(items = (
        ('BONE', "Swing Bone", ""),
        ('SHAPE', "Collision Shape", ""),
        ('CONNECTION', "Connection", ""),
        ('GROUP', "Group", ""),
    ))
    
    ui_swing_right : bpy.props.EnumProperty(items = (
        ('BONE', "Swing Bone", ""),
        ('PARAM', "Parameters", ""),
        ('BOTH', "BOTH", ""),
    ))
    
    ui_shape_right : bpy.props.EnumProperty(items = (
        ('SPHERE', "Sphere", ""),
        ('OVAL', "Oval", ""),
        ('ELLIPSOID', "Ellipsoid", ""),
        ('CAPSULE', "Capsule", ""),
        ('PLANE', "Plane", ""),
    ))
    
    def FindPRCIndex(self, name):
        return [x.index for x in self.data if x.name == name][0]
    
    def FindData(self, name):
        for prc in self.data:
            if prc.name == name:
                return prc
        return None
        
    def GetActiveIndex(self):
        return int(self.index)
    
    def GetActiveData(self):
        return self.data[int(self.index)] if self.count > 0 else None
    
    def Add(self, name="New Swing Data"):
        prc = self.data.add()
        prc.name = name + " %d" % self.count
        self.UpdateIndex()
        self.index = str(prc.index)
        return prc
    
    def Remove(self, index):
        if self.count > 0:
            self.data.remove(index)
            self.UpdateIndex()
    
    def UpdateIndex(self, update_enum=True):
        self.count = len(self.data)
        if self.count > 0:
            for i, prc in enumerate(self.data):
                prc.index = i
            self.index = str(max(0, min(len(self.data), int(self.index if self.index else self.count-1))))
    
    def UpdateLabels(self, path):
        with open(path, 'r') as csvfile:
            csvreader = csv.reader(csvfile)
            fields = next(csvreader)
            
            labels = [r for r in csvreader]
            labels.sort(key=lambda x: x[1])
            
            self.prc_labels.clear()
            for r in labels:
                l = self.prc_labels.add()
                l.hex = r[0]
                l.name = r[1]
        print("> Labels updated")
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
        return {'FINISHED'}
classlist.append(SWINGULT_OP_UpdateLabels)

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
class SWINGULT_OP_SwingData_Visualize(bpy.types.Operator):
    bl_idname = "swingult.visualize"
    bl_label = "Visualize Swing Data (BETA)"
    bl_description = "Creates shapes for collisions from active swing data"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(self, context):
        return context.object and context.object.type == 'ARMATURE'
    
    def execute(self, context):
        out = context.scene.swing_ultimate.GetActiveData().CreateVisuals(context.object)
        return {'FINISHED'}
#classlist.append(SWINGULT_OP_SwingData_Visualize)

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
        conflicts = context.scene.swing_ultimate.GetActiveData().Validate()
        
        if conflicts == None:
            self.report({'INFO'}, "No labels loaded to reference. Use \"Update Labels\" to load from ParamLabels.csv on disk")
        
        elif len(conflicts) > 0:
            self.report({'INFO'}, "%d Conflicts. First is %s" % (len(conflicts), conflicts[0]))
        else:
            self.report({'INFO'}, "No conflicts found")
        return {'FINISHED'}
classlist.append(SWINGULT_OP_SwingData_Validate)

# =========================================================================================================

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

# =========================================================================================================

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

# =========================================================================================================

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

"================================================================================================"
"LAYOUT"
"================================================================================================"

class SWINGULT_UL_SwingEdit(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        r = layout.row(align=1)
        r.label(text='[%d] %s' % (index, item.name))
classlist.append(SWINGULT_UL_SwingEdit)

# --------------------------------------------------------------------------
class SWINGULT_UL_SwingData_SwingBone(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        r = layout.row(align=1)
        r.label(text='[%d]: %s' % (index, item.name))
        rr = r.row()
        rr.scale_x = 0.8
        rr.label(text="(Size %d)" % len(item.params))
classlist.append(SWINGULT_UL_SwingData_SwingBone)

# --------------------------------------------------------------------------
class SWINGULT_UL_SwingData_SwingBone_Params(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        r = layout.row(align=1)
        r.label(text='Bone {0}: ({1} Collisions)'.format(index, len(item.collisions)), icon='PROPERTIES')
classlist.append(SWINGULT_UL_SwingData_SwingBone_Params)

# --------------------------------------------------------------------------
class SWINGULT_UL_SwingData_SwingBone_Params_Collisions(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        r = layout.row(align=1)
        r.prop(item, 'hash40', text='[%d]' % index, icon='PHYSICS')
classlist.append(SWINGULT_UL_SwingData_SwingBone_Params_Collisions)

# --------------------------------------------------------------------------
class SWINGULT_UL_SwingData_CollisionStruct(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        r = layout.row(align=1)
        r.label(text='[%d] %s' % (index, item.name))
classlist.append(SWINGULT_UL_SwingData_CollisionStruct)

# --------------------------------------------------------------------------
class SWINGULT_UL_SwingData_Connection(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        r = layout.row(align=1)
        r.label(text='[%d] (%s) ... (%s)' % (index, item.start_bonename, item.end_bonename))
classlist.append(SWINGULT_UL_SwingData_Connection)

# --------------------------------------------------------------------------
class SWINGULT_UL_SwingData_Group(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        r = layout.row(align=1)
        r.label(text='[%d] %s (%s)' % (index, item.name, item.size))
classlist.append(SWINGULT_UL_SwingData_Group)

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
            c = layout.column(align=1)
            r = c.row(align=1)
            r.prop(swing_ultimate, 'index', text='', icon='PRESET', icon_only=1)
            r.prop(swing_ultimate.GetActiveData(), 'name', text="")
            r = r.row(align=1)
            r.operator('swingult.new', icon='ADD', text="")
            r.operator('swingult.remove', icon='REMOVE', text="").index = swing_ultimate.GetActiveIndex()
            
            r = c.row()
            r.operator('swingult.update_labels', text="Update Labels")
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
            r.operator('swingult.xml_save', icon='EXPORT', text="Serialize")
            #r.operator('swingult.visualize', icon='MESH_UVSPHERE', text="Visualize")
            
            r = col.row()
            #r.operator('swingult.clean', icon='FILE_REFRESH', text="Clean")
            r.operator('swingult.validate', icon='LINENUMBERS_ON', text="Validate")
classlist.append(SWINGULT_PT_SwingData_3DView)

"========================================================================================================="

def DrawStructUIList(self, layout, prc, type, typename, list_pt, varname, indexname):
    r = layout.row(align=1)
    r.template_list(list_pt, "", prc, varname, prc, indexname, rows=5)
    
    c = r.column(align=1)
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
    op.target_prc = prc.name

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
        
        self.bl_label = "Swing Bones (%d)" % prc.GetStructListSize(type)
        
        if not entry:
            col.operator('swingult.struct_add', text="New Swing Bone").type = type
        else:
            r = col.row(align=1)
            r.template_list(
                "SWINGULT_UL_SwingData_SwingBone", "", prc, "swingbones", prc, "index_bone", rows=5)
            
            c = r.column(align=1)
            
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
            b = col.box().column(align=1)
            b.prop(entry, 'name')
            b.prop(entry, 'start_bonename', icon='BONE_DATA')
            b.prop(entry, 'end_bonename', icon='BONE_DATA')
            
            c = b.column(align=1)
            c.prop(entry, 'isskirt')
            c.prop(entry, 'rotateorder')
            c.prop(entry, 'curverotatex')
            c.prop(entry, 'unknown_0x0f7316a113')
    
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
        col = layout.box()
        prc = context.scene.swing_ultimate.GetActiveData()
        swingbone = prc.GetStructActive('BONE')
        
        if swingbone:
            r = col.row(align=1)
            r.operator('swingult.swing_bone_params_add', text="New Params", icon='ADD')
            r.operator('swingult.swing_bone_params_remove', text="Remove Active", icon='REMOVE')
            
            if swingbone.params:
                self.bl_label = SUBPANELLABELSPACE + "Params (%d)" % len(swingbone.params)
                
                entry = swingbone.params[swingbone.index_param]
                
                r = col.row(align=1)
                r.template_list(
                    "SWINGULT_UL_SwingData_SwingBone_Params", "", swingbone, "params", swingbone, "index_param", rows=3)
                
                c = r.column(align=1)
                c.operator('swingult.swing_bone_params_move', text="", icon='TRIA_UP').direction = 'UP'
                c.operator('swingult.swing_bone_params_move', text="", icon='TRIA_DOWN').direction = 'DOWN'
                
                b = col.column(align=1)
                
                c = b.column(align=1)
                c.prop(entry, 'airresistance')
                c.prop(entry, 'waterresistance')
                c.prop(entry, 'minanglez')
                c.prop(entry, 'maxanglez')
                c.prop(entry, 'minangley')
                c.prop(entry, 'maxangley')
                c.prop(entry, 'collisionsizetip')
                c.prop(entry, 'collisionsizeroot')
                c.prop(entry, 'frictionrate')
                c.prop(entry, 'goalstrength')
                c.prop(entry, 'unknown_0x0cc10e5d3a')
                c.prop(entry, 'localgravity', expand=True)
                c.prop(entry, 'fallspeedscale')
                c.prop(entry, 'groundhit')
                c.prop(entry, 'windaffect')
                
                b2 = b.box().column()
                r = b2.row(align=1)
                r.operator('swingult.swing_bone_params_collision_add', text="New Collision", icon='ADD')
                r.operator('swingult.swing_bone_params_collision_remove', text="Remove Active", icon='REMOVE')
                
                r = b2.row(align=1)
                r.template_list(
                    "SWINGULT_UL_SwingData_SwingBone_Params_Collisions", "", entry, "collisions", entry, "index_collision", rows=3)
                
                c = r.column(align=1)
                c.operator('swingult.swing_bone_params_collision_move', text="", icon='TRIA_UP').direction = 'UP'
                c.operator('swingult.swing_bone_params_collision_move', text="", icon='TRIA_DOWN').direction = 'DOWN'
    
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
        
        #self.bl_label = SUBPANELLABELSPACE + "Spheres (%d)" % prc.GetStructListSize(type)
        
        if not entry:
            col.operator('swingult.struct_add', text="New Sphere").type = type
        else:
            DrawStructUIList(self, col, prc, type, "Sphere", 'SWINGULT_UL_SwingData_CollisionStruct', "spheres", "index_sphere")
            
            b = col.box().column(align=1)
            b.prop(entry, 'name')
            b.prop(entry, 'bonename', icon='BONE_DATA')
            
            c = b.column(align=1)
            c.prop(entry, 'cx')
            c.prop(entry, 'cy')
            c.prop(entry, 'cz')
            c.prop(entry, 'radius')
    
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
        
        self.bl_label = SUBPANELLABELSPACE + "Ovals (%d)" % prc.GetStructListSize(type)
        
        if not entry:
            col.operator('swingult.struct_add', text="New Oval").type = type
        else:
            DrawStructUIList(self, col, prc, type, "Oval", 'SWINGULT_UL_SwingData_CollisionStruct', "ovals", "index_oval")
            
            b = col.box().column(align=1)
            b.prop(entry, 'name')
            b.prop(entry, 'bonename', icon='BONE_DATA')
            
            c = b.column()
            c.prop(entry, 'cx')
            c.prop(entry, 'cy')
            c.prop(entry, 'cz')
            c.prop(entry, 'radius')
    
    def draw(self, context):
        self.DrawLayout(context, self.layout)
classlist.append(SWINGULT_PT_SwingData_3DView_Ovals)

# ---------------------------------------------------------------------------------------
class SWINGULT_PT_SwingData_3DView_Ellipsoids(StructPanelSuper):
    bl_label = SUBPANELLABELSPACE + "Ellipsoids"
    bl_parent_id = 'SWINGULT_PT_SwingData_3DView_CollisionShapeHeader'
    
    def DrawLayout(self, context, layout):
        type = 'ELLIPSOID'
        col = layout
        prc = context.scene.swing_ultimate.GetActiveData()
        entry = prc.GetStructActive('ELLIPSOID')
        
        self.bl_label = SUBPANELLABELSPACE + "Ellipsoids (%d)" % prc.GetStructListSize(type)
        
        if not entry:
            col.operator('swingult.struct_add', text="New Ellipsoid").type = type
        else:
            DrawStructUIList(self, col, prc, type, "Ellipsoid", 'SWINGULT_UL_SwingData_CollisionStruct', "ellipsoids", "index_ellipsoid")
            
            b = col.box().column(align=1)
            b.prop(entry, 'name')
            b.prop(entry, 'bonename', icon='BONE_DATA')
            
            c = b.column(align=1)
            c.prop(entry, 'cx')
            c.prop(entry, 'cy')
            c.prop(entry, 'cz')
            c.prop(entry, 'rx')
            c.prop(entry, 'ry')
            c.prop(entry, 'rz')
            c.prop(entry, 'sx')
            c.prop(entry, 'sy')
            c.prop(entry, 'sz')
    
    def draw(self, context):
        self.DrawLayout(context, self.layout)
classlist.append(SWINGULT_PT_SwingData_3DView_Ellipsoids)

# ---------------------------------------------------------------------------------------
class SWINGULT_PT_SwingData_3DView_Capsules(StructPanelSuper):
    bl_label = SUBPANELLABELSPACE + "Capsules"
    bl_parent_id = 'SWINGULT_PT_SwingData_3DView_CollisionShapeHeader'
    
    def DrawLayout(self, context, layout):
        type = 'CAPSULE'
        col = layout
        prc = context.scene.swing_ultimate.GetActiveData()
        entry = prc.GetStructActive('CAPSULE')
        
        self.bl_label = SUBPANELLABELSPACE + "Capsules (%d)" % prc.GetStructListSize(type)
        
        if not entry:
            col.operator('swingult.struct_add', text="New Capsule").type = type
        else:
            DrawStructUIList(self, col, prc, type, "Capsule", 'SWINGULT_UL_SwingData_CollisionStruct', "capsules", "index_capsule")
            
            b = col.box().column(align=1)
            b.prop(entry, 'name')
            b.prop(entry, 'start_bonename', icon='BONE_DATA')
            b.prop(entry, 'end_bonename', icon='BONE_DATA')
            
            c = b.column(align=1)
            c.prop(entry, 'start_offset_x')
            c.prop(entry, 'start_offset_y')
            c.prop(entry, 'start_offset_z')
            c.prop(entry, 'end_offset_x')
            c.prop(entry, 'end_offset_y')
            c.prop(entry, 'end_offset_z')
            c.prop(entry, 'start_radius')
            c.prop(entry, 'end_radius')
    
    def draw(self, context):
        self.DrawLayout(context, self.layout)
classlist.append(SWINGULT_PT_SwingData_3DView_Capsules)

# ---------------------------------------------------------------------------------------
class SWINGULT_PT_SwingData_3DView_Planes(StructPanelSuper):
    bl_label = SUBPANELLABELSPACE + "Planes"
    bl_parent_id = 'SWINGULT_PT_SwingData_3DView_CollisionShapeHeader'
    
    def DrawLayout(self, context, layout):
        type = 'PLANE'
        col = layout
        prc = context.scene.swing_ultimate.GetActiveData()
        entry = prc.GetStructActive('PLANE')
        
        self.bl_label = SUBPANELLABELSPACE + "Planes (%d)" % prc.GetStructListSize(type)
        
        if not entry:
            col.operator('swingult.struct_add', text="New Plane").type = type
        else:
            DrawStructUIList(self, col, prc, type, "Plane", 'SWINGULT_UL_SwingData_CollisionStruct', "planes", "index_plane")
            
            b = col.box().column(align=1)
            b.prop(entry, 'name')
            b.prop(entry, 'bonename', icon='BONE_DATA')
            
            c = b.column(align=1)
            c.prop(entry, 'nx')
            c.prop(entry, 'ny')
            c.prop(entry, 'nz')
            c.prop(entry, 'distance')
    
    def draw(self, context):
        self.DrawLayout(context, self.layout)
classlist.append(SWINGULT_PT_SwingData_3DView_Planes)

# ---------------------------------------------------------------------------------------
class SWINGULT_PT_SwingData_3DView_Connections(StructPanelSuper):
    bl_label = "Connections"
    
    def DrawLayout(self, context, layout):
        type = 'CONNECTION'
        col = layout
        prc = context.scene.swing_ultimate.GetActiveData()
        entry = prc.GetStructActive('CONNECTION')
        
        self.bl_label = "Connections (%d)" % prc.GetStructListSize(type)
        
        if not entry:
            col.operator('swingult.struct_add', text="New Connection").type = type
        else:
            r = col.row(align=1)
            r.operator('swingult.struct_add', text="New Connection", icon='ADD').type = type
            r.operator('swingult.struct_remove', text="Remove Active", icon='REMOVE').type = type
            
            r = col.row(align=1)
            r.operator('swingult.connections_transfer', text="Transfer Connection").target_prc = prc.name
            r.operator('swingult.connections_transfer_pattern', text="... By Pattern").target_prc = prc.name
            
            r = col.row(align=1)
            r.template_list(
                "SWINGULT_UL_SwingData_Connection", "", prc, "connections", prc, "index_connection", rows=5)
            
            c = r.column(align=1)
            op = c.operator('swingult.struct_move', text="", icon='TRIA_UP')
            op.type = type
            op.direction = 'UP'
            op = c.operator('swingult.struct_move', text="", icon='TRIA_DOWN')
            op.type = type
            op.direction = 'DOWN'
            
            b = col.box().column(align=1)
            b.prop(entry, 'start_bonename', icon='BONE_DATA')
            b.prop(entry, 'end_bonename', icon='BONE_DATA')
            
            c = b.column(align=1)
            c.prop(entry, 'radius')
            c.prop(entry, 'length')
    
    def draw(self, context):
        self.DrawLayout(context, self.layout)
classlist.append(SWINGULT_PT_SwingData_3DView_Connections)

# ---------------------------------------------------------------------------------------
class SWINGULT_PT_SwingData_3DView_Groups(StructPanelSuper):
    bl_label = "Groups"
    
    def DrawLayout(self, context, layout):
        type = 'GROUP'
        col = self.layout
        prc = context.scene.swing_ultimate.GetActiveData()
        entry = prc.GetStructActive(type)
        
        self.bl_label = "Groups (%d)" % prc.GetStructListSize(type)
        
        if not entry:
            col.operator('swingult.struct_add', text="New Group").type = type
        else:
            r = col.row(align=1)
            r.operator('swingult.struct_add', text="New Group", icon='ADD').type = type
            r.operator('swingult.struct_remove', text="Remove Active", icon='REMOVE').type = type
            
            r = col.row(align=1)
            r.template_list(
                "SWINGULT_UL_SwingData_Group", "", prc, "groups", prc, "index_group", rows=5)
            
            c = r.column(align=1)
            op = c.operator('swingult.struct_move', text="", icon='TRIA_UP')
            op.type = type
            op.direction = 'UP'
            op = c.operator('swingult.struct_move', text="", icon='TRIA_DOWN')
            op.type = type
            op.direction = 'DOWN'
            
            b = col.box().column(align=1)
            b.prop(entry, 'name')
            
            activegroup = prc.groups[prc.index_group]
            
            col.template_list(
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
    
    def draw(self, context):
        layout = self.layout
        
        swing_ultimate = context.scene.swing_ultimate
        
        row = layout.row()
        
        c = row.box().column()
        c.row().prop_tabs_enum(swing_ultimate, "ui_view_left")
        if swing_ultimate.ui_view_left == 'BONE':
            c.row().prop_tabs_enum(swing_ultimate, "ui_swing_left")
        elif swing_ultimate.ui_view_left == 'SHAPE':
            c.row().prop_tabs_enum(swing_ultimate, "ui_shape_left")
        
        c = row.box().column()
        c.row().prop_tabs_enum(swing_ultimate, "ui_view_right")
        if swing_ultimate.ui_view_right == 'BONE':
            c.row().prop_tabs_enum(swing_ultimate, "ui_swing_right")
        elif swing_ultimate.ui_view_right == 'SHAPE':
            c.row().prop_tabs_enum(swing_ultimate, "ui_shape_right")
        
        rparent = layout.row(align=0)
        
        for view, swingtype, shapetype in (
            (swing_ultimate.ui_view_left, swing_ultimate.ui_swing_left, swing_ultimate.ui_shape_left),
            (swing_ultimate.ui_view_right, swing_ultimate.ui_swing_right, swing_ultimate.ui_shape_right)
            ):
            c = rparent.box()
            
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
                    c.label(text="Swing Params")
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
        
        self.bl_label = "Swing Data"

classlist.append(SWINGULT_PT_SwingData_Properties_Data)

"========================================================================================================="

# Register and add to the "object" menu (required to also use F3 search "Simple Object Operator" for quick access).
def register():
    for c in classlist:
        bpy.utils.register_class(c)
    
    bpy.types.Scene.swing_ultimate = bpy.props.PointerProperty(name="Swing Data", type=SwingSceneData)

def unregister():
    for c in classlist[::-1]:
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()

