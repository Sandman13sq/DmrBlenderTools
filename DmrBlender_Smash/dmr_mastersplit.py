import bpy
import shutil
import os

classlist=  []

print("-" * 80)

VALIDEXTENSIONS = [
    "."+x for x in "prcxml xmbst eff nutexb nuhlpb numatb numdlb numshb numshexb xmb nusrcmdlb nusktb prc bntx nus3audio xmsbt prcx".split()
]

ROOTEXTENSIONS = VALIDEXTENSIONS + [
    "."+x for x in "json toml webp".split()
]

def TryMakeDir(path):
    path = path.replace("\\", "/")
    pos = path.find("/")
    
    os.makedirs(path[:path.rfind("/")+1], exist_ok=True)

# ----------------------------------------------------------------------------------

def ReplaceTextInFile(fpath, oldstring, newstring):
    oldstring = str(oldstring)
    newstring = str(newstring)
    
    if os.path.isfile(fpath):
        #print("> Replacing text in \"%s\"" % fpath)
        try:
            f = open(fpath, 'r')
            ftext = f.read().replace(oldstring, newstring)
            f.close()
            f = open(fpath, 'w')
            f.write(ftext)
            f.close()
        except:
            oldstring = oldstring.encode('utf-16-le')
            newstring = newstring.encode('utf-16-le')
            
            f = open(fpath, 'rb')
            
            ftext = f.read().replace(oldstring, newstring)
            f.close()
            
            f = open(fpath, 'wb')
            f.write(ftext)
            f.close()
    else:
        print("> No file found for replacing: \"%s\"" % fpath)

'# ==================================================================================================='
'# PROPERTY GROUPS'
'# ==================================================================================================='

class CSplit_SplitMaster_SplitEntry(bpy.types.PropertyGroup):
    name : bpy.props.StringProperty()
    replace : bpy.props.StringProperty()
classlist.append(CSplit_SplitMaster_SplitEntry)

# -------------------------------------------------------------------

class CSplit_SplitMaster(bpy.types.PropertyGroup):
    csplit_source : bpy.props.StringProperty(subtype='DIR_PATH')
    csplit_destination : bpy.props.StringProperty(subtype='DIR_PATH')
    modname : bpy.props.StringProperty()
    masterpath : bpy.props.StringProperty(subtype='DIR_PATH')
    outpath : bpy.props.StringProperty(subtype='DIR_PATH')
    master_indices : bpy.props.BoolVectorProperty(size=8, default=[True]*8)
    
    csplit_entries : bpy.props.CollectionProperty(type=CSplit_SplitMaster_SplitEntry)
    csplit_entries_index : bpy.props.IntProperty()
    
    split_char : bpy.props.StringProperty(name="Split Char", default="X")
    
    def AddEntry(self):
        self.csplit_entries.add().name = self.csplit_entries[self.csplit_entries_index].name if self.csplit_entries else "filename.ext"
    
    def RemoveEntry(self, index):
        self.csplit_entries.remove(index)
    
    def SplitFiles(self):
        print("> Splitting files...")
        
        sourcefolder = os.path.realpath(bpy.path.abspath(bpy.context.scene.csplit_source))
        destfolder = os.path.realpath(bpy.path.abspath(bpy.context.scene.csplit_destination))
        
        cindices = ["c0" + str(i) for i,c in enumerate(self.master_indices) if c]
        print(cindices)
        
        # Compose filenames
        filenames = [
            entry.name % replace
            for entry in self.csplit_entries
            for replace in ( entry.replace.split() if entry.replace else "")
        ]
        
        # Copy Files
        for fpath in filenames:
            for cindex in cindices:
                srcpath = sourcefolder + "\\" + fpath
                destpath = destfolder + "\\" + cindex + "\\" + fpath
                
                if os.path.exists(srcpath):
                    shutil.copy2(srcpath, destpath)
                else:
                    print('> Path invalid: "%s"' % srcpath)
    
    def SplitMaster(self):
        modname = self.modname
        indices = [i for i,x in enumerate(self.master_indices) if x]
        masterpath = self.masterpath
        outpath = self.outpath
        
        # Split Mods
        for i in indices:
            self.SplitMod(masterpath, outpath + modname + (" c0%d" % i) + "/", [i], False)
        
        # All
        self.SplitMod(masterpath, outpath + modname + "/", indices, True)
    
    def SplitMod(self, masterpath, outpath, cindices=range(0,8), all_slots=True):
        """
            Files evaluate reverse alphabetically
            
            PREFIX:
            "_" = Skip on export
            
            SUFFIX:
            "/cXX" = Splits directory into c00, c01, c02, ...
            "_xx" = Appropriate index is written. All written on no index
            "-c__" = Written for all slots only. "-c__" part removed.
            "-c##" = Appropriate index is written. "-c##" part removed (## = Color Index)
            "-cXX" = Appropriate index is written. "-cXX" part removed
            "_cXX" = Appropriate index is written. Splits on all slots
        """
        
        masterpath = os.path.realpath(bpy.path.abspath(masterpath))
        outpath = os.path.realpath(bpy.path.abspath(outpath))
        
        if masterpath[-1] not in "/\\":
            masterpath += "/"
        if outpath[-1] not in "/\\":
            outpath += "/"
        
        print("> Writing to ", masterpath)
        
        dosplit = not all_slots
        
        excludedir = ["c0%d" % i for i in range(0, 8) if (i not in cindices)]
        includedir = ["c0%d" % i for i in range(0, 8) if (i in cindices)]
        
        validcXX = ["0%d" % i for i in range(0, 8)]
        validcXX_underscore = ["_c0%d" % i for i in range(0, 8)]
        validcXX_hyphen = ["-c0%d" % i for i in range(0, 8)]
        
        includecXX = ["0%d" % i for i in cindices]
        includecXX_underscore = ["_c0%d" % i for i in cindices] # _cXX
        includecXX_hyphen = ["-c0%d" % i for i in cindices] # -cXX
        
        cXXorder = [
            [(0,1,2,3,4,5,6,7)],  # cXX
            [(0,2,4,6), (1,3,5,7)], # cXX, cYY
            ]
        
        def Basename(name):
            return name[:name.find(".")]
        
        def CopyFile(srcpth, destpth):
            TryMakeDir(destpth)
            shutil.copy2(srcpth, destpth)
        
        def Split(currentpath, currentoutpath):
            walk = list(os.walk(masterpath + currentpath))
            
            if walk:
                fullpath, dirnames, fnames = walk[0]
                nextdirs = [d for d in dirnames if d not in excludedir]
                
                cXXindices = cXXorder[0]
                if ("cXX" in nextdirs) and ("cYY" in nextdirs):
                    cXXindices = cXXorder[1]
                
                # Directories
                for dirname in nextdirs[::-1]:
                    if dirname[0] == "_":
                        continue
                    
                    if dirname == "cXX": # Split cXX to c00, c01, c02, ...
                        for cdir in [("c0%d" % ci) for ci in cXXindices[0] if ci in cindices]:
                            Split(currentpath+dirname+"/", currentoutpath+cdir+"/")
                    elif dirname == "cYY": # Split cXX to c00, c01, c02, ...
                        for cdir in [("c0%d" % ci) for ci in cXXindices[1] if ci in cindices]:
                            Split(currentpath+dirname+"/", currentoutpath+cdir+"/")
                    else:
                        Split(currentpath+dirname+"/", currentpath+dirname+"/")
                
                srcdir = masterpath + currentpath
                destdir = outpath + currentoutpath
                
                # Files
                if not fnames:
                    return
                print("<root>/"+currentoutpath)
                
                fnames.sort(key=lambda x: "-c__" not in x)
                
                validextlist = ROOTEXTENSIONS if currentoutpath == "" else VALIDEXTENSIONS
                
                # Split cXX, cYY
                cXXindices = cXXorder[0]
                if sum([1 for x in fnames if Basename(x)[-3:] == "cYY"]) > 0:
                    cXXindices = cXXorder[1]
                
                for fname in fnames[::-1]:
                    # Skip leading underscore names or names with spaces
                    if fname[0] == "_" or " " in fname:
                        continue
                    
                    if sum([1 for x in validextlist if fname[-len(x):].lower() == x.lower()]) == 0:
                        #print("> Omitting", fname)
                        continue
                    
                    if currentoutpath == "":
                        print(fname)
                    
                    basename = Basename(fname)
                    last4chars = basename[-4:]
                    filecolor = last4chars[-2:]
                    
                    if 'sound' in currentpath:
                        print(basename, cXXindices)
                    
                    # Keep on all slots, cut filename
                    if last4chars == '-c__':
                        if all_slots:
                            CopyFile(srcdir+fname, destdir+fname.replace(last4chars, ""))
                    
                    # cXX, cYY, ...
                    else:
                        normalfile = True
                        for XXindex, XX in enumerate([c*2 for c in "XYZW"[:len(cXXindices)]]):
                            # Write appropriate color, cut filename
                            if last4chars in ['-c0%d' % ci for ci in cXXindices[XXindex]]:
                                if last4chars in ['-c0%d' % ci for ci in cXXindices[XXindex]]:
                                    CopyFile(srcdir+fname, destdir+fname.replace(last4chars, ""))
                                normalfile = False
                                break
                            
                            # Split to appropriate color, cut filename
                            elif last4chars == '-c'+XX:
                                for ci in ['-c0%d' % ci for ci in cXXindices[XXindex] if ci in cindices]:
                                    CopyFile(srcdir+fname, destdir+fname.replace(last4chars, ""))
                                normalfile = False
                                break
                            
                            # Split and write colors, fix filename
                            elif last4chars == '_c'+XX:
                                for ci in ['_c0%d' % ci for ci in cXXindices[XXindex] if ci in cindices]:
                                    CopyFile(srcdir+fname, destdir+fname.replace(last4chars, ci))
                                normalfile = False
                                break
                            
                            # Write Appropriate color for "chara" file
                            elif fname[:len("chara")] == "chara" and filecolor in ['0%d' % ci for ci in cXXindices[XXindex]]:
                                if last4chars[1:] in ['_0%d' % ci for ci in cXXindices[XXindex] if ci in cindices]:
                                    CopyFile(srcdir+fname, destdir+fname)
                                normalfile = False
                                break
                            
                        # Write file as is
                        if normalfile:
                            CopyFile(srcdir+fname, destdir+fname)
        
        Split("", "")
        
        if dosplit:
            ReplaceTextInFile(outpath+"config.json", "cXX", "c0%d" % cindices[0])
            ReplaceTextInFile(outpath+"/ui/message/msg_name.xmsbt", "_XX", "_0%d" % cindices[0])
            ReplaceTextInFile(outpath+"/info.toml", "[INDEX]", str(cindices[0]).zfill(2))
            ReplaceTextInFile(outpath+"/info.toml", "[COLOR]", cindices[0]+1)
        
        print(cindices)

classlist.append(CSplit_SplitMaster)

# ------------------------------------------------------------------

class CSPLIT_UL_SplitEntries(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        c = layout.column(align=1)
        r = c.row(align=1)
        r.prop(item, 'name', text="")
        r.operator('csplit.remove_entry', text="", icon='REMOVE').index=index
        c.prop(item, 'replace', text="%s List")
classlist.append(CSPLIT_UL_SplitEntries)

# ==================================================================================================

class CSplit_Master(bpy.types.PropertyGroup):
    size : bpy.props.IntProperty()
    items : bpy.props.CollectionProperty(type=CSplit_SplitMaster)
    itemindex : bpy.props.IntProperty()
    
    update_mutex : bpy.props.BoolProperty(default=False)
    
    op_add_item : bpy.props.BoolProperty(default=False, update=lambda s,c: s.Update(c))
    op_remove_item : bpy.props.BoolProperty(default=False, update=lambda s,c: s.Update(c))
    op_move_up : bpy.props.BoolProperty(default=False, update=lambda s,c: s.Update(c))
    op_move_down : bpy.props.BoolProperty(default=False, update=lambda s,c: s.Update(c))
    
    op_cycles : bpy.props.BoolProperty(default=False, update=lambda s,c: s.Update(c))
    op_image_textures : bpy.props.BoolProperty(default=False, update=lambda s,c: s.Update(c))
    
    def GetActive(self):
        return self.items[self.itemindex] if self.size > 0 else None
    
    def GetItem(self, index):
        return self.items[index] if self.size else None 
    
    def FindItem(self, name):
        return ([x for x in self.items if x.name == name]+[None])[0]
    
    def Add(self):
        item = self.items.add()
        #item.Update(None)
        item.name = "New Splitter"
        self.size = len(self.items)
        self.itemindex = max(min(self.itemindex, self.size-1), 0)
        return item
    
    def RemoveAt(self, index):
        if len(self.items) > 0:
            self.items.remove(index)
            self.size = len(self.items)
            self.itemindex = max(min(self.itemindex, self.size-1), 0)
    
    def MoveItem(self, index, move_down=True):
        newindex = index + (1 if move_down else -1)
        self.items.move(index, newindex)
    
    def Update(self, context):
        # Add
        if self.op_add_item:
            self.op_add_item = False
            self.Add()
            self.itemindex = self.size-1
        
        # Remove
        if self.op_remove_item:
            self.op_remove_item = False
            self.RemoveAt(self.itemindex)
        
        # Move
        if self.op_move_down:
            self.op_move_down = False
            self.items.move(self.itemindex, self.itemindex+1)
            self.itemindex = max(min(self.itemindex+1, self.size-1), 0)
        
        if self.op_move_up:
            self.op_move_up = False
            self.items.move(self.itemindex, self.itemindex-1)
            self.itemindex = max(min(self.itemindex-1, self.size-1), 0)
    
classlist.append(CSplit_Master)

# -------------------------------------------------------------------------------------

class CSPLIT_UL_SplitMasterList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.prop(item, 'name', text="", emboss=False)
classlist.append(CSPLIT_UL_SplitMasterList)

'# ==================================================================================================='
'# OPERATORS'
'# ==================================================================================================='

class CSPLIT_OT_Split(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "dmrsmash.csplit"
    bl_label = "Split Files"
    
    @classmethod
    def poll(self, context):
        return context.scene.csplit_master.GetActive()
    
    def execute(self, context):
        context.scene.csplit_master.GetActive().SplitFiles()
        return {'FINISHED'}
classlist.append(CSPLIT_OT_Split)

# ================================================================================

class CSPLIT_OT_AddEntry(bpy.types.Operator):
    bl_idname = "csplit.add_entry"
    bl_label = "Add Entry"
    
    @classmethod
    def poll(self, context):
        return context.scene.csplit_master.GetActive()
    
    def execute(self, context):
        context.scene.csplit_master.GetActive().AddEntry()
        return {'FINISHED'}
classlist.append(CSPLIT_OT_AddEntry)

# ---------------------------------------------------------------

class CSPLIT_OT_RemoveEntry(bpy.types.Operator):
    bl_idname = "csplit.remove_entry"
    bl_label = "Remove Entry"
    
    index : bpy.props.IntProperty()
    
    @classmethod
    def poll(self, context):
        return context.scene.csplit_master.GetActive()
    
    def execute(self, context):
        context.scene.csplit_master.GetActive().RemoveEntry(self.index)
        return {'FINISHED'}
classlist.append(CSPLIT_OT_RemoveEntry)

# ================================================================================

class CSPLIT_OT_MasterSplit(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "dmrsmash.master_split"
    bl_label = "Split Master"
    
    @classmethod
    def poll(self, context):
        return context.scene.csplit_master.GetActive()
    
    def execute(self, context):
        context.scene.csplit_master.GetActive().SplitMaster()
        return {'FINISHED'}
classlist.append(CSPLIT_OT_MasterSplit)

'# ==================================================================================================='
'# UI & PANELS'
'# ==================================================================================================='

class CSPLIT_PT_CSplit(bpy.types.Panel):
    bl_label = 'CSplit'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "DmrSmash" # Name of sidebar
    
    def draw(self, context):
        layout = self.layout
        
        master = context.scene.csplit_master
        
        # Item List
        r = layout.row()
        c = r.column(align=1)
        c.template_list(
            "CSPLIT_UL_SplitMasterList", "", 
            master, "items", 
            master, "itemindex", 
            rows=3)
        
        c = r.column(align=1)
        c.prop(master, 'op_add_item', text="", icon='ADD')
        c.prop(master, 'op_remove_item', text="", icon='REMOVE')
        
classlist.append(CSPLIT_PT_CSplit)

# =====================================================================================

class CSPLIT_PT_CSplit_MasterSplit(bpy.types.Panel):
    bl_label = 'Master Split'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "DmrSmash" # Name of sidebar
    bl_parent_id = 'CSPLIT_PT_CSplit'
    
    def draw(self, context):
        layout = self.layout
        
        master = context.scene.csplit_master
        
        # Active Item
        csplit = master.GetActive()
        
        if csplit:
            b = layout.box().column(align=1)
            b.prop(csplit, 'modname', text="Modname")
            b.prop(csplit, 'masterpath', text="master")
            b.prop(csplit, 'outpath', text="out")
            b.row().prop(csplit, 'split_char')
            
            r = b.column().row(align=1)
            for i in range(0, 8):
                r.prop(csplit, 'master_indices', text=str(i), index=i, toggle=1)
            b.operator('dmrsmash.master_split')
        
classlist.append(CSPLIT_PT_CSplit_MasterSplit)

# ================================================================================

class CSPLIT_PT_CSplit_FileSplit(bpy.types.Panel):
    bl_label = 'File Split'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "DmrSmash" # Name of sidebar
    bl_parent_id = 'CSPLIT_PT_CSplit'
    
    def draw(self, context):
        layout = self.layout
        
        csplit = context.scene.csplit_master.GetActive()
        
        if csplit:
            b = layout.box().column(align=1)
            b.prop(csplit, 'csplit_source', text="cXX")
            b.prop(csplit, 'csplit_destination', text="Dest")
            
            cc = b.column()
            cc.operator('csplit.add_entry', icon='ADD')
            cc.template_list(
                "CSPLIT_UL_SplitEntries", "", 
                csplit, "csplit_entries", 
                csplit, "csplit_entries_index", 
                rows=4)
            
            b.operator('dmrsmash.csplit')
        
classlist.append(CSPLIT_PT_CSplit_FileSplit)

'# ==================================================================================================='
'# REGISTER'
'# ==================================================================================================='

def register():
    for c in classlist:
        bpy.utils.register_class(c)
    bpy.types.Scene.csplit_master = bpy.props.PointerProperty(type=CSplit_Master)

def unregister():
    for c in reversed(classlist):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()

# Run on file start
bpy.data.texts[__file__[__file__.rfind("\\")+1:]].use_module = True


