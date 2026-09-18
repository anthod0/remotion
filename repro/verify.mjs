import fs from 'node:fs/promises';
import {existsSync, writeFileSync} from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';

const dir = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(dir, '../..');
const require = createRequire(path.join(repo, 'packages/example/package.json'));
const {bundle} = require('@remotion/bundler');
const {openBrowser, selectComposition, renderMedia, renderStill} = require('@remotion/renderer');
const oldFilter = 'zscale=matrix=709:matrixin=709:range=limited';
const newFilter = 'zscale=matrix=709:range=limited:primariesin=709:primaries=709:transferin=709:transfer=709';
await fs.mkdir(path.join(dir, 'public'), {recursive: true});
if (!existsSync(path.join(dir, 'node_modules'))) {
  await fs.symlink(path.join(repo, 'packages/example/node_modules'), path.join(dir, 'node_modules'));
}
const serveUrl = await bundle({
  entryPoint: path.join(dir, 'color-repro.tsx'),
  outDir: path.join(dir, 'bundle'),
  rootDir: path.join(repo, 'packages/example'),
  publicDir: path.join(dir, 'public'),
  enableCaching: false,
});
console.log('Bundled:', serveUrl);
const browser = await openBrowser('chrome', {
  browserExecutable: path.join(repo, 'node_modules/.remotion/chrome-headless-shell/linux64/chrome-headless-shell-linux64/chrome-headless-shell'),
});
try {
  const composition = await selectComposition({serveUrl, id: 'ColorBars', puppeteerInstance: browser});
  await renderStill({serveUrl, composition, puppeteerInstance: browser, output: path.join(dir, 'reference.png'), imageFormat: 'png'});
  for (const imageFormat of ['jpeg', 'png']) {
    for (const version of ['before', 'after']) {
      const name = `${imageFormat}-${version}`;
      let filterSeen = 0;
      await renderMedia({
        serveUrl,
        composition,
        puppeteerInstance: browser,
        codec: 'h264',
        colorSpace: 'bt709',
        imageFormat,
        concurrency: 2,
        outputLocation: path.join(dir, `${name}.mp4`),
        ffmpegOverride: ({type, args}) => {
          const result = args.map((arg) => {
            if (arg !== newFilter) return arg;
            filterSeen++;
            return version === 'before' ? oldFilter : newFilter;
          });
          writeFileSync(path.join(dir, `${name}-${type}-ffmpeg-args.json`), JSON.stringify(result, null, 2));
          return result;
        },
      });
      if (filterSeen !== 1) throw new Error(`Expected exactly one filter replacement for ${name}, got ${filterSeen}`);
      console.log('Rendered:', name);
    }
  }
} finally {
  await browser.close({silent: true});
}
