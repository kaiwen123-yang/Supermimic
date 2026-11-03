"""Render fixed-checkpoint physical replay records; rendering never advances physics."""
from pathlib import Path
import argparse
import json
import subprocess
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT, FPS = 512, 384, 10
CANVAS = (WIDTH * 3, 688)
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT = ImageFont.truetype(FONT_PATH, 18)
SMALL = ImageFont.truetype(FONT_PATH, 15)
TITLE = ImageFont.truetype(FONT_PATH, 23)
COLORS = [(82, 221, 181), (249, 169, 79), (94, 178, 255)]


def encoder(path):
    return subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{CANVAS[0]}x{CANVAS[1]}",
        "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-threads", "2",
        "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path)],
        stdin=subprocess.PIPE)


def render_model():
    xml = ET.parse(ROOT / "data/robot/g1.xml").getroot()
    assets = xml.find("asset")
    if assets is None:
        assets = ET.SubElement(xml, "asset")
    ET.SubElement(assets, "texture", name="video_grid", type="2d", builtin="checker", width="512", height="512",
                  rgb1="0.79 0.82 0.86", rgb2="0.65 0.70 0.76")
    ET.SubElement(assets, "material", name="video_ground", texture="video_grid", texrepeat="1 1", texuniform="true")
    xml.find(".//geom[@name='floor']").set("material", "video_ground")
    model = mujoco.MjModel.from_xml_string(ET.tostring(xml, encoding="unicode"))
    model.vis.global_.offwidth, model.vis.global_.offheight = WIDTH, HEIGHT
    model.vis.headlight.ambient[:] = [0.4, 0.4, 0.4]
    return model


def main():
    global CANVAS
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("reference_heading", type=Path)
    parser.add_argument("robot_root", type=Path, nargs="?")
    parser.add_argument("--labels", nargs="+", default=["A reference_heading", "B robot_root"])
    parser.add_argument("--motions", nargs="+")
    args = parser.parse_args()
    directory = args.directory.absolute()
    output = directory / "videos"
    output.mkdir(exist_ok=False)
    evaluation_dirs = [args.reference_heading] + ([args.robot_root] if args.robot_root else [])
    count = len(evaluation_dirs)
    args.labels = args.labels[:count]
    CANVAS = (WIDTH * (count + 1), 688)
    evaluations = [json.loads((p / "evaluation.json").read_text()) for p in evaluation_dirs]
    names = args.motions or ["walk1_subject1", "run1_subject5", "dance2_subject3", "jumps1_subject1", "fallAndGetUp1_subject5"]
    reports = [{c["motion"]: c for c in e["clips"]} for e in evaluations]
    model = render_model()
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    renderer = mujoco.Renderer(model, height=HEIGHT, width=WIDTH)
    original_rgba = model.geom_rgba.copy()
    body_geoms = model.geom_bodyid != 0
    camera = mujoco.MjvCamera()
    camera.type = mujoco.mjtCamera.mjCAMERA_FREE
    camera.azimuth, camera.elevation = 135, -20
    assets, overview_frames, contact_images = [], [], []
    for motion_index, name in enumerate(names):
        records = [np.load(p/"trajectories"/(name+".npz"), allow_pickle=False) for p in evaluation_dirs]
        ends = [reports[i][name]["executed_steps"] for i in range(count)]
        full_steps = reports[0][name]["full_reference_steps"]
        last = max(ends)
        assert last <= full_steps
        poses = [r["qpos"] for r in records]
        reference = records[int(np.argmax(ends))]["reference_qpos"]
        last = min(last, len(reference) - 1)
        frame_count = int(np.ceil((last * 0.02 + 2) * FPS)) + 1
        filename = name + ("_comparison.mp4" if count == 2 else "_c0_final.mp4")
        process = encoder(output / filename)
        static_xy = [reference[:last+1:25, :2]] + [pose[:end+1:25, :2] for pose,end in zip(poses,ends)]
        all_xy = np.concatenate(static_xy)
        low, high = all_xy.min(0) - 0.5, all_xy.max(0) + 0.5
        chart_width = 650 if count == 2 else 410
        text_x = 730 if count == 2 else 470
        scale = min(chart_width / max(high[0]-low[0], 1), 112 / max(high[1]-low[1], 1))

        def point(xy):
            return (int(25 + (xy[0]-low[0])*scale), int(663 - (xy[1]-low[1])*scale))

        frozen = [None] * count
        overview_segment = []
        for video_frame in range(frame_count):
            step = min(round(video_frame / FPS / 0.02), last)
            ref = reference[step]
            robot_q = [p[min(step, end)] for p, end in zip(poses, ends)]
            # All running panels use the same world camera. A terminated policy's
            # image freezes at failure, clearly labeled, instead of being reset.
            centers = [ref[:3]] + [q[:3] for q, end in zip(robot_q, ends) if step <= end]
            center = np.mean(centers, axis=0)
            camera.lookat[:] = [center[0], center[1], 0.72]
            spread = max(np.linalg.norm(c[:2] - center[:2]) for c in centers)
            camera.distance = max(3.8, 3.8 + 1.7 * spread)
            panels = []
            for index, qpos in enumerate([ref, *robot_q]):
                if index and step >= ends[index-1] and frozen[index-1] is not None:
                    panels.append(frozen[index-1])
                    continue
                assert np.isfinite(qpos).all(), (name, step, index)
                data.qpos[:] = qpos
                mujoco.mj_kinematics(model, data)
                model.geom_rgba[:] = original_rgba
                if index == 0:
                    model.geom_rgba[body_geoms] = [0.22, 0.76, 0.58, 1.0]
                renderer.update_scene(data, camera=camera)
                panel = Image.fromarray(renderer.render())
                panels.append(panel)
                if index and step >= ends[index-1]:
                    frozen[index-1] = panel.copy()
            canvas = Image.new("RGB", CANVAS, (15, 22, 34))
            draw = ImageDraw.Draw(canvas)
            draw.text((18, 12), f"G1  |  {name}", font=TITLE, fill="white")
            draw.text((CANVAS[0]-516, 15), f"t = {step*.02:6.2f} s    |    1x speed", font=FONT, fill=(210, 219, 230))
            labels = ["REFERENCE  |  kinematic", *[f"{label} | i{e['iteration']}" for label,e in zip(args.labels,evaluations)]]
            for index, panel in enumerate(panels):
                x = index * WIDTH
                draw.text((x+16, 49), labels[index], font=FONT, fill=COLORS[index])
                canvas.paste(panel, (x, 78))
                if index == 0:
                    draw.text((x+16, 473), "Reference animation; not a physical rollout", font=SMALL, fill=(210, 219, 230))
                    draw.text((x+16, 496), f"Full reference duration: {full_steps*.02:.2f} s", font=SMALL, fill=(210, 219, 230))
                else:
                    i = index-1
                    stopped = step >= ends[i]
                    report = reports[i][name]
                    status = (f"{'FAILED' if report['failed'] else 'COMPLETED'} @ {ends[i]*.02:.2f}s  |  FROZEN"
                              if stopped else "RUNNING")
                    draw.text((x+16, 473), status, font=SMALL,
                              fill=(255, 120, 120) if stopped and report['failed'] else COLORS[index])
                    t = max(0, min(step, ends[i])-1)
                    m = lambda key: float(records[i][key][t]) if step else 0.0
                    draw.text((x+16, 496), f"Root error: {m('root_position_error_m'):.2f} m   Joint RMSE: {m('joint_rmse_rad'):.2f} rad", font=SMALL, fill="white")
                    draw.text((x+16, 519), f"Height: {m('root_height_error_m'):.3f}/0.250 m   Tilt: {m('tilt_error'):.3f}/0.800", font=SMALL, fill=(210, 219, 230))
            draw.line((0, 549, CANVAS[0], 549), fill=(52, 65, 81))
            draw.text((text_x, 560), "WORLD XY PATHS (metres) | Shared world camera", font=SMALL, fill="white")
            legend=f"Green: reference    Orange: {args.labels[0]}"
            if count == 2: legend += f"    Blue: {args.labels[1]}"
            draw.text((text_x, 585), legend, font=SMALL, fill=(210, 219, 230))
            draw.text((text_x, 610), "Failed panels freeze; physics does not restart.", font=SMALL, fill=(210, 219, 230))
            draw.text((text_x, 635), "Final scoring trajectories; no extra physical replay.", font=SMALL, fill=(210, 219, 230))
            draw.text((20, 554), f"XY span: {high[0]-low[0]:.1f} x {high[1]-low[1]:.1f} m", font=SMALL, fill=(210, 219, 230))
            for k, xy in enumerate(static_xy):
                if len(xy)>1:
                    draw.line([point(p) for p in xy], fill=tuple(int(v*.35) for v in COLORS[k]), width=1)
            current_paths = [reference[:step+1:5, :2]] + [pose[:min(step,end)+1:5, :2] for pose,end in zip(poses,ends)]
            for k, xy in enumerate(current_paths):
                if len(xy)>1:
                    draw.line([point(p) for p in xy], fill=COLORS[k], width=2)
                px, py = point(xy[-1]);draw.ellipse((px-3,py-3,px+3,py+3),fill=COLORS[k])
            frame = np.asarray(canvas)
            process.stdin.write(frame.tobytes())
            # Overview contains the first 12 s and last 4 s of each comparison.
            # Every frame retains physical time; an explicit cut label marks the tail.
            if video_frame < 12*FPS or (frame_count > 16*FPS and video_frame >= frame_count-4*FPS):
                if video_frame >= 12*FPS:
                    draw.rectangle((0,0,CANVAS[0],43),fill=(80,45,20))
                    draw.text((18,10),f"TAIL EXCERPT  |  {name}  |  physical t={step*.02:.2f}s",font=TITLE,fill="white")
                preview_path = output / f"overview_{motion_index:02d}_{video_frame:05d}.jpg"
                canvas.save(preview_path,quality=90)
                overview_segment.append(preview_path)
            if video_frame in {10,60,min(300,frame_count-1),frame_count-1}:
                preview = output / f"{name}_frame_{video_frame:05d}.jpg"
                canvas.save(preview, quality=92)
                contact_images.append((name, video_frame/FPS, preview))
        process.stdin.close()
        if process.wait() != 0:
            raise RuntimeError("Video encoder failed")
        overview_frames.extend(overview_segment)
        assets.append({"motion": name, "file": filename, "bytes": (output/filename).stat().st_size,
                       "fps": FPS, "playback_speed": 1.0,
                       "duration_seconds": frame_count/FPS, "source_steps": last,
                       "arms": {label:report[name] for label,report in zip(args.labels,reports)}})
        print("VIDEO_COMPLETE", name, frame_count/FPS, flush=True)
    overview = output / ("goal_feedback_comparison_overview.mp4" if count == 2 else "c0_continuation_overview.mp4")
    process = encoder(overview)
    for p in overview_frames:
        with Image.open(p) as frame:
            process.stdin.write(np.asarray(frame.convert("RGB")).tobytes())
    process.stdin.close()
    if process.wait() != 0:
        raise RuntimeError("Overview encoder failed")
    # A small contact sheet supports visual QA without downloading the videos.
    preview_height = round(CANVAS[1]*768/CANVAS[0])
    sheet = Image.new("RGB", (768, preview_height*len(names)), (15,22,34))
    for i,name in enumerate(names):
        chosen = min(((t, p) for n,t,p in contact_images if n==name), key=lambda item: abs(item[0]-6.0))[1]
        with Image.open(chosen) as frame:
            sheet.paste(frame.resize((768,preview_height)),(0,preview_height*i))
    sheet.save(output/"contact_sheet.jpg",quality=90)
    manifest={"selection":names,
              "checkpoints":[{"label":label,"iteration":e['iteration'],"goal_frame":e['goal_frame']} for label,e in zip(args.labels,evaluations)],
              "videos":assets,"overview":{"file":overview.name,"duration_seconds":len(overview_frames)/FPS,
                  "bytes":overview.stat().st_size,"editing":"First 12 seconds plus last 4 seconds where applicable; tail cuts labeled; 1x playback"},
              "rendering":"MuJoCo kinematics on recorded physical qpos, separate kinematic reference, no resimulated physics",
              "recording_results":[{"iteration":e['iteration'],"failed_motions":e['failed_motions'],
                  "mean_normalized_return":e['mean_normalized_return']} for e in evaluations]}
    (output/"video_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    for p in overview_frames:
        p.unlink()  # disposable encoder input, not a retained experiment artifact
    renderer.close()
    print("ALL_VIDEOS_COMPLETE",len(assets),flush=True)


if __name__ == "__main__":
    main()
