module.exports = {
  parserOpts: {
    strictMode: true,
  },
  presets: [
    ['@babel/preset-react', { runtime: 'automatic' }],
    ['@babel/preset-typescript', { allowDeclareFields: true }],
    [
      '@babel/preset-env',
      {
        targets: 'chrome > 85',
        bugfixes: true,
        modules: false,
      },
    ],
  ],
  plugins: [
    require.resolve('./import-fixer'),
    ['@babel/plugin-proposal-decorators', { legacy: true }],
    ['@babel/plugin-proposal-class-properties', { loose: true }],
    '@babel/plugin-transform-react-inline-elements',
    '@babel/plugin-transform-react-constant-elements',
  ],
};
