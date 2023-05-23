import bpy
import os


classlist = []

# =============================================================================

class DMR_OP_Reset3DCursor(bpy.types.Operator):
    bl_label = "Reset 3D Cursor"
    bl_idname = 'dmr.reset_3d_cursor'
    bl_description = 'Resets 3D cursor to (0, 0, 0)'
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        context.scene.cursor.location = (0.0, 0.0, 0.0)
        return {'FINISHED'}
classlist.append(DMR_OP_Reset3DCursor)

# =============================================================================

class DMR_OP_Reset3DCursorX(bpy.types.Operator):
    bl_label = "Zero 3D Cursor X"
    bl_idname = 'dmr.reset_3d_cursor_x'
    bl_description = 'Resets x coordinate of 3D Cursor'
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        context.scene.cursor.location[0] = 0.0
        return {'FINISHED'}
classlist.append(DMR_OP_Reset3DCursorX)

# =============================================================================

class DMR_OP_ToggleEditModeWeights(bpy.types.Operator):
    bl_label = "Toggle Edit Mode Weights"
    bl_idname = 'dmr.toggle_editmode_weights'
    bl_description = 'Toggles Weight Display for Edit Mode'
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        bpy.context.scene.tool_settings.vertex_group_user = 'ALL'
        bpy.context.space_data.overlay.show_weight = not bpy.context.space_data.overlay.show_weight
        
        return {'FINISHED'}
classlist.append(DMR_OP_ToggleEditModeWeights)

# =============================================================================

class DMR_OP_ToggleAnimation(bpy.types.Operator):
    bl_label = "Play/Pause Animation"
    bl_idname = 'dmr.play_anim'
    bl_description = 'Toggles animation playback'
    
    def execute(self, context):
        bpy.ops.screen.animation_play()
        return {'FINISHED'}
classlist.append(DMR_OP_ToggleAnimation)

# =============================================================================

class DMR_OP_ImageReloadAll(bpy.types.Operator):
    bl_label = "Reload All Images"
    bl_idname = 'dmr.image_reload'
    bl_description = 'Reloads all images from files'
    
    def execute(self, context):
        for image in bpy.data.images:
            image.reload()
        
        return {'FINISHED'}
classlist.append(DMR_OP_ImageReloadAll)

# =============================================================================

class DMR_OP_RenameNodeInput(bpy.types.Operator):
    bl_label = "Rename Node Input (May not save correctly)"
    bl_idname = 'dmr.rename_node_input'
    bl_description = 'Changes name of node input. (NOTE: may not keep changes after reloading file)'
    bl_options = {'REGISTER', 'UNDO'}
    
    ioindex : bpy.props.EnumProperty(
        name="Target Input",
        description="Name of input to rename",
        items=lambda s, context: [
            ( (str(i), '[%d]: %s' % (i, io.name), 'Rename input %d "%s"' % (i, io.name)) )
            for i, io in enumerate(context.active_node.inputs)
        ])
    
    newname : bpy.props.StringProperty(
        name="New Name", description="New name of input", default='New Name')
    
    def invoke(self, context, event):
        if context.active_node == None:
            self.report({'WARNING'}, 'No active node')
            return {'FINISHED'}
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        [x for x in context.active_node.inputs][int(self.ioindex)].name = self.newname
        return {'FINISHED'}
classlist.append(DMR_OP_RenameNodeInput)

# =============================================================================

class DMR_OP_RenameNodeOutput(bpy.types.Operator):
    bl_label = "Rename Node Output (May not save correctly)"
    bl_idname = 'dmr.rename_node_output'
    bl_description = 'Changes name of node output. (NOTE: may not keep changes after reloading file)'
    bl_options = {'REGISTER', 'UNDO'}
    
    ioindex : bpy.props.EnumProperty(
        name="Target Output",
        description="Name of output to rename",
        items=lambda s, context: [
            ( (str(i), '[%d]: %s' % (i, io.name), 'Rename output %d "%s"' % (i, io.name)) )
            for i, io in enumerate(context.active_node.outputs)
        ])
    
    newname : bpy.props.StringProperty(
        name="New Name", description="New name of output", default='New Name')
    
    def invoke(self, context, event):
        if context.active_node == None:
            self.report({'WARNING'}, 'No active node')
            return {'FINISHED'}
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        [x for x in context.active_node.outputs][int(self.ioindex)].name = self.newname
        return {'FINISHED'}
classlist.append(DMR_OP_RenameNodeOutput)

# =============================================================================

class DMR_OP_FixFileOutputNames(bpy.types.Operator):
    bl_label = "Fix Filename Output"
    bl_idname = 'dmr.fix_filename_output'
    bl_description = "Removes frame count from files exported from File Output Node"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        nodes = scene.node_tree.nodes
        
        framenumber = str(scene.frame_current)
        framenumber = '0'*len(framenumber)+framenumber
        
        for nd in nodes:
            if nd.type == 'OUTPUT_FILE':
                basepath = bpy.path.abspath(nd.base_path)
                for slot in nd.file_slots:
                    ext = slot.format.file_format.lower()
                    fpath = basepath+slot.path+framenumber+'.'+ext
                    
                    if os.path.isfile(fpath):
                        newpath = fpath.replace(framenumber, '')
                        if os.path.isfile(newpath):
                            os.remove(newpath)
                        os.rename(fpath, newpath)
        return {'FINISHED'}
classlist.append(DMR_OP_FixFileOutputNames)

# =============================================================================

class DMR_OP_SetEdgeCrease(bpy.types.Operator):
    bl_label = "Set Crease"
    bl_idname = 'dmr.set_crease'
    bl_description = "Sets edge crease value for selected edges"
    bl_options = {'REGISTER', 'UNDO'}
    
    crease : bpy.props.FloatProperty(
        name="Crease",
        description='Value to set crease to',
        min=-0.0,
        max=1.0, 
    )

    @classmethod
    def poll(cls, context):
        return (context.object is not None and
                context.object.type == 'MESH' and
                context.object.data.is_editmode)

    def execute(self, context):
        crease = self.crease
        context = bpy.context
        objs = [o for o in context.selected_objects if o.type == 'MESH']
        
        lastobjectmode = bpy.context.active_object.mode
        bpy.ops.object.mode_set(mode = 'OBJECT') # Update selected
        
        for obj in objs:
            edges = [e for e in obj.data.edges if e.select]
            for e in edges:
                e.crease = crease
        
        bpy.ops.object.mode_set(mode = lastobjectmode)
        
        return {'FINISHED'}
classlist.append(DMR_OP_SetEdgeCrease)

# =============================================================================

class DMR_OP_RenamePalette(bpy.types.Operator):
    """"""
    bl_idname = "dmr.palette_rename"
    bl_label = "Rename Palette"
    bl_options = {'REGISTER', 'UNDO'}
    
    palette_name : bpy.props.EnumProperty(items = lambda x,c: (tuple([x.name]*3) for x in bpy.data.palettes))
    new_name : bpy.props.StringProperty()
    
    def execute(self, context):
        data = bpy.data.palettes
        if self.palette_name in data.keys():
            data[self.palette_name].name = self.new_name
        return {'FINISHED'}
classlist.append(DMR_OP_RenamePalette)

# =============================================================================

class DMR_OP_PaletteAddColor(bpy.types.Operator):
    """"""
    bl_idname = "dmr.palette_add_color"
    bl_label = "Add Color to Palette"
    
    palette_name : bpy.props.EnumProperty(items = lambda x,c: (tuple([x.name]*3) for x in bpy.data.palettes))
    color : bpy.props.FloatVectorProperty(
        name="Paint Color", subtype="COLOR_GAMMA", size=4, min=0.0, max=1.0,
        default=(1.0, 1.0, 1.0, 1.0)
    )
    
    def execute(self, context):
        data = bpy.data.palettes
        if self.palette_name in data.keys():
            data[self.palette_name].colors.new().color = self.color[:3]
        return {'FINISHED'}
classlist.append(DMR_OP_PaletteAddColor)

# =============================================================================

class DMR_OP_PaletteRemoveColor(bpy.types.Operator):
    """"""
    bl_idname = "dmr.palette_remove_color"
    bl_label = "Remove Color from Palette"
    
    palette_name : bpy.props.EnumProperty(items = lambda x,c: (tuple([x.name]*3) for x in bpy.data.palettes))
    index : bpy.props.IntProperty(default=0)
    
    def execute(self, context):
        data = bpy.data.palettes
        if self.palette_name in data.keys():
            data[self.palette_name].colors.remove(data[self.palette_name].colors[self.index])
        return {'FINISHED'}
classlist.append(DMR_OP_PaletteRemoveColor)

# =============================================================================

class DMR_OP_RemovePalette(bpy.types.Operator):
    """"""
    bl_idname = "dmr.palette_remove"
    bl_label = "Remove Palette"
    
    palette_name : bpy.props.EnumProperty(items = lambda x,c: (tuple([x.name]*3) for x in bpy.data.palettes))
    
    def execute(self, context):
        data = bpy.data.palettes
        if self.palette_name in data.keys():
            data.remove(data.palettes[self.palette_name])
        return {'FINISHED'}
classlist.append(DMR_OP_RemovePalette)

# =============================================================================

class DMR_OP_SetTextFromDialog(bpy.types.Operator):
    bl_idname = "dmr.set_text_from_dialog"
    bl_label = "Set Text From Dialog"
    bl_description = "Sets text from invoke window"
    bl_options = {'REGISTER', 'UNDO'}
    
    text : bpy.props.StringProperty(name="Text")
    
    @classmethod
    def poll(self, context):
        return context.object and context.object.type == 'FONT'
    
    def invoke(self, context, event):
        self.text = context.object.data.body
        return context.window_manager.invoke_props_dialog(self)
    
    def execute(self, context):
        context.object.data.body = self.text
        return {'FINISHED'}
classlist.append(DMR_OP_SetTextFromDialog)

# =============================================================================

class DMR_OP_ModifierOffsetFromCursor(bpy.types.Operator):
    bl_idname = "dmr.modifier_offset_from_cursor"
    bl_label = "Set Modifier Offset From Cursor"
    bl_description = "Sets offset for active modifier using 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(self, context):
        return context.object and context.object.modifiers
    
    def execute(self, context):
        context.object.modifiers.active.offset = context.scene.cursor.location
        return {'FINISHED'}
classlist.append(DMR_OP_ModifierOffsetFromCursor)

# =============================================================================

class DMR_OP_QuickMixInnerSolidify(bpy.types.Operator):
    bl_idname = "dmr.quick_mix_inner_solidify"
    bl_label = "Quick Mix Inner Solidify"
    bl_options = {'REGISTER', 'UNDO'}
    
    solidify : bpy.props.StringProperty(name="Solidify Name")
    shell_group : bpy.props.StringProperty(name="Shell Group", default="-SOLIDSHELL")
    rim_group : bpy.props.StringProperty(name="Rim Group", default="-SOLIDRIM")
    inner_group : bpy.props.StringProperty(name="Inner Group", default="-SOLIDINNER")
    show_render : bpy.props.BoolProperty(name="Show Render", default=False)
    
    @classmethod
    def poll(self, context):
        return context.object and context.object.modifiers != None
    
    def invoke(self, context, event):
        m = context.object.modifiers.active
        if m and m.type == 'SOLIDIFY':
            self.solidify = m.name
            if m.shell_vertex_group:
                self.shell_group = m.shell_vertex_group
            if m.rim_vertex_group:
                self.rim_group = m.rim_vertex_group
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.prop_search(self, 'solidify', context.object, 'modifiers')
        layout.prop_search(self, 'shell_group', context.object, 'vertex_groups')
        layout.prop_search(self, 'rim_group', context.object, 'vertex_groups')
        layout.prop(self, 'show_render')
    
    def execute(self, context):
        modifiers = context.object.modifiers
        vgroups = context.object.vertex_groups
        
        msolidify = ([m for m in modifiers if m.name == self.solidify]+[None])[0]
        if not msolidify:
            msolidify = modifiers.new(name=self.solidify, type='SOLIDIFY')
        
        if self.shell_group not in vgroups.keys():
            vgroups.new(name=self.shell_group)
        vgshell = vgroups[self.shell_group]
        
        if self.rim_group not in vgroups.keys():
            vgroups.new(name=self.rim_group)
        vgrim = vgroups[self.rim_group]
        
        if self.inner_group not in vgroups.keys():
            vgroups.new(name=self.inner_group)
        vginner = vgroups[self.inner_group]
        
        msolidify.shell_vertex_group = vgshell.name
        msolidify.rim_vertex_group = vgrim.name
        
        m = modifiers.new(name="VGMix - Shell + Rim", type='VERTEX_WEIGHT_MIX')
        m.show_expanded = False
        m.show_render = self.show_render
        m.vertex_group_a = vgshell.name
        m.vertex_group_b = vgrim.name
        m.mix_mode = 'SUB'
        m.mix_set = 'ALL'
        
        m = modifiers.new(name="VGMix - Inner + Shell", type='VERTEX_WEIGHT_MIX')
        m.show_expanded = False
        m.show_render = self.show_render
        m.vertex_group_a = vginner.name
        m.vertex_group_b = vgshell.name
        m.mix_mode = 'MUL'
        m.mix_set = 'ALL'
        
        m = modifiers.new(name="Mask - Inner + Shell", type='MASK')
        m.show_expanded = False
        m.show_render = self.show_render
        m.vertex_group = vginner.name
        m.invert_vertex_group = True
        
        return {'FINISHED'}
classlist.append(DMR_OP_QuickMixInnerSolidify)

# =============================================================================

class DMR_OP_ToggleChildrenVisibility(bpy.types.Operator):
    bl_idname = "dmr.toggle_children_visibility"
    bl_label = "Toggle Children Visibility"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(self, context):
        return context.object
    
    def execute(self, context):
        objects = context.object.children
        alloff = sum([1 for x in objects if x.hide_get()]) == len(objects)
        [obj.hide_set(not alloff) for obj in objects]
        return {'FINISHED'}
classlist.append(DMR_OP_ToggleChildrenVisibility)

# =============================================================================

class DMR_OP_CleanUnusedDrivers(bpy.types.Operator):
    bl_label = "Clean Unused Drivers"
    bl_idname = 'dmr.clean_unused_drivers'
    bl_description = 'Removes drivers with no users'
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        """
            Credit: batFINGER on Stack Overflow
            https://blender.stackexchange.com/questions/212450/invalid-drivers-arent-shown-and-cant-be-deleted
        """
        
        colls = [
            p for p in dir(bpy.data)
            if isinstance(getattr(bpy.data, p), bpy.types.bpy_prop_collection)
            ]

        for p in colls:
            for ob in getattr(bpy.data, p, []):
                ad = getattr(ob, "animation_data", None)
                if not ad:
                    continue
                bung_drivers = []
                # find bung drivers
                for d in ad.drivers:
                    try:
                        ob.path_resolve(d.data_path)
                    except ValueError:
                        bung_drivers.append(d)
                # remove bung drivers
                while bung_drivers:
                    ad.drivers.remove(
                            bung_drivers.pop()
                            )
        return {'FINISHED'}
classlist.append(DMR_OP_CleanUnusedDrivers)

# =============================================================================

def register():
    for c in classlist:
        bpy.utils.register_class(c)

def unregister():
    for c in classlist[::-1]:
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
