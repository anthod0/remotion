import hashlib
import json
import pathlib
import subprocess

root = pathlib.Path(__file__).resolve().parent
repo = root.parent.parent
ff = str(repo / 'packages/compositor-linux-x64-gnu/ffmpeg')
probe = str(repo / 'packages/compositor-linux-x64-gnu/ffprobe')

def run(args):
    return subprocess.run(args, capture_output=True, check=True).stdout

report = {'samples': {}, 'metadata': {}, 'decoded_yuv_sha256': {}}
raw_frames = {}
for name in ['jpeg-before', 'jpeg-after', 'png-before', 'png-after']:
    video = root / f'{name}.mp4'
    report['metadata'][name] = json.loads(run([
        probe, '-v', 'error', '-select_streams', 'v:0', '-show_entries',
        'stream=width,height,pix_fmt,color_space,color_range,color_primaries,color_transfer,nb_frames',
        '-of', 'json', str(video),
    ]))['streams'][0]
    avi = root / f'{name}-decoded.avi'
    run([ff, '-v', 'error', '-i', str(video), '-c:v', 'rawvideo', '-pix_fmt', 'yuv420p', '-y', str(avi)])
    raw = run(['/usr/bin/ffmpeg', '-v', 'error', '-i', str(avi), '-c:v', 'copy', '-f', 'rawvideo', '-'])
    raw_frames[name] = raw
    assert len(raw) == 640 * 360 * 3 // 2 * 30, (name, len(raw))
    report['decoded_yuv_sha256'][name] = hashlib.sha256(raw).hexdigest()
    frame = raw[:640 * 360 * 3 // 2]
    samples = {}
    for color, x in [('red', 80), ('green', 240), ('blue', 400), ('gray', 560)]:
        y = 180
        samples[color] = [frame[y * 640 + x], frame[640 * 360 + (y // 2) * 320 + x // 2], frame[640 * 360 * 5 // 4 + (y // 2) * 320 + x // 2]]
    report['samples'][name] = samples
    run(['/usr/bin/ffmpeg', '-v', 'error', '-i', str(video), '-frames:v', '1', '-y', str(root / f'{name}.png')])

report['png_before_after_identical_all_frames'] = raw_frames['png-before'] == raw_frames['png-after']
assert report['png_before_after_identical_all_frames']
expected_green = [95, 85, 77]
assert all(abs(a-b) <= 2 for a, b in zip(report['samples']['jpeg-after']['green'], expected_green))
assert abs(report['samples']['jpeg-before']['green'][0] - expected_green[0]) >= 10
for name, meta in report['metadata'].items():
    assert meta['color_space'] == 'bt709'
    assert meta['color_range'] == 'tv' and meta['pix_fmt'] == 'yuv420p'
    if name.endswith('after'):
        assert meta['color_primaries'] == meta['color_transfer'] == 'bt709'
(root / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))

labels = ['Reference - original PNG', 'Before fix - JPEG / BT.709', 'After fix - JPEG / BT.709']
inputs = ['reference.png', 'jpeg-before.png', 'jpeg-after.png']
args = ['/usr/bin/ffmpeg', '-v', 'error']
for image in inputs:
    args += ['-i', str(root / image)]
filters = []
for i, label in enumerate(labels):
    filters.append(f'[{i}:v]pad=640:400:0:40:color=white,drawtext=text={label}:fontsize=22:fontcolor=black:x=12:y=10[v{i}]')
filters.append('[v0][v1][v2]vstack=inputs=3[out]')
run(args + ['-filter_complex', ';'.join(filters), '-map', '[out]', '-frames:v', '1', '-y', str(root / 'comparison.png')])
