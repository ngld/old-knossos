const path = require('path');
const fastify = require('fastify');
const chokidar = require('chokidar');
const { build } = require('esbuild');
const { pnpPlugin } = require('@yarnpkg/esbuild-plugin-pnp');

const app = fastify();

const buildConfig = {
  color: true,
  entryPoints: ['src/index.tsx'],
  bundle: true,
  incremental: true,
  outfile: 'watched/bundle.js',
  plugins: [pnpPlugin({
    filter: /^[^:]+$/,
  })],
  define: {
    'process.env.NODE_ENV': '"development"',
    'process.env.BLUEPRINT_NAMESPACE': 'null',
    'process.env.REACT_APP_BLUEPRINT_NAMESPACE': 'null',
    'global': 'window',
  },
  target: 'es2020',
  loader: {},
};

const listeners = [];
app.get('/events', async (req, reply) => {
  reply.raw.setHeader('Content-Type', 'text/event-stream');
  reply.raw.setHeader('Connection', 'keep-alive');
  reply.raw.setHeader('Cache-Control', 'no-cache,no-transform');
  reply.raw.setHeader('x-no-compression', '1');

  reply.raw.write('data: ready\n\n');

  const listen = () => {
    reply.raw.write('data: reload\n\n');
  };
  listeners.push(listen);
  reply.raw.on('close', () => {
    listeners.splice(listeners.indexOf(listen), 1);
  });
});

app.register(require('fastify-static'), {
  root: path.resolve(path.dirname(buildConfig.outfile)),
});

async function buildWorker() {
  let hasChanges = false;
  let bundle;
  const watcher = chokidar.watch('src', {});

  watcher.on('change', async (_path) => {
    if (!hasChanges) {
      hasChanges = true;
      console.log('Rebuilding...');
      try {
        await bundle.rebuild();
      } catch (e) {
        console.log(e);
      }
      console.log('Done.');

      for (const cb of listeners) {
        cb();
      }
      hasChanges = false;
    }
  });

  try {
    bundle = await build(buildConfig);
  } catch (e) {
    // console.log(e);
    process.exit(1);
  }

  for (const cb of listeners) {
    cb();
  }
  console.log('Ready');
}

void buildWorker();
void app.listen(9000);
