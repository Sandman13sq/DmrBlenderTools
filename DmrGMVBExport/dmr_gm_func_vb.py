import bpy
import struct
import zlib
import sys
import mathutils
import time

from bpy_extras.io_utils import ExportHelper
from struct import pack as Pack

PackString = lambda x: b'%c%s' % (len(x), str.encode(x));
PackVector = lambda f, v: struct.pack(f*len(v), *(v[:]));
PackMatrix = lambda f, m: b''.join( [struct.pack(f*4, *x) for x in m.copy().transposed()] );
QuatValid = lambda q: q if q.magnitude != 0.0 else [1.0, 0.0, 0.0, 0.00001];

# ================================================================================

VBXVERSION = 1;
FCODE = 'f';

MODLIST = [
    'MIRROR', 
    'SUBSURF', 
    'NORMAL_EDIT', 
    'SOLIDIFY',
    'WELD',
    'EDGE_SPLIT',
    'TRIANGULATE',
    'DATA_TRANSFER',
    'SHRINKWRAP',
    'MASK',
    'ARRAY'
];

# This is more for loading files outside of GMS
# If you don't mind longer load times for converting numbers to floats,
# get some more accuracy with doubles or save some space with binary16s
FloatChoiceItems = (
    ('f', 'Float (32bit) *GMS*', 'Write floating point data using floats (32 bits)\n***Use for Game Maker Studio***'),
    ('d', 'Double (64bit)', 'Write floating point data using doubles (64 bits)'),
    ('e', 'Binary16 (16bit)', 'Write floating point data using binary16 (16 bits)'),
);

VBF_000 = '000';
VBF_POS = 'POS';
VBF_TEX = 'TEX';
VBF_NOR = 'NOR';
VBF_TAN = 'TAN';
VBF_BTN = 'BTN';
VBF_COL = 'COL';
VBF_CO2 = 'CO2';
VBF_WEI = 'WEI';
VBF_BON = 'BON';
VBF_BOI = 'BOI';

VBFSize = {
    VBF_000: 0,
    VBF_POS: 3, 
    VBF_TEX: 2, 
    VBF_NOR: 3, 
    VBF_TAN: 3,
    VBF_BTN: 3,
    VBF_COL: 4, 
    VBF_CO2: 1, 
    VBF_WEI: 4, 
    VBF_BON: 4,
    VBF_BOI: 1,
    };

VBFItems = (
    (VBF_000, '---', 'No Data'),
    (VBF_POS, 'Position', '3 Floats'),
    (VBF_TEX, 'UVs', '2 Floats'),
    (VBF_NOR, 'Normal', '3 Floats'),
    (VBF_TAN, 'Tangents', '3 Floats'),
    (VBF_BTN, 'Bitangents', '3 Floats'),
    (VBF_COL, 'Color (RGBA)', '4 Floats'),
    (VBF_CO2, 'Color Bytes (RGBA)', '4 Bytes = Size of 1 Float in format 0xRRGGBBAA'),
    (VBF_BON, 'Bone Indices', '4 Floats (Use with Weights)'),
    (VBF_BOI, 'Bone Index Bytes', '4 Bytes = Size of 1 Float in format 0xWWZZYYZZ'),
    (VBF_WEI, 'Weights', '4 Floats'),
);

VBFType = {x[1]: x[0] for x in enumerate([
    VBF_000,
    VBF_POS,
    VBF_TEX,
    VBF_NOR,
    VBF_COL,
    VBF_CO2,
    VBF_WEI,
    VBF_BON,
    VBF_TAN,
    VBF_BTN,
    ])};

LayerChoiceItems = (
    ('render', 'Render Layer', 'Use the layer that will be rendered (camera icon is on)', 'RESTRICT_RENDER_OFF', 0),
    ('active', 'Active Layer', 'Use the layer that is active (highlighted)', 'RESTRICT_SELECT_OFF', 1),
);

LYR_GLOBAL = '<__global__>';
LYR_RENDER = '<__render__>';
LYR_SELECT = '<__select__>';

def GetUVLayers(self, context):
    items = [];
    items.append( (LYR_GLOBAL, '<UV Source>', 'Use setting "UV Source" below') );
    items.append( (LYR_RENDER, '<Render Layer>', 'Use Render Layer of object') );
    items.append( (LYR_SELECT, '<Selected Layer>', 'Use Selected Layer of object') );
    
    objects = [x for x in context.selected_objects if (x and x.type == 'MESH')];
    lyrnames = [];
    
    for obj in objects:
        for lyr in obj.data.uv_layers:
            lyrnames.append(lyr.name);
    
    lyrnames.sort(key=lambda x: lyrnames.count(x));
    lyrnames = list(set(lyrnames));
    
    for name in lyrnames:
        items.append( (name, name, 'Use "%s" layer for uv data' % name) );
    
    return items;

def GetVCLayers(self, context):
    items = [];
    items.append( (LYR_GLOBAL, '<Color Source>', 'Use setting "Color Source" below') );
    items.append( (LYR_RENDER, '<Render Layer>', 'Use Render Layer of object') );
    items.append( (LYR_SELECT, '<Selected Layer>', 'Use Selected Layer of object') );
    
    objects = [x for x in context.selected_objects if (x and x.type == 'MESH')];
    lyrnames = [];
    
    for obj in objects:
        for lyr in obj.data.vertex_colors:
            lyrnames.append(lyr.name);
    
    lyrnames.sort(key=lambda x: lyrnames.count(x));
    lyrnames = list(set(lyrnames));
    
    for name in lyrnames:
        items.append( (name, name, 'Use "%s" layer for color data' % name) );
    
    return items;

MTY_VIEW = 'V';
MTY_RENDER = 'R';
MTY_OR = 'OR';
MTY_AND = 'AND';
MTY_ALL = 'ALL';

ModChoiceItems = (
    (MTY_VIEW, 'Viewport Only', 'Only export modifiers visible in viewports'), 
    (MTY_RENDER, 'Render Only', 'Only export modifiers visible in renders'), 
    (MTY_OR, 'Viewport or Render', 'Export modifiers if they are visible in viewport or renders'), 
    (MTY_AND, 'Viewport and Render', 'Export modifiers only if they are visible in viewport and renders'), 
    (MTY_ALL, 'All', 'Export all supported modifiers')
);

UpAxisItems = (
    ('+x', '+X Up', 'Export model(s) with +X Up axis'),
    ('+y', '+Y Up', 'Export model(s) with +Y Up axis'),
    ('+z', '+Z Up (Blender)', 'Export model(s) with +Z Up axis'),
    ('-x', '-X Up', 'Export model(s) with -X Up axis'),
    ('-y', '-Y Up (GM)', 'Export model(s) with -Y Up axis'),
    ('-z', '-Z Up', 'Export model(s) with -Z Up axis'),
);

ForwardAxisItems = (
    ('+x', '+X Forward', 'Export model(s) with +X Forward axis'),
    ('+y', '+Y Forward (Blender)', 'Export model(s) with +Y Forward axis'),
    ('+z', '+Z Forward (GM)', 'Export model(s) with +Z Forward axis'),
    ('-x', '-X Forward', 'Export model(s) with -X Forward axis'),
    ('-y', '-Y Forward', 'Export model(s) with -Y Forward axis'),
    ('-z', '-Z Forward', 'Export model(s) with -Z Forward axis'),
);

def GetVBData(sourceobj, format = [], settings = {}, uvtarget = [LYR_GLOBAL], vctarget = [LYR_GLOBAL]):
    context = bpy.context;
    
    armature = None;
    formatneedsbones = VBF_BON in format or VBF_WEI in format;
    formatneedsbones = formatneedsbones and not settings.get('applyarmature', 0);
    
    # Set source as active
    bpy.ops.object.select_all(action='DESELECT');
    bpy.context.view_layer.objects.active = sourceobj;
    sourceobj.select_set(True);
    # Duplicate source
    bpy.ops.object.duplicate(linked = 0, mode = 'TRANSLATION');
    obj = bpy.context.view_layer.objects.active;
    sourceobj.select_set(False);
    obj.select_set(True);
    bpy.context.view_layer.objects.active = obj;
    obj.name = sourceobj.name + '__temp';
    
    # Find armature
    for m in obj.modifiers:
        if m.type == 'ARMATURE':
            if m.object:
                armature = m.object;
                bpy.ops.object.modifier_move_to_index(modifier=m.name, index=len(obj.modifiers)-1)
    
    # Apply shape keys
    if obj.data.shape_keys:
        print("> Removing shape keys...");
        bpy.ops.object.shape_key_add(from_mix = True);
        shape_keys = obj.data.shape_keys.key_blocks;
        count = len(shape_keys);
        for i in range(0, count):
            obj.active_shape_key_index = 0;
            bpy.ops.object.shape_key_remove(all=False);
    
    # Apply modifiers
    maxsubdivisions = settings.get('maxsubdivisions', -1);
    modreq = settings.get('modifierpick', MTY_OR);
    if obj.modifiers != None:
        modifiers = obj.modifiers;
        for i, m in enumerate(modifiers):
            # Modifier requirements
            if modreq == MTY_VIEW:
                if not m.show_viewport:
                    bpy.ops.object.modifier_remove(modifier = m.name);
                    continue;
            elif modreq == MTY_RENDER:
                if not m.show_render:
                    bpy.ops.object.modifier_remove(modifier = m.name);
                    continue;
            elif modreq == MTY_OR:
                if not (m.show_viewport or m.show_render):
                    bpy.ops.object.modifier_remove(modifier = m.name);
                    continue;
            elif modreq == MTY_AND:
                if not (m.show_viewport and m.show_render):
                    bpy.ops.object.modifier_remove(modifier = m.name);
                    continue;
            
            # Subdivision maximum
            if m.type == 'SUBSURF':
                if maxsubdivisions >= 0:
                    m.levels = min(m.levels, maxsubdivisions);
            
            # Apply enabled modifiers
            if (m.name[0] != '!') and (m.type in MODLIST) \
            or (m.type == 'ARMATURE' and settings.get('applyarmature', 0)):
                try:
                    # Data Transfer can crash if source object is not set
                    bpy.ops.object.modifier_apply(modifier = m.name);
                except:
                    print('> Modifier "%s" unable to apply' % m.name);
                    bpy.ops.object.modifier_remove(modifier = m.name);
            # Ignore Modifier
            elif m.type != 'ARMATURE':
                bpy.ops.object.modifier_remove(modifier = m.name);
        
        minquads = modifiers.new('MinQuads', 'TRIANGULATE');
        minquads.min_vertices = 5;
        bpy.ops.object.modifier_apply(modifier = 'MinQuads');
    
    if not formatneedsbones:
        armature = None;
    
    # Apply Transforms
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True);
    bpy.ops.object.visual_transform_apply();
    
    for c in obj.constraints:
        obj.constraints.remove(c);
    
    yvec = mathutils.Vector((1.0, 1.0, 1.0));
    
    if settings.get('yflip', 0):
        yvec[1] *= -1.0;
    #bpy.ops.object.convert(target='MESH');
    
    obj.matrix_world = settings.get('matrix', mathutils.Matrix());
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True);
    
    # Calc data
    mesh = obj.data;
    mesh.calc_loop_triangles();
    usetris = (len(mesh.loop_triangles) > 0) and (not settings.get('edgesonly', False));
    if usetris:
        mesh.calc_normals_split();
        if mesh.uv_layers:
            mesh.calc_tangents();
    mesh.update();
    
    # Setup Object Data
    vertices = mesh.vertices;
    loops = mesh.loops;
    
    # Find active group for layer if exists, else create new and use it
    if not obj.vertex_groups:
        obj.vertex_groups.new();
    vgroups = obj.vertex_groups;
    
    if armature and vgroups:
        group_select_mode = 'BONE_DEFORM';
        try:
            bpy.ops.object.vertex_group_clean(group_select_mode=group_select_mode, limit=0, keep_single=True);
            bpy.ops.object.vertex_group_limit_total(group_select_mode=group_select_mode, limit=4);
        except:
            group_select_mode = 'ALL';
            bpy.ops.object.vertex_group_clean(group_select_mode=group_select_mode, limit=0, keep_single=True);
            bpy.ops.object.vertex_group_limit_total(group_select_mode=group_select_mode, limit=4);
    
    def FindLayers(layerlist, targetlist, targetpick):
        if not layerlist:
            targetlist = layerlist.new().name;
        if not type(targetlist) == list:
            targetlist = [targetlist];
        targetlist += [targetlist[-1]] * (len(format) - len(targetlist));
        
        attriblayers = [0] * len(targetlist);
        for i, t in enumerate(targetlist):
            if t in [y.name for y in layerlist]:
                attriblayers[i] = layerlist[t].data;
            elif targetpick or t == LYR_RENDER:
                attriblayers[i] = [x for x in layerlist if x.active_render][0].data;
        
        return (layerlist, attriblayers);
    
    uvlayers, uvattriblayers = FindLayers(mesh.uv_layers, uvtarget, settings.get('uvlayerpick', 1));
    vclayers, vcattriblayers = FindLayers(mesh.vertex_colors, vctarget, settings.get('colorlayerpick', 1));
    
    fullalpha = settings.get('fullalpha', 0);
    
    # Set up armature
    if armature:
        bones = armature.data.bones;
        
        if settings.get('deformonly', False):
            bones = [b for b in armature.data.bones if b.use_deform];
        
        bonenames = [b.name for b in bones]
        grouptobone = {vg.index: bonenames.index(vg.name) for vg in vgroups if vg.name in bonenames};
        validvgroups = [vg.index for vg in vgroups if vg.name in bonenames];
    else:
        grouptobone = {vg.index: vg.index for vg in vgroups};
        validvgroups = grouptobone.values();
    
    # Compose data
    out = { (m.name if m else '__null'): [b''] for m in obj.data.materials}; # {materialname: vertexdata[]};
    if not out:
        out = {'0': [b'']};
    materialnames = [m.name for m in obj.data.materials] if obj.data.materials else ['0'];
    materialcount = len(materialnames);
    
    stride = 0;
    for k in format:
        stride += VBFSize[k];
    
    vertexcounts = {k: 0 for k in out.keys()};
    chunksize = 1024;
    
    vgesortfunc = lambda x: x.weight;
    range2 = range(0, 2);
    range3 = range(0, 3);
    
    # Triangles
    if usetris:
        def fPOS(attribindex): materialgroup[-1] += PackVector(FCODE, v.co*yvec);
        def fNOR(attribindex): materialgroup[-1] += PackVector(FCODE, p_normals[i]*yvec);
        def fTAN(attribindex): materialgroup[-1] += PackVector(loops[l].tangent*yvec);
        def fBTN(attribindex): materialgroup[-1] += PackVector(loops[l].bitangent*yvec);
        def fTEX(attribindex): materialgroup[-1] += PackVector(FCODE, (uvattriblayers[attribindex][l].uv[0], 1-uvattriblayers[attribindex][l].uv[1]));
        def fCOL(attribindex): materialgroup[-1] += PackVector(FCODE, vcattriblayers[attribindex][l].color);
        def fCO2(attribindex): materialgroup[-1] += PackVector('B', [ int(x*255.0) for x in vcattriblayers[attribindex][l].color]);
        def fBON(attribindex):
            vgelements = sorted([vge for vge in v.groups if vge.group in validvgroups], reverse=True, key=vgesortfunc);
            vertbones = [grouptobone[vge.group] for vge in vgelements];
            vertbones += [0] * (4-len(vertbones));
            materialgroup[-1] += PackVector(FCODE, vertbones[:4]);
        def fBOI(attribindex):
            vgelements = sorted([vge for vge in v.groups if vge.group in validvgroups], reverse=True, key=vgesortfunc);
            vertbones = [grouptobone[vge.group] for vge in vgelements];
            vertbones += [0] * (4-len(vertbones));
            materialgroup[-1] += PackVector('B', vertbones[:4]);
        def fWEI(attribindex):
            vgelements = sorted([vge for vge in v.groups if vge.group in validvgroups], reverse=True, key=vgesortfunc);
            vertweights = [vge.weight for vge in vgelements];
            vertweights += [0] * (4-len(vertweights));
            vertweights = vertweights[:4];
            weightmagnitude = sum(vertweights);
            if weightmagnitude != 0:
                materialgroup[-1] += PackVector(FCODE, [x/weightmagnitude for x in vertweights[:4]]);
            else:
                materialgroup[-1] += PackVector(FCODE, [x for x in vertweights[:4]]);
        
        fFunc = {
            VBF_POS : fPOS,
            VBF_NOR : fNOR,
            VBF_TAN : fTAN,
            VBF_BTN : fBTN,
            VBF_TEX : fTEX,
            VBF_COL : fCOL,
            VBF_CO2 : fCO2,
            VBF_BON : fBON,
            VBF_BOI : fBOI,
            VBF_WEI : fWEI,
        }
        
        tt = time.time();
        for p in mesh.loop_triangles[:]: # For all mesh's triangles...
            p_loops = p.loops;
            p_vertices = p.vertices;
            p_normals = [
                mathutils.Vector((x[0], x[1], x[2]))
                for x in p.split_normals
                ];
            
            groupkey = materialnames[min(p.material_index, max(0, materialcount-1))];
            materialgroup = out[ groupkey ];
            if len(materialgroup[-1]) >= chunksize:
                materialgroup.append(b'');
            
            vertexcounts[groupkey] += 3;
            
            for i in range3: # For each vertex index...
                l = p_loops[i];
                v = vertices[ p_vertices[i] ];
                
                [fFunc[formatentry](i) for i, formatentry in enumerate(format)];
                
                continue;
            
        print('Time: %s' % (time.time() - tt))
    # Edges
    else:
        for p in mesh.edges[:]: # For all mesh's edges...
            p_vertices = p.vertices;
            
            materialgroup = out[materialnames[0]];
            if len(materialgroup[-1]) >= chunksize:
                materialgroup.append(b'');
            
            vertexcounts[materialnames[0]] += 2;
            
            for i in range2: # For each vertex index...
                v = vertices[ p_vertices[i] ];
                normal = v.normal;
                
                for formatentry in format: # For each attribute in vertex format...
                    if formatentry == VBF_POS: # Position
                        materialgroup[-1] += PackVector(FCODE, v.co);
                    
                    elif formatentry == VBF_NOR: # Normal
                        materialgroup[-1] += PackVector(FCODE, normal);
                    
                    elif formatentry == VBF_TAN: # Tangent
                        materialgroup[-1] += PackVector(FCODE, normal);
                    
                    elif formatentry == VBF_BTN: # Bitangent
                        materialgroup[-1] += PackVector(FCODE, normal);
                    
                    elif formatentry == VBF_TEX: # Texture
                        materialgroup[-1] += PackVector(FCODE, (i, v.index/len(vertices)));
                    
                    elif formatentry == VBF_COL: # Color
                        materialgroup[-1] += PackVector(FCODE, [1.0]*4);
                    
                    elif formatentry == VBF_CO2: # Color
                        materialgroup[-1] += PackVector('B', [255]*4);
                    
                    elif formatentry == VBF_BON: # Bone
                        vertbones = [grouptobone[vge.group] for vge in v.groups if vge.group in validvgroups];
                        vertbones += [0] * (4-len(vertbones));
                        materialgroup[-1] += PackVector(FCODE, vertbones[:4]);
                    
                    elif formatentry == VBF_WEI: # Weight
                        vertweights = [vge.weight for vge in v.groups if vge.group in validvgroups];
                        vertweights += [0] * (4-len(vertweights));
                        weightmagnitude = sum(vertweights);
                        if weightmagnitude != 0:
                            materialgroup[-1] += PackVector(FCODE, [x/weightmagnitude for x in vertweights[:4]]);
                        else:
                            materialgroup[-1] += PackVector(FCODE, [x for x in vertweights[:4]]);
    
    for k in out.keys():
        out[k] = b''.join(out[k]);
    print('vcounts: %s' % [vertexcounts])
    if 0:
        for name, data in out.items():
            print("\"%s\" (%d): " % (name, len(data) / stride));
            for i in range(0, len(data[:40]), stride):
                s = "".join(["%.2f, " % x for x in data[i:i+stride]]);
                print("< %s>" % s);
    
    bpy.context.view_layer.objects.active = sourceobj;
    sourceobj.select_set(1);
    
    return (out, vertexcounts);

def RemoveTempObjects():
    objects = bpy.data.objects;
    selected = [x for x in bpy.context.selected_objects if '__temp' not in x.name];
    
    object = bpy.context.active_object if bpy.context.active_object else bpy.context.object
    
    if not object:
        selected[0].select_set(1);
        bpy.context.view_layer.objects.active = selected[0];
        lastactive = bpy.context.view_layer.objects.active;
        print(bpy.context.active_object.name)
    
    lastobjectmode = bpy.context.active_object.mode;
    lastactive = bpy.context.view_layer.objects.active;
    lastname = lastactive.name;
    
    bpy.ops.object.mode_set(mode = 'OBJECT'); # Update selected
    bpy.ops.object.select_all(action='DESELECT');
    
    targets = [x for x in objects if '__temp' in x.name];
    if lastactive in targets:
        lastactive = None;
    
    for x in targets:
        x.select_set(1);
    
    bpy.ops.object.delete(use_global=False, confirm=False);
    
    # Restore State
    bpy.context.view_layer.objects.active = lastactive;
    for obj in selected:
        obj.select_set(1);
    if not lastactive:
        if selected:
            bpy.context.view_layer.objects.active = selected[0];
        else:
            bpy.context.view_layer.objects.active = objects[lastname[:-len('__temp')]];
    else:
        bpy.ops.object.mode_set(mode = lastobjectmode);
    
def ComposeOutFlag(self):
    flag = 0;
    if self.floattype == 'd':
        flag |= 1 << 0;
    elif self.floattype == 'e':
        flag |= 1 << 1;
    return Pack('B', flag);

def ComposeOutFormat(self, format = -1):
    if format == -1:
        format = self.format;
    
    out_format = b'';
    out_format += Pack('B', len(format)); # Format length
    for f in format:
        out_format += Pack('B', VBFType[f]); # Attribute Type
        out_format += Pack('B', VBFSize[f]); # Attribute Float Size
    return Pack('B', out_format);
