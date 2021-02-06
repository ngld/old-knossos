const { build } = require('esbuild');
const { pnpPlugin } = require('@yarnpkg/esbuild-plugin-pnp');

build({
  color: true,
  entryPoints: ['src/index.tsx'],
  bundle: true,
  minify: true,
  outfile: 'bundle.js',
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
});
