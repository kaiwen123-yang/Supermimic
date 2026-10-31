"""Explicit G1 model construction and joint-name based conventions.

The robot mesh/geometry is from pinned mjlab; gains/default pose/action scales
follow pinned BeyondMimic. This is a documented reconstruction, not the authors'
unreleased SuperMimic XML.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
JOINTS = [
    "left_hip_pitch_joint", "left_hip_roll_joint", "left_hip_yaw_joint", "left_knee_joint",
    "left_ankle_pitch_joint", "left_ankle_roll_joint",
    "right_hip_pitch_joint", "right_hip_roll_joint", "right_hip_yaw_joint", "right_knee_joint",
    "right_ankle_pitch_joint", "right_ankle_roll_joint",
    "waist_yaw_joint", "waist_roll_joint", "waist_pitch_joint",
    "left_shoulder_pitch_joint", "left_shoulder_roll_joint", "left_shoulder_yaw_joint", "left_elbow_joint",
    "left_wrist_roll_joint", "left_wrist_pitch_joint", "left_wrist_yaw_joint",
    "right_shoulder_pitch_joint", "right_shoulder_roll_joint", "right_shoulder_yaw_joint", "right_elbow_joint",
    "right_wrist_roll_joint", "right_wrist_pitch_joint", "right_wrist_yaw_joint",
]
TRACKED_BODIES = [
    "pelvis", "left_hip_roll_link", "left_knee_link", "left_ankle_roll_link",
    "right_hip_roll_link", "right_knee_link", "right_ankle_roll_link", "torso_link",
    "left_shoulder_roll_link", "left_elbow_link", "left_wrist_yaw_link",
    "right_shoulder_roll_link", "right_elbow_link", "right_wrist_yaw_link",
]


def joint_parameters(name: str) -> dict[str, float]:
    if "hip_roll" in name or "knee" in name:
        inertia, effort, speed = 0.025101925, 139.0, 20.0
    elif "hip_pitch" in name or "hip_yaw" in name or name == "waist_yaw_joint":
        inertia, effort, speed = 0.010177520, 88.0, 32.0
    elif "ankle" in name or name in ("waist_roll_joint", "waist_pitch_joint"):
        inertia, effort, speed = 2 * 0.003609725, 50.0, 37.0
    elif "wrist_pitch" in name or "wrist_yaw" in name:
        inertia, effort, speed = 0.00425, 5.0, 22.0
    else:
        inertia, effort, speed = 0.003609725, 25.0, 37.0
    natural_frequency = 10 * 2 * math.pi
    kp = inertia * natural_frequency**2
    kd = 4 * inertia * natural_frequency
    q0 = 0.0
    for part, value in (("hip_pitch", -0.312), ("knee", 0.669), ("ankle_pitch", -0.363),
                        ("elbow", 0.6), ("shoulder_pitch", 0.2)):
        if part in name:
            q0 = value
    if name == "left_shoulder_roll_joint":
        q0 = 0.2
    if name == "right_shoulder_roll_joint":
        q0 = -0.2
    return {"armature": inertia, "effort_limit": effort, "velocity_reference_limit": speed,
            "kp": kp, "kd": kd, "q0": q0, "action_scale": 0.25 * effort / kp}


def build_model() -> Path:
    lock = json.loads((ROOT / "configs/sources.lock.json").read_text())
    source = ROOT / ".cache/upstream/mjlab" / lock["mjlab_asset"]["path"] / "xmls/g1.xml"
    tree = ET.parse(source)
    xml = tree.getroot()
    xml.find("compiler").set("meshdir", str((source.parent / "assets").resolve()))
    for element in list(xml.findall("option")):
        xml.remove(element)
    ET.SubElement(xml, "option", timestep="0.005", integrator="implicitfast", solver="Newton",
                  iterations="10", ls_iterations="10", cone="elliptic", impratio="1")
    ET.SubElement(xml, "statistic", center="0 0 0.8", extent="2.5")
    world = xml.find("worldbody")
    ET.SubElement(world, "geom", name="floor", type="plane", size="0 0 0.05",
                  friction="1 0.005 0.0001", rgba="0.72 0.75 0.78 1", condim="3")
    ET.SubElement(world, "light", pos="0 -3 5", dir="0 0 -1", directional="true")
    for geom in xml.iter("geom"):
        name = geom.get("name", "")
        if name.endswith("_collision"):
            foot = "_foot" in name
            geom.set("condim", "3" if foot else "1")
            geom.set("priority", "1" if foot else "0")
            geom.set("friction", "1 0.005 0.0001")
    for section in list(xml.findall("actuator")) + list(xml.findall("keyframe")):
        xml.remove(section)
    actuator = ET.SubElement(xml, "actuator")
    params = {}
    for joint in xml.findall(".//body/joint"):
        name = joint.attrib["name"]
        if name not in JOINTS:
            raise RuntimeError(f"Unexpected G1 joint {name}")
        p = joint_parameters(name)
        params[name] = p
        joint.set("armature", str(p["armature"]))
        joint.set("damping", "0")
        joint.set("frictionloss", "0")
    for name in JOINTS:
        p = params[name]
        ET.SubElement(actuator, "general", name=name + "_pd", joint=name, gaintype="fixed",
                      biastype="affine", gainprm=str(p["kp"]), biasprm=f"0 {-p['kp']} {-p['kd']}",
                      forcelimited="true", forcerange=f"{-p['effort_limit']} {p['effort_limit']}",
                      ctrllimited="false")
    target = ROOT / "data/robot/g1.xml"
    target.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(xml)
    tree.write(target, encoding="utf-8", xml_declaration=True)
    model = mujoco.MjModel.from_xml_path(str(target))
    names = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, i) for i in range(1, model.njnt)]
    if names != JOINTS or (model.nq, model.nv, model.nu) != (36, 35, 29):
        raise RuntimeError(f"Unexpected joint layout: {names}")
    metadata = {
        "source": lock["mjlab_asset"], "source_xml_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "generated_xml_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "mujoco_version": mujoco.__version__, "nq": model.nq, "nv": model.nv, "nu": model.nu,
        "joint_names": JOINTS, "tracked_bodies": TRACKED_BODIES, "parameters": params,
        "root_reward_and_termination_body": "pelvis",
        "choice_note": "SuperMimic Appendix A explicitly names pelvis for root termination. Use pelvis consistently; BeyondMimic torso anchor is not silently substituted.",
        "velocity_limit_note": "Published limits are recorded for diagnostics; no artificial velocity clipping is applied to MuJoCo qvel.",
        "training_control_hz": 50, "physics_dt": 0.005,
    }
    (target.parent / "model_manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return target


def load_model() -> mujoco.MjModel:
    path = ROOT / "data/robot/g1.xml"
    if not path.exists():
        raise FileNotFoundError("Run scripts/prepare_lafan1.py first")
    return mujoco.MjModel.from_xml_path(str(path))


def joint_arrays() -> dict[str, np.ndarray]:
    params = [joint_parameters(name) for name in JOINTS]
    return {key: np.array([p[key] for p in params], dtype=np.float64) for key in params[0]}
