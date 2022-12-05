import bpy
import os

classlist = []

def Items_ObjectUVLayers(s, context):
    return (
        (x.name, x.name, x.name) for x in context.object.data.uv_layers
    )

# =====================================================================================================

class DMR_OP_FitMirrorModifierToUVEdge(bpy.types.Operator):
    """Sets the \"Mirror U\" value to object UV bounds"""
    bl_idname = "dmr.mirror_modifier_fit_to_uv_bounds"
    bl_label = "Fit Mirror Modifier U Offset to UV Bounds"
    bl_options = {'REGISTER', 'UNDO'}
    
    edge : bpy.props.EnumProperty(
        name="Edge", default = 0, items=(
            ('LEFT', "Left", "Fit to left bound of UVs"),
            ('RIGHT', "Right", "Fit to right bound of UVs"),
            ('CURSOR', "2D Cursor", "Fit to 2D Cursor"),
        ))
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        object = context.object
        uvlayer = object.data.uv_layers.active.data
        print([m.type for m in object.modifiers])
        
        bound = 0
        if self.edge == 'LEFT':
            bound = min([uv.uv[0] for uv in uvlayer])-0.5
        elif self.edge == 'RIGHT':
            bound = max([uv.uv[0] for uv in uvlayer])-0.5
        elif self.edge == 'RIGHT':
            bound = context.area.spaces.active.cursor_location[0]-0.5
        
        for m in context.object.modifiers:
            if m.type == 'MIRROR' and m.use_mirror_u:
                m.mirror_offset_u = bound*2
                print(bound)
        return {'FINISHED'}
classlist.append(DMR_OP_FitMirrorModifierToUVEdge)

# ---------------------------------------------------------------------------

class DMR_OP_FlipUVsAlongAnchor(bpy.types.Operator):
    """Flips selected UVs along anchor"""
    bl_idname = "dmr.flip_uvs_along_anchor"
    bl_label = "Flips UVs Along Anchor"
    bl_options = {'REGISTER', 'UNDO'}   
    
    anchor : bpy.props.EnumProperty(name="Side", items = (
        ('LEFT', "Left", "Flip over left side"),
        ('RIGHT', "Right", "Flip over right side")
    ))
    
    def execute(self, context):
        mode = context.active_object.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        for obj in [x for x in bpy.context.selected_objects if x.type == 'MESH']:
            if not obj.data.uv_layers:
                continue
            uvlayer = obj.data.uv_layers.active
            selectedloops = [i for p in obj.data.polygons if p.select for i in p.loop_indices]
            targetloops = tuple([l for i,l in enumerate(uvlayer.data) if (l.select and i in selectedloops)])
            
            if self.anchor == 'LEFT':
                point = min([l.uv[0] for l in targetloops if l.uv[0] != 0.0])
                for l in targetloops:
                    l.uv[0] = point-(l.uv[0]-point)
            
            elif self.anchor == 'RIGHT':
                point = max([l.uv[0] for l in targetloops if l.uv[0] != 0.0])
                for l in targetloops:
                    l.uv[0] = point-(l.uv[0]-point)
        
        bpy.ops.object.mode_set(mode=mode)
        return {'FINISHED'}
classlist.append(DMR_OP_FlipUVsAlongAnchor)

# ---------------------------------------------------------------------------

class DMR_OP_SplitAndAlignUVEnds(bpy.types.Operator):
    """Splits and aligns selected uv tris and quads"""
    bl_idname = "dmr.split_uv_ends"
    bl_label = "Split And Align UV Ends"
    bl_options = {'REGISTER', 'UNDO'}   
    
    def execute(self, context):
        bpy.ops.object.mode_set(mode='OBJECT')
        for obj in bpy.context.selected_objects:
            if obj.type != 'MESH':
                continue
            uvlayer = obj.data.uv_layers.active
            uvdata = tuple(uvlayer.data)
            uvindex = {uv: i for i,uv in enumerate(uvdata)}
            polys = tuple(obj.data.polygons)
            targetloops = tuple([i for i, uv in enumerate(uvdata) if uv.select])
            targetpolys = [p for p in polys if (not p.hide and p.select and sum([1 for l in p.loop_indices if l in targetloops]) == p.loop_total) ]
            
            Sqr = lambda x: x*x
            
            for p in targetpolys:
                n = p.loop_total
                uvs = [uvdata[l] for l in p.loop_indices]
                edges = [ [uvs[i], uvs[(i+1) % n]] for i in range(0, n) ]
                
                xedges = edges[:]
                yedges = edges[:]
                xedges.sort( key=lambda x: Sqr(x[0].uv[1]-x[1].uv[1]) )
                yedges.sort( key=lambda x: Sqr(x[0].uv[0]-x[1].uv[0]) )
                
                xpair = xedges[0]
                ypair = yedges[0]
                
                # Align with X
                if Sqr(xpair[0].uv[1]-xpair[1].uv[1]) < Sqr(ypair[0].uv[0]-ypair[1].uv[0]):
                    xpair.sort(key=lambda x: x.uv[0])
                    
                    if n == 3:
                        otheruv = [x for x in uvs if x not in xpair][0]
                        otheruv.uv[0] = (xpair[0].uv[0]+xpair[1].uv[0])*0.5
                        
                    elif n == 4:
                        otheruvs = [
                            uv
                            for e in edges if sum(1 for x in xpair if x in e) == 1
                            for uv in e if uv not in xpair
                        ][::-1]
                        
                        #otheruvs = [x for x in uvs if x not in xpair]
                        #otheruvs.sort(key=lambda x: x.uv[0])
                        mid = (otheruvs[0].uv[1] + otheruvs[1].uv[1]) * 0.5
                        
                        otheruvs[0].uv[0] = xpair[0].uv[0]
                        otheruvs[1].uv[0] = xpair[1].uv[0]
                        otheruvs[0].uv[1] = mid
                        otheruvs[1].uv[1] = mid
        
        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}
classlist.append(DMR_OP_SplitAndAlignUVEnds)

# ---------------------------------------------------------------------------

class DMR_OP_CopyUVLayerLoops(bpy.types.Operator):
    """Copies uvs from one layer to another"""
    bl_idname = "dmr.copy_uv_layer_loops"
    bl_label = "Copy UV Layer Loops"
    bl_options = {'REGISTER', 'UNDO'}   
    
    source : bpy.props.EnumProperty(name="Source Layer", items=Items_ObjectUVLayers)
    target : bpy.props.EnumProperty(name="Target Layer", items=Items_ObjectUVLayers)
    
    @classmethod
    def poll(self, context):
        return context.object and context.object.type == 'MESH' and context.object.mode == 'EDIT'
    
    def execute(self, context):
        mode = context.active_object.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        for mesh in list(set([obj.data for obj in context.selected_objects if obj.type == 'MESH'])):
            uvlayers = mesh.uv_layers
            
            if self.source in uvlayers.keys() and self.target in uvlayers.keys():
                sourcelayer = uvlayers[self.source].data
                targetlayer = uvlayers[self.target].data
                
                targetloops = tuple([l for p in mesh.polygons if (p.select and not p.hide) for l in p.loop_indices])
                for l in targetloops:
                    if sourcelayer[l].select:
                        targetlayer[l].uv = sourcelayer[l].uv
        
        bpy.ops.object.mode_set(mode=mode)
        return {'FINISHED'}
classlist.append(DMR_OP_CopyUVLayerLoops)

# =====================================================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
