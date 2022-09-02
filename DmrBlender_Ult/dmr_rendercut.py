import bpy
import bmesh
import os

classlist = []

class RenderCutSettings(bpy.types.PropertyGroup):
    regionnames = [
        "Records", "Portrait", "Versus", "Battle", "Final", "Icon"
    ]
    regionindices = [0, 1, 3, 4, 6, 7]
    
    region_records : bpy.props.PointerProperty(type=bpy.types.Object)
    region_portrait : bpy.props.PointerProperty(type=bpy.types.Object)
    region_versus : bpy.props.PointerProperty(type=bpy.types.Object)
    region_battle : bpy.props.PointerProperty(type=bpy.types.Object)
    region_final : bpy.props.PointerProperty(type=bpy.types.Object)
    region_icon : bpy.props.PointerProperty(type=bpy.types.Object)
    
    battle_mask : bpy.props.PointerProperty(name="Battle Mask", type=bpy.types.Image)
    
    def GetRegionObjects(self):
        return [
            self.region_records,
            self.region_portrait,
            self.region_versus,
            self.region_battle,
            self.region_final,
            self.region_icon
        ]
    
    def GetOutputNames(self, colorindex=0):
        return [
            "chara_0_" + self.character_name + "_0" + str(colorindex),
            "chara_1_" + self.character_name + "_0" + str(colorindex),
            "chara_3_" + self.character_name + "_0" + str(colorindex),
            "chara_4_" + self.character_name + "_0" + str(colorindex),
            "chara_6_" + self.character_name + "_0" + str(colorindex),
            "chara_7_" + self.character_name + "_0" + str(colorindex),
        ]
    
    def CreateObjects(self, context):
        scene = context.scene
        
        objheader = "rendercut-"
        objectmeta = ( # [name, size, pixels, color]
            ('ch0_records', (0.2, 0.2), (128, 128), (1.0, 0.5, 0.0) ),
            ('ch1_portrait', (0.4, 0.4), (512, 512), (0.8, 1.0, 0.0) ),
            ('ch3_versus', (0.7, 0.8), (2376, 1456), (0.0, 1.0, 1.0) ),
            ('ch4_battle', (0.2, 0.2), (162, 162), (1.0, 0.1, 0.0) ),
            ('ch6_final', (0.2, 0.1), (512, 256), (0.0, 0.1, 1.0) ),
            ('ch7_icon', (0.3, 0.2), (454, 300), (1.0, 0.5, 0.0) ),
        )
        
        # Create Collection
        name = "RenderCut"
        collection = None
        if name not in bpy.data.collections.keys():
            collection = bpy.data.collections.new(name)
            context.scene.collection.children.link(collection)
        collection = bpy.data.collections[name]
        collection.hide_render = True
        
        # Create Material
        if "RenderCut" not in bpy.data.materials.keys():
            material = bpy.data.materials.new(name="RenderCut")
            material.use_nodes = True
            
            node_tree = material.node_tree
            nodes = node_tree.nodes
            
            [nodes.remove(nd) for nd in nodes]
            
            def NewNode(type, label, location):
                nd = node_tree.nodes.new(type=type)
                nd.location = location
                nd.label = label
                nd.name = label
                
                return nd
            
            def LinkNodes(n1, output_index, n2, input_index):
                return node_tree.links.new(
                    (node_tree.nodes[n1] if isinstance(n1, str) else n1).outputs[output_index], 
                    (node_tree.nodes[n2] if isinstance(n2, str) else n2).inputs[input_index]
                )
            
            nd_output = NewNode('ShaderNodeOutputMaterial', "Output", (100, 0))
            nd_image = NewNode('ShaderNodeTexImage', "preview", (-100, 0))
            
            LinkNodes(nd_image, 0, nd_output, 0)
        
        # Objects
        for objectindex, meta in enumerate(objectmeta):
            print(meta)
            obj = None
            planemesh = None
            planeobj = None
            
            material = bpy.data.materials["RenderCut"] if "RenderCut" in bpy.data.materials.keys() else None
            objname, scale, pixel_dimensions, color = meta
            
            # Mesh (Visual)
            name = "rendercut_plane"
            
            if name not in bpy.data.meshes.keys():
                planemesh = bpy.data.meshes.new(name=name)
                bm = bmesh.new()
                verts = [
                    bm.verts.new((0,-2,0)),
                    bm.verts.new((2,-2,0)),
                    bm.verts.new((2,0,0)),
                    bm.verts.new((0,0,0)),
                ]
                
                bm.verts.ensure_lookup_table()
                face = bm.faces.new(verts)
                
                uvlayer = bm.loops.layers.uv.new()
                for loop in face.loops:
                    loop[uvlayer].uv = (loop.vert.co[0]/2, -loop.vert.co[1]/2)
                bm.to_mesh(planemesh)
            planemesh = bpy.data.meshes[name]
            
            # Empty (Position)
            name = objheader+objname
            if name not in bpy.data.objects.keys():
                obj = bpy.data.objects.new(name=name, object_data=None)
                obj.location = (0.5, 0.9-scale[1]/3, objectindex * 0.01)
                obj.rotation_mode='QUATERNION'
                obj.rotation_quaternion[:2] = pixel_dimensions
                obj.scale = (scale[0]/2, scale[1]/2, 0.01)
            
            obj = bpy.data.objects[name]
            [c.objects.unlink(obj) for c in obj.users_collection]
            #scene.collection.objects.link(obj)
            collection.objects.link(obj)
            
            obj.lock_location[2] = True
            obj.lock_rotation[2] = True
            obj.lock_scale[2] = True
            obj.empty_display_type = 'CUBE'
            
            [obj.constraints.remove(c) for c in obj.constraints]
            c = obj.constraints.new('LIMIT_ROTATION')
            c.use_limit_x, c.use_limit_y, c.use_limit_z = (True, True, True)
            
            # Mesh Object (Visual)
            name = objname
            if name not in bpy.data.objects.keys():
                bpy.data.objects.new(name=name, object_data=planemesh)
            
            planeobj = bpy.data.objects[name]
            planeobj.parent = obj
            [c.objects.unlink(planeobj) for c in planeobj.users_collection]
            #scene.collection.objects.link(planeobj)
            collection.objects.link(planeobj)
            
            planeobj.show_name = True
            planeobj.hide_select = True
            if material:
                planeobj.data.materials.clear()
                planeobj.data.materials.append(material)
            planeobj.location = (-1, 1, 0)
            planeobj.lock_location = (True, True, True)
            planeobj.lock_rotation = (True, True, True)
            planeobj.lock_scale = (True, True, True)
            planeobj.color[:3] = color
            if 'battle' in name:
                planeobj.scale[2] = -1
        
        rendercutsettings = self
        
        rendercutsettings.region_records = bpy.data.objects[objheader+"ch0_records"]
        rendercutsettings.region_portrait = bpy.data.objects[objheader+"ch1_portrait"]
        rendercutsettings.region_versus = bpy.data.objects[objheader+"ch3_versus"]
        rendercutsettings.region_battle = bpy.data.objects[objheader+"ch4_battle"]
        rendercutsettings.region_final = bpy.data.objects[objheader+"ch6_final"]
        rendercutsettings.region_icon = bpy.data.objects[objheader+"ch7_icon"]
    
    def CreateCompositorGroup(self, context):
        scene = bpy.context.scene
        
        rendercut_settings = self
        regionindices = rendercut_settings.regionindices
        regionobjects = rendercut_settings.GetRegionObjects()
        
        scene.use_nodes = True
        
        name = "RenderCut Crop"
        if name not in bpy.data.node_groups.keys():
            bpy.data.node_groups.new(name=name, type='CompositorNodeTree')
        node_tree = bpy.data.node_groups[name]
        node_tree.use_fake_user = True
        
        if not node_tree.animation_data:
            node_tree.animation_data_create()
        [node_tree.animation_data.drivers.remove(fc) for fc in node_tree.animation_data.drivers] # Clear Drivers
        [node_tree.nodes.remove(nd) for nd in node_tree.nodes] # Clear Nodes
        
        if len(node_tree.inputs) < len(regionindices) or len(node_tree.outputs) < len(regionindices):
            [node_tree.inputs.remove(x) for x in node_tree.inputs]
            [node_tree.outputs.remove(x) for x in node_tree.outputs]
            
            for i in regionindices:
                input = node_tree.inputs.new(type='NodeSocketColor', name="Image ch%d" % i)
                output = node_tree.outputs.new(type='NodeSocketColor', name="Cropped ch%d" % i)
        
        def NewNode(type, label, location):
            #return node_tree.nodes[label]
            nd = node_tree.nodes.new(type=type)
            nd.location = location
            nd.label = label
            nd.name = label
            
            return nd
        
        def LinkNodes(n1, output_index, n2, input_index):
            #return
            return node_tree.links.new(
                (node_tree.nodes[n1] if isinstance(n1, str) else n1).outputs[output_index], 
                (node_tree.nodes[n2] if isinstance(n2, str) else n2).inputs[input_index]
                )
        
        def DriverTransformVariable(driver, name, obj, transform_type):
            v = driver.variables.new()
            v.name = name
            v.type = 'TRANSFORMS'
            v.targets[0].id = obj
            v.targets[0].transform_type = transform_type
            v.targets[0].transform_space = 'TRANSFORM_SPACE'
            return v
        
        def DriverPropertyVariable(driver, name, id_type, obj, data_path):
            v = driver.variables.new()
            v.name = name
            v.type = 'SINGLE_PROP'
            v.targets[0].id_type = id_type
            v.targets[0].id = obj
            v.targets[0].data_path = data_path
            return v
        
        nd_input = NewNode("NodeGroupInput", "input", (-800, 0))
        nd_output = NewNode("NodeGroupOutput", "output", (800, 0))
        
        objindex = 0
        for charaindex, obj in zip(regionindices, regionobjects):
            y = -(objindex)*300
            frame = NewNode("NodeFrame", "ch%d"%charaindex, (0, y))
            
            # Node Create --------------------------------------------------------------------
            nd_crop1 = NewNode("CompositorNodeCrop", "Crop To Region ch%d"%charaindex, (-400, y))
            nd_crop1.use_crop_size = True
            nd_crop1.relative = False
            
            nd_scale = NewNode("CompositorNodeScale", "Scale To Output ch%d"%charaindex, (-200, y))
            
            nd_sepRGBA = NewNode("CompositorNodeSepRGBA", "Sep RGBA ch%d"%charaindex, (0, y-20))
            nd_sepRGBA.hide = True
            
            nd_mask = NewNode("CompositorNodeMask", "Output Mask ch%d"%charaindex, (0, y-80))
            nd_mask.use_feather = False
            nd_mask.size_source = 'FIXED'
            nd_mask.hide = True
            
            nd_setalpha = NewNode("CompositorNodeSetAlpha", "Set Alpha ch%d"%charaindex, (200, y-20))
            nd_setalpha.mode = 'REPLACE_ALPHA'
            nd_setalpha.hide = True
            
            nd_maskmix = NewNode("CompositorNodeMixRGB", "Force Size ch%d"%charaindex, (200, y-80))
            nd_maskmix.hide = True
            
            nd_crop2 = NewNode("CompositorNodeCrop", "Crop To Output ch%d"%charaindex, (400, y))
            nd_crop2.use_crop_size = True
            nd_crop2.relative = False
            
            for nd in [nd_crop1, nd_scale, nd_sepRGBA, nd_mask, nd_setalpha, nd_maskmix, nd_crop2]:
                nd.parent = frame
            
            # Linking --------------------------------------------------------------------
            LinkNodes(nd_input, objindex, nd_crop1, 0)
            
            LinkNodes(nd_crop1, 0, nd_scale, 0)
            
            LinkNodes(nd_scale, 0, nd_sepRGBA, 0)
            LinkNodes(nd_mask, 0, nd_setalpha, 0)
            LinkNodes(nd_sepRGBA, 3, nd_setalpha, 1)
            LinkNodes(nd_setalpha, 0, nd_maskmix, 1)
            LinkNodes(nd_scale, 0, nd_maskmix, 2)
            
            LinkNodes(nd_maskmix, 0, nd_crop2, 0)
            
            LinkNodes(nd_crop2, 0, nd_output, objindex)
            
            # Drivers --------------------------------------------------------------------
            for i in range(0, 4):
                d = node_tree.animation_data.drivers.new(nd_crop1.path_from_id("%s_%s" % (["min", "max"][i%2], "xy"[i//2]))).driver
                d.type = 'SCRIPTED'
                v = DriverTransformVariable(d, "x", obj, 'LOC_' + "XY"[i//2])
                v = DriverTransformVariable(d, "s", obj, 'SCALE_' + "XY"[i//2])
                v = DriverPropertyVariable(d, "r", 'SCENE', scene, "render.resolution_" + "xy"[i//2])
                v = DriverPropertyVariable(d, "rscale", 'SCENE', scene, "render.resolution_percentage")
                d.expression = ["-(-((x-s) * r*rscale/100)//1)", "(((x+s) * r*rscale/100)//1)"][i%2]
            
            for i in range(0, 2):
                d = node_tree.animation_data.drivers.new(nd_scale.inputs[i+1].path_from_id("default_value")).driver
                d.type = 'SCRIPTED'
                v = DriverPropertyVariable(d, "target", 'OBJECT', obj, "rotation_quaternion[%d]" % (i))
                v = DriverTransformVariable(d, "x", obj, 'LOC_' + "XY"[i])
                v = DriverTransformVariable(d, "s", obj, 'SCALE_' + "XY"[i])
                v = DriverPropertyVariable(d, "r", 'SCENE', scene, "render.resolution_" + "xy"[i])
                v = DriverPropertyVariable(d, "rscale", 'SCENE', scene, "render.resolution_percentage")
                d.expression = "(target / ( (((x+s) * r*rscale/100)//1) - -(-((x-s) * r*rscale/100)//1) ))"
            
            for i in range(0, 2):
                d = node_tree.animation_data.drivers.new(nd_mask.path_from_id("size_"+"xy"[i])).driver
                d.type = 'SCRIPTED'
                v = DriverPropertyVariable(d, "target", 'OBJECT', obj, "rotation_quaternion[%d]" % (i))
                v = DriverTransformVariable(d, "x", obj, 'LOC_' + "XY"[i])
                v = DriverTransformVariable(d, "s", obj, 'SCALE_' + "XY"[i])
                v = DriverPropertyVariable(d, "r", 'SCENE', scene, "render.resolution_" + "xy"[i])
                v = DriverPropertyVariable(d, "rscale", 'SCENE', scene, "render.resolution_percentage")
                d.expression = "max(target, (2*s*r*rscale/100))"
            
            for i in range(0, 4):
                d = node_tree.animation_data.drivers.new(nd_crop2.path_from_id("%s_%s" % (["min", "max"][i%2], "xy"[i//2]))).driver
                d.type = 'SCRIPTED'
                v = DriverPropertyVariable(d, "target", 'OBJECT', obj, "rotation_quaternion[%d]" % (i//2))
                v = DriverTransformVariable(d, "x", obj, 'LOC_' + "XY"[i//2])
                v = DriverTransformVariable(d, "s", obj, 'SCALE_' + "XY"[i//2])
                v = DriverPropertyVariable(d, "r", 'SCENE', scene, "render.resolution_" + "xy"[i//2])
                v = DriverPropertyVariable(d, "rscale", 'SCENE', scene, "render.resolution_percentage")
                #d.expression = ["( (r*rscale/100*s)//1 - (x-s)//2)", "-(-( (r*rscale/100*s*2.0) - (r*s)/4 )//1)"][i%2]
                d.expression = (
                    "max(0, -(-((-(-2*s*r*rscale/100.0) - target) / 2)//1) )",
                    "( (( (target - (-2*s*r*rscale/100.0) ) / 2)//1) ) if ( -(-((-(-2*s*r*rscale/100.0) - target) / 2)//1) ) > 0 else target"
                    )[i%2]
            
            objindex += 1
        
classlist.append(RenderCutSettings)

# -----------------------------------------------------------------------------------

class RENDERCUT_OP_InitializeCompositor(bpy.types.Operator):
    """Creates RenderCut Crop node group for use in compositor"""
    bl_idname = 'rendercut.init_compositor'
    bl_label = "Initialize Compositor"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        context.scene.rendercut_settings.CreateCompositorGroup(context)
        return {'FINISHED'}
classlist.append(RENDERCUT_OP_InitializeCompositor)

# -----------------------------------------------------------------------------------

class RENDERCUT_OP_InitializeObjects(bpy.types.Operator):
    """Creates objects for setting up render regions"""
    bl_idname = 'rendercut.init_objects'
    bl_label = "Initialize Objects"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        context.scene.rendercut_settings.CreateObjects(context)
        return {'FINISHED'}
classlist.append(RENDERCUT_OP_InitializeObjects)

# -----------------------------------------------------------------------------------

class RENDERCUT_OP_Clean(bpy.types.Operator):
    """Removes all RenderCut objects"""
    bl_idname = 'rendercut.clean'
    bl_label = "Fix Aspect"
    bl_options = {'REGISTER', 'UNDO'}
    
    objects : bpy.props.BoolProperty(name="Clear Objects", default=True)
    materials : bpy.props.BoolProperty(name="Clear Materials", default=True)
    compositor : bpy.props.BoolProperty(name="Clear Compositor", default=True)
    
    def draw(self, context):
        self.layout.prop(self, 'objects')
        self.layout.prop(self, 'materials')
        self.layout.prop(self, 'compositor')
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        if self.objects:
            rendercut_settings.CleanObjects()
        
        return {'FINISHED'}
classlist.append(RENDERCUT_OP_Clean)

# -----------------------------------------------------------------------------------

class RENDERCUT_OP_FixAspect(bpy.types.Operator):
    """Fixes scale aspect to match set resolution's aspect"""
    bl_idname = 'rendercut.correct_aspect'
    bl_label = "Fix Aspect"
    bl_options = {'REGISTER', 'UNDO'}
    
    object : bpy.props.StringProperty()
    
    def execute(self, context):
        if self.object in bpy.data.objects.keys():
            object = bpy.data.objects[self.object]
            pixelsize = object.rotation_quaternion[:2]
            
            if pixelsize[1] > pixelsize[0]:
                object.scale[0] = object.scale[1]*(pixelsize[0]/pixelsize[1])
            else:
                object.scale[1] = object.scale[0]*(pixelsize[1]/pixelsize[0])
        
        return {'FINISHED'}
classlist.append(RENDERCUT_OP_FixAspect)

# =============================================================================

def RenderCutLayout(self, context):
    scene = context.scene
    
    rendercutsettings = scene.rendercut_settings
    layout = self.layout
    
    c = layout.column(align=1)
    c.operator('rendercut.init_objects')
    c.operator('rendercut.init_compositor')
    
    c = layout.column()
    
    if 'RenderCut' in bpy.data.materials.keys():
        if 'preview' in bpy.data.materials['RenderCut'].node_tree.nodes.keys():
            c.prop(bpy.data.materials['RenderCut'].node_tree.nodes['preview'], "image", text="Preview Image")
    
    cc = c.box().column(align=1)
    
    regionnames = rendercutsettings.regionnames
    regionindices = rendercutsettings.regionindices
    
    outputresolution = (
        scene.render.resolution_x * scene.render.resolution_percentage/100,
        scene.render.resolution_y * scene.render.resolution_percentage/100
        )
    
    for i, obj in enumerate(rendercutsettings.GetRegionObjects()):
        if obj:
            b = c.box().column(align=1)
            
            r = b.row()
            r.label(text=regionnames[i] + " (ch%d)" % regionindices[i])
            r.operator('rendercut.correct_aspect', text="Fix Aspect").object = obj.name
            
            r = b.row(align=1)
            rr = r.row()
            rr.scale_x = 0.8
            rr.label(text="Pixels:")
            r.prop(obj, "rotation_quaternion", text="Width", index=0)
            r.prop(obj, "rotation_quaternion", text="Height", index=1)
            
            cropsizes = (
                (outputresolution[0] * obj.scale[0]*2),
                (outputresolution[1] * obj.scale[1]*2)
            )
            
            b.label(text="First Crop Size: (%d, %d)" % (cropsizes))
            
            if cropsizes[0] < obj.rotation_quaternion[0]:
                b.label(text="Increase Render Width", icon='ERROR')
            if cropsizes[1] < obj.rotation_quaternion[1]:
                b.label(text="Increase Render Height", icon='ERROR')

class DMRSMASH_PT_RenderCut(bpy.types.Panel): # ------------------------------
    bl_label = "Render Cut"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Render Cut" # Name of sidebar
    
    draw = RenderCutLayout
classlist.append(DMRSMASH_PT_RenderCut)

class DMRSMASH_PT_RenderCut_Properties(bpy.types.Panel): # ------------------------------
    bl_label = "Render Cut"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "output"
    
    draw = RenderCutLayout
classlist.append(DMRSMASH_PT_RenderCut_Properties)

# =====================================================================================

# Register and add to the "object" menu (required to also use F3 search "Simple Object Operator" for quick access).
def register():
    for c in classlist:
        bpy.utils.register_class(c)
    bpy.types.Scene.rendercut_settings = bpy.props.PointerProperty(type=RenderCutSettings)

def unregister():
    for c in classlist.reverse():
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
