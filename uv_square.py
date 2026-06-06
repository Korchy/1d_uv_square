# Nikita Akimov
# interplanety@interplanety.org
#
# GitHub
#    https://github.com/Korchy/1d_uv_square


import bmesh
import bpy
from bpy.types import Operator, Panel
from bpy.utils import register_class, unregister_class
from math import ceil, floor
from mathutils import Vector
from mathutils.geometry import barycentric_transform

bl_info = {
    "name": "1D UV Square",
    "description": "Create initial UV-quad around all vertices of selected triangle",
    "author": "Nikita Akimov, Paul Kotelevets",
    "version": (1, 0, 0),
    "blender": (2, 79, 0),
    "location": "View3D > Tool panel > 1D > UV Square",
    "doc_url": "https://github.com/Korchy/1d_uv_square",
    "tracker_url": "https://github.com/Korchy/1d_uv_square",
    "category": "All"
}


# MAIN CLASS

class UVSquare:

    @classmethod
    def uv_square(cls, context):
        # create polygons around all vertices of selected triangle with initial uv-size
        # current mode
        mode = context.active_object.mode
        if context.active_object.mode == 'EDIT':
            bpy.ops.object.mode_set(mode='OBJECT')
        # switch to face selection mode
        context.tool_settings.mesh_select_mode = (False, False, True)
        # working with active face
        active_face_id = context.object.data.polygons.active
        if active_face_id > -1:
            bm = bmesh.new()
            bm.from_mesh(context.active_object.data)
            bm.verts.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            uv_layer = cls._active_uv_layer(bm)
            bm_active_face = next((_face for _face in bm.faces if _face.index == active_face_id), None)
            if bm_active_face:
                world_matrix_inv = context.object.matrix_world.inverted()
                # get points coordinates of active face and that face on the uv
                dest_triangle_co = []
                src_triangle_co = []
                uv_points = cls._uv_points_bm([bm_active_face], uv_layer) # [(BMVert, uv-point), ...]
                # get min-max values for uv-points coordinates to make a quad grid
                mm = cls._min_max_x_y([p[1] for p in uv_points])
                # create quads grid between min and max values
                grid_verts = []
                grid_faces = []
                for x_offset in range(mm['min_x'], mm['max_x']):
                    for y_offset in range(mm['min_y'], mm['max_y']):
                        quad_cos = [world_matrix_inv * Vector((0.0 + x_offset, 0.0 + y_offset, 0.0)),
                                    world_matrix_inv * Vector((1.0 + x_offset, 0.0 + y_offset, 0.0)),
                                    world_matrix_inv * Vector((1.0 + x_offset, 1.0 + y_offset, 0.0)),
                                    world_matrix_inv * Vector((0.0 + x_offset, 1.0 + y_offset, 0.0))
                                    ]
                        quad_verts = [bm.verts.new(pos) for pos in quad_cos]
                        face = bm.faces.new(quad_verts)
                        # set uv coordinates for created quad
                        uv_coords = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
                        for loop, uv in zip(face.loops, uv_coords):
                            loop[uv_layer].uv = uv
                        # append to grid vertices for future transformations
                        grid_verts.extend(quad_verts)
                        grid_faces.append(face)
                for uv_point in uv_points:
                    src_triangle_co.append(uv_point[0].co)
                    dest_triangle_co.append(world_matrix_inv * Vector((uv_point[1].uv.x, uv_point[1].uv.y)).to_3d())
                # transform all grid vertices coordinates by transformation between dest_triangle_co and src_triangle_co
                for vertex in grid_verts:
                    new_co = barycentric_transform(vertex.co, *dest_triangle_co, *src_triangle_co)
                    vertex.co = new_co
                # check normals of source triangle and one of grid quads
                bm.normal_update()
                normals_dot = bm_active_face.normal.dot(grid_faces[0].normal)
                if normals_dot < 0:
                    for grid_face in grid_faces:
                        grid_face.normal_flip()
                    bm.normal_update()
            # save changed data to mesh
            bm.to_mesh(context.active_object.data)
            bm.free()
        else:
            print('no active face')
        # return mode back
        bpy.ops.object.mode_set(mode=mode)

    @staticmethod
    def _active_uv_layer(obj):
        # get active uv-layer (UV Map)
        if isinstance(obj, bmesh.types.BMesh):
            # from bmesh object
            return obj.loops.layers.uv.active
        else:
            # from object
            return obj.data.uv_layers.active

    @staticmethod
    def _uv_points_bm(bm_faces_list, uv_layer):
        # get list of UV points for mesh BM-faces from faces_list
        # [(BMVert, uv_point), (BMVert, uv_point), ...]
        return [(loop.vert, loop[uv_layer]) for _face in bm_faces_list for loop in _face.loops]

    @staticmethod
    def _min_max_x_y(uv_points):
        # find min and max values (rounded to 1) by x- and y-axis for uv points list
        x, y = zip(*(p.uv for p in uv_points))
        return {
            'min_x': floor(min(x)),
            'min_y': floor(min(y)),
            'max_x': ceil(max(x)),
            'max_y': ceil(max(y))
        }

    @staticmethod
    def ui(layout, context, area):
        # ui panels
        # uv square
        box = layout.box().column()
        box.label(text='UV Square')
        box.operator(
            operator='uvsquare.uv_square',
            icon='MOD_MESHDEFORM'
        )


# OPERATORS

class UVSquare_OT_uvsquare(Operator):
    bl_idname = 'uvsquare.uv_square'
    bl_label = 'UV Square'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        UVSquare.uv_square(
            context=context
        )
        return {'FINISHED'}


# PANELS

class UVSquare_PT_panel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_label = 'UV Square'
    bl_category = '1D'

    def draw(self, context):
        UVSquare.ui(
            layout=self.layout,
            context=context,
            area='VIEWPORT'
        )


# REGISTER

def register(ui=True):
    register_class(UVSquare_OT_uvsquare)
    if ui:
        register_class(UVSquare_PT_panel)


def unregister(ui=True):
    if ui:
        unregister_class(UVSquare_PT_panel)
    # butch clean
    unregister_class(UVSquare_OT_uvsquare)


if __name__ == "__main__":
    register()
