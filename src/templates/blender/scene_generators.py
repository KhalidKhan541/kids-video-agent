"""Fast Blender scene generators — optimized for quick renders."""

from typing import Any


def _header(proj: dict, scene: dict, config: dict, idx: int) -> str:
    duration = scene.get("duration_seconds", 10)
    fps = config.get("fps", 24)
    res = config.get("resolution", (1280, 720))
    total = duration * fps
    return f'''
import bpy, math, random, os
bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.render.resolution_x = {res[0]}; scene.render.resolution_y = {res[1]}
scene.render.fps = {fps}; scene.render.frame_end = {total}
scene.render.engine = "BLENDER_EEVEE"
scene.render.film_transparent = False
scene.render.ffmpeg.format = "MPEG4"; scene.render.ffmpeg.codec = "H264"
scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
scene.render.image_settings.file_format = "FFMPEG"
scene.render.filepath = os.path.join(os.path.dirname(bpy.data.filepath) or os.getcwd(), "scene_{idx+1:03d}.mp4")
'''


def generate_simple_scene(scene: dict, config: dict, proj: dict, idx: int) -> str:
    dur = scene.get("duration_seconds", 10)
    total = dur * config.get("fps", 24)
    code = _header(proj, scene, config, idx)

    code += f'''
random.seed({idx + 42})
bpy.data.worlds["World"].use_nodes = True
bpy.data.worlds["World"].node_tree.nodes["Background"].inputs["Color"].default_value = (0.05, 0.1, 0.3, 1)

# Camera
cam = bpy.data.cameras.new("C"); co = bpy.data.objects.new("C", cam)
co.location = (0, -10, 3); co.rotation_euler = (1.047, 0, 0)
scene.camera = co; bpy.context.collection.objects.link(co)

for f in range(0, {total}+1, 6):
    t = f/{total}
    co.location.x = 1.5 * math.sin(t * math.pi * 2)
    co.keyframe_insert(data_path="location", frame=f)

# Sun
bpy.ops.object.light_add(type="SUN", location=(5,5,10)); bpy.context.active_object.data.energy = 3

# 8 twinkling stars (big keyframe spacing)
for s in range(8):
    x = random.uniform(-7,7); y = random.uniform(-3,7); z = random.uniform(1,5)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=random.uniform(0.12,0.25), location=(x,y,z))
    star = bpy.context.active_object; star.name = f"S_{{s}}"
    m = bpy.data.materials.new(f"M_{{s}}"); m.use_nodes = True
    col = random.choice([(1,0.4,0.7,1),(0.5,0.7,1,1),(1,1,0.6,1),(0.5,1,0.5,1)])
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = col
    m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 0.3
    star.data.materials.append(m)
    for f in range(0, {total}+1, 6):
        sc = 1 + 0.3 * math.sin(f * 0.08 + s * 2)
        star.scale = (sc, sc, sc); star.keyframe_insert(data_path="scale", frame=f)

# Center torus
bpy.ops.mesh.primitive_torus_add(major_radius=0.8, minor_radius=0.2, location=(0,0,0.8))
ring = bpy.context.active_object
m = bpy.data.materials.new("R"); m.use_nodes = True
m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (1,0.85,0.2,1)
m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 0.5
ring.data.materials.append(m)
for f in range(0, {total}+1, 4):
    ring.rotation_euler.z = f * 0.03; ring.keyframe_insert(data_path="rotation_euler", frame=f)
'''
    return code


def generate_character_scene(scene: dict, config: dict, proj: dict, idx: int) -> str:
    dur = scene.get("duration_seconds", 10)
    total = dur * config.get("fps", 24)
    count = config.get("character_count", 2)
    code = _header(proj, scene, config, idx)

    code += f'''
random.seed({idx + 99})
bpy.data.worlds["World"].use_nodes = True
bpy.data.worlds["World"].node_tree.nodes["Background"].inputs["Color"].default_value = (0.25,0.4,0.7,1)

# Camera
cam = bpy.data.cameras.new("C"); co = bpy.data.objects.new("C", cam)
co.location = (0,-8,2.5); co.rotation_euler = (1.047,0,0)
scene.camera = co; bpy.context.collection.objects.link(co)

# Ground
bpy.ops.mesh.primitive_plane_add(size=14, location=(0,0,-0.5))
g = bpy.context.active_object
gm = bpy.data.materials.new("G"); gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.15,0.6,0.15,1)
g.data.materials.append(gm)

bpy.ops.object.light_add(type="SUN", location=(5,5,10)); bpy.context.active_object.data.energy = 3.5

# Characters
colors = [(1,0.35,0.55,1),(0.35,0.65,1,1),(1,1,0.3,1),(0.4,1,0.4,1)]
for c in range({count}):
    x = (c - {count}/2 + 0.5) * 2.5
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=(x,0,0.5))
    body = bpy.context.active_object; body.name = f"B_{{c}}"
    bm = bpy.data.materials.new(f"BM_{{c}}"); bm.use_nodes = True
    bm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = colors[c % len(colors)]
    bm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.3
    body.data.materials.append(bm)

    # Eyes
    for s in [-1,1]:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.08, location=(x + s*0.14,0.4,0.65))
        eye = bpy.context.active_object; eye.parent = body
        em = bpy.data.materials.new(f"EM_{{c}}_{{s}}"); em.use_nodes = True
        em.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (1,1,1,1)
        eye.data.materials.append(em)

    # Animation (big keyframe spacing)
    for f in range(0, {total}+1, 4):
        body.location.z = 0.5 + 0.15 * abs(math.sin(f * 0.05 + c * 1.5))
        body.keyframe_insert(data_path="location", frame=f)
'''
    return code


def generate_nature_scene(scene: dict, config: dict, proj: dict, idx: int) -> str:
    dur = scene.get("duration_seconds", 10)
    total = dur * config.get("fps", 24)
    code = _header(proj, scene, config, idx)

    code += f'''
random.seed({idx + 77})
bpy.data.worlds["World"].use_nodes = True
bpy.data.worlds["World"].node_tree.nodes["Background"].inputs["Color"].default_value = (0.35,0.55,0.9,1)

cam = bpy.data.cameras.new("C"); co = bpy.data.objects.new("C", cam)
co.location = (0,-12,5); co.rotation_euler = (1.047,0,0)
scene.camera = co; bpy.context.collection.objects.link(co)

bpy.ops.mesh.primitive_plane_add(size=20, location=(0,0,-0.5))
g = bpy.context.active_object
gm = bpy.data.materials.new("G"); gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.25,0.65,0.2,1)
g.data.materials.append(gm)

bpy.ops.object.light_add(type="SUN", location=(5,5,10)); bpy.context.active_object.data.energy = 4

# Trees (simple)
for t in range(3):
    x = random.uniform(-6,6); y = random.uniform(-2,4)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=1.2, location=(x,y,0.1))
    bpy.ops.mesh.primitive_cone_add(radius_1=0.5, depth=0.6, location=(x,y,0.8))
    fol = bpy.context.active_object
    fm = bpy.data.materials.new(f"F_{{t}}"); fm.use_nodes = True
    fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.15,0.5+0.2*random.random(),0.08,1)
    fol.data.materials.append(fm)

# Flowers
for _ in range(10):
    x = random.uniform(-7,7); y = random.uniform(-1,5)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.06, location=(x,y,0))
    fm = bpy.data.materials.new(f"FM_{{_}}"); fm.use_nodes = True
    fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (
        random.uniform(0.7,1), random.uniform(0.3,0.8), random.uniform(0.5,1), 1)
    bpy.context.active_object.data.materials.append(fm)
'''
    return code


def generate_abstract_scene(scene: dict, config: dict, proj: dict, idx: int) -> str:
    dur = scene.get("duration_seconds", 10)
    total = dur * config.get("fps", 24)
    code = _header(proj, scene, config, idx)

    code += f'''
random.seed({idx + 200})
bpy.data.worlds["World"].use_nodes = True
bpy.data.worlds["World"].node_tree.nodes["Background"].inputs["Color"].default_value = (0.02,0.02,0.08,1)

cam = bpy.data.cameras.new("C"); co = bpy.data.objects.new("C", cam)
co.location = (0,-10,2); co.rotation_euler = (1.2,0,0)
scene.camera = co; bpy.context.collection.objects.link(co)

bpy.ops.object.light_add(type="SUN", location=(5,5,10)); bpy.context.active_object.data.energy = 2

# Icosahedron
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=(0,0,0.5))
ico = bpy.context.active_object
m = bpy.data.materials.new("I"); m.use_nodes = True
m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.8,0.2,0.5,1)
m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 0.6
ico.data.materials.append(m)
for f in range(0, {total}+1, 4):
    ico.rotation_euler.x = f*0.02; ico.rotation_euler.y = f*0.03
    ico.keyframe_insert(data_path="rotation_euler", frame=f)

# 2 orbiting rings
for ri in range(2):
    r = 1.5 + ri*0.5
    bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=0.04, location=(0,0,0.5))
    ring = bpy.context.active_object
    rm = bpy.data.materials.new(f"RM_{ri}"); rm.use_nodes = True
    rm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = random.choice([(1,0.3,0.6,1),(0.3,0.6,1,1)])
    rm.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 0.5
    ring.data.materials.append(rm)
    speed = 0.015 + ri*0.005
    for f in range(0, {total}+1, 4):
        ring.rotation_euler.z = f * speed * (1 if ri%2==0 else -1)
        ring.keyframe_insert(data_path="rotation_euler", frame=f)
'''
    return code


SCENE_GENERATORS = {
    "simple": generate_simple_scene,
    "character": generate_character_scene,
    "nature": generate_nature_scene,
    "abstract": generate_abstract_scene,
}
