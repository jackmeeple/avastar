### Copyright 2015, Gaia Clary
### Modifications 2015 Gaia Clary
###
### This file is part of Avastar 1.
###

### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####





msg_RigProp_spine_is_visible=\
                  "Show Bento Spine bones (mSpine1, mSpine2, mSPine3, mSpine4)\n"\
                + "\n"\
                + "You can Enable/Disable the usage of the Spine bones in the Rig Control Panel"


msg_export_warnings = '%d areas found where the export could be optimized. (Please Read on)|'\
                +  '$operator\n\n'\
                +  '%s \n'\
                +  'Note: The listed issues could be important. I recommend that\n'\
                +  'you review the list and optimize your model if necessary.'


msg_export_warning_note = 'Note: The issues above probably are not very important, but i\n'\
                +  'recommend that you review the list and optimize your model if necessary.\n\n'\
                +  'For Experts: More info can be found in the Blender Console'

msg_export_errors = '%d areas found where the export failed. (Please Read on)|'\
                +  '$operator\n\n'\
                +  '%s \n'\
                +  'Note: The mentioned issues must be carefully inspected and fixed.\n'\
                +  'But i can not do this for you.\n\n'\
                +  'For Experts: More info can be found in the Blender Console\n|'

msg_export_error_note = 'Note: The mentioned issues must be carefully inspected and fixed.\n'\
                +  'But i can not do this for you.\n\n'\
                +  'For Experts: More info can be found in the Blender Console'

msg_no_armature = '%s is not assigned to an Armature.|'\
                +  'DETAIL: We need an armature to decide which weight groups need to be examined.\n'\
                +  'However your object is currently not assigned to an armature.\n'\
                +  'ACTION: Please assign this object to an armature, then try again.|'

msg_undeform_bones = '%d weightgroups assigned to non deforming bones.|'\
                   + 'DETAIL: non deforming bones for Mesh %s are completely ignored.\n'\
                   + 'Tip: Check if the bone deform flags are set as expected.\n'

msg_unweighted_verts = 'Please fix %d unweighted vertices on %s.|'\
                +  'DETAIL INFO:\nSome of the vertices in your mesh are not assigned to any weight group.\n'\
                +  'Avastar has stopped processing your request, because it can not handle unweighted vertices.\n\n'\
                +  'YOUR ACTION:\n'\
                +  '- Ensure that all vertices of your mesh are assigned to weight groups.\n'\
                +  '- Tip: Open Avastar Tool box\n'\
                +  '       Call the [Unweighted Verts] finder from the vertex tools section.\n\n|find_unweighted'

msg_zero_verts = 'Please fix %d verts with a weight sum of 0 in %s.|'\
                +  'DETAIL INFO:\nAll of the vertices in your mesh are assigned correctly to weight groups.\n'\
                +  'But some of the assigned verts have a weight sum of 0 (zero). Avastar can not handle \n'\
                +  'this and has aborted the operation.\n\n'\
                +  'YOUR ACTION:\n'\
                +  '- Open Avastar Tool Box\n'\
                +  '- Lookup the [Zero Weights] finder from the Vertex Tools setion.\n'\
                +  '- For each selected vertex assign a non zero value to at least one weight group.\n'\
                +  '- Please use the available Weight copy tools from the\n'\
                +  '  Weight Paint Tools shelf to fix this.\n\n|find_unweighted'

msg_zero_materials = 'No materials assigned to exported Object(s)|'\
                   + 'We recommend that you create at least one Material for your opbjects'\
                   + 'to declare the SL texture Faces'

msg_face_tricount = 'At least one Texture Face with high Triangle count (%d tris).|'\
              +  'DETAIL INFO:\nIn SL any Texture Face has a limit of 21844 Triangles.\n'\
              +  'If a texture face uses more than 21844 Triangles,\n'\
              +  'the SL Importer automatically splits the face into subfaces.\n'\
              +  'and each subface is treated by the SL Importer as one extra Material.\n'\
              +  'This can lead to unexpected results:\n\n'\
              +  'More than 8 materials:\n'\
              +  'If a Mesh has more than 8 materials the entire mesh gets split into submeshes.\n'\
              +  'You might want to avoid this.\n\n'\
              +  'Missing Material in LOD\n'\
              +  'When you let the SL Importer generate LOD, then it may end up in a weird state\n'\
              +  "where it calculates different Material counts in the lower LOD's\n"\
              +  'which results in an Importer Error.\n\n'\
              +  'YOUR ACTION:\n'\
              +  '- Reduce the number of Triangles in your Mesh\n'\
              +  '- Take care to create texture faces with less than 21844 triangles\n\n|high_tricount'

msg_mesh_tricount = 'Mesh with high Triangle count (%d tris).|'\
              +  'DETAIL INFO:\nAccording to the SL Wiki a Mesh may not use\n'\
              +  'more than 174,752 triangles in total.\n'\
              +  'One of your meshes exceeds this number.\n'\
              +  'This will cause an error when you try to import your mesh to SL.\n\n'\
              +  'YOUR ACTION:\n'\
              +  '- Reduce the number of Triangles in your Mesh\n'\
              +  '- Take care to create texture faces with less than 21844 triangles\n\n|high_tricount'

msg_identified_weightgroups = "The following %d mesh Weight Groups have been identified as Bone deforming Weightmaps.\n"\
                + "These Weightmaps will be exported by Avastar\n\n"\
                + "List of affected Weightmaps:\n\n"

msg_discarded_weightgroups = "The following %d mesh Weight Groups will not be used as Bone deforming Weightmaps,\n"\
                + "because the associated Bones are not marked as 'Deforming Bones'.\n\n"\
                + "Note: You can change this by enabling 'Deform' in the corresponding\n"\
                + "Bone properties of the associated Armature.\n\n"\
                + "List of affected Weight Groups:\n\n"
                
msg_missing_uvmaps = "No UV Map found in %d %s:|"\
                + "%s\n"\
                + "DETAIL:\n"\
                + "You need UV Maps to texturise your Mesh.\n"\
                + "If you later try to add a texture to an object without UV Map,\n"\
                + "this will fail (the mesh gets a unique color at best).\n\n"\
                + "YOUR ACTION:\n"\
                + "Unwrap (keyboard shortcut 'U') all meshes with no UV Layer\n\n"\
                + "NOTE:\nYou must have a good understanding of UV unwrapping\n"\
                + "before you can expect to get good results!\n"

msg_no_objects_to_copy_from = "No meshes available from where to copy weights|"\
                + "DETAIL:\n"\
                + "You want to assign weights from other meshes to %s.\n"\
                + "But i could not find weight sources\n\n"\
                + "Possible causes:\n"\
                + "* There is no other weighted mesh rigged to the Armature [%s]\n"\
                + "* You have not selected any weight sources\n"\
                + "* All weight sources are invisible\n\n"\
                + "YOUR ACTION:\n"\
                + "Make sure you have selected the weight sources properly.\n"\
                + "Maybe you want to switch the Weight Source from 'Meshes' to 'Bones' (see panel)|copy_bone_weights"

msg_no_avastar_meshes_to_copy_from = "No Avastar meshes available from where to copy weights|"\
                + "DETAIL:\n"\
                + "You want to assign weights from Avastar meshes to %s.\n"\
                + "But all Meshes from where you want to copy weights\n"\
                + "either do not exist in Armature [%s] or are not visible\n\n"\
                + "YOUR ACTION:\n"\
                + "Make the Avastar meshes visible or use a different strategy (see panel)|copy_bone_weights"

msg_no_weights_to_copy_from = "No meshes visible from where to copy weights|"\
                + "DETAIL:\n"\
                + "You want to Bind with copy weights from other 'Meshes' to %s. However \n"\
                + "all other rigged meshes on the active armature [%s] are not visible.\n\n"\
                + "YOUR ACTION:\n"\
                + "- Either Switch the Weight option from 'Meshes' to 'Bones' (see panel)\n"\
                + "or otherwise please ensure that:\n"\
                + "- At least one other Mesh is already attached to the Armature\n"\
                + "- AND at least one of the attached other meshes is visible|copy_bone_weights"

msg_failed_to_bind_automatic = "Could not generate weights for all vertices|"\
                + "DETAIL:\n"\
                + "You want to Bind with generating weights from Bones. However \n"\
                + "Blender was not able to find a solution for %d vertices in your mesh \"%s\".\n\n"\
                + "REASON:\n"\
                + "Your Mesh probably contains multiple overlaping sub meshes.\n\n"\
                + "YOUR ACTIONS (alternatives):\n"\
                + "- Ensure that the submeshes do not overlap\n"\
                + "- consider to make a cleaner topology with only one mesh\n"\
                + "- You could separate your mesh into multiple objects\n"\
                + "  instead of using just one single object\n"\
                + "Hint: You can revert this operation by pressing CTRL Z|binding"

msg_edit_system_mesh = '''Avastar Object "%s" should never be edited directly|Detail:
Editing a system mesh can cause heavy distortions 
and may break the Avatar shape!

Your Action:
Please use the Freeze Tool to create an editable copy.
You find the Freeze tool in the Tool Shelf:

    Avastar Tab --> Tools Panel --> Freeze Shape section

Important: The freeze tool applies all shape keys to the mesh!
|/help/freeze-shape'''

panel_info_mesh = '''Mesh Inspector Display Important Mesh statistics for current Selection| Quickinfo:
* Statistics:
  - Verts : Number of vertices for current selection
  - Faces : Number of Faces for Current Selection
  - Tris  : Number of Triangles after triangulate is performed
  - Mats  : Number of Materials (for the Object with highest number of materials)
Note: Mats can have 2 numbers n/m where n is the number of user defined materials
and m is the number of materials created by the SL Importer

* Estimates: Estimated numbers for different Levels of Detail.
The estimates only give an estimate! 
The final numbers are calculated by the Mesh Importer.
'''

panel_info_workflow = '''Workflow (Only available for Avastar Armatures)| Quickinfo:
* Presets for various Tasks:
  - Skin      : Preset for weighting your mesh
  - Pose      : Preset for posing your Mesh
  - Retarget: Preset for importing a BVH animation for your Mesh
  - Edit      : Preset for editing the Bones (for non human characters)
'''

panel_info_rigging = '''Rigging (Only available for Avastar Armatures)| Quickinfo:
* Bone Display Style: modifies the look&feel of the bones.
* Visibility: defines which bones are displayed
* Deform Bones: These Bones are used to animate your Mesh
'''

panel_info_weight_sources = '''Weight sourcess - only applicable for the Meshes strategy:
       All listed meshes are considered as influencing weight sources
       All visible meshes are used as copy sources(*)

    (*) Important: This is only applicable for the Meshes Strategy:
        For each vertex all copied weights are taken only from the closest mesh.
        If the closest mesh is listed but not visible, then no weights are copied
        for the vertex!'''

panel_info_skinning = '''Skinning|Skinning is the process of creating an association
between a Mesh (the Skin) and a Rig.
Quickinfo:

Bind to Armature: Assign selected Meshes to selected Armature
* Strategy: The method used to get the weigths.
  Note: Each weight strategy uses different intitial parameters

''' + panel_info_weight_sources

panel_info_weight_copy = '''Weight Copy|The weight Copy panel allows to copy or generate weights.
Quickinfo:

Update Weights: copy weights by using the selkected weight copy strategy
* Strategy: The method used to get the weigths.
  Note: Each weight strategy uses different intitial parameters
* Scope: The subset of bones for which weights shall be updated on the active mesh(*)

''' + panel_info_weight_sources

panel_info_materials = '''Material Settings (Only available for Avastar Meshes)| Quickinfo:
* None: Default material
* Female: female Starlight Textures
* Male: colored objects (no textures available)
* Custom: Placeholder (uses checker textures by default)
* Template: Template textures (for matching to SL System textures)
'''

panel_info_posing = \
'''Posing|Posing is the process of placing bones to create Poses
and animations for the Meshes bound to the Skeleton.

Quickinfo:

* Pose Position : The Rig can be posed and animated. Current Pose is shown
* Rest Position : the Rig's Restpose is shown. The rig can not be animated in this mode.
* Draw Joint Offsets: Draw Greasepencil lines to indicate joint offsets
  Only available when joints have been edited
* Armature Presets: complete joint position presets (experimental)
* Use Bind Pose: Use the current Pose as new Restpose

* Bone constraints:
  - Unlock the Secondlife bones to move them indepenedentlyfrom
  - Unlock the Animation bones to add joint positions
  - Unlock the Volume bones to allow moving them around (experimental)

* As bindpose: Store joints to use with Default SL Rig and Bind pose
* With Joints: Store joints to use with Joint positions
* Generate LSL: Script to apply restpose animation (for use bind pose)
* Export Restpose: to be used with the LSL Script
  Can also be generated by the Collada exporter.

'''

panel_info_fitting = '''Fitting|The Fitting Panel is used to create the weights
for the Collision Volume Bones.
This pannel is not needed for classic (mBone) weighting.

Fitting Presets: Predefined weight distributions
   - Fully Classic: Use only mBones (classic weighting)
   - Fully Fitted: Use only Collision Volume bones for weighting

* Generate Physics: Enables the Peck, Butt, Handles, Back bones and adds initial weights.
* Bone fitting Strength: Gradually shift bone weights between fully classic and fully fitted
* Adjust Shape: Use existing Shape key as target shape for the fitting weights (experimental)
* Smooth Weights: tries to make the mesh smoother by smoothing the weights.
'''

panel_info_appearance = '''Avatar Shape|We support the same shape slider system as you can find
in SL, OpenSim or other compatible worlds.

* Shape Presets: Your Shapes to be applied in one click.
* The orange stickman: Avatar default Shape
* The white Stickman: Avatar technical restpose Shape

* Bake to Mesh: Bake the current Shape key setting to Mesh
'''
panel_warning_appearance = '''Avatar Shape|This Armature has unsaved Joints!

You probably have opened the Armature Editor and moved some bones.
When you do this then you need to ensure the joint edits have been
stored before you can use the Avatar shape again.

You can store the joints when the Armature is in Edit mode.
Then open the Posing panel.
And Store Joint Edits.
'''

panel_info_tools = '''Tools|The Avastar Tools Panel is a container for tools which
do not fit anywhere else. You find the Avastar Tool Panel in the Tool Shelf,
in the Avastar tab.

* Vertex Tools: to find zero weighted unweighted vertices, etc...
* Most important tool: Freeze shape
'''

panel_info_weblinks = '''Weblinks|Some useful links into our documentation website
'''

panel_info_general_settings = '''General settings|We have taken great care to set these options
most reasonably. Please read the hover tool tips
to get more information about each option.
'''

panel_info_debug_settings = '''Debug settings|This section is only good for debugging!
Please do never change these settings unless you exactly know what you are doing'''

panel_info_credentials = '''Credentials|If you have an account on the Machinimatrix Website
and if you have registered your Avastar purchase then
you can get inbuilt Updates (see the Avastar Maintenance panel)
You can plakce your credentials here if you do not want to
add them each time you open the Maintenance panel.

Note: The credentials are not stored in your blend files,
but within your local file system. Hence it is safe to
forward blend files to other people.
'''

panel_info_visibility = '''Visibility|- Show Collada panel in tool Shelf
- Show Avatar Shape Panel in Properties Panel
- Set Addon Complexity (hide/unhide parts of user interface)
'''

panel_info_adaptive_sliders = '''Adaptive Sliders|This panel is deprecated.
PLEASE DO NOT USE.
The panel will be removed soon.
'''

panel_info_logging ='''Logging|Change the level of log reports
for various Addon Sections. This is only for debugging purpose.
You will change the settings only when requested.
'''

panel_info_character_presets = '''Rig Presets|Here you can define custom Rig templates for Avastar.

hints:

1.) Create Avatar (with Tris or with Quads)
2.) Rig Type Basic (Legacy Rig) or Externded (Bento Rig)
3.) Joint Type Pivot(recommended) or Pos(only rarely needed)

Whewn you reset to Factory (see above), then Avastar ensures 
the settings are restored like from a fresh Avastar Installation.
Note: The factory reset removes all of your own Custom Rig templates.
'''

panel_info_devkit_presets = '''Devkit Presets|Here you can add presets for your devkit characters.
You can define one preset entry for each devkit file.
Please fill in the options as necessary.
When in doubt please ask the devekit creator.
They should know what presets are needed.

hints:

1.) Devkit file type   : .dae (Collada) or .blend (Blender file)
2.) Devkit file content: One Rig ( + any number of bound meshes)
3.) Name and Short name can be whatever you like
4.) Scale Factor : to adjust the devkit size to the Avastar size
5.) Joint type: POS or PIVOT (ask the creator)
6.) Is Male: can be changed in the appearance panel
7.) Use Bind Pose:  can be changed in the appearance panel

Important: The meshes must be bound to the armature.
|/avastar-2/reference/advanced/devkits/users/'''

panel_info_devkit_manager = '''Info|Direct import of a foreign developer kit into an Avastar Rig.
You can configure additional entries in the Addon Properties panel.
'''

panel_info_register = '''Info|This panel is about your product registration.
If you have registered your product
and if you have created an account on our website,
then you can always check/download/install
the newest Update right away from this panel...
'''

panel_info_edited_joints = '''Joint State|This armature has been modified.
Note: This Armature contains at least one bone with a Joint Offset.
When you upload this rig to SL then do one of the 2 options below:

- enable the 'with joints' option to propagate the edited joints to SL
- enable the 'bind pose' option in this panel

Note: If you enable the bind pose option then the rig behaves effectively
equal to a Rig without Joint Offsets. It just happens to have a different
Rest position (bind pose)
'''

panel_info_clean_joints = '''Joint State|This armature is a clean vanilla Second Life Rig.
Note: This Armature does not contain any edited Joints.
When you upload this rig to SL then keep the 'with joints' option disabled.
'''

panel_info_negative_scales = '''Negative Scales|At least one of the selected Objects contains negative Object Scaling.
This can potentially damage your Face Normals.

Your Action (mandatory): Please cleanup your Object Scaling before binding.
'''

panel_info_scales = '''Scaled items|At least one of the selected Objects has Object Scaling.
This can potentially damage your Exported Objects.

Your Action (optional): Consider to cleanup your Object Scaling before binding.
'''

panel_info_rotations = '''Rotated items|At least one of the selected Objects has Object rotations.
This can potentially damage your Exported Objects.

Your Action (optional): Consider to cleanup your Object Rotations before binding.
'''

panel_info_rigversion = '''The Avastar Rig Version | Describes which Avastar version was used to create the Armature. 
The version number contains 4 parts:

- [V] Major version number (%s)
- [M] Minor version number (%s)
- [U] Update number  (%s)
- [ID] Rig ID (%s)

The rig is compatible with current Avastar version 
if at least one of the following matches apply:

- [V,M,U] match (same version numbers), 
- ID match (same rig ID)

For more detailed information, see online documentation (link is below)
Note: we do not support downgrades to older Avastar Versions.
However, it possibly might work.'''

panel_info_collada = '''Collada|The Avastar Collada Panel contains the user interface
for our own optimised Collada Exporter. The exporter implements a few special features
which can not be added to the Blender default Collada exporter. Here are the most
important export features:

* Modifiers: To swtich between exporting the modifier settings for Viewport or Render
* Texures: To specify which textuires shall be exported
* Advanced: A set of tools for special situations
* Unsupported: A set of tools which are not or no longer supported by SL

The Collada exporter also can export to different target systems:
Basic    : Old behavior for Second Life before Project Bento
Extended : Takes new Bones from Project Bento into account
Other    : Export to worlds other than Second Life, currently identical to Basic

Note: The Unsupported subpanel appears only when it is also enabled in the Addon panel.
Please check the Avastar documentation for more details.
|/help/io/collada-avastar/'''





avastar_copy_rig_bl_description = \
'''Convert/Update/Cleanup Rigs

- Single Rig: convert/Update to Avastar
- Multiple Rigs: Copy active to selected
- If rig is up to date: fix Missing bones,
  synchronize Control rig to Deform Rig,
  Align pole angles, ...'''

avastar_copy_rig_transferMeshes = "Migrate Child Meshes from Source armature to target Armature"

avastar_copy_rig_transferJoints = \
'''Migrate Joint positions from Source armature to target Armature
and calculate the joint offsets for the Rig.

Note:
The current slider settings and the current Skeleton both are taken
into account. You may optionally want to set the sliders to SL Restpose
(white stickman icon in appearance panel) to get reproducible results'''

avastar_copy_rig_mesh_repair = \
'''Reconstruct all missing Avastar Meshes.
This applies when Avastar meshes have been removed from the original rig

CAUTION: If your character has modified joints
then the regenerated Avastar meshes may become distorted!'''

avastar_copy_rig_show_offsets = \
'''Draw the offset vectors by using the Grease pencil.
The line colors are derived from the related Avastar Bone group colors.
This option is only good for testing when something goes wrong during the conversion'''

avastar_copy_rig_sl_bone_ends = \
'''Ensure that the bone ends are defined according to the SL Skeleton Specification
You probably need this when you import a Collada devkit
because Collada does not maintain Bone ends (tricky thing)

Hint:
Disable this option
- when you transfer a non human character
- or when you know you want to use Joint Positions'''





UpdateRigProp_snap_collision_volumes_description = \
'''Try to move the Collision Volumes to reasonable locations
relative to their related Deform Bones (experimental)
'''

UpdateRigProp_snap_attachment_points_description = \
'''Try to move the Attachment Points to reasonable locations
relative to their related Deform Bones (experimental)
'''

UpdateRigProp_fix_reference_meshes_description = \
'''Recalculate the Avatar Shape Reference Data.
Enable this option to make sure the Shape slideres use
proper reference meshes. This option should not be disabled,
unless you must preserve the current reference meshes.
'''

UpdateRigProp_preserve_bone_colors_description = \
'''Changed color settings of the Pose Bone Groups are preserved.
When disabled, then the Avastar default color themes are used
'''

UpdateRigProp_bone_repair_description = \
'''Reconstruct all missing bones.
This applies when bones have been removed from the original rig

IMPORTANT: when you convert a Basic Rig to an Extended Rig
then you should enable this option
Otherwise the extended (Bento) bones are not generated'''

UpdateRigProp_adjust_pelvis_description = \
'''Auto Align Pelvis and COG.

Pelvis, Tinker, and COG must be placed relative to each other:

- Pelvis and Tinker reverse match (head to tail, tail to head)
- Pelvis and mPelvis match
- COG head must be placed at Pelvis tail

Note: The Slider system only works when the bones are adjusted'''

UpdateRigProp_adjust_rig_description = \
'''Synchronize the Control Bones and the Deform Bones.

With Avastar-2 the slider system is much more integrated into the tool.
Because of this we have to ensure that the control bones and the deform
bones are aligned to each other. You have 2 choices:

- Align Control bones to match the Deform Bones
- Align Deform Bones to match the Control Bones'''

UpdateRigProp_align_to_deform_description = \
'''Specify who is the alignment master (pelvis or mPelvis):

-Pelvis: Move mPelvis to Pelvis (Use the green Pelvis bone as master)
-mPelvis:  Move Pelvis to mPelvis (Use the blue mPelvis bone as master)'''

UpdateRigProp_align_to_rig_description = \
'''Specify who is the alignment master (Deform Rig or Control Rig):

-Control Rig: Adjust the Deform Rig to match the Control Rig
-Deform Rig:  Adjust the Control Rig to match the Deform Rig'''

UpdateRigProp_adjust_origin = \
'''Matches the Avastar Root Bone with the Avastar Origin location.

Note: This adjustment is necessary to keep the Avatar shape working.
'''

UpdateRigProp_adjust_origin_armature = \
'''Move the Root Bone to the Armature Origin Location.
The location of the Armature in the scene is not affected'''

UpdateRigProp_adjust_origin_rootbone = \
'''Move the Armature Origin Location to the Root Bone.
The location of the Armature in the scene is not affected'''

UpdateRigProp_devkit_filepath = \
'''Enter the location of your Developerkit file.

Important: The developerkit file must contain exactly one 
armature and a set of Meshes parented or bound to the armature.

We currently support 2 file types:
- .blend
- .dae (Collada)

Note: This field is marked red when the filepath is missing
or does not point to a valid file'''

UpdateRigProp_devkit_shapepath = \
'''Enter the location of your Developerkit shape file (xml).

The Shape file contains the slider settings that shall be used
when a new rig is created by the developerkit manager.

Note: The developerkit shape file can be exported from the
SL Viewer or it can be exported from Avastar itself.

Note: This field can be kept empty'''

Avastar_rig_edit_check_description = \
'''Avastar Meshes should not be edited.
By default Avastar creates a popup when a user attempts to edit an Avastar mesh
You can disable this check to permanently suppress the popup message.

Note: We recommend you keep this option enabled!'''

Avastar_rig_cache_data_description = \
'''The Rig definition is stored on file.
By default Avastar loads and caches this data into memory when it
creates its first Avastar character. This option should never
be disabled unless for debugging purposes!
'''

Avastar_fix_after_load_description = \
'''Avastar needs its Rig data to be setup correct.
This may sometimes not be the case, especially when
you load an Avastar armature that was created by 
another (older) version of Avastar. Therefore 
Avastar inspects the data and fixes inconsistencies.

However: It may be possible that the attempt to fix the data
actually fails and makes the rig unusable. In that case you
can disable the automatic fixing after load, so that your file
loads with an unchanged rig. Then you can try to fix the 
Armature manually'''

AnimProp_Translation_description = \
'''Export bone translation channels.
Enable this option when you intend to create animations with translation components.
Note: the COG (and mPelvis) translations are always exported.

Good to know:
When your animation contains translation components we recommend
that you also test your animations with different appearance slider settings
to detect potential conflicts with the slider system(Avatar Shapes)

Note: Animations with only Rotation channels are less likely to conflict with the avatar shape'''

AnimProp_selected_actions_description = \
'''Export all Actions in the scene
When this option is enabled you get a list of all available actions
from which you can select the ones you want to export'''

ObjectProp_apply_armature_on_snap_rig_description = \
'''Apply the current Pose to all bound meshes (including the Avastar meshes) before Applying the pose to the Rig.

Note: The Apply Pose to Rig operator modifies the Restpose of the Armature.
When this flag is enabled, the bound objects will be frozen and later reparented to the new restpose

Important: When this option is enabled, the operator deletes all Shape keys from the bound objects!

Handle with Care!'''

RigProp_restpose_mode_description = \
'''The Armature has been locked to the SL Restpose.
Click to unlock the Avatar shape.

Note: You use this mode when you want to attach Mesh characters (or devkits)
which have originally been made with the simple SL Avatar rig.
Unlocking the SLiders keeps the Restpose intact until you modify the Slider settings'''

RigProp_rig_use_bind_pose_description = \
'''Only applies when your Rig does not use the Standard T-Pose:
Calculate the difference between the current restpose and a regular SL T-Pose.
This is used to import your Restpose to SL without actually converting it to a T-Pose.

Important: 
When disabled: enable 'with joints' when importing to SL
When enabled: keep 'with joints' disabled when importing to SL

We strongly recommend to use this option only if your restpose
is derived from a T-Pose by rotations only'''

RigProp_rig_lock_scales = \
'''Lock scaling for bones with edited joint positions.
The scale lock option implements the same behavior as the SL viewer when
a Rig is imported with the lock bone scale option enabled.

Note: This option only makes sense if your rig actually has edited joints.
for more information please see the Secondlife documentation 
Tip: Google for "bento Scale Locking Option"'''

RigProp_rig_rig_export_in_sl_restpose = \
'''Reset the Rig to Animesh Shape (white stickman) before exporting
Note: You might need to disable this mode to achieve compatibility with
models created before Avastar 2.5'''

RigProp_rig_export_visual_matrix_description = \
'''Export Bind Pose to Rig.
The current Restpose is recalculated for optimized joint offsets.
This export mode allows exporting modified rigs (e.g. A-Pose rigs)
and preserve fully functional SL Avatar shape if ever possible.

Important: You either must import the collada file with joint offsets,
or apply a reset animation when wearing your model'''

RigProp_rig_export_pose_reset_anim = \
'''Generate an animation to apply the correct restpose to the SL rig.
Avastar exports 2 files in this case: 

- filename.dae (always)
- filename_reset.anim (if option is set)

Import the .dae and the .anim to SL
and then place the .anim and an additional 
animation Resetter (LSL Script) into the model's inventory'''

RigProp_rig_export_pose_reset_script = \
'''Generate an animation Resetter (LSL Script) to auto apply a reset anim.
Avastar exports one additional file in this case: 

- filename.dae (always)
- filename_reset.lsl (if option is set)

Import the .dae and then drag the .lsl script into the model's inventory'''

RigProp_keep_edit_joints_description = \
'''Keep the Bone locations unchanged while removing the Joint data

Warning: When this option is set then the skeleton edits are preserved in Blender.
But any subsequent Slider Change resets the skeleton
regardless of the setting of this button!'''

RigProp_display_joint_values_description = \
'''List the modified Bone head locations (offsets).

If Heads, Tails and Values are all enabled:
For bones with head and tail modified, only the head data is shown'''

RigProp_hip_compatibility = \
'''Set Hips to match older Avastar versions

Older Avastar versions had a small error in the Hip Bones roll.
This error has been fixed by now, but possibly some creators have
worked around the error, so fixing the rig may cause damage to old
projects.
This option reverts the Hip Bone roll to how it was before the fix'''

SceneProp_collada_full_hierarchy = \
'''* Disabled: Avastar includes unweighted bones from the parent bone chain 
   but only if they have Edited Joint Offsets (optimal choice).
* Enabled: Avastar makes sure that all bones in the parent bone chain are exported
   regardless if they have weights or joint edits. (safest choice)

Note: Enable this option only when your target system supports partial rig import.
Partial rig import is a Second Life feature since Project Bento has been released'''

SceneProp_collada_complete_rig = \
'''Export the complete Rig
Important: only use this option when you want to transfer
the entire Rig to another 3D tool'''

SceneProp_collada_only_weighted = \
'''* Disabled: Do not check if bones are weighted.
* Enabled: Export only bones for which at least one mesh has weights.

Note: Enable this option only when your target system supports partial rig import.
Partial rig import is a Second Life feature since Project Bento has been released'''

SceneProp_collada_only_deform = \
'''* Disabled: Do not check the Deform flag
* Enabled: Export only bones which are marked as Deforming.

Note: Enable this option only when your target system supports partial rig import.
Partial rig import is a Second Life feature since Project Bento is released'''

SceneProp_collada_export_with_joints_description = \
'''Export the reference skeleton with stored joint positions.
Important: When you disable this option
then the skeleton is exported unchanged (to transfer data to other tools)
The sliders must be set to the Neutral Shape in this case!

This option is not used when you export to Tool Exchange'''

SceneProp_collada_assume_pos_rig_description = \
'''Assume the default restpose is a POS Rig, even if your exported rig
is a Pivot Rig (the default for Custom meshes)

WARNING: This option tricks the SL importer into not adding
artificial joint offsets to match a Pivot Rig to the SL Default Rig
for System Avatars. This option is fully experimental! 

Tip: If you depend on having a POS restpose then we recommend you use a POS Rig.
You can setup POS rigs in Avastar preferndes -> Character Definitions'''

SceneProp_snap_control_to_rig_description = \
'''The Bone Snap direction to be used when storing the joint edits.

- Disabled: Snap the Deform Rig to the Control rig
- Enabled : Snap the Control Rig to the Deform Rig'''

SceneProp_store_as_bind_pose_description = \
'''Store the current Rig definition as the new bind pose.

- Enabled: Store the Rig with 'Use bind pose' enabled
- Disabled: Store the Rig with 'Use bind pose' disabled

Tip: After storing the Joint positions, the Use Bind Pose option
in the Appeartance panel will automatically set to match this option'''

section_info_deform_bone_groups = \
'''Active Deform Groups|Please select all bone groups which the Weight map updater
shall treat as additional deform bones.

Explain:

When generating weights from bones, then each resulting weightmap is calculated
from all active deform bones. However, by default Avastar excludes some of the
regular deform bone groups when calculating automatic weight from Bones.

You can enable these bone groups additionaly. But be aware that
Your generated weight maps depend heavily on this choice!'''

avastar_reparent_armature_description = \
'''Adjust Reference Mesh and Bind shape

Use this operator to fix the Avastar shape data
after editing your Mesh.

Note: The Operator basically does:

%s

'''

avastar_reparent_armature_description_rebind = \
'''- Unbind from Armature
- Bind to Armature

Take care here: The original bindshape will be
permanently replaced by the current bindshape'''

avastar_reparent_armature_description_keep = \
'''- go to original bind shape
- Rebind Armature
- revert to current shape

In simple terms: The original Bindshape is retained
and the current shape is retained'''

avastar_reparent_mesh_description = \
'''Mismatch in Reference Mesh happens after editing the Mesh or
upgrading the Rig. Avastar also indicates a mismatch when you 
load an old rig/mesh combination with missing meta information.

This is equal to: Unbind -> Bind to Armature'''

avastar_weld_weights_from_rigged_description = \
'''Adjust weights for vertices adjacent to other Mesh objects.

The weights of selected (or all) vertices of the active Mesh are adjusted
to match the closest vertices from other meshes.

Note: Only Meshes are taken into account which are rigged to the same Armature'''

avastar_www_error_popup_text = \
'''%s.
The reported Error Code was: %d:(%s)

possible codes:

- 400 Database not online
- 405 No wpuser defined
- 406 No product defined
- 407 No Version provided
- 409 No purchaseid for given user

Important: Please use your Machinimatrix account name to login.
Just using the email address will log you in, but you can not use
it for downloading anything from the server.

'''

avastar_apply_as_restpose_text= \
'''Apply pose as new Rest pose.

- As Bindpose: SL-Rig with current Pose and Avatar shape
- With Joints: Joint Positions

Tip:

Changing here between 'As Bindpose' and 'With Joints'
preserves the bone locations'''

UpdateRigProp_transferJoints_text = \
'''Migrate Joint positions from Source armature to target Armature
and calculate the joint offsets for the Rig.

Note:
The current slider settings and the current Skeleton both are taken 
into account. You may optionally want to set the sliders to SL Restpose 
(white stickman icon in appearance panel) to get reproducible results'''

UpdateRigProp_up_axis_text = \
'''Which Axis is used as Up axis in the imported Rig

* Devkit from blendfile: uses Z (probably)
* Devkit from Avastar Rig: uses Z
* Devkit from Maya: typically uses Y (see hint below)

Hint: You find the used up axis in the developer kit collada file <up_axis> tag
When in doubt, then ask the devkit creator'''

prop_with_listed_avastar_meshes = \
'''Copy weights from entries in the Weight sources selection (See the list above)

enabled:  copy from all items in the list, regardless if they are selected or not.
disabled: Copy only from Selected items in the list'''

Operator_apply_shape_sliders = \
'''Freeze visual shape to all custom meshes and rebind:

- applies and removes all shape keys
- conserves all mesh edits
- rebinds frozen meshes back to armature

Tip: You can undo with CTRL Z'''

### Notifications

M001_limited_weightcount = "M001 : Limited weightcount to 4 for %d verts in Mesh %s "
M002_zero_weights        = "M002 : Found %d zero weighted verts in %s "
M003_undefined_weightmap = "M003 : Bone %s is not defined in SL. %d weights not exported "
M004_weight_limit_exceed = "M004 : The Mesh %s uses %d Bones while SL limit is %d Bones per Mesh "
M005_high_tricount       = "M005 : High Tricount %d in material face [%s] of mesh %s "
M006_image_not_found     = "M006 : Image [%s] from material [%s]: not found on disk "
M007_image_copy_failed   = "M007 : Image copy failed "
M008_not_an_avastar      = "M008 : Armature [%s] not an Avastar Rig (can't export mesh [%s]) "
M009_outdated_reference  = "M009 : Out of Date Reference for '%s'. (need rebind/repair) "
M010_no_image_texture    = "M010 : No image assigned to mat:'%s' tex:'%s' "
M011_msg_undeform_bones  = "M011 : %d weightgroups assigned to non deforming bones in Mesh '%s' "
M012_msg_unweighted_verts= "M012 : %d unweighted vertices in Mesh '%s'] "
M013_msg_zero_verts      = "M013 : %d verts have a weight sum of 0 in Mesh '%s' "
M014_msg_empty_selection = "M014 : No objects selected of type '%s' (Nothing to export) "

### Code pieces

pose_reset_script_lsl = '''/* ====================================================================
 Copyright 2018 Machinimatrix

 This file is part of Avastar and may be used in combination with any
 rigged Mesh that was created by Avastar.

 You may redistribute this script with NOMOD permission within
 your Mesh Creations. But publishing this script or redistributing
 it in readable form is explicitly not allowed.

 Avastar is distributed under an End User License Agreement and you
 should have received a copy of the license together with Avastar.
 The license can also be obtained from http://www.machinimatrix.org/
 ====================================================================== 
*/
string animation;

request_permissions()
{
    key owner = llGetOwner();
    llRequestPermissions(owner ,PERMISSION_TRIGGER_ANIMATION);    
}

integer fetch_animation ()
{
    animation = llGetInventoryName(INVENTORY_ANIMATION,0);
    return (animation != "");
}

start_animation()
{
    if (animation) {
        if(llGetPermissions() & PERMISSION_TRIGGER_ANIMATION){
            llStartAnimation(animation);
        }
    }
}

stop_animation()
{
    if (animation) {
        if(llGetPermissions()&PERMISSION_TRIGGER_ANIMATION){
             llStopAnimation(animation);
        }
    }
}

default
{
    state_entry()
    {
        request_permissions();
    }

    run_time_permissions(integer perm){
        if (fetch_animation()) {
            start_animation();
        }
    }

    changed(integer change){
        if(change & CHANGED_INVENTORY){
            if (fetch_animation()) {
                start_animation();
            }
        }
        else if ((change & CHANGED_TELEPORT)) {
            start_animation();
        }
    }

    attach(key id){
         //if someone is wearing me
        if(id){
            request_permissions();
        }
        else {
            stop_animation();
        }
    }
}
'''

classes = (

)

def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)
        registerlog.info("Registered messages:%s" % cls)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
        registerlog.info("Unregistered messages:%s" % cls)
